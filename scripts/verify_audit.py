"""Walk audit/log.jsonl and fail on any break. Prints the chain length and the last hash.

Run: uv run python scripts/verify_audit.py [--path audit/log.jsonl] [--expect-last <hash>]
--expect-last compares the last hash with the one Alex posted publicly at freeze, which is the
only way to notice lines cut off the end of the file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts import audit_log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--path", type=Path, default=audit_log.LOG)
    parser.add_argument("--expect-last", default=None, help="hash posted at freeze")
    parser.add_argument("--allow-test-kind", action="store_true", help="tests only")
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="a missing log is fine, before the first entry",
    )
    args = parser.parse_args(argv)
    if not args.path.exists() and not args.allow_missing:
        print(
            f"audit-log: BROKEN: no log at {args.path}. Nothing has been recorded, so this check "
            "proves nothing. Pass --allow-missing before the first entry is written."
        )
        return 1
    try:
        length = audit_log.verify(args.path, allow_test_kind=args.allow_test_kind)
    except audit_log.AuditError as e:
        print(f"audit-log: BROKEN: {e}")
        return 1
    last = audit_log.last_hash(args.path)
    if args.expect_last and args.expect_last != last:
        print(f"audit-log: {length} entries, last hash {last}")
        print(f"audit-log: BROKEN: last hash differs from the posted hash {args.expect_last}")
        return 1
    print(f"audit-log: {length} entries, chain intact, last hash {last}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
