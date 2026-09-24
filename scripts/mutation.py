"""make mutation: do the tests notice when four deciding modules are broken? (UPDATE_29 section 4)

mutmut changes core/gate.py, core/followups.py, core/scoring.py and core/fhir_emit.py one small
change at a time (a < becomes <=, an and becomes an or, a word in a message changes, a line goes)
and runs core's own tests against each changed copy. A change the tests catch is killed; one they
miss survived. A module's score is the share of its changes the tests caught, and each of the
four must be at 85 percent or more. pyproject.toml, [tool.mutmut], says what is changed and which
tests run.

mutmut works in mutants/, which git ignores. This script empties it first, so no result from an
earlier run is reused, then reads what each changed copy did and writes results/mutation.json.
It fails if a module is under the line, if a change was never checked, or if a module has no kill
at all, because that would mean the tests never ran the changed code. About three minutes.

Run: uv run python scripts/mutation.py            (make mutation)
     uv run python scripts/mutation.py --no-run   read the last run in mutants/ again
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("core/gate.py", "core/followups.py", "core/scoring.py", "core/fhir_emit.py")
THRESHOLD_PERCENT = 85.0
OUT = ROOT / "results" / "mutation.json"
SHORT_KEYS = ("mutants", "killed", "survived", "timeout", "score_percent")
SCORE_RULE = (
    "killed divided by every change checked, times 100, to one decimal; a timeout or any other "
    "outcome counts as not caught"
)


def status_by_exit_code() -> Mapping[int | None, str]:
    """mutmut's own reading of a changed copy's exit code: killed, survived, timeout and so on."""
    from mutmut.stats import status_by_exit_code as table

    return table


def module_counts(meta: Mapping[str, Any], statuses: Mapping[int | None, str]) -> dict[str, Any]:
    """Counts for one module from its mutants/<module>.meta file."""
    codes: Mapping[str, int | None] = meta.get("exit_code_by_key") or {}
    by_status = Counter(statuses[code] for code in codes.values())
    killed = by_status.pop("killed", 0)
    survived = by_status.pop("survived", 0)
    timeout = by_status.pop("timeout", 0)
    total = killed + survived + timeout + sum(by_status.values())
    survivors = sorted(name for name, code in codes.items() if statuses[code] == "survived")
    return {
        "mutants": total,
        "killed": killed,
        "survived": survived,
        "timeout": timeout,
        "other": dict(sorted(by_status.items())),
        "score_percent": round(100.0 * killed / total, 1) if total else 0.0,
        "survivors": survivors,
    }


def problems_with(modules: Mapping[str, Mapping[str, Any]]) -> list[str]:
    problems: list[str] = []
    for module in MODULES:
        counts = modules.get(module)
        if counts is None:
            problems.append(f"{module}: mutmut left no result")
            continue
        if counts["killed"] == 0:
            problems.append(f"{module}: no change was caught, so the tests never ran it")
        if counts["other"].get("not checked"):
            problems.append(f"{module}: {counts['other']['not checked']} changes never checked")
        if counts["score_percent"] < THRESHOLD_PERCENT:
            problems.append(
                f"{module}: {counts['score_percent']} percent of changes caught, "
                f"under {THRESHOLD_PERCENT:.0f}"
            )
    return problems


def read_run(mutants: Path) -> dict[str, dict[str, Any]]:
    statuses = status_by_exit_code()
    out: dict[str, dict[str, Any]] = {}
    for module in MODULES:
        meta = mutants / f"{module}.meta"
        if meta.is_file():
            out[module] = module_counts(json.loads(meta.read_text(encoding="utf-8")), statuses)
    return out


def document(modules: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    total = Counter[str]()
    for counts in modules.values():
        for key in ("mutants", "killed", "survived", "timeout"):
            total[key] += int(counts[key])
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "script": "scripts/mutation.py",
        "synthetic": False,
        "tool": "mutmut",
        "tool_version": importlib.metadata.version("mutmut"),
        "python": platform.python_version(),
        "tests": "core/tests, as set in pyproject.toml [tool.mutmut]",
        "threshold_percent": THRESHOLD_PERCENT,
        "score_rule": SCORE_RULE,
        "modules": {m: dict(modules[m]) for m in MODULES if m in modules},
        # The same counts under a short name with no slash, so the README can cite them: a claim
        # pointer cannot step through a key such as "core/gate.py".
        "by_name": {
            Path(m).stem: {k: modules[m][k] for k in SHORT_KEYS} for m in MODULES if m in modules
        },
        "total": {
            **total,
            "score_percent": round(100.0 * total["killed"] / total["mutants"], 1)
            if total["mutants"]
            else 0.0,
        },
    }


def run_mutmut(root: Path) -> int:
    shutil.rmtree(root / "mutants", ignore_errors=True)
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY",)}
    children = max(1, (os.cpu_count() or 2) - 2)
    proc = subprocess.run(
        [sys.executable, "-m", "mutmut", "run", "--max-children", str(children)],
        cwd=root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        lines = (proc.stderr or "").strip().splitlines()
        print(f"mutmut: {lines[-1] if lines else 'failed with no message'}")
    return proc.returncode


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-run", action="store_true", help="read the last run in mutants/")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--out", type=Path, default=OUT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not args.no_run and run_mutmut(root) != 0:
        print("mutation: mutmut did not finish; nothing written")
        return 1
    modules = read_run(root / "mutants")
    problems = problems_with(modules)
    for module in MODULES:
        c = modules.get(module)
        if c is not None:
            print(
                f"{module}: {c['killed']} of {c['mutants']} changes caught, "
                f"{c['survived']} survived, {c['timeout']} timed out, {c['score_percent']} percent"
            )
    if problems:
        print("\n".join(f"mutation: {p}" for p in problems))
        return 1
    doc = document(modules)
    args.out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"mutation: every module at {THRESHOLD_PERCENT:.0f} percent or more; wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
