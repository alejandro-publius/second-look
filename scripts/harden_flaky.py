"""Run the whole test suite several times and list what flakes (Update 16A section 3).

Runs in a fresh clone of HEAD outside the repo, so nothing the suites write (the web build rewrites
apps/web/public/_headers, npm test rewrites worker/dist) can touch the worktree. Each run is:

- pytest over every test path in pyproject.toml, with a JUnit file per run;
- the Worker golden tests (esbuild, then node --test with the JUnit reporter);
- the Worker end to end (wrangler dev with local D1 and KV) on a port from 8900 to 8999;
- with --web, the web end to end (Playwright on the phone viewport), only when ports 3100 and 8100
  are free, because its config reuses any server already on 3100 and would test somebody else's
  build. It is off by default: while another session uses 3100 on the same machine, binding it
  would get in that session's way.

A test is flaky when its outcome differs between runs. Writes results/harden/flaky.md and
results/harden/flaky.json.

  uv run python scripts/harden_flaky.py --work /tmp/somewhere --runs 3
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
E2E_PORT = 8971


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None, timeout: int = 1800) -> dict:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env={**os.environ, **(env or {})},
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        code, out = proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as exc:
        got = [s.decode() if isinstance(s, bytes) else (s or "") for s in (exc.stdout, exc.stderr)]
        code, out = -1, f"timed out after {timeout} s\n{got[0]}{got[1]}"
    return {"code": code, "seconds": round(time.monotonic() - started, 1), "tail": out[-3000:]}


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def junit(path: Path) -> dict[str, dict[str, str]]:
    """Outcome per test id from a JUnit file: passed, failed, error, skipped or xfail."""
    if not path.exists():
        return {}
    out: dict[str, dict[str, str]] = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        tid = f"{case.get('classname', '')}::{case.get('name', '')}"
        outcome, message = "passed", ""
        for child in case:
            if child.tag in ("failure", "error"):
                outcome, message = (
                    ("failed" if child.tag == "failure" else "error"),
                    (child.get("message") or (child.text or "")),
                )
            elif child.tag == "skipped":
                msg = child.get("message") or ""
                outcome = (
                    "xfail"
                    if msg.startswith("xfail") or child.get("type") == "pytest.xfail"
                    else "skipped"
                )
                message = msg
        out[tid] = {"outcome": outcome, "message": message[:300]}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--work", type=Path, required=True, help="scratch folder outside the repo")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--web", action="store_true", help="also run the Playwright suite on 3100")
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "harden")
    args = ap.parse_args()
    if ROOT in args.work.resolve().parents:
        raise SystemExit("--work must be outside the repo")
    tree = args.work / "tree"
    subprocess.run(["rm", "-rf", str(tree)], check=True)
    subprocess.run(["git", "clone", "-q", str(ROOT), str(tree)], check=True)
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=tree, capture_output=True, text=True
    ).stdout.strip()
    setup = {
        "uv sync": run(["uv", "sync", "--frozen"], tree),
        "worker npm ci": run(["npm", "ci", "--no-audit", "--no-fund"], tree / "worker"),
    }
    if args.web:
        setup["web npm ci"] = run(["npm", "ci", "--no-audit", "--no-fund"], tree / "apps" / "web")
    runs: list[dict[str, Any]] = []
    for i in range(1, args.runs + 1):
        rd = args.work / f"run{i}"
        rd.mkdir(parents=True, exist_ok=True)
        r: dict[str, Any] = {"run": i, "suites": {}}
        py = run(["uv", "run", "pytest", f"--junitxml={rd / 'pytest.xml'}"], tree)
        py["tests"] = junit(rd / "pytest.xml")
        r["suites"]["pytest"] = py
        bundle = tree / "worker" / "dist" / "golden.test.mjs"
        build = run(
            [
                "npx",
                "esbuild",
                "test/golden.test.ts",
                "--bundle",
                "--platform=node",
                "--format=esm",
                f"--outfile={bundle}",
                "--log-level=warning",
            ],
            tree / "worker",
        )
        golden = run(
            [
                "node",
                "--test",
                "--test-reporter=junit",
                f"--test-reporter-destination={rd / 'golden.xml'}",
                str(bundle),
            ],
            tree / "worker",
        )
        golden["build_code"] = build["code"]
        golden["tests"] = junit(rd / "golden.xml")
        r["suites"]["worker golden"] = golden
        e2e = run(["node", "test/e2e.mjs"], tree / "worker", env={"E2E_PORT": str(E2E_PORT)})
        e2e["tests"] = {
            "worker/test/e2e.mjs::end to end": {
                "outcome": "passed" if e2e["code"] == 0 else "failed",
                "message": "" if e2e["code"] == 0 else e2e["tail"][-300:],
            }
        }
        r["suites"]["worker e2e"] = e2e
        web: dict[str, Any]
        if not args.web:
            web = {"code": None, "seconds": 0, "tail": "not run: needs --web", "tests": {}}
        elif port_free(3100) and port_free(8100):
            web = run(
                ["npx", "playwright", "test", "--reporter=junit"],
                tree / "apps" / "web",
                env={"PLAYWRIGHT_JUNIT_OUTPUT_NAME": str(rd / "web.xml"), "CI": ""},
                timeout=2400,
            )
            web["tests"] = junit(rd / "web.xml")
        else:
            web = {"code": None, "seconds": 0, "tail": "ports 3100 or 8100 busy", "tests": {}}
        r["suites"]["web e2e"] = web
        runs.append(r)
        print(
            f"run {i}: "
            + ", ".join(f"{k} exit {v['code']} in {v['seconds']} s" for k, v in r["suites"].items())
        )

    flaky = []
    suites = sorted({s for r in runs for s in r["suites"]})
    counts: dict[str, list[dict[str, int]]] = {}
    for suite in suites:
        ids = sorted({t for r in runs for t in r["suites"][suite]["tests"]})
        counts[suite] = []
        for r in runs:
            tests = r["suites"][suite]["tests"]
            c: dict[str, int] = {}
            for t in tests.values():
                c[t["outcome"]] = c.get(t["outcome"], 0) + 1
            counts[suite].append(c)
        for tid in ids:
            seen = [
                r["suites"][suite]["tests"].get(tid, {"outcome": "absent", "message": ""})
                for r in runs
            ]
            if len({s["outcome"] for s in seen}) > 1:
                flaky.append({"suite": suite, "test": tid, "seen": seen})
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    args.out.mkdir(parents=True, exist_ok=True)
    slim = [
        {
            "run": r["run"],
            "suites": {
                k: {"code": v["code"], "seconds": v["seconds"], "counts": counts[k][r["run"] - 1]}
                for k, v in r["suites"].items()
            },
        }
        for r in runs
    ]
    (args.out / "flaky.json").write_text(
        json.dumps(
            {
                "measured_utc": stamp,
                "commit": commit,
                "setup": {k: v["code"] for k, v in setup.items()},
                "runs": slim,
                "flaky": flaky,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Flaky tests",
        "",
        f"Measured {stamp} at commit {commit} by `uv run python scripts/harden_flaky.py --runs "
        f"{args.runs}`, in a fresh clone outside the repo. A test is flaky when its outcome "
        "differs between runs.",
        "",
        "## Runs",
        "",
        "| Run | Suite | Exit | Seconds | Outcomes |",
        "|---|---|---|---|---|",
    ]
    for r in runs:
        for k, v in r["suites"].items():
            c = counts[k][r["run"] - 1]
            shown = ", ".join(f"{n} {o}" for o, n in sorted(c.items())) or v["tail"][-80:].strip()
            lines.append(f"| {r['run']} | {k} | {v['code']} | {v['seconds']} | {shown} |")
    lines += ["", "## Flaky", ""]
    if not flaky:
        lines += [f"None. Every test had the same outcome in all {args.runs} runs.", ""]
    else:
        lines += ["| Suite | Test | What we saw, run by run |", "|---|---|---|"]
        for f in flaky:
            story = "; ".join(
                f"run {i + 1} {s['outcome']}" + (f" ({s['message'][:120]})" if s["message"] else "")
                for i, s in enumerate(f["seen"])
            )
            lines.append(f"| {f['suite']} | `{f['test']}` | {story.replace('|', '/')} |")
        lines.append("")
    failing = [
        (r["run"], k, v["tail"][-400:])
        for r in runs
        for k, v in r["suites"].items()
        if v["code"] not in (0, None)
    ]
    if failing:
        lines += ["## Runs that did not exit 0", ""]
        for run_no, k, tail in failing:
            lines += [f"Run {run_no}, {k}:", "", "```", tail.strip(), "```", ""]
    (args.out / "flaky.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(flaky)} flaky tests; wrote {args.out / 'flaky.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
