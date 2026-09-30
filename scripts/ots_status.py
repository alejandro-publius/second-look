"""Where each OpenTimestamps proof in proofs/ stands, written to results/ots.json for /verify.

Run: uv run python scripts/ots_status.py              ots upgrade, then read and check each proof
     uv run python scripts/ots_status.py --offline    read the proofs as they are, no network

OpenTimestamps is a public timestamp service, not our own chain. A new proof is pending: the
calendars hold the hash and promise to put it in Bitcoin. `ots upgrade` asks them for the finished
proof, which ends in one Bitcoin block, and saves it in place. This script runs that, then reads
each proof with the same library `ots info` uses and checks four things:

- the proof is for the file it names: the file's SHA-256 is the hash the proof starts from;
- for an audit head proof, the audit log still holds the line it stamped. The proof matches the
  copy of that line in proofs/, and a log rewritten after the stamp, last line included, still
  holds together on its own, so only this comparison notices the rewrite;
- for a finished proof, the block: the header at that height, from the public Blockstream
  explorer, holds the Merkle root the proof arrives at, hashes to the block's id, and carries
  the proof of work its own difficulty asks for. `ots verify` does this with a local Bitcoin
  node, which this Mac does not run, so the header comes from the explorer instead;
- nothing else. The calendars only ever see a hash.

Status per proof: pending (calendars only), confirmed (with the block height and time), unchecked
(a block is named but its header could not be read, for example offline), or broken (the file,
the audit log line or the block does not match). Exit 1 only when a proof is broken.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

import httpx
from opentimestamps.core.notary import BitcoinBlockHeaderAttestation, PendingAttestation
from opentimestamps.core.serialize import StreamDeserializationContext
from opentimestamps.core.timestamp import DetachedTimestampFile

from scripts import audit_log
from scripts.anchor_audit_head import PREFIX, ots_command

ROOT = Path(__file__).resolve().parents[1]
PROOFS = ROOT / "proofs"
OUT = ROOT / "results" / "ots.json"
EXPLORER = "https://blockstream.info/api"
USER_AGENT = "second-look ots_status (github.com/alejandro-publius/second-look)"
# A proof whose stamped file does not sit beside it, minus .ots, names its file here.
TARGETS = {
    "analysis_plan.md.ots": "docs/analysis_plan.md",
    "analysis_plan_v2.md.ots": "docs/analysis_plan_v2.md",
    "analysis_plan_v3.md.ots": "docs/analysis_plan_v3.md",
}
WHAT = {
    "prereg-v1.tag.ots": "prereg_tag",
    "analysis_plan.md.ots": "analysis_plan",
    "prereg-v2.tag.ots": "prereg_tag_v2",
    "analysis_plan_v2.md.ots": "analysis_plan_v2",
    "prereg-v3.tag.ots": "prereg_tag_v3",
    "analysis_plan_v3.md.ots": "analysis_plan_v3",
}

# Returns the 80 byte header of the block at a height, and the id the explorer gave it.
HeaderFetch = Callable[[int], tuple[bytes, str]]
Upgrader = Callable[[Path], None]


class ProofError(Exception):
    """A proof that cannot be read at all."""


def fetch_header(height: int) -> tuple[bytes, str]:
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=20, headers=headers) as client:
        block_id = client.get(f"{EXPLORER}/block-height/{height}").raise_for_status().text.strip()
        raw = client.get(f"{EXPLORER}/block/{block_id}/header").raise_for_status().text.strip()
    return bytes.fromhex(raw), block_id


def ots_upgrade(proof: Path) -> None:
    """ots upgrade saves a finished proof in place and keeps the old one as .bak. It exits 1
    while a proof is still pending, which is not an error here."""
    backup = proof.with_name(proof.name + ".bak")
    subprocess.run(
        [ots_command(), "upgrade", str(proof)], capture_output=True, text=True, timeout=180
    )
    if backup.exists():
        try:
            read_proof(proof)  # the new one reads; only then is the old one let go
        except ProofError:
            backup.replace(proof)
            raise
        backup.unlink()


def read_proof(proof: Path) -> Any:
    try:
        with proof.open("rb") as f:
            return DetachedTimestampFile.deserialize(StreamDeserializationContext(f))
    except Exception as e:  # the library raises its own kinds for every bad byte
        raise ProofError(f"{proof.name} is not a readable OpenTimestamps proof: {e}") from e


def target_of(proof: Path, root: Path = ROOT) -> Path:
    named = TARGETS.get(proof.name)
    return root / named if named else proof.with_suffix("")


def check_header(header: bytes, block_id: str, merkle_root: bytes) -> tuple[str | None, int]:
    """Why the header does not back the proof, or None; and the block's time."""
    if len(header) != 80:
        return f"the header is {len(header)} bytes, not 80", 0
    digest = hashlib.sha256(hashlib.sha256(header).digest()).digest()
    if digest[::-1].hex() != block_id:
        return "the header does not hash to the block id the explorer gave", 0
    bits = int.from_bytes(header[72:76], "little")
    target = (bits & 0xFFFFFF) * 256 ** ((bits >> 24) - 3)
    if int.from_bytes(digest, "little") > target:
        return "the header does not carry the proof of work its difficulty asks for", 0
    if header[36:68] != merkle_root:
        return "the block's Merkle root is not the one the proof arrives at", 0
    return None, int.from_bytes(header[68:72], "little")


def stamped_line_gone(
    stamped: bytes, seq: int, root: Path = ROOT, log: Path | None = None
) -> str | None:
    """Why audit/log.jsonl no longer holds the line an audit head proof stamped, or None.

    The proof is checked against its copy of the line in proofs/, which a rewrite of the log
    leaves alone, and a rewritten log with fresh hashes still walks as a chain. So the stamped
    text is compared with the log's own line at that seq. scripts/verify_audit.py passes the log
    it walks as log."""
    log = log or root / "audit" / "log.jsonl"
    try:
        entries = audit_log.verified_entries(log)
    except audit_log.AuditError as e:
        return f"audit/log.jsonl does not hold together: {e}"
    if len(entries) < seq:
        return f"audit/log.jsonl has no line {seq}, the line this proof stamped"
    if audit_log.hashed_text(entries[seq - 1]).encode("utf-8") != stamped:
        return f"line {seq} of audit/log.jsonl is not the line this proof stamped"
    return None


def status_of(proof: Path, *, root: Path = ROOT, fetch: HeaderFetch | None = fetch_header) -> dict:
    """One proof's row for results/ots.json. fetch=None reads no header (offline)."""
    detached = read_proof(proof)
    target = target_of(proof, root)
    row: dict[str, Any] = {
        "proof": proof.relative_to(root).as_posix(),
        "file": target.relative_to(root).as_posix(),
        "what": WHAT.get(proof.name, "audit_head" if proof.name.startswith(PREFIX) else "other"),
        "file_sha256": detached.file_digest.hex(),
        "calendars": [],
        "bitcoin": None,
        "problem": None,
    }
    if str(detached.file_hash_op) != "sha256":
        how = detached.file_hash_op
        row.update(status="broken", problem=f"the proof hashes its file with {how}, not sha256")
        return row
    if not target.is_file():
        row.update(status="broken", problem=f"{row['file']} is missing")
        return row
    if hashlib.sha256(target.read_bytes()).digest() != detached.file_digest:
        row.update(status="broken", problem=f"{row['file']} is not the file this proof stamped")
        return row
    if row["what"] == "audit_head":  # the text the audit log hashed, which starts with its seq
        row["audit_seq"] = int(target.read_text(encoding="utf-8").split("|", 1)[0])
        gone = stamped_line_gone(target.read_bytes(), row["audit_seq"], root)
        if gone:
            row.update(status="broken", problem=gone)
            return row
    blocks = []
    for msg, attestation in detached.timestamp.all_attestations():
        if isinstance(attestation, PendingAttestation):
            row["calendars"].append(attestation.uri)
        elif isinstance(attestation, BitcoinBlockHeaderAttestation):
            blocks.append((attestation.height, msg))
    row["calendars"].sort()
    if not blocks:
        row["status"] = "pending"
        return row
    height, merkle_root = min(blocks)
    row["bitcoin"] = {"block_height": height, "merkle_root": merkle_root[::-1].hex()}
    if fetch is None:
        row.update(status="unchecked", problem="offline: the block header was not read")
        return row
    try:
        header, block_id = fetch(height)
    except (httpx.HTTPError, ValueError, OSError) as e:
        row.update(status="unchecked", problem=f"the block header could not be read: {e}")
        return row
    problem, block_time = check_header(header, block_id, merkle_root)
    row["bitcoin"]["block_hash"] = block_id
    if problem:
        row.update(status="broken", problem=problem)
        return row
    row["bitcoin"]["block_time_utc"] = datetime.fromtimestamp(block_time, UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    row["bitcoin"]["header_from"] = EXPLORER
    row["status"] = "confirmed"
    return row


def report(
    proofs: Path = PROOFS,
    *,
    root: Path = ROOT,
    upgrade: Upgrader | None = ots_upgrade,
    fetch: HeaderFetch | None = fetch_header,
) -> dict[str, Any]:
    rows = []
    for proof in sorted(proofs.glob("*.ots")):
        try:
            if upgrade is not None:
                upgrade(proof)
            rows.append(status_of(proof, root=root, fetch=fetch))
        except ProofError as e:
            rows.append(
                {"proof": proof.relative_to(root).as_posix(), "status": "broken", "problem": str(e)}
            )
    return {
        "checked_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "service": "OpenTimestamps, a public timestamp service that anchors hashes in Bitcoin",
        "client": f"opentimestamps-client {metadata.version('opentimestamps-client')}",
        "upgraded": upgrade is not None,
        "counts": {
            s: sum(r["status"] == s for r in rows)
            for s in ("pending", "confirmed", "unchecked", "broken")
        },
        "proofs": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="no ots upgrade, no block header")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    doc = report(
        upgrade=None if args.offline else ots_upgrade,
        fetch=None if args.offline else fetch_header,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    for r in doc["proofs"]:
        block = r.get("bitcoin") or {}
        at = f" at block {block['block_height']}" if block.get("block_height") else ""
        why = f": {r['problem']}" if r.get("problem") else ""
        print(f"ots-status: {r['proof']} {r['status']}{at}{why}")
    return 1 if doc["counts"]["broken"] else 0


if __name__ == "__main__":
    sys.exit(main())
