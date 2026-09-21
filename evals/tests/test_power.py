"""results/power.json exists, is honest about its model, and matches the plan's planning note."""

from __future__ import annotations

import json
import re

import pytest

from evals.common import ROOT
from evals.power import beta_params, rejection_rate, run

POWER_PATH = ROOT / "results" / "power.json"
PLAN_PATH = ROOT / "docs" / "analysis_plan.md"
TOLERANCE = 0.10  # "about 80 percent" is read as 70 to 90


def test_beta_params_recover_the_mean_and_sd() -> None:
    a, b = beta_params(0.6, 0.1)
    mean = a / (a + b)
    var = a * b / ((a + b) ** 2 * (a + b + 1))
    assert mean == pytest.approx(0.6)
    assert var**0.5 == pytest.approx(0.1)
    with pytest.raises(ValueError):
        beta_params(0.6, 0.6)


def planning_note_numbers() -> tuple[float, int, int, int, int]:
    text = PLAN_PATH.read_text(encoding="utf-8")
    m = re.search(
        r"about (\d+) percent power for a (\d+) point difference at (\d+) per arm, "
        r"and for about (\d+) points at (\d+) per arm",
        text,
    )
    assert m, "the planning note sentence in docs/analysis_plan.md item 7 has changed shape"
    return int(m.group(1)) / 100, int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))


def test_power_file_agrees_with_the_planning_note() -> None:
    assert POWER_PATH.exists(), "run: uv run python evals/power.py"
    doc = json.loads(POWER_PATH.read_text(encoding="utf-8"))
    for key in ("generated_at_utc", "script", "synthetic"):
        assert key in doc
    note_power, points_a, n_a, points_b, n_b = planning_note_numbers()
    case_a = doc["cases"][f"{n_a}_per_arm_{points_a}_points"]
    case_b = doc["cases"][f"{n_b}_per_arm_{points_b}_points"]
    disagreements = []
    for label, case in (("40 per arm, 10 points", case_a), ("30 per arm, 12 points", case_b)):
        if abs(case["power"] - note_power) > 0.02:
            disagreements.append(
                f"{label}: simulation {case['power']:.3f} vs planning note {note_power:.2f}"
            )
    if disagreements:
        print("planning note vs simulation: " + "; ".join(disagreements))
    else:
        print(
            "planning note agrees with the simulation: "
            f"{case_a['power']:.3f} and {case_b['power']:.3f}"
        )
    assert abs(case_a["power"] - note_power) <= TOLERANCE, disagreements
    assert abs(case_b["power"] - note_power) <= TOLERANCE, disagreements
    assert doc["false_positive_rate_40_per_arm"] <= 0.08


def test_quick_simulation_has_the_right_shape_and_a_sane_false_positive_rate() -> None:
    alpha_rate = rejection_rate(n_per_arm=40, difference_points=0, n_sims=150, n_perm=300, seed=5)
    assert 0.0 <= alpha_rate <= 0.12
    big = rejection_rate(n_per_arm=40, difference_points=30, n_sims=40, n_perm=200, seed=6)
    assert big >= 0.95
    result = run(n_sims=20, n_perm=100)
    assert set(result["cases"]) == {
        "40_per_arm_10_points",
        "30_per_arm_12_points",
        "40_per_arm_0_points",
    }
    assert result["synthetic"] is False
    assert result["model"]["between_person_sd_of_accuracy"] == 0.10
