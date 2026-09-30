"""The privacy papers name both data locks as core/lock.py holds them (UPDATE_33).

Nobody took the test before the first lock, so the same study runs a second time under
docs/analysis_plan_v3.md, with a second lock. The privacy page, docs/DATA_HANDLING.md,
SECURITY.md and docs/THREAT_MODEL.md all say when that lock is. Each reads its instant from a
person's typing, not from the code, so this holds the words against the constants: if a lock
moves in core/lock.py and a paper keeps the old day, this goes red.

It checks the instants and the plan's name, not what the papers say around them.
"""

from __future__ import annotations

import json
import re
from datetime import UTC
from pathlib import Path
from zoneinfo import ZoneInfo

from core import lock

ROOT = Path(__file__).resolve().parents[2]
PAPERS = {
    "docs/DATA_HANDLING.md": ROOT / "docs" / "DATA_HANDLING.md",
    "SECURITY.md": ROOT / "SECURITY.md",
    "docs/THREAT_MODEL.md": ROOT / "docs" / "THREAT_MODEL.md",
}
LOCALE = ROOT / "content" / "locales" / "en.json"
PACIFIC = ZoneInfo("America/Los_Angeles")


def iso(ts) -> str:
    return ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_words(ts) -> str:
    """The way the privacy page writes an instant: 'Oct 3 at 04:00 UTC'."""
    return ts.astimezone(UTC).strftime("%b %-d at %H:%M UTC")


def pacific_words(ts) -> str:
    """The way the privacy page writes the same instant in California: 'Fri Oct 2 at 21:00 PDT'."""
    local = ts.astimezone(PACIFIC)
    return local.strftime("%a %b %-d at %H:%M ") + local.tzname()


def privacy_strings() -> dict[str, str]:
    words = json.loads(LOCALE.read_text(encoding="utf-8"))
    return {k: v for k, v in words.items() if k.startswith("privacy.")}


def test_each_paper_names_both_locks_and_the_second_wave_plan() -> None:
    first, second = iso(lock.DATA_LOCK_UTC), iso(lock.SECOND_LOCK_UTC)
    for name, path in PAPERS.items():
        text = path.read_text(encoding="utf-8")
        assert first in text, f"{name} does not name the first lock {first}"
        assert second in text, f"{name} does not name the second lock {second}"
        assert "docs/analysis_plan_v3.md" in text, f"{name} does not name the second wave's plan"


def test_the_papers_name_no_lock_instant_the_code_does_not_hold() -> None:
    """A date written as a lock must be one of the two locks or the wave's opening."""
    known = {iso(lock.DATA_LOCK_UTC), iso(lock.SECOND_LOCK_UTC), iso(lock.WAVE2_OPEN_UTC)}
    instant = re.compile(r"\b2026-\d\d-\d\dT\d\d:\d\d:\d\dZ\b")
    for name, path in PAPERS.items():
        found = set(instant.findall(path.read_text(encoding="utf-8")))
        strange = found - known
        assert not strange, f"{name} names instants the code does not hold: {sorted(strange)}"


def test_the_privacy_page_says_when_the_second_window_closes() -> None:
    words = privacy_strings()
    assert "privacy.windows" in words, "the privacy page has no paragraph about the two windows"
    body = words["privacy.windows"]
    assert utc_words(lock.SECOND_LOCK_UTC) in body, body
    assert pacific_words(lock.SECOND_LOCK_UTC) in body, body
    assert utc_words(lock.DATA_LOCK_UTC) in body, body
    assert "docs/analysis_plan_v3.md" in body, body


def test_the_privacy_page_words_for_the_second_lock_match_the_code_labels() -> None:
    """core/lock.py carries its own local label; the page must agree with it on the day and hour."""
    label = lock.SECOND_LOCK_LOCAL_LABEL  # "Friday Oct 2, 2026 at 21:00 PDT"
    body = privacy_strings()["privacy.windows"]
    found = re.search(r"(\w+ \d+), 2026 at (\d\d:\d\d \w+)", label)
    assert found is not None, f"core/lock.py's label {label!r} is not a day and an hour"
    day, hour = found.groups()
    assert day in body and hour in body, f"{body!r} does not match {label!r}"
