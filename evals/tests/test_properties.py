"""Hypothesis property tests for the exclusions and the vote arithmetic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from core.lock import DATA_LOCK_UTC
from evals.common import SESSION_COLUMNS, iso_utc
from evals.consensus import (
    WEIGHTS,
    plain_vote_correct,
    scored_vote_correct,
    weight_for_correct,
    weights_from_other_items,
)
from evals.usability_analysis import apply_exclusions, tidy_responses, tidy_sessions

BASE = DATA_LOCK_UTC - timedelta(days=4)


@dataclass(frozen=True)
class Rec:
    idx: int
    n_answered: int
    has_completed: bool
    test_seconds: float | None
    is_test: bool
    hidden: bool
    post_lock: bool
    after_lock_start: bool
    token: str
    offset_min: int

    @property
    def session_id(self) -> str:
        return f"s-{self.idx:03d}"

    @property
    def completed_at(self):  # noqa: ANN201
        return BASE + timedelta(minutes=self.offset_min)

    @property
    def started_at(self):  # noqa: ANN201
        if self.after_lock_start:
            return DATA_LOCK_UTC + timedelta(minutes=1)
        return self.completed_at - timedelta(minutes=5)


mostly_false = st.sampled_from([False, False, False, True])
rec_fields = st.fixed_dictionaries(
    {
        "n_answered": st.sampled_from([0, 3, 15, 16, 16, 16]),
        "has_completed": st.sampled_from([True, True, True, False]),
        "test_seconds": st.one_of(
            st.none(), st.floats(min_value=0, max_value=300, allow_nan=False)
        ),
        "is_test": mostly_false,
        "hidden": mostly_false,
        "post_lock": mostly_false,
        "after_lock_start": mostly_false,
        "token": st.sampled_from(["", "a", "b", "c", "d"]),
        "offset_min": st.integers(min_value=0, max_value=3000),
    }
)
rec_lists = st.lists(rec_fields, min_size=0, max_size=12)


def to_recs(fields: list[dict[str, Any]]) -> list[Rec]:
    return [Rec(idx=i, **f) for i, f in enumerate(fields)]


def to_frames(recs: list[Rec]) -> tuple[pd.DataFrame, pd.DataFrame]:
    srows = []
    rrows = []
    for r in recs:
        srows.append(
            {
                "session_id": r.session_id,
                "arm": "trained" if r.idx % 2 else "untrained",
                "block_id": str(r.idx // 4),
                "source_label": "chat",
                "ua_class": "phone",
                "consent_version": "v1",
                "content_hash": "c",
                "build_hash": "b",
                "started_at_utc": iso_utc(r.started_at),
                "lesson_seconds_total": "100",
                "completed_at_utc": iso_utc(r.completed_at) if r.has_completed else "",
                "test_seconds": "" if r.test_seconds is None else str(r.test_seconds),
                "is_test": str(r.is_test),
                "post_lock": str(r.post_lock),
                "hidden_field_filled": str(r.hidden),
                "client_token_hash": r.token,
                "prior_experience": "no",
                "warmup_choice": "w01",
            }
        )
        for i in range(r.n_answered):
            rrows.append(
                {
                    "session_id": r.session_id,
                    "item_id": f"t{i + 1:02d}",
                    "feature": "artificial_bank",
                    "gold": "present",
                    "answer": "yes",
                    "correct": "1",
                    "rt_ms": "1000",
                    "position": str(i + 1),
                }
            )
    sessions = tidy_sessions(pd.DataFrame(srows, columns=SESSION_COLUMNS))
    responses = tidy_responses(
        pd.DataFrame(
            rrows,
            columns=[
                "session_id",
                "item_id",
                "feature",
                "gold",
                "answer",
                "correct",
                "rt_ms",
                "position",
            ],
        )
    )
    return sessions, responses


def oracle_kept(recs: list[Rec]) -> set[str]:
    """A plain-Python statement of the plan's rules, independent of the pandas code."""
    scope = [r for r in recs if not r.post_lock and not r.after_lock_start]
    r1 = [r for r in scope if r.n_answered == 16 and r.has_completed]
    r2 = [r for r in r1 if not (r.test_seconds is not None and r.test_seconds < 40)]
    seen: set[str] = set()
    r3 = []
    for r in sorted(r2, key=lambda r: (r.completed_at, r.session_id)):
        if r.token and r.token in seen:
            continue
        if r.token:
            seen.add(r.token)
        r3.append(r)
    r4 = [r for r in r3 if not r.is_test]
    r5 = [r for r in r4 if not r.hidden]
    return {r.session_id for r in r5}


@settings(max_examples=60, deadline=None)
@given(rec_lists)
def test_exclusions_match_a_plain_statement_of_the_rules(fields: list[dict[str, Any]]) -> None:
    recs = to_recs(fields)
    sessions, responses = to_frames(recs)
    excl = apply_exclusions(sessions, responses)
    assert set(excl.kept["session_id"]) == oracle_kept(recs)
    assert excl.steps[-1].remaining == len(excl.kept)
    assert sum(s.removed for s in excl.steps) + len(excl.kept) == len(recs)


@settings(max_examples=40, deadline=None)
@given(rec_lists, st.integers(min_value=40, max_value=300))
def test_a_session_that_meets_every_rule_is_never_dropped(
    fields: list[dict[str, Any]], seconds: int
) -> None:
    recs = to_recs(fields)
    clean = Rec(
        idx=999,
        n_answered=16,
        has_completed=True,
        test_seconds=float(seconds),
        is_test=False,
        hidden=False,
        post_lock=False,
        after_lock_start=False,
        token="unique-clean-token",
        offset_min=1000,
    )
    sessions, responses = to_frames([*recs, clean])
    assert clean.session_id in set(apply_exclusions(sessions, responses).kept["session_id"])


@settings(max_examples=40, deadline=None)
@given(
    rec_lists,
    st.sampled_from(
        [
            "incomplete",
            "no_completed_at",
            "fast",
            "repeat",
            "qa",
            "hidden",
            "post_lock",
            "late_start",
        ]
    ),
)
def test_a_session_that_fails_any_rule_is_always_dropped(
    fields: list[dict[str, Any]], failure: str
) -> None:
    recs = to_recs(fields)
    bad = Rec(
        idx=998,
        n_answered=15 if failure == "incomplete" else 16,
        has_completed=failure != "no_completed_at",
        test_seconds=39.9 if failure == "fast" else 100.0,
        is_test=failure == "qa",
        hidden=failure == "hidden",
        post_lock=failure == "post_lock",
        after_lock_start=failure == "late_start",
        token="dup" if failure == "repeat" else "unique-bad-token",
        offset_min=2000,
    )
    extra = []
    if failure == "repeat":
        extra.append(Rec(997, 16, True, 100.0, False, False, False, False, "dup", offset_min=1999))
    sessions, responses = to_frames([*recs, *extra, bad])
    assert bad.session_id not in set(apply_exclusions(sessions, responses).kept["session_id"])


# ---------------------------------------------------------------------------
# Vote arithmetic
# ---------------------------------------------------------------------------

N_ITEMS_SMALL = 4
vote_rows = st.lists(st.sampled_from([-1, 0, 1]), min_size=N_ITEMS_SMALL, max_size=N_ITEMS_SMALL)
vote_matrix = st.lists(vote_rows, min_size=1, max_size=7).map(
    lambda rows: np.array(rows, dtype=int)
)
gold_signs = st.lists(st.sampled_from([-1, 1]), min_size=N_ITEMS_SMALL, max_size=N_ITEMS_SMALL).map(
    lambda g: np.array(g, dtype=int)
)


@settings(max_examples=100, deadline=None)
@given(vote_matrix, gold_signs)
def test_plain_vote_is_the_sign_of_the_sum_and_zero_is_wrong(
    votes: np.ndarray, gold: np.ndarray
) -> None:
    result = plain_vote_correct(votes, gold)
    total = votes.sum(axis=0)
    for j in range(N_ITEMS_SMALL):
        if total[j] == 0:
            assert not result[j]
        else:
            assert result[j] == (np.sign(total[j]) == gold[j])
    flipped = plain_vote_correct(-votes, -gold)
    assert (flipped == result).all()


@settings(max_examples=100, deadline=None)
@given(vote_matrix, gold_signs, st.floats(min_value=0.01, max_value=5.0, allow_nan=False))
def test_equal_positive_weights_give_the_plain_result(
    votes: np.ndarray, gold: np.ndarray, w: float
) -> None:
    weights = np.full(votes.shape, w)
    assert (scored_vote_correct(votes, weights, gold) == plain_vote_correct(votes, gold)).all()


@settings(max_examples=100, deadline=None)
@given(vote_matrix, gold_signs)
def test_negative_weights_are_refused(votes: np.ndarray, gold: np.ndarray) -> None:
    weights = np.full(votes.shape, -0.1)
    try:
        scored_vote_correct(votes, weights, gold)
    except ValueError:
        return
    raise AssertionError("negative weights were accepted")


@settings(max_examples=100, deadline=None)
@given(
    st.lists(st.lists(st.sampled_from([0, 1]), min_size=16, max_size=16), min_size=1, max_size=9)
)
def test_weights_from_other_items_are_never_negative_and_come_from_the_table(
    rows: list[list[int]],
) -> None:
    correct = np.array(rows, dtype=int)
    feature_of_item = np.repeat(np.arange(4), 4)
    w = weights_from_other_items(correct, feature_of_item)
    assert w.shape == correct.shape
    assert (w >= 0).all()
    assert set(np.round(w, 6).ravel()) <= {round(x, 6) for x in WEIGHTS}
    # A person right on all four items of a feature has the top weight on each of them.
    for person in range(correct.shape[0]):
        for f in range(4):
            block = slice(4 * f, 4 * f + 4)
            if correct[person, block].sum() == 4:
                assert np.allclose(w[person, block], WEIGHTS[3])
            if correct[person, block].sum() == 0:
                assert np.allclose(w[person, block], WEIGHTS[0])


def test_weight_table_is_monotone_and_starts_at_zero() -> None:
    values = [weight_for_correct(c) for c in range(4)]
    assert values[0] == 0.0 and values[1] == 0.0
    assert values == sorted(values)
