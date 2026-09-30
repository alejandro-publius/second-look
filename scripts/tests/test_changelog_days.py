"""CHANGELOG.md names every day that has commits, so make go-public's changelog step can pass.

On Sep 29 the file ended at Sep 25, and the step would have stopped the flip for the days after
it. The flip is on the morning of Sat Oct 3, and the days from Sep 30 to Oct 2 get their lines
that morning (docs/SUBMISSION_DAY.md). These tests hold the days written so far: they ask the
step's own functions with the day fixed at the first day the file does not cover yet, so they do
not turn red by themselves when the calendar moves, and the step run on the flip day still asks
for every day up to Oct 2.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from scripts import go_public as gp

ROOT = Path(__file__).resolve().parents[2]
WRITTEN_UP_TO = date(2026, 9, 30)  # the first day the changelog does not name yet
FLIP_DAY = date(2026, 10, 3)


def real_notes() -> str:
    return gp.release_notes((ROOT / gp.CHANGELOG).read_text(encoding="utf-8"))


def commit_days_before(day: date) -> set[date]:
    days = gp.commit_days(ROOT)
    if days is None:
        pytest.skip("not a git checkout, so there are no commit days to read")
    return {d for d in days if gp.FIRST_DAY <= d < day}


def test_every_day_with_commits_before_the_written_day_has_a_heading() -> None:
    wanted = commit_days_before(WRITTEN_UP_TO)
    missing = sorted(wanted - gp.days_named(real_notes()))
    assert missing == [], f"CHANGELOG.md has no ### line for {[str(d) for d in missing]}"


def test_the_changelog_step_passes_on_the_written_day() -> None:
    commit_days_before(WRITTEN_UP_TO)
    run = gp.Run(root=ROOT, today=WRITTEN_UP_TO)
    step = gp.step_changelog(run)
    assert step.result == "PASS", step.output


def test_the_release_section_names_the_flip_day_and_not_sep_30() -> None:
    text = (ROOT / gp.CHANGELOG).read_text(encoding="utf-8")
    heading = next(line for line in text.splitlines() if line.startswith(f"## {gp.TAG}"))
    assert f"{FLIP_DAY:%b} {FLIP_DAY.day}" in heading, heading
    assert "Sep 30" not in heading


def test_the_days_run_from_the_first_to_the_written_day_with_no_gap() -> None:
    days = gp.days_named(real_notes())
    # Every calendar day from the first to the day before WRITTEN_UP_TO, across the month's end.
    every = {gp.FIRST_DAY + timedelta(days=n) for n in range((WRITTEN_UP_TO - gp.FIRST_DAY).days)}
    assert len(every) >= 14
    assert sorted(every - days) == []


def test_every_day_heading_has_a_line_under_it() -> None:
    notes = real_notes()
    parts = ("\n" + notes).split("\n### ")[1:]
    assert parts
    for part in parts:
        heading, _, body = part.partition("\n")
        assert any(line.startswith("- ") for line in body.splitlines()), f"### {heading} is empty"
