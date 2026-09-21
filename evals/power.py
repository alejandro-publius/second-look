"""Power simulation behind docs/analysis_plan.md item 7. Writes results/power.json.

Model, stated plainly: each person has a hidden chance of answering an item right, drawn from a
Beta distribution with the arm's mean and a between-person standard deviation of 0.10. The
untrained mean is 0.60. Each of the 16 items is a coin flip at that chance. The test is the plan's
two-sided permutation test on the difference in mean accuracy at alpha 0.05.

Usage: uv run python evals/power.py [--sims 2000] [--permutations 1000]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np

from evals.common import N_ITEMS, PLAN_SEED, RESULTS_DIR, result_header, write_json
from evals.usability_analysis import ALPHA, permutation_p

SCRIPT = "evals/power.py"
UNTRAINED_MEAN = 0.60
PERSON_SD = 0.10
N_SIMS = 2_000
N_PERM = 1_000
CASES: tuple[dict[str, Any], ...] = (
    {
        "name": "40_per_arm_10_points",
        "n_per_arm": 40,
        "difference_points": 10,
        "planning_note": 0.80,
    },
    {
        "name": "30_per_arm_12_points",
        "n_per_arm": 30,
        "difference_points": 12,
        "planning_note": 0.80,
    },
    {
        "name": "40_per_arm_0_points",
        "n_per_arm": 40,
        "difference_points": 0,
        "planning_note": ALPHA,
    },
)


def beta_params(mean: float, sd: float) -> tuple[float, float]:
    """Alpha and beta of a Beta distribution with this mean and standard deviation."""
    if not 0 < mean < 1:
        raise ValueError("mean must be strictly between 0 and 1")
    if sd <= 0:
        raise ValueError("sd must be positive")
    common = mean * (1 - mean) / sd**2 - 1
    if common <= 0:
        raise ValueError("sd too large for this mean")
    return mean * common, (1 - mean) * common


def simulate_arm(
    mean: float, n: int, rng: np.random.Generator, *, sd: float = PERSON_SD
) -> np.ndarray:
    """Per-person accuracy over 16 items for n people."""
    a, b = beta_params(mean, sd)
    skill = rng.beta(a, b, size=n)
    right = rng.binomial(N_ITEMS, skill)
    return right / N_ITEMS


def rejection_rate(
    *,
    n_per_arm: int,
    difference_points: float,
    n_sims: int,
    n_perm: int,
    seed: int,
    untrained_mean: float = UNTRAINED_MEAN,
    sd: float = PERSON_SD,
) -> float:
    rng = np.random.default_rng(seed)
    trained_mean = untrained_mean + difference_points / 100.0
    rejections = 0
    for _ in range(n_sims):
        untrained = simulate_arm(untrained_mean, n_per_arm, rng, sd=sd)
        trained = simulate_arm(trained_mean, n_per_arm, rng, sd=sd)
        p = permutation_p(trained, untrained, n_perm=n_perm, rng=rng)
        rejections += int(p < ALPHA)
    return rejections / n_sims


def run(*, n_sims: int = N_SIMS, n_perm: int = N_PERM, seed: int = PLAN_SEED) -> dict[str, Any]:
    result = result_header(SCRIPT, synthetic=False, stamp="power")
    result["model"] = {
        "items": N_ITEMS,
        "untrained_mean_accuracy": UNTRAINED_MEAN,
        "between_person_sd_of_accuracy": PERSON_SD,
        "skill_distribution": "Beta with the stated mean and sd, one draw per person",
        "item_model": "16 independent coin flips at the person's skill",
        "test": "two-sided permutation test on the difference in means",
        "alpha": ALPHA,
        "simulated_data_sets_per_case": n_sims,
        "permutations_per_data_set": n_perm,
        "seed": seed,
    }
    cases: dict[str, Any] = {}
    for i, case in enumerate(CASES):
        power = rejection_rate(
            n_per_arm=case["n_per_arm"],
            difference_points=case["difference_points"],
            n_sims=n_sims,
            n_perm=n_perm,
            seed=seed + i,
        )
        se = float(np.sqrt(power * (1 - power) / n_sims))
        cases[case["name"]] = {
            "n_per_arm": case["n_per_arm"],
            "difference_points": case["difference_points"],
            "power": round(power, 3),
            "simulation_se": round(se, 3),
            "planning_note": case["planning_note"],
            "purpose": "type 1 error check, should sit near alpha"
            if case["difference_points"] == 0
            else "power",
        }
    result["cases"] = cases
    result["power_40_per_arm_10_points"] = cases["40_per_arm_10_points"]["power"]
    result["power_30_per_arm_12_points"] = cases["30_per_arm_12_points"]["power"]
    result["false_positive_rate_40_per_arm"] = cases["40_per_arm_0_points"]["power"]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--sims", type=int, default=N_SIMS)
    parser.add_argument("--permutations", type=int, default=N_PERM)
    parser.add_argument("--out", type=Path, default=RESULTS_DIR / "power.json")
    args = parser.parse_args(argv)
    result = run(n_sims=args.sims, n_perm=args.permutations)
    write_json(args.out, result)
    print(
        f"power: {result['power_40_per_arm_10_points']:.3f} at 40 per arm for 10 points, "
        f"{result['power_30_per_arm_12_points']:.3f} at 30 per arm for 12 points, "
        f"false positive rate {result['false_positive_rate_40_per_arm']:.3f} at 0 points "
        f"({args.sims} data sets, between-person sd {PERSON_SD})"
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
