"""Benchmark, agreement and ablation harnesses: Wilson intervals, kappa, the vote, the files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from scipy.stats import binomtest

from core.records import FEATURES
from evals import ablation, agreement, benchmark
from evals.ablation import SiteContext, combine, wet_weather_rule
from evals.agreement import cohens_kappa, pairs_from_csvs, summarise
from evals.benchmark import labelled_pool, per_feature_accuracy, skipped_rows, wilson_interval
from evals.model_sweep import REFUSAL_NO_KEY, AnswerRecord

MODEL_IDS = (
    "claude-haiku-4-5-20251001",
    "claude-sonnet-5",
    "claude-opus-5-5",
    "claude-fable-5-1",
)

# Wilson -----------------------------------------------------------------------------------------


@pytest.mark.parametrize("k,n", [(0, 4), (4, 4), (2, 4), (13, 16), (7, 40), (150, 150), (1, 1)])
def test_wilson_matches_scipy(k: int, n: int) -> None:
    lo, hi = wilson_interval(k, n)
    ref = binomtest(k, n).proportion_ci(confidence_level=0.95, method="wilson")
    assert lo == pytest.approx(ref.low, abs=1e-9)
    assert hi == pytest.approx(ref.high, abs=1e-9)


def test_wilson_edges() -> None:
    assert wilson_interval(0, 0) == (0.0, 1.0)
    lo, hi = wilson_interval(0, 4)
    assert lo == 0.0 and 0.0 < hi < 1.0
    lo, hi = wilson_interval(4, 4)
    assert 0.0 < lo < 1.0 and hi == 1.0
    lo, hi = wilson_interval(8, 16)
    assert lo < 0.5 < hi


# pool -------------------------------------------------------------------------------------------


def row(**kw: str) -> dict[str, str]:
    base = {
        "id": "x",
        "file": "placeholders/x.jpg",
        "license": "placeholder",
        "role": "test",
        "feature": "artificial_bank",
        "gold_label": "present",
    }
    return base | kw


def test_labelled_pool_keeps_only_labelled_benchmark_and_test_rows() -> None:
    manifest = {
        "a": row(id="a"),
        "b": row(id="b", role="benchmark", gold_label="absent", license="CC-BY-4.0"),
        "c": row(id="c", role="benchmark", gold_label=""),
        "d": row(id="d", role="lesson"),
        "e": row(id="e", gold_label="ambiguous"),
        "f": row(id="f", feature="graffiti"),
    }
    pool = labelled_pool(manifest)
    assert [i.id for i in pool] == ["a", "b"]
    assert pool[0].is_placeholder and not pool[1].is_placeholder
    assert skipped_rows(manifest) == 3


def rec(model: str, feature: str, correct: bool, answer: str = "yes") -> AnswerRecord:
    return AnswerRecord(
        model=model,
        item_id="i",
        feature=feature,
        gold="present",
        run=0,
        custom_id="c",
        answer=answer,  # type: ignore[arg-type]
        note="",
        correct=correct,
        malformed=False,
        reason="",
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
        error=None,
        raw=None,
    )


def test_per_feature_accuracy_cells() -> None:
    records = [
        rec("m", "artificial_bank", True),
        rec("m", "artificial_bank", False, "cant_tell"),
        rec("m", "pipe_running", True),
    ]
    cells = per_feature_accuracy(records, ["m"])["m"]
    assert cells["artificial_bank"]["n"] == 2 and cells["artificial_bank"]["accuracy"] == 0.5
    assert cells["dug_out_channel"]["n"] == 0 and cells["dug_out_channel"]["accuracy"] is None
    assert cells["all"]["correct"] == 2 and cells["all"]["n"] == 3
    assert cells["cant_tell_share"] == pytest.approx(1 / 3, abs=1e-4)
    lo, hi = cells["artificial_bank"]["wilson_95"]
    assert lo <= 0.5 <= hi


def test_benchmark_main_synthetic_writes_a_stamped_file(tmp_path: Path, capsys: Any) -> None:
    code = benchmark.main(["--synthetic", "--seed", "3", "--results-dir", str(tmp_path)])
    assert code == 0
    files = list(tmp_path.glob("benchmark_*.json"))
    assert len(files) == 1
    doc = json.loads(files[0].read_text())
    assert doc["synthetic"] is True and doc["stamp"] == "SYNTHETIC" and doc["real"] is False
    # Every test photo carries the label chosen at picking now, so nothing is skipped for want
    # of one. It was 2 while the manifest held unlabelled gray placeholders.
    assert doc["pool"]["n_photos"] == 16 and doc["pool"]["skipped_unlabelled"] == 0
    assert set(doc["models"]) == set(MODEL_IDS)
    for cells in doc["models"].values():
        for f in (*FEATURES, "all"):
            lo, hi = cells[f]["wilson_95"]
            assert 0.0 <= lo <= cells[f]["accuracy"] <= hi <= 1.0
    assert "SYNTHETIC" in capsys.readouterr().out
    assert (tmp_path / "cost_log.jsonl").exists()


def test_the_benchmark_keeps_every_answer_with_its_reply(tmp_path: Path) -> None:
    """make reproduce grades a benchmark again from its replies, so the run must keep them."""
    assert benchmark.main(["--synthetic", "--seed", "3", "--results-dir", str(tmp_path)]) == 0
    doc = json.loads(next(tmp_path.glob("benchmark_*.json")).read_text())
    answers = doc["answers"]
    assert len(answers) == 16 * len(MODEL_IDS)
    for model_id, cells in doc["models"].items():
        mine = [a for a in answers if a["model"] == model_id]
        assert sum(a["correct"] for a in mine) == cells["all"]["correct"]
    first = answers[0]
    assert {"raw", "input_tokens", "output_tokens", "custom_id", "error"} <= set(first)
    assert first["raw"] is not None


def test_benchmark_real_refuses_without_a_key(tmp_path: Path, capsys: Any) -> None:
    code = benchmark.main(
        ["--real", "--env-file", str(tmp_path / "none.env"), "--results-dir", str(tmp_path)],
        environ={},
    )
    assert code == 2
    assert capsys.readouterr().out.strip() == REFUSAL_NO_KEY
    assert list(tmp_path.glob("benchmark_*.json")) == []


# agreement --------------------------------------------------------------------------------------


def test_kappa_known_values() -> None:
    assert cohens_kappa(["p", "a", "p"], ["p", "a", "p"]) == pytest.approx(1.0)
    a = ["y", "y", "n", "n", "y", "n", "y", "y"]
    b = ["y", "n", "n", "n", "y", "y", "y", "y"]
    assert cohens_kappa(a, b) == pytest.approx(0.21875 / 0.46875)
    assert cohens_kappa(["p", "p"], ["p", "p"]) is None, "one category only is undefined"
    assert cohens_kappa([], []) is None
    with pytest.raises(ValueError):
        cohens_kappa(["p"], [])


def test_kappa_is_near_zero_for_independent_labels() -> None:
    a = ["p", "a"] * 50
    b = ["p", "p", "a", "a"] * 25
    assert cohens_kappa(a, b) == pytest.approx(0.0, abs=1e-9)


def test_summarise_says_plainly_when_a_column_is_empty() -> None:
    pairs: dict[str, list[tuple[str, str]]] = {f: [] for f in FEATURES}
    missing_b: dict[str, int] = dict.fromkeys(FEATURES, 4)
    missing_a: dict[str, int] = dict.fromkeys(FEATURES, 0)
    features, sentence = summarise(
        pairs, missing_a, missing_b, name_a="gold_label", name_b="labeller_2"
    )
    assert sentence == (
        "The labeller_2 column is empty for every photo, so there is no agreement to compute yet."
    )
    assert all(cell["kappa"] is None for cell in features.values())


def test_agreement_main_on_the_manifest(tmp_path: Path, capsys: Any) -> None:
    code = agreement.main(["--results-dir", str(tmp_path)])
    assert code == 0
    out = capsys.readouterr().out
    files = list(tmp_path.glob("agreement_*.json"))
    assert len(files) == 1
    doc = json.loads(files[0].read_text())
    assert set(doc["features"]) == set(FEATURES)
    assert doc["sentence"] in out
    if doc["n_placeholders_in_pool"]:
        assert doc["synthetic"] is True and doc["stamp"] == "SYNTHETIC"
    for cell in doc["features"].values():
        assert cell["kappa"] is None or -1.0 <= cell["kappa"] <= 1.0


def test_agreement_from_two_csvs(tmp_path: Path, capsys: Any) -> None:
    a = tmp_path / "rachel.csv"
    b = tmp_path / "alex.csv"
    a.write_text(
        "id,feature,label\n"
        "p1,pipe_running,present\np2,pipe_running,absent\np3,pipe_running,present\n"
        "p4,pipe_running,absent\np5,artificial_bank,present\n",
        encoding="utf-8",
    )
    b.write_text(
        "id,feature,label\n"
        "p1,pipe_running,present\np2,pipe_running,absent\np3,pipe_running,absent\n"
        "p4,pipe_running,absent\np6,artificial_bank,absent\n",
        encoding="utf-8",
    )
    pairs, ma, mb = pairs_from_csvs(a, b)
    assert len(pairs["pipe_running"]) == 4 and pairs["artificial_bank"] == []
    assert ma["artificial_bank"] == 1 and mb["artificial_bank"] == 1
    code = agreement.main(["--a", str(a), "--b", str(b), "--results-dir", str(tmp_path)])
    assert code == 0
    doc = json.loads(next(tmp_path.glob("agreement_*.json")).read_text())
    assert doc["synthetic"] is False
    assert doc["features"]["pipe_running"]["kappa"] == pytest.approx(0.5)
    assert "Kappa over all 4" in capsys.readouterr().out


def test_agreement_needs_both_csvs(capsys: Any) -> None:
    assert agreement.main(["--a", "only.csv"]) == 2
    assert "both" in capsys.readouterr().out


# ablation ---------------------------------------------------------------------------------------

DRY = SiteContext(rain="dry", dry_days=7)
WET = SiteContext(rain="wet", dry_days=0)


def test_combine_is_a_plain_vote_where_cant_tell_abstains() -> None:
    assert combine("cant_tell", "cant_tell", "cant_tell", feature="invasive_plant", site=DRY) == (
        "cant_tell"
    )
    assert combine("yes", "yes", "no", feature="invasive_plant", site=DRY) == "yes"
    assert combine("no", "cant_tell", "no", feature="invasive_plant", site=DRY) == "no"
    assert combine("yes", "no", "cant_tell", feature="invasive_plant", site=DRY) == "cant_tell"
    assert combine("yes", "no", "no", feature="invasive_plant", site=DRY) == "no"
    assert combine("yes", "cant_tell", "no", feature="invasive_plant", site=DRY) == "no"


def test_wet_weather_downgrades_a_running_pipe_only() -> None:
    assert wet_weather_rule("yes", "pipe_running", WET) == "cant_tell"
    assert wet_weather_rule("yes", "pipe_running", DRY) == "yes"
    assert wet_weather_rule("no", "pipe_running", WET) == "no"
    assert wet_weather_rule("yes", "artificial_bank", WET) == "yes"
    assert combine("yes", "yes", "yes", feature="pipe_running", site=WET) == "cant_tell"


def test_ablation_main_writes_four_conditions(tmp_path: Path, capsys: Any) -> None:
    code = ablation.main(["--synthetic", "--seed", "11", "--results-dir", str(tmp_path)])
    assert code == 0
    doc = json.loads(next(tmp_path.glob("ablation_*.json")).read_text())
    assert doc["synthetic"] is True and doc["stamp"] == "SYNTHETIC" and doc["stubs"] is True
    assert set(doc["conditions"]) == set(ablation.CONDITIONS)
    for cells in doc["conditions"].values():
        assert cells["all"]["n"] == 16
        lo, hi = cells["all"]["wilson_95"]
        assert 0.0 <= lo <= cells["all"]["accuracy"] <= hi <= 1.0
    assert doc["adversarial_yes_answers"] == []
    assert len(doc["per_item"]) == 16
    assert "SYNTHETIC" in capsys.readouterr().out


def test_ablation_requires_the_synthetic_flag() -> None:
    with pytest.raises(SystemExit):
        ablation.main([])
