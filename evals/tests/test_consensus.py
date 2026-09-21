"""Plan item 11: plain and scored votes, the fixed weights, ties as wrong, and the two scenarios."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from evals.consensus import (
    GROUP_SIZES,
    WEIGHTS,
    build_matrices,
    main,
    plain_vote_correct,
    run_consensus,
    scored_vote_correct,
    weight_for_correct,
    weights_from_other_items,
)
from evals.usability_analysis import apply_exclusions

Loader = Callable[[str], tuple[pd.DataFrame, pd.DataFrame]]


def test_weights_are_0_0_051_and_195() -> None:
    assert [round(w, 2) for w in WEIGHTS] == [0.0, 0.0, 0.51, 1.95]
    assert [round(weight_for_correct(c), 2) for c in range(4)] == [0.0, 0.0, 0.51, 1.95]
    assert all(w >= 0 for w in WEIGHTS)


def test_a_tie_counts_as_wrong_for_both_methods() -> None:
    votes = np.array([[1, 1, 0], [-1, 0, 0]])  # two people, three items
    gold = np.array([1, 1, 1])
    assert plain_vote_correct(votes, gold).tolist() == [False, True, False]
    weights = np.ones_like(votes, dtype=float)
    assert scored_vote_correct(votes, weights, gold).tolist() == [False, True, False]
    # Weighted sum that lands exactly on zero is also wrong.
    votes = np.array([[1], [-1]])
    weights = np.array([[0.51], [0.51]])
    assert scored_vote_correct(votes, weights, np.array([1])).tolist() == [False]
    # A single Can't tell is a zero sum, so wrong.
    assert plain_vote_correct(np.array([[0]]), np.array([-1])).tolist() == [False]


def test_weights_come_only_from_the_other_three_items_of_the_feature() -> None:
    feature_of_item = np.repeat(np.arange(4), 4)
    correct = np.zeros((2, 16), dtype=int)
    correct[0, :4] = 1  # person 0 right on every artificial_bank item
    correct[1, :3] = 1  # person 1 right on three of four
    w = weights_from_other_items(correct, feature_of_item)
    assert np.allclose(w[0, :4], WEIGHTS[3])
    assert np.allclose(w[0, 4:], WEIGHTS[0])
    assert np.allclose(w[1, :3], WEIGHTS[2])  # the other three: two right
    assert np.isclose(w[1, 3], WEIGHTS[3])  # the wrong item: the other three all right
    assert (w >= 0).all()


def test_matrices_line_up_with_gold(loaded: Loader) -> None:
    sessions, responses = loaded("equal_skill")
    kept = apply_exclusions(sessions, responses).kept
    mats = build_matrices(kept, responses)
    for arm in ("untrained", "trained"):
        votes, correct = mats[arm]["votes"], mats[arm]["correct"]
        assert votes.shape == (42, 16) and correct.shape == (42, 16)
        assert set(np.unique(votes)) <= {-1, 0, 1}
        assert ((votes == mats[arm]["gold_sign"][None, :]) == correct.astype(bool)).all()


def test_scored_beats_plain_when_skill_varies(loaded: Loader) -> None:
    sessions, responses = loaded("skill_spread")
    result = run_consensus(sessions, responses, n_draws=600)
    gains = []
    for arm in ("untrained", "trained"):
        for size in GROUP_SIZES:
            row = result["arms"][arm]["by_size"][str(size)]
            gain = row["scored_minus_plain_mean"]
            assert gain > 0, f"{arm} size {size}: scored {row['scored']} plain {row['plain']}"
            gains.append(gain)
    assert float(np.mean(gains)) >= 0.03


def test_scores_give_no_gain_when_skill_is_equal(loaded: Loader) -> None:
    sessions, responses = loaded("equal_skill")
    result = run_consensus(sessions, responses, n_draws=600)
    for arm in ("untrained", "trained"):
        for size in GROUP_SIZES:
            row = result["arms"][arm]["by_size"][str(size)]
            assert row["scored_minus_plain_mean"] <= 0.02, f"{arm} size {size}: {row}"
            band_lo, band_hi = row["plain"]["p2_5"], row["plain"]["p97_5"]
            assert band_lo <= row["scored"]["mean_share_right"] <= band_hi, (
                f"{arm} size {size}: {row}"
            )


def test_small_arms_skip_group_sizes_they_cannot_fill(loaded: Loader) -> None:
    sessions, responses = loaded("no_effect")
    kept = apply_exclusions(sessions, responses).kept
    few = kept.groupby("arm").head(4)
    result = run_consensus(
        sessions[sessions["session_id"].isin(few["session_id"])], responses, n_draws=50
    )
    by_size = result["arms"]["trained"]["by_size"]
    assert "skipped" not in by_size["3"]
    assert "skipped" in by_size["5"] and "skipped" in by_size["7"]
    assert result["summary"]["trained_plain_size5"] is None


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
        ]
    )
    assert code == 0
    doc = json.loads((tmp_path / "consensus_synthetic.json").read_text())
    assert doc["stamp"] == "SYNTHETIC" and doc["synthetic"] is True
    assert doc["scenario"] == "skill_spread"
    assert doc["chart_title"].startswith("SYNTHETIC")
    assert doc["plan"]["weights_by_correct_of_other_three"] == [0.0, 0.0, 0.5108, 1.9459]
    assert set(doc["arms"]["trained"]["by_size"]) == {"3", "5", "7"}
    assert isinstance(doc["summary"]["trained_scored_size5"], float)
    assert (tmp_path / "consensus_synthetic.png").stat().st_size > 1000
