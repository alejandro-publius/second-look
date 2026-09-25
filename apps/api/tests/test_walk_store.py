"""A finished video walk's demo record (UPDATE_30 section 1 item 3): stored in its own table,
read back by its id, never counted, never mirrored, and guarded by a size cap, a daily cap, the
form's own values and a delete date."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func
from sqlmodel import Session, select

from apps.api import content, walk_store
from apps.api.db import engine
from apps.api.fhir_store import store_dir, stored_bundle_paths
from apps.api.models import SpotRow, VisitRow, WalkRecordRow
from apps.api.tests.conftest import freeze_now
from core.walks import (
    DEMO_TAG_CODE,
    WALK_DAILY_CAP,
    WALK_KEEP_DAYS,
    WALK_MAX_BYTES,
    is_demo,
    walk_bundle,
    walk_visit_id,
)
from scripts import repush_sandbox

NOW = datetime(2026, 9, 25, 10, 0, 0, tzinfo=UTC)
AT = "2026-09-25T09:58:30.250Z"
ANSWERS = {
    "bank_type": "present",
    "draining_pipes": "present",
    "water_height_m": 0.5,
    "habitats": ["riffles"],
    "feelings": ["joy:3", "fear:not_applicable"],
}


def walk_id() -> str:
    return content.walks()[0]["id"]


def body(**over: object) -> dict[str, object]:
    return {"walk_id": walk_id(), "answers": ANSWERS, "answered_at": AT, **over}


def rows() -> int:
    with Session(engine) as db:
        return int(db.exec(select(func.count()).select_from(WalkRecordRow)).one())


def test_a_finished_walk_is_stored_and_read_back_by_its_id(client) -> None:
    freeze_now(NOW)
    stored = client.post("/api/walk", json=body())
    assert stored.status_code == 200, stored.text
    at = datetime(2026, 9, 25, 9, 58, 30, tzinfo=UTC)
    record_id = walk_visit_id(walk_id(), at)
    assert stored.json() == {
        "record_id": record_id,
        "walk_id": walk_id(),
        "answered_at": "2026-09-25T09:58:30Z",
        "delete_after": "2026-10-25T10:00:00Z",
    }
    read = client.get(f"/api/walk/{record_id}")
    assert read.status_code == 200, read.text
    record = read.json()
    assert record["answers"] == ANSWERS
    # The record the phone built from the same answers, tagged as a demo on every resource.
    walk = content.walk_by_id(walk_id())
    assert walk is not None
    assert record["bundle"] == walk_bundle(walk, ANSWERS, at)
    assert is_demo(record["bundle"])
    for entry in record["bundle"]["entry"]:
        codes = [t["code"] for t in entry["resource"]["meta"]["tag"]]
        assert DEMO_TAG_CODE in codes, entry["resource"]["resourceType"]


def test_the_same_walk_sent_twice_is_one_record_and_other_answers_in_its_second_are_refused(
    client,
) -> None:
    freeze_now(NOW)
    first = client.post("/api/walk", json=body()).json()
    again = client.post("/api/walk", json=body())
    assert again.status_code == 200 and again.json() == first
    assert rows() == 1
    other = client.post("/api/walk", json=body(answers={"bank_type": "absent"}))
    assert other.status_code == 409
    assert "same second" in other.json()["detail"]
    assert rows() == 1


def test_a_walk_record_is_never_counted_never_a_creek_and_never_mirrored(client, tmp_path) -> None:
    freeze_now(NOW)
    counts = client.get("/api/test/counts").json()
    creeks = client.get("/api/creeks").json()
    two = client.get("/api/two").json()
    stored = client.post("/api/walk", json=body())
    assert stored.status_code == 200
    # Not in the study counts, not a creek of its own, not the latest record /two shows.
    assert client.get("/api/test/counts").json() == counts
    assert client.get("/api/creeks").json() == creeks
    assert client.get("/api/two").json()["ours_example"] == two["ours_example"] is True
    assert client.get(f"/api/city/walk-{walk_id()}").status_code == 404
    # Not a spot, not a visit, not a file in the FHIR store the sandbox mirror reads.
    with Session(engine) as db:
        assert db.exec(select(SpotRow)).all() == []
        assert db.exec(select(VisitRow)).all() == []
    assert stored_bundle_paths() == []
    assert repush_sandbox.load_bundles(store_dir()) == []
    # And a copy of it put in that folder by hand is still refused by the mirror.
    bundle = client.get(f"/api/walk/{stored.json()['record_id']}").json()["bundle"]
    folder = Path(tmp_path) / "store"
    folder.mkdir()
    (folder / "walk.json").write_text(json.dumps(bundle), encoding="utf-8")
    assert repush_sandbox.load_bundles(folder) == []


@pytest.mark.parametrize(
    ("payload", "status", "detail"),
    [
        (body(walk_id="v99"), 404, "We do not know that walk."),
        (body(extra="a note"), 422, "A walk has no field called 'extra'."),
        (body(answers={"bank_type": "my own words"}), 422, "bank_type: pick one of the listed"),
        (body(answers={"notes": "free text"}), 422, "We do not have a question called 'notes'."),
        (body(answers={"habitats": [{"x": 1}]}), 422, "a value from the form's lists"),
        (body(answers=["bank_type"]), 422, "answers must be an object"),
        (body(answered_at="2026-09-10T10:00:00Z"), 422, "more than 7 days old"),
        (body(answered_at="2026-09-25T11:00:00Z"), 422, "dated in the future"),
        (body(answered_at="soon"), 422, "answered_at must be a time like"),
        ([1, 2], 422, "one JSON object"),
    ],
)
def test_a_walk_holds_only_what_a_walk_collects(client, payload, status, detail) -> None:
    freeze_now(NOW)
    r = client.post("/api/walk", json=payload)
    assert r.status_code == status, r.text
    assert detail in r.json()["detail"]
    assert rows() == 0


def test_a_body_that_is_not_json_is_refused(client) -> None:
    freeze_now(NOW)
    r = client.post("/api/walk", content=b"walk_id=v02", headers={"content-type": "text/plain"})
    assert r.status_code == 422
    assert r.json()["detail"] == "That was not JSON."


def test_a_large_body_is_refused(client) -> None:
    freeze_now(NOW)
    padded = json.dumps(body()) + " " * WALK_MAX_BYTES
    r = client.post("/api/walk", content=padded, headers={"content-type": "application/json"})
    assert r.status_code == 413
    assert r.json()["detail"] == "That walk is too large to store."
    assert rows() == 0


def test_a_large_body_that_says_its_size_is_refused_before_it_is_read(client) -> None:
    """The declared length is enough: the route answers 413 without reading a byte of it."""
    freeze_now(NOW)

    def never_read():
        raise AssertionError("the route read a body it had already been told was too large")
        yield b""  # pragma: no cover

    r = client.post(
        "/api/walk",
        content=never_read(),
        headers={"content-type": "application/json", "content-length": str(WALK_MAX_BYTES + 1)},
    )
    assert r.status_code == 413


def test_a_large_body_with_no_length_is_cut_off_at_the_cap(client) -> None:
    """Sent in chunks with no declared length, it is read one chunk past the cap and refused."""
    freeze_now(NOW)
    chunks = [json.dumps(body()).encode()[:-1], b" " * WALK_MAX_BYTES, b"}"]
    r = client.post("/api/walk", content=iter(chunks), headers={"content-type": "application/json"})
    assert r.status_code == 413
    assert rows() == 0
    with pytest.raises(walk_store.TooLarge):
        walk_store.parse_body(b" " * (WALK_MAX_BYTES + 1))


def test_the_largest_walk_the_form_allows_fits_under_the_size_cap(client) -> None:
    """Every list ticked in full, every plant, every slider: still under WALK_MAX_BYTES."""
    freeze_now(NOW)
    answers: dict[str, object] = {}
    for item in content.form_items():
        kind = item["type"]
        values = [str(o["value"]) for o in item.get("options", []) or []]
        if kind == "choice":
            answers[item["id"]] = max(values, key=len)
        elif kind == "yesno":
            answers[item["id"]] = "cant_tell"
        elif kind == "multi":
            answers[item["id"]] = values
        elif kind == "number":
            answers[item["id"]] = 99.99
        elif kind == "pick_region_list":
            answers[item["id"]] = sorted(content.region_plant_names())
        elif kind == "sliders":
            answers[item["id"]] = ["joy:5", "serenity:5", "anger:not_applicable", "fear:0"]
    payload = json.dumps(body(answers=answers))
    assert len(payload.encode()) < WALK_MAX_BYTES, len(payload.encode())
    r = client.post("/api/walk", content=payload, headers={"content-type": "application/json"})
    assert r.status_code == 200, r.text


def test_the_daily_cap_stops_new_walks_until_the_next_day(client, monkeypatch) -> None:
    assert WALK_DAILY_CAP == 200
    monkeypatch.setattr(walk_store, "WALK_DAILY_CAP", 2)
    freeze_now(NOW)
    for second in ("10", "20"):
        ok = client.post("/api/walk", json=body(answered_at=f"2026-09-25T09:59:{second}Z"))
        assert ok.status_code == 200, ok.text
    full = client.post("/api/walk", json=body(answered_at="2026-09-25T09:59:30Z"))
    assert full.status_code == 429
    assert "for today" in full.json()["detail"]
    # A walk already stored may still be sent again: the phone's queue must be able to finish.
    resent = client.post("/api/walk", json=body(answered_at="2026-09-25T09:59:10Z"))
    assert resent.status_code == 200
    freeze_now(NOW + timedelta(days=1))
    later = client.post("/api/walk", json=body(answered_at="2026-09-26T09:59:30Z"))
    assert later.status_code == 200, later.text


def test_a_walk_record_is_deleted_after_its_days(client) -> None:
    freeze_now(NOW)
    record_id = client.post("/api/walk", json=body()).json()["record_id"]
    freeze_now(NOW + timedelta(days=WALK_KEEP_DAYS) - timedelta(seconds=1))
    assert client.get(f"/api/walk/{record_id}").status_code == 200
    freeze_now(NOW + timedelta(days=WALK_KEEP_DAYS))
    gone = client.get(f"/api/walk/{record_id}")
    assert gone.status_code == 404
    assert f"deleted {WALK_KEEP_DAYS} days after" in gone.json()["detail"]
    # The next walk stored deletes the row itself, not only hides it.
    assert rows() == 1
    new_at = (NOW + timedelta(days=WALK_KEEP_DAYS, seconds=-30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert client.post("/api/walk", json=body(answered_at=new_at)).status_code == 200
    with Session(engine) as db:
        assert [r.record_id for r in db.exec(select(WalkRecordRow)).all()] != [record_id]
        assert db.get(WalkRecordRow, record_id) is None


@pytest.mark.parametrize("record_id", ["walk-0000000000000000", "spot-1", "walk-XYZ", "x" * 200])
def test_an_unknown_record_is_a_plain_404(client, record_id) -> None:
    r = client.get(f"/api/walk/{record_id}")
    assert r.status_code == 404
    assert "no stored walk record" in r.json()["detail"]


def test_the_walk_routes_carry_the_same_headers_and_cors_as_the_others(client) -> None:
    freeze_now(NOW)
    origin = {"Origin": "http://web.test"}
    stored = client.post("/api/walk", json=body(), headers=origin)
    read = client.get(f"/api/walk/{stored.json()['record_id']}", headers=origin)
    preflight = client.options(
        "/api/walk",
        headers={**origin, "Access-Control-Request-Method": "POST"},
    )
    for r in (stored, read, preflight):
        assert r.headers["access-control-allow-origin"] == "http://web.test", r.url
        assert r.headers["content-security-policy"] == "default-src 'none'", r.url
        assert r.headers["x-content-type-options"] == "nosniff", r.url
        assert r.headers["referrer-policy"] == "no-referrer", r.url
    other = client.get(
        f"/api/walk/{stored.json()['record_id']}", headers={"Origin": "https://x.example"}
    )
    assert "access-control-allow-origin" not in other.headers
