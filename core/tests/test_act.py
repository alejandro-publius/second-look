"""ACT: findings, what a creek needs, pipes worth testing, the pin guards, the downstream note."""

from __future__ import annotations

from datetime import UTC, date, datetime

from core.act import (
    MEASURE_FOR_FEATURE,
    SAME_SPOT_METRES,
    Finding,
    downstream_note,
    findings_from_visits,
    looks_like_a_test_name,
    metres_between,
    nearest_spot,
    needs_from_findings,
    pipes_worth_testing,
)
from core.records import CheckResult, FeatureScore, Observer, Spot, VisitRecord

TODAY = date(2026, 9, 24)
# A contributor token is at least eight characters, so these look like the real thing.
ALICE = "alicetoken23456"
BOB = "bobtoken23456789"
SPOT = Spot(
    spot_id="s1",
    spot_name="Footbridge",
    reach_id="campus",
    reach_name="Campus reach",
    creek_id="strawberry",
    creek_name="Strawberry Creek",
    latitude=37.8719,
    longitude=-122.2585,
    coarse=False,
)


def observer(token: str, pipe_correct: int = 4, tested_on: date = date(2026, 9, 20)) -> Observer:
    return Observer(
        contributor_token=token,
        scores=(FeatureScore(feature="pipe_running", correct=pipe_correct, tested_on=tested_on),),
    )


def visit(
    visit_id: str,
    token: str,
    *,
    answers: dict | None = None,
    day: int = 22,
    dry_days: int | None = None,
    dry_answer: str = "yes",
    pipe_correct: int = 4,
    tested_on: date = date(2026, 9, 20),
    spot: Spot = SPOT,
) -> VisitRecord:
    checks: tuple[CheckResult, ...] = ()
    if dry_days is not None:
        checks = (
            CheckResult(
                rule_id="dry_pipe",
                asked=True,
                question_text="It has not rained. Is anything coming out of that pipe?",
                answer=dry_answer,
                detail={"days": dry_days},
            ),
        )
    return VisitRecord(
        visit_id=visit_id,
        spot=spot,
        observer=observer(token, pipe_correct, tested_on),
        answered_at=datetime(2026, 9, day, 12, 0, tzinfo=UTC),
        answers=answers if answers is not None else {"pipe_running": "present"},
        checks=checks,
    )


# Findings --------------------------------------------------------------------------------------


def test_one_person_visiting_twice_counts_once() -> None:
    found = findings_from_visits(
        [
            visit("v1", ALICE, day=22),
            visit("v2", ALICE, day=23),
            visit("v3", BOB, day=23),
        ]
    )
    assert len(found) == 1
    f = found[0]
    assert f.feature == "pipe_running"
    assert f.observers == (ALICE, BOB), "people, not visits"
    assert f.n_observers == 2
    assert f.visit_ids == ("v1", "v2", "v3"), "every visit is still evidence"
    assert f.first_seen == date(2026, 9, 22) and f.last_seen == date(2026, 9, 23)


def test_absent_is_not_a_finding() -> None:
    assert findings_from_visits([visit("v1", ALICE, answers={"pipe_running": "absent"})]) == []
    assert findings_from_visits([visit("v1", ALICE, answers={"pipe_running": "cant_tell"})]) == []


def test_every_feature_with_a_measure_can_be_found() -> None:
    answers = dict.fromkeys(MEASURE_FOR_FEATURE, "present")
    found = findings_from_visits([visit("v1", ALICE, answers=answers)])
    assert {f.feature for f in found} == set(MEASURE_FOR_FEATURE)


# What this creek needs -------------------------------------------------------------------------


APPROVED = [
    {
        "id": "city_fix_sewers",
        "audience": "city",
        "text": "Find and fix leaking sewers.",
        "source": "Policy Brief page 9",
        "approved": True,
    },
    {
        "id": "city_replant_margins",
        "audience": "city",
        "text": "Replant both margins.",
        "source": "Policy Brief page 9",
        "approved": False,
    },
]


def test_an_unapproved_sentence_says_nothing_at_all() -> None:
    """Hard rule 5. A city sees nothing rather than a sentence nobody checked."""
    findings = findings_from_visits([visit("v1", ALICE, answers={"artificial_bank": "present"})])
    assert findings and findings[0].feature == "artificial_bank"
    assert needs_from_findings(findings, APPROVED) == []


def test_an_approved_sentence_carries_its_source_and_its_evidence() -> None:
    findings = findings_from_visits([visit("v1", ALICE), visit("v2", BOB)])
    needs = needs_from_findings(findings, APPROVED)
    assert len(needs) == 1
    need = needs[0]
    assert need.sentence_id == "city_fix_sewers"
    assert need.text == "Find and fix leaking sewers."
    assert need.source == "Policy Brief page 9"
    assert need.because == ("pipe_running",)
    assert need.visit_ids == ("v1", "v2"), "no number without its ids"


def test_a_sentence_for_the_person_is_never_a_city_measure() -> None:
    person = [{**APPROVED[0], "audience": "person"}]
    findings = findings_from_visits([visit("v1", ALICE)])
    assert needs_from_findings(findings, person) == []


# Pipes worth testing ---------------------------------------------------------------------------


def test_two_different_people_who_both_passed_put_a_pipe_on_the_list() -> None:
    cases = pipes_worth_testing(
        [visit("v1", ALICE, dry_days=5), visit("v2", BOB, dry_days=9)], TODAY
    )
    assert len(cases) == 1
    case = cases[0]
    assert case.spot_id == "s1" and case.spot_name == "Footbridge"
    assert case.observers == (ALICE, BOB)
    assert case.visit_ids == ("v1", "v2")
    assert sorted(case.dry_days) == [5, 9]


def test_one_person_twice_is_not_two_people() -> None:
    assert (
        pipes_worth_testing(
            [visit("v1", ALICE, dry_days=5, day=22), visit("v2", ALICE, dry_days=6, day=23)],
            TODAY,
        )
        == []
    )


def test_a_person_who_did_not_pass_the_pipe_feature_does_not_count() -> None:
    """A person who cannot tell a pipe from a shadow must not send a city out with a bottle."""
    assert (
        pipes_worth_testing(
            [visit("v1", ALICE, dry_days=5), visit("v2", BOB, dry_days=5, pipe_correct=2)],
            TODAY,
        )
        == []
    )


def test_an_expired_score_does_not_count() -> None:
    old = date(2026, 1, 1)
    assert (
        pipes_worth_testing(
            [visit("v1", ALICE, dry_days=5), visit("v2", BOB, dry_days=5, tested_on=old)], TODAY
        )
        == []
    )


def test_a_pipe_without_dry_weather_is_not_on_the_list() -> None:
    assert pipes_worth_testing([visit("v1", ALICE), visit("v2", BOB)], TODAY) == []


def test_a_no_to_the_dry_pipe_question_is_not_a_report() -> None:
    assert (
        pipes_worth_testing(
            [visit("v1", ALICE, dry_days=5, dry_answer="no"), visit("v2", BOB, dry_days=5)],
            TODAY,
        )
        == []
    )


# The pin guards --------------------------------------------------------------------------------


def test_a_pin_within_thirty_metres_offers_the_spot_that_is_already_there() -> None:
    # About 22 metres north of the footbridge.
    near = nearest_spot(37.8721, -122.2585, [SPOT])
    assert near is not None
    assert near.spot.spot_id == "s1"
    assert 15 < near.metres < 30


def test_a_pin_further_away_is_a_new_spot() -> None:
    assert nearest_spot(37.8760, -122.2585, [SPOT]) is None


def test_the_closest_spot_wins() -> None:
    further = SPOT.model_copy(update={"spot_id": "s2", "latitude": 37.87205})
    near = nearest_spot(37.8721, -122.2585, [SPOT, further])
    assert near is not None and near.spot.spot_id == "s2"


def test_a_spot_with_no_position_is_skipped() -> None:
    coarse = SPOT.model_copy(update={"spot_id": "s3", "latitude": None, "longitude": None})
    assert nearest_spot(37.8719, -122.2585, [coarse]) is None


def test_the_distance_is_right_to_about_a_metre() -> None:
    # One tenth of a degree of latitude is about 11,119 metres anywhere on Earth.
    assert abs(metres_between(0.0, 0.0, 0.1, 0.0) - 11_119) < 5
    assert metres_between(37.8719, -122.2585, 37.8719, -122.2585) == 0.0
    assert SAME_SPOT_METRES == 30.0


def test_a_name_that_reads_like_a_test_is_flagged() -> None:
    for name in ("test", "Test Creek", "asdf", "my demo spot", "123", "...", "  ", "DELETE ME"):
        assert looks_like_a_test_name(name), name


def test_a_real_place_name_is_left_alone() -> None:
    for name in ("Strawberry Creek", "Footbridge below the library", "Codornices Creek", "Attest"):
        assert not looks_like_a_test_name(name), name


# The downstream note ---------------------------------------------------------------------------


def test_the_downstream_note_says_who_and_when_and_nothing_about_risk() -> None:
    finding = Finding(
        spot_id="s1",
        feature="pipe_running",
        observers=(ALICE, BOB),
        visit_ids=("v1", "v2"),
        first_seen=date(2026, 9, 22),
        last_seen=date(2026, 9, 22),
    )
    notes = downstream_note(finding, "a pipe running", ["lower", "mouth"])
    assert set(notes) == {"lower", "mouth"}
    line = notes["lower"]
    assert line == "Upstream of here, 2 people reported a pipe running on Sep 22."
    for word in ("unsafe", "risk", "sick", "danger", "contaminated"):
        assert word not in line.lower()


def test_one_person_reads_as_one_person() -> None:
    finding = Finding(
        spot_id="s1",
        feature="pipe_running",
        observers=(ALICE,),
        visit_ids=("v1",),
        first_seen=date(2026, 9, 22),
        last_seen=date(2026, 9, 22),
    )
    assert "one person reported" in downstream_note(finding, "a pipe running", ["lower"])["lower"]
