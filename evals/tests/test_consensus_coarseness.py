"""The consensus coarseness simulation (UPDATE_22 section 1 answer 1).

Weight formulas, the tie rule, the passers fall back, the halves, the skill patterns,
determinism, and that the committed files are what the script writes. The full reproduction of
results/consensus_coarseness.json takes about 15 seconds, so it runs once in `make check` as
`make consensus-check`. Here the same --check path runs on a small run, and the committed files
are checked against the script's settings and against each other.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from evals import consensus_coarseness as cc
from evals.common import RESULTS_DIR

LN5 = math.log(5)
M = {name: i for i, name in enumerate(cc.METHODS)}
SCORE = np.array([[0, 1, 4, 5, 8, 9, 12, 13]])
VOTE = np.array([[2, 3, 6, 7, 10, 11, 14, 15]])
COMMITTED_JSON = RESULTS_DIR / "consensus_coarseness.json"
COMMITTED_MD = RESULTS_DIR / "consensus_coarseness.md"


# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------


def test_logit_at_the_three_feature_rates() -> None:
    assert float(cc.logit(1 / 6)) == pytest.approx(-LN5)
    assert float(cc.logit(1 / 2)) == 0.0
    assert float(cc.logit(5 / 6)) == pytest.approx(LN5)


def test_feature_only_weight_at_c_0_1_2() -> None:
    w = cc.feature_weight(np.array([0, 1, 2]))
    assert w[0] == 0.0, "max(0, logit(1/6)) is 0 because logit(1/6) = -ln 5"
    assert w[1] == 0.0, "max(0, logit(1/2)) is 0"
    assert w[2] == pytest.approx(LN5), "max(0, logit(5/6)) is ln 5"


def test_shrunk_weight_formula() -> None:
    # c = 2, C = 8: r = 8.5 / 9.
    # k = 3: p = (2.5 + 3 r) / 6 = 8/9. k = 6: p = (2.5 + 6 r) / 9 = 49/54.
    assert float(cc.shrunk_weight(2, 8, 3)) == pytest.approx(math.log(8))
    assert float(cc.shrunk_weight(2, 8, 6)) == pytest.approx(math.log(49 / 5))
    # c = 0, C = 6: r = 6.5 / 9. k = 6 gives p = 29/54, a small weight where feature only gives 0.
    assert float(cc.shrunk_weight(0, 6, 6)) == pytest.approx(math.log(29 / 25))
    assert float(cc.shrunk_weight(0, 6, 3)) == 0.0, "p = 4/9 is under a half"
    # c = 1, C = 4: r = 1/2, so p = 1/2 for any k.
    assert float(cc.shrunk_weight(1, 4, 3)) == 0.0
    assert float(cc.shrunk_weight(1, 4, 6)) == 0.0


def test_overall_only_weight() -> None:
    w = cc.overall_weight(np.arange(9))
    assert (w[:5] == 0.0).all(), "4 or fewer of 8 gives (C + 0.5) / 9 <= 1/2"
    assert w[5] == pytest.approx(math.log(5.5 / 3.5))
    assert w[8] == pytest.approx(math.log(17))


def test_method_weights_stack_every_method_in_order() -> None:
    c = np.array([[0, 1, 2, 2], [2, 2, 2, 0]])
    big_c = c.sum(axis=-1)
    w = cc.method_weights(c, big_c)
    per = np.broadcast_to(big_c[:, None], c.shape)
    assert w.shape == (len(cc.METHODS), 2, 4)
    assert (w[M["plain"]] == 1.0).all()
    assert np.allclose(w[M["feature_only"]], cc.feature_weight(c))
    assert np.allclose(w[M["shrunk_k3"]], cc.shrunk_weight(c, per, 3))
    assert np.allclose(w[M["shrunk_k6"]], cc.shrunk_weight(c, per, 6))
    assert np.allclose(w[M["overall_only"]], cc.overall_weight(per))
    assert (w[M["passers_only"]] == (per >= 6)).all()


# ---------------------------------------------------------------------------
# Ties and the passers fall back
# ---------------------------------------------------------------------------


def sums_of(**by_method: float) -> np.ndarray:
    """One group, one item: a (1, methods, 1) table of sums, zero unless named."""
    out = np.zeros((1, len(cc.METHODS), 1))
    for name, value in by_method.items():
        out[0, M[name], 0] = value
    return out


def test_a_tie_counts_as_wrong_for_every_method() -> None:
    right = cc.decide_items(sums_of())
    assert not right.any(), "a sum of exactly zero is wrong for every method"


def test_rounding_cannot_turn_a_tie_into_a_win() -> None:
    tiny = 0.1 + 0.2 - 0.3
    assert tiny > 0, "the point of this test: floating point leaves a crumb"
    right = cc.decide_items(sums_of(feature_only=tiny, overall_only=tiny, plain=1))
    assert not right[0, M["feature_only"], 0]
    assert not right[0, M["overall_only"], 0]
    assert right[0, M["plain"], 0]


def test_passers_fall_back_to_everyone_when_nobody_passed_or_they_tie() -> None:
    # Nobody passed and a passers tie both leave the passers' sum at zero.
    assert cc.decide_items(sums_of(passers_only=0, plain=1))[0, M["passers_only"], 0]
    assert not cc.decide_items(sums_of(passers_only=0, plain=-1))[0, M["passers_only"], 0]
    assert not cc.decide_items(sums_of(passers_only=0, plain=0))[0, M["passers_only"], 0]


def test_passers_decide_when_they_do_not_tie() -> None:
    assert cc.decide_items(sums_of(passers_only=1, plain=-3))[0, M["passers_only"], 0]
    assert not cc.decide_items(sums_of(passers_only=-1, plain=3))[0, M["passers_only"], 0]


def three_people() -> np.ndarray:
    """Two people perfect on the score half, one wrong on all of it. Only vote item 2 is voted
    right, by person 0 and person 2; everyone is wrong on the other seven voted items."""
    correct = np.zeros((3, 16), dtype=bool)
    correct[0, SCORE[0]] = True
    correct[1, SCORE[0]] = True
    correct[0, 2] = True
    correct[2, 2] = True
    return correct


def test_a_weighted_tie_in_a_real_group_is_wrong_and_passers_fall_back() -> None:
    contrib, passed = cc.vote_contributions(three_people(), SCORE, VOTE)
    assert passed.tolist() == [[True, True, False]]
    tally = cc.tally_groups(contrib, passed, np.array([[[0, 1, 2]]]))
    # Item 2: person 0 (+w) and person 1 (-w) have the same weight in every weighted method and
    # person 2 weighs 0, so every weighted sum is ln 5 - ln 5 or the like: a tie, so wrong. Plain
    # majority is 2 to 1, right. The passers (0 and 1) tie, so passers only falls back to plain.
    assert tally.right.tolist() == [1, 0, 0, 0, 0, 1]
    assert tally.tied.tolist() == [0, 1, 1, 1, 1, 0]
    assert tally.sent_back == 1
    assert tally.items == 8
    assert tally.groups_without_passer == 0


def test_an_even_split_is_wrong_for_plain_and_for_the_fall_back() -> None:
    contrib, passed = cc.vote_contributions(three_people(), SCORE, VOTE)
    tally = cc.tally_groups(contrib, passed, np.array([[[0, 1]]]))
    assert tally.right[M["plain"]] == 0
    assert tally.right[M["passers_only"]] == 0
    assert tally.tied[M["plain"]] == 1
    assert tally.tied[M["passers_only"]] == 1


def test_nobody_passed_means_passers_only_is_plain_majority() -> None:
    rng = np.random.default_rng(7)
    correct = rng.random((cc.N_PEOPLE, 16)) < 0.7
    correct[:, SCORE[0][5:]] = False  # at most 5 of the 8 scoring items right: nobody passes
    contrib, passed = cc.vote_contributions(correct, SCORE, VOTE)
    assert not passed.any()
    tally = cc.tally_groups(contrib, passed, cc.draw_groups(1, 200, 5, rng))
    assert tally.right[M["passers_only"]] == tally.right[M["plain"]]
    assert tally.groups_without_passer == tally.groups == 200
    assert tally.sent_back == tally.items


# ---------------------------------------------------------------------------
# Halves, groups and skills
# ---------------------------------------------------------------------------


def test_every_half_holds_two_items_of_each_feature() -> None:
    half_a, half_b = cc.split_halves(500, np.random.default_rng(1))
    assert half_a.shape == half_b.shape == (500, 8)
    position_feature = np.arange(8) // 2
    for a, b in zip(half_a, half_b, strict=True):
        assert sorted(a.tolist() + b.tolist()) == list(range(16)), "halves are disjoint and full"
        assert (a // 4 == position_feature).all() and (b // 4 == position_feature).all()
    assert len({tuple(a) for a in half_a.tolist()}) > 100, "the splits are random"
    score, vote = cc.score_vote_pairs(half_a, half_b)
    assert (score[:500] == half_a).all() and (vote[:500] == half_b).all()
    assert (score[500:] == half_b).all() and (vote[500:] == half_a).all()


def test_groups_have_no_repeats() -> None:
    groups = cc.draw_groups(4, 300, 7, np.random.default_rng(2))
    assert groups.shape == (4, 300, 7)
    assert all(len(set(g)) == 7 for g in groups.reshape(-1, 7).tolist())
    assert groups.min() >= 0 and groups.max() < cc.N_PEOPLE


def test_skill_patterns() -> None:
    rng = np.random.default_rng(3)
    skills = {p: cc.draw_skills(p, rng) for p in cc.PATTERNS}
    for s in skills.values():
        assert s.shape == (40, 4) and s.min() >= 0.50 and s.max() <= 0.95
    assert (skills["equal"] == 0.70).all()
    for p in ("normal_per_person", "uniform_per_person", "third_at_chance"):
        assert (skills[p] == skills[p][:, :1]).all(), f"{p} is one skill per person"
    assert not (
        skills["uniform_per_person_and_feature"] == skills["uniform_per_person_and_feature"][:, :1]
    ).all()
    assert cc.AT_CHANCE_COUNT == 13
    assert (skills["third_at_chance"][:13] == 0.50).all()
    assert (skills["third_at_chance"][13:] > 0.50).all()
    with pytest.raises(ValueError):
        cc.draw_skills("nobody", rng)


# ---------------------------------------------------------------------------
# Determinism and the committed files
# ---------------------------------------------------------------------------


def small_run(seed: int = cc.SEED) -> dict:
    return cc.run_simulation(seed=seed, n_populations=4, n_splits=2, n_groups=10)


def test_the_seed_fixes_the_result() -> None:
    assert cc.SEED == 20260921
    assert small_run() == small_run()
    assert small_run() != small_run(seed=cc.SEED + 1)


SMALL = ["--populations", "3", "--splits", "2", "--groups", "8"]


def test_check_passes_on_what_the_script_wrote_and_fails_on_any_edit(tmp_path: Path) -> None:
    args = ["--out-dir", str(tmp_path), *SMALL]
    assert cc.main([*args, "--now", "2026-09-23T00:00:00Z"]) == 0
    assert cc.main([*args, "--check"]) == 0

    json_path = tmp_path / "consensus_coarseness.json"
    md_path = tmp_path / "consensus_coarseness.md"
    good_json = json_path.read_text()
    doc = json.loads(good_json)
    doc["patterns"]["equal"]["by_size"]["5"]["methods"]["plain"]["mean_share_right"] += 0.01
    json_path.write_text(json.dumps(doc, indent=2) + "\n")
    assert cc.main([*args, "--check"]) == 1, "an edited number must fail the check"
    json_path.write_text(good_json)

    good_md = md_path.read_text()
    md_path.write_text(good_md.replace("plain majority", "plain vote", 1))
    assert cc.main([*args, "--check"]) == 1, "an edited table must fail the check"
    md_path.write_text(good_md)
    assert cc.main([*args, "--check"]) == 0

    changed = ["--out-dir", str(tmp_path), "--populations", "4", "--splits", "2", "--groups", "8"]
    assert cc.main([*changed, "--check"]) == 1, "other counts give other numbers"
    md_path.unlink()
    assert cc.main([*args, "--check"]) == 1, "a missing table fails the check"


def committed() -> dict:
    return json.loads(COMMITTED_JSON.read_text(encoding="utf-8"))


def test_committed_json_carries_the_stamp_and_the_script_settings() -> None:
    doc = committed()
    assert doc["synthetic"] is True and doc["stamp"] == "SYNTHETIC"
    assert doc["script"] == cc.SCRIPT and doc["seed"] == cc.SEED
    assert doc["parameters"] == cc.parameters(
        n_populations=cc.N_POPULATIONS,
        n_splits=cc.N_SPLITS,
        n_groups=cc.N_GROUPS,
        group_sizes=cc.GROUP_SIZES,
    )


def test_committed_summary_follows_from_the_committed_cells() -> None:
    doc = committed()
    assert doc["summary"] == cc.summarise(doc["patterns"], cc.GROUP_SIZES)


def test_committed_table_is_written_from_the_committed_json() -> None:
    assert COMMITTED_MD.read_text(encoding="utf-8") == cc.render_markdown(committed())


def test_monte_carlo_error_is_small_enough_for_the_reported_digits() -> None:
    mc = committed()["monte_carlo"]
    assert mc["max_se_of_a_mean"] <= 0.0025, "means stable to about 0.005"
    assert mc["max_se_of_a_difference_from_plain"] <= 0.0025
    assert mc["smallest_weighted_sum_not_counted_as_a_tie"] > 1000 * cc.TIE_TOL
