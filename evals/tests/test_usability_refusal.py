"""The analysis refuses real data before the lock, without the tag, or with a changed plan.

The git checks run against a throwaway repository under the test's temp folder, never the
project repository.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from evals.common import ROOT, parse_utc
from evals.usability_analysis import refusal_reason

SCRIPT = ROOT / "evals" / "usability_analysis.py"
PLAN_TEXT = (ROOT / "docs" / "analysis_plan.md").read_text(encoding="utf-8")
BEFORE_LOCK = "2026-09-27T00:00:00Z"
AFTER_LOCK = "2026-09-28T02:00:00Z"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
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
    )


def make_repo(root: Path, *, tag: bool) -> Path:
    repo = root / ("tagged" if tag else "untagged")
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "analysis_plan.md").write_text(PLAN_TEXT, encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "plan")
    if tag:
        _git(repo, "tag", "prereg-v1")
    return repo


def run_script(*args: str, test_clock: bool = True) -> subprocess.CompletedProcess[str]:
    """The pretend clock and pretend repo are test only, so tests say so in the environment."""
    env = dict(os.environ)
    if test_clock:
        env["SECOND_LOOK_TEST_CLOCK"] = "1"
    else:
        env.pop("SECOND_LOOK_TEST_CLOCK", None)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_pretend_clock_is_refused_without_the_test_environment() -> None:
    done = run_script("--now", AFTER_LOCK, "--repo", str(ROOT), test_clock=False)
    assert done.returncode == 2
    assert "for tests" in done.stdout


@pytest.fixture(scope="module")
def repos(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("repos")
    return {"tagged": make_repo(root, tag=True), "untagged": make_repo(root, tag=False)}


def test_refuses_before_the_lock_whatever_the_repo_says(repos: dict[str, Path]) -> None:
    done = run_script("--now", BEFORE_LOCK, "--repo", str(repos["tagged"]))
    assert done.returncode != 0
    assert done.stdout.startswith("Refusing to run: the data lock is 2026-09-28T01:00:00Z")


def test_refuses_with_the_real_clock_today(repos: dict[str, Path]) -> None:
    done = run_script("--repo", str(repos["untagged"]))
    assert done.returncode != 0
    assert done.stdout.startswith("Refusing to run:")


def test_refuses_without_the_tag(repos: dict[str, Path]) -> None:
    done = run_script("--now", AFTER_LOCK, "--repo", str(repos["untagged"]))
    assert done.returncode != 0
    assert "the git tag prereg-v1 does not exist" in done.stdout


def test_refuses_when_the_plan_differs_from_the_tag(repos: dict[str, Path], tmp_path: Path) -> None:
    repo = tmp_path / "changed"
    shutil.copytree(repos["tagged"], repo)
    plan = repo / "docs" / "analysis_plan.md"
    plan.write_text(PLAN_TEXT + "\nA line added after the tag.\n", encoding="utf-8")
    done = run_script("--now", AFTER_LOCK, "--repo", str(repo))
    assert done.returncode != 0
    assert "docs/analysis_plan.md differs from the version tagged prereg-v1" in done.stdout


def test_runs_after_the_lock_with_the_tag_and_the_same_plan(
    repos: dict[str, Path], synthetic_root: Path, tmp_path: Path
) -> None:
    done = run_script(
        "--now",
        AFTER_LOCK,
        "--repo",
        str(repos["tagged"]),
        "--input",
        str(synthetic_root / "real_gain"),
        "--out-dir",
        str(tmp_path),
        "--resamples",
        "200",
        "--permutations",
        "200",
    )
    assert done.returncode == 0, done.stdout + done.stderr
    doc = json.loads((tmp_path / "usability_20260928.json").read_text())
    assert doc["synthetic"] is False
    assert doc["stamp"] == "20260928"
    assert not doc["chart_title"].startswith("SYNTHETIC")


def test_synthetic_flag_bypasses_the_checks_before_the_lock(
    repos: dict[str, Path], synthetic_root: Path, tmp_path: Path
) -> None:
    done = run_script(
        "--synthetic",
        "--scenario",
        "no_effect",
        "--now",
        BEFORE_LOCK,
        "--repo",
        str(repos["untagged"]),
        "--input",
        str(synthetic_root / "no_effect"),
        "--out-dir",
        str(tmp_path),
        "--resamples",
        "100",
        "--permutations",
        "100",
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert done.stdout.startswith("SYNTHETIC no_effect:")
    doc = json.loads((tmp_path / "usability_synthetic_no_effect.json").read_text())
    assert doc["stamp"] == "SYNTHETIC" and doc["scenario"] == "no_effect"


def test_refusal_reason_is_none_only_when_everything_holds(repos: dict[str, Path]) -> None:
    assert refusal_reason(parse_utc(AFTER_LOCK), repos["tagged"]) is None
    assert refusal_reason(parse_utc(BEFORE_LOCK), repos["tagged"]) is not None
    assert refusal_reason(parse_utc(AFTER_LOCK), repos["untagged"]) is not None


def test_scenario_without_synthetic_is_rejected(repos: dict[str, Path]) -> None:
    done = run_script("--scenario", "real_gain", "--repo", str(repos["tagged"]))
    assert done.returncode != 0
    assert "only makes sense with --synthetic" in done.stdout
