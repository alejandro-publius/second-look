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
    for phrase in (
        "sewage",
        "sewer",
        "most people",
        "polluted",
        "unsafe",
        "contaminat",
        "toxic",
        "waste water",
        "wastewater",
    ):
        assert phrase not in spoken, phrase


# UPDATE_22 6.5: the creek footage is open footage from Wikimedia Commons, never our own.
OUR_OWN = (
    "our visit",
    "we visited",
    "our trip",
    "we went",
    "we filmed",
    "i filmed",
    "we shot",
    "our footage",
    "our own footage",
    "our video of",
    "our record of",
    "our photos of",
    "at the creek,",
)


def test_no_beat_calls_the_open_footage_ours() -> None:
    spoken = " ".join(w for _, w in shotlist_beats()).lower()
    for phrase in OUR_OWN:
        assert phrase not in spoken, phrase


def test_the_outfall_is_never_called_sewage_anywhere_in_the_video_files() -> None:
    # Not in the words, and not in what is on screen, the notes or the footage table either.
    for name in ("SHOTLIST.md", "VOICE_SCRIPT.md", "teleprompter.html", "CREDITS.md"):
        text = (VIDEO / name).read_text(encoding="utf-8").lower()
        assert "sewage" not in text, name


def test_the_words_point_at_the_creek_on_screen_the_honest_way() -> None:
    # A creek on screen is "a creek like this one" or is named; the Strawberry Creek photos are
    # named as Strawberry Creek.
    spoken = " ".join(w for _, w in shotlist_beats())
    assert "creeks like this one" in spoken
    assert "a creek like this one" in spoken
    assert "Strawberry Creek" in spoken
