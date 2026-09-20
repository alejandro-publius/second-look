"""The gate: model output becomes Flags or is dropped, and the record builder takes humans only."""

from __future__ import annotations

import inspect
import json
from datetime import UTC, date, datetime
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from core.followups import SiteContext, select_followups
from core.gate import MAX_CANDIDATES, NOTE_MAX_CHARS, Flag, build_record, parse_flags
from core.labels import observer_label
from core.records import FEATURES, CheckResult, FeatureScore, Observer, Spot

MODEL = "fake-vision-1"
OTHER_MODEL = "other-model"
PASS_TABLE: dict[str, Any] = {
    "real": False,
    "synthetic": True,
    "generated_at_utc": "2026-09-20T00:00:00Z",
    "models": {
        MODEL: {
            "artificial_bank": {"passed": True, "runs": [[True, True, True, True]] * 3},
            "dug_out_channel": {"passed": False, "runs": [[True, False, False, True]] * 3},
            "invasive_plant": {"passed": True, "runs": [[True, True, True, False]] * 3},
            "pipe_running": {"passed": False, "runs": [[False, False, True, True]] * 3},
        },
        OTHER_MODEL: {"artificial_bank": {"passed": False, "runs": []}},
    },
}
PASSED = {"artificial_bank", "invasive_plant"}
NOW = datetime(2026, 9, 23, 17, 0, tzinfo=UTC)
TODAY = date(2026, 9, 25)
SPOT = Spot(
    spot_id="spot-1",
    spot_name="Below the footbridge",
    reach_id="reach-1",
    reach_name="Lower reach",
    creek_id="creek-1",
    creek_name="Strawberry Creek",
)
LOCALE = {
    "label.score": "{correct} of {total} on {feature}, tested {date}",
    "label.expired": "Score expired. Tested {date}, more than 90 days ago. Retake the test.",
}
TABLE: dict[str, Any] = {
    "max_questions": 2,
    "rules": [
        {"id": "dry_pipe", "priority": 1, "question_key": "followup.dry_pipe"},
        {"id": "rating_check", "priority": 2, "question_key": "followup.rating_check"},
        {"id": "checker_flag", "priority": 3, "question_key": "followup.checker_flag"},
        {"id": "low_score", "priority": 4, "question_key": "followup.low_score"},
    ],
}
FORM_ITEMS: list[dict[str, Any]] = [
    {"id": "bank_type", "feature": "artificial_bank", "text": "Bank type"},
    {"id": "draining_pipes", "feature": "pipe_running", "text": "Pipes"},
    {"id": "invasive_species", "feature": "invasive_plant", "text": "Invasive"},
    {"id": "overall_rating", "feature": None, "text": "Overall"},
]


def good(**over: Any) -> dict[str, Any]:
    flag = {
        "feature": "artificial_bank",
        "confidence": 0.8,
        "note": "a straight concrete edge on the left bank",
    }
    flag.update(over)
    return flag


def parse(
    raw: object, model_id: str = MODEL, table: Any = PASS_TABLE
) -> tuple[list[Flag], list[str]]:
    return parse_flags(raw, model_id=model_id, pass_table=table)


def test_well_formed_flag_for_passed_feature_is_kept() -> None:
    flags, reasons = parse([good()])
    assert reasons == []
    assert flags == [
        Flag(
            feature="artificial_bank",
            confidence=0.8,
            note="a straight concrete edge on the left bank",
        )
    ]


def test_json_text_with_flags_key_is_parsed() -> None:
    flags, reasons = parse(json.dumps({"flags": [good(), good(feature="invasive_plant")]}))
    assert reasons == []
    assert [f.feature for f in flags] == ["artificial_bank", "invasive_plant"]


def test_single_object_is_one_candidate() -> None:
    flags, reasons = parse(good())
    assert len(flags) == 1 and reasons == []


def test_bytes_are_decoded_then_parsed() -> None:
    flags, reasons = parse(json.dumps([good()]).encode())
    assert len(flags) == 1 and reasons == []


def test_unknown_model_drops_everything_with_a_reason() -> None:
    flags, reasons = parse([good(), good()], model_id="nobody")
    assert flags == []
    assert len(reasons) == 2
    assert all("unknown model" in r for r in reasons)


def test_model_without_a_pass_for_the_feature_is_dropped() -> None:
    flags, reasons = parse([good()], model_id=OTHER_MODEL)
    assert flags == []
    assert "not passed" in reasons[0]


def test_unpassed_feature_is_dropped() -> None:
    flags, reasons = parse([good(feature="pipe_running")])
    assert flags == []
    assert reasons == [f"flag 1: feature pipe_running not passed by model {MODEL}"]


def test_unknown_feature_is_dropped() -> None:
    flags, reasons = parse([good(feature="litter")])
    assert flags == []
    assert "unknown feature" in reasons[0]


@pytest.mark.parametrize("passed", ["true", 1, "yes", None, [True]])
def test_passed_must_be_exactly_true(passed: object) -> None:
    table = {"models": {MODEL: {"artificial_bank": {"passed": passed}}}}
    flags, reasons = parse([good()], table=table)
    assert flags == []
    assert "not passed" in reasons[0]


@pytest.mark.parametrize("table", [None, [], "models", {"models": []}, {"models": {MODEL: []}}])
def test_garbage_pass_table_means_unknown_model(table: object) -> None:
    flags, reasons = parse([good()], table=table)
    assert flags == []
    assert "unknown model" in reasons[0]


@pytest.mark.parametrize(
    "confidence", [1.5, -0.1, "0.9", None, True, False, float("nan"), float("inf"), [0.5]]
)
def test_bad_confidence_is_dropped(confidence: object) -> None:
    flags, reasons = parse([good(confidence=confidence)])
    assert flags == []
    assert "bad confidence" in reasons[0]


@pytest.mark.parametrize("confidence", [0, 1, 0.0, 1.0, 0.5])
def test_confidence_at_the_edges_is_kept(confidence: float) -> None:
    flags, _ = parse([good(confidence=confidence)])
    assert len(flags) == 1
    assert flags[0].confidence == float(confidence)


def test_note_too_long_is_dropped_and_max_length_is_kept() -> None:
    flags, reasons = parse([good(note="x" * (NOTE_MAX_CHARS + 1))])
    assert flags == []
    assert "note too long" in reasons[0]
    flags, reasons = parse([good(note="x" * NOTE_MAX_CHARS)])
    assert len(flags) == 1 and reasons == []


@pytest.mark.parametrize("note", ["", "   ", None, 12, ["a"], "line one\nline two", "tab\tin"])
def test_bad_note_is_dropped(note: object) -> None:
    flags, reasons = parse([good(note=note)])
    assert flags == []
    assert "note" in reasons[0]


def test_note_is_stripped() -> None:
    flags, _ = parse([good(note="  something built  ")])
    assert flags[0].note == "something built"


@pytest.mark.parametrize("raw", [42, None, 3.5, object(), b"\xff\xfe", "not json {", "", True])
def test_not_parseable_input_drops_with_a_reason(raw: object) -> None:
    flags, reasons = parse(raw)
    assert flags == []
    assert len(reasons) == 1
    assert "not parseable" in reasons[0]


@pytest.mark.parametrize("candidate", [1, "flag", None, [good()]])
def test_candidate_that_is_not_an_object_is_dropped(candidate: object) -> None:
    flags, reasons = parse([candidate])
    assert flags == []
    assert "not an object" in reasons[0]


@pytest.mark.parametrize(
    "region",
    [[0.1, 0.2], [0.1, 0.2, 0.3, 1.5], ["a", 0.1, 0.1, 0.1], [0.1, 0.2, 0.3, -0.1], "0,0,1,1"],
)
def test_bad_region_is_dropped(region: object) -> None:
    flags, reasons = parse([good(region=region)])
    assert flags == []
    assert "bad region" in reasons[0]


def test_good_region_becomes_a_tuple_of_fractions() -> None:
    flags, reasons = parse([good(region=[0, 0.25, 0.5, 1])])
    assert reasons == []
    assert flags[0].region == (0.0, 0.25, 0.5, 1.0)


def test_extra_keys_are_ignored() -> None:
    flags, reasons = parse([good(answer="present", label="bad bank", id=7)])
    assert reasons == []
    assert len(flags) == 1


def test_mixed_list_keeps_good_and_drops_bad_in_order() -> None:
    raw = [good(), good(feature="pipe_running"), "junk", good(feature="invasive_plant", note="")]
    flags, reasons = parse(raw)
    assert [f.feature for f in flags] == ["artificial_bank"]
    assert [r.split(":")[0] for r in reasons] == ["flag 2", "flag 3", "flag 4"]


def test_a_flood_of_flags_drops_everything() -> None:
    flags, reasons = parse([good()] * (MAX_CANDIDATES + 1))
    assert flags == []
    assert reasons == [
        f"too many flags: {MAX_CANDIDATES + 1}, {MAX_CANDIDATES} at most, dropped everything"
    ]
    flags, reasons = parse([good()] * MAX_CANDIDATES)
    assert len(flags) == MAX_CANDIDATES and reasons == []


def test_flag_model_itself_refuses_bad_values() -> None:
    with pytest.raises(ValidationError):
        Flag(feature="artificial_bank", confidence=1.2, note="x")
    with pytest.raises(ValidationError):
        Flag(feature="artificial_bank", confidence=0.5, note="x" * (NOTE_MAX_CHARS + 1))
    with pytest.raises(ValidationError):
        Flag(feature="artificial_bank", confidence=0.5, note="x", region=(0, 0, 2, 0))
    with pytest.raises(ValidationError):
        Flag(feature="litter", confidence=0.5, note="x")  # type: ignore[arg-type]


def test_flag_is_frozen() -> None:
    flag = Flag(feature="artificial_bank", confidence=0.5, note="x")
    with pytest.raises(ValidationError):
        flag.note = "changed"


def human_kwargs(
    answers: dict[str, str | float | list[str]] | None = None, observer: Observer | None = None
) -> dict[str, Any]:
    return {
        "visit_id": "visit-1",
        "spot": SPOT,
        "observer": observer or Observer(contributor_token="tok-12345678"),
        "answered_at": NOW,
        "answers": answers if answers is not None else {"bank_type": "present"},
        "first_rating": "good",
        "final_rating": "moderate",
        "checks": [CheckResult(rule_id="rating_check", asked=True, answer="moderate")],
        "photo_ids": ["photo-1"],
    }


def test_build_record_signature_carries_human_inputs_only() -> None:
    params = inspect.signature(build_record).parameters
    assert set(params) == {
        "visit_id",
        "spot",
        "observer",
        "answered_at",
        "answers",
        "first_rating",
        "final_rating",
        "checks",
        "photo_ids",
    }
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in params.values())
    for name in params:
        for bad in ("flag", "model", "raw", "note", "checker"):
            assert bad not in name
    assert "No parameter carries model output" in (build_record.__doc__ or "")


def test_build_record_rejects_a_flags_argument() -> None:
    flags, _ = parse([good()])
    with pytest.raises(TypeError):
        build_record(**human_kwargs(), flags=flags)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        build_record(**human_kwargs(), model_output="present")  # type: ignore[call-arg]


def test_build_record_copies_answers_so_later_edits_do_not_leak() -> None:
    answers: dict[str, str | float | list[str]] = {"bank_type": "absent", "habitats": ["riffles"]}
    record = build_record(**human_kwargs(answers))
    answers["bank_type"] = "present"
    habitats = answers["habitats"]
    assert isinstance(habitats, list)
    habitats.append("sand_banks")
    assert record.answers == {"bank_type": "absent", "habitats": ["riffles"]}
    assert record.checks[0].rule_id == "rating_check"
    assert record.photo_ids == ("photo-1",)


json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats() | st.text(max_size=20),
    lambda children: (
        st.lists(children, max_size=4) | st.dictionaries(st.text(max_size=8), children, max_size=4)
    ),
    max_leaves=12,
)
flag_like = st.fixed_dictionaries(
    {
        "feature": st.sampled_from(FEATURES) | st.text(max_size=12),
        "confidence": st.floats() | st.integers(-2, 2) | st.text(max_size=4) | st.none(),
        "note": st.text(max_size=NOTE_MAX_CHARS + 20),
    },
    optional={"region": st.lists(st.floats(), max_size=5) | st.text(max_size=5)},
)
raw_model_output = st.one_of(
    json_values,
    st.lists(flag_like, max_size=5),
    st.fixed_dictionaries({"flags": st.lists(flag_like, max_size=5)}),
    st.text(max_size=40),
    st.binary(max_size=20),
    st.lists(flag_like, max_size=5).map(json.dumps),
)
answer_value = st.one_of(
    st.text(max_size=20),
    st.floats(allow_nan=False, allow_infinity=False),
    st.lists(st.text(max_size=8), max_size=4),
)
human_answers = st.dictionaries(st.text(min_size=1, max_size=16), answer_value, max_size=8)
scores = st.fixed_dictionaries({f: st.none() | st.integers(0, 4) for f in FEATURES})
model_ids = st.sampled_from([MODEL, OTHER_MODEL, "nobody"]) | st.text(max_size=8)
pass_tables = st.just(PASS_TABLE) | json_values


def observer_from(score_map: dict[str, int | None]) -> Observer:
    return Observer(
        contributor_token="tok-12345678",
        scores=tuple(
            FeatureScore(feature=f, correct=c, tested_on=date(2026, 9, 21))  # type: ignore[arg-type]
            for f, c in score_map.items()
            if c is not None
        ),
    )


@settings(max_examples=300, deadline=None)
@given(
    raw=raw_model_output,
    model_id=model_ids,
    table=pass_tables,
    answers=human_answers,
    score_map=scores,
    checker_enabled=st.booleans(),
)
def test_fuzz_model_output_never_reaches_answers_or_labels(
    raw: object,
    model_id: str,
    table: Any,
    answers: dict[str, str | float | list[str]],
    score_map: dict[str, int | None],
    checker_enabled: bool,
) -> None:
    flags, reasons = parse_flags(raw, model_id=model_id, pass_table=table)
    assert isinstance(flags, list) and isinstance(reasons, list)
    for flag in flags:
        assert table["models"][model_id][flag.feature]["passed"] is True
        assert 0.0 <= flag.confidence <= 1.0
        assert 1 <= len(flag.note) <= NOTE_MAX_CHARS

    observer = observer_from(score_map)
    record = build_record(
        visit_id="visit-1",
        spot=SPOT,
        observer=observer,
        answered_at=NOW,
        answers=answers,
        first_rating="good",
        final_rating=None,
        checks=(),
        photo_ids=(),
    )
    assert record.answers == dict(answers)
    for feature in FEATURES:
        from_humans = observer_label(observer.score_for(feature), feature, TODAY, LOCALE)
        from_record = observer_label(record.observer.score_for(feature), feature, TODAY, LOCALE)
        assert from_record == from_humans

    site = SiteContext(rain="dry", dry_days=3, mm_in_window=0.0)
    chosen = select_followups(
        answers,
        site,
        observer,
        flags,
        TABLE,
        form_items=FORM_ITEMS,
        checker_enabled=checker_enabled,
    )
    assert len(chosen) <= 2
    checker = [c for c in chosen if c.rule_id == "checker_flag"]
    assert len(checker) <= 1
    if checker:
        assert checker_enabled and flags
        assert checker[0].params["note"] in {f.note for f in flags}
    assert record.answers == dict(answers)
