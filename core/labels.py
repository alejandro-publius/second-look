"""What the analyst sees beside an answer (master brief section 9).

A label is the raw "k of 4" and the test date, or the expired sentence when the score is older
than SCORE_VALID_DAYS. No blended grade. No probability. The text comes from the locale.

Pure. No file or network I/O.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from core.records import FeatureScore, Frozen

HUMAN_PASS_MIN = 3

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
KEY_SCORE = "label.score"
KEY_EXPIRED = "label.expired"


class Label(Frozen):
    """The text beside one answer, whether the score is stale, and pass or fail when known."""

    text: str
    expired: bool
    passed: bool | None


def short_date(day: date) -> str:
    """ "Sep 23" style, fixed English month names so the output does not depend on the C locale."""
    return f"{MONTHS[day.month - 1]} {day.day}"


def observer_label(
    score: FeatureScore | None, feature_name: str, today: date, locale: Mapping[str, str]
) -> Label:
    """Raw k of total plus the test date, or the expired sentence. passed is None with no score
    and None when the score has expired."""
    if score is None:
        return Label(text="", expired=False, passed=None)
    tested = short_date(score.tested_on)
    if score.expired_on(today):
        text = locale[KEY_EXPIRED].format(
            correct=score.correct, total=score.total, feature=feature_name, date=tested
        )
        return Label(text=text, expired=True, passed=None)
    text = locale[KEY_SCORE].format(
        correct=score.correct, total=score.total, feature=feature_name, date=tested
    )
    return Label(text=text, expired=False, passed=score.correct >= HUMAN_PASS_MIN)
