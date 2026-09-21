"""The analysis follows docs/analysis_plan.md items 4 to 7 and 9 on synthetic data."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from core.lock import DATA_LOCK_UTC
from evals.common import SESSION_COLUMNS, SYNTHETIC_STAMP
from evals.make_synthetic_sessions import NO_EXTRAS, ExtraCounts, generate, simulate_accuracy
from evals.usability_analysis import (
    MIN_COMPLETED_PER_ARM,
    analyse,
    apply_exclusions,
    hedges_g,
    permutation_p,
    primary_estimate,
    run,
    tidy_responses,
    tidy_sessions,
)

Loader = Callable[[str], tuple[pd.DataFrame, pd.DataFrame]]

EXPECTED_RULES = [
    "started at or after the data lock",
    "did not finish all 16 items",
    "test finished in under 40 seconds",
    "repeat visit from the same browser token",
    "flagged as QA",
    "filled the hidden form field",
    "dry run before launch",
]


def test_exclusions_follow_the_plan_order_and_count_each_rule(loaded: Loader) -> None:
    sessions, responses = loaded("real_gain")
    excl = apply_exclusions(sessions, responses)
    extras = ExtraCounts()
    assert [s.order for s in excl.steps] == list(range(7))
    for step, prefix in zip(excl.steps, EXPECTED_RULES, strict=True):
        assert step.rule.startswith(prefix)
    assert [s.removed for s in excl.steps] == [
        extras.post_lock,
        extras.incomplete_no_answers + extras.incomplete_partial,
        extras.fast,
        extras.repeat_token,
        extras.qa,
        extras.hidden_field,
        0,
    ]
    assert excl.counts["analysed"] == {"untrained": 42, "trained": 42}
    assert excl.counts["completed_untrained"] == 42 and excl.counts["completed_trained"] == 42
    assert excl.counts["completed"]["untrained"] >= 42
    assert len(excl.kept) == 84
    randomized = excl.counts["randomized"]
    assert randomized["untrained"] + randomized["trained"] == len(sessions) - extras.post_lock
    for key in ("randomized", "started", "completed", "analysed"):
        assert set(excl.counts[key]) == {"untrained", "trained"}


def _session_row(**overrides: str) -> dict[str, str]:
    base = {
        "session_id": "s-a",
        "arm": "trained",
        "block_id": "0",
        "source_label": "chat",
        "ua_class": "phone",
        "consent_version": "v1",
        "content_hash": "c",
        "build_hash": "b",
        "started_at_utc": "2026-09-25T10:00:00Z",
        "lesson_seconds_total": "120",
        "completed_at_utc": "2026-09-25T10:05:00Z",
        "test_seconds": "100",
        "is_test": "false",
        "post_lock": "false",
        "hidden_field_filled": "false",
        "client_token_hash": "tok-a",
        "prior_experience": "no",
        "warmup_choice": "w02",
    }
    base.update(overrides)
    return base


def _responses_for(session_ids: list[str], n: int = 16) -> pd.DataFrame:
    rows = []
    for sid in session_ids:
        for i in range(n):
            rows.append(
                {
                    "session_id": sid,
                    "item_id": f"t{i + 1:02d}",
                    "feature": "artificial_bank",
                    "gold": "present",
                    "answer": "yes",
                    "correct": "1",
                    "rt_ms": "1000",
                    "position": str(i + 1),
                }
            )
    return tidy_responses(pd.DataFrame(rows))


def _sessions(rows: list[dict[str, str]]) -> pd.DataFrame:
    return tidy_sessions(pd.DataFrame(rows, columns=SESSION_COLUMNS))


def test_one_second_before_the_lock_is_kept_and_one_second_after_is_dropped() -> None:
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    before = (DATA_LOCK_UTC - timedelta(seconds=1)).strftime(fmt)
    after = (DATA_LOCK_UTC + timedelta(seconds=1)).strftime(fmt)
    sessions = _sessions(
        [
            _session_row(session_id="s-before", started_at_utc=before, client_token_hash="t1"),
            _session_row(session_id="s-after", started_at_utc=after, client_token_hash="t2"),
        ]
    )
    excl = apply_exclusions(sessions, _responses_for(["s-before", "s-after"]))
    assert list(excl.kept["session_id"]) == ["s-before"]
    assert excl.steps[0].removed == 1


def test_post_lock_flag_alone_drops_a_session() -> None:
    excl = apply_exclusions(_sessions([_session_row(post_lock="True")]), _responses_for(["s-a"]))
    assert excl.kept.empty and excl.steps[0].removed == 1


def test_repeat_token_keeps_only_the_first_completed_session() -> None:
    ids = ["s-late", "s-early", "s-empty-1", "s-empty-2"]
    rows = [
        _session_row(
            session_id=ids[0], completed_at_utc="2026-09-26T10:00:00Z", client_token_hash="same"
        ),
        _session_row(
            session_id=ids[1], completed_at_utc="2026-09-25T10:00:00Z", client_token_hash="same"
        ),
        _session_row(session_id=ids[2], client_token_hash=""),
        _session_row(session_id=ids[3], client_token_hash=""),
    ]
    excl = apply_exclusions(_sessions(rows), _responses_for(ids))
    assert set(excl.kept["session_id"]) == {"s-early", "s-empty-1", "s-empty-2"}
    assert excl.steps[3].removed == 1


def test_launch_time_drops_dry_runs() -> None:
    rows = [
        _session_row(
            session_id="s-dry", started_at_utc="2026-09-22T10:00:00Z", client_token_hash="a"
        ),
        _session_row(
            session_id="s-real", started_at_utc="2026-09-24T10:00:00Z", client_token_hash="b"
        ),
    ]
    excl = apply_exclusions(
        _sessions(rows),
        _responses_for(["s-dry", "s-real"]),
        launch_utc=datetime(2026, 9, 23, tzinfo=UTC),
    )
    assert list(excl.kept["session_id"]) == ["s-real"]
    assert excl.steps[6].removed == 1


def test_hedges_g_matches_a_hand_calculation() -> None:
    a = np.array([1.0, 2.0, 3.0, 4.0])
    b = np.array([2.0, 3.0, 4.0, 5.0])
    # means 2.5 and 3.5, pooled variance 5/3, J = 1 - 3 / (4 * 8 - 9)
    expected = (1 - 3 / 23) * (-1.0) / np.sqrt(5 / 3)
    assert hedges_g(a, b) == pytest.approx(expected, abs=1e-9)
    assert hedges_g(a, a) == pytest.approx(0.0)
    assert hedges_g(np.array([1.0]), b) is None


def test_permutation_p_is_one_when_the_arms_are_identical() -> None:
    x = np.array([0.5, 0.6, 0.7, 0.8, 0.9])
    assert permutation_p(x, x.copy(), n_perm=200, rng=np.random.default_rng(1)) == pytest.approx(
        1.0
    )


def test_below_twenty_per_arm_is_descriptive() -> None:
    rng = np.random.default_rng(3)
    small = primary_estimate(rng.random(19), rng.random(30), n_boot=200, n_perm=200)
    assert small["status"] == "descriptive"
    enough = primary_estimate(
        rng.random(MIN_COMPLETED_PER_ARM), rng.random(20), n_boot=200, n_perm=200
    )
    assert enough["status"] == "confirmatory"
    empty = primary_estimate(np.array([]), rng.random(20), n_boot=200, n_perm=200)
    assert empty["difference_points"] is None and empty["difference"] is None


def test_readme_facing_keys_are_percentages_with_one_decimal() -> None:
    trained = np.array([12, 14, 10, 13]) / 16
    untrained = np.array([9, 10, 11, 8]) / 16
    est = primary_estimate(trained, untrained, n_boot=200, n_perm=200)
    assert est["trained_mean"] == round(trained.mean() * 100, 1)
    assert est["untrained_mean"] == round(untrained.mean() * 100, 1)
    assert est["difference"] == round((trained.mean() - untrained.mean()) * 100, 1)
    assert est["ci_low"] <= est["difference"] <= est["ci_high"]
    assert (
        est["ci_low"] == est["ci95_points"][0] or abs(est["ci_low"] - est["ci95_points"][0]) < 0.06
    )


def test_real_gain_is_recovered_inside_its_interval(loaded: Loader) -> None:
    sessions, responses = loaded("real_gain")
    result = analyse(sessions, responses, n_boot=2000, n_perm=2000)
    lo, hi = result["primary"]["ci95_points"]
    assert lo < 10.0 < hi, result["primary"]
    assert result["primary"]["difference_points"] > 0
    covered = 0
    for seed in range(20):
        untrained, trained = simulate_accuracy("real_gain", 40, seed=100 + seed)
        est = primary_estimate(trained, untrained, n_boot=400, n_perm=100)
        lo, hi = est["ci95_points"]
        covered += int(lo <= 10.0 <= hi)
    assert covered >= 17, f"the interval covered the planted 10 points in {covered} of 20 seeds"


def test_no_effect_rejects_about_five_percent_of_the_time() -> None:
    seeds = range(300)
    rejections = 0
    for seed in seeds:
        untrained, trained = simulate_accuracy("no_effect", 40, seed=seed)
        est = primary_estimate(trained, untrained, n_boot=20, n_perm=400, seed=seed)
        rejections += int(est["rejects_at_alpha_05"])
    rate = rejections / len(seeds)
    assert 0.01 <= rate <= 0.09, f"no-effect data rejected in {rate:.3f} of {len(seeds)} seeds"


def test_yes_bias_shows_no_gain(loaded: Loader) -> None:
    sessions, responses = loaded("yes_bias")
    result = analyse(sessions, responses, n_boot=2000, n_perm=2000)
    primary = result["primary"]
    assert primary["difference_points"] < 3.0, primary
    assert not primary["rejects_at_alpha_05"] or primary["difference_points"] < 0
    assert result["yes_share"]["trained"] - result["yes_share"]["untrained"] > 0.05
    estimates = []
    for seed in range(10):
        untrained, trained = simulate_accuracy("yes_bias", 60, seed=500 + seed)
        estimates.append(trained.mean() - untrained.mean())
    assert float(np.mean(estimates)) < 0.02


def test_descriptives_cover_every_plan_item(loaded: Loader) -> None:
    sessions, responses = loaded("real_gain")
    result = analyse(sessions, responses, n_boot=200, n_perm=200)
    features = {"artificial_bank", "dug_out_channel", "invasive_plant", "pipe_running"}
    assert set(result["per_feature"]) == features
    for row in result["per_feature"].values():
        for arm in ("untrained", "trained"):
            assert {
                "accuracy",
                "hit_rate",
                "false_alarm_rate",
                "cant_tell_share",
                "n_answers",
            } <= set(row[arm])
            assert 0 <= row[arm]["hit_rate"] <= 1 and 0 <= row[arm]["false_alarm_rate"] <= 1
    assert len(result["per_item"]) == 16
    assert set(result["cant_tell_share"]) == {"untrained", "trained"}
    assert result["median_times"]["test_seconds"]["trained"]["median"] >= 40
    assert result["median_times"]["lesson_seconds"]["trained"]["n"] == 42
    assert set(result["by_source"]) <= {
        "poster",
        "chat",
        "friends",
        "creek_group",
        "other",
        "unknown",
    }
    assert sum(sum(v.values()) for v in result["by_source"].values()) == 84
    assert set(result["by_prior_experience"]) <= {"yes", "no", "not_answered"}
    assert set(result["by_device"]) <= {"phone", "desktop", "tablet", "unknown"}
    assert abs(sum(v["share"] for v in result["warmup"].values()) - 1.0) < 1e-9
    sens = result["sensitivity"]
    partial = sens["partial_completers_scored_wrong"]
    assert partial["n_trained"] + partial["n_untrained"] > 84
    assert sens["without_prior_experience"]["removed_for_prior_experience"] > 0
    assert sum(result["score_distribution"]["trained"]) == 42


def test_correct_column_is_recomputed_not_trusted(loaded: Loader) -> None:
    sessions, responses = loaded("no_effect")
    tampered = responses.copy()
    tampered["correct_export"] = 1
    result = analyse(sessions, tampered, n_boot=100, n_perm=100)
    assert result["data_quality"]["correct_column_mismatches"] > 0
    untampered = analyse(sessions, responses, n_boot=100, n_perm=100)
    assert result["primary"]["difference_points"] == untampered["primary"]["difference_points"]


def test_outputs_are_stamped_synthetic(synthetic_root: Path, tmp_path: Path) -> None:
    result = run(
        input_dir=synthetic_root / "no_effect",
        out_dir=tmp_path,
        synthetic=True,
        stamp_name="synthetic",
        scenario="no_effect",
        when=datetime(2026, 9, 20, tzinfo=UTC),
        n_boot=200,
        n_perm=200,
    )
    doc = json.loads((tmp_path / "usability_synthetic.json").read_text())
    for key in ("generated_at_utc", "script", "synthetic", "stamp"):
        assert key in doc
    assert doc["synthetic"] is True and doc["stamp"] == SYNTHETIC_STAMP
    assert doc["chart_title"].startswith(SYNTHETIC_STAMP)
    assert result["chart_title"].startswith("SYNTHETIC")
    for pointer in ("untrained_mean", "trained_mean", "difference", "ci_low", "ci_high"):
        assert isinstance(doc["primary"][pointer], float)
    assert isinstance(doc["counts"]["completed_untrained"], int)
    assert (tmp_path / "usability_synthetic.png").stat().st_size > 1000
    md = (tmp_path / "usability_synthetic.md").read_text()
    assert md.startswith("# SYNTHETIC")
    assert "Primary estimate" in md and "| 1 | did not finish all 16 items |" in md


def test_generate_without_extras_keeps_everyone() -> None:
    sessions, responses = generate("equal_skill", n_per_arm=10, extras=NO_EXTRAS)
    excl = apply_exclusions(
        tidy_sessions(sessions.astype(str)), tidy_responses(responses.astype(str))
    )
    assert len(excl.kept) == 20
    assert all(step.removed == 0 for step in excl.steps)
