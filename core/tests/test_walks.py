"""Video walks: a demo record on every resource, never a stored id, and the same id every time."""

from __future__ import annotations

import time
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from core.content_loader import load_content
from core.fhir_emit import check_bundle
from core.followups import Followup
from core.walks import (
    DEMO_TAG_CODE,
    WALK_FUTURE_SECONDS,
    WALK_KEEP_DAYS,
    WALK_PAST_DAYS,
    WalkRecordError,
    is_demo,
    utc_stamp,
    walk_bundle,
    walk_checks,
    walk_followups,
    walk_record,
    walk_spot,
    walk_visit_id,
)

ROOT = Path(__file__).resolve().parents[2]

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


# UPDATE_30 section 1 item 3: the row the store keeps for a finished walk.
NOW = datetime(2026, 9, 25, 10, 0, 0, tzinfo=UTC)


def test_a_stored_walk_is_the_record_the_phone_built_with_the_same_id() -> None:
    row = walk_record(WALK, {"bank_type": "present"}, "2026-09-25T09:59:58.250Z", NOW)
    at = datetime(2026, 9, 25, 9, 59, 58, tzinfo=UTC)
    assert row["record_id"] == walk_visit_id("v03", at)
    assert row["bundle"] == walk_bundle(WALK, {"bank_type": "present"}, at)
    assert is_demo(row["bundle"])
    assert row["answered_at"] == "2026-09-25T09:59:58Z"
    assert row["created_at"] == "2026-09-25T10:00:00Z"


def test_a_stored_walk_is_deleted_after_the_days_the_docs_name() -> None:
    row = walk_record(WALK, {}, "2026-09-25T10:00:00Z", NOW)
    assert row["delete_after"] == utc_stamp(NOW + timedelta(days=WALK_KEEP_DAYS))
    assert WALK_KEEP_DAYS == 30


def test_the_same_walk_sent_twice_is_one_record() -> None:
    first = walk_record(WALK, {"bank_type": "present"}, "2026-09-25T09:00:00Z", NOW)
    later = NOW + timedelta(hours=2)
    again = walk_record(WALK, {"bank_type": "present"}, "2026-09-25T09:00:00Z", later)
    assert first["record_id"] == again["record_id"]


@pytest.mark.parametrize(
    ("answered_at", "reason"),
    [
        ("2026-09-25T10:05:01Z", "dated in the future"),
        ("2026-09-18T09:59:59Z", "more than 7 days old"),
        ("2026-09-25T10:00:00", "must be a time like"),
        ("yesterday", "must be a time like"),
        (1790000000, "must be a time like"),
        (None, "must be a time like"),
    ],
)
def test_a_walk_dated_where_nobody_could_have_made_it_is_refused(
    answered_at: object, reason: str
) -> None:
    with pytest.raises(WalkRecordError, match=reason):
        walk_record(WALK, {"bank_type": "present"}, answered_at, NOW)


def test_the_edges_of_the_window_are_kept() -> None:
    ahead = NOW + timedelta(seconds=WALK_FUTURE_SECONDS)
    old = NOW - timedelta(days=WALK_PAST_DAYS)
    for moment in (ahead, old):
        assert walk_record(WALK, {}, utc_stamp(moment), NOW)["answered_at"] == utc_stamp(moment)


# Judge walk W01: a walk runs the creek check's follow-up rules on its answers. The judge's own
# answers: overall Good, the bank Artificial, a sewage discharge and a pipe.
JUDGE = {
    "overall_rating": "good",
    "bank_type": "present",
    "sewage_discharge": "present",
    "draining_pipes": "present",
}


def _followups(answers: Mapping[str, object]) -> list[Followup]:
    content = load_content(ROOT)
    return walk_followups(answers, content.followups, form_items=content.form["items"])


def test_a_walk_asks_the_rating_check_and_never_the_dry_pipe_question() -> None:
    chosen = _followups(JUDGE)
    # Rain is unknown for a clip, so the dry pipe rule fails closed although a pipe was reported;
    # no score and no flag, so the low score and checker rules have nothing to read.
    assert [f.rule_id for f in chosen] == ["rating_check"]
    assert chosen[0].params["issues"] == "artificial banks and a sewage discharge"
    assert _followups({**JUDGE, "overall_rating": "moderate"}) == []


def test_a_walk_keeps_its_checks_as_the_creek_check_does() -> None:
    chosen = _followups(JUDGE)
    checks, final = walk_checks(JUDGE, chosen, ["Keep it?"], {"rating_check": "change"}, "poor")
    assert final == "poor"
    assert [c.model_dump() for c in checks] == [
        {
            "rule_id": "rating_check",
            "asked": True,
            "question_text": "Keep it?",
            "answer": "change",
            "detail": {
                "issues": "artificial banks and a sewage discharge",
                "first_rating": "good",
                "kind": "keep_rating",
            },
        }
    ]
    assert walk_checks(JUDGE, chosen, ["Keep it?"], {}, None)[1] == "good"
    assert walk_checks(JUDGE, chosen, ["Keep it?"], {"rating_check": "keep"}, "good")[1] == "good"


@pytest.mark.parametrize(
    ("given", "final", "reason"),
    [
        ({"dry_pipe": "yes"}, None, "No follow-up called 'dry_pipe' was asked in this walk."),
        ({"rating_check": "yes"}, None, "rating_check: answer keep, change, skipped."),
        ({"rating_check": "change"}, None, "A changed rating needs the new rating."),
        ({"rating_check": "keep"}, "poor", "only when the rating check says change"),
        ({}, "poor", "only when the rating check says change"),
    ],
)
def test_a_walk_answer_that_does_not_fit_its_question_is_refused(
    given: dict[str, object], final: str | None, reason: str
) -> None:
    with pytest.raises(WalkRecordError, match=reason.replace(".", r"\.")):
        walk_checks(JUDGE, _followups(JUDGE), ["Keep it?"], given, final)


def _rating_answer(bundle: Mapping[str, object]) -> tuple[str, str]:
    """The overall rating the record's QuestionnaireResponse answers, and that response's text."""
    entries = bundle["entry"]
    assert isinstance(entries, list)
    for entry in entries:
        resource = entry["resource"]
        if resource["resourceType"] == "QuestionnaireResponse":
            rated = [i for i in resource["item"] if i["linkId"] == "overall_rating"]
            return rated[0]["answer"][0]["valueCoding"]["code"], resource["text"]["div"]
    raise AssertionError("no QuestionnaireResponse")


# Critic round 15 F02: after Change my rating the record screen said the new rating, but View as
# FHIR still answered Good. The record a city reads carries the rating the person kept.
def test_a_rating_changed_on_the_rating_check_is_the_rating_the_record_carries() -> None:
    changed = walk_bundle(WALK, JUDGE, AT, "poor")
    code, text = _rating_answer(changed)
    assert code == "poor"
    assert "The first overall rating was good." in text
    assert "changed it to poor" in text
    assert check_bundle(changed) == [] and is_demo(changed)
    # Kept, or no rating check at all: the record the walk's own answers make, word for word.
    assert walk_bundle(WALK, JUDGE, AT, "good") == walk_bundle(WALK, JUDGE, AT)
    assert _rating_answer(walk_bundle(WALK, JUDGE, AT))[0] == "good"
    # The stored row carries the same record, and the answers themselves are left as given.
    row = walk_record(WALK, JUDGE, "2026-09-25T09:59:58Z", NOW, "poor")
    at = datetime(2026, 9, 25, 9, 59, 58, tzinfo=UTC)
    assert row["bundle"] == walk_bundle(WALK, JUDGE, at, "poor")
    assert JUDGE["overall_rating"] == "good"


def test_a_walk_record_states_the_language_its_questions_were_shown_in() -> None:
    """UPDATE_32 section 2: the walk's QuestionnaireResponse carries the language; English when
    none is given, and the record id does not depend on it."""
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    at = "2026-09-26T11:59:00Z"
    nl = walk_record(WALK, {"draining_pipes": "absent"}, at, now, None, "nl")
    en = walk_record(WALK, {"draining_pipes": "absent"}, at, now)

    def qr(row: Mapping[str, object]) -> dict[str, object]:
        entries = row["bundle"]["entry"]  # type: ignore[index]
        kind = "QuestionnaireResponse"
        return next(e["resource"] for e in entries if e["resource"]["resourceType"] == kind)

    assert qr(nl)["language"] == "nl"
    assert qr(en)["language"] == "en"
    assert nl["record_id"] == en["record_id"]
