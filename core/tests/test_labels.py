"""Labels: raw k of 4 with the test date, expired after 90 days, no grade and no probability."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.labels import HUMAN_PASS_MIN, Label, observer_label, short_date
from core.records import SCORE_VALID_DAYS, FeatureScore

ROOT = Path(__file__).resolve().parents[2]
LOCALE: dict[str, str] = json.loads((ROOT / "content" / "locales" / "en.json").read_text("utf-8"))
TESTED = date(2026, 9, 23)


def score(correct: int, tested_on: date = TESTED) -> FeatureScore:
    return FeatureScore(feature="artificial_bank", correct=correct, tested_on=tested_on)


def test_pass_mark_is_three_of_four() -> None:
    assert HUMAN_PASS_MIN == 3


def test_fresh_score_reads_k_of_total_with_the_test_date() -> None:
    label = observer_label(score(4), "built banks", date(2026, 9, 25), LOCALE)
    assert label == Label(text="4 of 4 on built banks, tested Sep 23", expired=False, passed=True)


@pytest.mark.parametrize(
    ("correct", "passed"), [(0, False), (1, False), (2, False), (3, True), (4, True)]
)
def test_passed_is_three_or_better(correct: int, passed: bool) -> None:
    label = observer_label(score(correct), "built banks", date(2026, 9, 25), LOCALE)
    assert label.passed is passed
    assert label.text.startswith(f"{correct} of 4 on built banks")


def test_no_score_gives_an_empty_label_with_passed_unknown() -> None:
    assert observer_label(None, "built banks", date(2026, 9, 25), LOCALE) == Label(
        text="", expired=False, passed=None
    )


def test_ninety_days_old_is_still_valid() -> None:
    today = TESTED + timedelta(days=SCORE_VALID_DAYS)
    label = observer_label(score(4), "built banks", today, LOCALE)
    assert label.expired is False and label.passed is True
    assert label.text == "4 of 4 on built banks, tested Sep 23"


def test_ninety_one_days_old_is_expired_with_passed_unknown() -> None:
    today = TESTED + timedelta(days=SCORE_VALID_DAYS + 1)
    label = observer_label(score(4), "built banks", today, LOCALE)
    assert label == Label(
        text="Score expired. Tested Sep 23, more than 90 days ago. Retake the test.",
        expired=True,
        passed=None,
    )


def test_date_has_no_zero_padding_and_fixed_english_months() -> None:
    assert short_date(date(2026, 9, 5)) == "Sep 5"
    assert short_date(date(2026, 1, 31)) == "Jan 31"
    label = observer_label(score(2, date(2026, 6, 1)), "pipes", date(2026, 6, 2), LOCALE)
    assert label.text == "2 of 4 on pipes, tested Jun 1"


def test_label_never_shows_a_percentage_or_a_grade() -> None:
    for correct in range(5):
        text = observer_label(score(correct), "built banks", date(2026, 9, 25), LOCALE).text
        assert "%" not in text
        assert "probab" not in text.lower()
        assert "grade" not in text.lower()


def test_missing_locale_key_is_loud() -> None:
    with pytest.raises(KeyError):
        observer_label(score(4), "built banks", date(2026, 9, 25), {})


@settings(max_examples=200, deadline=None)
@given(
    correct=st.integers(0, 4),
    tested_on=st.dates(date(2026, 1, 1), date(2026, 12, 31)),
    age_days=st.integers(-5, 400),
)
def test_expiry_and_pass_follow_the_day_count_alone(
    correct: int, tested_on: date, age_days: int
) -> None:
    today = tested_on + timedelta(days=age_days)
    label = observer_label(score(correct, tested_on), "x", today, LOCALE)
    expired = age_days > SCORE_VALID_DAYS
    assert label.expired is expired
    if expired:
        assert label.passed is None
        assert label.text == LOCALE["label.expired"].format(date=short_date(tested_on))
    else:
        assert label.passed is (correct >= HUMAN_PASS_MIN)
        assert label.text == f"{correct} of 4 on x, tested {short_date(tested_on)}"
