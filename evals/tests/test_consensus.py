"""Plan item 11: split the items, pass a half, vote on the other half, fall back to everyone."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from evals.common import ITEMS_PER_FEATURE, PLAN_SEED, load_test_items
from evals.consensus import (
    GOLD_SIGN,
    HALF_ITEMS,
    build_matrices,
    consensus_for_arm,
    decide_items,
    draw_groups,
    main,
    run_consensus,
    split_items,
)
from evals.usability_analysis import apply_exclusions

Loader = Callable[[str], tuple[pd.DataFrame, pd.DataFrame]]

ITEMS = load_test_items()
GOLD = np.array([GOLD_SIGN[row["gold"]] for row in ITEMS])
FEATURES = sorted({row["feature"] for row in ITEMS})
FEATURE_OF_ITEM = np.array([FEATURES.index(row["feature"]) for row in ITEMS])
N_PEOPLE = 42


def arm_matrices(votes: np.ndarray) -> dict[str, np.ndarray]:
    """The shape consensus_for_arm wants, built from a votes table alone."""
    return {
        "votes": votes,
        "correct": (votes == GOLD[None, :]).astype(int),
        "gold_sign": GOLD,
        "feature_of_item": FEATURE_OF_ITEM,
    }


def votes_from_accuracy(accuracy: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Each person answers each item right with their own chance, and never says Can't tell."""
    right = rng.random((len(accuracy), len(GOLD))) < accuracy[:, None]
    return np.where(right, GOLD[None, :], -GOLD[None, :])


def run_arm(votes: np.ndarray, *, n_splits: int = 40, n_draws: int = 400) -> dict:
    return consensus_for_arm(
        arm_matrices(votes),
        n_splits=n_splits,
        n_draws=n_draws,
        rng=np.random.default_rng(PLAN_SEED),
    )


# ---------------------------------------------------------------------------
# The three cases the brief names
# ---------------------------------------------------------------------------


def test_the_filter_helps_when_a_third_of_people_answer_at_random() -> None:
    rng = np.random.default_rng(PLAN_SEED)
    accuracy = np.full(N_PEOPLE, 0.85)
    accuracy[::3] = 0.5  # one person in three taps at random
    result = run_arm(votes_from_accuracy(accuracy, rng))
    gain = result["passers_minus_everyone_mean"]
    print(
        f"a third at random: everyone {result['everyone']['mean_share_right']:.3f}, "
        f"passers only {result['passers_only']['mean_share_right']:.3f}, gain {gain:+.3f}, "
        f"people passing a half {result['share_of_people_passing_a_half']:.3f}"
    )
    # At the plan's own resolution (200 splits, 2,000 draws) this gain is about +0.007. It is
    # real and it is small, which is the whole point: the filter is worth reporting and is not
    # worth putting in a headline.
    assert gain > 0, result
    assert result["passers_only"]["mean_share_right"] > result["everyone"]["mean_share_right"]


def test_the_filter_does_not_help_when_skill_is_equal() -> None:
    rng = np.random.default_rng(PLAN_SEED)
    accuracy = np.full(N_PEOPLE, 0.70)
    result = run_arm(votes_from_accuracy(accuracy, rng))
    gain = result["passers_minus_everyone_mean"]
    print(
        f"equal skill: everyone {result['everyone']['mean_share_right']:.3f}, "
        f"passers only {result['passers_only']['mean_share_right']:.3f}, gain {gain:+.3f}, "
        f"people passing a half {result['share_of_people_passing_a_half']:.3f}"
    )
    # With equal skill the filter does not merely fail to help, it hurts: it throws away good
    # votes for no reason. About -0.045 at the plan's resolution.
    assert gain < 0, result
    assert result["passers_only"]["mean_share_right"] < result["everyone"]["mean_share_right"]


def test_the_group_falls_back_to_everyone_when_nobody_passes() -> None:
    # Each person is right on one item of each feature, so a half holds at most 4 of their
    # 8 correct answers and nobody ever reaches the pass mark of 6.
    votes = -np.tile(GOLD, (N_PEOPLE, 1))
    for person in range(N_PEOPLE):
        for feature in range(len(FEATURES)):
            idx = np.flatnonzero(FEATURE_OF_ITEM == feature)
            votes[person, idx[(person + feature) % ITEMS_PER_FEATURE]] *= -1
    result = run_arm(votes)
    print(
        f"nobody passes: everyone {result['everyone']['mean_share_right']:.3f}, "
        f"passers only {result['passers_only']['mean_share_right']:.3f}, "
        f"groups with no passer {result['share_of_groups_with_no_passer']:.3f}, "
        f"items sent back {result['share_of_items_sent_back_to_everyone']:.3f}"
    )
    assert result["share_of_people_passing_a_half"] == 0.0
    assert result["share_of_groups_with_no_passer"] == 1.0
    assert result["share_of_items_sent_back_to_everyone"] == 1.0
    assert result["passers_minus_everyone_mean"] == 0.0
    assert result["passers_only"] == result["everyone"]


# ---------------------------------------------------------------------------
# The parts the three cases rest on
# ---------------------------------------------------------------------------


def test_every_split_puts_two_items_of_each_feature_in_each_half() -> None:
    rng = np.random.default_rng(PLAN_SEED)
    seen = set()
    for _ in range(50):
        score, vote = split_items(FEATURE_OF_ITEM, rng)
        assert len(score) == HALF_ITEMS and len(vote) == HALF_ITEMS
        assert set(score).isdisjoint(vote)
        assert sorted([*score, *vote]) == list(range(len(GOLD)))
        for feature in range(len(FEATURES)):
            assert (FEATURE_OF_ITEM[score] == feature).sum() == ITEMS_PER_FEATURE // 2
            assert (FEATURE_OF_ITEM[vote] == feature).sum() == ITEMS_PER_FEATURE // 2
        seen.add(tuple(score))
    assert len(seen) > 1, "the split never changes, so it is not random"


def test_a_tie_among_the_passers_sends_the_item_back_to_everyone() -> None:
    # Two passers disagree on item 0, so everyone decides it. On item 1 the passers agree.
    votes = np.array([[[1, 1], [-1, 1], [-1, -1]]])  # one draw, three people, two items
    passed = np.array([[True, True, False]])
    gold = np.array([-1, 1])
    out = decide_items(votes, passed, gold)
    assert out["fell_back"].tolist() == [[True, False]]
    assert out["passers_right"].tolist() == [[True, True]]  # everyone says -1 on item 0
    assert out["everyone_right"].tolist() == [[True, True]]


def test_a_tie_among_everyone_is_a_wrong_answer() -> None:
    votes = np.array([[[1], [-1]]])  # one draw, two people, one item
    passed = np.array([[False, False]])
    out = decide_items(votes, passed, np.array([1]))
    assert out["everyone_right"].tolist() == [[False]]
    assert out["passers_right"].tolist() == [[False]]
    assert out["has_passer"].tolist() == [False]


def test_groups_hold_distinct_people() -> None:
    rng = np.random.default_rng(PLAN_SEED)
    groups = draw_groups(12, 5, 200, rng)
    assert groups.shape == (200, 5)
    assert all(len(set(row.tolist())) == 5 for row in groups)
    assert groups.min() >= 0 and groups.max() < 12


def test_matrices_line_up_with_gold(loaded: Loader) -> None:
    sessions, responses = loaded("equal_skill")
    kept = apply_exclusions(sessions, responses).kept
    mats = build_matrices(kept, responses)
    for arm in ("untrained", "trained"):
        votes, correct = mats[arm]["votes"], mats[arm]["correct"]
        assert votes.shape == (42, 16) and correct.shape == (42, 16)
        assert set(np.unique(votes)) <= {-1, 0, 1}
        assert ((votes == mats[arm]["gold_sign"][None, :]) == correct.astype(bool)).all()


def test_an_arm_too_small_for_a_group_is_skipped(loaded: Loader) -> None:
    sessions, responses = loaded("no_effect")
    kept = apply_exclusions(sessions, responses).kept
    few = kept.groupby("arm").head(4)
    result = run_consensus(
        sessions[sessions["session_id"].isin(few["session_id"])],
        responses,
        n_splits=5,
        n_draws=20,
    )
    assert "skipped" in result["arms"]["trained"]
    assert result["summary"]["trained_everyone"] is None


def test_cli_writes_stamped_outputs(synthetic_root: Path, tmp_path: Path) -> None:
    code = main(
        [
            "--synthetic",
            "--input",
            str(synthetic_root / "skill_spread"),
            "--out-dir",
            str(tmp_path),
            "--draws",
            "100",
            "--splits",
            "10",
        ]
    )
    assert code == 0
    doc = json.loads((tmp_path / "consensus_synthetic.json").read_text())
    assert doc["stamp"] == "SYNTHETIC" and doc["synthetic"] is True
    assert doc["scenario"] == "skill_spread"
    assert doc["chart_title"].startswith("SYNTHETIC")
    assert doc["plan"]["pass_mark_of_8"] == 6
    assert doc["plan"]["group_size"] == 5
    assert doc["plan"]["seed"] == PLAN_SEED
    assert isinstance(doc["summary"]["trained_passers_only"], float)
    assert isinstance(doc["arms"]["trained"]["share_of_groups_with_no_passer"], float)
    assert (tmp_path / "consensus_synthetic.png").stat().st_size > 1000
