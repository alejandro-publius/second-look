"""The words Alex reads are the same in the shot list, the voice script and the teleprompter."""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "docs" / "video"
SLOT = re.compile(r"\[SLOT:[^]]*\]")


def shotlist_beats() -> list[tuple[str, str]]:
    beats = []
    for line in (VIDEO / "SHOTLIST.md").read_text(encoding="utf-8").splitlines():
        if re.match(r"\| \d:\d\d \|", line):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            beats.append((cells[0], cells[4].strip('"')))
    return beats


def voice_script_beats() -> list[tuple[str, str]]:
    beats = []
    for line in (VIDEO / "VOICE_SCRIPT.md").read_text(encoding="utf-8").splitlines():
        if re.match(r"\| \d+ \| \d:\d\d \|", line):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            beats.append((cells[1], cells[3]))
    return beats


def teleprompter_beats() -> list[tuple[str, str]]:
    page = (VIDEO / "teleprompter.html").read_text(encoding="utf-8")
    found = re.findall(r'<section><p class="t">([^<]+)</p><p>(.*?)</p></section>', page)
    return [(t, html.unescape(re.sub(r"</?mark>", "", w))) for t, w in found]


def test_the_three_files_hold_the_same_fourteen_beats() -> None:
    shots = shotlist_beats()
    assert len(shots) == 14
    assert voice_script_beats() == shots
    assert teleprompter_beats() == shots


def test_the_spoken_words_fit_three_minutes_forty_five() -> None:
    words = sum(len(SLOT.sub("X", w).split()) for _, w in shotlist_beats())
    assert 520 <= words <= 580, words


def test_no_beat_says_what_a_pipe_means_or_what_most_people_pick() -> None:
    spoken = " ".join(w for _, w in shotlist_beats()).lower()
    for phrase in ("sewage", "most people", "polluted", "unsafe"):
        assert phrase not in spoken, phrase
