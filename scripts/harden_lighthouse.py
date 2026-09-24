"""Lighthouse on the live site for Update 16A section 4, on the throttled 4G profile. Reports only.

Lighthouse's default mobile run is the throttled 4G profile: a mid-range phone screen, simulated
throttling at 150 ms round trip and 1.6 Mbps down, and the CPU slowed four times. Each page runs
three times in a fresh headless Chrome and the run with the median performance score is the one
reported, because a single Lighthouse run moves by several points. The full reports stay outside the
repo; results/harden/lighthouse.json keeps the numbers of every run and lighthouse.md the medians.

Pages: every page of the web app on production, which serves them all since 2026-09-24. Lighthouse
only loads pages, and the axe run showed which pages send anything but GET on load.

  uv run python scripts/harden_lighthouse.py --reports /tmp/somewhere
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
LIGHTHOUSE = "lighthouse@13.5.0"
PROD = "https://second-look-79t.pages.dev"
# Every page of the web app, the same list the axe run checks (scripts/harden_axe.py).
PATHS = [
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
    "/about",
    "/privacy",
    "/credits",
    "/offline",
    "/share/12",
    "/accessibility",
    "/verify",
    "/city?creek=strawberry-creek",
    "/walk",
    "/walk/v02",
]
PAGES = [(f"production {p}", PROD + p) for p in PATHS]
AUDITS = {
    "first-contentful-paint": "FCP ms",
    "largest-contentful-paint": "LCP ms",
    "total-blocking-time": "TBT ms",
    "cumulative-layout-shift": "CLS",
    "speed-index": "SI ms",
    "interactive": "TTI ms",
    "server-response-time": "TTFB ms",
    "total-byte-weight": "bytes",
}


def one_run(url: str, report: Path) -> dict[str, Any]:
    env = {**os.environ, "CHROME_PATH": CHROME}
    cmd = [
        "npx",
        "-y",
        LIGHTHOUSE,
        url,
        "--quiet",
        "--output=json",
        f"--output-path={report}",
        "--chrome-flags=--headless=new --no-first-run --no-default-browser-check",
        "--only-categories=performance,accessibility,best-practices,seo",
    ]
    subprocess.run(cmd, env=env, check=True, capture_output=True, timeout=600)
    data = json.loads(report.read_text(encoding="utf-8"))
    cats = {
        k: round(v["score"] * 100) for k, v in data["categories"].items() if v["score"] is not None
    }
    metrics = {}
    for audit, label in AUDITS.items():
        a = data["audits"].get(audit, {})
        value = a.get("numericValue")
        metrics[label] = round(value, 3 if label == "CLS" else 0) if value is not None else None
    settings = data["configSettings"]
    return {
        "scores": cats,
        "metrics": metrics,
        "requests": len(
            data["audits"].get("network-requests", {}).get("details", {}).get("items", [])
        ),
        "form_factor": settings.get("formFactor"),
        "throttling": settings.get("throttling"),
        "throttling_method": settings.get("throttlingMethod"),
        "lighthouse": data.get("lighthouseVersion"),
        "final_url": data.get("finalDisplayedUrl") or data.get("finalUrl"),
        "warnings": data.get("runWarnings", []),
    }


def render(data: dict[str, Any], md: Path) -> None:
    lines = [
        "# Lighthouse",
        "",
        f"Measured {data['checked_utc']} by `uv run python scripts/harden_lighthouse.py`, "
        f"Lighthouse {LIGHTHOUSE.split('@')[1]} in headless Chrome on this Mac "
        f"({data['cpus']} CPUs). Default mobile run, which is the throttled 4G profile: a "
        "mid-range phone screen, simulated 150 ms round trip at 1.6 Mbps down, CPU slowed four "
        "times. Three runs per page; the table shows the run with the median performance score, "
        "and the last column shows all three. Full reports stay outside the repo.",
        "",
        "| Page | Perf | A11y | Best practices | SEO | FCP ms | LCP ms | TBT ms | CLS | "
        "SI ms | TTFB ms | Bytes | Perf, all runs |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    skipped = []
    for p in data["pages"]:
        m = p["median"]
        if not m:
            skipped.append(f"- {p['page']} ({p['url']}): HTTP {p['status']}, not deployed")
            continue
        s, x = m["scores"], m["metrics"]
        runs = ", ".join(str(r["scores"].get("performance")) for r in p["runs"])
        lines.append(
            f"| {p['page']} | {s.get('performance')} | {s.get('accessibility')} | "
            f"{s.get('best-practices')} | {s.get('seo')} | {x['FCP ms']} | {x['LCP ms']} | "
            f"{x['TBT ms']} | {x['CLS']} | {x['SI ms']} | {x['TTFB ms']} | {x['bytes']} | {runs} |"
        )
    lines += ["", "Not measured, because they are not deployed there:", "", *skipped, ""]
    warnings = sorted({w for p in data["pages"] for r in p["runs"] for w in r["warnings"]})
    if warnings:
        lines += ["Lighthouse warnings:", "", *[f"- {w}" for w in warnings], ""]
    md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--reports", type=Path, required=True, help="folder outside the repo")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "harden" / "lighthouse.json")
    args = ap.parse_args()
    if ROOT in args.reports.resolve().parents:
        raise SystemExit("--reports must be outside the repo: the full reports are large")
    args.reports.mkdir(parents=True, exist_ok=True)
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    pages = []
    for name, url in PAGES:
        status = httpx.get(url, timeout=20, follow_redirects=True).status_code
        if status != 200:
            pages.append({"page": name, "url": url, "status": status, "runs": [], "median": None})
            print(f"{name}: {status}, not deployed, skipped")
            continue
        runs = []
        for i in range(args.runs):
            slug = name.replace(" ", "_").replace("/", "_")
            runs.append(one_run(url, args.reports / f"{slug}_{i + 1}.json"))
        perf = [r["scores"].get("performance", 0) for r in runs]
        med = statistics.median_low(perf)
        median = runs[perf.index(med)]
        pages.append({"page": name, "url": url, "status": status, "runs": runs, "median": median})
        print(f"{name}: performance {perf}, median run {median['metrics']}")
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    data = {"checked_utc": started, "commit": commit, "cpus": os.cpu_count(), "pages": pages}
    args.out.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    render(data, args.out.with_suffix(".md"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
