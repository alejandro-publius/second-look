"""Count the tests, so the README can cite the counts with claim tokens (hard rule 12).

  uv run python scripts/count_tests.py            writes results/test_counts.json
  uv run python scripts/count_tests.py --print    prints the counts and writes nothing

What is counted, and how:

- Python tests: `uv run pytest --collect-only -q`, which prints one line per test file with its
  count (pyproject.toml already adds one -q), summed here.
- Worker golden cases: every list at the top of worker/golden/*.json, counted the way
  evals/golden_vectors.py counts them when it writes the files, plus the node test blocks in
  worker/test/golden.test.ts that replay them.
- Playwright: `npx playwright test --list` in apps/web, after scripts/build-content.mjs has
  written the content the specs import. Its last line reads "Total: N tests in M files".
- Worker end to end sections: the steps worker/test/e2e.mjs names with at("..."), after the two
  that only set up the local database and start wrangler dev.

Not part of make check on purpose: every branch that adds a test would turn it red. Run it
last, before the README is rendered: `make test-counts`.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "test_counts.json"
GOLDEN_DIR = ROOT / "worker" / "golden"
GOLDEN_TEST = ROOT / "worker" / "test" / "golden.test.ts"
E2E = ROOT / "worker" / "test" / "e2e.mjs"
WEB = ROOT / "apps" / "web"
PYTEST_ARGS = ["uv", "run", "pytest", "--collect-only", "-q"]

# "core/tests/test_gate.py: 41" when pytest runs at -qq, "path::name" at -q.
PER_FILE_RE = re.compile(r"^(\S+\.py): (\d+)$")
PER_TEST_RE = re.compile(r"^(\S+\.py)::\S")
COLLECTED_RE = re.compile(r"^(\d+) tests? collected")
PLAYWRIGHT_TOTAL_RE = re.compile(r"^Total: (\d+) tests? in (\d+) files?$")
NODE_TEST_RE = re.compile(r"^\s*test\(\s*[\"'`]", re.M)
E2E_STEP_RE = re.compile(r"^\s*at\(\s*\"([^\"]+)\"\s*\);", re.M)
# The steps before these two are set up, not a route being driven.
E2E_SETUP_STEPS = ("apply schema and arms", "start wrangler dev")


class CountError(RuntimeError):
    """A count could not be taken. Nothing is written."""


def parse_pytest(output: str) -> dict[str, int]:
    """Tests and files from pytest's --collect-only output, at either level of quiet."""
    per_file: dict[str, int] = {}
    for line in output.splitlines():
        line = line.strip()
        m = PER_FILE_RE.match(line)
        if m:
            per_file[m.group(1)] = per_file.get(m.group(1), 0) + int(m.group(2))
            continue
        m = PER_TEST_RE.match(line)
        if m:
            per_file[m.group(1)] = per_file.get(m.group(1), 0) + 1
    if not per_file:
        raise CountError("pytest printed no test file; is the collection broken?")
    tests = sum(per_file.values())
    for line in output.splitlines():
        m = COLLECTED_RE.match(line.strip())
        if m and int(m.group(1)) != tests:
            raise CountError(f"pytest says {m.group(1)} collected, the lines add up to {tests}")
    return {"tests": tests, "files": len(per_file)}


def parse_playwright(output: str) -> dict[str, int]:
    for line in reversed(output.splitlines()):
        m = PLAYWRIGHT_TOTAL_RE.match(line.strip())
        if m:
            tests, files = int(m.group(1)), int(m.group(2))
            if tests == 0:
                raise CountError("Playwright listed no test; did build-content.mjs run?")
            return {"tests": tests, "spec_files": files}
    raise CountError("Playwright printed no Total line")


def count_golden(golden_dir: Path, test_file: Path) -> dict[str, int]:
    files = sorted(golden_dir.glob("*.json"))
    if not files:
        raise CountError(f"no golden vector files in {golden_dir}")
    cases = 0
    for path in files:
        doc = json.loads(path.read_text(encoding="utf-8"))
        cases += sum(len(v) for v in doc.values() if isinstance(v, list))
    node_tests = len(NODE_TEST_RE.findall(test_file.read_text(encoding="utf-8")))
    return {"cases": cases, "files": len(files), "node_tests": node_tests}


def e2e_sections(text: str) -> list[str]:
    steps = E2E_STEP_RE.findall(text)
    missing = [s for s in E2E_SETUP_STEPS if s not in steps]
    if missing:
        raise CountError(f"worker/test/e2e.mjs no longer names the set up steps {missing}")
    after = steps.index(E2E_SETUP_STEPS[-1]) + 1
    return steps[after:]


def _run(argv: list[str], cwd: Path) -> str:
    try:
        done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise CountError(f"{argv[0]} is not installed") from exc
    if done.returncode != 0:
        tail = "\n".join((done.stdout + done.stderr).strip().splitlines()[-5:])
        raise CountError(f"{' '.join(argv)} exited {done.returncode}:\n{tail}")
    return done.stdout + done.stderr


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return done.stdout.strip()


def measure() -> dict[str, Any]:
    if not (WEB / "node_modules").exists():
        raise CountError("apps/web has no node_modules; run (cd apps/web && npm ci) first")
    python = parse_pytest(_run(PYTEST_ARGS, ROOT))
    _run(["node", "scripts/build-content.mjs"], WEB)
    playwright = parse_playwright(_run(["npx", "playwright", "test", "--list"], WEB))
    sections = e2e_sections(E2E.read_text(encoding="utf-8"))
    return {
        "script": "scripts/count_tests.py",
        "synthetic": False,
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "measured_at_commit": _git("rev-parse", "--short", "HEAD"),
        "tree_had_changes": bool(_git("status", "--porcelain")),
        "python": {**python, "command": " ".join(PYTEST_ARGS)},
        "worker_golden": count_golden(GOLDEN_DIR, GOLDEN_TEST),
        "playwright": {**playwright, "command": "npx playwright test --list"},
        "worker_e2e": {"sections": len(sections), "names": sections},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--print", action="store_true", help="print the counts, write nothing")
    args = parser.parse_args(argv)
    try:
        counts = measure()
    except CountError as exc:
        print(f"test-counts: {exc}", file=sys.stderr)
        return 1
    text = json.dumps(counts, indent=2) + "\n"
    if args.print:
        print(text, end="")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(
        f"test-counts: {counts['python']['tests']} Python tests, "
        f"{counts['worker_golden']['cases']} golden cases, "
        f"{counts['playwright']['tests']} Playwright tests, "
        f"{counts['worker_e2e']['sections']} e2e sections into {OUT.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
