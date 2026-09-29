"""Part 2 analysis on synthetic data, its exclusions, and its refusals (UPDATE_31 section 2 item 4).

The git checks run against a throwaway repository under the test's temp folder, never the
project repository. Only a test can point the checks there, by patching the module.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from evals import assist_analysis as aa
from evals.common import ROOT, parse_utc

N_FAST = 1000
PLAN_TEXT = (ROOT / "docs" / "analysis_plan_v2.md").read_text(encoding="utf-8")


def scenario(tmp_path: Path, name: str) -> dict[str, Any]:
    folder = aa.make_synthetic(name, tmp_path / name)
    return aa.run(
        input_dir=folder,
        out_dir=tmp_path,
        synthetic=True,
        stamp_name=name,
        scenario=name,
        n_boot=N_FAST,
        n_perm=N_FAST,
    )


def test_the_question_helps(tmp_path: Path) -> None:
    r = scenario(tmp_path, "helps")
    p, s = r["primary"], r["secondary"]
    assert p["difference"] > 5 and p["ci_low"] > 0 and p["rejects_at_alpha_05"]
    assert s["wrong_to_right"] > 0 and s["right_to_wrong"] == 0
    assert p["status"] == "confirmatory"


def test_the_question_does_nothing(tmp_path: Path) -> None:
    r = scenario(tmp_path, "nothing")
    p, s = r["primary"], r["secondary"]
    assert p["ci_low"] <= 0 <= p["ci_high"]
    assert not p["rejects_at_alpha_05"]
    assert s["question_shown"] > 0 and s["changed_after_question"] == 0


def test_people_change_to_the_wrong_answer_when_asked(tmp_path: Path) -> None:
    r = scenario(tmp_path, "wrong_changes")
    p, s = r["primary"], r["secondary"]
    assert p["difference"] < 0
    assert s["right_to_wrong"] > 0 and s["wrong_to_right"] == 0
    assert s["accuracy_changed"] == 0.0


def test_no_answer_changes_without_a_question(tmp_path: Path) -> None:
    for name in aa.SCENARIOS:
        assert scenario(tmp_path, name)["secondary"]["changed_without_question"] == 0


def test_declines_are_counted_as_not_started(tmp_path: Path) -> None:
    r = scenario(tmp_path, "nothing")
    c = r["counts"]
    assert c["declined"] == 12
    assert sum(c["randomized"].values()) == 120


def test_exclusions_in_the_plans_order(tmp_path: Path) -> None:
    folder = aa.make_synthetic("nothing", tmp_path / "x")
    s = pd.read_csv(folder / "part2_sessions.csv", dtype=str, keep_default_na=False)
    live = s[s["declined"] == "false"].index
    s.loc[live[0], "test_seconds"] = "12"
    s.loc[live[1], "is_test"] = "true"
    s.loc[live[2], "post_lock"] = "true"
    s.loc[live[3], "client_token_hash"] = s.loc[live[4], "client_token_hash"]
    s.to_csv(folder / "part2_sessions.csv", index=False)
    r = pd.read_csv(folder / "part2_responses.csv", dtype=str, keep_default_na=False)
    r = r[~((r["part2_id"] == s.loc[live[5], "part2_id"]) & (r["item_id"] == "a01"))]
    r.to_csv(folder / "part2_responses.csv", index=False)
    sessions, responses = aa.load_export(folder)
    kept = aa.apply_exclusions(sessions, responses)
    removed = {step.order: step.removed for step in kept.steps}
    assert removed == {0: 1, 1: 1, 2: 1, 3: 1, 4: 1}


def test_too_few_gives_the_sentence_not_a_number() -> None:
    row = aa.readme_row(
        {
            "primary": {
                "n_assisted": 3,
                "n_unassisted": 4,
                "difference": 10.0,
                "status": "descriptive",
            }
        }
    )
    assert row.startswith("Too few people finished part 2")


# --- refusals -------------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    done = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return done.stdout.strip()


def make_repo(repo: Path, *, tag: bool, text: str = PLAN_TEXT) -> Path:
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "analysis_plan_v2.md").write_text(text, encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "plan")
    if tag:
        _git(repo, "tag", "prereg-v2")
    return repo


BEFORE = parse_utc("2026-09-27T00:00:00Z")
AFTER = parse_utc("2026-09-28T02:00:00Z")


def test_refuses_before_the_lock_even_with_everything_pinned(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "r", tag=True)
    assert "data lock" in (aa.refusal_reason(BEFORE, repo) or "")


def test_refuses_without_the_tag(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "r", tag=False)
    assert "prereg-v2 does not exist" in (aa.refusal_reason(AFTER, repo) or "")


def test_refuses_while_nothing_is_pinned(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "r", tag=True)
    assert aa.PLAN_SHA256 is None or aa.PLAN_COMMIT is not None
    reason = aa.refusal_reason(AFTER, repo) or ""
    assert "SHA-256 pinned" in reason or "does not point at" in reason


def test_runs_when_tagged_pinned_and_after_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_repo(tmp_path / "r", tag=True)
    monkeypatch.setattr(aa, "PLAN_SHA256", hashlib.sha256(PLAN_TEXT.encode()).hexdigest())
    monkeypatch.setattr(aa, "PLAN_COMMIT", _git(repo, "rev-parse", "HEAD"))
    assert aa.refusal_reason(AFTER, repo) is None
    (repo / "docs" / "analysis_plan_v2.md").write_text(PLAN_TEXT + "\nlater\n", encoding="utf-8")
    assert "differs from the version tagged" in (aa.refusal_reason(AFTER, repo) or "")


def test_a_real_run_refuses_before_the_lock_and_never_reads_synthetic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The clock is handed in: on the real one this only held until the lock, and the test went
    # red on 2026-09-28, inside the lock job's own make check.
    monkeypatch.setattr(aa, "now_utc", lambda: BEFORE)
    folder = aa.make_synthetic("helps", tmp_path / "h")
    assert "SYNTHETIC.txt" in (aa.guard(folder, synthetic=False) or "")
    unmarked = tmp_path / "real"
    unmarked.mkdir()
    assert aa.guard(unmarked, synthetic=True) is not None
    reason = aa.guard(unmarked, synthetic=False)
    assert reason is not None and reason.startswith("Refusing to run")
    with pytest.raises(aa.Refused):
        aa.run(
            input_dir=unmarked,
            out_dir=tmp_path,
            synthetic=False,
            stamp_name="x",
            n_boot=N_FAST,
            n_perm=N_FAST,
        )
    assert aa.main(["--input", str(unmarked)]) == 3
