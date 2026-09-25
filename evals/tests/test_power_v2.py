"""results/power_v2.json exists and matches the planning note in docs/analysis_plan_v2.md."""

from __future__ import annotations

import json
import re

from evals.common import ROOT
from evals.power_v2 import N_ITEMS_V2, SEED_V2, rejection_rate, simulate_arm

POWER_PATH = ROOT / "results" / "power_v2.json"
PLAN_PATH = ROOT / "docs" / "analysis_plan_v2.md"


def test_simulated_scores_move_in_eighths() -> None:
    import numpy as np

    scores = simulate_arm(0.6, 500, np.random.default_rng(1))
    assert set(np.round(scores * N_ITEMS_V2, 9)) <= set(range(N_ITEMS_V2 + 1))


def test_plan_quotes_the_committed_simulation() -> None:
    doc = json.loads(POWER_PATH.read_text(encoding="utf-8"))
    assert doc["model"]["items"] == 8
    assert doc["model"]["seed"] == SEED_V2
    text = PLAN_PATH.read_text(encoding="utf-8")
    m = re.search(
        r"about (\d+) percent power for a (\d+) point difference at (\d+) per arm, "
        r"and about (\d+) percent at (\d+) per arm",
        text,
    )
    assert m, "the planning note sentence in docs/analysis_plan_v2.md item 7 changed shape"
    p40, points, n40, p20, n20 = (int(g) for g in m.groups())
    case40 = doc["cases"][f"{n40}_per_arm_{points}_points"]
    case20 = doc["cases"][f"{n20}_per_arm_{points}_points"]
    assert round(case40["power"] * 100) == p40
    assert round(case20["power"] * 100) == p20
    assert "evals/power_v2.py" in text and "results/power_v2.json" in text


def test_no_difference_rejects_near_alpha() -> None:
    rate = rejection_rate(n_per_arm=30, difference_points=0, n_sims=300, n_perm=200, seed=7)
    assert rate < 0.12
