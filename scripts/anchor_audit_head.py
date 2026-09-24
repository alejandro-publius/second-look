"""Stamp the audit log's last hash with OpenTimestamps (UPDATE_29 section 3). Once a day.

Run: uv run python scripts/anchor_audit_head.py
     bash scripts/install_anchor_job.sh     runs it daily at 06:00 with launchd

It writes proofs/audit-head-<date>, holding the exact text audit/log.jsonl hashes for its last
entry, so the SHA-256 of that file is the last hash itself. Then `ots stamp` sends that hash, and
nothing else, to the public OpenTimestamps calendars and writes proofs/audit-head-<date>.ots.
Because each entry's hash covers the one before it, one stamp of the last hash covers the whole
log up to that line. Check one with `uv run ots verify proofs/audit-head-<date>.ots`.

It refuses a broken chain, since a stamp would lend it weight. It stamps nothing when the newest
proof already holds the same last hash: an earlier stamp of a hash proves more than a later one.
It stamps once a date; a hash added later that day is stamped by the next day's run. It commits
nothing: the new files wait in proofs/ for the next commit.

The date is UTC, like every stored time. Exit 0 when stamped or when nothing needed stamping.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from scripts import audit_log

ROOT = Path(__file__).resolve().parents[1]
PROOFS = ROOT / "proofs"
PREFIX = "audit-head-"
OTS_MAGIC = b"\x00OpenTimestamps\x00\x00Proof\x00"

Stamper = Callable[[Path], None]


def ots_command() -> str:
    """The ots script uv installed beside this Python, or whatever ots is on the PATH."""
    beside = Path(sys.executable).with_name("ots")
    return str(beside) if beside.exists() else "ots"


def ots_stamp(target: Path) -> None:
    """Stamp one file through the public calendars. Raises when ots fails."""
    subprocess.run([ots_command(), "stamp", str(target)], check=True, timeout=120)


def anchored_hashes(proofs: Path) -> list[tuple[str, str]]:
    """(date, last hash) for every audit head proof there is, oldest date first."""
    out = []
    for proof in sorted(proofs.glob(f"{PREFIX}*.ots")):
        target = proof.with_suffix("")
        if target.is_file():
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            out.append((target.name.removeprefix(PREFIX), digest))
    return out


def anchor(
    log: Path = audit_log.LOG,
    proofs: Path = PROOFS,
    *,
    day: str | None = None,
    stamp: Stamper = ots_stamp,
) -> tuple[str, Path | None]:
    """Stamp the last hash of log into proofs. Returns what happened and the new proof, if any."""
    entries = audit_log.verified_entries(log)
    if not entries:
        raise audit_log.AuditError(f"{log} has no entries, so there is no hash to stamp")
    last = entries[-1]
    text = audit_log.hashed_text(last)
    if hashlib.sha256(text.encode()).hexdigest() != last["hash"]:
        raise audit_log.AuditError("the last entry's text does not hash to its hash")
    day = day or datetime.now(UTC).strftime("%Y-%m-%d")
    done = anchored_hashes(proofs)
    if done and done[-1][1] == last["hash"]:
        return f"last hash unchanged since the proof of {done[-1][0]}, nothing to stamp", None
    target = proofs / f"{PREFIX}{day}"
    proof = target.with_name(target.name + ".ots")
    if proof.exists() or target.exists():
        return f"{target.name} already exists; the next day's run stamps the new hash", None
    proofs.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    try:
        stamp(target)
    except (OSError, subprocess.SubprocessError):
        target.unlink(missing_ok=True)
        raise
    if not proof.is_file() or not proof.read_bytes().startswith(OTS_MAGIC):
        target.unlink(missing_ok=True)
        proof.unlink(missing_ok=True)
        raise RuntimeError(f"ots stamp left no proof at {proof}")
    return f"stamped entry {last['seq']}, hash {last['hash']}", proof


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--log", type=Path, default=audit_log.LOG)
    parser.add_argument("--proofs", type=Path, default=PROOFS)
    args = parser.parse_args(argv)
    try:
        said, proof = anchor(args.log, args.proofs)
    except audit_log.AuditError as e:
        print(f"anchor-audit-head: REFUSED: {e}")
        return 1
    except (OSError, subprocess.SubprocessError, RuntimeError) as e:
        print(f"anchor-audit-head: FAILED: {e}")
        return 1
    if proof is not None:
        said += f", proof {proof.relative_to(ROOT) if proof.is_relative_to(ROOT) else proof}"
    print(f"anchor-audit-head: {said}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
