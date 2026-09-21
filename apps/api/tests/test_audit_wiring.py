"""A stored record leaves one hash chained audit line, and tests never touch audit/log.jsonl."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from apps.api import core_calls
from apps.api.settings import settings
from core.records import Observer, Spot, VisitRecord


def _visit() -> VisitRecord:
    return VisitRecord(
        visit_id="visit-audit-test-0001",
        spot=Spot(
            spot_id="spot-a",
            spot_name="Spot A",
            reach_id="reach-a",
            reach_name="Reach A",
            creek_id="creek-a",
            creek_name="Creek A",
            latitude=37.87,
            longitude=-122.26,
        ),
        observer=Observer(contributor_token="ct-test-observer-02"),
        answered_at=datetime(2026, 9, 24, 16, 40, tzinfo=UTC),
        answers={"bank_type": "present"},
    )


def test_store_success_appends_record_written(monkeypatch, tmp_path: Path) -> None:
    audit = tmp_path / "audit.jsonl"
    monkeypatch.setattr(settings, "audit_log_path", str(audit))
    import apps.api.fhir_store as store_mod

    monkeypatch.setattr(store_mod, "save_visit_bundle", lambda v, **kw: tmp_path / "v.json")
    assert core_calls.save_visit_bundle(_visit()) == tmp_path / "v.json"
    lines = [json.loads(line) for line in audit.read_text().splitlines()]
    assert len(lines) == 1 and lines[0]["kind"] == "record_written" and lines[0]["seq"] == 1
    assert not Path("audit/log.jsonl").exists() or Path("audit/log.jsonl").stat().st_size == 0


def test_store_failure_appends_nothing(monkeypatch, tmp_path: Path) -> None:
    audit = tmp_path / "audit.jsonl"
    monkeypatch.setattr(settings, "audit_log_path", str(audit))
    import apps.api.fhir_store as store_mod

    def boom(v, **kw):
        raise ValueError("refused")

    monkeypatch.setattr(store_mod, "save_visit_bundle", boom)
    assert core_calls.save_visit_bundle(_visit()) is None
    assert not audit.exists()
