"""README examples are picked by the plan's rule, never by hand."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.common import load_test_items, write_json
from evals.pick_examples import best_model, main, pick, synthetic_model_accuracy


def test_pick_takes_the_three_largest_gaps_in_either_direction() -> None:
    per_item = {
        "t01": {"trained": 0.9, "feature": "a", "gold": "present", "photo_id": "p1"},
        "t02": {"trained": 0.5, "feature": "a", "gold": "absent", "photo_id": "p2"},
        "t03": {"trained": 0.7, "feature": "b", "gold": "present", "photo_id": "p3"},
        "t04": {"trained": 0.6, "feature": "b", "gold": "absent", "photo_id": "p4"},
        "t05": {"trained": None, "feature": "c", "gold": "absent", "photo_id": "p5"},
    }
    model = {"t01": 0.2, "t02": 0.95, "t03": 0.7, "t04": 0.75, "t05": 1.0}
    picked = pick(per_item, model)
    assert [p["item_id"] for p in picked] == ["t01", "t02", "t04"]
    assert picked[0]["direction"] == "people ahead" and picked[1]["direction"] == "model ahead"
    assert picked[0]["gap_points"] == 70.0 and picked[1]["gap_points"] == -45.0


def test_pick_breaks_ties_by_item_id() -> None:
    per_item = {f"t{i:02d}": {"trained": 0.5} for i in range(1, 6)}
    model = {f"t{i:02d}": 0.8 for i in range(1, 6)}
    assert [p["item_id"] for p in pick(per_item, model)] == ["t01", "t02", "t03"]


def test_best_model_is_the_highest_mean_with_a_stable_tie_break() -> None:
    models = {
        "zeta": {"t01": 0.5, "t02": 0.5},
        "alpha": {"t01": 0.6, "t02": 0.4},
        "mid": {"t01": 0.9, "t02": 0.5},
    }
    assert best_model(models) == ("mid", pytest.approx(0.7))
    with pytest.raises(ValueError):
        best_model({})


def _fake_usability(path: Path, *, synthetic: bool) -> None:
    per_item = {
        row["id"]: {
            "feature": row["feature"],
            "gold": row["gold"],
            "photo_id": row["photo_id"],
            "trained": 0.5 + i / 40,
        }
        for i, row in enumerate(load_test_items())
    }
    write_json(
        path,
        {
            "synthetic": synthetic,
            "stamp": "SYNTHETIC" if synthetic else "20260928",
            "per_item": per_item,
        },
    )


def test_main_writes_a_synthetic_model_file_when_missing(tmp_path: Path) -> None:
    _fake_usability(tmp_path / "usability_synthetic.json", synthetic=True)
    assert main(["--synthetic", "--results-dir", str(tmp_path)]) == 0
    model_doc = json.loads((tmp_path / "model_item_accuracy.json").read_text())
    assert (
        model_doc["synthetic"] is True
        and model_doc["real"] is False
        and model_doc["stamp"] == "SYNTHETIC"
    )
    assert set(model_doc["models"]) and all(len(v) == 16 for v in model_doc["models"].values())
    examples = json.loads((tmp_path / "examples.json").read_text())
    assert examples["synthetic"] is True and examples["stamp"] == "SYNTHETIC"
    assert len(examples["examples"]) == 3
    gaps = [abs(e["gap_points"]) for e in examples["examples"]]
    assert gaps == sorted(gaps, reverse=True)
    assert examples["best_model"]["model_id"] in model_doc["models"]


def test_main_uses_an_existing_model_file(tmp_path: Path) -> None:
    _fake_usability(tmp_path / "usability_synthetic.json", synthetic=True)
    doc = synthetic_model_accuracy(seed=3)
    doc["models"] = {"only": {row["id"]: 1.0 for row in load_test_items()}}
    write_json(tmp_path / "model_item_accuracy.json", doc)
    assert main(["--synthetic", "--results-dir", str(tmp_path)]) == 0
    examples = json.loads((tmp_path / "examples.json").read_text())
    assert examples["best_model"]["model_id"] == "only"
    assert all(e["direction"] == "model ahead" for e in examples["examples"])


def test_real_mode_refuses_synthetic_inputs(tmp_path: Path) -> None:
    _fake_usability(tmp_path / "usability_synthetic.json", synthetic=True)
    assert main(["--results-dir", str(tmp_path)]) != 0
    assert (
        main(
            [
                "--results-dir",
                str(tmp_path),
                "--usability",
                str(tmp_path / "usability_synthetic.json"),
            ]
        )
        != 0
    )
    _fake_usability(tmp_path / "usability_20260928.json", synthetic=False)
    with pytest.raises(SystemExit):
        main(["--results-dir", str(tmp_path)])  # real usability but no real model file
