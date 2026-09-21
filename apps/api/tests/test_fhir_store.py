"""The FHIR store: write, index, read back, and refuse a broken Bundle."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from apps.api import fhir_store
from core.fhir_emit import FhirEmitError
from core.records import FEATURES, FeatureScore, Observer, Spot, VisitRecord


def make_visit(visit_id: str = "visit-0001", spot_id: str = "spot-1") -> VisitRecord:
    scores = tuple(
        FeatureScore(feature=f, correct=c, tested_on=date(2026, 9, 23))
        for f, c in zip(FEATURES, (4, 2, 3, 4), strict=True)
    )
    return VisitRecord(
        visit_id=visit_id,
        spot=Spot(
            spot_id=spot_id,
            spot_name="Strawberry Creek, campus reach, spot 1",
            reach_id="campus-reach",
            reach_name="Strawberry Creek, campus reach",
            creek_id="strawberry-creek",
            creek_name="Strawberry Creek",
            latitude=37.8719,
            longitude=-122.2585,
            coarse=False,
        ),
        observer=Observer(contributor_token="ct_7f3a9c2e", scores=scores),
        answered_at=datetime(2026, 9, 24, 16, 40, tzinfo=UTC),
        answers={"bank_type": "present", "draining_pipes": "cant_tell", "water_height_m": 0.2},
    )


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("FHIR_STORE_DIR", str(tmp_path / "fhir_store"))
    return tmp_path / "fhir_store"


def test_save_writes_bundle_and_index(store: Path) -> None:
    path = fhir_store.save_visit_bundle(make_visit())
    assert path == store / "visit-0001.json"
    bundle = json.loads(path.read_text(encoding="utf-8"))
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    index = json.loads((store / "index.json").read_text(encoding="utf-8"))
    assert index == {"spots": {"spot-1": ["visit-0001"]}, "latest": "visit-0001"}
    assert fhir_store.load_visit_bundle("visit-0001") == bundle
    assert fhir_store.latest_visit_id_for_spot("spot-1") == "visit-0001"
    assert fhir_store.latest_visit_id() == "visit-0001"


def test_latest_visit_per_spot_follows_write_order(store: Path) -> None:
    fhir_store.save_visit_bundle(make_visit("v1", "spot-a"))
    fhir_store.save_visit_bundle(make_visit("v2", "spot-b"))
    fhir_store.save_visit_bundle(make_visit("v3", "spot-a"))
    assert fhir_store.latest_visit_id_for_spot("spot-a") == "v3"
    assert fhir_store.latest_visit_id_for_spot("spot-b") == "v2"
    assert fhir_store.latest_visit_id() == "v3"
    assert [p.name for p in fhir_store.stored_bundle_paths()] == ["v1.json", "v2.json", "v3.json"]


def test_saving_the_same_visit_twice_keeps_one_index_entry(store: Path) -> None:
    fhir_store.save_visit_bundle(make_visit())
    fhir_store.save_visit_bundle(make_visit())
    assert fhir_store.load_index()["spots"]["spot-1"] == ["visit-0001"]


def test_missing_visit_is_none(store: Path) -> None:
    assert fhir_store.load_visit_bundle("nope") is None
    assert fhir_store.latest_visit_id_for_spot("nope") is None
    assert fhir_store.latest_visit_id() is None
    assert fhir_store.stored_bundle_paths() == []


def test_visit_id_with_unsafe_characters_gets_a_safe_file_name(store: Path) -> None:
    path = fhir_store.save_visit_bundle(make_visit("visit_with/slash"))
    assert path.parent == store
    assert "/" not in path.name and "_" not in path.name
    assert fhir_store.load_visit_bundle("visit_with/slash") is not None


def test_broken_bundle_is_refused(store: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_emit(*args: object, **kwargs: object) -> dict:
        return {"resourceType": "Bundle", "type": "collection", "entry": []}

    monkeypatch.setattr(fhir_store, "emit_visit", broken_emit)
    with pytest.raises(FhirEmitError):
        fhir_store.save_visit_bundle(make_visit())
    assert not (store / "visit-0001.json").exists()


def test_corrupt_file_reads_as_none(store: Path) -> None:
    store.mkdir(parents=True)
    (store / "bad.json").write_text("{not json", encoding="utf-8")
    assert fhir_store.load_visit_bundle("bad") is None
