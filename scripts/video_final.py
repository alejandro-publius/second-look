"""The final cut of the video, captions only or with Alex's voice (UPDATE_30 section 4).

`make video-final` builds one 1920 by 1080, 30 fps video, under 4:00, from the same shot list,
footage clips and screen recordings as the rough cut (scripts/video_rough.py), with no title cards
and no scratch voice:

- the words of each beat (the "Alex says" column of docs/video/SHOTLIST.md, the same words as
  docs/video/VOICE_SCRIPT.md) burned in as captions, a sentence or two at a time, spread over the
  beat by their length. A beat runs as long as the shot list says, or longer if its words need
  more time to read at MAX_CPS letters a second;
- every footage clip keeps the credit line scripts/cut_footage.py drew in its lower left corner,
  so each credit is on screen while its footage shows. The caption sits above it;
- the end card over the last shot: the live link, the repository and "This video is CC BY-SA 4.0";
- a credits card after it with every footage credit, and the photos and walk clip that the screen
  recordings show;
- silence for sound. No music, so there is no music licence to check.

A voice file in ~/second-look-media/voice/ (voice.m4a, voice.wav or voice.mp3, the first found in
that order) replaces the captions' own timing. Which way it fits depends on the files:

- "each beat": voice_beats.txt beside the voice gives the second each beat starts in the voice, one
  line per beat (an Audacity label export works: only the first number on a line is read). Each
  beat gets its own stretch of voice and keeps its shot list length, or grows to hold it;
- "whole voice": with no voice_beats.txt the voice plays unbroken from the first words, after any
  quiet at its start, and each beat is cut to where its words should fall, by its share of the
  script's letters.

With a voice the captions are no longer burned in: they go into the mp4 as a subtitles track. The
captions are always written beside the mp4 as an .srt. Nothing here writes a video file into the
repository. The summary, docs/video/final_cut.json, is committed: the length, the size, the beats,
the captions file's SHA-256 and whether a voice was used.

Run: make video-final
     make video-frames             one PNG every 10 seconds, named by the second, for a review
     uv run python scripts/video_final.py --screens ~/second-look-depth/docs/video/clips
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import yaml
from PIL import Image, ImageDraw, ImageFont

from scripts.fetch_footage import FETCHED
from scripts.video_rough import (
    FIT,
    FPS,
    PHONE,
    SCREEN,
    SHOTLIST,
    VIDEO_LICENCE,
    H,
    Part,
    Piece,
    W,
    duration,
    ff,
    footage_parts,
    piece_video,
    plan,
    rows,
)

ROOT = Path(__file__).resolve().parents[1]
MEDIA = Path(os.environ.get("SECOND_LOOK_MEDIA", str(Path.home() / "second-look-media")))
FOOTAGE = Path(os.environ.get("SECOND_LOOK_CLIPS", str(MEDIA / "clips")))
SCREENS = Path(os.environ.get("SECOND_LOOK_SCREENS", str(ROOT / "docs" / "video" / "clips")))
VOICE_DIR = Path(os.environ.get("SECOND_LOOK_VOICE", str(MEDIA / "voice")))
FINAL = Path(os.environ.get("SECOND_LOOK_FINAL", str(MEDIA / "final")))
OUT = FINAL / "second-look-final.mp4"
THUMBNAIL = FINAL / "thumbnail.png"
SUMMARY = ROOT / "docs" / "video" / "final_cut.json"
TEST_ITEMS = ROOT / "content" / "test_items.yaml"
PHOTO_MANIFEST = ROOT / "photos" / "manifest.csv"
WALKS = ROOT / "content" / "walks.yaml"

VOICE_NAMES = ("voice.m4a", "voice.wav", "voice.mp3")
MARKS_NAME = "voice_beats.txt"
LIVE_LINK = "https://second-look-79t.pages.dev"
REPO_LINK = "github.com/alejandro-publius/second-look"
LICENCE_LINK = "creativecommons.org/licenses/by-sa/4.0"
MAX_S = 240.0  # under 4:00, not at it
MIN_S = 180.0  # scripts/submit_check.py wants 3 to 5 minutes
MAX_CPS = 17.0  # letters a second a 12 year old can read in a caption
MAX_CUE_CHARS = 100  # a caption is at most two lines
CAPTION_GAP_S = 0.3  # the last caption of a beat goes a moment before the pictures change
CREDITS_S = 8.0
TAIL_S = 2.0  # "whole voice": the end card stays this long after the last word
SRT_LINE = 52
THUMB_MAX_BYTES = 1_900_000

FONT = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
BOLD = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
INK = (255, 255, 255)
CARD = (24, 44, 52)
CAPTION_SIZE = 46
CAPTION_LIFT = 120  # the footage credit sits in the bottom 100 pixels; the caption stays above it
ENCODE = ("-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p")

END_CARD = (
    "Second Look",
    "Take the two-minute test:",
    LIVE_LINK,
    f"Code: {REPO_LINK}",
    "No camera needed.",
)
END_CARD_LICENCE = (
    f"This video is {VIDEO_LICENCE} ({LICENCE_LINK}), because several creek clips in it are "
    "CC BY-SA. Every credit is on the next card and at second-look-79t.pages.dev/credits"
)
APP_PHOTOS_NOTE = (
    "The photos inside the lesson and the test are credited one by one at "
    "second-look-79t.pages.dev/credits"
)


class CutError(Exception):
    """The cut cannot be built as asked; the message says why and what to do."""


# ---- the words -------------------------------------------------------------------------------

SENTENCE = re.compile(r"(?<=[.?!])\s+")


def clean(words: str) -> str:
    """The words as captioned: no stage direction in brackets, single spaces, no slot left."""
    if "[SLOT" in words:
        raise CutError(f"a slot is still in the words, fill it from results/ first: {words[:60]}")
    text = re.sub(r"\([^)]*\)", " ", words).replace('"', "")
    return re.sub(r"\s+", " ", text).strip()


def halves(sentence: str, limit: int = MAX_CUE_CHARS) -> list[str]:
    """A sentence too long for one caption, split at the comma nearest its middle, or a space."""
    if len(sentence) <= limit:
        return [sentence]
    middle = len(sentence) / 2
    commas = [m.end() for m in re.finditer(r", ", sentence)]
    spaces = [m.end() for m in re.finditer(r" ", sentence)]
    cuts = [c for c in commas if limit >= c - 1 and len(sentence) - c <= limit] or spaces
    if not cuts:
        return [sentence]
    at = min(cuts, key=lambda c: abs(c - middle))
    return [*halves(sentence[:at].strip(), limit), *halves(sentence[at:].strip(), limit)]


def split_cues(words: str, limit: int = MAX_CUE_CHARS) -> list[str]:
    """The beat's words as captions: whole sentences, packed together while they fit."""
    cues: list[str] = []
    cur = ""
    for sentence in SENTENCE.split(clean(words)):
        for piece in halves(sentence, limit):
            trial = f"{cur} {piece}".strip()
            if len(trial) <= limit:
                cur = trial
            else:
                cues.append(cur)
                cur = piece
    if cur:
        cues.append(cur)
    return cues


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str
    beat: str


def time_cues(texts: list[str], start: float, end: float, beat: str) -> list[Cue]:
    """Captions one after another from start to end, each given time by its length."""
    total = sum(len(t) for t in texts)
    if not total:
        return []
    out, at = [], start
    for i, text in enumerate(texts):
        stop = end if i == len(texts) - 1 else at + (end - start) * len(text) / total
        out.append(Cue(round(at, 3), round(stop, 3), text, beat))
        at = stop
    return out


def reading_seconds(words: str) -> float:
    return len(clean(words)) / MAX_CPS


def stamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def wrap_chars(text: str, width: int = SRT_LINE) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if len(trial) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return [*lines, cur] if cur else lines


def srt(cues: list[Cue]) -> str:
    return "\n".join(
        f"{i}\n{stamp(c.start)} --> {stamp(c.end)}\n" + "\n".join(wrap_chars(c.text)) + "\n"
        for i, c in enumerate(cues, 1)
    )


# ---- the voice -------------------------------------------------------------------------------


def find_voice(folder: Path) -> Path | None:
    """The first of voice.m4a, voice.wav, voice.mp3 in the folder that has something in it."""
    for name in VOICE_NAMES:
        path = folder / name
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def read_marks(text: str, beats: int, voice_s: float) -> list[float]:
    """voice_beats.txt: the second each beat starts in the voice, the first number on each line."""
    marks = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        first = re.split(r"[\s,]+", line)[0]
        try:
            marks.append(float(first))
        except ValueError as err:
            raise CutError(f"{MARKS_NAME}: not a number of seconds: {line!r}") from err
    if len(marks) != beats:
        raise CutError(f"{MARKS_NAME} has {len(marks)} marks; the shot list has {beats} beats")
    if marks[0] < 0 or any(b <= a for a, b in zip(marks, marks[1:], strict=False)):
        raise CutError(f"{MARKS_NAME}: the marks must start at 0 or later and go up: {marks}")
    if marks[-1] >= voice_s:
        raise CutError(f"{MARKS_NAME}: the last mark, {marks[-1]} s, is past the voice's end")
    return marks


SILENCE_END = re.compile(r"silence_end:\s*([\d.]+)")
SILENCE_START = re.compile(r"silence_start:\s*(-?[\d.]+)")


def leading_silence(silencedetect_log: str) -> float:
    """How long the voice is quiet before the first word, from ffmpeg's silencedetect output."""
    starts = SILENCE_START.findall(silencedetect_log)
    ends = SILENCE_END.findall(silencedetect_log)
    if starts and ends and float(starts[0]) <= 0.05:
        return float(ends[0])
    return 0.0


# ---- the plan ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Beat:
    time: str
    screen: str  # the beat's screen recording, "01-landing"
    shot_seconds: float
    words: str
    parts: tuple[Part, ...]


def beats_from(text: str) -> list[Beat]:
    table = footage_parts(text)
    out = []
    for b in rows(text):
        parts = table.get(b["time"]) or [Part(b["time"], 1, SCREEN, 0.0, None, False, "")]
        out.append(Beat(b["time"], b["clip"], float(b["seconds"]), b["says"], tuple(parts)))
    unknown = sorted(set(table) - {b.time for b in out})
    if unknown:
        raise CutError(f"the footage table names beats the shot list has not: {unknown}")
    return out


@dataclass(frozen=True)
class PlannedBeat:
    time: str
    screen: str
    start: float
    seconds: float
    words_wait: float
    pieces: tuple[Piece, ...]
    voice_from: float | None = None  # "each beat": this beat's stretch of the voice
    voice_to: float | None = None


@dataclass
class CutPlan:
    beats: list[PlannedBeat]
    cues: list[Cue]
    credits_s: float
    mode: str  # "captions only", "each beat" or "whole voice"
    voice_offset: float = 0.0  # "whole voice": the quiet skipped at the voice's start
    notes: list[str] = field(default_factory=list)

    @property
    def cut_s(self) -> float:
        return self.beats[-1].start + self.beats[-1].seconds if self.beats else 0.0

    @property
    def total_s(self) -> float:
        return round(self.cut_s + self.credits_s, 3)


def frames(seconds: float) -> float:
    """A length rounded to whole frames, so the pictures, captions and voice never drift."""
    return round(seconds * FPS) / FPS


def plan_cut(
    beats: list[Beat],
    voice_s: float | None = None,
    marks: list[float] | None = None,
    voice_offset: float = 0.0,
    credits_s: float = CREDITS_S,
    max_s: float = MAX_S,
) -> CutPlan:
    """Where every beat starts, how long it runs, and when each caption shows.

    No voice: each beat runs its shot list length, or longer if its words need it at MAX_CPS.
    Marks: each beat holds its own stretch of voice. A voice with no marks: the voice runs unbroken
    and each beat ends where its share of the script's letters ends in the voice.
    """
    if not beats:
        raise CutError("no beats in the shot list")
    mode = "captions only" if voice_s is None else ("each beat" if marks else "whole voice")
    letters = [len(clean(b.words)) for b in beats]
    planned: list[PlannedBeat] = []
    cues: list[Cue] = []
    at = 0.0
    lead_1 = plan(list(beats[0].parts), beats[0].shot_seconds, 0.0)[1]
    speech = (voice_s or 0.0) - voice_offset
    for i, b in enumerate(beats):
        last = i == len(beats) - 1
        v_from = v_to = None
        if mode == "captions only":
            length, lead, pieces = plan(list(b.parts), b.shot_seconds, reading_seconds(b.words))
        elif mode == "each beat":
            assert marks is not None and voice_s is not None
            v_from, v_to = marks[i], (voice_s if last else marks[i + 1])
            length, lead, pieces = plan(list(b.parts), b.shot_seconds, v_to - v_from)
        else:
            ends = lead_1 + speech * sum(letters[: i + 1]) / sum(letters)
            target = ends + (TAIL_S if last else 0.0) - at
            length, lead, pieces = plan(list(b.parts), max(target, 0.1), 0.0)
        length = frames(length)
        words_from = at + lead
        if mode == "each beat":
            assert v_from is not None and v_to is not None
            words_to = min(words_from + (v_to - v_from), at + length)
        elif mode == "whole voice":
            words_to = at + length - (TAIL_S if last else 0.0)
        else:
            words_to = at + length - CAPTION_GAP_S
        cues += time_cues(split_cues(b.words), words_from, words_to, b.time)
        planned.append(
            PlannedBeat(b.time, b.screen, round(at, 3), length, lead, tuple(pieces), v_from, v_to)
        )
        at = round(at + length, 6)
    cut = CutPlan(planned, cues, credits_s, mode, voice_offset)
    if cut.total_s >= max_s:
        over = cut.total_s - max_s
        raise CutError(
            f"the cut would run {cut.total_s:.1f} s with the {credits_s:.0f} s credits card, "
            f"{over:.1f} s too long for under {max_s:.0f} s"
            + ("; trim the pauses in the voice" if voice_s is not None else "")
        )
    return cut


# ---- credits ---------------------------------------------------------------------------------


def licence_words(name: str) -> str:
    """photos/manifest.csv and content/walks.yaml write CC-BY-SA-4.0; a credit says CC BY-SA 4.0."""
    m = re.fullmatch(r"CC-((?:BY|SA|NC|ND)(?:-(?:BY|SA|NC|ND))*)-(\d\.\d)", name.strip())
    if m:
        return f"CC {m.group(1)} {m.group(2)}"
    return {"public-domain": "Public domain", "cc0": "CC0"}.get(name.strip().lower(), name)


def where(url: str) -> str:
    if "commons.wikimedia.org" in url:
        return "Wikimedia Commons"
    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube"
    return url


def file_title(url: str, fallback: str) -> str:
    m = re.search(r"/wiki/File:(.+)$", url)
    if not m:
        return fallback
    stem = re.sub(r"\.[A-Za-z0-9]{2,4}$", "", unquote(m.group(1)))
    return stem.replace("_", " ")


def footage_credits(fetched: dict[str, Any]) -> dict[str, str]:
    """Clip name to the credit line scripts/cut_footage.py drew on it, for every clip kept."""
    return {c["clip"].removesuffix(".mp4"): c["credit"] for c in fetched.get("clips", [])}


def landing_photos(
    test_items: Path = TEST_ITEMS, manifest: Path = PHOTO_MANIFEST
) -> list[dict[str, str]]:
    """The two creek photos on the landing page, left then right, with their manifest rows."""
    items = yaml.safe_load(test_items.read_text(encoding="utf-8"))
    with manifest.open(encoding="utf-8", newline="") as f:
        photos = {r["id"]: r for r in csv.DictReader(f)}
    out = []
    for w in items["warmup"]:
        r = photos[w["photo_id"]]
        out.append(
            {
                "id": w["photo_id"],
                "file": r["file"],
                "title": file_title(r["source_url"], w["photo_id"]),
                "author": r["author"],
                "licence": licence_words(r["license"]),
                "where": where(r["source_url"]),
                "source": r["source_url"],
            }
        )
    return out


def screen_credits(
    test_items: Path = TEST_ITEMS, manifest: Path = PHOTO_MANIFEST, walks: Path = WALKS
) -> list[str]:
    """What the screen recordings show that is not ours: the two landing photos and the walk clip.

    The landing page shows the warm-up pair; apps/web/scripts/record-clips.mjs records the first
    walk in content/walks.yaml.
    """
    out = [
        f'"{p["title"]}" by {p["author"]}, {p["licence"]}, {p["where"]}'
        for p in landing_photos(test_items, manifest)
    ]
    first = (yaml.safe_load(walks.read_text(encoding="utf-8")).get("walks") or [None])[0]
    if first:
        out.append(
            f'"{first["title"]}" by {first["author"]}, {licence_words(first["license"])}, '
            f"{where(first['source_url'])}"
        )
    return out


def credit_sections(fetched: dict[str, Any], used: list[str]) -> list[tuple[str, list[str]]]:
    """The credits card: the footage in the order it plays, then the rest, then the app screens."""
    lines = footage_credits(fetched)
    order = [c for c in used if c in lines] + sorted(c for c in lines if c not in used)
    return [
        ("Creek footage and photos", [lines[c] for c in order]),
        ("Inside the app screens", [*screen_credits(), APP_PHOTOS_NOTE]),
    ]


def footage_used(cut: CutPlan) -> list[str]:
    seen: list[str] = []
    for b in cut.beats:
        for p in b.pieces:
            if p.clip not in (SCREEN, PHONE) and p.clip not in seen:
                seen.append(p.clip)
    return seen


def screens_used(cut: CutPlan) -> list[str]:
    return [b.screen for b in cut.beats if any(p.clip in (SCREEN, PHONE) for p in b.pieces)]


def missing_inputs(
    cut: CutPlan, footage: Path, screens: Path, fetched: dict[str, Any]
) -> list[str]:
    """Everything the cut needs that is not there. The final cut never shows a grey card."""
    credits = footage_credits(fetched)
    out = []
    for clip in footage_used(cut):
        if not (footage / f"{clip}.mp4").is_file():
            out.append(f"footage clip {footage / clip}.mp4")
        if clip not in credits:
            out.append(f"no credit for {clip} in {FETCHED.name}: run scripts/cut_footage.py")
    for name in screens_used(cut):
        raw = screens / "raw" / f"{name}.webm"
        if not ((screens / f"{name}.mp4").is_file() or raw.is_file()):
            out.append(f"screen recording {screens / name}.mp4 (make video-clips)")
    return out


# ---- pictures --------------------------------------------------------------------------------


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = BOLD if bold else FONT
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def wrap(draw: ImageDraw.ImageDraw, text: str, f: Any, width: float) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=f) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return [*lines, cur] if cur else lines


def caption_lines(text: str) -> list[str]:
    draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    return wrap(draw, text, font(CAPTION_SIZE), W - 320)


def caption_png(path: Path, text: str) -> None:
    """One caption, centred, on a dark box fitted to it, above the footage credit line."""
    lines = caption_lines(text)
    if len(lines) > 2:
        raise CutError(f"a caption needs {len(lines)} lines, two at most: {text}")
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    f = font(CAPTION_SIZE)
    line_h = CAPTION_SIZE + 14
    widest = max(draw.textlength(line, font=f) for line in lines)
    bottom = H - CAPTION_LIFT
    top = bottom - line_h * len(lines) - 28
    draw.rounded_rectangle(
        [(W - widest) / 2 - 28, top, (W + widest) / 2 + 28, bottom], radius=14, fill=(0, 0, 0, 185)
    )
    y = top + 14
    for line in lines:
        draw.text(((W - draw.textlength(line, font=f)) / 2, y), line, font=f, fill=INK)
        y += line_h
    img.save(path)


def end_card_png(path: Path) -> None:
    """Name, live link, repository, "No camera needed." and the licence, on a dark panel."""
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    text = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text)
    y = 120
    for i, line in enumerate(END_CARD):
        size = 96 if i == 0 else 50
        draw.text((150, y), line, font=font(size, bold=i in (0, 2)), fill=INK)
        y += size + 26
    for line in wrap(draw, END_CARD_LICENCE, font(32), W - 300):
        draw.text((150, y + 10), line, font=font(32), fill=INK)
        y += 42
    ImageDraw.Draw(panel).rounded_rectangle(
        [100, 80, W - 100, y + 40], radius=24, fill=(0, 0, 0, 180)
    )
    Image.alpha_composite(panel, text).save(path)


def credits_card_png(path: Path, sections: list[tuple[str, list[str]]]) -> int:
    """Every credit on one card, in the largest type that fits. Returns the type size."""
    footer = f"This video: {VIDEO_LICENCE}, {LICENCE_LINK}.   Try it: {LIVE_LINK}"
    for size in range(32, 17, -1):
        img = Image.new("RGB", (W, H), CARD)
        draw = ImageDraw.Draw(img)
        y = 60
        draw.text((120, y), "Credits", font=font(64, bold=True), fill=INK)
        y += 100
        for heading, lines in sections:
            draw.text((120, y), heading, font=font(size + 4, bold=True), fill=INK)
            y += int((size + 4) * 1.5)
            for line in lines:
                for part in wrap(draw, line, font(size), W - 280):
                    draw.text((150, y), part, font=font(size), fill=INK)
                    y += int(size * 1.32)
            y += size
        draw.text((120, y + 10), footer, font=font(size, bold=True), fill=INK)
        if y + 10 + size * 1.4 <= H - 50:
            img.save(path)
            return size
    raise CutError("the credits do not fit on one card")


def thumbnail_png(path: Path, test_items: Path = TEST_ITEMS) -> list[str]:
    """1280 by 720: the two landing creek photos side by side and the question. Returns credits."""
    tw, th = 1280, 720
    pair = landing_photos(test_items)[:2]
    img = Image.new("RGB", (tw, th), (255, 255, 255))
    half = (tw - 8) // 2
    for k, p in enumerate(pair):
        src = Image.open(ROOT / "photos" / p["file"]).convert("RGB")
        scale = max(half / src.width, th / src.height)
        size = (round(src.width * scale), round(src.height * scale))
        src = src.resize(size, Image.Resampling.LANCZOS)
        left, top = (src.width - half) // 2, (src.height - th) // 2
        img.paste(src.crop((left, top, left + half, top + th)), (k * (half + 8), 0))
    shade = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    ImageDraw.Draw(shade).rectangle([0, 0, tw, 170], fill=(0, 0, 0, 175))
    ImageDraw.Draw(shade).rectangle([0, th - 34, tw, th], fill=(0, 0, 0, 150))
    out = Image.alpha_composite(img.convert("RGBA"), shade)
    draw = ImageDraw.Draw(out)
    question = "Which creek is healthier?"
    f = font(84, bold=True)
    draw.text(((tw - draw.textlength(question, font=f)) / 2, 38), question, font=f, fill=INK)
    sides = zip(("left", "right"), pair, strict=True)
    line = "Photos: " + "; ".join(f"{side} {p['author']}, {p['licence']}" for side, p in sides)
    draw.text((14, th - 27), line + ", Wikimedia Commons", font=font(18), fill=INK)
    rgb = out.convert("RGB")
    rgb.save(path, optimize=True)
    if path.stat().st_size > THUMB_MAX_BYTES:  # YouTube takes a thumbnail under 2 MB
        rgb.quantize(256, dither=Image.Dither.FLOYDSTEINBERG).save(path, optimize=True)
    return [f'"{p["title"]}" by {p["author"]}, {p["licence"]}, {p["where"]}' for p in pair]


# ---- ffmpeg ----------------------------------------------------------------------------------


def probe(path: Path) -> dict[str, Any]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    data: dict[str, Any] = json.loads(out)
    return data


def voice_quiet_start(voice: Path) -> float:
    log = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(voice), "-af", "silencedetect=noise=-40dB:d=0.3",
         "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr  # fmt: skip
    return leading_silence(log)


def screen_clip(screens: Path, name: str, work: Path) -> Path | None:
    """The beat's recording; a raw webm newer than its mp4 is converted in the work folder."""
    mp4 = screens / f"{name}.mp4"
    raw = screens / "raw" / f"{name}.webm"
    if raw.is_file() and (not mp4.is_file() or raw.stat().st_mtime > mp4.stat().st_mtime):
        out = work / f"screen-{name}.mp4"
        if not out.exists():
            ff("-i", str(raw), "-an", "-vf", FIT, "-c:v", "libx264", "-crf", "20", str(out))
        return out
    return mp4 if mp4.is_file() else None


Shown = list[tuple[float, float, Path]]  # a caption's start and end in its beat, and its picture


def beat_video(work: Path, index: int, parts: list[Path], seconds: float, captions: Shown) -> Path:
    """The pieces one after another with each caption on top for its own few seconds."""
    out = work / f"beat{index:03d}.mp4"
    n = len(parts)
    inputs = [a for p in parts for a in ("-i", str(p))]
    graph = "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[c0]"
    for k, (a, b, png) in enumerate(captions):
        inputs += ["-loop", "1", "-framerate", str(FPS), "-i", str(png)]
        graph += (
            f";[c{k}][{n + k}:v]overlay=0:0:enable='gte(t,{a:.3f})*lt(t,{b:.3f})'"
            f":eof_action=pass[c{k + 1}]"
        )
    graph += f";[c{len(captions)}]tpad=stop_mode=clone:stop_duration=1,format=yuv420p,setsar=1[v]"
    ff(*inputs, "-filter_complex", graph, "-map", "[v]", "-an",
       "-frames:v", str(round(seconds * FPS)), "-r", str(FPS), *ENCODE, str(out))  # fmt: skip
    return out


def still_video(work: Path, name: str, still: Path, seconds: float) -> Path:
    out = work / f"{name}.mp4"
    ff("-loop", "1", "-framerate", str(FPS), "-i", str(still), "-vf", FIT, "-an",
       "-frames:v", str(round(seconds * FPS)), "-r", str(FPS), *ENCODE, str(out))  # fmt: skip
    return out


def audio_graph(cut: CutPlan, voice_input: int) -> str:
    """The voice laid under the pictures: one stretch per beat, or the whole voice unbroken."""
    fmt = "aformat=sample_rates=48000:channel_layouts=stereo"
    if cut.mode == "whole voice":
        ms = int(round(cut.beats[0].words_wait * 1000))
        return (
            f"[{voice_input}:a]atrim=start={cut.voice_offset:.3f},asetpts=PTS-STARTPTS,{fmt},"
            f"adelay=delays={ms}:all=1,apad,atrim=end={cut.total_s:.3f}[a]"
        )
    n = len(cut.beats)
    graph = f"[{voice_input}:a]{fmt},asplit={n}" + "".join(f"[s{i}]" for i in range(n))
    for i, b in enumerate(cut.beats):
        assert b.voice_from is not None and b.voice_to is not None
        ms = int(round(b.words_wait * 1000))
        graph += (
            f";[s{i}]atrim=start={b.voice_from:.3f}:end={b.voice_to:.3f},asetpts=PTS-STARTPTS,"
            f"adelay=delays={ms}:all=1,apad,atrim=end={b.seconds:.3f},asetpts=PTS-STARTPTS[b{i}]"
        )
    graph += ";" + "".join(f"[b{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1,apad[p]"
    graph += f";[p]atrim=end={cut.total_s:.3f}[a]"
    return graph


def extract_frames(video: Path, folder: Path, every: int = 10) -> list[Path]:
    """One PNG every `every` seconds, named by the second: frame_000.png, frame_010.png, ..."""
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("frame_*.png"):
        old.unlink()
    out = []
    length = duration(video)
    t = 0
    while t < length:
        path = folder / f"frame_{t:03d}.png"
        ff("-ss", str(t), "-i", str(video), "-frames:v", "1", str(path))
        out.append(path)
        t += every
    return out


# ---- the build -------------------------------------------------------------------------------


@dataclass
class Paths:
    shotlist: Path = SHOTLIST
    fetched: Path = FETCHED
    footage: Path = FOOTAGE
    screens: Path = SCREENS
    voice_dir: Path = VOICE_DIR
    out: Path = OUT
    summary: Path | None = SUMMARY
    thumbnail: Path | None = THUMBNAIL


def home(path: Path) -> str:
    return str(path).replace(str(Path.home()), "~", 1)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plan_for(paths: Paths, credits_s: float = CREDITS_S) -> tuple[CutPlan, Path | None]:
    """The plan, and the voice it lays in, if there is one."""
    beats = beats_from(paths.shotlist.read_text(encoding="utf-8"))
    voice = find_voice(paths.voice_dir)
    if voice is None:
        return plan_cut(beats, credits_s=credits_s), None
    voice_s = duration(voice)
    marks_file = paths.voice_dir / MARKS_NAME
    if marks_file.is_file():
        marks = read_marks(marks_file.read_text(encoding="utf-8"), len(beats), voice_s)
        return plan_cut(beats, voice_s, marks, credits_s=credits_s), voice
    offset = voice_quiet_start(voice)
    return plan_cut(beats, voice_s, voice_offset=offset, credits_s=credits_s), voice


def build(paths: Paths, credits_s: float = CREDITS_S) -> dict[str, Any]:
    fetched = json.loads(paths.fetched.read_text(encoding="utf-8"))
    cut, voice = plan_for(paths, credits_s)
    missing = missing_inputs(cut, paths.footage, paths.screens, fetched)
    if missing:
        raise CutError("missing, so nothing was built:\n  " + "\n  ".join(missing))
    burn = voice is None
    captions = srt(cut.cues)
    srt_path = paths.out.with_suffix(".srt")
    paths.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="second-look-final-") as tmp:
        work = Path(tmp)
        end_card = work / "end_card.png"
        end_card_png(end_card)
        segments = []
        for i, b in enumerate(cut.beats):
            screen = screen_clip(paths.screens, b.screen, work)
            files = []
            for j, piece in enumerate(b.pieces):
                last = i == len(cut.beats) - 1 and j == len(b.pieces) - 1
                path, gap = piece_video(
                    work, f"p{i:03d}_{j}", piece, screen, paths.footage, end_card if last else None
                )
                if gap:
                    raise CutError(f"{b.time}: {gap}")
                files.append(path)
            shown = []
            if burn:
                for k, cue in enumerate(c for c in cut.cues if c.beat == b.time):
                    png = work / f"cap{i:03d}_{k}.png"
                    caption_png(png, cue.text)
                    shown.append((cue.start - b.start, cue.end - b.start, png))
            segments.append(beat_video(work, i, files, b.seconds, shown))
        card = work / "credits.png"
        sections = credit_sections(fetched, footage_used(cut))
        type_size = credits_card_png(card, sections)
        segments.append(still_video(work, "credits", card, cut.credits_s))
        listing = work / "list.txt"
        listing.write_text("".join(f"file '{s}'\n" for s in segments), encoding="utf-8")
        pictures = work / "pictures.mp4"
        ff("-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(pictures))
        srt_path.write_text(captions, encoding="utf-8")
        staged = work / "final.mp4"
        if voice is None:
            ff("-i", str(pictures), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
               "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
               "-t", f"{cut.total_s:.3f}", "-movflags", "+faststart", str(staged))  # fmt: skip
        else:
            ff("-i", str(pictures), "-i", str(voice), "-i", str(srt_path),
               "-filter_complex", audio_graph(cut, 1),
               "-map", "0:v", "-map", "[a]", "-map", "2:s", "-c:v", "copy", "-c:a", "aac",
               "-b:a", "192k", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng",
               "-t", f"{cut.total_s:.3f}", "-movflags", "+faststart", str(staged))  # fmt: skip
        shutil.move(str(staged), paths.out)
    info = probe(paths.out)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    length = float(info["format"]["duration"])
    thumb_credits = thumbnail_png(paths.thumbnail) if paths.thumbnail else []
    summary = {
        "file": home(paths.out),
        "committed": False,
        "made_by": "make video-final (scripts/video_final.py)",
        "length_s": round(length, 1),
        "length": f"{int(length // 60)}:{int(length % 60):02d}",
        "under_4_min": length < MAX_S,
        "bytes": paths.out.stat().st_size,
        "width": video["width"],
        "height": video["height"],
        "fps": FPS,
        "streams": [s["codec_type"] for s in info["streams"]],
        "voice_used": voice is not None,
        "voice_file": home(voice) if voice else None,
        "voice_fit": None if voice is None else cut.mode,
        "sound": "the voice" if voice else "silence, no music",
        "captions": {
            "file": home(srt_path),
            "sha256": sha256(captions),
            "cues": len(cut.cues),
            "burned_in": burn,
            "subtitles_track": not burn,
            "max_letters_a_second": MAX_CPS,
        },
        "shotlist_sha256": sha256(paths.shotlist.read_text(encoding="utf-8")),
        "video_licence": VIDEO_LICENCE,
        "end_card_link": LIVE_LINK,
        "credits_card_s": cut.credits_s,
        "credits_card_type_px": type_size,
        "credits": [line for _, lines in sections for line in lines],
        "thumbnail": home(paths.thumbnail) if paths.thumbnail else None,
        "thumbnail_credits": thumb_credits,
        "footage_folder": home(paths.footage),
        "screens_folder": home(paths.screens),
        "footage_clips_used": footage_used(cut),
        "beats": [
            {
                "time": b.time,
                "starts_at_s": round(b.start, 2),
                "seconds": round(b.seconds, 2),
                "words_wait_s": round(b.words_wait, 2),
                "captions": sum(1 for c in cut.cues if c.beat == b.time),
                "parts": [
                    {"clip": p.clip, "from_s": round(p.start, 2), "seconds": round(p.seconds, 2)}
                    for p in b.pieces
                ],
            }
            for b in cut.beats
        ],
    }
    if paths.summary:
        paths.summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", "utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--footage", type=Path, default=FOOTAGE, help="the cut footage clips")
    parser.add_argument("--screens", type=Path, default=SCREENS, help="the screen recordings")
    parser.add_argument("--voice-dir", type=Path, default=VOICE_DIR)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument(
        "--frames-into", type=Path, default=None,
        help="do not build: take one frame every 10 s of the built cut into this folder",
    )  # fmt: skip
    args = parser.parse_args(argv)
    out = args.out.expanduser()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("video-final: needs ffmpeg and ffprobe")
        return 1
    if args.frames_into:
        if not out.is_file():
            print(f"video-final: no cut at {home(out)} yet; run make video-final")
            return 1
        found = extract_frames(out, args.frames_into.expanduser())
        print(f"video-frames: {len(found)} frames in {home(args.frames_into.expanduser())}")
        return 0
    paths = Paths(
        footage=args.footage.expanduser(),
        screens=args.screens.expanduser(),
        voice_dir=args.voice_dir.expanduser(),
        out=out,
        thumbnail=out.parent / THUMBNAIL.name,
    )
    try:
        summary = build(paths)
    except CutError as err:
        print(f"video-final: {err}")
        return 1
    fit = f", voice fitted: {summary['voice_fit']}" if summary["voice_used"] else ", no voice"
    print(
        f"video-final: {summary['file']}, {summary['length']} ({summary['length_s']} s), "
        f"{summary['width']}x{summary['height']}, {summary['bytes'] / 1e6:.1f} MB, "
        f"{summary['captions']['cues']} captions{fit}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
