"""The validator run: a crash is a failure, never the last run's result read again."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts import fhir_validate

CLEAN = {"resourceType": "OperationOutcome", "issue": [{"severity": "information"}]}


def test_a_validator_that_writes_nothing_fails_and_the_old_outcome_is_gone(
    tmp_path: Path,
) -> None:
    outcome = tmp_path / "validation_outcome.json"
    outcome.write_text(json.dumps(CLEAN), encoding="utf-8")  # the last run, all clean
    crash = [sys.executable, "-c", "import sys; sys.exit('java.lang.OutOfMemoryError')"]
    with pytest.raises(fhir_validate.ValidatorFailed) as caught:
        fhir_validate.run_validator(crash, outcome)
    assert "exited with code 1 and wrote no outcome" in str(caught.value)
    assert "OutOfMemoryError" in str(caught.value)
    assert not outcome.exists()


def test_the_outcome_read_is_the_one_this_run_wrote(tmp_path: Path) -> None:
    outcome = tmp_path / "validation_outcome.json"
    outcome.write_text(json.dumps(CLEAN), encoding="utf-8")
    fresh = {"resourceType": "OperationOutcome", "issue": [{"severity": "error"}]}
    write = [
        sys.executable,
        "-c",
        "import sys; open(sys.argv[1], 'w').write(sys.argv[2]); print('done')",
        str(outcome),
        json.dumps(fresh),
    ]
    got, tail = fhir_validate.run_validator(write, outcome)
    assert got == fresh
    assert tail == "done"


def test_main_fails_on_a_crashed_validator_and_leaves_the_results_file_alone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    outcome = tmp_path / "validation_outcome.json"
    outcome.write_text(json.dumps(CLEAN), encoding="utf-8")
    results = tmp_path / "fhir_validation.json"
    instance = tmp_path / "ts-bundle.json"
    instance.write_text("{}", encoding="utf-8")

    def crashed(cmd: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="Exception in thread main")

    monkeypatch.setattr(sys, "argv", ["fhir_validate.py", "--no-build", "--tx", "n/a"])
    monkeypatch.setattr(fhir_validate, "OUTCOME", outcome)
    monkeypatch.setattr(fhir_validate, "RESULTS", results)
    monkeypatch.setattr(fhir_validate, "our_files", lambda: [instance])
    monkeypatch.setattr(fhir_validate, "ensure_jar", lambda: None)
    monkeypatch.setattr(fhir_validate.subprocess, "run", crashed)
    assert fhir_validate.main() == 1
    out = capsys.readouterr().out
    assert "exited with code 1 and wrote no outcome" in out
    assert not results.exists(), "a crash must not be written down as a clean run"
