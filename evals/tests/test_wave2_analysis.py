"""The second wave (docs/analysis_plan_v3.md): the window, the registered rules, the refusals.

Every sitting here is made up. The git checks run against a throwaway repository under the
test's temp folder, never the project repository, and every clock is handed in, so these tests
say the same thing before and after the second lock.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

import core.lock
from evals import assist_analysis as aa
from evals import usability_analysis as ua
from evals import wave2_analysis as w2
from evals.common import RESPONSE_COLUMNS, ROOT, SESSION_COLUMNS, load_test_items, parse_utc

N_FAST = 200
FIRST_LOCK = core.lock.DATA_LOCK_UTC
OPEN = w2.WAVE2_OPEN_UTC
LOCK = w2.SECOND_LOCK_UTC
BEFORE = LOCK - timedelta(hours=1)
AFTER = LOCK + timedelta(minutes=10)
# The two plans and the two analysis scripts as they ran at the first lock (unchanged since
# 6f582c0, the commit that pinned part 2's script). Plan v3 rests on exactly these bytes.
REGISTERED_SHA256 = {
    "docs/analysis_plan.md": "86da527e30c0a8e8492b6fb22c3056be1a2ad3087b5ca8c6f4a0a1bd58aed9cf",
    "docs/analysis_plan_v2.md": "723f7980a2e05eba3b74f43826e0afbf2211a7c35da6dcc18581dba3df73a8c3",
    "evals/usability_analysis.py": (
        "7a2ab6e41df546feff834c1b048218491c389104ffd1ff6c34a343835fd5594c"
    ),
    "evals/assist_analysis.py": "04cd28bd780e9c54082bbafcc33b98a4f9908767bf6787aef556c9a225455aab",
}
FIRST_WAVE = {
    "part1": ROOT / "results" / "usability_20260929.json",
    "part2": ROOT / "results" / "assist_20260929.json",
}


def z(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Made up exports
# ---------------------------------------------------------------------------


def sitting(sid: str, start: datetime, arm: str = "trained", **over: str) -> dict[str, str]:
    """One finished part 1 sitting, with post_lock as the server stores it."""
    row = {
        "session_id": sid,
        "arm": arm,
        "block_id": "0",
        "source_label": "panel",
        "ua_class": "phone",
        "consent_version": "v1",
        "content_hash": "c",
        "build_hash": "b",
        "started_at_utc": z(start),
        "lesson_seconds_total": "120",
        "completed_at_utc": z(start + timedelta(minutes=5)),
        "test_seconds": "100",
        "is_test": "false",
        "post_lock": str(start >= FIRST_LOCK).lower(),
        "hidden_field_filled": "false",
        "client_token_hash": f"tok-{sid}",
        "prior_experience": "no",
        "warmup_choice": "w02",
    }
    row.update(over)
    return row


def answers(sids: list[str], right: int = 12) -> list[dict[str, str]]:
    """Sixteen answers per sitting, the first `right` of them correct."""
    rows = []
    for sid in sids:
        for i, item in enumerate(load_test_items()):
            correct = i < right
            good = "yes" if item["gold"] == "present" else "no"
            bad = "no" if item["gold"] == "present" else "yes"
            rows.append(
                {
                    "session_id": sid,
                    "item_id": item["id"],
                    "feature": item["feature"],
                    "gold": item["gold"],
                    "answer": good if correct else bad,
                    "correct": str(int(correct)),
                    "rt_ms": "4000",
                    "position": str(i + 1),
                }
            )
    return rows


def part2_sitting(
    pid: str, sid: str, start: datetime, arm: str = "assisted", **over: str
) -> dict[str, str]:
    row = {
        "part2_id": pid,
        "session_id": sid,
        "part1_arm": "trained",
        "arm": arm,
        "block_id": "0",
        "offered_at_utc": z(start),
        "declined": "false",
        "started_at_utc": z(start),
        "completed_at_utc": z(start + timedelta(seconds=90)),
        "test_seconds": "90",
        "client_token_hash": f"tok-{sid}",
        "is_test": "false",
        "post_lock": str(start >= FIRST_LOCK).lower(),
    }
    row.update(over)
    return row


def part2_answers(pids: list[str]) -> list[dict[str, str]]:
    rows = []
    for pid in pids:
        for i, item in enumerate(aa._items()):
            good = "yes" if item["gold"] == "present" else "no"
            rows.append(
                {
                    "part2_id": pid,
                    "item_id": item["id"],
                    "feature": item["feature"],
                    "gold": item["gold"],
                    "position": str(i),
                    "first_answer": good,
                    "final_answer": good,
                    "question_shown": "false",
                    "choice": "",
                    "t_first_ms": "4000",
                    "t_final_ms": "4000",
                    "correct": "1",
                }
            )
    return rows


def write_export(
    folder: Path,
    sittings: list[dict[str, str]],
    *,
    part2: list[dict[str, str]] | None = None,
    unfinished: tuple[str, ...] = (),
    marked: bool = True,
) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(sittings, columns=SESSION_COLUMNS).to_csv(folder / "sessions.csv", index=False)
    done = [s["session_id"] for s in sittings if s["session_id"] not in unfinished]
    pd.DataFrame(answers(done), columns=RESPONSE_COLUMNS).to_csv(
        folder / "responses.csv", index=False
    )
    if part2 is not None:
        pd.DataFrame(part2, columns=aa.SESSION_COLUMNS).to_csv(
            folder / "part2_sessions.csv", index=False
        )
        pd.DataFrame(
            part2_answers([p["part2_id"] for p in part2]), columns=aa.RESPONSE_COLUMNS
        ).to_csv(folder / "part2_responses.csv", index=False)
    if marked:
        (folder / w2.SYNTHETIC_MARKER).write_text("made up for a test\n", encoding="utf-8")
    return folder


def run(folder: Path, out: Path, *, synthetic: bool = True) -> dict[str, Any]:
    return w2.run(
        input_dir=folder,
        out_dir=out,
        synthetic=synthetic,
        stamp_name="w2_test",
        n_boot=N_FAST,
        n_perm=N_FAST,
    )


def kept_ids(result: dict[str, Any], folder: Path) -> set[str]:
    """The sittings the analysis kept: those whose answers are behind the per item counts."""
    sessions, responses = ua.load_export(folder)
    part1, _ = w2.window_part1(sessions)
    with w2.wave2_constants():
        kept = ua.apply_exclusions(part1, responses, launch_utc=OPEN).kept
    assert len(kept) == sum(result["counts"]["analysed"].values())
    return set(kept["session_id"])


def removed(result: dict[str, Any]) -> dict[int, int]:
    return {step["order"]: step["removed"] for step in result["exclusions"]}


FOUR_TIMES = [
    sitting("before-first-lock-t", FIRST_LOCK - timedelta(days=1), "trained"),
    sitting("before-first-lock-u", FIRST_LOCK - timedelta(days=1, hours=1), "untrained"),
    sitting("between-t", FIRST_LOCK + timedelta(hours=5), "trained"),
    sitting("between-u", OPEN - timedelta(seconds=1), "untrained"),
    sitting("inside-first-second", OPEN, "trained"),
    sitting("inside-t", OPEN + timedelta(hours=30), "trained"),
    sitting("inside-u", OPEN + timedelta(hours=31), "untrained"),
    sitting("inside-last-second", LOCK - timedelta(seconds=1), "untrained"),
    sitting("at-the-second-lock", LOCK, "trained"),
    sitting("after-second-lock", LOCK + timedelta(hours=2), "untrained"),
]
INSIDE = {"inside-first-second", "inside-t", "inside-u", "inside-last-second"}


# ---------------------------------------------------------------------------
# The window
# ---------------------------------------------------------------------------


def test_the_two_instants_are_the_ones_of_the_brief() -> None:
    assert OPEN == datetime(2026, 9, 30, 4, 0, 0, tzinfo=UTC)
    assert LOCK == datetime(2026, 10, 3, 4, 0, 0, tzinfo=UTC)
    deadline = datetime(2026, 10, 5, 4, 0, 0, tzinfo=UTC)
    assert deadline - LOCK == timedelta(hours=48)
    assert w2.LOCK_JOB_UTC - LOCK == timedelta(minutes=10)
    assert FIRST_LOCK < OPEN < LOCK
    assert w2.local_label(OPEN) == "Tuesday Sep 29, 2026 at 21:00 PDT"
    assert w2.local_label(LOCK) == "Friday Oct 2, 2026 at 21:00 PDT"


def disagreements(lock_module: Any) -> list[str]:
    """The instants core/lock.py holds under the same names that differ from wave 2's."""
    ours = {"SECOND_LOCK_UTC": LOCK, "WAVE2_OPEN_UTC": OPEN}
    return [
        f"core/lock.py says {name} is {getattr(lock_module, name)}, wave 2 says {value}"
        for name, value in ours.items()
        if hasattr(lock_module, name) and getattr(lock_module, name) != value
    ]


def test_core_lock_agrees_wherever_it_names_the_same_instants() -> None:
    assert disagreements(core.lock) == []
    # The check itself: silent when core/lock.py has neither yet, loud when one differs.
    assert disagreements(SimpleNamespace()) == []
    assert disagreements(SimpleNamespace(SECOND_LOCK_UTC=LOCK, WAVE2_OPEN_UTC=OPEN)) == []
    moved = SimpleNamespace(SECOND_LOCK_UTC=LOCK + timedelta(hours=1), WAVE2_OPEN_UTC=OPEN)
    assert len(disagreements(moved)) == 1 and "SECOND_LOCK_UTC" in disagreements(moved)[0]


def test_only_sittings_that_started_inside_the_window_are_kept(tmp_path: Path) -> None:
    folder = write_export(tmp_path / "in", FOUR_TIMES)
    result = run(folder, tmp_path)["part1"]
    assert kept_ids(result, folder) == INSIDE
    assert result["counts"]["analysed"] == {"untrained": 2, "trained": 2}
    # Each kind leaves under the plan's own rule: after the lock first, dry runs last.
    assert removed(result) == {0: 2, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 4}
    assert result["exclusions"][6]["note"] == "launch at 2026-09-30T04:00:00Z"
    assert result["plan"]["data_lock_utc"] == "2026-10-03T04:00:00Z"
    window = result["window"]
    assert window["by_start_time"] == {
        "before_the_first_lock": 2,
        "between_the_first_lock_and_the_opening": 2,
        "inside_the_window": 4,
        "at_or_after_the_second_lock": 2,
        "no_start_time": 0,
    }
    assert window["open_utc"] == z(OPEN) and window["lock_utc"] == z(LOCK)


def test_the_stored_post_lock_mark_is_ignored_both_ways(tmp_path: Path) -> None:
    # The server marked every sitting of the wave post_lock. A wrong mark on an early sitting, or
    # a missing one on a late sitting, changes nothing either: the start time decides.
    rows = [
        sitting("inside-marked", OPEN + timedelta(hours=1), "trained", post_lock="true"),
        sitting("inside-unmarked", OPEN + timedelta(hours=2), "untrained", post_lock="false"),
        sitting("late-unmarked", LOCK + timedelta(hours=1), "trained", post_lock="false"),
    ]
    folder = write_export(tmp_path / "in", rows)
    result = run(folder, tmp_path)["part1"]
    assert kept_ids(result, folder) == {"inside-marked", "inside-unmarked"}
    assert removed(result)[0] == 1
    assert result["window"]["stored_post_lock_marks_ignored"] == 1


def test_a_sitting_with_no_start_time_is_left_out(tmp_path: Path) -> None:
    rows = [
        sitting("inside", OPEN + timedelta(hours=1), "trained"),
        sitting("no-time", OPEN + timedelta(hours=1), "untrained", started_at_utc=""),
    ]
    folder = write_export(tmp_path / "in", rows)
    result = run(folder, tmp_path)["part1"]
    assert kept_ids(result, folder) == {"inside"}
    assert result["window"]["by_start_time"]["no_start_time"] == 1


def test_the_plans_rules_drop_the_same_sittings_inside_the_window(tmp_path: Path) -> None:
    t = OPEN + timedelta(hours=10)
    rows = [
        sitting("clean-t", t, "trained"),
        sitting("clean-u", t + timedelta(minutes=1), "untrained"),
        sitting("qa", t + timedelta(minutes=2), "trained", is_test="true"),
        sitting("repeat", t + timedelta(hours=3), "trained", client_token_hash="tok-clean-t"),
        sitting("fast", t + timedelta(minutes=4), "untrained", test_seconds="39.9"),
        sitting("hidden", t + timedelta(minutes=5), "untrained", hidden_field_filled="true"),
        sitting("unfinished", t + timedelta(minutes=6), "trained", completed_at_utc=""),
    ]
    folder = write_export(tmp_path / "in", rows, unfinished=("unfinished",))
    result = run(folder, tmp_path)["part1"]
    assert kept_ids(result, folder) == {"clean-t", "clean-u"}
    assert removed(result) == {0: 0, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 0}
    rules = [step["rule"] for step in result["exclusions"]]
    first = json.loads(FIRST_WAVE["part1"].read_text(encoding="utf-8"))
    assert rules == [step["rule"] for step in first["exclusions"]]


def test_a_browser_that_sat_before_the_wave_opened_is_left_out_of_it(tmp_path: Path) -> None:
    # The plan's order: repeat visits before dry runs. That person has seen the photos.
    rows = [
        sitting("early", OPEN - timedelta(hours=3), "trained", client_token_hash="same"),
        sitting("again", OPEN + timedelta(hours=3), "trained", client_token_hash="same"),
        sitting("other", OPEN + timedelta(hours=4), "untrained"),
    ]
    folder = write_export(tmp_path / "in", rows)
    result = run(folder, tmp_path)["part1"]
    assert kept_ids(result, folder) == {"other"}
    assert removed(result)[3] == 1 and removed(result)[6] == 1


def test_part2_is_kept_only_when_its_part1_sitting_is_in_the_window(tmp_path: Path) -> None:
    inside = OPEN + timedelta(hours=5)
    rows = [
        sitting("p1-early", OPEN - timedelta(hours=2), "trained"),
        sitting("p1-in-a", inside, "trained"),
        sitting("p1-in-b", inside + timedelta(minutes=1), "untrained"),
        sitting("p1-last", LOCK - timedelta(minutes=4), "trained"),
        sitting("p1-late", LOCK + timedelta(hours=1), "untrained"),
    ]
    part2 = [
        part2_sitting("x-early", "p1-early", OPEN - timedelta(hours=1), "assisted"),
        part2_sitting("x-in-a", "p1-in-a", inside + timedelta(minutes=6), "assisted"),
        part2_sitting("x-in-b", "p1-in-b", inside + timedelta(minutes=7), "unassisted"),
        # Part 1 started inside the window, part 2 only after the second lock.
        part2_sitting("x-over", "p1-last", LOCK + timedelta(minutes=2), "unassisted"),
        part2_sitting("x-late", "p1-late", LOCK + timedelta(hours=2), "assisted"),
        part2_sitting("x-orphan", "no-such-sitting", inside, "assisted"),
    ]
    folder = write_export(tmp_path / "in", rows, part2=part2)
    result = run(folder, tmp_path)["part2"]
    assert result is not None
    assert result["counts"]["analysed"] == {"unassisted": 1, "assisted": 1}
    assert result["counts"]["offered"] == 2
    window = result["window"]
    assert window["part2_sittings_in_the_export"] == 6
    assert window["left_out_because_part1_started_outside_the_window"] == 3
    assert window["part1_sitting_inside_the_window"] == 3
    assert removed(result)[0] == 1
    first = json.loads(FIRST_WAVE["part2"].read_text(encoding="utf-8"))
    assert [s["rule"] for s in result["exclusions"]] == [s["rule"] for s in first["exclusions"]]


def test_an_export_without_part2_files_gives_no_part2_result(tmp_path: Path) -> None:
    folder = write_export(tmp_path / "in", FOUR_TIMES)
    assert run(folder, tmp_path)["part2"] is None
    assert not list(tmp_path.glob("assist_*"))


def test_empty_arms_say_the_sentence_the_first_wave_gave(tmp_path: Path) -> None:
    # Our own checks in both arms, as at the first lock: the plan's rules drop them all.
    rows = [
        sitting("qa-t", OPEN + timedelta(hours=1), "trained", is_test="true"),
        sitting("qa-u", OPEN + timedelta(hours=1), "untrained", is_test="true"),
    ]
    part2 = [
        part2_sitting("x-a", "qa-t", OPEN + timedelta(hours=2), "assisted", is_test="true"),
        part2_sitting("x-u", "qa-u", OPEN + timedelta(hours=2), "unassisted", is_test="true"),
    ]
    folder = write_export(tmp_path / "in", rows, part2=part2)
    results = run(folder, tmp_path)
    for part, path in FIRST_WAVE.items():
        first = json.loads(path.read_text(encoding="utf-8"))["primary"]["status"]
        assert first == "not computed: an arm is empty"
        assert results[part]["primary"]["status"] == first
    assert results["part2"]["readme_row"].startswith("Too few people finished part 2")


def test_the_generated_second_wave_holds_all_four_times(tmp_path: Path) -> None:
    folder = w2.make_synthetic(tmp_path / "made")
    assert (folder / w2.SYNTHETIC_MARKER).exists()
    results = run(folder, tmp_path)
    part1, part2 = results["part1"], results["part2"]
    seen = part1["window"]["by_start_time"]
    assert all(seen[k] > 0 for k in seen if k != "no_start_time")
    assert removed(part1) == {0: 3, 1: 8, 2: 3, 3: 4, 4: 2, 5: 2, 6: 6}
    assert part1["counts"]["analysed"] == {"untrained": 41, "trained": 43}
    assert part1["primary"]["status"] == "confirmatory" and part1["stamp"] == "SYNTHETIC"
    assert part2["window"]["left_out_because_part1_started_outside_the_window"] == 4
    assert part2["primary"]["status"] == "confirmatory" and part2["synthetic"] is True


# ---------------------------------------------------------------------------
# The constants the two scripts read
# ---------------------------------------------------------------------------


def constants() -> dict[tuple[str, str], Any]:
    return {(m.__name__, n): getattr(m, n) for m in (ua, aa) for n in w2.SWAPPED}


def test_inside_the_run_the_two_scripts_hold_wave_2s_constants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}
    real_part1, real_part2 = ua.analyse, aa.analyse

    def part1(*args: Any, **kw: Any) -> dict[str, Any]:
        seen["part1"] = constants()
        seen["launch"] = kw.get("launch_utc")
        return real_part1(*args, **kw)

    def part2(*args: Any, **kw: Any) -> dict[str, Any]:
        seen["part2"] = constants()
        return real_part2(*args, **kw)

    monkeypatch.setattr(ua, "analyse", part1)
    monkeypatch.setattr(aa, "analyse", part2)
    before = constants()
    rows = [sitting("a", OPEN + timedelta(hours=1))]
    part2_rows = [part2_sitting("x", "a", OPEN + timedelta(hours=2))]
    run(write_export(tmp_path / "in", rows, part2=part2_rows), tmp_path)
    for part in ("part1", "part2"):
        for module in ("evals.usability_analysis", "evals.assist_analysis"):
            assert seen[part][(module, "DATA_LOCK_UTC")] == LOCK
            assert seen[part][(module, "PLAN_TAG")] == "prereg-v3"
            assert seen[part][(module, "PLAN_RELATIVE")] == "docs/analysis_plan_v3.md"
            assert seen[part][(module, "SCRIPT")] == "evals/wave2_analysis.py"
            assert seen[part][(module, "PLAN_COMMIT")] == w2.PLAN_COMMIT
            assert seen[part][(module, "PLAN_SHA256")] == w2.PLAN_SHA256
    assert seen["launch"] == OPEN
    assert constants() == before


def test_the_constants_are_as_before_after_a_run_and_after_a_run_that_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = constants()
    assert before[("evals.usability_analysis", "DATA_LOCK_UTC")] == FIRST_LOCK
    assert before[("evals.usability_analysis", "PLAN_TAG")] == "prereg-v1"
    assert before[("evals.assist_analysis", "PLAN_TAG")] == "prereg-v2"
    folder = write_export(tmp_path / "in", FOUR_TIMES)
    run(folder, tmp_path)
    assert constants() == before

    def fails(*args: Any, **kw: Any) -> dict[str, Any]:
        assert ua.DATA_LOCK_UTC == LOCK
        raise RuntimeError("the analysis fell over")

    monkeypatch.setattr(ua, "analyse", fails)
    with pytest.raises(RuntimeError, match="fell over"):
        run(folder, tmp_path)
    assert constants() == before
    with pytest.raises(KeyboardInterrupt), w2.wave2_constants():
        raise KeyboardInterrupt
    assert constants() == before


def test_the_first_waves_rules_are_as_they_were_after_a_second_wave_run(tmp_path: Path) -> None:
    run(write_export(tmp_path / "in", FOUR_TIMES), tmp_path)
    rows = [
        sitting("s-before", FIRST_LOCK - timedelta(seconds=1), post_lock="false"),
        sitting("s-after", FIRST_LOCK + timedelta(seconds=1), post_lock="false"),
    ]
    sessions = ua.tidy_sessions(pd.DataFrame(rows, columns=SESSION_COLUMNS))
    responses = ua.tidy_responses(pd.DataFrame(answers(["s-before", "s-after"])))
    excl = ua.apply_exclusions(sessions, responses)
    assert list(excl.kept["session_id"]) == ["s-before"] and excl.steps[0].removed == 1
    early = ua.refusal_reason(parse_utc("2026-09-27T00:00:00Z"), ROOT) or ""
    assert "the data lock is 2026-09-28T01:00:00Z" in early


def changed_files(root: Path) -> list[str]:
    """The registered files under root that are not, byte for byte, the ones of the first lock."""
    return [
        rel
        for rel, sha in REGISTERED_SHA256.items()
        if hashlib.sha256((root / rel).read_bytes()).hexdigest() != sha
    ]


def test_the_two_plans_and_the_two_scripts_are_byte_for_byte_as_at_the_first_lock(
    tmp_path: Path,
) -> None:
    assert set(REGISTERED_SHA256) == set(w2.REGISTERED)
    assert changed_files(ROOT) == []
    # The check itself, on a copy with one byte added to one script.
    for rel in REGISTERED_SHA256:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    assert changed_files(tmp_path) == []
    with (tmp_path / "evals/assist_analysis.py").open("a", encoding="utf-8") as f:
        f.write("\n")
    assert changed_files(tmp_path) == ["evals/assist_analysis.py"]


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------


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


def make_repo(repo: Path, *, tag: bool) -> Path:
    """A throwaway repository that holds the plan and what it rests on, tagged or not."""
    for rel in (w2.PLAN_RELATIVE, *w2.REGISTERED):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, repo / rel)
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "plan v3")
    if tag:
        _git(repo, "tag", "prereg-v3")
    return repo


@pytest.fixture
def pinned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The throwaway tagged repository stands in for this one, pinned to its commit and plan."""
    repo = make_repo(tmp_path / "repo", tag=True)
    plan = (repo / w2.PLAN_RELATIVE).read_bytes()
    monkeypatch.setattr(w2, "REPO_ROOT", repo)
    monkeypatch.setattr(w2, "PLAN_COMMIT", _git(repo, "rev-parse", "HEAD"))
    monkeypatch.setattr(w2, "PLAN_SHA256", hashlib.sha256(plan).hexdigest())
    return repo


def test_the_pins_are_both_unset_or_both_match_the_plan_and_the_notes() -> None:
    assert (w2.PLAN_COMMIT is None) == (w2.PLAN_SHA256 is None)
    if w2.PLAN_SHA256 is not None:
        notes = (ROOT / "docs" / "notes" / "plan_hash.md").read_text(encoding="utf-8")
        assert f"`{w2.PLAN_COMMIT}`" in notes and f"`{w2.PLAN_SHA256}`" in notes
        plan = (ROOT / w2.PLAN_RELATIVE).read_bytes()
        assert hashlib.sha256(plan).hexdigest() == w2.PLAN_SHA256


def test_refuses_before_the_second_lock_even_with_everything_pinned(pinned: Path) -> None:
    reason = w2.refusal_reason(BEFORE, pinned) or ""
    assert reason.startswith("Refusing to run: the second data lock is 2026-10-03T04:00:00Z")
    assert w2.refusal_reason(LOCK - timedelta(seconds=1), pinned) is not None
    assert w2.refusal_reason(LOCK, pinned) is None
    # The first lock has long passed, and that is not enough.
    assert w2.refusal_reason(FIRST_LOCK + timedelta(days=1), pinned) is not None


def test_refuses_without_the_tag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = make_repo(tmp_path / "r", tag=False)
    monkeypatch.setattr(w2, "PLAN_COMMIT", _git(repo, "rev-parse", "HEAD"))
    plan = (repo / w2.PLAN_RELATIVE).read_bytes()
    monkeypatch.setattr(w2, "PLAN_SHA256", hashlib.sha256(plan).hexdigest())
    assert "prereg-v3 does not exist" in (w2.refusal_reason(AFTER, repo) or "")
    # The first wave's tags do not stand in for it.
    _git(repo, "tag", "prereg-v1")
    _git(repo, "tag", "prereg-v2")
    assert "prereg-v3 does not exist" in (w2.refusal_reason(AFTER, repo) or "")


def test_refuses_while_nothing_is_pinned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = make_repo(tmp_path / "r", tag=True)
    plan = (repo / w2.PLAN_RELATIVE).read_bytes()
    monkeypatch.setattr(w2, "PLAN_COMMIT", None)
    monkeypatch.setattr(w2, "PLAN_SHA256", None)
    assert "SHA-256 pinned" in (w2.refusal_reason(AFTER, repo) or "")
    monkeypatch.setattr(w2, "PLAN_SHA256", hashlib.sha256(plan).hexdigest())
    assert "does not point at the commit" in (w2.refusal_reason(AFTER, repo) or "")
    monkeypatch.setattr(w2, "PLAN_COMMIT", "0" * 40)
    assert "does not point at the commit" in (w2.refusal_reason(AFTER, repo) or "")


def test_refuses_a_plan_that_differs_from_the_tagged_one(pinned: Path) -> None:
    assert w2.refusal_reason(AFTER, pinned) is None
    plan = pinned / w2.PLAN_RELATIVE
    plan.write_text(plan.read_text(encoding="utf-8") + "\nlater\n", encoding="utf-8")
    reason = w2.refusal_reason(AFTER, pinned) or ""
    assert "docs/analysis_plan_v3.md differs from the version tagged prereg-v3" in reason
    # Committing the edit and moving the tag does not help: the pins name the first one.
    _git(pinned, "commit", "-q", "-am", "edit the plan after the tag")
    _git(pinned, "tag", "-f", "prereg-v3")
    assert "SHA-256 pinned" in (w2.refusal_reason(AFTER, pinned) or "")


@pytest.mark.parametrize("relative", w2.REGISTERED)
def test_refuses_when_a_plan_or_a_script_it_rests_on_differs_from_the_tag(
    pinned: Path, relative: str
) -> None:
    assert w2.refusal_reason(AFTER, pinned) is None
    with (pinned / relative).open("a", encoding="utf-8") as f:
        f.write("\n")
    reason = w2.refusal_reason(AFTER, pinned) or ""
    assert f"{relative} differs from its copy at the tag prereg-v3" in reason
    (pinned / relative).unlink()
    assert relative in (w2.refusal_reason(AFTER, pinned) or "")


def test_a_real_run_refuses_before_the_lock_and_never_reads_synthetic(
    pinned: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(w2, "now_utc", lambda: BEFORE)
    marked = write_export(tmp_path / "marked", FOUR_TIMES)
    unmarked = write_export(tmp_path / "real", FOUR_TIMES, marked=False)
    assert "SYNTHETIC.txt" in (w2.guard(marked, synthetic=False) or "")
    assert w2.guard(unmarked, synthetic=True) is not None
    assert (w2.guard(unmarked, synthetic=False) or "").startswith(
        "Refusing to run: the second data lock"
    )
    with pytest.raises(w2.Refused):
        run(unmarked, tmp_path / "out", synthetic=False)
    assert w2.main(["--input", str(unmarked), "--out-dir", str(tmp_path / "out")]) == 3
    assert not (tmp_path / "out").exists()
    # After the lock a marked folder is still never read as real.
    monkeypatch.setattr(w2, "now_utc", lambda: AFTER)
    assert w2.main(["--input", str(marked), "--out-dir", str(tmp_path / "out")]) == 3
    assert not (tmp_path / "out").exists()
    monkeypatch.setattr(w2, "EXPORT_DIR", marked)
    assert "never the real export" in (w2.guard(marked, synthetic=True) or "")


def test_no_option_fakes_the_clock_or_the_repository(capsys: pytest.CaptureFixture[str]) -> None:
    for option in (["--now", z(AFTER)], ["--repo", str(ROOT)], ["--lock", z(BEFORE)]):
        with pytest.raises(SystemExit) as done:
            w2.main(option)
        assert done.value.code == 2
        assert "unrecognized arguments" in capsys.readouterr().err


def test_after_the_lock_a_real_run_writes_the_first_waves_shape_plus_the_window(
    pinned: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(w2, "now_utc", lambda: AFTER)
    part2 = [part2_sitting("x", "inside-t", OPEN + timedelta(hours=31))]
    export = write_export(tmp_path / "real", FOUR_TIMES, part2=part2, marked=False)
    out = tmp_path / "results"
    argv = ["--input", str(export), "--out-dir", str(out)]
    assert w2.main([*argv, "--resamples", "200", "--permutations", "200"]) == 0
    said = capsys.readouterr().out
    assert f"wrote json: {out / 'usability_w2_20261003.json'}" in said
    assert f"wrote part 2 json: {out / 'assist_w2_20261003.json'}" in said
    names = sorted(p.name for p in out.iterdir())
    assert names == [
        "assist_w2_20261003.json",
        "assist_w2_20261003.md",
        "usability_w2_20261003.json",
        "usability_w2_20261003.md",
        "usability_w2_20261003.png",
    ]
    plan = hashlib.sha256((pinned / w2.PLAN_RELATIVE).read_bytes()).hexdigest()
    for part, name in (("part1", names[2]), ("part2", names[0])):
        ours = json.loads((out / name).read_text(encoding="utf-8"))
        first = json.loads(FIRST_WAVE[part].read_text(encoding="utf-8"))
        assert [k for k in ours if k != "window"] == list(first)
        assert set(ours["primary"]) >= set(first["primary"])
        assert set(ours["counts"]) == set(first["counts"])
        assert ours["synthetic"] is False and ours["stamp"] == "w2_20261003"
        assert ours["script"] == "evals/wave2_analysis.py" and ours["plan_sha256"] == plan
        assert ours["window"]["wave"] == 2 and ours["window"]["plan_tag"] == "prereg-v3"
    words = (out / "usability_w2_20261003.md").read_text(encoding="utf-8")
    assert words.startswith("# Usability test results (second wave)")
    assert "## The second wave" in words and "SYNTHETIC" not in words


# ---------------------------------------------------------------------------
# results/wave2_window.json, which the README quotes before the second lock
# ---------------------------------------------------------------------------


def test_the_committed_window_file_is_what_the_script_writes(tmp_path: Path) -> None:
    assert w2.window_differs() == []
    record = w2.window_record()
    assert record["synthetic"] is False and record["min_per_arm"] == 20
    assert record["open_utc"] == "2026-09-30T04:00:00Z"
    assert record["lock_utc"] == "2026-10-03T04:00:00Z"
    assert record["lock_job_utc"] == "2026-10-03T04:10:00Z" and record["window_hours"] == 72
    stale = tmp_path / "wave2_window.json"
    stale.write_text(json.dumps({**record, "lock_utc": "2026-09-28T01:00:00Z"}), encoding="utf-8")
    assert len(w2.window_differs(stale)) == 1 and "lock_utc" in w2.window_differs(stale)[0]
    assert "cannot be read" in w2.window_differs(tmp_path / "missing.json")[0]
