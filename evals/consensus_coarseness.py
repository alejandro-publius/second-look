"""Is four photos per feature enough to weight a group's votes? A synthetic simulation.

UPDATE_22 section 1 answer 1 asks for the planner's simulation (UPDATE_09 item 4) to be written
down, run and committed, so that the README line under Known weaknesses says what a file in
results/ shows. Everything here is made up: no participant, no photo and no answer from the live
test. The output is stamped SYNTHETIC.

The method, exactly as run
--------------------------
People and items. 40 people, 4 features, 4 items per feature, so 16 items. Every item is a yes
or no question, so a vote is simply right or wrong (the real test's Can't tell button is not
modelled). Person i answers each item of feature f right with chance skill[i, f], on its own,
apart from every other answer. The items of one feature are alike: there is no item difficulty.

Five skill patterns. Every skill is clipped to [0.50, 0.95] after it is drawn.
  equal                           everyone at 0.70 on every feature.
  normal_per_person               one draw per person from a normal curve with mean 0.70 and
                                  sd 0.07, used for all four features. Our reading: the brief
                                  says "normal around 0.70" and asks for a draw per person and
                                  feature only in pattern 3, so this draw is per person.
  uniform_per_person_and_feature  one uniform draw from 0.50 to 0.95 for every person and every
                                  feature.
  uniform_per_person              one uniform draw from 0.50 to 0.95 per person, the same for
                                  every feature.
  third_at_chance                 exactly 13 of the 40 people at 0.50 on every feature. A third
                                  of 40 is 13.33, rounded to the nearest whole person. The count
                                  is fixed, not a coin flip per person, so every population has
                                  the same share at chance. The other 27 get one draw per person
                                  from a normal curve with mean 0.80 and sd 0.06, used for every
                                  feature (per person, by the same reading as pattern 2).

Halves. The 16 items are split into two halves of 8 with 2 items of each feature in each half:
for every feature, 2 of its 4 items are picked at random for half A and the other 2 go to half
B. Each split is used both ways: score everyone on half A (the calibration half) and vote on
half B, then score on B and vote on A. A person's score never uses an item they vote on.

Groups. Groups of 3, 5 and 7 people drawn at random from the 40, without repeats in a group.

Methods. c is the number a person got right of the 2 calibration items of the voted item's
feature (0, 1 or 2). C is the number they got right of all 8 calibration items (0 to 8).
logit(p) = ln(p / (1 - p)).
  plain         w = 1 for everyone.
  feature_only  w = max(0, logit((c + 0.5) / 3)). At c = 0, 1, 2 that is max(0, logit(1/6)),
                max(0, logit(1/2)), max(0, logit(5/6)) = 0, 0 and ln 5 = 1.609.
  shrunk_k3,    r = (C + 0.5) / 9 is the person's overall calibration rate. Then
  shrunk_k6     p = (c + 0.5 + k * r) / (3 + k), with k = 3 or k = 6, and w = max(0, logit(p)).
                This adds k pretend items, answered at the person's overall rate, to the
                feature's own count, so a feature with only 2 photos leans on all 8.
  overall_only  w = max(0, logit((C + 0.5) / 9)), the same weight for every feature.
  passers_only  a person passes with C >= 6 (6 or more of 8). The passers in the group vote by
                plain majority. When nobody in the group passed, or the passers' votes tie, the
                whole group votes by plain majority instead.

A group's weighted vote on an item is the sum of w over the people who got it right minus the
sum of w over the people who got it wrong. The group is right when that sum is above zero. A sum
of exactly zero is a tie (this includes every weight being zero) and counts as WRONG, for every
method, including plain majority and the fall back of passers only. The code treats a sum within
TIE_TOL = 1e-9 of zero as zero, only so that rounding in the computer's arithmetic cannot turn a
true tie into a win (0.1 + 0.2 - 0.3 is not exactly 0 in floating point). The run records the
smallest sum it did not treat as a tie and stops if that is ever near TIE_TOL.

Replications. 1000 simulated populations per pattern. For each population, 8 random splits, each
used both ways (16 score and vote pairs), and 50 random groups of each size for each pair. Every
method is scored on the same populations, splits and groups, so the differences between methods
are paired. Each result cell averages 1000 x 16 x 50 = 800,000 group votes over 8 items.

Monte Carlo error. Each population's mean share right is one independent draw, so the standard
error of a mean is the standard deviation of those 1000 population means over the square root of
1000, and the same for the paired difference from plain majority. The JSON gives both for every
cell and the largest of each. A method "clearly" beats or loses to plain majority when the
difference is more than twice its standard error.

Random numbers. One numpy Generator seeded 20260921, drawn in a fixed order: for each pattern in
the order above, for each population, the skills, the answers, the splits, then the groups for
sizes 3, 5 and 7. Changing any count changes every later draw.

Usage:
  uv run python evals/consensus_coarseness.py            write results/consensus_coarseness.json
                                                         and results/consensus_coarseness.md
  uv run python evals/consensus_coarseness.py --check    exit 1 unless the committed files are
                                                         exactly what the script writes
  make consensus-coarseness | make consensus-check       the same two commands
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from evals.common import (
    ITEMS_PER_FEATURE,
    N_ITEMS,
    RESULTS_DIR,
    iso_utc,
    now_utc,
    parse_utc,
    result_header,
)

SCRIPT = "evals/consensus_coarseness.py"
SEED = 20260921
N_PEOPLE = 40
N_FEATURES = N_ITEMS // ITEMS_PER_FEATURE
PER_HALF = ITEMS_PER_FEATURE // 2
HALF_ITEMS = N_FEATURES * PER_HALF
SKILL_MIN = 0.50
SKILL_MAX = 0.95
GROUP_SIZES = (3, 5, 7)
HEADLINE_SIZE = 5
PASS_MARK = 6
SHRINK_KS = (3, 6)
TIE_TOL = 1e-9
AT_CHANCE_COUNT = round(N_PEOPLE / 3)
N_POPULATIONS = 1000
N_SPLITS = 8
N_GROUPS = 50

METHODS = ("plain", "feature_only", "shrunk_k3", "shrunk_k6", "overall_only", "passers_only")
PLAIN = METHODS.index("plain")
PASSERS = METHODS.index("passers_only")
WEIGHTED = ("feature_only", "shrunk_k3", "shrunk_k6", "overall_only")
METHOD_LABEL = {
    "plain": "plain majority",
    "feature_only": "feature only weights",
    "shrunk_k3": "feature weights shrunk to overall, k = 3",
    "shrunk_k6": "feature weights shrunk to overall, k = 6",
    "overall_only": "overall weights",
    "passers_only": "passers only (6 of 8)",
}
METHOD_FORMULA = {
    "plain": "w = 1",
    "feature_only": "w = max(0, logit((c + 0.5) / 3))",
    "shrunk_k3": "r = (C + 0.5) / 9; p = (c + 0.5 + 3 * r) / (3 + 3); w = max(0, logit(p))",
    "shrunk_k6": "r = (C + 0.5) / 9; p = (c + 0.5 + 6 * r) / (3 + 6); w = max(0, logit(p))",
    "overall_only": "w = max(0, logit((C + 0.5) / 9))",
    "passers_only": (
        "people with C >= 6 vote by plain majority; when nobody in the group passed or the "
        "passers tie, the whole group votes by plain majority"
    ),
}
PATTERNS = (
    "equal",
    "normal_per_person",
    "uniform_per_person_and_feature",
    "uniform_per_person",
    "third_at_chance",
)
PATTERN_LABEL = {
    "equal": "everyone at 0.70",
    "normal_per_person": "normal around 0.70, sd 0.07, one skill per person",
    "uniform_per_person_and_feature": "uniform 0.50 to 0.95 per person and feature",
    "uniform_per_person": "uniform 0.50 to 0.95 per person, same for every feature",
    "third_at_chance": "13 of 40 at 0.50, the rest normal around 0.80, sd 0.06",
}
PATTERN_RULE = {
    "equal": "skill 0.70 for every person and feature",
    "normal_per_person": (
        "one draw per person from normal(0.70, sd 0.07), used for all four features"
    ),
    "uniform_per_person_and_feature": "one draw per person and feature from uniform(0.50, 0.95)",
    "uniform_per_person": "one draw per person from uniform(0.50, 0.95), used for all features",
    "third_at_chance": (
        f"exactly {AT_CHANCE_COUNT} of {N_PEOPLE} people (40 / 3 rounded to the nearest whole "
        "person) at 0.50 on every feature; the rest one draw per person from normal(0.80, sd "
        "0.06), used for all four features"
    ),
}

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]
BoolArray = npt.NDArray[np.bool_]


# ---------------------------------------------------------------------------
# Skills, answers and splits
# ---------------------------------------------------------------------------


def draw_skills(pattern: str, rng: np.random.Generator, n_people: int = N_PEOPLE) -> FloatArray:
    """A (people, features) table of the chance each person gets an item of each feature right."""
    shape = (n_people, N_FEATURES)
    if pattern == "equal":
        skills = np.full(shape, 0.70)
    elif pattern == "normal_per_person":
        skills = np.broadcast_to(rng.normal(0.70, 0.07, size=(n_people, 1)), shape)
    elif pattern == "uniform_per_person_and_feature":
        skills = rng.uniform(SKILL_MIN, SKILL_MAX, size=shape)
    elif pattern == "uniform_per_person":
        skills = np.broadcast_to(rng.uniform(SKILL_MIN, SKILL_MAX, size=(n_people, 1)), shape)
    elif pattern == "third_at_chance":
        at_chance = round(n_people / 3)
        rest = rng.normal(0.80, 0.06, size=(n_people - at_chance, 1))
        skills = np.vstack(
            [
                np.full((at_chance, N_FEATURES), 0.50),
                np.broadcast_to(rest, (n_people - at_chance, N_FEATURES)),
            ]
        )
    else:
        raise ValueError(f"unknown skill pattern {pattern!r}")
    return np.clip(np.asarray(skills, dtype=np.float64), SKILL_MIN, SKILL_MAX)


def draw_answers(skills: FloatArray, rng: np.random.Generator) -> BoolArray:
    """(people, 16) right or wrong. Items 4f to 4f + 3 belong to feature f."""
    chance = np.repeat(skills, ITEMS_PER_FEATURE, axis=1)
    return np.asarray(rng.random(chance.shape) < chance)


def split_halves(n_splits: int, rng: np.random.Generator) -> tuple[IntArray, IntArray]:
    """n_splits random splits into half A and half B, each (n_splits, 8) item indexes.

    For every feature, 2 of its 4 items go to A and the other 2 to B. Positions 2f and 2f + 1 of
    a half hold feature f, so the feature of a position j is j // 2.
    """
    order = np.argsort(rng.random((n_splits, N_FEATURES, ITEMS_PER_FEATURE)), axis=-1)
    items = order + ITEMS_PER_FEATURE * np.arange(N_FEATURES)[None, :, None]
    half_a = items[:, :, :PER_HALF].reshape(n_splits, HALF_ITEMS)
    half_b = items[:, :, PER_HALF:].reshape(n_splits, HALF_ITEMS)
    return half_a.astype(np.int64), half_b.astype(np.int64)


def score_vote_pairs(half_a: IntArray, half_b: IntArray) -> tuple[IntArray, IntArray]:
    """Use every split both ways: (score on A, vote on B), then (score on B, vote on A)."""
    return np.concatenate([half_a, half_b]), np.concatenate([half_b, half_a])


# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------


def logit(p: npt.ArrayLike) -> FloatArray:
    q = np.asarray(p, dtype=np.float64)
    return np.asarray(np.log(q / (1.0 - q)))


def overall_rate(big_c: npt.ArrayLike) -> FloatArray:
    """r = (C + 0.5) / 9 from C right of the 8 calibration items."""
    return np.asarray((np.asarray(big_c, dtype=np.float64) + 0.5) / (HALF_ITEMS + 1))


def feature_weight(c: npt.ArrayLike) -> FloatArray:
    """w = max(0, logit((c + 0.5) / 3)) from c right of the feature's 2 calibration items."""
    p = (np.asarray(c, dtype=np.float64) + 0.5) / (PER_HALF + 1)
    return np.maximum(0.0, logit(p))


def shrunk_weight(c: npt.ArrayLike, big_c: npt.ArrayLike, k: float) -> FloatArray:
    """w = max(0, logit(p)), p = (c + 0.5 + k * r) / (3 + k), r = (C + 0.5) / 9."""
    r = overall_rate(big_c)
    p = (np.asarray(c, dtype=np.float64) + 0.5 + k * r) / (PER_HALF + 1 + k)
    return np.maximum(0.0, logit(p))


def overall_weight(big_c: npt.ArrayLike) -> FloatArray:
    """w = max(0, logit((C + 0.5) / 9)), the same for every feature."""
    return np.maximum(0.0, logit(overall_rate(big_c)))


def method_weights(c: IntArray, big_c: IntArray) -> FloatArray:
    """Every method's weight, stacked in METHODS order: (methods, *c.shape).

    c has the features on its last axis; big_c has the same shape without it. Passers only is a
    weight of 1 for a passer and 0 for anyone else; decide_items adds its fall back.
    """
    per_feature = np.broadcast_to(big_c[..., None], c.shape)
    passed = (per_feature >= PASS_MARK).astype(np.float64)
    return np.stack(
        [
            np.ones(c.shape),
            feature_weight(c),
            shrunk_weight(c, per_feature, SHRINK_KS[0]),
            shrunk_weight(c, per_feature, SHRINK_KS[1]),
            overall_weight(per_feature),
            passed,
        ]
    )


# ---------------------------------------------------------------------------
# Votes
# ---------------------------------------------------------------------------


def vote_contributions(
    correct: BoolArray, score_items: IntArray, vote_items: IntArray
) -> tuple[FloatArray, BoolArray]:
    """What each person adds to a group's sum on each voted item, for every method.

    correct: (people, 16). score_items, vote_items: (pairs, 8), feature of position j is j // 2.
    Returns contributions (pairs, people, methods, 8), +w when the person is right and -w when
    wrong, and passed (pairs, people).
    """
    n_people = correct.shape[0]
    n_pairs = score_items.shape[0]
    scored = correct[:, score_items]
    c = scored.reshape(n_people, n_pairs, N_FEATURES, PER_HALF).sum(axis=-1)
    big_c = c.sum(axis=-1)
    weights = np.repeat(method_weights(c, big_c), PER_HALF, axis=-1)
    sign = np.where(correct[:, vote_items], 1.0, -1.0)
    contrib = (weights * sign[None]).transpose(2, 1, 0, 3)
    return np.ascontiguousarray(contrib), np.asarray((big_c >= PASS_MARK).T)


def is_tie(sums: FloatArray) -> BoolArray:
    return np.asarray(np.abs(sums) <= TIE_TOL)


def decide_items(sums: FloatArray) -> BoolArray:
    """Right or wrong for every method from the group sums, shape (..., methods, items).

    Above zero is right. A tie (a sum of zero) is wrong. Passers only takes the passers' sum,
    and falls back to everyone's plain sum when that is a tie, which is also the case when
    nobody in the group passed. A tie in the fall back is wrong too.
    """
    right = np.asarray(sums > TIE_TOL)
    passers = sums[..., PASSERS, :]
    answer = np.where(is_tie(passers), sums[..., PLAIN, :], passers)
    right[..., PASSERS, :] = answer > TIE_TOL
    return right


def draw_groups(n_pairs: int, n_groups: int, size: int, rng: np.random.Generator) -> IntArray:
    """(pairs, groups, size) people, all different inside a group.

    Each row is a fresh random order of all 40 people, and the group is its first `size`.
    """
    everyone = np.broadcast_to(np.arange(N_PEOPLE, dtype=np.int64), (n_pairs, n_groups, N_PEOPLE))
    return np.ascontiguousarray(rng.permuted(everyone, axis=-1)[..., :size])


@dataclass
class GroupTally:
    """Counts for one population and one group size. Every count is a whole number."""

    right: IntArray  # (methods,) items right
    tied: IntArray  # (methods,) items where the final sum was a tie
    items: int
    sent_back: int  # passers only items that fell back to everyone
    groups: int
    groups_without_passer: int
    smallest_non_tie: float  # smallest |sum| of a weighted method not treated as a tie


def tally_groups(contrib: FloatArray, passed: BoolArray, groups: IntArray) -> GroupTally:
    """Sum each group's votes, decide every item, and count."""
    pair_index = np.arange(contrib.shape[0])[:, None, None]
    sums = contrib[pair_index, groups].sum(axis=2)
    right = decide_items(sums)
    tie = is_tie(sums)
    passer_tie = tie[..., PASSERS, :]
    tied = tie.sum(axis=(0, 1, 3)).astype(np.int64)
    # Passers only ends in a tie only when its fall back, everyone's plain sum, ties too.
    tied[PASSERS] = int((passer_tie & tie[..., PLAIN, :]).sum())
    weighted = np.abs(sums[..., 1:PASSERS, :])
    smallest = float(np.where(weighted > TIE_TOL, weighted, math.inf).min(initial=math.inf))
    has_passer = passed[pair_index, groups].any(axis=-1)
    return GroupTally(
        right=right.sum(axis=(0, 1, 3)).astype(np.int64),
        tied=tied,
        items=int(sums.shape[0] * sums.shape[1] * sums.shape[3]),
        sent_back=int(passer_tie.sum()),
        groups=int(has_passer.size),
        groups_without_passer=int((~has_passer).sum()),
        smallest_non_tie=smallest,
    )


def simulate_population(
    pattern: str,
    rng: np.random.Generator,
    *,
    n_splits: int = N_SPLITS,
    n_groups: int = N_GROUPS,
    group_sizes: tuple[int, ...] = GROUP_SIZES,
) -> tuple[dict[int, GroupTally], int]:
    """One made-up population of 40: its tallies per group size, and how many people passed."""
    skills = draw_skills(pattern, rng)
    correct = draw_answers(skills, rng)
    score_items, vote_items = score_vote_pairs(*split_halves(n_splits, rng))
    contrib, passed = vote_contributions(correct, score_items, vote_items)
    tallies = {
        size: tally_groups(contrib, passed, draw_groups(len(score_items), n_groups, size, rng))
        for size in group_sizes
    }
    return tallies, int(passed.sum())


# ---------------------------------------------------------------------------
# Running and summing up
# ---------------------------------------------------------------------------


def se_of_mean(counts: IntArray, denominator: int) -> float:
    """Standard error of the mean of counts / denominator, over populations.

    Worked in whole numbers until the last step, so the result does not depend on the order a
    machine adds floating point numbers in.
    """
    n = int(counts.size)
    total = int(counts.sum())
    squares = int((counts.astype(np.int64) ** 2).sum())
    variance = (n * squares - total * total) / (n * (n - 1))
    return math.sqrt(variance / n) / denominator


def points(value: float) -> float:
    return round(100.0 * value, 1)


def run_simulation(
    *,
    seed: int = SEED,
    n_populations: int = N_POPULATIONS,
    n_splits: int = N_SPLITS,
    n_groups: int = N_GROUPS,
    group_sizes: tuple[int, ...] = GROUP_SIZES,
) -> dict[str, Any]:
    """Every pattern, size and method. Returns the patterns block and the run checks."""
    if n_populations < 2:
        raise ValueError("need at least 2 populations for a standard error")
    rng = np.random.default_rng(seed)
    patterns: dict[str, Any] = {}
    smallest_non_tie = math.inf
    max_se = 0.0
    max_se_diff = 0.0
    for pattern in PATTERNS:
        right = {
            size: np.zeros((n_populations, len(METHODS)), dtype=np.int64) for size in group_sizes
        }
        tied = {size: np.zeros(len(METHODS), dtype=np.int64) for size in group_sizes}
        sent_back = dict.fromkeys(group_sizes, 0)
        no_passer = dict.fromkeys(group_sizes, 0)
        groups_seen = dict.fromkeys(group_sizes, 0)
        items_per_population = dict.fromkeys(group_sizes, 0)
        people_passing = 0
        for pop in range(n_populations):
            tallies, passing = simulate_population(
                pattern, rng, n_splits=n_splits, n_groups=n_groups, group_sizes=group_sizes
            )
            people_passing += passing
            for size, tally in tallies.items():
                right[size][pop] = tally.right
                tied[size] += tally.tied
                sent_back[size] += tally.sent_back
                no_passer[size] += tally.groups_without_passer
                groups_seen[size] += tally.groups
                items_per_population[size] = tally.items
                smallest_non_tie = min(smallest_non_tie, tally.smallest_non_tie)
        by_size: dict[str, Any] = {}
        for size in group_sizes:
            per_pop = items_per_population[size]
            all_items = per_pop * n_populations
            counts = right[size]
            methods: dict[str, Any] = {}
            for m, method in enumerate(METHODS):
                diff = counts[:, m] - counts[:, PLAIN]
                se = se_of_mean(counts[:, m], per_pop)
                se_diff = se_of_mean(diff, per_pop) if m != PLAIN else 0.0
                max_se = max(max_se, se)
                max_se_diff = max(max_se_diff, se_diff)
                mean_diff = int(diff.sum()) / all_items
                methods[method] = {
                    "mean_share_right": round(int(counts[:, m].sum()) / all_items, 4),
                    "se": round(se, 4),
                    "minus_plain": round(mean_diff, 4),
                    "minus_plain_se": round(se_diff, 4),
                    "clearly_beats_plain": bool(mean_diff > 2 * se_diff) if m != PLAIN else False,
                    "clearly_loses_to_plain": bool(mean_diff < -2 * se_diff)
                    if m != PLAIN
                    else False,
                    "tie_share": round(int(tied[size][m]) / all_items, 4),
                }
            by_size[str(size)] = {
                "voted_items_per_population": per_pop,
                "methods": methods,
                "passers_only_share_of_items_sent_back_to_everyone": round(
                    sent_back[size] / all_items, 4
                ),
                "share_of_groups_with_no_passer": round(no_passer[size] / groups_seen[size], 4),
            }
        pairs = 2 * n_splits
        patterns[pattern] = {
            "label": PATTERN_LABEL[pattern],
            "skill_rule": PATTERN_RULE[pattern],
            "share_of_people_passing_a_half": round(
                people_passing / (n_populations * pairs * N_PEOPLE), 4
            ),
            "by_size": by_size,
        }
    if smallest_non_tie <= 1000 * TIE_TOL:
        raise RuntimeError(
            f"a weighted sum of {smallest_non_tie!r} is too close to the tie tolerance {TIE_TOL}"
        )
    return {
        "patterns": patterns,
        "checks": {
            "max_se_of_a_mean": round(max_se, 4),
            "max_se_of_a_difference_from_plain": round(max_se_diff, 4),
            "smallest_weighted_sum_not_counted_as_a_tie": float(f"{smallest_non_tie:.3g}"),
            "tie_tolerance": TIE_TOL,
        },
    }


def summarise(patterns: dict[str, Any], group_sizes: tuple[int, ...]) -> dict[str, Any]:
    """Which method is best per pattern and size, and whether weighting ever beats plain."""
    by_pattern: dict[str, Any] = {}
    cells = 0
    plain_best_cells = 0
    weighted_beats_cells = 0
    passers_beats_cells = 0
    for pattern in PATTERNS:
        row: dict[str, Any] = {"label": PATTERN_LABEL[pattern]}
        for size in group_sizes:
            methods = patterns[pattern]["by_size"][str(size)]["methods"]
            best = max(METHODS, key=lambda m: (methods[m]["mean_share_right"], m == "plain"))
            best_weighted = max(WEIGHTED, key=lambda m: methods[m]["minus_plain"])
            weighted_beats = [m for m in WEIGHTED if methods[m]["clearly_beats_plain"]]
            cell = {
                "plain_pct": points(methods["plain"]["mean_share_right"]),
                "best_method": best,
                "best_pct": points(methods[best]["mean_share_right"]),
                "best_minus_plain_points": points(methods[best]["minus_plain"]),
                "best_clearly_beats_plain": methods[best]["clearly_beats_plain"],
                "best_weighted_method": best_weighted,
                "best_weighted_minus_plain_points": points(methods[best_weighted]["minus_plain"]),
                "weighted_methods_that_clearly_beat_plain": weighted_beats,
                "passers_only_minus_plain_points": points(methods["passers_only"]["minus_plain"]),
                "passers_only_clearly_beats_plain": methods["passers_only"]["clearly_beats_plain"],
                "feature_only_minus_plain_points": points(methods["feature_only"]["minus_plain"]),
            }
            cell["statement"] = cell_statement(pattern, size, cell)
            row[f"size_{size}"] = cell
            cells += 1
            plain_best_cells += best == "plain"
            weighted_beats_cells += bool(weighted_beats)
            passers_beats_cells += bool(cell["passers_only_clearly_beats_plain"])
        by_pattern[pattern] = row

    size = HEADLINE_SIZE if HEADLINE_SIZE in group_sizes else group_sizes[len(group_sizes) // 2]
    key = f"size_{size}"
    head = {p: by_pattern[p][key] for p in PATTERNS}
    plain_best = [p for p in PATTERNS if head[p]["best_method"] == "plain"]
    weighted_win = [p for p in PATTERNS if head[p]["weighted_methods_that_clearly_beat_plain"]]
    passers_win = [p for p in PATTERNS if head[p]["passers_only_clearly_beats_plain"]]
    feature_loses = [
        p
        for p in PATTERNS
        if patterns[p]["by_size"][str(size)]["methods"]["feature_only"]["clearly_loses_to_plain"]
    ]
    feature_losses = [-head[p]["feature_only_minus_plain_points"] for p in PATTERNS]
    best_gain_pattern = max(PATTERNS, key=lambda p: head[p]["best_minus_plain_points"])
    best_weighted_pattern = max(PATTERNS, key=lambda p: head[p]["best_weighted_minus_plain_points"])
    passers_pattern = max(PATTERNS, key=lambda p: head[p]["passers_only_minus_plain_points"])
    at_head = {
        "group_size": size,
        "n_patterns": len(PATTERNS),
        "patterns_where_plain_is_best": plain_best,
        "n_patterns_where_plain_is_best": len(plain_best),
        "patterns_where_a_weighted_method_clearly_beats_plain": weighted_win,
        "n_patterns_where_a_weighted_method_clearly_beats_plain": len(weighted_win),
        "patterns_where_passers_only_clearly_beats_plain": passers_win,
        "n_patterns_where_passers_only_clearly_beats_plain": len(passers_win),
        "n_patterns_where_feature_only_clearly_loses": len(feature_loses),
        "feature_only_loss_points_min": min(feature_losses),
        "feature_only_loss_points_max": max(feature_losses),
        "largest_gain_over_plain_points": head[best_gain_pattern]["best_minus_plain_points"],
        "largest_gain_method": head[best_gain_pattern]["best_method"],
        "largest_gain_pattern": best_gain_pattern,
        "largest_weighted_gain_over_plain_points": head[best_weighted_pattern][
            "best_weighted_minus_plain_points"
        ],
        "largest_weighted_gain_method": head[best_weighted_pattern]["best_weighted_method"],
        "largest_weighted_gain_pattern": best_weighted_pattern,
        "largest_passers_only_gain_points": head[passers_pattern][
            "passers_only_minus_plain_points"
        ],
        "largest_passers_only_gain_pattern": passers_pattern,
    }
    at_head["statement"] = headline_statement(at_head)
    return {
        "statement": at_head["statement"],
        "beats_rule": (
            "a method clearly beats (or loses to) plain majority when its mean share right is "
            "higher (or lower) by more than twice the Monte Carlo standard error of the paired "
            "difference"
        ),
        "weighted_methods": list(WEIGHTED),
        "at_headline_size": at_head,
        "all_sizes": {
            "cells": cells,
            "cells_where_plain_is_best": plain_best_cells,
            "cells_where_a_weighted_method_clearly_beats_plain": weighted_beats_cells,
            "cells_where_passers_only_clearly_beats_plain": passers_beats_cells,
        },
        "by_pattern": by_pattern,
    }


def _gap(value: float) -> str:
    if value > 0:
        return f"{value:.1f} points ahead of"
    if value < 0:
        return f"{-value:.1f} points behind"
    return "level with"


def _clear(clear: bool) -> str:
    return ", a clear gain" if clear else ", within the Monte Carlo error"


def _first_upper(text: str) -> str:
    return text[:1].upper() + text[1:]


def cell_statement(pattern: str, size: int, cell: dict[str, Any]) -> str:
    lead = f"Groups of {size}, {PATTERN_LABEL[pattern]}: "
    if cell["best_method"] == "plain":
        lead += f"plain majority is best ({cell['plain_pct']:.1f} percent right)."
    else:
        lead += (
            f"{METHOD_LABEL[cell['best_method']]} is best, "
            f"{_gap(cell['best_minus_plain_points'])} plain majority"
            f"{_clear(cell['best_clearly_beats_plain'])}."
        )
    weighted = cell["best_weighted_method"]
    lead += (
        f" The best weighted method, {METHOD_LABEL[weighted]}, is "
        f"{_gap(cell['best_weighted_minus_plain_points'])} plain majority"
    )
    if cell["best_weighted_minus_plain_points"] > 0:
        lead += _clear(weighted in cell["weighted_methods_that_clearly_beat_plain"])
    if cell["best_method"] != "passers_only":
        lead += f"; passers only is {_gap(cell['passers_only_minus_plain_points'])} plain majority"
    return lead + "."


def headline_statement(head: dict[str, Any]) -> str:
    n = head["n_patterns"]
    size = head["group_size"]
    text = (
        f"In groups of {size}, plain majority is best in {head['n_patterns_where_plain_is_best']} "
        f"of {n} skill patterns. Feature only weights clearly lose to plain majority in "
        f"{head['n_patterns_where_feature_only_clearly_loses']} of {n}, by "
        f"{head['feature_only_loss_points_min']:.1f} to "
        f"{head['feature_only_loss_points_max']:.1f} points. "
    )
    weighted = head["patterns_where_a_weighted_method_clearly_beats_plain"]
    if weighted:
        text += (
            f"A weighted method clearly beats plain majority in {len(weighted)} of {n} "
            f"({', '.join(weighted)}), by at most "
            f"{head['largest_weighted_gain_over_plain_points']:.1f} points "
            f"({head['largest_weighted_gain_method']}). "
        )
    else:
        text += f"No weighted method clearly beats plain majority in any of the {n} patterns. "
    passers = head["patterns_where_passers_only_clearly_beats_plain"]
    if passers:
        text += (
            f"Passers only clearly beats plain majority in {len(passers)} of {n} "
            f"({', '.join(passers)}), by at most "
            f"{head['largest_passers_only_gain_points']:.1f} points."
        )
    else:
        text += f"Passers only never clearly beats plain majority in the {n} patterns."
    return text


def parameters(
    *, n_populations: int, n_splits: int, n_groups: int, group_sizes: tuple[int, ...]
) -> dict[str, Any]:
    c_values = list(range(PER_HALF + 1))
    big_c_values = list(range(HALF_ITEMS + 1))
    return {
        "people": N_PEOPLE,
        "features": N_FEATURES,
        "items_per_feature": ITEMS_PER_FEATURE,
        "items": N_ITEMS,
        "answers": "yes or no only, so each vote is right or wrong; Can't tell is not modelled",
        "skill_clip": [SKILL_MIN, SKILL_MAX],
        "patterns": {p: PATTERN_RULE[p] for p in PATTERNS},
        "at_chance_count_in_third_at_chance": AT_CHANCE_COUNT,
        "at_chance_rounding": "40 / 3 = 13.33, rounded to the nearest whole person",
        "group_sizes": list(group_sizes),
        "headline_group_size": HEADLINE_SIZE,
        "halves": (
            "for every feature 2 of its 4 items go to half A and 2 to half B; score on one "
            "half, vote on the other, then swap; results are over both ways"
        ),
        "items_per_feature_per_half": PER_HALF,
        "pass_mark_of_8": PASS_MARK,
        "populations_per_pattern": n_populations,
        "random_splits_per_population": n_splits,
        "score_vote_pairs_per_population": 2 * n_splits,
        "groups_per_size_per_pair": n_groups,
        "group_votes_per_cell": n_populations * 2 * n_splits * n_groups,
        "paired": "every method is scored on the same populations, splits and groups",
        "methods": {m: METHOD_FORMULA[m] for m in METHODS},
        "symbols": {
            "c": "right of the 2 calibration items of the voted item's feature",
            "C": "right of all 8 calibration items",
            "r": "(C + 0.5) / 9, the person's overall calibration rate",
            "logit": "logit(p) = ln(p / (1 - p))",
        },
        "weights_by_c_feature_only": [round(float(feature_weight(c)), 4) for c in c_values],
        "weights_by_C_overall_only": [round(float(overall_weight(c)), 4) for c in big_c_values],
        "vote_rule": (
            "sum of w over people right minus sum of w over people wrong; above zero is right"
        ),
        "tie_rule": (
            "a sum of exactly zero (a tie, including every weight zero) counts as wrong for every "
            "method; sums within the tie tolerance of zero are treated as zero to absorb "
            "floating point rounding"
        ),
        "monte_carlo_error": (
            "standard error across the simulated populations: the standard deviation of the "
            "per population mean share right over the square root of the number of populations"
        ),
    }


def build_result(
    *,
    when: datetime | None = None,
    seed: int = SEED,
    n_populations: int = N_POPULATIONS,
    n_splits: int = N_SPLITS,
    n_groups: int = N_GROUPS,
    group_sizes: tuple[int, ...] = GROUP_SIZES,
) -> dict[str, Any]:
    sim = run_simulation(
        seed=seed,
        n_populations=n_populations,
        n_splits=n_splits,
        n_groups=n_groups,
        group_sizes=group_sizes,
    )
    result = result_header(SCRIPT, synthetic=True, stamp="SYNTHETIC", when=when)
    result["question"] = (
        "With four photos per feature, does weighting a person's vote by their score beat a "
        "plain majority? UPDATE_22 section 1 answer 1; the planner's method from UPDATE_09 item 4"
    )
    result["seed"] = seed
    result["summary"] = summarise(sim["patterns"], group_sizes)
    result["monte_carlo"] = sim["checks"]
    result["parameters"] = parameters(
        n_populations=n_populations, n_splits=n_splits, n_groups=n_groups, group_sizes=group_sizes
    )
    result["patterns"] = sim["patterns"]
    result["outputs"] = {"table": "consensus_coarseness.md"}
    return result


def render_markdown(result: dict[str, Any]) -> str:
    """The table, written from the JSON alone, so the two can never disagree."""
    params = result["parameters"]
    sizes = params["group_sizes"]
    mc = result["monte_carlo"]
    lines = [
        "# SYNTHETIC: can four photos per feature weight a group's votes?",
        "",
        f"Written by `{result['script']}` from `results/consensus_coarseness.json` (seed "
        f"{result['seed']}). Made up people only, no real answers. Do not edit by hand: run "
        "`make consensus-coarseness`.",
        "",
        "Each number is the mean share of voted items a random group gets right, in percent. "
        "The number in brackets is the difference from plain majority, in points. A star marks a "
        "method that clearly beats plain majority (by more than twice the Monte Carlo standard "
        "error).",
        "",
        "## Summary",
        "",
        result["summary"]["statement"],
        "",
    ]
    for pattern in PATTERNS:
        block = result["patterns"][pattern]
        lines += [
            f"## {block['label']} (`{pattern}`)",
            "",
            f"Skills: {block['skill_rule']}. Share of people passing a half: "
            f"{100 * block['share_of_people_passing_a_half']:.1f} percent.",
            "",
            "| method | " + " | ".join(f"groups of {s}" for s in sizes) + " |",
            "|---|" + "---|" * len(sizes),
        ]
        for method in METHODS:
            cells = []
            for size in sizes:
                row = block["by_size"][str(size)]["methods"][method]
                share = f"{100 * row['mean_share_right']:.1f}"
                if method == "plain":
                    cells.append(share)
                else:
                    star = " *" if row["clearly_beats_plain"] else ""
                    cells.append(f"{share} ({100 * row['minus_plain']:+.1f}){star}")
            lines.append(f"| {METHOD_LABEL[method]} | " + " | ".join(cells) + " |")
        lines.append("")
        for size in sizes:
            lines.append(
                f"- {result['summary']['by_pattern'][pattern][f'size_{size}']['statement']}"
            )
        lines.append("")
    lines += [
        "## Method",
        "",
        f"{params['people']} people, {params['features']} features of "
        f"{params['items_per_feature']} items. {_first_upper(params['answers'])}. "
        f"Halves: {params['halves']}. Groups of {', '.join(str(s) for s in sizes)} drawn at "
        f"random. {params['populations_per_pattern']} populations per pattern, "
        f"{params['random_splits_per_population']} random splits each used both ways, and "
        f"{params['groups_per_size_per_pair']} groups per size for each way, so "
        f"{params['group_votes_per_cell']:,} group votes per cell.",
        "",
    ]
    for method in METHODS:
        lines.append(f"- {METHOD_LABEL[method]}: {params['methods'][method]}")
    lines += [
        "",
        f"c is {params['symbols']['c']}; C is {params['symbols']['C']}; "
        f"{params['symbols']['logit']}. {_first_upper(params['tie_rule'])}.",
        "",
        f"Monte Carlo error: the largest standard error of a mean is {mc['max_se_of_a_mean']:.4f} "
        f"and of a difference from plain majority {mc['max_se_of_a_difference_from_plain']:.4f} "
        "(as shares, not percent).",
        "",
    ]
    return "\n".join(lines)


def dump_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--now", default=None, help="stamp this UTC time instead of the clock")
    parser.add_argument("--populations", type=int, default=N_POPULATIONS)
    parser.add_argument("--splits", type=int, default=N_SPLITS)
    parser.add_argument("--groups", type=int, default=N_GROUPS)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 unless the committed JSON and table are exactly what this run writes",
    )
    args = parser.parse_args(argv)
    json_path = args.out_dir / "consensus_coarseness.json"
    md_path = args.out_dir / "consensus_coarseness.md"

    if args.check:
        if not json_path.exists() or not md_path.exists():
            print(f"consensus-check: {json_path.name} or {md_path.name} is missing")
            return 1
        committed = json.loads(json_path.read_text(encoding="utf-8"))
        when = parse_utc(committed["generated_at_utc"])
    else:
        when = parse_utc(args.now) if args.now else now_utc()

    result = build_result(
        when=when, n_populations=args.populations, n_splits=args.splits, n_groups=args.groups
    )
    json_text = dump_json(result)
    md_text = render_markdown(result)

    if args.check:
        stale = [
            path.name
            for path, text in ((json_path, json_text), (md_path, md_text))
            if path.read_text(encoding="utf-8") != text
        ]
        if stale:
            print(
                f"consensus-check: {', '.join(stale)} is not what the script writes at "
                f"{iso_utc(when)}; run make consensus-coarseness"
            )
            return 1
        print(f"consensus-check: {json_path.name} and {md_path.name} match the script")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json_text, encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")
    print(result["summary"]["statement"])
    print(f"wrote {json_path} and {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
