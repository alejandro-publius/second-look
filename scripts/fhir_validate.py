"""Run the HL7 validator over every emitted resource in fhir/build/instances (hard rule 11).

Phase 0 behaviour: with no instances yet, print that and pass. Later phases fill this in with
the pinned validator, the guide built from fhir/ig-src at the commit in fhir/ig.lock, and a
results file that records whether terminology checks ran.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTANCES = ROOT / "fhir" / "build" / "instances"


def main() -> int:
    files = sorted(INSTANCES.glob("*.json")) if INSTANCES.exists() else []
    if not files:
        print("fhir-validate: no emitted instances yet, nothing to validate")
        return 0
    print(f"fhir-validate: {len(files)} instance(s) found but the validator step is not wired yet")
    return 1


if __name__ == "__main__":
    sys.exit(main())
