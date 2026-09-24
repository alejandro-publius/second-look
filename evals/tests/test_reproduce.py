"""make reproduce: the committed AI numbers regrade exactly, and any changed one is caught.

Each test builds a stand-in repository whose files link to the real ones, copies the one file it
changes, and runs the same checks make reproduce runs. A check that passed a changed number would
be worth nothing, so every kind of number is changed once here: a pass, a right-answer count, a
gate count, a cost, a reply in a fixture, a paid run with no fixture, a call nobody accounts for
and a synthetic answer.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
import yaml

from evals import extract_raw, reproduce
from evals.paid_runs import PAID_RUNS, PaidRun

ROOT = reproduce.ROOT
LATEST_SWEEP = "model_sweep_20260924T054756Z"
LATEST_FOOTAGE = "footage_20260924T060539Z"
LATEST_BENCHMARK = "benchmark_20260924T054939Z"


def stand_in(tmp_path: Path, results: tuple[str, ...] = (), raw: tuple[str, ...] = ()) -> Path:
    """A repository of links to this one. The results and raw fixtures named are copies."""
    root = tmp_path / "repo"
    root.mkdir()
    for name in ("content", "photos"):
        (root / name).symlink_to(ROOT / name)
    evals = root / "evals"
    (evals / "fixtures" / "raw").mkdir(parents=True)
    (evals / "models.yaml").symlink_to(ROOT / "evals" / "models.yaml")
    (evals / "fixtures" / "seeds.json").symlink_to(ROOT / "evals" / "fixtures" / "seeds.json")
    for path in (ROOT / "evals" / "fixtures" / "raw").iterdir():
        target = evals / "fixtures" / "raw" / path.name
        if path.name in raw:
            shutil.copy(path, target)
        else:
            target.symlink_to(path)
    (root / "results").mkdir()
    for path in (ROOT / "results").iterdir():
        if not path.is_file():
            continue
        if path.name in results:
            shutil.copy(path, root / "results" / path.name)
        else:
            (root / "results" / path.name).symlink_to(path)
    return root


def edit_json(path: Path, change: Callable[[Any], None]) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def problems_of(checks: list[reproduce.Check], path: str) -> list[str]:
    return [p for c in checks if c.path == path for p in c.problems]


def all_problems(checks: list[reproduce.Check]) -> list[str]:
    return [f"{c.path}: {p}" for c in checks for p in c.problems]


def test_every_committed_paid_number_regrades_exactly() -> None:
    checks = reproduce.paid_checks(ROOT)
    assert all_problems(checks) == []
    regraded = {c.path: c.values for c in checks}
    for run in PAID_RUNS:
        assert regraded[f"results/{run.results_name}"] > 100, run.results_name
    # Sixteen passes, their 192 run cells and the two real and synthetic marks, all from the
    # latest paid sweep's replies.
    assert regraded["results/model_pass_table.json"] == 16 + 16 * 3 * 4 + 2


def test_a_pass_flipped_in_the_pass_table_is_caught(tmp_path: Path) -> None:
    root = stand_in(tmp_path, results=("model_pass_table.json",))

    def flip(doc: Any) -> None:
        cell = doc["models"]["claude-fable-5-1"]["dug_out_channel"]
        cell["passed"] = not cell["passed"]

    edit_json(root / "results" / "model_pass_table.json", flip)
    found = problems_of(reproduce.paid_checks(root), "results/model_pass_table.json")
    assert any("claude-fable-5-1/dug_out_channel/passed" in p for p in found), found


def test_a_pass_written_as_a_number_is_caught(tmp_path: Path) -> None:
    """1 is not true: the gate reads passed as exactly true, so the file must say exactly true."""
    root = stand_in(tmp_path, results=("model_pass_table.json",))

    def as_number(doc: Any) -> None:
        cell = doc["models"]["claude-haiku-4-5-20251001"]["artificial_bank"]
        assert cell["passed"] is True
        cell["passed"] = 1

    edit_json(root / "results" / "model_pass_table.json", as_number)
    found = problems_of(reproduce.paid_checks(root), "results/model_pass_table.json")
    assert any("artificial_bank/passed: committed 1, regraded True" in p for p in found), found


def test_a_right_answer_count_changed_in_the_benchmark_is_caught(tmp_path: Path) -> None:
    name = f"{LATEST_BENCHMARK}.json"
    root = stand_in(tmp_path, results=(name,))

    def one_more(doc: Any) -> None:
        doc["models"]["claude-haiku-4-5-20251001"]["all"]["correct"] += 1

    edit_json(root / "results" / name, one_more)
    found = problems_of(reproduce.paid_checks(root), f"results/{name}")
    assert any("/correct" in p for p in found), found


def test_a_feature_count_and_its_accuracy_changed_together_are_still_caught(
    tmp_path: Path,
) -> None:
    """Moving a right answer between features keeps the total; the intervals still give it away."""
    name = f"{LATEST_BENCHMARK}.json"
    root = stand_in(tmp_path, results=(name,))

    def move(doc: Any) -> None:
        cells = doc["models"]["claude-sonnet-5"]
        cells["pipe_running"]["correct"] += 1
        cells["pipe_running"]["accuracy"] = round(cells["pipe_running"]["correct"] / 12, 4)
        cells["dug_out_channel"]["correct"] -= 1

    edit_json(root / "results" / name, move)
    found = problems_of(reproduce.paid_checks(root), f"results/{name}")
    assert any("wilson_95" in p for p in found), found


def test_a_model_cut_from_the_pass_table_is_caught(tmp_path: Path) -> None:
    """A number deleted is a number that differs: the gate would read a table the replies do not
    give, so the regrade must not pass it just because what is left still matches."""
    root = stand_in(tmp_path, results=("model_pass_table.json",))
    edit_json(
        root / "results" / "model_pass_table.json",
        lambda doc: doc["models"].pop("claude-haiku-4-5-20251001"),
    )
    found = problems_of(reproduce.paid_checks(root), "results/model_pass_table.json")
    assert any(
        "/models/claude-haiku-4-5-20251001/artificial_bank/passed: regraded True, committed has "
        "nothing there" in p
        for p in found
    ), found


def test_a_drop_reason_cut_from_the_footage_is_caught(tmp_path: Path) -> None:
    name = f"{LATEST_FOOTAGE}.json"
    root = stand_in(tmp_path, results=(name,))
    cut = "feature dug_out_channel not passed by model claude-fable-5-1"

    def drop(doc: Any) -> None:
        del doc["gate"]["drop_reasons"][cut]

    edit_json(root / "results" / name, drop)
    found = problems_of(reproduce.paid_checks(root), f"results/{name}")
    assert f"/gate/drop_reasons/{cut}: regraded 3, committed has nothing there" in found, found


def test_a_model_or_a_cell_cut_from_the_benchmark_is_caught(tmp_path: Path) -> None:
    """The two paid benchmarks kept counts only, so their cells are checked for being all there."""
    name = f"{LATEST_BENCHMARK}.json"
    root = stand_in(tmp_path, results=(name,))
    edit_json(root / "results" / name, lambda doc: doc["models"].pop("claude-fable-5-1"))
    found = problems_of(reproduce.paid_checks(root), f"results/{name}")
    assert any(p.startswith("/models (the models with calls in the cost log)") for p in found)

    (tmp_path / "cell").mkdir()
    root = stand_in(tmp_path / "cell", results=(name,))
    edit_json(
        root / "results" / name,
        lambda doc: doc["models"]["claude-sonnet-5"].pop("malformed"),
    )
    found = problems_of(reproduce.paid_checks(root), f"results/{name}")
    assert any(p.startswith("/models/claude-sonnet-5 (its cells)") for p in found), found


def test_a_gate_count_changed_in_the_footage_is_caught(tmp_path: Path) -> None:
    name = f"{LATEST_FOOTAGE}.json"
    root = stand_in(tmp_path, results=(name,))

    def one_more(doc: Any) -> None:
        doc["gate"]["kept"] += 1

    edit_json(root / "results" / name, one_more)
    checks = reproduce.paid_checks(root)
    assert any("/gate/kept" in p for p in problems_of(checks, f"results/{name}"))
    # footage_latest.json is the newest run's copy, so it no longer matches either.
    assert problems_of(checks, "results/footage_latest.json")


def test_a_cost_changed_in_the_footage_is_caught(tmp_path: Path) -> None:
    name = f"{LATEST_FOOTAGE}.json"
    root = stand_in(tmp_path, results=(name,))

    def cheaper(doc: Any) -> None:
        doc["cost"]["per_100_frames_usd"] = 51.3

    edit_json(root / "results" / name, cheaper)
    found = problems_of(reproduce.paid_checks(root), f"results/{name}")
    assert any("per_100_frames_usd" in p for p in found), found


def test_a_cost_changed_in_the_cost_log_is_caught(tmp_path: Path) -> None:
    root = stand_in(tmp_path, results=("cost_log.jsonl",))
    path = root / "results" / "cost_log.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    line = json.loads(lines[2665])
    line["cost_usd"] = 0.001
    lines[2665] = json.dumps(line, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    found = [p for p in all_problems(reproduce.paid_checks(root)) if "line 2666" in p]
    assert found


def test_a_call_that_no_fixture_accounts_for_is_caught(tmp_path: Path) -> None:
    root = stand_in(tmp_path, results=("cost_log.jsonl",))
    extra = {
        "cost_usd": 0.01,
        "input_tokens": 1000,
        "model": "claude-sonnet-5",
        "output_tokens": 100,
        "purpose": "model_sweep",
        "real": True,
        "ts_utc": "2026-09-25T00:00:00+00:00",
    }
    with (root / "results" / "cost_log.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(extra, sort_keys=True) + "\n")
    found = problems_of(reproduce.paid_checks(root), "results/cost_log.jsonl")
    assert any("no fixture" in p for p in found), found


def test_a_reply_changed_in_a_fixture_is_caught(tmp_path: Path) -> None:
    name = f"{LATEST_SWEEP}.jsonl"
    root = stand_in(tmp_path, raw=(name,))
    path = root / "evals" / "fixtures" / "raw" / name
    lines = path.read_text(encoding="utf-8").splitlines()
    reply = json.loads(lines[1])
    assert reply["raw"]["answer"] == "yes"
    reply["raw"]["answer"] = "no"
    lines[1] = json.dumps(reply, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    found = problems_of(reproduce.paid_checks(root), f"results/{LATEST_SWEEP}.json")
    assert any("/0/answer" in p for p in found), found
    assert any("/0/correct" in p for p in found), found


def test_a_paid_run_with_no_raw_replies_is_caught(tmp_path: Path) -> None:
    root = stand_in(tmp_path)
    (root / "results" / "model_sweep_20260925T000000Z.json").write_text(
        json.dumps({"real": True, "answers": []}), encoding="utf-8"
    )
    found = problems_of(reproduce.paid_checks(root), "results/")
    assert any("model_sweep_20260925T000000Z.json" in p for p in found), found


def test_a_missing_fixture_is_caught(tmp_path: Path) -> None:
    root = stand_in(tmp_path)
    (root / "evals" / "fixtures" / "raw" / f"{LATEST_FOOTAGE}.jsonl").unlink()
    found = problems_of(reproduce.paid_checks(root), "results/")
    assert any(f"{LATEST_FOOTAGE}.jsonl is missing" in p for p in found), found


def test_a_synthetic_answer_changed_is_caught(tmp_path: Path) -> None:
    name = "model_sweep_20260922T054916Z.json"
    root = stand_in(tmp_path, results=(name,))

    def other(doc: Any) -> None:
        first = doc["answers"][0]
        first["answer"] = "no" if first["answer"] == "yes" else "yes"

    edit_json(root / "results" / name, other)
    check, _records = reproduce.synthetic_sweep(f"results/{name}", root)
    assert any("/0/answer" in p for p in check.problems), check.problems


def test_the_committed_synthetic_sweeps_and_benchmarks_regrade_exactly() -> None:
    for stamp in ("20260921T001414Z", "20260921T001651Z", "20260922T054916Z"):
        check, _records = reproduce.synthetic_sweep(f"results/model_sweep_{stamp}.json", ROOT)
        assert check.problems == [] and check.values > 500
    old = reproduce.synthetic_benchmark(
        "results/benchmark_20260921T001415Z.json", ROOT, reproduce.placeholder_pool(ROOT)
    )
    assert old.problems == [] and old.values > 50


def test_the_placeholder_pool_is_needed_for_the_oldest_benchmark() -> None:
    """Without the pool of Sep 20 the oldest fake benchmark is not the run it claims to be."""
    check = reproduce.synthetic_benchmark("results/benchmark_20260921T001415Z.json", ROOT, None)
    assert check.problems == ["the pool is not the photos this run used"]


def benchmark_run_with_answers(root: Path) -> PaidRun:
    """A paid benchmark as a run after this change writes it: answers kept, calls logged."""
    from evals.benchmark import labelled_pool, per_feature_accuracy
    from evals.model_sweep import Query, RawAnswer, load_manifest, record_from

    run = PaidRun("benchmark", "20990101T000000Z", "direct", PAID_RUNS[-1].prices, "a test")
    pool = labelled_pool(load_manifest(root), root)
    pricing = run.pricing()
    records = []
    log = []
    for index, item in enumerate(pool):
        payload = {"answer": "yes" if index % 3 else "no", "note": f"reply {index}"}
        cost = pricing.cost_usd("claude-sonnet-5", 1500, 90, batch=False)
        query = Query(
            custom_id=f"claude-sonnet-5|{item.id}|r0",
            item_id=item.id,
            feature=item.feature,
            question="",
            image_bytes=b"",
            model_id="claude-sonnet-5",
            run=0,
        )
        raw = RawAnswer(payload, "claude-sonnet-5", 1500, 90, cost)
        records.append(record_from(query, raw, item.gold))
        log.append(
            {
                "cost_usd": cost,
                "input_tokens": 1500,
                "model": "claude-sonnet-5",
                "output_tokens": 90,
                "purpose": "benchmark",
                "real": True,
                "ts_utc": "2099-01-01T00:00:00+00:00",
            }
        )
    base = json.loads((ROOT / "results" / f"{LATEST_BENCHMARK}.json").read_text())
    doc = {
        **base,
        "generated_at_utc": "2099-01-01T00:00:00+00:00",
        "runs": 1,
        "models": per_feature_accuracy(records, ["claude-sonnet-5"]),
        "cost_usd": round(sum(r.cost_usd for r in records), 6),
        "answers": [asdict(r) for r in records],
    }
    (root / "results" / run.results_name).write_text(json.dumps(doc), encoding="utf-8")
    (root / "results" / "cost_log.jsonl").write_text(
        "".join(json.dumps(x) + "\n" for x in log), encoding="utf-8"
    )
    lines = extract_raw.fixture_lines(run, log, (run,), root / "results")
    extract_raw.write_fixture(root / "evals" / "fixtures" / "raw" / run.fixture_name, lines)
    return run


def test_a_benchmark_that_kept_its_answers_is_graded_from_every_reply(tmp_path: Path) -> None:
    root = stand_in(tmp_path)
    (root / "results" / "cost_log.jsonl").unlink()
    run = benchmark_run_with_answers(root)
    log = extract_raw.load_cost_log(root / "results" / "cost_log.jsonl")
    check = reproduce.check_benchmark(run, root, log)
    assert check.problems == [] and check.notes == []
    assert check.values > 16 * 8

    def one_more(doc: Any) -> None:
        doc["models"]["claude-sonnet-5"]["pipe_running"]["correct"] += 1
        doc["models"]["claude-sonnet-5"]["all"]["correct"] += 1

    edit_json(root / "results" / run.results_name, one_more)
    check = reproduce.check_benchmark(run, root, log)
    assert any("pipe_running/correct" in p for p in check.problems), check.problems


def test_the_adversarial_pass_is_each_models_last_calls() -> None:
    calls = [
        (n, {"model": model})
        for n, model in enumerate(["a", "b", "a", "b"] + ["a"] * 48 + ["b"] * 48, start=1)
    ]
    passes = extract_raw.split_adversarial(calls, runs_per_item=3)
    assert passes[:4] == ["frames"] * 4
    assert passes[4:] == ["adversarial"] * 96


def test_the_regrade_refuses_the_network_and_fails_if_something_tried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tried: list[str] = []

    def reaching_out(root: Path) -> list[reproduce.Check]:
        try:
            socket.getaddrinfo("example.com", 443)
        except OSError as exc:
            tried.append(str(exc))
        return [reproduce.Check("results/x.json", "a test")]

    monkeypatch.setattr(reproduce, "paid_checks", reaching_out)
    assert reproduce.main(["--paid-only"]) == 1
    assert tried and "no network" in tried[0]


def test_the_regrade_runs_with_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str | None] = []

    def look(root: Path) -> list[reproduce.Check]:
        seen.append(os.environ.get("ANTHROPIC_API_KEY"))
        return [reproduce.Check("results/x.json", "a test")]

    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    monkeypatch.setattr(reproduce, "paid_checks", look)
    assert reproduce.main(["--paid-only"]) == 0
    assert seen == [None]


def test_the_report_fails_on_any_problem_and_names_what_is_not_regraded() -> None:
    lines: list[str] = []
    good = reproduce.Check("results/a.json", "a fixture", values=3)
    skipped = reproduce.not_regraded()
    assert reproduce.report([good, *skipped], lines.append) == 0
    assert any(line.startswith("skip results/consensus_synthetic.json") for line in lines)
    bad = reproduce.Check("results/b.json", "a fixture", values=1, problems=["/x: differs"])
    lines.clear()
    assert reproduce.report([good, bad], lines.append) == 1
    assert "FAIL results/b.json: 1 values regraded from a fixture" in lines


def test_ci_runs_make_reproduce_after_make_check() -> None:
    # REVIEW_03 R49: no test reads results/usability_synthetic.json again, so its p value flipped
    # from 0.051 to 0.049 passed make check; only make reproduce failed. CI runs it as its own step.
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "check.yml").read_text())
    runs = [str(step.get("run", "")).strip() for step in workflow["jobs"]["check"]["steps"]]
    assert "make reproduce" in runs, runs
    assert runs.index("make reproduce") > runs.index("make check")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    recipe = makefile.split("\nreproduce:\n", 1)[1].split("\n\n", 1)[0]
    assert "python evals/reproduce.py" in recipe
    assert not recipe.lstrip().startswith("-"), "a leading - would ignore its failure"
