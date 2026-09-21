"""Hash-chained audit log (CONTRACTS, "Audit log"). Call it an audit log, never a blockchain.

audit/log.jsonl holds one JSON object per line: seq, ts_utc, kind, payload_sha256, prev_hash, hash.
hash = sha256("{seq}|{ts_utc}|{kind}|{payload_sha256}|{prev_hash}"). First prev_hash: 64 zeros.
Payloads are not stored here; the caller keeps them (for example results/key_hash.json).

What verify() catches: a changed field, a removed or added line in the middle, a reordered line.
What it cannot catch: cutting lines off the end. That is why the README prints the last hash at
freeze and Alex posts it publicly; scripts/verify_audit.py --expect-last compares against it.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "audit" / "log.jsonl"
GENESIS = "0" * 64
KINDS = frozenset(
    {
        "plan_tagged",
        "key_frozen",
        "launch_wipe",
        "model_pass_table",
        "data_lock",
        "record_written",
        "sandbox_push",
    }
)
TEST_KIND = "test_only"
FIELDS = ("seq", "ts_utc", "kind", "payload_sha256", "prev_hash", "hash")


class AuditError(Exception):
    """A break in the chain, or a misuse of the module. The message says which line."""


def _hash(seq: int, ts_utc: str, kind: str, payload_sha256: str, prev_hash: str) -> str:
    text = f"{seq}|{ts_utc}|{kind}|{payload_sha256}|{prev_hash}"
    return hashlib.sha256(text.encode()).hexdigest()


def _entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            raise AuditError(f"line {n}: not JSON ({e.msg})") from None
        if not isinstance(entry, dict) or any(k not in entry for k in FIELDS):
            raise AuditError(f"line {n}: missing one of {FIELDS}")
        out.append(entry)
    return out


def append(
    kind: str, payload: dict[str, Any], *, path: Path = LOG, allow_test_kind: bool = False
) -> str:
    """Append one entry and return its hash. Unknown kinds are refused."""
    if kind not in KINDS and not (allow_test_kind and kind == TEST_KIND):
        raise AuditError(f"unknown audit kind {kind!r}; allowed: {sorted(KINDS)}")
    entries = _entries(path)
    prev = entries[-1]["hash"] if entries else GENESIS
    seq = len(entries) + 1
    ts_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload_sha256 = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    digest = _hash(seq, ts_utc, kind, payload_sha256, prev)
    entry = {
        "seq": seq,
        "ts_utc": ts_utc,
        "kind": kind,
        "payload_sha256": payload_sha256,
        "prev_hash": prev,
        "hash": digest,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, separators=(",", ":")) + "\n")
    return digest


def verify(path: Path = LOG, *, allow_test_kind: bool = False) -> int:
    """Walk the chain. Returns its length. Raises AuditError on the first break."""
    prev = GENESIS
    entries = _entries(path)
    for n, e in enumerate(entries, 1):
        if e["seq"] != n:
            raise AuditError(f"line {n}: seq is {e['seq']}, expected {n} (missing or reordered)")
        if e["kind"] not in KINDS and not (allow_test_kind and e["kind"] == TEST_KIND):
            raise AuditError(f"line {n}: unknown kind {e['kind']!r}")
        if e["prev_hash"] != prev:
            raise AuditError(f"line {n}: prev_hash does not match the hash of line {n - 1}")
        expected = _hash(e["seq"], e["ts_utc"], e["kind"], e["payload_sha256"], e["prev_hash"])
        if e["hash"] != expected:
            raise AuditError(f"line {n}: hash does not match its fields (tampered line)")
        prev = e["hash"]
    return len(entries)


def last_hash(path: Path = LOG) -> str:
    """The hash of the last entry, or the 64 zero genesis when the log is empty."""
    entries = _entries(path)
    return str(entries[-1]["hash"]) if entries else GENESIS
