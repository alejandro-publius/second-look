"""Which clip plays in which beat of the rough cut (UPDATE_22 6.4), and how the parts are timed."""

from __future__ import annotations

import json

import pytest

from scripts.fetch_footage import FETCHED
from scripts.submit_check import video_links
from scripts.video_rough import (
    PHONE,
    SCREEN,
    SHOTLIST,
    SUMMARY,
    VIDEO_LICENCE,
    Part,
    footage_parts,
    plan,
    rows,
)

TEXT = SHOTLIST.read_text(encoding="utf-8")
BEATS = rows(TEXT)
TABLE = footage_parts(TEXT)
CLIPS = {c["clip"].removesuffix(".mp4"): c for c in json.loads(FETCHED.read_text())["clips"]}
ESTUARY = "berkeley-strawberry-creek-estuary-berkeley"


def beat_saying(words: str) -> dict[str, str]:
    found = [b for b in BEATS if words in b["says"]]
    assert len(found) == 1, words
    return found[0]


def clips_in(beat: dict[str, str]) -> list[str]:
    return [p.clip for p in TABLE.get(beat["time"], [])]


def test_no_beat_waits_for_a_creek_visit_or_a_person_on_camera() -> None:
    for b in BEATS:
        assert b["needs"] not in ("creek footage", "person on camera"), b["time"]


def test_every_open_footage_beat_has_footage_and_no_other_does() -> None:
    for b in BEATS:
        parts = TABLE.get(b["time"], [])
        footage = [p for p in parts if p.is_footage]
        assert bool(footage) == ("open footage" in b["needs"]), b["time"]
        screens = [p for p in parts if not p.is_footage]
        if "screen recording" in b["needs"] and parts:
            assert screens, b["time"]
        if "screen recording" not in b["needs"]:
            assert not screens, b["time"]


def test_every_named_clip_was_cut_and_kept_and_every_cut_clip_plays() -> None:
    named = {p.clip for parts in TABLE.values() for p in parts if p.is_footage}
    assert named <= set(CLIPS), sorted(named - set(CLIPS))
    assert set(CLIPS) <= named, sorted(set(CLIPS) - named)
    for name in named:
        assert CLIPS[name]["ok"] is True, name


def test_each_part_starts_inside_its_clip() -> None:
    for parts in TABLE.values():
        for p in parts:
            if p.is_footage:
                room = CLIPS[p.clip]["seconds"] - p.start
                assert room > 1.0, (p.beat, p.clip)
                if p.seconds is not None:
                    assert p.seconds <= room + 0.05, (p.beat, p.clip)


def test_the_clips_fit_the_beats_as_update_22_asks() -> None:
    opening = TABLE[BEATS[0]["time"]][0]
    assert opening.clip.startswith("berkeley-") and opening.before_words
    assert any(c.startswith("natural-") for c in clips_in(beat_saying("doing better")))
    assert any(c.startswith("problem-") for c in clips_in(beat_saying("walk past")))
    assert any(c.startswith("pipes-") for c in clips_in(beat_saying("pipe or drain outlet")))
    assert any(c.startswith("pipes-") for c in clips_in(beat_saying("worth a lab test")))
    first_score = next(b for b in BEATS if "score" in b["says"])
    assert clips_in(first_score)[0].startswith("gauge-")
    assert any(c.startswith("action-") for c in clips_in(beat_saying("what it needs")))
    city = clips_in(beat_saying("follower city"))
    assert any(c.startswith("berkeley-") for c in city)
    assert any(c.startswith("global-") for c in clips_in(beat_saying("any other city")))


def test_the_estuary_is_the_very_last_shot_and_only_there() -> None:
    last = TABLE[BEATS[-1]["time"]]
    assert last[-1].clip == ESTUARY
    elsewhere = [p for parts in TABLE.values() for p in parts if p.clip == ESTUARY]
    assert elsewhere == [last[-1]]


def test_the_person_on_camera_beat_is_a_screen_recording_in_a_phone_frame() -> None:
    check = beat_saying("the check asks one question at a time")
    screens = [c for c in clips_in(check) if c in (SCREEN, PHONE)]
    assert screens and all(c == PHONE for c in screens)
    assert "phone frame" in check["needs"]


def test_every_beat_the_table_names_is_in_the_shot_list() -> None:
    assert set(TABLE) <= {b["time"] for b in BEATS}


def part(clip: str, seconds: float | None, before: bool = False, start: float = 0.0) -> Part:
    return Part("0:00", 1, clip, start, seconds, before, "")


def test_rest_takes_what_is_left_and_the_voice_waits_for_the_opening() -> None:
    parts = [part("berkeley-a", 3.5, before=True), part(SCREEN, None), part("natural-b", 3)]
    length, delay, pieces = plan(parts, 15, 11.1)
    assert delay == 3.5
    assert length == pytest.approx(15.0)
    assert [p.seconds for p in pieces] == pytest.approx([3.5, 8.5, 3.0])


def test_a_beat_grows_when_the_words_need_it() -> None:
    length, _, pieces = plan([part("gauge-a", 5), part(SCREEN, None)], 15, 14.9)
    assert length == pytest.approx(15.3)
    assert sum(p.seconds for p in pieces) == pytest.approx(length)


def test_a_silent_opening_makes_room_for_all_the_words_after_it() -> None:
    parts = [part("berkeley-a", 3.5, before=True), part(SCREEN, None)]
    length, delay, pieces = plan(parts, 10, 9.0)
    assert delay == 3.5
    assert length == pytest.approx(3.5 + 9.0 + 0.4)
    assert pieces[-1].seconds == pytest.approx(9.4)


def test_screen_parts_carry_on_through_the_recording() -> None:
    parts = [part(SCREEN, 5.5), part("action-a", 5, start=2.5), part(SCREEN, None)]
    _, _, pieces = plan(parts, 20, 14)
    assert [p.start for p in pieces] == [0.0, 2.5, 5.5]


def test_without_rest_the_last_part_stretches() -> None:
    _, _, pieces = plan([part("problem-a", 7), part("berkeley-b", 6)], 15, 14)
    assert pieces[-1].seconds == pytest.approx(8.0)


def test_bad_tables_are_refused() -> None:
    with pytest.raises(ValueError):
        plan([part(SCREEN, None), part("a", None)], 10, 5)
    with pytest.raises(ValueError):
        plan([part(SCREEN, 3), part("a", 2, before=True)], 10, 5)


def test_devpost_says_the_video_licence_without_faking_a_video_link() -> None:
    # make submit-check passes the video slot on any line with "video" and a link, so the licence
    # line next to the slot must carry no link of its own.
    devpost = (SHOTLIST.parents[1] / "devpost.md").read_text(encoding="utf-8")
    lines = [ln for ln in devpost.splitlines() if "CC BY-SA 4.0" in ln and "video" in ln.lower()]
    assert lines, "docs/devpost.md must say the video is CC BY-SA 4.0"
    assert all(not video_links(ln) for ln in lines)


def test_the_committed_summary_has_nothing_missing_and_says_the_licence() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["committed"] is False
    assert summary["video_licence"] == VIDEO_LICENCE == "CC BY-SA 4.0"
    assert summary["waiting_for_footage_or_recording"] == []
    assert set(summary["footage_clips_used"]) <= set(CLIPS)
    assert summary["played"][-1]["parts"][-1]["clip"] == ESTUARY
