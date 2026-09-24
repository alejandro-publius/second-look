"""The committed pass table licenses only what its own runs earned (hard rule 4).

core/gate.py and core/checker.py trust the `passed` cell of results/model_pass_table.json. A hand
edit that turned one cell to true, by a person or by a coding agent, would let a model speak on a
feature it failed, and the gate would never know. Here every cell is graded again from the runs
stored beside it, by the pass rule in the analysis plan, item 8.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.records import FEATURES
from evals.model_sweep import ITEMS_PER_FEATURE, PASS_RUNS_NEEDED, feature_passes

TABLE = Path(__file__).resolve().parents[2] / "results" / "model_pass_table.json"


def committed() -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(TABLE.read_text(encoding="utf-8"))
    return doc


def test_every_passed_cell_follows_from_its_own_runs() -> None:
    table = committed()
    wrong = [
        f"{model} {feature}: says {cell['passed']}, its runs say {feature_passes(cell['runs'])}"
        for model, row in table["models"].items()
        for feature, cell in row.items()
        if cell["passed"] is not feature_passes(cell["runs"])
    ]
    assert wrong == []


def test_every_model_has_every_feature_with_three_full_runs() -> None:
    table = committed()
    assert table["models"], "the pass table names no model"
    for model, row in table["models"].items():
        assert set(row) == set(FEATURES), model
        for feature, cell in row.items():
            runs = cell["runs"]
            assert len(runs) == 3, (model, feature)
            assert all(len(run) == ITEMS_PER_FEATURE for run in runs), (model, feature)
            assert all(isinstance(v, bool) for run in runs for v in run), (model, feature)
            assert isinstance(cell["passed"], bool), (model, feature)


def test_the_table_is_from_a_real_run_and_states_the_rule_it_used() -> None:
    table = committed()
    assert table["real"] is True and table["synthetic"] is False
    assert f"at least {PASS_RUNS_NEEDED} of 3 runs" in table["pass_rule"]
