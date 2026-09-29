"""CHANGELOG.md names every day that has commits, so make go-public's changelog step can pass.

On Sep 29 the file ended at Sep 25, and the step would have stopped the flip on Sep 30 for the
days after it. These tests ask the step's own functions, with the day fixed, so they do not turn
red by themselves when the calendar moves.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scripts import go_public as gp

ROOT = Path(__file__).resolve().parents[2]
FLIP_DAY = date(2026, 9, 30)


def real_notes() -> str:
    return gp.release_notes((ROOT / gp.CHANGELOG).read_text(encoding="utf-8"))


def commit_days_before(day: date) -> set[date]:
    days = gp.commit_days(ROOT)
    if days is None:
        pytest.skip("not a git checkout, so there are no commit days to read")
    return {d for d in days if gp.FIRST_DAY <= d < day}


def test_every_day_with_commits_before_the_flip_has_a_heading() -> None:
    wanted = commit_days_before(FLIP_DAY)
    missing = sorted(wanted - gp.days_named(real_notes()))
    assert missing == [], f"CHANGELOG.md has no ### line for {[str(d) for d in missing]}"


def test_the_changelog_step_passes_on_the_flip_day() -> None:
    commit_days_before(FLIP_DAY)
    run = gp.Run(root=ROOT, today=FLIP_DAY)
    step = gp.step_changelog(run)
    assert step.result == "PASS", step.output


def test_the_days_run_from_the_first_to_the_day_before_the_flip_with_no_gap() -> None:
    days = gp.days_named(real_notes())
    every = {date(2026, 9, d) for d in range(gp.FIRST_DAY.day, FLIP_DAY.day)}
    assert sorted(every - days) == []


def test_every_day_heading_has_a_line_under_it() -> None:
    notes = real_notes()
    parts = ("\n" + notes).split("\n### ")[1:]
    assert parts
    for part in parts:
        heading, _, body = part.partition("\n")
        assert any(line.startswith("- ") for line in body.splitlines()), f"### {heading} is empty"
