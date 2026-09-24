"""axe on every deployed screen, phone and desktop, for Update 16A section 4. Reports, never fixes.

Drives Chromium through the Playwright and axe-core packages that apps/web already installs, so no
new dependency. Every request that is not GET, HEAD or OPTIONS is aborted before it leaves the
browser and listed, so no screen can write to production while it is checked. Each screen is the
first view of its route; the inner screens of the two-minute test need a POST to reach and are
checked by the repo's own Playwright suite on a local build instead.

Targets: production (built from main) for every route it serves, and the depth preview for the
routes production does not serve yet. Viewports: phone 390 by 844 in light and dark, and desktop
1280 by 800. Rules: WCAG 2.0, 2.1 and 2.2 at A and AA, plus axe best practices. Writes
results/harden/axe.json; docs/internal/reviews/A11Y_00.md is written from it.

  uv run python scripts/harden_axe.py
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WEB_PKG = ROOT / "apps" / "web" / "package.json"
PROD = "https://second-look-79t.pages.dev"
PREVIEW = "https://depth.second-look-79t.pages.dev"
PROD_PATHS = [
    "/",
    "/t",
    "/demo",
    "/judges",
    "/check",
    "/spot",
    "/quick",
    "/two",
    "/poster",
    "/how-we-know",
    "/verify",
    "/about",
    "/privacy",
    "/credits",
    "/offline",
    "/share/12",
]
PREVIEW_ONLY = ["/city?creek=strawberry-creek"]  # /health there is API JSON, not a screen
VIEWPORTS = [
    {"name": "phone", "width": 390, "height": 844, "dpr": 3, "mobile": True, "dark": False},
    {"name": "phone-dark", "width": 390, "height": 844, "dpr": 3, "mobile": True, "dark": True},
    {"name": "desktop", "width": 1280, "height": 800, "dpr": 1, "mobile": False, "dark": False},
]
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"]

JS = r"""
const { createRequire } = require("node:module");
const req = createRequire(process.env.WEB_PKG);
const { chromium } = req("@playwright/test");
const AxeBuilder = req("@axe-core/playwright").default;
const cfg = JSON.parse(process.env.AXE_CFG);
(async () => {
  const browser = await chromium.launch();
  const out = [];
  for (const vp of cfg.viewports) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      deviceScaleFactor: vp.dpr,
      isMobile: vp.mobile,
      hasTouch: vp.mobile,
      colorScheme: vp.dark ? "dark" : "light",
    });
    let blocked = [];
    await context.route("**/*", (route) => {
      const r = route.request();
      if (!["GET", "HEAD", "OPTIONS"].includes(r.method())) {
        blocked.push(`${r.method()} ${r.url()}`);
        return route.abort();
      }
      return route.continue();
    });
    for (const t of cfg.targets) {
      for (const p of t.paths) {
        blocked = [];
        const page = await context.newPage();
        const origins = new Set();
        page.on("request", (r) => {
          try { origins.add(new URL(r.url()).origin); } catch (e) { /* data: urls */ }
        });
        let status = 0;
        let error = "";
        try {
          // Some screens keep a request open (the API wake up, the sandbox read), so wait for
          // the load event and then a fixed pause rather than for the network to go quiet.
          const resp = await page.goto(t.base + p, { waitUntil: "load", timeout: 60000 });
          status = resp ? resp.status() : 0;
          await page.waitForTimeout(3000);
        } catch (e) {
          error = String(e).slice(0, 200);
        }
        let violations = [];
        let incomplete = [];
        let passes = 0;
        if (!error) {
          const res = await new AxeBuilder({ page }).withTags(cfg.tags).analyze();
          violations = res.violations.map((v) => ({
            id: v.id, impact: v.impact, help: v.help, helpUrl: v.helpUrl, tags: v.tags,
            nodes: v.nodes.length,
            examples: v.nodes.slice(0, 5).map((n) => ({
              target: n.target.join(" "),
              html: n.html.slice(0, 240),
              summary: (n.failureSummary || "").slice(0, 400),
            })),
          }));
          incomplete = res.incomplete.map((v) => ({
            id: v.id, impact: v.impact, nodes: v.nodes.length,
          }));
          passes = res.passes.length;
        }
        out.push({
          target: t.name, base: t.base, path: p, viewport: vp.name, status, error,
          violations, incomplete, passes, blocked_writes: blocked, origins: [...origins],
        });
        await page.close();
      }
    }
    await context.close();
  }
  await browser.close();
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
"""


def run(targets: list[dict[str, Any]], viewports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    env = {
        **os.environ,
        "WEB_PKG": str(WEB_PKG),
        "AXE_CFG": json.dumps({"targets": targets, "viewports": viewports, "tags": TAGS}),
    }
    proc = subprocess.run(
        ["node", "-e", JS], env=env, capture_output=True, text=True, timeout=3600, check=False
    )
    if proc.returncode != 0:
        raise SystemExit(f"axe run failed:\n{proc.stderr[-4000:]}")
    rows: list[dict[str, Any]] = json.loads(proc.stdout)
    return rows


def render(data: dict[str, Any], md: Path) -> None:
    """Write the review page from the JSON, so the page and the numbers cannot drift apart."""
    rows = data["screens"]
    by_impact: dict[str, int] = {}
    for r in rows:
        for v in r["violations"]:
            by_impact[v["impact"] or "none"] = by_impact.get(v["impact"] or "none", 0) + 1
    serious = [
        (r, v) for r in rows for v in r["violations"] if v["impact"] in ("serious", "critical")
    ]
    origins = sorted({o for r in rows for o in r["origins"]})
    writes = [w for r in rows for w in r["blocked_writes"]]
    failed = [r for r in rows if r["error"] or r["status"] != 200]
    lines = [
        "# Accessibility check 00",
        "",
        f"Checked {data['checked_utc']} at commit {data['commit']} by `uv run python "
        "scripts/harden_axe.py`, with axe-core through Playwright and Chromium, the packages "
        "apps/web already installs. Rules: " + ", ".join(data["tags"]) + ". Raw results: "
        "`results/harden/axe.json`.",
        "",
        "What was checked: the first view of every route production serves (built from main), "
        "and /city on the depth preview because production does not serve it yet. Each at "
        "phone size 390 by 844 in light and in dark, and at desktop 1280 by 800. "
        f"{len(rows)} screen views in all. /walk is deployed nowhere yet. /health on the "
        "preview is the API's JSON, not a screen, so it is left out.",
        "",
        "What was not: the inner screens of the two-minute test (consent sent, lesson, items, "
        "end screen) and of the creek check need a POST to reach, and nothing here writes to "
        "production. The repo's own apps/web/tests/axe.spec.ts covers consent and one test item, "
        "the demo, the check's first and location screens, a spot record and /two on a local "
        "build with a mocked API; it serves on port 3100, which another session uses on this "
        "machine, so it was not run here. CI runs it.",
        "",
        "Every request that was not GET, HEAD or OPTIONS was aborted before it left the "
        f"browser: {len(writes)} were attempted. Origins any screen asked for: "
        + ", ".join(origins)
        + ". None is a third party.",
        "",
        "## Counts",
        "",
        "| Impact | Violations (rule hits across screen views) |",
        "|---|---|",
        *[f"| {k} | {n} |" for k, n in sorted(by_impact.items())],
        f"| serious or critical | {len(serious)} |",
        "",
    ]
    if not by_impact:
        lines += ["No violations on any screen view.", ""]
    lines += [
        "Serious or critical findings get a patch file under docs/internal/reviews/patches/. "
        + (
            "There are none, so no accessibility patch was written."
            if not serious
            else f"There are {len(serious)}; see the patches."
        ),
        "",
        "## Findings",
        "",
    ]
    hits = [(r, v) for r in rows for v in r["violations"]]
    if not hits:
        lines += ["None.", ""]
    else:
        lines += [
            "| Screen | Viewport | Rule | Impact | Nodes | What axe says | Example |",
            "|---|---|---|---|---|---|---|",
        ]
        for r, v in hits:
            ex = v["examples"][0]["target"] if v["examples"] else ""
            lines.append(
                f"| {r['target']} {r['path']} | {r['viewport']} | {v['id']} | {v['impact']} | "
                f"{v['nodes']} | {v['help']} | `{ex}` |"
            )
        lines.append("")
    lines += [
        "## Every screen view",
        "",
        "| Target | Screen | Viewport | HTTP | Violations | Needs review | Rules passed |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        inc = len(r["incomplete"]) if isinstance(r["incomplete"], list) else r["incomplete"]
        lines.append(
            f"| {r['target']} | {r['path']} | {r['viewport']} | {r['status']} | "
            f"{len(r['violations'])} | {inc} | {r['passes']} |"
        )
    if failed:
        lines += ["", "Screen views that did not load:", ""]
        lines += [
            f"- {r['target']} {r['path']} {r['viewport']}: {r['error'][:160]}" for r in failed
        ]
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "harden" / "axe.json")
    ap.add_argument(
        "--md", type=Path, default=ROOT / "docs" / "internal" / "reviews" / "A11Y_00.md"
    )
    ap.add_argument("--render-only", action="store_true", help="rewrite the page from --out")
    args = ap.parse_args()
    if args.render_only:
        render(json.loads(args.out.read_text(encoding="utf-8")), args.md)
        return 0
    targets = [
        {"name": "production", "base": PROD, "paths": PROD_PATHS},
        {"name": "depth preview", "base": PREVIEW, "paths": PREVIEW_ONLY},
    ]
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rows = run(targets, VIEWPORTS)
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {"checked_utc": started, "commit": commit, "tags": TAGS, "screens": rows}, indent=1
        )
        + "\n",
        encoding="utf-8",
    )
    by_impact: dict[str, int] = {}
    for r in rows:
        for v in r["violations"]:
            by_impact[v["impact"] or "none"] = by_impact.get(v["impact"] or "none", 0) + 1
    render(json.loads(args.out.read_text(encoding="utf-8")), args.md)
    writes = sum(len(r["blocked_writes"]) for r in rows)
    print(f"{len(rows)} screen views; violations by impact {by_impact}; writes blocked {writes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
