"""The analysis refuses real data before the lock, without the tag, or with a changed plan.

It also refuses a synthetic run on real data and a real run on synthetic data, and no option or
environment variable fakes the clock or the repository. evals/usability_analysis.py and
evals/consensus.py share the same guard, so every check runs against both.

The git checks run against a throwaway repository under the test's temp folder, never the
project repository. Only a test can point the checks there, by patching the module.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from evals import consensus
from evals import usability_analysis as ua
from evals.common import ROOT, parse_utc

PLAN_BYTES = (ROOT / "docs" / "analysis_plan.md").read_bytes()
PLAN_TEXT = PLAN_BYTES.decode("utf-8")
EDITED_PLAN = PLAN_TEXT + "\nA line added after the tag.\n"
BEFORE_LOCK = "2026-09-27T00:00:00Z"
AFTER_LOCK = "2026-09-28T02:00:00Z"
MAINS: dict[str, Callable[[list[str]], int]] = {"usability": ua.main, "consensus": consensus.main}
FAST = {
    "usability": ["--resamples", "200", "--permutations", "200"],
    "consensus": ["--draws", "50", "--splits", "5"],
}


def _git(repo: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    done = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.invalid",
            *args,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return done.stdout.strip()


def make_repo(repo: Path, *, tag: bool, text: str = PLAN_TEXT) -> Path:
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "analysis_plan.md").write_text(text, encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "plan")
    if tag:
        _git(repo, "tag", "prereg-v1")
    return repo


def copy_with_edited_plan(source: Path, repo: Path, *, commit: bool) -> Path:
    shutil.copytree(source, repo)
    (repo / "docs" / "analysis_plan.md").write_text(EDITED_PLAN, encoding="utf-8")
    if commit:
        _git(repo, "commit", "-q", "-am", "edit the plan after the tag")
    return repo


def set_clock(monkeypatch: pytest.MonkeyPatch, when: str) -> None:
    for module in (ua, consensus):
        monkeypatch.setattr(module, "now_utc", lambda: parse_utc(when))


@pytest.fixture(scope="module")
def repos(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("repos")
    return {
        "tagged": make_repo(root / "tagged", tag=True),
        "untagged": make_repo(root / "untagged", tag=False),
    }


@pytest.fixture
def pinned(repos: dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> Path:
    """The throwaway tagged repo stands in for this one, pinned to its own commit and plan."""
    repo = repos["tagged"]
    monkeypatch.setattr(ua, "REPO_ROOT", repo)
    monkeypatch.setattr(ua, "PLAN_COMMIT", _git(repo, "rev-parse", "HEAD"))
    monkeypatch.setattr(ua, "PLAN_SHA256", hashlib.sha256(PLAN_BYTES).hexdigest())
    return repo


@pytest.fixture
def export(synthetic_root: Path, tmp_path: Path) -> Path:
    """Generated sessions without SYNTHETIC.txt, standing in for the real export."""
    folder = tmp_path / "export"
    folder.mkdir()
    for name in ("sessions.csv", "responses.csv"):
        shutil.copy(synthetic_root / "real_gain" / name, folder / name)
    return folder


def test_the_pins_match_the_plan_and_docs_notes_plan_hash() -> None:
    notes = (ROOT / "docs" / "notes" / "plan_hash.md").read_text(encoding="utf-8")
    assert f"`{ua.PLAN_COMMIT}`" in notes
    assert f"`{ua.PLAN_SHA256}`" in notes
    assert hashlib.sha256(PLAN_BYTES).hexdigest() == ua.PLAN_SHA256


@pytest.mark.parametrize("script", sorted(MAINS))
@pytest.mark.parametrize("synthetic", [[], ["--synthetic"]])
@pytest.mark.parametrize("option", [["--now", AFTER_LOCK], ["--repo", str(ROOT)]])
def test_no_option_or_variable_fakes_the_clock_or_the_repo(
    script: str,
    synthetic: list[str],
    option: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SECOND_LOOK_TEST_CLOCK", "1")
    with pytest.raises(SystemExit) as done:
        MAINS[script]([*synthetic, *option])
    assert done.value.code == 2
    assert "unrecognized arguments" in capsys.readouterr().err


def test_refuses_before_the_lock_whatever_the_repo_says(pinned: Path) -> None:
    reason = ua.refusal_reason(parse_utc(BEFORE_LOCK), pinned)
    assert reason is not None
    assert reason.startswith("Refusing to run: the data lock is 2026-09-28T01:00:00Z")


@pytest.mark.parametrize("script", sorted(MAINS))
def test_a_real_run_refuses_before_the_lock(
    script: str,
    pinned: Path,
    export: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    set_clock(monkeypatch, BEFORE_LOCK)
    out = tmp_path / "out"
    assert MAINS[script](["--input", str(export), "--out-dir", str(out)]) == 3
    assert capsys.readouterr().out.startswith("Refusing to run: the data lock is")
    assert not out.exists()


def test_run_itself_refuses_so_an_import_cannot_skip_the_checks(
    pinned: Path, export: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    set_clock(monkeypatch, BEFORE_LOCK)
    out = tmp_path / "out"
    with pytest.raises(ua.Refused, match="the data lock is"):
        ua.run(
            input_dir=export,
            out_dir=out,
            synthetic=False,
            stamp_name="20260927",
            scenario=None,
            n_boot=100,
            n_perm=100,
        )
    assert not out.exists()


def test_refuses_without_the_tag(repos: dict[str, Path]) -> None:
    reason = ua.refusal_reason(parse_utc(AFTER_LOCK), repos["untagged"])
    assert reason is not None and "the git tag prereg-v1 does not exist" in reason


def test_refuses_when_the_plan_differs_from_the_tag(repos: dict[str, Path], tmp_path: Path) -> None:
    repo = copy_with_edited_plan(repos["tagged"], tmp_path / "changed", commit=False)
    reason = ua.refusal_reason(parse_utc(AFTER_LOCK), repo)
    assert reason is not None
    assert "docs/analysis_plan.md differs from the version tagged prereg-v1" in reason


def test_a_throwaway_repo_with_its_own_tag_is_refused(repos: dict[str, Path]) -> None:
    reason = ua.refusal_reason(parse_utc(AFTER_LOCK), repos["tagged"])
    assert reason is not None and "does not point at commit ca0a832" in reason


def test_git_variables_cannot_point_the_check_at_another_repo(
    pinned: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = copy_with_edited_plan(pinned, tmp_path / "changed", commit=False)
    other = make_repo(tmp_path / "other", tag=True, text=EDITED_PLAN)
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))
    reason = ua.refusal_reason(parse_utc(AFTER_LOCK), repo)
    assert reason is not None and "differs from the version tagged" in reason


def test_a_lookalike_ref_cannot_stand_in_for_the_tag(pinned: Path, tmp_path: Path) -> None:
    repo = copy_with_edited_plan(pinned, tmp_path / "shadowed", commit=True)
    _git(repo, "update-ref", "refs/prereg-v1", "HEAD")
    reason = ua.refusal_reason(parse_utc(AFTER_LOCK), repo)
    assert reason is not None and "differs from the version tagged" in reason


def test_a_moved_tag_with_a_new_plan_is_refused(pinned: Path, tmp_path: Path) -> None:
    repo = copy_with_edited_plan(pinned, tmp_path / "moved", commit=True)
    _git(repo, "tag", "-f", "prereg-v1")
    reason = ua.refusal_reason(parse_utc(AFTER_LOCK), repo)
    assert reason is not None and "does not have the SHA-256 pinned" in reason


def test_a_moved_tag_with_the_same_plan_is_refused(pinned: Path, tmp_path: Path) -> None:
    repo = tmp_path / "moved"
    shutil.copytree(pinned, repo)
    _git(repo, "commit", "-q", "--allow-empty", "-m", "a later commit")
    _git(repo, "tag", "-f", "prereg-v1")
    reason = ua.refusal_reason(parse_utc(AFTER_LOCK), repo)
    assert reason is not None and "does not point at commit" in reason


def test_refusal_reason_is_none_only_when_everything_holds(
    pinned: Path, repos: dict[str, Path]
) -> None:
    assert ua.refusal_reason(parse_utc(AFTER_LOCK), pinned) is None
    assert ua.refusal_reason(parse_utc(BEFORE_LOCK), pinned) is not None
    assert ua.refusal_reason(parse_utc(AFTER_LOCK), repos["untagged"]) is not None


@pytest.mark.parametrize("script", sorted(MAINS))
def test_a_real_run_goes_ahead_after_the_lock_and_stamps_the_real_time(
    script: str, pinned: Path, export: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    set_clock(monkeypatch, AFTER_LOCK)
    out = tmp_path / "out"
    assert MAINS[script](["--input", str(export), "--out-dir", str(out), *FAST[script]]) == 0
    doc = json.loads((out / f"{script}_20260928.json").read_text())
    assert doc["synthetic"] is False
    assert doc["stamp"] == "20260928"
    assert not doc["chart_title"].startswith("SYNTHETIC")
    written = parse_utc(doc["generated_at_utc"])
    assert abs(written - datetime.now(UTC)) < timedelta(minutes=10)
    assert doc["plan_sha256"] == hashlib.sha256(PLAN_BYTES).hexdigest()


@pytest.mark.parametrize("script", sorted(MAINS))
def test_a_real_run_refuses_synthetic_data(
    script: str,
    pinned: Path,
    synthetic_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    set_clock(monkeypatch, AFTER_LOCK)
    out = tmp_path / "out"
    code = MAINS[script](["--input", str(synthetic_root / "real_gain"), "--out-dir", str(out)])
    assert code == 3
    assert "holds SYNTHETIC.txt" in capsys.readouterr().out
    assert not out.exists()


@pytest.mark.parametrize("script", sorted(MAINS))
def test_synthetic_refuses_a_folder_without_the_marker(
    script: str, export: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out"
    assert MAINS[script](["--synthetic", "--input", str(export), "--out-dir", str(out)]) == 3
    assert "with SYNTHETIC.txt in it" in capsys.readouterr().out
    assert not out.exists()


@pytest.mark.parametrize("script", sorted(MAINS))
def test_synthetic_refuses_the_real_export_even_with_the_marker(
    script: str,
    synthetic_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    real_export = tmp_path / "export"
    shutil.copytree(synthetic_root / "real_gain", real_export)
    monkeypatch.setattr(ua, "EXPORT_DIR", real_export)
    out = tmp_path / "out"
    assert MAINS[script](["--synthetic", "--input", str(real_export), "--out-dir", str(out)]) == 3
    assert "never the real export" in capsys.readouterr().out
    assert not out.exists()


def test_guard_checks_the_marker_both_ways(synthetic_root: Path, export: Path) -> None:
    marked = synthetic_root / "real_gain"
    assert ua.guard(marked, synthetic=True) is None
    assert ua.guard(export, synthetic=True) is not None
    assert ua.guard(ua.EXPORT_DIR, synthetic=True) is not None
    assert "holds SYNTHETIC.txt" in (ua.guard(marked, synthetic=False) or "")


def test_synthetic_runs_before_the_lock_without_the_tag(
    repos: dict[str, Path],
    synthetic_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    set_clock(monkeypatch, BEFORE_LOCK)
    monkeypatch.setattr(ua, "REPO_ROOT", repos["untagged"])
    code = ua.main(
        [
            "--synthetic",
            "--scenario",
            "no_effect",
            "--input",
            str(synthetic_root / "no_effect"),
            "--out-dir",
            str(tmp_path),
            "--resamples",
            "100",
            "--permutations",
            "100",
        ]
    )
    assert code == 0
    assert capsys.readouterr().out.startswith("SYNTHETIC no_effect:")
    doc = json.loads((tmp_path / "usability_synthetic_no_effect.json").read_text())
    assert doc["stamp"] == "SYNTHETIC" and doc["scenario"] == "no_effect"


@pytest.mark.parametrize("script", sorted(MAINS))
def test_scenario_without_synthetic_is_rejected(
    script: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert MAINS[script](["--scenario", "real_gain"]) == 2
    assert "only makes sense with --synthetic" in capsys.readouterr().out
