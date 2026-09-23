"""Coverage of core/, apps/api and worker/src, before and after the harden tests (Update 16A).

Python: pytest-cov with branch coverage over the whole suite, run through 'uv run --with pytest-cov'
so the lock file does not change, with the data file kept outside the repo. A function is under
the bar when its own line and branch coverage is below 90 percent. Test files are left out of the
totals. The Worker: the golden tests bundled with source maps and run under c8, so the numbers are
per TypeScript line; files the golden tests never load are listed at 0, because only the Worker
end to end run (wrangler dev, not instrumented) reaches them.

"Before" is measured on a clone at --before-ref, the commit before the harden tests, unless a JSON
file from an earlier run is passed with --before-json. Writes results/harden/coverage.md and
results/harden/coverage.json.

  uv run python scripts/harden_coverage.py --work /tmp/somewhere
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
BAR = 90.0


def sh(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> str:
    proc = subprocess.run(
        cmd, cwd=cwd, env={**os.environ, **(env or {})}, capture_output=True, text=True, check=False
    )
    return proc.stdout + proc.stderr


def measure_python(tree: Path, work: Path, name: str) -> tuple[Path, str]:
    out = work / f"{name}.json"
    log = sh(
        [
            "uv",
            "run",
            "--with",
            "pytest-cov",
            "pytest",
            "--cov=core",
            "--cov=apps/api",
            "--cov-branch",
            "-rfE",
            f"--cov-report=json:{out}",
        ],
        cwd=tree,
        env={"COVERAGE_FILE": str(work / f".coverage-{name}")},
    )
    (work / f"pytest-{name}.log").write_text(log, encoding="utf-8")
    summary = next(
        (ln for ln in reversed(log.splitlines()) if " passed" in ln or " failed" in ln), ""
    )
    return out, summary.strip("= ")


def measure_worker(tree: Path, work: Path) -> dict[str, Any]:
    """Bundle the golden tests with source maps into a scratch layout that mirrors worker/."""
    wroot = work / "wroot"
    (wroot / "worker" / "dist").mkdir(parents=True, exist_ok=True)
    golden = wroot / "worker" / "golden"
    if golden.is_symlink() or golden.exists():
        golden.unlink()
    golden.symlink_to(tree / "worker" / "golden")
    bundle = wroot / "worker" / "dist" / "golden.cov.mjs"
    sh(
        [
            "npx",
            "esbuild",
            "test/golden.test.ts",
            "--bundle",
            "--platform=node",
            "--format=esm",
            "--sourcemap=inline",
            "--sources-content=true",
            f"--outfile={bundle}",
            "--log-level=warning",
        ],
        cwd=tree / "worker",
    )
    reports = work / "c8"
    log = sh(
        [
            "npx",
            "-y",
            "c8@10",
            "--reporter=json-summary",
            "--reporter=text",
            f"--reports-dir={reports}",
            "--exclude=**/test/**",
            "--exclude=**/node_modules/**",
            "node",
            "--test",
            "--enable-source-maps",
            str(bundle),
        ],
        cwd=bundle.parent,
    )
    raw = json.loads((reports / "coverage-summary.json").read_text(encoding="utf-8"))
    files: dict[str, dict[str, float]] = {}
    for path, s in raw.items():
        if path == "total" or "/worker/src/" not in path or path.endswith(".json"):
            continue
        rel = "worker/src/" + path.split("/worker/src/", 1)[1]
        files[rel] = {k: s[k]["pct"] for k in ("lines", "branches", "functions")}
    for ts in sorted((tree / "worker" / "src").rglob("*.ts")):
        rel = str(ts.relative_to(tree))
        files.setdefault(rel, {"lines": 0.0, "branches": 0.0, "functions": 0.0, "not_loaded": 1})
    tests = next((ln for ln in log.splitlines() if ln.startswith("ℹ tests")), "")
    passed = next((ln for ln in log.splitlines() if ln.startswith("ℹ pass")), "")
    return {"files": files, "tests": f"{tests.strip('ℹ ')}, {passed.strip('ℹ ')}"}


def package_totals(cov: dict[str, Any], prefix: str) -> dict[str, float]:
    stmts = miss = br = brmiss = 0
    for path, f in cov["files"].items():
        if not path.startswith(prefix) or "/tests/" in path:
            continue
        s = f["summary"]
        stmts += s["num_statements"]
        miss += s["missing_lines"]
        br += s.get("num_branches", 0)
        brmiss += s.get("missing_branches", 0)
    covered = (stmts - miss) + (br - brmiss)
    total = stmts + br
    return {
        "statements": stmts,
        "missing": miss,
        "branches": br,
        "missing_branches": brmiss,
        "percent": round(100 * covered / total, 1) if total else 100.0,
    }


def functions_under(cov: dict[str, Any]) -> dict[str, float]:
    out = {}
    for path, f in cov["files"].items():
        if not path.startswith("core/") or "/tests/" in path:
            continue
        for fn, info in f.get("functions", {}).items():
            pct = info["summary"]["percent_covered"]
            if fn and pct < BAR:
                out[f"{path}::{fn}"] = round(pct, 1)
    return out


def function_pct(cov: dict[str, Any], key: str) -> float | None:
    path, fn = key.split("::")
    info = cov["files"].get(path, {}).get("functions", {}).get(fn)
    return round(info["summary"]["percent_covered"], 1) if info else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--work", type=Path, required=True, help="scratch folder outside the repo")
    ap.add_argument("--before-ref", default="92fa280")
    ap.add_argument("--before-json", type=Path)
    ap.add_argument("--before-summary", default="")
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "harden")
    args = ap.parse_args()
    if ROOT in args.work.resolve().parents:
        raise SystemExit("--work must be outside the repo")
    args.work.mkdir(parents=True, exist_ok=True)

    if args.before_json:
        before_path, before_summary = args.before_json, args.before_summary
    else:
        clone = args.work / "before-tree"
        if not clone.exists():
            sh(["git", "clone", "-q", str(ROOT), str(clone)], cwd=args.work)
        sh(["git", "checkout", "-q", args.before_ref], cwd=clone)
        sh(["uv", "sync", "--frozen"], cwd=clone)
        before_path, before_summary = measure_python(clone, args.work, "before")
    after_path, after_summary = measure_python(ROOT, args.work, "after")
    before = json.loads(before_path.read_text(encoding="utf-8"))
    after = json.loads(after_path.read_text(encoding="utf-8"))
    worker = measure_worker(ROOT, args.work)

    under_before = functions_under(before)
    rows = [
        (k, v, function_pct(after, k)) for k, v in sorted(under_before.items(), key=lambda x: x[0])
    ]
    still = functions_under(after)
    totals = {
        pkg: {"before": package_totals(before, pkg), "after": package_totals(after, pkg)}
        for pkg in ("core/", "apps/api/")
    }
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    commit = sh(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT).strip()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "coverage.json").write_text(
        json.dumps(
            {
                "measured_utc": stamp,
                "commit": commit,
                "before_ref": args.before_ref,
                "suite_before": before_summary,
                "suite_after": after_summary,
                "totals": totals,
                "functions_under_90_before": under_before,
                "functions_under_90_after": still,
                "worker": worker,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )

    def pct(t: dict[str, float]) -> str:
        return (
            f"{t['percent']} ({t['statements']} statements, {t['missing']} missed; "
            f"{t['branches']} branches, {t['missing_branches']} missed)"
        )

    lines = [
        "# Coverage",
        "",
        f"Measured {stamp} at commit {commit} by `uv run python scripts/harden_coverage.py`. "
        f"Before is commit {args.before_ref}, the last commit without the harden tests. Line "
        "and branch coverage together, over the whole Python suite, with test files left out of "
        "the totals.",
        "",
        f"- Suite before: {before_summary or 'see coverage.json'}",
        f"- Suite after: {after_summary}",
        "",
        "## Python packages",
        "",
        "| Package | Before, percent | After, percent |",
        "|---|---|---|",
        *[f"| {pkg} | {pct(t['before'])} | {pct(t['after'])} |" for pkg, t in totals.items()],
        "",
        f"## Core functions that were under {BAR:.0f} percent",
        "",
        f"{len(under_before)} functions in core/ were under the bar before; "
        f"{len(still)} are under it after.",
        "",
        "| Function | Before | After |",
        "|---|---|---|",
        *[f"| `{k}` | {b} | {a} |" for k, b, a in rows],
        "",
    ]
    if still:
        lines += ["Still under the bar after:", ""]
        lines += [f"- `{k}`: {v}" for k, v in sorted(still.items())] + [""]
    lines += [
        "## apps/api files",
        "",
        "| File | Before | After |",
        "|---|---|---|",
    ]
    for path in sorted(after["files"]):
        if path.startswith("apps/api/") and "/tests/" not in path:
            b = before["files"].get(path, {}).get("summary", {}).get("percent_covered")
            a = after["files"][path]["summary"]["percent_covered"]
            lines.append(f"| {path} | {round(b, 1) if b is not None else 'none'} | {round(a, 1)} |")
    lines += [
        "",
        "## worker/src",
        "",
        f"The golden tests, run under c8 with source maps: {worker['tests']}. The harden run added "
        "no Worker test, so before and after are the same. Files marked not loaded are reached "
        "only by `make worker-e2e`, which drives wrangler dev over HTTP and is not instrumented.",
        "",
        "| File | Lines | Branches | Functions |",
        "|---|---|---|---|",
    ]
    for path, s in sorted(worker["files"].items()):
        if s.get("not_loaded"):
            lines.append(f"| {path} | not loaded | not loaded | not loaded |")
        else:
            lines.append(f"| {path} | {s['lines']} | {s['branches']} | {s['functions']} |")
    (args.out / "coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for pkg, t in totals.items():
        print(f"{pkg} {t['before']['percent']} to {t['after']['percent']}")
    print(f"core functions under {BAR}: {len(under_before)} before, {len(still)} after")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
