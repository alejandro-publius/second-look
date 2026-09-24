"""Walk audit/log.jsonl and fail on any break. Prints the chain length and the last hash.

Run: uv run python scripts/verify_audit.py [--path audit/log.jsonl] [--expect-last <hash>]
--expect-last compares the last hash with the one Alex posted publicly at freeze, which is the
only way to notice lines cut off the end of the file before the first daily anchor.

An empty log fails like a missing one, since it proves nothing. The repository's own log is also
held to its audit head proofs (proofs/audit-head-*, made by scripts/anchor_audit_head.py): each
line one of them stamped must still be in the log, word for word, so a log cut back or rewritten
after a stamp fails here, not only in scripts/ots_status.py. --proofs names another folder of
them, for a log given with --path.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts import audit_log, ots_status
from scripts.anchor_audit_head import PREFIX


def stamped_lines(proofs: Path, log: Path) -> tuple[int, list[str]]:
    """How many audit head proofs are in proofs, and why each whose line is gone fails."""
    copies = sorted(p for p in proofs.glob(f"{PREFIX}*") if p.suffix != ".ots" and p.is_file())
    problems = []
    for copy in copies:
        stamped = copy.read_bytes()
        head = stamped.split(b"|", 1)[0]
        if not head.isdigit():
            problems.append(f"{copy.name}: does not start with the number of the line it stamped")
            continue
        gone = ots_status.stamped_line_gone(stamped, int(head), log=log)
        if gone:
            problems.append(f"{copy.name}: {gone}")
    return len(copies), problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--path", type=Path, default=audit_log.LOG)
    parser.add_argument("--expect-last", default=None, help="hash posted at freeze")
    parser.add_argument("--allow-test-kind", action="store_true", help="tests only")
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="a missing or empty log is fine, before the first entry",
    )
    parser.add_argument(
        "--proofs",
        type=Path,
        default=None,
        help="the audit head proofs the log must still hold; proofs/ for the default log",
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
    if length == 0 and not args.allow_missing:
        print(
            f"audit-log: BROKEN: the log at {args.path} has no entries, so this check proves "
            "nothing. Pass --allow-missing before the first entry is written."
        )
        return 1
    last = audit_log.last_hash(args.path)
    if args.expect_last and args.expect_last != last:
        print(f"audit-log: {length} entries, last hash {last}")
        print(f"audit-log: BROKEN: last hash differs from the posted hash {args.expect_last}")
        return 1
    proofs = args.proofs
    if proofs is None and args.path.resolve() == audit_log.LOG.resolve():
        proofs = ots_status.PROOFS
    stamped = ""
    if proofs is not None:
        count, gone = stamped_lines(proofs, args.path)
        if gone:
            print(f"audit-log: {length} entries, last hash {last}")
            for line in gone:
                print(f"audit-log: BROKEN: {line}")
            return 1
        if count:
            stamped = f", {count} stamped line(s) still in place"
    print(f"audit-log: {length} entries, chain intact{stamped}, last hash {last}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
