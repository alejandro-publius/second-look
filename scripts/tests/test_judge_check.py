"""judge-check's FHIR step, against the results file the validator really writes."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
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
    assert step.notes == []


def reproduce_output_with_notes() -> str:
    """What make reproduce prints for two files with the same note, one with its own and a skip,
    printed by evals/reproduce.py's own report, so the parser reads the real format."""
    from evals import reproduce

    first = reproduce.Check("results/benchmark_a.json", "a fixture", values=5)
    second = reproduce.Check("results/benchmark_b.json", "a fixture", values=5)
    for check in (first, second):
        check.notes.append("the right-answer counts per feature are as recorded")
    footage = reproduce.Check("results/footage_a.json", "a fixture", values=7)
    footage.notes.append("the adversarial answers are as recorded")
    lines: list[str] = []
    assert reproduce.report([first, second, footage, *reproduce.not_regraded()], lines.append) == 0
    return "\n".join(lines) + "\n"


def test_the_reproduce_step_keeps_every_note_and_every_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Judge walk 01, R02: the benchmark runs kept counts, not replies, and make reproduce says so
    # in a note under the file. The step kept only the last line, so the README said every
    # number was regraded from a reply.
    out = reproduce_output_with_notes()
    monkeypatch.setattr(judge_check, "run", lambda argv, cwd, env: (0, out))
    step = judge_check.step_reproduce(judge_check.ROOT, {})
    assert step.ok
    assert step.lines == [judge_check.last_line(out)]
    assert step.notes[:2] == [
        "note on results/benchmark_a.json and results/benchmark_b.json: "
        "the right-answer counts per feature are as recorded",
        "note on results/footage_a.json: the adversarial answers are as recorded",
    ]
    skipped = [n for n in step.notes[2:] if ": not regraded: " in n]
    assert len(skipped) == len(step.notes) - 2 == 3, step.notes
    assert skipped[0].startswith("note on results/ablation_20260921T001415Z.json: not regraded:")


def test_the_summary_and_its_file_carry_the_reproduce_notes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    notes = ["note on results/b.json: the counts are as recorded", "note on results/c.json: x"]

    def stand_in(name: str) -> object:
        def make(*args: object) -> judge_check.Step:
            step = judge_check.Step(name, lines=[f"{name} ok"])
            if name == "reproduce":
                step.notes = list(notes)
            return step

        return make

    for name in ("tests", "reproduce", "fhir", "audit", "secrets"):
        monkeypatch.setattr(judge_check, f"step_{name}", stand_in(name))
    out = tmp_path / "judge_check.json"
    assert judge_check.main(["--quick", "--out", str(out)]) == 0
    summary = capsys.readouterr().out.split("\n\n", 1)[1]
    lines = summary.splitlines()
    at = next(i for i, ln in enumerate(lines) if "reproduce ok" in ln)
    assert [ln.strip() for ln in lines[at + 1 : at + 3]] == notes
    step = json.loads(out.read_text(encoding="utf-8"))["steps"][1]
    assert step["name"] == "reproduce"
    assert step["text"] == "; ".join(["reproduce ok", *notes])


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


def test_the_tests_step_shows_how_many_python_tests_passed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # REVIEW_03 R47: pyproject.toml's addopts already hold -q, and one more -q hid the count, so
    # the line read "python: .... [100%]". A real pytest runs here on the same addopts, with the
    # arguments step_tests gives, in place of uv run.
    pyproject = (judge_check.ROOT / "pyproject.toml").read_text(encoding="utf-8")
    addopts = next(ln for ln in pyproject.splitlines() if ln.startswith("addopts"))
    (tmp_path / "pyproject.toml").write_text(f"[tool.pytest.ini_options]\n{addopts}\n")
    (tmp_path / "test_one.py").write_text("def test_one():\n    assert True\n")

    def real_pytest(argv: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, str]:
        assert argv[:3] == ["uv", "run", "pytest"]
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", *argv[3:]],
            cwd=cwd,
            env={**os.environ, "PYTEST_ADDOPTS": ""},
            capture_output=True,
            text=True,
        )
        return proc.returncode, proc.stdout + proc.stderr

    monkeypatch.setattr(judge_check, "run", real_pytest)
    step = judge_check.step_tests(tmp_path, {})
    assert step.ok, step.lines
    assert re.fullmatch(r"python: 1 passed in [\d.]+s", step.lines[0]), step.lines


def test_the_tests_step_runs_with_no_key_and_a_proxy_that_goes_nowhere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # REVIEW_03 R56: the docstring promised a dead proxy, but only two flags nobody reads were set.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    monkeypatch.setenv("http_proxy", "http://proxy.example:8080")
    seen: dict[str, dict[str, str]] = {}

    def stand_in(root: Path, env: dict[str, str], *rest: object) -> judge_check.Step:
        seen.setdefault("env", dict(env))
        return judge_check.Step("stand in", lines=["ok"])

    for name in ("tests", "reproduce", "fhir", "audit", "secrets"):
        monkeypatch.setattr(judge_check, f"step_{name}", stand_in)
    assert judge_check.main(["--quick"]) == 0
    env = seen["env"]
    assert "ANTHROPIC_API_KEY" not in env
    # What a Python client in that environment would really use, read in a fresh interpreter.
    code = "import json, urllib.request as u; print(json.dumps(u.getproxies()))"
    out = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
    ).stdout
    proxies = json.loads(out)
    assert proxies["http"] == proxies["https"] == "http://127.0.0.1:9"
    assert set(proxies["no"].split(",")) == {"localhost", "127.0.0.1"}


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


def test_the_summary_file_holds_one_line_per_step_as_printed(tmp_path: Path) -> None:
    steps = [
        judge_check.Step("tests", True, ["python: 3 passed", "worker: pass 2"], 1.4),
        judge_check.Step("secrets", False, ["gitleaks found 1"], 0.2),
    ]
    out = tmp_path / "judge_check.json"
    judge_check.write_summary(out, judge_check.ROOT, steps, "judge-check: 1 of 2 steps failed")
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert [s["name"] for s in doc["steps"]] == ["tests", "secrets"]
    assert doc["steps"][0] == {
        "name": "tests",
        "ok": True,
        "text": "python: 3 passed; worker: pass 2",
        "seconds": 1,
    }
    assert doc["steps"][1]["ok"] is False
    assert doc["last"] == "judge-check: 1 of 2 steps failed"
    assert re.fullmatch(r"[0-9a-f]{7,}", doc["commit"])
