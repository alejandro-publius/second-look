"""The gate says exactly why it dropped a flag, and keeps the human's two ratings.

Mutation testing (make mutation) found these edges unpinned: the other gate tests look for a word
in a drop reason, so a reason could turn to nonsense and nothing would notice. The reasons are
what evals/footage.py counts and what the results say ("feature pipe_running not passed by model
..."), so each is checked word for word here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from core.gate import build_record, parse_flags
from core.records import CheckResult, Observer, Spot

MODEL = "fake-vision-1"
PASS_TABLE: dict[str, Any] = {
    "real": True,
    "models": {
        MODEL: {
            "artificial_bank": {"passed": True},
            "dug_out_channel": {"passed": False},
            "invasive_plant": {"passed": True},
            "pipe_running": {"passed": False},
        }
    },
}


def candidate(**over: Any) -> dict[str, Any]:
    flag: dict[str, Any] = {
        "feature": "artificial_bank",
        "confidence": 0.8,
        "note": "a straight concrete edge on the left bank",
    }
    flag.update(over)
    return flag


def reason_for(raw: object) -> list[str]:
    flags, reasons = parse_flags(raw, model_id=MODEL, pass_table=PASS_TABLE)
    assert flags == []
    return reasons


@pytest.mark.parametrize(
    ("over", "reason"),
    [
        ({"note": 12}, "note is not text"),
        ({"note": "   "}, "note is empty"),
        ({"note": "one\ntwo"}, "note has line breaks or control characters"),
        ({"note": "a bell\x07 in the note"}, "note has line breaks or control characters"),
        ({"note": "a line\u2028separator"}, "note has line breaks or control characters"),
        ({"note": "abc\u202edef"}, "note has text direction controls"),
        ({"note": "a <b>bold</b> edge"}, "note has angle brackets"),
        ({"region": [0.1, 0.2]}, "bad region: needs four numbers x, y, w, h"),
        ({"region": ["a", 0.1, 0.1, 0.1]}, "bad region: parts must be numbers"),
        ({"region": [0.1, 0.2, 0.3, 1.5]}, "bad region: parts must be fractions between 0 and 1"),
        ({"confidence": "high"}, "bad confidence: not a number"),
        ({"confidence": 1.5}, "bad confidence: must be between 0 and 1"),
        ({"feature": "pipe_running"}, f"feature pipe_running not passed by model {MODEL}"),
        ({"feature": "beaver_dam"}, "unknown feature 'beaver_dam'"),
    ],
)
def test_each_drop_says_why_in_the_same_words(over: dict[str, Any], reason: str) -> None:
    assert reason_for([candidate(**over)]) == [f"flag 1: {reason}"]


@pytest.mark.parametrize(("value", "kind"), [(7, "int"), ("flag", "str"), (None, "NoneType")])
def test_a_candidate_that_is_not_an_object_names_what_it_was(value: object, kind: str) -> None:
    flags, reasons = parse_flags([candidate(), value], model_id=MODEL, pass_table=PASS_TABLE)
    assert len(flags) == 1
    assert reasons == [f"flag 2: not an object: got {kind}"]


@pytest.mark.parametrize(
    "note",
    [
        "Concrete wall, marked X2 on the culvert",
        "XXL drain pipe under the path",
        "Pipe P3 by the XC trail, water running",
    ],
)
def test_an_ordinary_note_with_capital_letters_is_kept(note: str) -> None:
    flags, reasons = parse_flags([candidate(note=note)], model_id=MODEL, pass_table=PASS_TABLE)
    assert reasons == []
    assert [f.note for f in flags] == [note]


def test_the_record_keeps_the_first_and_the_final_rating_the_person_gave() -> None:
    spot = Spot(
        spot_id="spot-1",
        spot_name="Below the footbridge",
        reach_id="reach-1",
        reach_name="Lower reach",
        creek_id="creek-1",
        creek_name="Strawberry Creek",
    )
    record = build_record(
        visit_id="visit-1",
        spot=spot,
        observer=Observer(contributor_token="ct-test-observer-01"),
        answered_at=datetime(2026, 9, 23, 17, 0, tzinfo=UTC),
        answers={"overall_rating": "good", "bank_type": "present"},
        first_rating="good",
        final_rating="moderate",
        checks=[CheckResult(rule_id="rating_check", asked=True, answer="moderate")],
        photo_ids=[],
    )
    assert record.first_rating == "good"
    assert record.final_rating == "moderate"
