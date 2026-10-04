"""The dated cleanup preserves an export and can delete only raw part 2 rows."""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from scripts import cleanup_part2 as cleanup
from scripts import mac_jobs


def database() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript((cleanup.ROOT / "worker/schema.sql").read_text())
    db.execute("INSERT INTO part2_counter VALUES ('trained', 7)")
    db.execute("INSERT INTO counter VALUES (1, 9)")
    db.execute("INSERT INTO part2_slot VALUES ('trained', 0, 'assisted', 1)")
    db.execute("INSERT INTO arm_slot VALUES (0, 'trained', 1)")
    db.execute(
        "INSERT INTO part2_session (id,session_id,part1_arm,arm,offered_at,client_token_hash) "
        "VALUES ('original-p2','original-first','trained','assisted',"
        "'2026-10-01T12:00:00Z','browser-hash')"
    )
    db.execute(
        "INSERT INTO part2_response (part2_id,item_id,position,first_answer,question_shown,"
        "received_at) VALUES ('original-p2','p2-photo',0,'yes',1,'2026-10-01T12:00:02Z')"
    )
    return db


def test_cleanup_deletes_only_part2_raw_rows_after_saving_a_deidentified_export(
    tmp_path: Path,
) -> None:
    db = database()
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    protected = {
        t: list(db.execute(f'SELECT * FROM "{t}"'))
        for t in tables
        if t not in {"part2_response", "part2_session"}
    }
    calls = []

    def query(sql: str) -> list[dict[str, Any]]:
        calls.append(sql)
        if sql == cleanup.DELETE_SQL:
            # The actual delete runs only after both export files exist and contain the rows.
            files = list(tmp_path.glob("export-*/*.csv"))
            assert len(files) == 2
            assert all(len(list(csv.DictReader(p.open()))) == 1 for p in files)
            db.executescript(sql)
            return []
        return [dict(r) for r in db.execute(sql)]

    assert "cleared" in cleanup.cleanup(cleanup.DELETE_AT, query, tmp_path)
    for table, rows in protected.items():
        assert list(db.execute(f'SELECT * FROM "{table}"')) == rows, table
    for table in ("part2_session", "part2_response"):
        assert db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] == 0
    assert [s for s in calls if s.startswith("DELETE")] == [
        "DELETE FROM part2_response; DELETE FROM part2_session;"
    ]
    for file in tmp_path.glob("export-*/*.csv"):
        assert file.stat().st_mode & 0o777 == 0o600
        text = file.read_text()
        assert "browser-hash" not in text and "client_token_hash" not in text
        assert "original-p2" not in text and "original-first" not in text
        assert "p2-1" in text
    receipt = json.loads((tmp_path / "completed.json").read_text())
    assert receipt["sessions_exported"] == receipt["responses_exported"] == 1
    before = len(calls)
    assert "already completed" in cleanup.cleanup(
        cleanup.DELETE_AT + timedelta(days=366), query, tmp_path
    )
    assert len(calls) == before


def test_before_the_date_neither_reads_nor_deletes(tmp_path: Path) -> None:
    def forbidden(sql: str) -> list[dict[str, Any]]:
        pytest.fail(f"an early call reached D1: {sql}")

    assert "not due" in cleanup.cleanup(
        cleanup.DELETE_AT - timedelta(seconds=1), forbidden, tmp_path
    )
    assert list(tmp_path.iterdir()) == []


def test_an_export_failure_sends_no_delete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def query(sql: str) -> list[dict[str, Any]]:
        calls.append(sql)
        return []

    def broken_save(path: Path, text: str) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(cleanup, "save", broken_save)
    with pytest.raises(OSError, match="disk full"):
        cleanup.cleanup(cleanup.DELETE_AT, query, tmp_path)
    assert not any(s.startswith("DELETE") for s in calls)
    assert not (tmp_path / "completed.json").exists()


def test_remaining_rows_never_get_a_completion_receipt(tmp_path: Path) -> None:
    def query(sql: str) -> list[dict[str, Any]]:
        return [{"n": 1}, {"n": 0}] if "COUNT" in sql else []

    with pytest.raises(RuntimeError, match="rows remain"):
        cleanup.cleanup(cleanup.DELETE_AT, query, tmp_path)
    assert not (tmp_path / "completed.json").exists()


def test_job_is_november_30_pacific_and_uses_only_the_cleanup_script() -> None:
    job = next(
        j for j in mac_jobs.jobs(ZoneInfo("America/Los_Angeles")) if j.name == "part2_retention"
    )
    assert job.calendar == {"Month": 11, "Day": 30, "Hour": 9, "Minute": 0}
    assert job.command == ("uv", "run", "python", "scripts/cleanup_part2.py", "--execute")
    assert not job.writes and not job.audit_kinds
