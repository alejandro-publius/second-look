"""The final cut (UPDATE_30 section 4): captions, credits, the 4:00 cap, the voice, and one build.

Everything but the last test is plain Python: caption timing, credits coverage, the length cap and
voice detection. The last one runs ffmpeg on a tiny generated input, with a generated tone in place
of a voice, when ffmpeg is on this machine; it never reads a real voice.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.fetch_footage import FETCHED, FOOTAGE_CSV
from scripts.video_final import (
    END_CARD,
    END_CARD_LICENCE,
    FONT,
    LIVE_LINK,
    MAX_CPS,
    MAX_S,
    MIN_S,
    SUMMARY,
    TAIL_S,
    VIDEO_LICENCE,
    Beat,
    CutError,
    Paths,
    audio_graph,
    beats_from,
    build,
    caption_lines,
    clean,
    credit_sections,
    credits_card_png,
    extract_frames,
    find_voice,
    footage_credits,
    footage_used,
    leading_silence,
    missing_inputs,
    plan_cut,
    read_marks,
    sha256,
    split_cues,
    srt,
    stamp,
    thumbnail_png,
)
from scripts.video_rough import SCREEN, SHOTLIST, Part

TEXT = SHOTLIST.read_text(encoding="utf-8")
BEATS = beats_from(TEXT)
CUT = plan_cut(BEATS)
FETCHED_DATA = json.loads(FETCHED.read_text(encoding="utf-8"))
EPS = 0.002


def screen_beat(time: str, seconds: float, words: str) -> Beat:
    return Beat(time, "x", seconds, words, (Part(time, 1, SCREEN, 0.0, None, False, ""),))


# ---- caption timing ----------------------------------------------------------------------------


def test_every_word_of_every_beat_is_captioned_once_and_in_order() -> None:
    for beat in BEATS:
        said = " ".join(c.text for c in CUT.cues if c.beat == beat.time)
        assert said == clean(beat.words), beat.time
    assert [c.beat for c in CUT.cues] == sorted(
        (c.beat for c in CUT.cues), key=[b.time for b in BEATS].index
    )


def test_captions_stay_inside_their_beat_after_the_lead_in_and_never_overlap() -> None:
    beats = {b.time: b for b in CUT.beats}
    for cue in CUT.cues:
        b = beats[cue.beat]
        assert cue.start >= b.start + b.words_wait - EPS, cue
        assert cue.end <= b.start + b.seconds + EPS, cue
        assert cue.end > cue.start, cue
    for one, two in zip(CUT.cues, CUT.cues[1:], strict=False):
        assert one.end <= two.start + EPS, (one, two)
    # The opening shot plays 3.5 seconds with no words, so no caption covers it.
    assert CUT.cues[0].start >= 3.5 - EPS


def test_no_caption_asks_for_faster_reading_than_the_limit() -> None:
    # 17 letters a second is the usual caption speed for young readers; the script must keep it.
    assert MAX_CPS <= 17.0
    for cue in CUT.cues:
        assert len(cue.text) / (cue.end - cue.start) <= 17.05, cue


def test_a_beat_grows_when_its_words_need_more_time_to_read() -> None:
    words = "A sentence of words. " * 10  # about 210 letters, twelve seconds at the limit
    cut = plan_cut([screen_beat("0:00", 5, words)], credits_s=0)
    assert cut.beats[0].seconds > 12
    short = plan_cut([screen_beat("0:00", 5, "Short.")], credits_s=0)
    assert short.beats[0].seconds == 5


def test_long_sentences_split_at_the_comma_nearest_the_middle() -> None:
    words = (
        "None we know of measures how well each volunteer sees each feature, "
        "and keeps it with every observation. Short one."
    )
    assert split_cues(words) == [
        "None we know of measures how well each volunteer sees each feature,",
        "and keeps it with every observation. Short one.",
    ]
    assert split_cues("One. Two. Three.") == ["One. Two. Three."]
    assert split_cues("(five seconds of quiet) Look.") == ["Look."]


def test_a_slot_left_in_the_words_stops_the_cut() -> None:
    with pytest.raises(CutError, match="slot"):
        plan_cut([screen_beat("0:00", 10, "It found [SLOT: errors] errors.")])
    assert not any("[SLOT" in b.words for b in BEATS)


@pytest.mark.skipif(not FONT.exists(), reason="the caption font is the Mac's Arial")
def test_every_caption_fits_on_two_lines() -> None:
    for cue in CUT.cues:
        assert len(caption_lines(cue.text)) <= 2, cue.text


def test_srt_numbers_each_caption_with_its_times() -> None:
    assert stamp(0) == "00:00:00,000"
    assert stamp(3723.4567) == "01:02:03,457"
    text = srt(CUT.cues)
    blocks = text.strip().split("\n\n")
    assert len(blocks) == len(CUT.cues)
    first = blocks[0].splitlines()
    assert first[0] == "1"
    assert first[1] == f"{stamp(CUT.cues[0].start)} --> {stamp(CUT.cues[0].end)}"
    assert " ".join(first[2:]) == CUT.cues[0].text


def test_the_committed_summary_matches_the_script_it_was_built_from() -> None:
    """A changed word in the script means the cut on disk is stale: run make video-final."""
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["shotlist_sha256"] == sha256(TEXT)
    if not summary["voice_used"]:
        assert summary["captions"]["sha256"] == sha256(srt(CUT.cues))
        assert summary["captions"]["burned_in"] is True
        assert summary["captions"]["cues"] == len(CUT.cues)
        assert [b["time"] for b in summary["beats"]] == [b.time for b in CUT.beats]


# ---- credits -----------------------------------------------------------------------------------


def footage_rows() -> list[dict[str, str]]:
    with FOOTAGE_CSV.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_every_footage_clip_in_the_cut_carries_its_own_credit_line() -> None:
    credits = footage_credits(FETCHED_DATA)
    ok = {c["clip"].removesuffix(".mp4"): c.get("ok") for c in FETCHED_DATA["clips"]}
    rows = {re.sub(r"\.[A-Za-z]{3,4}$", "", r["title"]): r for r in footage_rows()}
    for clip in footage_used(CUT):
        assert clip in credits, clip
        assert ok[clip] is True, clip
        title = re.search(r'^"(.+)" by ', credits[clip])
        assert title, credits[clip]
        row = rows[title.group(1)]
        assert row["author"] in credits[clip] and row["licence"] in credits[clip], clip


def test_the_credits_card_names_every_row_of_footage_csv() -> None:
    lines = [line for _, ls in credit_sections(FETCHED_DATA, footage_used(CUT)) for line in ls]
    for row in footage_rows():
        stem = re.sub(r"\.[A-Za-z]{3,4}$", "", row["title"])
        who = (stem, row["author"], row["licence"])
        assert [line for line in lines if all(w in line for w in who)], row["title"]
    assert set(footage_used(CUT)) == set(footage_credits(FETCHED_DATA))


def test_the_credits_card_names_what_the_screen_recordings_show() -> None:
    screens = dict(credit_sections(FETCHED_DATA, footage_used(CUT)))["Inside the app screens"]
    assert any("Gregwadley" in s and "CC BY-SA 4.0" in s for s in screens)
    assert any("Roger Kidd" in s and "CC BY-SA 2.0" in s for s in screens)
    assert any("CC BY 3.0, YouTube" in s for s in screens)
    assert any("second-look-79t.pages.dev/credits" in s for s in screens)


def test_the_end_card_has_the_live_link_and_the_licence() -> None:
    assert LIVE_LINK == "https://second-look-79t.pages.dev"
    assert LIVE_LINK in END_CARD
    assert f"This video is {VIDEO_LICENCE}" in END_CARD_LICENCE
    assert VIDEO_LICENCE == "CC BY-SA 4.0"


@pytest.mark.skipif(not FONT.exists(), reason="the card's type size is measured in the Mac's Arial")
def test_the_credits_fit_one_card_in_type_a_viewer_can_read(tmp_path: Path) -> None:
    size = credits_card_png(tmp_path / "c.png", credit_sections(FETCHED_DATA, footage_used(CUT)))
    assert size >= 22


def test_a_missing_clip_or_credit_stops_the_build_before_any_grey_card(tmp_path: Path) -> None:
    footage, screens = tmp_path / "footage", tmp_path / "screens"
    footage.mkdir()
    screens.mkdir()
    missing = missing_inputs(CUT, footage, screens, FETCHED_DATA)
    assert any("footage clip" in m for m in missing)
    assert any("screen recording" in m for m in missing)
    for clip in footage_used(CUT):
        (footage / f"{clip}.mp4").write_bytes(b"x")
    for b in CUT.beats:
        (screens / f"{b.screen}.mp4").write_bytes(b"x")
    assert missing_inputs(CUT, footage, screens, FETCHED_DATA) == []
    fewer = {"clips": FETCHED_DATA["clips"][1:]}
    assert any("no credit" in m for m in missing_inputs(CUT, footage, screens, fewer))


# ---- the length cap ----------------------------------------------------------------------------


def test_the_cut_runs_under_four_minutes_and_at_least_three() -> None:
    assert MIN_S <= CUT.total_s < MAX_S == 240
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert MIN_S <= summary["length_s"] < MAX_S
    assert summary["under_4_min"] is True
    assert (summary["width"], summary["height"]) == (1920, 1080)
    assert summary["end_card_link"] == LIVE_LINK
    assert not summary["file"].startswith(("docs/", "./")), "the cut never goes in the repo"


def test_a_cut_at_or_over_four_minutes_is_refused() -> None:
    beats = [screen_beat(f"0:{i:02d}", 58, "Words.") for i in range(4)]  # 232 s
    assert plan_cut(beats, credits_s=7.9).total_s < MAX_S
    with pytest.raises(CutError, match="too long"):
        plan_cut(beats, credits_s=8.0)
    with pytest.raises(CutError, match="too long"):
        plan_cut(beats, credits_s=20.0)


def test_a_voice_too_long_for_four_minutes_is_refused() -> None:
    with pytest.raises(CutError, match="trim the pauses"):
        plan_cut(BEATS, voice_s=300.0)


# ---- the voice ---------------------------------------------------------------------------------


def test_find_voice_takes_m4a_then_wav_then_mp3(tmp_path: Path) -> None:
    assert find_voice(tmp_path) is None
    assert find_voice(tmp_path / "not-there") is None
    (tmp_path / "voice.mp3").write_bytes(b"x")
    assert find_voice(tmp_path) == tmp_path / "voice.mp3"
    (tmp_path / "voice.wav").write_bytes(b"x")
    assert find_voice(tmp_path) == tmp_path / "voice.wav"
    (tmp_path / "voice.m4a").write_bytes(b"x")
    assert find_voice(tmp_path) == tmp_path / "voice.m4a"


def test_find_voice_ignores_other_names_and_an_empty_file(tmp_path: Path) -> None:
    for name in ("voice.aiff", "Voice.M4A.txt", "voice_old.m4a", "take2.wav"):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "voice.m4a").write_bytes(b"")
    assert find_voice(tmp_path) is None


def test_voice_beats_reads_an_audacity_label_export() -> None:
    text = "0.000000\t0.000000\tbeat 1\n# a note\n\n12.5\t12.5\tbeat 2\n30,30,beat 3\n"
    assert read_marks(text, 3, 60.0) == [0.0, 12.5, 30.0]


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("0\n10\n", "has 2 marks"),
        ("0\n10\n5\n", "go up"),
        ("0\n10\n10\n", "go up"),
        ("-1\n10\n20\n", "go up"),
        ("0\n10\n70\n", "past the voice"),
        ("0\nten\n20\n", "not a number"),
    ],
)
def test_voice_beats_refuses_marks_that_cannot_be_right(text: str, why: str) -> None:
    with pytest.raises(CutError, match=why):
        read_marks(text, 3, 60.0)


def test_the_quiet_before_the_first_word_is_found() -> None:
    log = "[silencedetect @ 0x1] silence_start: 0\n[silencedetect @ 0x1] silence_end: 1.25 | x\n"
    assert leading_silence(log) == 1.25
    later = "[silencedetect @ 0x1] silence_start: 4.2\n[silencedetect @ 0x1] silence_end: 5 | x\n"
    assert leading_silence(later) == 0.0
    assert leading_silence("") == 0.0


def test_each_beat_holds_its_own_stretch_of_voice() -> None:
    stretches = [12.0] * len(BEATS)
    stretches[2] = 25.0  # beat 3 runs long in the voice
    marks = [sum(stretches[:i]) for i in range(len(BEATS))]
    voice_s = sum(stretches)
    cut = plan_cut(BEATS, voice_s=voice_s, marks=marks, max_s=1000)
    assert cut.beats[2].seconds >= 25.0
    assert cut.mode == "each beat"
    for i, b in enumerate(cut.beats):
        stretch = (marks[i + 1] if i + 1 < len(marks) else voice_s) - marks[i]
        assert b.voice_from == marks[i]
        assert b.seconds >= b.words_wait + stretch - EPS
        assert b.seconds >= BEATS[i].shot_seconds - EPS
        for cue in (c for c in cut.cues if c.beat == b.time):
            assert b.start + b.words_wait - EPS <= cue.start
            assert cue.end <= b.start + b.words_wait + stretch + EPS
    graph = audio_graph(cut, 1)
    assert graph.count("atrim=start=") == len(BEATS)
    assert f"asplit={len(BEATS)}" in graph


def test_a_whole_voice_plays_unbroken_and_the_beats_follow_it() -> None:
    cut = plan_cut(BEATS, voice_s=200.0, voice_offset=1.0)
    assert cut.mode == "whole voice"
    lead = cut.beats[0].words_wait
    assert abs(cut.cut_s - (lead + 199.0 + TAIL_S)) < 1.0
    graph = audio_graph(cut, 1)
    assert "asplit" not in graph
    assert "atrim=start=1.000" in graph
    assert f"adelay=delays={int(lead * 1000)}" in graph


# ---- docs/video/UPLOAD.md ----------------------------------------------------------------------

UPLOAD = SHOTLIST.parent / "UPLOAD.md"


def paste_field(heading: str) -> str:
    """The code block under a heading of UPLOAD.md: what gets pasted into YouTube."""
    text = UPLOAD.read_text(encoding="utf-8")
    m = re.search(rf"^## {heading}\n.*?```text\n(.*?)```", text, re.M | re.S)
    assert m, heading
    return m.group(1).strip()


def test_the_upload_description_credits_everything_the_cut_shows() -> None:
    description = paste_field("Description")
    for row in footage_rows():
        stem = re.sub(r"\.[A-Za-z]{3,4}$", "", row["title"])
        line = f'"{stem}" by {row["author"]}, {row["licence"]}: {row["source_page"]}'
        assert line in description.splitlines(), line
    screens = dict(credit_sections(FETCHED_DATA, footage_used(CUT)))["Inside the app screens"]
    for line in screens:
        m = re.fullmatch(r'"(.+)" by (.+), (.+), (Wikimedia Commons|YouTube)', line)
        if m:
            assert f'"{m[1]}" by {m[2]}, {m[3]}, {m[4]}: ' in description, line
        else:
            assert "second-look-79t.pages.dev/credits" in line
            assert "lesson and the test are credited one by one at https://" in description
    assert f"This video is released under {VIDEO_LICENCE}" in description
    assert "https://creativecommons.org/licenses/by-sa/4.0/" in description
    assert LIVE_LINK in description


def test_the_upload_fields_fit_youtube() -> None:
    title, description, tags = (paste_field(h) for h in ("Title", "Description", "Tags"))
    assert 0 < len(title) <= 100
    assert len(description) <= 5000
    assert len(tags) <= 500
    for field in (title, description, tags):
        assert "<" not in field and ">" not in field, "YouTube refuses angle brackets"
    steps = UPLOAD.read_text(encoding="utf-8")
    assert "**Unlisted**" in steps
    assert "Standard YouTube License" in steps


# ---- the thumbnail -----------------------------------------------------------------------------


def test_the_thumbnail_is_the_two_landing_photos_under_two_megabytes(tmp_path: Path) -> None:
    from PIL import Image

    out = tmp_path / "thumbnail.png"
    credits = thumbnail_png(out)
    with Image.open(out) as img:
        assert img.size == (1280, 720)
    assert out.stat().st_size <= 2_000_000
    assert [c.split(" by ")[1].split(",")[0] for c in credits] == ["Gregwadley", "Roger Kidd"]


# ---- one real build on a tiny input ------------------------------------------------------------

TINY = """
| Time | Clip file | Seconds | On screen | Alex says | Needs |
|---|---|---|---|---|---|
| 0:00 | aa-screen.mp4 | 2 | a screen | "One short line. Then another." | screen and footage |
| 0:02 | open footage | 2 | footage | "The end." | open footage |

| Part | Beat | Clip | From | Seconds | Shows |
|---|---|---|---|---|---|
| 1.1 | 0:00 | tiny-footage | 0 | 0.5 before the words | a clip |
| 1.2 | 0:00 | screen | | rest | the screen |
| 2.1 | 0:02 | tiny-footage | 0 | rest | the clip again |
"""
FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


def run(*args: str) -> str:
    done = subprocess.run(args, capture_output=True, text=True, check=True)
    return done.stdout + done.stderr


def streams(path: Path) -> list[str]:
    out = run("ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0",
              str(path))  # fmt: skip
    return [s for s in out.split() if s]


def loudest(path: Path) -> float:
    out = run("ffmpeg", "-hide_banner", "-i", str(path), "-map", "0:a", "-af", "volumedetect",
              "-f", "null", "-")  # fmt: skip
    return float(re.findall(r"max_volume: (-?[\d.]+) dB", out)[0])


@pytest.mark.skipif(not FFMPEG, reason="needs ffmpeg and ffprobe")
def test_a_tiny_cut_builds_silent_then_with_a_tone_for_a_voice(tmp_path: Path) -> None:
    footage, screens, voice = tmp_path / "footage", tmp_path / "screens", tmp_path / "voice"
    for d in (footage, screens, voice):
        d.mkdir()
    source = "testsrc=size=1920x1080:rate=30:duration=1"
    for path in (footage / "tiny-footage.mp4", screens / "aa-screen.mp4"):
        run("ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", source,
            "-pix_fmt", "yuv420p", str(path))  # fmt: skip
    shotlist = tmp_path / "SHOTLIST.md"
    shotlist.write_text(TINY, encoding="utf-8")
    fetched = tmp_path / "fetched.json"
    credit = '"Tiny" by Test, CC0, Wikimedia Commons'
    fetched.write_text(json.dumps({"clips": [{"clip": "tiny-footage.mp4", "credit": credit}]}))
    paths = Paths(
        shotlist=shotlist,
        fetched=fetched,
        footage=footage,
        screens=screens,
        voice_dir=voice,
        out=tmp_path / "final" / "cut.mp4",
        summary=tmp_path / "final_cut.json",
        thumbnail=None,
    )

    silent = build(paths, credits_s=1.0)
    assert silent["voice_used"] is False and silent["voice_fit"] is None
    assert (silent["width"], silent["height"]) == (1920, 1080)
    assert streams(paths.out) == ["video", "audio"]
    assert loudest(paths.out) < -80, "no scratch voice and no music"
    srt_file = paths.out.with_suffix(".srt")
    assert sha256(srt_file.read_text(encoding="utf-8")) == silent["captions"]["sha256"]
    assert silent["captions"]["burned_in"] is True
    assert credit in silent["credits"]
    beats = beats_from(TINY)
    assert abs(silent["length_s"] - plan_cut(beats, credits_s=1.0).total_s) < 0.15
    assert json.loads(paths.summary.read_text()) == silent  # type: ignore[union-attr]

    run("ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
        "sine=frequency=440:duration=3", str(voice / "voice.wav"))  # fmt: skip
    (voice / "voice_beats.txt").write_text("0\n1.5\n", encoding="utf-8")
    each = build(paths, credits_s=1.0)
    assert each["voice_used"] is True and each["voice_fit"] == "each beat"
    assert streams(paths.out) == ["video", "audio", "subtitle"]
    assert loudest(paths.out) > -40, "the tone is laid under the pictures"
    assert each["captions"]["burned_in"] is False and each["captions"]["subtitles_track"] is True
    assert srt_file.is_file()

    (voice / "voice_beats.txt").unlink()
    whole = build(paths, credits_s=1.0)
    assert whole["voice_fit"] == "whole voice"
    assert streams(paths.out) == ["video", "audio", "subtitle"]
    assert abs(whole["length_s"] - (0.5 + 3.0 + TAIL_S + 1.0)) < 0.3

    frames = extract_frames(paths.out, tmp_path / "frames", every=2)
    assert [f.name for f in frames] == ["frame_000.png", "frame_002.png", "frame_004.png",
                                        "frame_006.png"]  # fmt: skip
