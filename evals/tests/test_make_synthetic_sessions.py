"""The synthetic export matches the CONTRACTS schema and plants every exclusion case."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.lock import DATA_LOCK_UTC
from evals.common import N_ITEMS, RESPONSE_COLUMNS, SESSION_COLUMNS, parse_utc
from evals.make_synthetic_sessions import NO_EXTRAS, SCENARIOS, ExtraCounts, generate, main


def test_every_scenario_has_the_export_columns_in_order() -> None:
    for scenario in SCENARIOS:
        sessions, responses = generate(scenario, n_per_arm=8)
        assert list(sessions.columns) == SESSION_COLUMNS
        assert list(responses.columns) == RESPONSE_COLUMNS


def test_same_seed_gives_the_same_data() -> None:
    a_s, a_r = generate("real_gain", seed=7, n_per_arm=8)
    b_s, b_r = generate("real_gain", seed=7, n_per_arm=8)
    pd.testing.assert_frame_equal(a_s, b_s)
    pd.testing.assert_frame_equal(a_r, b_r)
    c_s, _ = generate("real_gain", seed=8, n_per_arm=8)
    assert not a_s["session_id"].equals(c_s["session_id"])


def test_exclusion_cases_are_planted() -> None:
    extras = ExtraCounts()
    sessions, responses = generate("no_effect", n_per_arm=30, extras=extras)
    answered = responses.groupby("session_id").size()
    n_answered = sessions["session_id"].map(answered).fillna(0)
    assert int(sessions["post_lock"].sum()) == extras.post_lock
    assert int(sessions["is_test"].sum()) == extras.qa
    assert int(sessions["hidden_field_filled"].sum()) == extras.hidden_field
    assert int((n_answered == 0).sum()) == extras.incomplete_no_answers
    assert int(((n_answered > 0) & (n_answered < N_ITEMS)).sum()) == extras.incomplete_partial
    fast = pd.to_numeric(sessions["test_seconds"], errors="coerce") < 40
    assert int(fast.sum()) == extras.fast
    assert int(sessions["client_token_hash"].duplicated().sum()) == extras.repeat_token
    late = sessions.loc[sessions["post_lock"], "started_at_utc"].map(parse_utc)
    assert bool((late >= DATA_LOCK_UTC).all())
    early = sessions.loc[~sessions["post_lock"], "started_at_utc"].map(parse_utc)
    assert bool((early < DATA_LOCK_UTC).all())


def test_completed_sessions_have_sixteen_distinct_items_and_a_consistent_correct_column() -> None:
    sessions, responses = generate("real_gain", n_per_arm=20)
    completed = sessions[sessions["completed_at_utc"] != ""]
    per_session = responses[responses["session_id"].isin(completed["session_id"])]
    counts = per_session.groupby("session_id")["item_id"].nunique()
    assert bool((counts == N_ITEMS).all())
    assert set(counts.index) == set(completed["session_id"])
    expected = (
        ((responses["answer"] == "yes") & (responses["gold"] == "present"))
        | ((responses["answer"] == "no") & (responses["gold"] == "absent"))
    ).astype(int)
    assert bool((responses["correct"] == expected).all())
    assert set(responses["answer"]) <= {"yes", "no", "cant_tell"}
    assert set(responses["position"]) <= set(range(1, N_ITEMS + 1))


def test_arms_are_balanced_inside_every_full_block() -> None:
    sessions, _ = generate("no_effect", n_per_arm=25)
    sizes = sessions.groupby("block_id").size()
    for block in sizes[sizes == 4].index:
        arms = sessions.loc[sessions["block_id"] == block, "arm"].value_counts()
        assert arms.get("trained", 0) == 2 and arms.get("untrained", 0) == 2


def test_real_gain_and_yes_bias_move_the_intended_things() -> None:
    gain_s, gain_r = generate("real_gain", n_per_arm=60, extras=NO_EXTRAS)
    merged = gain_r.merge(gain_s[["session_id", "arm"]])
    acc = merged.groupby("arm")["correct"].mean()
    assert acc["trained"] - acc["untrained"] > 0.05

    bias_s, bias_r = generate("yes_bias", n_per_arm=60, extras=NO_EXTRAS)
    merged = bias_r.merge(bias_s[["session_id", "arm"]])
    yes = merged.assign(yes=merged["answer"] == "yes").groupby("arm")["yes"].mean()
    assert yes["trained"] - yes["untrained"] > 0.05


def test_cli_writes_one_folder_per_scenario(tmp_path: Path) -> None:
    assert main(["--out", str(tmp_path), "--n-per-arm", "6"]) == 0
    for scenario in SCENARIOS:
        assert (tmp_path / scenario / "sessions.csv").exists()
        assert (tmp_path / scenario / "responses.csv").exists()
        assert "SYNTHETIC" in (tmp_path / scenario / "SYNTHETIC.txt").read_text()
