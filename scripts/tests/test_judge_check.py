"""judge-check's FHIR step, against the results file the validator really writes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import judge_check

COMMITTED = judge_check.ROOT / "results" / "fhir_validation.json"


def no_golden_run(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Stand in for the golden Bundle pytest run, so only the reading of the file is tested."""
    calls: list[list[str]] = []

    def fake_run(argv: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str]:
        calls.append(argv)
        return 0, "1 passed"

    monkeypatch.setattr(judge_check, "run", fake_run)
    return calls


def validator_line(step: judge_check.Step) -> str:
    lines = [ln for ln in step.lines if ln.startswith("last validator run:")]
    assert len(lines) == 1, step.lines
    return lines[0]


def test_the_fhir_step_reads_the_committed_validation_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = json.loads(COMMITTED.read_text(encoding="utf-8"))
    assert isinstance(data["files"], list), "the validator writes files as a list of paths"
    calls = no_golden_run(monkeypatch)
    step = judge_check.step_fhir(judge_check.ROOT, {})
    assert step.ok == (data["errors"] == 0)
    line = validator_line(step)
    assert f"{data['files_validated']} file(s)" in line
    assert f"at {data['ig_commit']}" in line
    assert calls and "core/tests/test_fhir_emit.py" in calls[0]


def test_without_a_count_the_fhir_step_counts_the_list_of_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "results").mkdir()
    doc = {"errors": 0, "ig_commit": "b907cf0", "files": ["fhir/golden/a.json", "b.json"]}
    (tmp_path / "results" / "fhir_validation.json").write_text(json.dumps(doc), encoding="utf-8")
    no_golden_run(monkeypatch)
    step = judge_check.step_fhir(tmp_path, {})
    assert step.ok
    assert "2 file(s)" in validator_line(step)


def test_an_error_in_the_last_run_fails_the_fhir_step(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "results").mkdir()
    doc = {"errors": 3, "files_validated": 1, "files": ["a.json"], "ig_commit": "b907cf0"}
    (tmp_path / "results" / "fhir_validation.json").write_text(json.dumps(doc), encoding="utf-8")
    no_golden_run(monkeypatch)
    step = judge_check.step_fhir(tmp_path, {})
    assert not step.ok
    assert step.lines[0] == "3 validation error(s) in the last run"


def test_the_reproduce_step_runs_make_reproduce_and_reports_its_last_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    last = "reproduce: 3 values in 1 files regraded from raw replies and seeds"

    def fake_run(argv: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str]:
        calls.append(argv)
        return 0, f"ok   results/a.json: 3 values regraded from a fixture\n{last}\n"

    monkeypatch.setattr(judge_check, "run", fake_run)
    step = judge_check.step_reproduce(judge_check.ROOT, {})
    assert step.ok
    assert calls == [["make", "--no-print-directory", "reproduce"]]
    assert step.lines == [last]


def test_a_number_that_does_not_reproduce_fails_the_step_and_names_the_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = (
        "ok   results/a.json: 3 values regraded from a fixture\n"
        "FAIL results/b.json: 1 values regraded from a fixture\n"
        "       /gate/kept: committed 36, regraded 35\n"
        "reproduce: 1 of 2 files differ from the raw replies or seeds\n"
    )
    monkeypatch.setattr(judge_check, "run", lambda argv, cwd, env: (1, out))
    step = judge_check.step_reproduce(judge_check.ROOT, {})
    assert not step.ok
    assert step.lines[0] == (
        "make reproduce failed: reproduce: 1 of 2 files differ from the raw replies or seeds"
    )
    assert "FAIL results/b.json: 1 values regraded from a fixture" in step.lines


def test_judge_check_runs_the_reproduce_step_second(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ran: list[str] = []
    for name in ("tests", "reproduce", "fhir", "audit", "secrets"):

        def stand_in(*args: object, _name: str = name) -> judge_check.Step:
            ran.append(_name)
            return judge_check.Step(_name, lines=[f"{_name} ok"])

        monkeypatch.setattr(judge_check, f"step_{name}", stand_in)
    assert judge_check.main(["--quick"]) == 0
    assert ran == ["tests", "reproduce", "fhir", "audit", "secrets"]
    assert "6 of 6 steps passed" in capsys.readouterr().out
