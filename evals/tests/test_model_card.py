"""The model card's counts: the sweep behind the pass table, and the paid calls in the cost log."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evals import model_card

STAMP = "2026-09-24T05:47:56+00:00"


def answer(model: str, feature: str, given: str, correct: bool) -> dict[str, Any]:
    return {"model": model, "feature": feature, "answer": given, "correct": correct}


def fixture(tmp_path: Path, *, stamp: str = STAMP, real: bool = True) -> Path:
    results = tmp_path / "results"
    results.mkdir()
    (results / "model_pass_table.json").write_text(json.dumps({"generated_at_utc": STAMP}))
    (results / "model_sweep_a.json").write_text(
        json.dumps({"generated_at_utc": "2026-09-01T00:00:00+00:00", "real": True, "answers": []})
    )
    answers = [
        answer("m1", "invasive_plant", "cant_tell", False),
        answer("m1", "invasive_plant", "yes", True),
        answer("m2", "invasive_plant", "cant_tell", False),
        answer("m2", "pipe_running", "no", True),
        {**answer("m2", "pipe_running", "cant_tell", False), "malformed": True},
    ]
    (results / "model_sweep_b.json").write_text(
        json.dumps({"generated_at_utc": stamp, "real": real, "answers": answers})
    )
    lines = [
        {
            "real": True,
            "purpose": "footage",
            "cost_usd": 0.25,
            "ts_utc": "2026-09-24T06:00:00Z",
            "model": "m1",
        },
        {
            "real": True,
            "purpose": "footage",
            "cost_usd": 0.5,
            "ts_utc": "2026-09-24T03:00:00Z",
            "model": "m1",
        },
        {"real": True, "purpose": "benchmark", "cost_usd": 1.0, "ts_utc": "2026-09-24T04:00:00Z"},
        {"real": False, "purpose": "benchmark", "cost_usd": 9.0, "ts_utc": "2026-09-22T00:00:00Z"},
    ]
    (results / "cost_log.jsonl").write_text("".join(json.dumps(r) + "\n" for r in lines))
    (tmp_path / "content").mkdir()
    golds = ["present", "present", "absent", "absent", "absent"]
    items = "".join(f"  - {{ id: t{i}, gold: {g} }}\n" for i, g in enumerate(golds))
    (tmp_path / "content" / "test_items.yaml").write_text("items:\n" + items)
    return tmp_path


def test_the_committed_file_is_what_the_sweep_and_the_cost_log_say() -> None:
    committed = json.loads(model_card.OUT.read_text(encoding="utf-8"))
    assert committed == model_card.build(), "run: uv run python evals/model_card.py"
    assert model_card.main(["--check"]) == 0


def test_the_sweep_is_the_one_with_the_pass_tables_time_stamp(tmp_path: Path) -> None:
    doc = model_card.build(fixture(tmp_path))
    assert doc["sweep"] == "results/model_sweep_b.json"
    plants = doc["by_feature"]["invasive_plant"]
    assert plants == {
        "answers": 3,
        "yes": 1,
        "no": 0,
        "cant_tell": 2,
        "correct": 1,
        "malformed": 0,
    }
    assert doc["by_feature"]["pipe_running"]["malformed"] == 1
    assert doc["by_model_and_feature"]["m2"]["invasive_plant"]["cant_tell"] == 1
    assert doc["by_model_and_feature"]["m1"]["pipe_running"]["answers"] == 0


@pytest.mark.parametrize(("stamp", "real"), [("2026-09-02T00:00:00+00:00", True), (STAMP, False)])
def test_no_real_sweep_with_the_stamp_is_refused(tmp_path: Path, stamp: str, real: bool) -> None:
    with pytest.raises(model_card.SweepNotFound):
        model_card.build(fixture(tmp_path, stamp=stamp, real=real))


def test_only_real_calls_are_summed_and_the_fake_ones_are_counted_apart(tmp_path: Path) -> None:
    spent = model_card.build(fixture(tmp_path))["cost"]
    assert (spent["calls"], spent["real_calls"], spent["fake_calls"]) == (4, 3, 1)
    assert spent["real_usd"] == 1.75
    assert spent["real_usd_by_purpose"] == {"benchmark": 1.0, "footage": 0.75}
    assert spent["first_real_call_utc"] == "2026-09-24T03:00:00Z"
    assert spent["last_real_call_utc"] == "2026-09-24T06:00:00Z"
    assert spent["log"] == "results/cost_log.jsonl"
    # One footage call, by model, in cents: (0.25 + 0.5) / 2 dollars.
    assert spent["footage_cents_per_call"] == {"m1": 37.5}


def bench(real: bool, correct: int) -> dict[str, Any]:
    return {
        "real": real,
        "runs": 3,
        "interval": "Wilson score, 95 percent",
        "pool": {"n_photos": 16},
        "models": {
            "m1": {
                "all": {"correct": correct, "n": 12, "wilson_95": [0.552, 0.953]},
                "pipe_running": {"correct": 0, "n": 12, "wilson_95": [0.0, 0.2425]},
                "invasive_plant": {"correct": 0, "n": 12, "wilson_95": [0.0, 0.2425]},
                "artificial_bank": {"correct": 9, "n": 12, "wilson_95": [0.5, 0.9]},
                "cant_tell_share": 0.2708,
                "malformed": 0,
            }
        },
    }


def test_the_newest_real_benchmark_is_copied_with_intervals_in_whole_percent(
    tmp_path: Path,
) -> None:
    root = fixture(tmp_path)
    results = root / "results"
    (results / "benchmark_20260921T000000Z.json").write_text(json.dumps(bench(True, 1)))
    (results / "benchmark_20260923T000000Z.json").write_text(json.dumps(bench(True, 10)))
    (results / "benchmark_20260925T000000Z.json").write_text(json.dumps(bench(False, 12)))
    block = model_card.build(root)["benchmark"]
    assert block["file"] == "results/benchmark_20260923T000000Z.json"
    assert (block["runs"], block["photos"]) == (3, 16)
    assert block["models"]["m1"] == {
        "all": {"correct": 10, "n": 12, "low_pct": 55, "high_pct": 95},
        "pipe_running": {"correct": 0, "n": 12, "low_pct": 0, "high_pct": 24},
        "invasive_plant": {"correct": 0, "n": 12, "low_pct": 0, "high_pct": 24},
        "artificial_bank": {"correct": 9, "n": 12, "low_pct": 50, "high_pct": 90},
        "cant_tell_pct": 27,
        # Right answers on everything but the plant photos, and the floor of always answering No.
        "without_plants": {"correct": 9, "n": 24},
    }
    assert block["always_no"] == {"correct": 9, "n": 15}


def test_no_real_benchmark_gives_none(tmp_path: Path) -> None:
    assert model_card.build(fixture(tmp_path))["benchmark"] is None


def test_check_fails_when_the_committed_file_is_stale(tmp_path: Path, monkeypatch: Any) -> None:
    stale = tmp_path / "model_card.json"
    stale.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(model_card, "OUT", stale)
    assert model_card.main(["--check"]) == 1
