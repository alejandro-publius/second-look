"""The OpenTimestamps scripts: the daily audit head anchor, its launchd job, and the status file.

No test here reaches a calendar or an explorer. Stamping is a fake that writes a real proof with
the library, and block headers are made here with a proof of work easy enough to find at once,
except one real header (block 800000) that checks the proof of work rule on a real block.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from opentimestamps.core.notary import BitcoinBlockHeaderAttestation, PendingAttestation
from opentimestamps.core.op import OpAppend, OpSHA256
from opentimestamps.core.serialize import StreamSerializationContext
from opentimestamps.core.timestamp import DetachedTimestampFile, Timestamp

from scripts import anchor_audit_head, audit_log, ots_status

ROOT = Path(__file__).resolve().parents[2]
CALENDAR = "https://alice.btc.calendar.opentimestamps.org"
# Bitcoin block 800000, read from the public explorer once: a real header with real work in it.
BLOCK_800000 = bytes.fromhex(
    "00601d3455bb9fbd966b3ea2dc42d0c22722e4c0c1729fad17210100000000000000000055087fab0c8f3f89"
    "f8bcfd4df26c504d81b0a88e04907161838c0c53001af09135edbd64943805175e955e06"
)
BLOCK_800000_ID = "00000000000000000002a7c4c1e48d76c5a37902165a270156b7a8d72728a054"
EASY_BITS = 0x207FFFFF  # the easiest target Bitcoin's rules can express


# --- helpers ------------------------------------------------------------------------------------


def write_proof(target: Path, proof: Path, *, block: int | None = None) -> bytes:
    """A proof for target like ots stamp writes, pending at one calendar, and when block is given
    also finished in that block. Returns the message the block's Merkle root must equal."""
    stamp = Timestamp(hashlib.sha256(target.read_bytes()).digest())
    nonce = stamp.ops.add(OpAppend(b"\x01" * 16))
    tip = nonce.ops.add(OpSHA256())
    tip.attestations.add(PendingAttestation(CALENDAR))
    if block is not None:
        tip.attestations.add(BitcoinBlockHeaderAttestation(block))
    buf = io.BytesIO()
    DetachedTimestampFile(OpSHA256(), stamp).serialize(StreamSerializationContext(buf))
    proof.write_bytes(buf.getvalue())
    return tip.msg


def header_for(merkle_root: bytes, *, when: int = 1790200000) -> tuple[bytes, str]:
    """An 80 byte header holding merkle_root, with just enough work for EASY_BITS."""
    target = (EASY_BITS & 0xFFFFFF) * 256 ** ((EASY_BITS >> 24) - 3)
    base = (
        (4).to_bytes(4, "little")
        + bytes(32)
        + merkle_root
        + when.to_bytes(4, "little")
        + EASY_BITS.to_bytes(4, "little")
    )
    for nonce in range(1 << 16):
        header = base + nonce.to_bytes(4, "little")
        digest = hashlib.sha256(hashlib.sha256(header).digest()).digest()
        if int.from_bytes(digest, "little") <= target:
            return header, digest[::-1].hex()
    raise AssertionError("no nonce found")


def fake_stamp(target: Path) -> None:
    write_proof(target, target.with_name(target.name + ".ots"))


def chain(tmp_path: Path, n: int) -> Path:
    log = tmp_path / "audit" / "log.jsonl"
    for i in range(n):
        audit_log.append("key_frozen", {"i": i}, path=log)
    return log


# --- anchor_audit_head ---------------------------------------------------------------------------


def test_the_stamped_file_hashes_to_the_last_hash_of_the_log(tmp_path: Path) -> None:
    log, proofs = chain(tmp_path, 3), tmp_path / "proofs"
    said, proof = anchor_audit_head.anchor(log, proofs, day="2026-09-24", stamp=fake_stamp)
    assert proof == proofs / "audit-head-2026-09-24.ots"
    assert proof.read_bytes().startswith(anchor_audit_head.OTS_MAGIC)
    stamped = (proofs / "audit-head-2026-09-24").read_bytes()
    assert hashlib.sha256(stamped).hexdigest() == audit_log.last_hash(log)
    assert stamped.decode().startswith("3|")
    assert "entry 3" in said


def test_the_real_log_head_text_hashes_to_its_hash() -> None:
    last = audit_log.verified_entries(audit_log.LOG)[-1]
    text = audit_log.hashed_text(last)
    assert hashlib.sha256(text.encode()).hexdigest() == last["hash"]


def test_an_unchanged_head_is_not_stamped_again(tmp_path: Path) -> None:
    log, proofs = chain(tmp_path, 2), tmp_path / "proofs"
    anchor_audit_head.anchor(log, proofs, day="2026-09-24", stamp=fake_stamp)
    said, proof = anchor_audit_head.anchor(log, proofs, day="2026-09-25", stamp=fake_stamp)
    assert proof is None and "unchanged" in said
    assert sorted(p.name for p in proofs.glob("*.ots")) == ["audit-head-2026-09-24.ots"]


def test_a_new_head_is_stamped_the_next_day_not_twice_the_same_day(tmp_path: Path) -> None:
    log, proofs = chain(tmp_path, 2), tmp_path / "proofs"
    anchor_audit_head.anchor(log, proofs, day="2026-09-24", stamp=fake_stamp)
    audit_log.append("data_lock", {"n": 1}, path=log)
    said, proof = anchor_audit_head.anchor(log, proofs, day="2026-09-24", stamp=fake_stamp)
    assert proof is None and "already exists" in said
    _, proof = anchor_audit_head.anchor(log, proofs, day="2026-09-25", stamp=fake_stamp)
    assert proof == proofs / "audit-head-2026-09-25.ots"
    assert (proofs / "audit-head-2026-09-25").read_text().startswith("3|")


def test_a_broken_chain_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    log, proofs = chain(tmp_path, 3), tmp_path / "proofs"
    lines = log.read_text().splitlines()
    lines[1] = lines[1].replace('"key_frozen"', '"data_lock"')
    log.write_text("\n".join(lines) + "\n")
    with pytest.raises(audit_log.AuditError):
        anchor_audit_head.anchor(log, proofs, day="2026-09-24", stamp=fake_stamp)
    assert not proofs.exists()
    assert anchor_audit_head.main(["--log", str(log), "--proofs", str(proofs)]) == 1


def test_an_empty_log_has_nothing_to_stamp(tmp_path: Path) -> None:
    with pytest.raises(audit_log.AuditError, match="no entries"):
        anchor_audit_head.anchor(tmp_path / "none.jsonl", tmp_path / "p", stamp=fake_stamp)


def test_a_failed_stamp_leaves_no_half_proof(tmp_path: Path) -> None:
    log, proofs = chain(tmp_path, 1), tmp_path / "proofs"

    def silent(target: Path) -> None:
        return None  # ots ran and wrote nothing

    with pytest.raises(RuntimeError, match="no proof"):
        anchor_audit_head.anchor(log, proofs, day="2026-09-24", stamp=silent)
    assert list(proofs.iterdir()) == []


# --- install_anchor_job.sh -----------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("plutil") is None, reason="plutil is macOS only")
def test_the_job_runs_the_anchor_then_the_status_daily(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "launchctl.calls"
    (fake_bin / "launchctl").write_text(f'#!/bin/sh\necho "$@" >> {calls}\n')
    (fake_bin / "uv").write_text("#!/bin/sh\nexit 0\n")
    for f in fake_bin.iterdir():
        f.chmod(0o755)
    env = {**os.environ, "HOME": str(tmp_path), "PATH": f"{fake_bin}:/usr/bin:/bin"}
    subprocess.run(
        ["bash", str(ROOT / "scripts" / "install_anchor_job.sh")],
        env=env,
        check=True,
        capture_output=True,
    )
    plist = tmp_path / "Library" / "LaunchAgents" / "com.secondlook.anchor.plist"
    job = plistlib.loads(plist.read_bytes())
    command = job["ProgramArguments"][-1]
    assert command.index("anchor_audit_head.py") < command.index("ots_status.py")
    assert job["StartCalendarInterval"] == {"Hour": 6, "Minute": 0}
    assert job["WorkingDirectory"] == str(ROOT)
    assert "bootstrap" in calls.read_text()


# --- ots_status ----------------------------------------------------------------------------------


def repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    (root / "proofs").mkdir(parents=True)
    (root / "docs").mkdir()
    return root, root / "proofs"


def test_a_new_proof_is_pending_with_its_calendars(tmp_path: Path) -> None:
    root, proofs = repo(tmp_path)
    (proofs / "prereg-v1.tag").write_bytes(b"object abc\n")
    write_proof(proofs / "prereg-v1.tag", proofs / "prereg-v1.tag.ots")
    row = ots_status.status_of(proofs / "prereg-v1.tag.ots", root=root, fetch=None)
    assert row["status"] == "pending"
    assert row["calendars"] == [CALENDAR]
    assert row["bitcoin"] is None
    assert row["what"] == "prereg_tag"


def test_the_plan_proof_is_checked_against_the_plan_in_docs(tmp_path: Path) -> None:
    root, proofs = repo(tmp_path)
    plan = root / "docs" / "analysis_plan.md"
    plan.write_text("the plan\n")
    write_proof(plan, proofs / "analysis_plan.md.ots")
    row = ots_status.status_of(proofs / "analysis_plan.md.ots", root=root, fetch=None)
    assert (row["file"], row["status"]) == ("docs/analysis_plan.md", "pending")
    plan.write_text("the plan, changed after the stamp\n")
    row = ots_status.status_of(proofs / "analysis_plan.md.ots", root=root, fetch=None)
    assert row["status"] == "broken" and "not the file" in row["problem"]


def test_a_finished_proof_is_confirmed_with_its_block_height_and_time(tmp_path: Path) -> None:
    root, proofs = repo(tmp_path)
    (proofs / "audit-head-2026-09-24").write_text("3|t|plan_tagged|p|h")
    root_msg = write_proof(
        proofs / "audit-head-2026-09-24", proofs / "audit-head-2026-09-24.ots", block=915000
    )
    header, block_id = header_for(root_msg)
    asked: list[int] = []

    def fetch(height: int) -> tuple[bytes, str]:
        asked.append(height)
        return header, block_id

    row = ots_status.status_of(proofs / "audit-head-2026-09-24.ots", root=root, fetch=fetch)
    assert row["status"] == "confirmed", row["problem"]
    assert asked == [915000]
    assert row["bitcoin"]["block_height"] == 915000
    assert row["bitcoin"]["block_hash"] == block_id
    assert row["bitcoin"]["block_time_utc"] == "2026-09-23T21:46:40Z"
    assert row["what"] == "audit_head" and row["audit_seq"] == 3


def test_a_block_whose_merkle_root_differs_is_broken(tmp_path: Path) -> None:
    root, proofs = repo(tmp_path)
    (proofs / "x").write_text("x")
    write_proof(proofs / "x", proofs / "x.ots", block=915000)
    header, block_id = header_for(bytes(32))
    row = ots_status.status_of(proofs / "x.ots", root=root, fetch=lambda h: (header, block_id))
    assert row["status"] == "broken" and "Merkle root" in row["problem"]


def test_an_unreadable_header_leaves_the_proof_unchecked(tmp_path: Path) -> None:
    root, proofs = repo(tmp_path)
    (proofs / "x").write_text("x")
    write_proof(proofs / "x", proofs / "x.ots", block=915000)

    def down(height: int) -> tuple[bytes, str]:
        raise httpx.ConnectError("no network")

    row = ots_status.status_of(proofs / "x.ots", root=root, fetch=down)
    assert row["status"] == "unchecked"
    offline = ots_status.status_of(proofs / "x.ots", root=root, fetch=None)
    assert offline["status"] == "unchecked" and offline["bitcoin"]["block_height"] == 915000


def test_the_header_check_on_a_real_block() -> None:
    merkle = BLOCK_800000[36:68]
    assert ots_status.check_header(BLOCK_800000, BLOCK_800000_ID, merkle) == (None, 1690168629)
    wrong_id = "00" * 32
    assert "block id" in (ots_status.check_header(BLOCK_800000, wrong_id, merkle)[0] or "")
    assert "80" in (ots_status.check_header(BLOCK_800000[:79], BLOCK_800000_ID, merkle)[0] or "")


def test_a_header_without_its_proof_of_work_is_refused() -> None:
    # Block 800000's header claiming a target of 1, which no hash meets. Its id is its own hash,
    # so only the proof of work rule can refuse it.
    hard = BLOCK_800000[:72] + (0x03000001).to_bytes(4, "little") + BLOCK_800000[76:]
    digest = hashlib.sha256(hashlib.sha256(hard).digest()).digest()[::-1].hex()
    problem, _ = ots_status.check_header(hard, digest, hard[36:68])
    assert problem is not None and "proof of work" in problem


def fake_ots(tmp_path: Path, new_bytes: bytes) -> Path:
    """An ots that upgrades the way the real one does: old proof to .bak, new proof in place."""
    new = tmp_path / "upgraded.bin"
    new.write_bytes(new_bytes)
    script = tmp_path / "ots"
    script.write_text(f'#!/bin/sh\nmv "$2" "$2.bak"\ncp {new} "$2"\nexit 1\n')
    script.chmod(0o755)
    return script


def test_an_upgrade_that_reads_replaces_the_proof_and_drops_the_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, proofs = repo(tmp_path)
    (proofs / "x").write_text("x")
    write_proof(proofs / "x", proofs / "finished.ots", block=915000)
    write_proof(proofs / "x", proofs / "x.ots")
    finished = (proofs / "finished.ots").read_bytes()
    (proofs / "finished.ots").unlink()
    monkeypatch.setattr(ots_status, "ots_command", lambda: str(fake_ots(tmp_path, finished)))
    ots_status.ots_upgrade(proofs / "x.ots")
    assert (proofs / "x.ots").read_bytes() == finished
    assert not (proofs / "x.ots.bak").exists()


def test_an_upgrade_that_does_not_read_puts_the_old_proof_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, proofs = repo(tmp_path)
    (proofs / "x").write_text("x")
    write_proof(proofs / "x", proofs / "x.ots")
    before = (proofs / "x.ots").read_bytes()
    monkeypatch.setattr(ots_status, "ots_command", lambda: str(fake_ots(tmp_path, b"junk")))
    doc = ots_status.report(proofs, root=root, upgrade=ots_status.ots_upgrade, fetch=None)
    assert (proofs / "x.ots").read_bytes() == before
    assert not (proofs / "x.ots.bak").exists()
    assert doc["counts"]["broken"] == 1


def test_an_unreadable_proof_is_reported_broken_not_skipped(tmp_path: Path) -> None:
    root, proofs = repo(tmp_path)
    (proofs / "junk.ots").write_bytes(b"not a proof")
    doc = ots_status.report(proofs, root=root, upgrade=None, fetch=None)
    assert doc["counts"]["broken"] == 1
    assert doc["proofs"][0]["status"] == "broken"


def test_the_committed_status_file_names_every_committed_proof() -> None:
    doc = json.loads((ROOT / "results" / "ots.json").read_text())
    named = {r["proof"] for r in doc["proofs"]}
    on_disk = {p.relative_to(ROOT).as_posix() for p in (ROOT / "proofs").glob("*.ots")}
    assert named == on_disk
    assert all(r["status"] in {"pending", "confirmed", "unchecked"} for r in doc["proofs"])
    assert "public timestamp service" in doc["service"]


def test_the_committed_proofs_are_for_the_files_they_name() -> None:
    doc = ots_status.report(ROOT / "proofs", root=ROOT, upgrade=None, fetch=None)
    assert doc["counts"]["broken"] == 0, doc["proofs"]
    tag = subprocess.run(
        ["git", "cat-file", "tag", "prereg-v1"], cwd=ROOT, capture_output=True, check=False
    )
    if tag.returncode == 0:  # a shallow clone may not carry the tag
        assert tag.stdout == (ROOT / "proofs" / "prereg-v1.tag").read_bytes()


def test_the_status_command_runs_offline(tmp_path: Path) -> None:
    out = tmp_path / "ots.json"
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.ots_status", "--offline", "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(out.read_text())["upgraded"] is False
