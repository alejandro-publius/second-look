"""Video walks: a demo record on every resource, never a stored id, and the same id every time."""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, timezone

import pytest

from core.fhir_emit import check_bundle
from core.walks import DEMO_TAG_CODE, is_demo, utc_stamp, walk_bundle, walk_spot, walk_visit_id

WALK = {"id": "v03", "spot_name": "The stretch in the clip", "creek_name": "A creek in Chile"}
AT = datetime(2026, 9, 24, 16, 5, 9, tzinfo=UTC)


def test_every_resource_in_a_walk_record_carries_the_demo_tag() -> None:
    bundle = walk_bundle(WALK, {"bank_type": "present"}, AT)
    assert is_demo(bundle)
    for entry in bundle["entry"]:
        codes = [t["code"] for t in entry["resource"]["meta"]["tag"]]
        assert codes.count(DEMO_TAG_CODE) == 1, entry["resource"]["resourceType"]


def test_a_walk_record_is_structurally_sound() -> None:
    assert check_bundle(walk_bundle(WALK, {"bank_type": "absent"}, AT)) == []


def test_a_walk_spot_has_no_position_and_ids_no_stored_spot_can_have() -> None:
    spot = walk_spot(WALK)
    assert spot.latitude is None and spot.longitude is None and spot.coarse
    assert all(i.startswith("walk-") for i in (spot.spot_id, spot.reach_id, spot.creek_id))
    assert len({spot.spot_id, spot.reach_id, spot.creek_id}) == 3


def test_the_visit_id_depends_on_the_walk_and_the_moment_only() -> None:
    assert walk_visit_id("v03", AT) == walk_visit_id("v03", AT)
    assert walk_visit_id("v03", AT) != walk_visit_id("v04", AT)
    later = datetime(2026, 9, 24, 16, 5, 10, tzinfo=UTC)
    assert walk_visit_id("v03", AT) != walk_visit_id("v03", later)
    # Sub-second noise does not change it: both languages write seconds only.
    assert walk_visit_id("v03", AT) == walk_visit_id("v03", AT.replace(microsecond=750000))


def test_a_bundle_without_the_tag_is_not_a_demo() -> None:
    bundle = walk_bundle(WALK, {}, AT)
    assert not is_demo({**bundle, "meta": {}})


def test_the_spot_reach_and_creek_are_three_locations_with_three_urls() -> None:
    bundle = walk_bundle(WALK, {"bank_type": "present"}, AT)
    urls = [e["fullUrl"] for e in bundle["entry"]]
    assert len(urls) == len(set(urls))
    locations = [
        e["resource"]["id"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Location"
    ]
    assert len(set(locations)) == 3


@pytest.fixture
def far_from_utc(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Run as a machine in California would, so a time read as local time shows up."""
    monkeypatch.setenv("TZ", "America/Los_Angeles")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


@pytest.mark.usefixtures("far_from_utc")
def test_a_time_with_no_zone_is_read_as_utc_like_the_emitter_and_the_worker() -> None:
    naive = AT.replace(tzinfo=None)
    assert utc_stamp(naive) == "2026-09-24T16:05:09Z"
    assert walk_visit_id("v03", naive) == walk_visit_id("v03", AT)
    # The record's own times read it the same way, so the id and the record agree.
    record = walk_bundle(WALK, {"bank_type": "present"}, naive)
    assert record == walk_bundle(WALK, {"bank_type": "present"}, AT)


def test_a_time_with_a_zone_is_moved_to_utc() -> None:
    berlin = AT.astimezone(timezone(timedelta(hours=2)))
    assert utc_stamp(berlin) == "2026-09-24T16:05:09Z"
