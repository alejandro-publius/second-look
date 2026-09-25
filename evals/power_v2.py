"""Power simulation behind docs/analysis_plan_v2.md item 7. Writes results/power_v2.json.

The same model as evals/power.py, for part 2's eight items: each person has a hidden chance of
answering an item right, drawn from a Beta distribution with the arm's mean and a between-person
standard deviation of 0.10. The unassisted mean is 0.60. Each of the 8 items is a coin flip at
that chance. The test is the plan's two-sided permutation test on the difference in mean accuracy
at alpha 0.05. With 8 items a person's score moves in steps of 12.5 points, so it is noisier than
part 1's and needs a larger difference for the same power.

Usage: uv run python evals/power_v2.py [--sims 2000] [--permutations 1000]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np

from evals.common import RESULTS_DIR, result_header, write_json
from evals.power import PERSON_SD, beta_params
from evals.usability_analysis import ALPHA, permutation_p

SCRIPT = "evals/power_v2.py"
N_ITEMS_V2 = 8
SEED_V2 = 20260926
UNASSISTED_MEAN = 0.60
N_SIMS = 2_000
N_PERM = 1_000
CASES: tuple[dict[str, Any], ...] = (
    {"name": "40_per_arm_12_points", "n_per_arm": 40, "difference_points": 12},
    {"name": "40_per_arm_10_points", "n_per_arm": 40, "difference_points": 10},
    {"name": "20_per_arm_12_points", "n_per_arm": 20, "difference_points": 12},
    {"name": "40_per_arm_0_points", "n_per_arm": 40, "difference_points": 0},
)


def simulate_arm(mean: float, n: int, rng: np.random.Generator) -> np.ndarray:
    """Per-person accuracy over 8 items for n people."""
    a, b = beta_params(mean, PERSON_SD)
    skill = rng.beta(a, b, size=n)
    return rng.binomial(N_ITEMS_V2, skill) / N_ITEMS_V2


def rejection_rate(
    *, n_per_arm: int, difference_points: float, n_sims: int, n_perm: int, seed: int
) -> float:
    rng = np.random.default_rng(seed)
    assisted_mean = UNASSISTED_MEAN + difference_points / 100.0
    rejections = 0
    for _ in range(n_sims):
        unassisted = simulate_arm(UNASSISTED_MEAN, n_per_arm, rng)
        assisted = simulate_arm(assisted_mean, n_per_arm, rng)
        rejections += int(permutation_p(assisted, unassisted, n_perm=n_perm, rng=rng) < ALPHA)
    return rejections / n_sims


def run(*, n_sims: int = N_SIMS, n_perm: int = N_PERM, seed: int = SEED_V2) -> dict[str, Any]:
    result = result_header(SCRIPT, synthetic=False, stamp="power_v2")
    result["model"] = {
        "items": N_ITEMS_V2,
        "unassisted_mean_accuracy": UNASSISTED_MEAN,
        "between_person_sd_of_accuracy": PERSON_SD,
        "skill_distribution": "Beta with the stated mean and sd, one draw per person",
        "item_model": "8 independent coin flips at the person's skill",
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
        cases[case["name"]] = {
            "n_per_arm": case["n_per_arm"],
            "difference_points": case["difference_points"],
            "power": round(power, 3),
            "simulation_se": round(float(np.sqrt(power * (1 - power) / n_sims)), 3),
            "purpose": "type 1 error check, should sit near alpha"
            if case["difference_points"] == 0
            else "power",
        }
    result["cases"] = cases
    result["power_40_per_arm_12_points"] = cases["40_per_arm_12_points"]["power"]
    result["power_20_per_arm_12_points"] = cases["20_per_arm_12_points"]["power"]
    result["false_positive_rate_40_per_arm"] = cases["40_per_arm_0_points"]["power"]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--sims", type=int, default=N_SIMS)
    parser.add_argument("--permutations", type=int, default=N_PERM)
    parser.add_argument("--out", type=Path, default=RESULTS_DIR / "power_v2.json")
    args = parser.parse_args(argv)
    result = run(n_sims=args.sims, n_perm=args.permutations)
    write_json(args.out, result)
    print(
        f"power v2: {result['power_40_per_arm_12_points']:.3f} at 40 per arm for 12 points, "
        f"{result['power_20_per_arm_12_points']:.3f} at 20 per arm for 12 points, "
        f"false positive rate {result['false_positive_rate_40_per_arm']:.3f} at 0 points "
        f"({args.sims} data sets, 8 items)"
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
