"""Score a test sitting from the gold key. Pure functions, no I/O.

The gold key never reaches the browser. The API calls these after the person has
answered every item, and the export writes the same correctness column.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from core.records import FEATURES, FeatureId, FeatureScore, GoldLabel, TestAnswer

_MATCH: dict[GoldLabel, TestAnswer] = {"present": "yes", "absent": "no"}


def is_correct(answer: TestAnswer, gold: GoldLabel) -> bool:
    """True only when yes meets present or no meets absent. Can't tell is never correct."""
    return _MATCH.get(gold) == answer


def score_sitting(
    responses: Mapping[str, TestAnswer], items: Sequence[Mapping[str, Any]], tested_on: date
) -> list[FeatureScore]:
    """One FeatureScore per feature, in FEATURES order. Missing or cant_tell answers count as wrong.

    `items` is the list from content/test_items.yaml: each has id, feature and gold.
    `total` is the number of items the key holds for that feature, so a short key still scores.
    """
    correct: dict[str, int] = dict.fromkeys(FEATURES, 0)
    total: dict[str, int] = dict.fromkeys(FEATURES, 0)
    for item in items:
        feature = str(item["feature"])
        if feature not in total:
            raise ValueError(f"test item {item.get('id')} has unknown feature {feature!r}")
        total[feature] += 1
        answer = responses.get(str(item["id"]))
        if answer is not None and is_correct(answer, item["gold"]):
            correct[feature] += 1
    out: list[FeatureScore] = []
    for feature in FEATURES:
        fid: FeatureId = feature
        out.append(
            FeatureScore(
                feature=fid, correct=correct[feature], total=total[feature], tested_on=tested_on
            )
        )
    return out
