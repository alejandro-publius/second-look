"""The rough cut, as far as software can take it (Update 14 section 7 item 3, UPDATE_22 6.4).

Reads the two tables in docs/video/SHOTLIST.md and builds one 1920 by 1080, 30 fps video:

- a 3 second title card before each beat, with its start time and what is on screen;
- the beat itself, from its parts in the table "Footage in each beat": open creek footage from
  ~/second-look-media/clips/ (made by scripts/cut_footage.py; SECOND_LOOK_CLIPS or --footage reads
  them from elsewhere), the beat's own screen recording (apps/web/scripts/record-clips.mjs writes
  the raw webm; this script converts it), or that recording inside a plain phone outline. A beat
  the table does not name plays its screen recording alone. A clip or recording that is missing
  becomes a grey card that names it;
- the line Alex says, burned in as a caption, above the footage credit line;
- the end card over the last shot, with the video's licence, CC BY-SA 4.0;
- a SCRATCH voice from macOS `say`, only so the timing can be checked. The file name says scratch.
  Alex replaces it with his own voice.

ffmpeg on this Mac has no drawtext filter, so the cards and captions are drawn with Pillow and laid
over the clip. Nothing here is committed: the clips and the cut are video files. The summary,
docs/video/rough_cut.json, is, with the length, the size and which clip plays where.

Run: make video-rough
     uv run python scripts/video_rough.py --footage /another/clips/folder
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SHOTLIST = ROOT / "docs" / "video" / "SHOTLIST.md"
CLIPS = ROOT / "docs" / "video" / "clips"
RAW = CLIPS / "raw"
FOOTAGE = Path(
    os.environ.get("SECOND_LOOK_CLIPS", str(Path.home() / "second-look-media" / "clips"))
)
OUT = ROOT / "docs" / "video" / "rough_cut_scratch_voice.mp4"
SUMMARY = ROOT / "docs" / "video" / "rough_cut.json"
W, H, FPS = 1920, 1080, 30
TITLE_S = 3.0
FONT = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
GREY = (92, 96, 100)
INK = (255, 255, 255)
BACKDROP = "0x2b2f33"
# The default voice on this Mac can come out silent, so the scratch voice names one.
VOICE = os.environ.get("SECOND_LOOK_SAY_VOICE", "Samantha")
# The footage credit sits in the bottom CAPTION_LIFT pixels; the caption stays above it.
CAPTION_LIFT = 110
SCREEN = "screen"
PHONE = "screen in a phone frame"
BEFORE = "before the words"
VIDEO_LICENCE = "CC BY-SA 4.0"
END_CARD = (
    "Second Look",
    "Take the two-minute test: second-look-79t.pages.dev",
    "github.com/alejandro-publius/second-look",
    "No camera needed.",
)
END_CARD_LICENCE = (
    f"This video is {VIDEO_LICENCE}, because several creek clips in it are CC BY-SA. "
    "Creek footage and photos from Wikimedia Commons, credited at second-look-79t.pages.dev/credits"
)


def rows(text: str) -> list[dict[str, str]]:
    """The shot list table: time, clip, seconds, on screen, line, needs."""
    out = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 6 or not re.fullmatch(r"\d+:\d\d", cells[0]):
            continue
        time, clip, seconds, screen, says, needs = cells
        out.append(
            {
                "time": time,
                "clip": Path(clip).stem,
                "seconds": seconds,
                "screen": screen.replace("`", ""),
                "says": says.strip('"'),
                "needs": needs,
            }
        )
    return out


@dataclass(frozen=True)
class Part:
    """One row of the table "Footage in each beat"."""

    beat: str  # the beat's start time, as in the shot list: "0:00"
    order: int
    clip: str  # a footage clip name, SCREEN or PHONE
    start: float  # seconds into a footage clip; a screen part carries on where the last one ended
    seconds: float | None  # None means the rest of the beat
    before_words: bool
    shows: str

    @property
    def is_footage(self) -> bool:
        return self.clip not in (SCREEN, PHONE)


PART_ROW = re.compile(r"^\|\s*(\d+)\.(\d+)\s*\|\s*(\d+:\d\d)\s*\|")
SECONDS = re.compile(rf"^(\d+(?:\.\d+)?|rest)(?: ({BEFORE}))?$")


def footage_parts(text: str) -> dict[str, list[Part]]:
    """The parts of every beat the footage table names, in order, keyed by the beat's time."""
    out: dict[str, list[Part]] = {}
    for line in text.splitlines():
        match = PART_ROW.match(line.strip())
        if not match:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            raise ValueError(f"a footage row needs 6 cells: {line}")
        _, beat, clip, start, seconds, shows = cells
        clip = clip.strip("`")
        when = SECONDS.match(seconds)
        if not when:
            raise ValueError(f"seconds must be a number or rest, then maybe '{BEFORE}': {line}")
        out.setdefault(beat, []).append(
            Part(
                beat=beat,
                order=int(match.group(2)),
                clip=clip,
                start=float(start) if start else 0.0,
                seconds=None if when.group(1) == "rest" else float(when.group(1)),
                before_words=bool(when.group(2)),
                shows=shows,
            )
        )
    for parts in out.values():
        parts.sort(key=lambda p: p.order)
    return out


@dataclass(frozen=True)
class Piece:
    clip: str
    start: float
    seconds: float
    shows: str


def plan(
    parts: list[Part], shot_seconds: float, voice_seconds: float
) -> tuple[float, float, list[Piece]]:
    """How long the beat runs, how long the voice waits, and every piece with its exact length.

    The beat runs at least as long as the shot list says and long enough for the words. A part
    marked 'rest' takes what is left, at least one second; with no 'rest' part the last part
    stretches or the beat grows. Screen parts carry on through the recording in order.
    """
    leading = 0
    while leading < len(parts) and parts[leading].before_words:
        leading += 1
    if any(p.before_words for p in parts[leading:]):
        raise ValueError(
            f"{parts[0].beat}: only the first parts of a beat can come before the words"
        )
    if any(p.seconds is None for p in parts[:leading]):
        raise ValueError(f"{parts[0].beat}: a part before the words needs a length")
    lead = sum(p.seconds or 0.0 for p in parts[:leading])
    length = max(shot_seconds, lead + voice_seconds + 0.4)
    fixed = sum(p.seconds for p in parts if p.seconds is not None)
    rests = [p for p in parts if p.seconds is None]
    if len(rests) > 1:
        raise ValueError(f"{parts[0].beat}: one 'rest' part at most")
    seconds = [p.seconds for p in parts]
    if rests:
        length = max(length, fixed + 1.0)
        seconds[parts.index(rests[0])] = length - fixed
    elif fixed < length:
        seconds[-1] = (seconds[-1] or 0.0) + length - fixed
    else:
        length = fixed
    pieces, screen_at = [], 0.0
    for p, s in zip(parts, seconds, strict=True):
        assert s is not None
        start = p.start if p.is_footage else screen_at
        if not p.is_footage:
            screen_at += s
        pieces.append(Piece(p.clip, start, s, p.shows))
    return length, lead, pieces


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.truetype(str(FONT), size) if FONT.exists() else ImageFont.load_default()


def wrap(draw: ImageDraw.ImageDraw, text: str, f: object, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=f) <= width:  # type: ignore[arg-type]
            cur = trial
        else:
            lines.append(cur)
            cur = w
    return [*lines, cur] if cur else lines


def card(path: Path, heading: str, body: str, background: tuple[int, int, int]) -> None:
    img = Image.new("RGB", (W, H), background)
    draw = ImageDraw.Draw(img)
    y = 300
    for line in wrap(draw, heading, font(72), W - 240):
        draw.text((120, y), line, font=font(72), fill=INK)
        y += 90
    y += 30
    for line in wrap(draw, body, font(40), W - 240)[:8]:
        draw.text((120, y), line, font=font(40), fill=INK)
        y += 54
    img.save(path)


def caption(path: Path, text: str) -> None:
    """A transparent frame with the line in a dark band, above the footage credit line."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    lines = wrap(draw, text, font(44), W - 300)[:3]
    band = 40 + 58 * len(lines)
    bottom = H - CAPTION_LIFT
    draw.rectangle([0, bottom - band - 40, W, bottom], fill=(0, 0, 0, 170))
    y = bottom - band - 10
    for line in lines:
        x = (W - draw.textlength(line, font=font(44))) / 2
        draw.text((x, y), line, font=font(44), fill=INK)
        y += 58
    img.save(path)


def end_card(path: Path) -> None:
    """The end card: name, links, "No camera needed." and the video's licence, on a dark panel."""
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    text = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text)
    y = 130
    for i, line in enumerate(END_CARD):
        size = 96 if i == 0 else 48
        draw.text((150, y), line, font=font(size), fill=INK)
        y += size + 30
    for line in wrap(draw, END_CARD_LICENCE, font(32), W - 300):
        draw.text((150, y + 10), line, font=font(32), fill=INK)
        y += 42
    # The panel is drawn to fit the text, so a longer licence line never spills out of it.
    ImageDraw.Draw(panel).rounded_rectangle(
        [100, 90, W - 100, y + 40], radius=24, fill=(0, 0, 0, 170)
    )
    Image.alpha_composite(panel, text).save(path)


def phone_frame(path: Path, screen_w: int, screen_h: int) -> None:
    """A plain phone outline, transparent where the screen shows through. No hands, no person."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    x0, y0 = (W - screen_w) // 2, (H - screen_h) // 2
    side, top = 20, 48
    draw.rounded_rectangle(
        [x0 - side, y0 - top, x0 + screen_w + side, y0 + screen_h + top],
        radius=58,
        fill=(14, 17, 19, 255),
        outline=(120, 126, 130, 255),
        width=3,
    )
    draw.rounded_rectangle([x0, y0, x0 + screen_w, y0 + screen_h], radius=26, fill=(0, 0, 0, 0))
    draw.rounded_rectangle(
        [W // 2 - 50, y0 - 30, W // 2 + 50, y0 - 18], radius=6, fill=(40, 44, 48, 255)
    )
    img.save(path)


def ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return float(out.strip() or 0)


FIT = (
    f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
    f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={BACKDROP},fps={FPS},format=yuv420p"
)
ENCODE = ("-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p")
PHONE_SCREEN = (352, 762)  # a 390 by 844 phone recording, scaled to fit inside the outline


def converted_clip(name: str) -> Path | None:
    """The recorded clip as a 30 fps mp4 in docs/video/clips/, made from the raw webm."""
    mp4 = CLIPS / f"{name}.mp4"
    raw = RAW / f"{name}.webm"
    if raw.exists() and (not mp4.exists() or raw.stat().st_mtime > mp4.stat().st_mtime):
        ff("-i", str(raw), "-an", "-vf", FIT, "-c:v", "libx264", "-crf", "23", str(mp4))
    return mp4 if mp4.exists() else None


def piece_video(
    work: Path,
    name: str,
    piece: Piece,
    screen: Path | None,
    footage: Path,
    over: Path | None,
) -> tuple[Path, str | None]:
    """One piece as a silent mp4 of exactly its length, and what was missing, if anything."""
    out = work / f"{name}.mp4"
    frames = str(round(piece.seconds * FPS))
    if piece.clip in (SCREEN, PHONE) and screen is None:
        missing: str | None = "the screen recording for this beat"
    elif piece.clip not in (SCREEN, PHONE) and not (footage / f"{piece.clip}.mp4").exists():
        missing = f"footage clip {piece.clip}"
    else:
        missing = None
    if missing:
        grey = work / f"{name}.png"
        card(grey, f"Missing: {missing}", piece.shows.replace("`", ""), GREY)
        inputs = ["-loop", "1", "-i", str(grey)]
        graph = f"[0:v]{FIT}[p]"
    elif piece.clip == SCREEN:
        assert screen is not None
        start = piece.start % max(0.1, duration(screen))
        inputs = ["-stream_loop", "-1", "-ss", f"{start:.2f}", "-i", str(screen)]
        graph = f"[0:v]{FIT}[p]"
    elif piece.clip == PHONE:
        assert screen is not None
        start = piece.start % max(0.1, duration(screen))
        frame = work / "phone.png"
        if not frame.exists():
            phone_frame(frame, *PHONE_SCREEN)
        sw, sh = PHONE_SCREEN
        inputs = ["-stream_loop", "-1", "-ss", f"{start:.2f}", "-i", str(screen), "-i", str(frame)]
        # The converted recording is the phone page padded to 16:9; cut the page back out.
        graph = (
            f"color=c={BACKDROP}:s={W}x{H}:r={FPS}[bg];"
            f"[0:v]crop=trunc(ih*390/844/2)*2:ih,scale={sw}:{sh},setsar=1[s];"
            "[bg][s]overlay=(W-w)/2:(H-h)/2[a];[a][1:v]overlay=0:0[p]"
        )
    else:
        src = footage / f"{piece.clip}.mp4"
        room = max(0.1, duration(src) - piece.start)
        slow = max(1.0, piece.seconds / room)  # a part longer than its clip plays slower
        inputs = ["-ss", f"{piece.start:.2f}", "-i", str(src)]
        graph = (
            f"[0:v]setpts=PTS*{slow:.4f},fps={FPS},scale={W}:{H},setsar=1,"
            "tpad=stop_mode=clone:stop_duration=1[p]"
        )
    if over:
        k = inputs.count("-i")
        inputs += ["-i", str(over)]
        graph += f";[p][{k}:v]overlay=0:0,format=yuv420p,setsar=1[v]"
    else:
        graph += ";[p]format=yuv420p,setsar=1[v]"
    ff(*inputs, "-filter_complex", graph, "-map", "[v]", "-an",
       "-frames:v", frames, "-r", str(FPS), *ENCODE, str(out))  # fmt: skip
    return out, missing


def title_segment(work: Path, index: int, still: Path) -> Path:
    out = work / f"seg{index:03d}.mp4"
    ff("-loop", "1", "-i", str(still), "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
       "-filter_complex", f"[0:v]{FIT}[v]", "-map", "[v]", "-map", "1:a", "-t", f"{TITLE_S:.2f}",
       "-r", str(FPS), *ENCODE[:6], "-crf", "26", "-c:a", "aac", "-ac", "1", str(out))  # fmt: skip
    return out


def beat_segment(
    work: Path,
    index: int,
    pieces: list[Path],
    seconds: float,
    voice: Path,
    delay: float,
    over: Path,
) -> Path:
    """The pieces one after another, the caption on top and the voice, which may wait."""
    out = work / f"seg{index:03d}.mp4"
    n = len(pieces)
    inputs = [a for p in pieces for a in ("-i", str(p))]
    chain = "".join(f"[{i}:v]" for i in range(n))
    ms = int(round(delay * 1000))
    # The caption comes in with the words, not over a lead-in that has none.
    graph = (
        f"{chain}concat=n={n}:v=1:a=0[b];"
        f"[b][{n}:v]overlay=0:0:enable='gte(t,{delay:.2f})',format=yuv420p[v];"
        f"[{n + 1}:a]adelay=delays={ms}:all=1,apad,aresample=44100[a]"
    )
    ff(*inputs, "-loop", "1", "-i", str(over), "-i", str(voice), "-filter_complex", graph,
       "-map", "[v]", "-map", "[a]", "-t", f"{seconds:.2f}", "-r", str(FPS),
       "-c:v", "libx264", "-crf", "26", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ac", "1",
       str(out))  # fmt: skip
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--footage", type=Path, default=FOOTAGE, help="the cut footage clips")
    args = parser.parse_args(argv)
    footage = args.footage.expanduser()
    if not shutil.which("ffmpeg") or not shutil.which("say"):
        print("video-rough: needs ffmpeg and macOS say")
        return 1
    text = SHOTLIST.read_text(encoding="utf-8")
    beats = rows(text)
    if not beats:
        print("video-rough: no rows in docs/video/SHOTLIST.md")
        return 1
    table = footage_parts(text)
    unknown = sorted(set(table) - {b["time"] for b in beats})
    if unknown:
        print(f"video-rough: the footage table names beats the shot list has not: {unknown}")
        return 1
    CLIPS.mkdir(parents=True, exist_ok=True)
    segments: list[Path] = []
    waiting: list[dict[str, str]] = []
    recorded: list[str] = []
    played: list[dict[str, object]] = []
    used_clips: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="second-look-rough-") as tmp:
        work = Path(tmp)
        for i, b in enumerate(beats):
            title = work / f"title{i:03d}.png"
            card(title, f"{b['time']}  {b['clip']}", b["screen"], (24, 60, 72))
            segments.append(title_segment(work, 2 * i, title))

            voice = work / f"voice{i:03d}.aiff"
            # A stage direction in brackets, such as "(five seconds of quiet)", is not spoken.
            spoken = re.sub(r"\([^)]*\)", " ", b["says"]).replace('"', "")
            subprocess.run(["say", "-v", VOICE, "-o", str(voice), spoken], check=True)
            if duration(voice) < 0.5:
                print(f"video-rough: say gave a silent voice for {b['time']}; try another voice")
                return 1
            parts = table.get(b["time"]) or [Part(b["time"], 1, SCREEN, 0.0, None, False, "")]
            length, delay, pieces = plan(parts, float(b["seconds"]), duration(voice))
            uses_screen = any(p.clip in (SCREEN, PHONE) for p in pieces)
            screen = converted_clip(b["clip"]) if uses_screen else None
            if screen is not None:
                recorded.append(b["clip"])
            files = []
            last_beat = i == len(beats) - 1
            for j, piece in enumerate(pieces):
                over = None
                if last_beat and j == len(pieces) - 1:
                    over = work / "end_card.png"
                    end_card(over)
                path, missing = piece_video(work, f"p{i:03d}_{j}", piece, screen, footage, over)
                files.append(path)
                if missing:
                    waiting.append({"time": b["time"], "missing": missing})
            used_clips.update(p.clip for p in pieces if p.clip not in (SCREEN, PHONE))
            played.append(
                {
                    "time": b["time"],
                    "seconds": round(length, 2),
                    "voice_waits_s": round(delay, 2),
                    "parts": [
                        {
                            "clip": p.clip,
                            "from_s": round(p.start, 2),
                            "seconds": round(p.seconds, 2),
                        }
                        for p in pieces
                    ],
                }
            )
            over = work / f"cap{i:03d}.png"
            caption(over, b["says"])
            segments.append(beat_segment(work, 2 * i + 1, files, length, voice, delay, over))
        listing = work / "list.txt"
        listing.write_text("".join(f"file '{s}'\n" for s in segments), encoding="utf-8")
        ff("-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(OUT))
    total = duration(OUT)
    used = sorted(used_clips)
    summary = {
        "file": str(OUT.relative_to(ROOT)),
        "committed": False,
        "voice": f"scratch, macOS say ({VOICE}); Alex replaces it with his own voice",
        "video_licence": VIDEO_LICENCE,
        "length_s": round(total, 1),
        "length_without_title_cards_s": round(total - TITLE_S * len(beats), 1),
        "bytes": OUT.stat().st_size,
        "beats": len(beats),
        "recorded": recorded,
        "footage_clips_used": used,
        "footage_folder": str(footage).replace(str(Path.home()), "~", 1),
        "played": played,
        "waiting_for_footage_or_recording": waiting,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    minutes, secs = divmod(int(round(total)), 60)
    print(
        f"video-rough: {OUT.relative_to(ROOT)}, {minutes}:{secs:02d} with title cards "
        f"({total:.1f} s), {OUT.stat().st_size / 1e6:.1f} MB, {len(used)} footage clips, "
        f"{len(recorded)} screen recordings, {len(waiting)} missing"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
