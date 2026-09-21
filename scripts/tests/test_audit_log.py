"""The audit log catches a tampered line, a missing line and a reordered line."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import audit_log, verify_audit


def _log_with(tmp_path: Path, n: int) -> Path:
    path = tmp_path / "audit" / "log.jsonl"
    for i in range(n):
        audit_log.append("test_only", {"i": i}, path=path, allow_test_kind=True)
    return path


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def test_empty_log_verifies_to_zero(tmp_path: Path) -> None:
    path = tmp_path / "audit" / "log.jsonl"
    assert audit_log.verify(path) == 0
    assert audit_log.last_hash(path) == audit_log.GENESIS


def test_append_links_to_previous_hash(tmp_path: Path) -> None:
    path = _log_with(tmp_path, 3)
    entries = [json.loads(line) for line in _lines(path)]
    assert [e["seq"] for e in entries] == [1, 2, 3]
    assert entries[0]["prev_hash"] == "0" * 64
    assert entries[1]["prev_hash"] == entries[0]["hash"]
    assert entries[2]["prev_hash"] == entries[1]["hash"]
    assert audit_log.verify(path, allow_test_kind=True) == 3
    assert audit_log.last_hash(path) == entries[2]["hash"]


def test_hash_is_sha256_of_the_pipe_joined_fields(tmp_path: Path) -> None:
    import hashlib

    path = _log_with(tmp_path, 1)
    e = json.loads(_lines(path)[0])
    text = f"{e['seq']}|{e['ts_utc']}|{e['kind']}|{e['payload_sha256']}|{e['prev_hash']}"
    assert e["hash"] == hashlib.sha256(text.encode()).hexdigest()


def test_unknown_kind_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "log.jsonl"
    with pytest.raises(audit_log.AuditError, match="unknown audit kind"):
        audit_log.append("blockchain_block", {}, path=path)
    with pytest.raises(audit_log.AuditError):
        audit_log.append("test_only", {}, path=path)  # needs the explicit flag
    assert not path.exists()


def test_real_kinds_are_accepted(tmp_path: Path) -> None:
    path = tmp_path / "log.jsonl"
    for kind in sorted(audit_log.KINDS):
        audit_log.append(kind, {"kind": kind}, path=path)
    assert audit_log.verify(path) == len(audit_log.KINDS)


def test_tampered_line_breaks_the_chain(tmp_path: Path) -> None:
    path = _log_with(tmp_path, 3)
    lines = _lines(path)
    e = json.loads(lines[1])
    e["kind"] = "key_frozen"
    lines[1] = json.dumps(e)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(audit_log.AuditError, match="line 2: hash does not match"):
        audit_log.verify(path, allow_test_kind=True)


def test_tampered_payload_hash_breaks_the_chain(tmp_path: Path) -> None:
    path = _log_with(tmp_path, 2)
    lines = _lines(path)
    e = json.loads(lines[0])
    e["payload_sha256"] = "f" * 64
    lines[0] = json.dumps(e)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(audit_log.AuditError, match="line 1: hash does not match"):
        audit_log.verify(path, allow_test_kind=True)


def test_missing_middle_line_breaks_the_chain(tmp_path: Path) -> None:
    path = _log_with(tmp_path, 3)
    lines = _lines(path)
    del lines[1]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(audit_log.AuditError, match="line 2: seq is 3"):
        audit_log.verify(path, allow_test_kind=True)


def test_reordered_lines_break_the_chain(tmp_path: Path) -> None:
    path = _log_with(tmp_path, 3)
    lines = _lines(path)
    lines[1], lines[2] = lines[2], lines[1]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(audit_log.AuditError, match="line 2: seq is 3"):
        audit_log.verify(path, allow_test_kind=True)


def test_rewritten_seq_still_breaks_on_prev_hash(tmp_path: Path) -> None:
    """Fixing the seq numbers after deleting a line does not help: prev_hash no longer links."""
    path = _log_with(tmp_path, 3)
    lines = _lines(path)
    del lines[1]
    e = json.loads(lines[1])
    e["seq"] = 2
    lines[1] = json.dumps(e)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(audit_log.AuditError, match="line 2"):
        audit_log.verify(path, allow_test_kind=True)


def test_unknown_kind_in_file_breaks_verify(tmp_path: Path) -> None:
    path = _log_with(tmp_path, 1)
    with pytest.raises(audit_log.AuditError, match="unknown kind"):
        audit_log.verify(path)  # test_only kind without the flag


def test_garbage_line_is_reported_with_its_number(tmp_path: Path) -> None:
    path = _log_with(tmp_path, 1)
    with path.open("a", encoding="utf-8") as f:
        f.write("not json\n")
    with pytest.raises(audit_log.AuditError, match="line 2: not JSON"):
        audit_log.verify(path, allow_test_kind=True)


def test_verify_audit_cli_reports_length_and_last_hash(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _log_with(tmp_path, 2)
    assert verify_audit.main(["--path", str(path), "--allow-test-kind"]) == 0
    out = capsys.readouterr().out
    assert "2 entries" in out and audit_log.last_hash(path) in out


def test_verify_audit_cli_exits_1_on_a_break(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _log_with(tmp_path, 2)
    lines = _lines(path)
    lines.reverse()
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert verify_audit.main(["--path", str(path), "--allow-test-kind"]) == 1
    assert "BROKEN" in capsys.readouterr().out


def test_verify_audit_cli_expect_last_catches_a_cut_off_tail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _log_with(tmp_path, 3)
    posted = audit_log.last_hash(path)
    lines = _lines(path)
    path.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
    assert audit_log.verify(path, allow_test_kind=True) == 2  # a cut tail alone is not seen
    args = ["--path", str(path), "--allow-test-kind", "--expect-last", posted]
    assert verify_audit.main(args) == 1
    assert "differs from the posted hash" in capsys.readouterr().out
