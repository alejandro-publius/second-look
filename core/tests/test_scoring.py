from datetime import date

import pytest

from core.records import FEATURES, FeatureScore, TestAnswer
from core.scoring import is_correct, score_sitting

ITEMS = [
    {"id": "t01", "feature": "artificial_bank", "photo_id": "p1", "gold": "present"},
    {"id": "t02", "feature": "artificial_bank", "photo_id": "p2", "gold": "present"},
    {"id": "t03", "feature": "artificial_bank", "photo_id": "p3", "gold": "absent"},
    {"id": "t04", "feature": "artificial_bank", "photo_id": "p4", "gold": "absent"},
    {"id": "t05", "feature": "dug_out_channel", "photo_id": "p5", "gold": "present"},
    {"id": "t06", "feature": "dug_out_channel", "photo_id": "p6", "gold": "present"},
    {"id": "t07", "feature": "dug_out_channel", "photo_id": "p7", "gold": "absent"},
    {"id": "t08", "feature": "dug_out_channel", "photo_id": "p8", "gold": "absent"},
    {"id": "t09", "feature": "invasive_plant", "photo_id": "p9", "gold": "present"},
    {"id": "t10", "feature": "invasive_plant", "photo_id": "p10", "gold": "present"},
    {"id": "t11", "feature": "invasive_plant", "photo_id": "p11", "gold": "absent"},
    {"id": "t12", "feature": "invasive_plant", "photo_id": "p12", "gold": "absent"},
    {"id": "t13", "feature": "pipe_running", "photo_id": "p13", "gold": "present"},
    {"id": "t14", "feature": "pipe_running", "photo_id": "p14", "gold": "present"},
    {"id": "t15", "feature": "pipe_running", "photo_id": "p15", "gold": "absent"},
    {"id": "t16", "feature": "pipe_running", "photo_id": "p16", "gold": "absent"},
]
DAY = date(2026, 9, 23)


@pytest.mark.parametrize(
    ("answer", "gold", "expected"),
    [
        ("yes", "present", True),
        ("no", "present", False),
        ("cant_tell", "present", False),
        ("yes", "absent", False),
        ("no", "absent", True),
        ("cant_tell", "absent", False),
    ],
)
def test_is_correct_every_combination(answer, gold, expected):
    assert is_correct(answer, gold) is expected


def test_perfect_sitting_scores_four_of_four_everywhere():
    responses: dict[str, TestAnswer] = {
        i["id"]: ("yes" if i["gold"] == "present" else "no") for i in ITEMS
    }
    scores = score_sitting(responses, ITEMS, DAY)
    assert [s.feature for s in scores] == list(FEATURES)
    assert all(s.correct == 4 and s.total == 4 and s.tested_on == DAY for s in scores)
    assert all(isinstance(s, FeatureScore) for s in scores)


def test_missing_answers_count_as_wrong():
    responses: dict[str, TestAnswer] = {"t01": "yes", "t02": "yes"}  # nothing else answered
    scores = {s.feature: s for s in score_sitting(responses, ITEMS, DAY)}
    assert scores["artificial_bank"].correct == 2
    assert scores["artificial_bank"].total == 4
    for feature in ("dug_out_channel", "invasive_plant", "pipe_running"):
        assert scores[feature].correct == 0
        assert scores[feature].total == 4


def test_cant_tell_counts_as_wrong():
    responses: dict[str, TestAnswer] = {i["id"]: "cant_tell" for i in ITEMS}
    assert all(s.correct == 0 for s in score_sitting(responses, ITEMS, DAY))


def test_all_yes_scores_the_present_items_only():
    responses: dict[str, TestAnswer] = {i["id"]: "yes" for i in ITEMS}
    assert all(s.correct == 2 for s in score_sitting(responses, ITEMS, DAY))


def test_answers_for_unknown_items_are_ignored():
    responses: dict[str, TestAnswer] = {"t99": "yes", "t01": "yes"}
    scores = {s.feature: s for s in score_sitting(responses, ITEMS, DAY)}
    assert scores["artificial_bank"].correct == 1


def test_unknown_feature_in_key_is_an_error():
    bad = [{"id": "x1", "feature": "sky_colour", "gold": "present"}]
    with pytest.raises(ValueError, match="unknown feature"):
        score_sitting({}, bad, DAY)


def test_the_error_names_the_item_to_fix_in_the_key():
    """Found by make mutation: the message must say which of the 16 items is wrong."""
    bad = [*ITEMS[:3], {"id": "t04", "feature": "sky_colour", "gold": "absent"}]
    with pytest.raises(ValueError) as caught:
        score_sitting({}, bad, DAY)
    assert str(caught.value) == "test item t04 has unknown feature 'sky_colour'"


def test_total_follows_the_key_not_a_constant():
    scores = {s.feature: s for s in score_sitting({}, ITEMS[:2], DAY)}
    assert scores["artificial_bank"].total == 2
    assert scores["pipe_running"].total == 0
