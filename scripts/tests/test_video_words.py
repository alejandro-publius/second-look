"""The video voiced by ElevenLabs: its words are the same in the voice script and the shot list,
every number in them still matches the file it comes from, and its upload page credits what it shows
and says the voice is an AI voice. The first video, read by Alex, is kept in docs/video/v1/; the
tests of its builder read the shot list there."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "docs" / "video"


def voice_script_beats() -> list[tuple[str, str]]:
    beats = []
    for line in (VIDEO / "VOICE_SCRIPT.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| \d+ \| (\d:\d\d) \| [^|]+ \| (.+) \|$", line)
        if m:
            beats.append((m[1], m[2].strip()))
    return beats


def shotlist_rows() -> list[list[str]]:
    rows = []
    for line in (VIDEO / "SHOTLIST.md").read_text(encoding="utf-8").splitlines():
        if re.match(r"\| \d:\d\d \|", line):
            rows.append([c.strip() for c in line.split("|")[1:-1]])
    return rows


def shotlist_beats() -> list[tuple[str, str]]:
    return [(r[0], r[3]) for r in shotlist_rows() if r[3]]


def spoken() -> str:
    return " ".join(w for _, w in voice_script_beats())


def constant(path: str, name: str) -> int:
    m = re.search(rf"^{name} = (\d+)$", (ROOT / path).read_text(encoding="utf-8"), re.M)
    assert m, (path, name)
    return int(m[1])


def code_block(text: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\n\n```text\n(.*?)\n```", text, re.S | re.M)
    assert m, heading
    return m[1]


def test_the_voice_script_and_the_shot_list_hold_the_same_eighteen_beats() -> None:
    beats = voice_script_beats()
    assert len(beats) == 18  # the cover and one beat per slide, 01 to 17
    assert shotlist_beats() == beats


def test_the_spoken_words_fit_three_and_a_half_to_four_and_three_quarter_minutes() -> None:
    # At the voice's pace, about 150 words a minute, with the holds on screens and the credits.
    words = len(spoken().split())
    assert 600 <= words <= 680, words


def test_no_beat_says_what_a_pipe_means_or_what_most_people_pick() -> None:
    words = spoken().lower()
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
        assert phrase not in words, phrase


# UPDATE_22 6.5: open footage is never called our own. "At the creek," was on this list for the
# first video, whose words stood over open footage; here it names where a volunteer uses the check,
# and the same beat says the creek on screen is open footage checked from a desk.
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
)


def test_no_beat_calls_the_open_footage_ours() -> None:
    words = spoken().lower()
    for phrase in OUR_OWN:
        assert phrase not in words, phrase


def test_the_walk_beat_says_its_creek_is_open_footage_seen_from_a_desk() -> None:
    walk = [w for _, w in voice_script_beats() if w.startswith("At the creek,")]
    assert len(walk) == 1
    assert "the creek is real footage from an open video, checked from a desk" in walk[0]


def test_no_video_file_calls_a_pipe_sewage() -> None:
    for name in ("SHOTLIST.md", "VOICE_SCRIPT.md", "UPLOAD.md"):
        assert "sewage" not in (VIDEO / name).read_text(encoding="utf-8").lower(), name


def test_every_number_in_the_words_matches_the_file_it_comes_from() -> None:
    w = spoken()
    items = yaml.safe_load((ROOT / "content" / "test_items.yaml").read_text(encoding="utf-8"))[
        "items"
    ]
    assert "sixteen real photos" in w and len(items) == 16
    assert "for ninety days" in w and constant("core/records.py", "SCORE_VALID_DAYS") == 90
    app = json.loads((ROOT / "content" / "app_strings.json").read_text(encoding="utf-8"))
    assert "in six languages" in w and len(app["languages"]) == 6
    assert (
        "Two follow-ups, at most." in w
        and constant("core/followups.py", "DEFAULT_MAX_QUESTIONS") == 2
    )
    models = json.loads((ROOT / "results" / "model_pass_table.json").read_text(encoding="utf-8"))[
        "models"
    ]
    assert "Four models, three times each." in w and len(models) == 4
    assert {len(f["runs"]) for m in models.values() for f in m.values()} == {3}
    gate = json.loads((ROOT / "results" / "footage_latest.json").read_text(encoding="utf-8"))[
        "gate"
    ]
    assert "the gate stopped twenty-nine of sixty-four flags" in w
    assert (gate["dropped"], gate["candidates"]) == (29, 64)
    fhir = json.loads((ROOT / "results" / "fhir_validation.json").read_text(encoding="utf-8"))
    assert "with zero validation errors" in w and fhir["errors"] == 0
    assert "two contributors who passed the pipe questions" in w
    assert constant("core/act.py", "PIPE_OBSERVERS_NEEDED") == 2
    fallback = app["fallback"]
    assert "we found fourteen places" in w and sum(len(v) for v in fallback.values()) == 14
    assert "The Italian pipe question asks about rainwater." in w
    assert "rainwater" in fallback["it"]["draining_pipes.text"]


def test_the_record_and_the_city_page_say_on_screen_that_their_records_are_samples() -> None:
    for row in shotlist_rows():
        if "`/spot?id=example`" in row[2] or "`/city?" in row[2]:
            assert 'A note on screen: "Sample records, made up for this video."' in row[2], row[1]


def test_the_upload_description_credits_what_the_video_shows_and_names_the_ai_voice() -> None:
    page = (VIDEO / "UPLOAD.md").read_text(encoding="utf-8")
    title, description, tags = (code_block(page, h) for h in ("Title", "Description", "Tags"))
    walk = next(
        x
        for x in yaml.safe_load((ROOT / "content" / "walks.yaml").read_text(encoding="utf-8"))[
            "walks"
        ]
        if x["id"] == "v02"
    )
    licence = walk["license"].replace("-", " ")
    assert (
        f'"{walk["title"]}" by {walk["author"]}, {licence}, YouTube: {walk["source_url"]}'
        in description
    )
    assert '"Norman Creek as concrete channel" by Gregwadley, CC BY-SA 4.0' in description
    assert "by Roger Kidd, CC BY-SA 2.0" in description
    assert "credited one by one at https://second-look-79t.pages.dev/credits" in description
    assert "The narration is an AI voice" in description
    assert (
        "This video is released under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)"
        in description
    )
    assert "https://second-look-79t.pages.dev" in description
    assert 0 < len(title) <= 100 and len(description) <= 5000 and len(tags) <= 500
    for field in (title, description, tags):
        assert "<" not in field and ">" not in field, "YouTube refuses angle brackets"
    assert "**Unlisted**" in page and "Altered content: choose **Yes**" in page


# UPDATE_22 6.7: nobody visits the creek for the video, so nothing Alex or a judge reads may still
# promise that trip, or the real check he was to file there.
ALEX_READS = (
    "README.md",
    "docs/ALEX_TODO.md",
    "docs/SUBMISSION_CHECKLIST.md",
    "docs/video/SHOTLIST.md",
    "docs/video/VOICE_SCRIPT.md",
    "docs/video/UPLOAD.md",
    "docs/video/RECORD_AT_THE_CREEK.md",
)
TRIP = (
    "visit to the creek arrives",
    "minutes at the creek",
    "minutes at strawberry creek",
    "while you are there",
    "person filmed at the creek",
)


def test_nothing_alex_reads_still_promises_the_creek_trip() -> None:
    for name in ALEX_READS:
        text = " ".join((ROOT / name).read_text(encoding="utf-8").lower().split())
        for phrase in TRIP:
            assert phrase not in text, (name, phrase)
