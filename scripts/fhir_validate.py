"""Run the pinned HL7 validator over our emitted FHIR instances (hard rule 11).

Inputs: the emitter's golden files under fhir/golden, every *.json under fhir/build/instances
(written by tests) and the example Bundle SUSHI builds from fhir/fsh. Profiles come from the
guide built at the pinned commit by scripts/fhir_build.sh. Output: results/fhir_validation.json
with error and warning counts per file and whether terminology checks ran. Exit 1 on any error.

Flags: --no-build skips the guide build. --tx <url> uses a terminology server (default n/a,
recorded in the results file, Update 02 section 11.4).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / "fhir" / "tools" / "validator_cli.jar"
IG_RESOURCES = ROOT / "fhir" / "build" / "ig" / "fsh-generated" / "resources"
INSTANCES = ROOT / "fhir" / "build" / "instances"
GOLDEN = ROOT / "fhir" / "golden"
RESULTS = ROOT / "results" / "fhir_validation.json"
LOCK = ROOT / "fhir" / "ig.lock"


def lock_value(key: str, default: str) -> str:
    if not LOCK.exists():
        return default
    for line in LOCK.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return default


def java_cmd() -> str:
    for candidate in (
        os.environ.get("JAVA17_HOME"),
        "/opt/homebrew/opt/openjdk@17",
        "/usr/lib/jvm/temurin-17-jdk-amd64",
    ):
        if candidate and (Path(candidate) / "bin" / "java").exists():
            return str(Path(candidate) / "bin" / "java")
    return shutil.which("java") or "java"


def ensure_jar() -> None:
    if JAR.exists():
        return
    url = lock_value("validator_url", "")
    if not url:
        raise SystemExit("fhir-validate: validator jar missing, no validator_url in fhir/ig.lock")
    JAR.parent.mkdir(parents=True, exist_ok=True)
    print(f"fhir-validate: downloading validator from {url}")
    subprocess.run(["curl", "-sSL", "-o", str(JAR), url], check=True)


def our_files() -> list[Path]:
    files: list[Path] = []
    if IG_RESOURCES.exists():
        files += sorted(IG_RESOURCES.glob("Bundle-sl-*.json"))
    if GOLDEN.exists():
        files += sorted(GOLDEN.glob("*.json"))
    if INSTANCES.exists():
        files += sorted(INSTANCES.glob("*.json"))
    return files


def summarise(outcome: dict) -> tuple[dict[str, dict[str, int]], list[dict[str, str]]]:
    by_file: dict[str, dict[str, int]] = {}
    messages: list[dict[str, str]] = []
    issues = outcome.get("issue", []) if outcome.get("resourceType") == "OperationOutcome" else []
    entries = outcome.get("entry", []) if outcome.get("resourceType") == "Bundle" else []
    outcomes = [e.get("resource", {}) for e in entries] or [outcome]
    for oo in outcomes:
        fname = ""
        for ext in oo.get("extension", []):
            if ext.get("url", "").endswith("operationoutcome-file"):
                fname = Path(ext.get("valueString", "")).name
        empty = {"error": 0, "warning": 0, "information": 0}
        counts = by_file.setdefault(fname or "(single)", empty)
        for issue in oo.get("issue", []) or issues:
            sev = issue.get("severity", "information")
            counts[sev] = counts.get(sev, 0) + 1
            if sev in {"error", "warning"}:
                loc = ", ".join(issue.get("expression", []) or issue.get("location", []))
                text = issue.get("details", {}).get("text", "")
                messages.append(
                    {"file": fname, "severity": sev, "location": loc, "text": text[:300]}
                )
    return by_file, messages


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--tx", default="n/a")
    args = parser.parse_args()
    if not args.no_build:
        subprocess.run(["bash", str(ROOT / "scripts" / "fhir_build.sh")], check=True)
    files = our_files()
    if not files:
        print("fhir-validate: no emitted instances yet, nothing to validate")
        return 0
    ensure_jar()
    outcome_path = ROOT / "fhir" / "build" / "validation_outcome.json"
    cmd = [
        java_cmd(),
        "-Xmx3g",
        "-jar",
        str(JAR),
        *[str(f) for f in files],
        "-version",
        lock_value("fhir_version", "4.0.1"),
        "-ig",
        str(IG_RESOURCES),
        "-tx",
        args.tx,
        "-output",
        str(outcome_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    tail = "\n".join(proc.stdout.splitlines()[-25:])
    outcome = json.loads(outcome_path.read_text(encoding="utf-8")) if outcome_path.exists() else {}
    by_file, messages = summarise(outcome)
    errors = sum(c.get("error", 0) for c in by_file.values())
    warnings = sum(c.get("warning", 0) for c in by_file.values())
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text(
        json.dumps(
            {
                "ran_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                "validator_version": lock_value("validator_version", "unknown"),
                "ig_commit": lock_value("ig_commit", "unknown"),
                "fhir_version": lock_value("fhir_version", "4.0.1"),
                "terminology_checks_ran": args.tx != "n/a",
                "terminology_server": args.tx,
                "files": [str(f.relative_to(ROOT)) for f in files],
                "errors": errors,
                "warnings": warnings,
                "by_file": by_file,
                "messages": messages,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(tail)
    tx_state = "ran" if args.tx != "n/a" else "off"
    print(
        f"fhir-validate: {len(files)} file(s), {errors} error(s), {warnings} warning(s), "
        f"terminology checks {tx_state}; details in results/fhir_validation.json"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
