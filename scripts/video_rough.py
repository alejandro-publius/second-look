"""The rough cut, as far as software can take it (Update 14 section 7 item 3).

Reads the table in docs/video/SHOTLIST.md and builds one 1920 by 1080, 30 fps video:

- a 3 second title card before each beat, with its start time and what is on screen;
- the beat's own clip when it has been recorded (apps/web/scripts/record-clips.mjs writes the raw
  webm; this script converts it), otherwise a grey card saying what goes there, which is always
  the case for creek footage and a person on camera;
- the line Alex says, burned in as a caption;
- a SCRATCH voice from macOS `say`, only so the timing can be checked. The file name says scratch.
  Alex replaces it with his own voice.

ffmpeg on this Mac has no drawtext filter, so the cards and captions are drawn with Pillow and laid
over the clip. Nothing here is committed: the clips and the cut are video files. The summary,
docs/video/rough_cut.json, is, with the length and the beats still waiting for footage.

Run: make video-rough
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SHOTLIST = ROOT / "docs" / "video" / "SHOTLIST.md"
CLIPS = ROOT / "docs" / "video" / "clips"
RAW = CLIPS / "raw"
OUT = ROOT / "docs" / "video" / "rough_cut_scratch_voice.mp4"
SUMMARY = ROOT / "docs" / "video" / "rough_cut.json"
W, H, FPS = 1920, 1080, 30
TITLE_S = 3.0
FONT = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
GREY = (92, 96, 100)
INK = (255, 255, 255)


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
    """A transparent frame with the line in a dark band at the bottom."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    lines = wrap(draw, text, font(44), W - 300)[:3]
    band = 40 + 58 * len(lines)
    draw.rectangle([0, H - band - 40, W, H], fill=(0, 0, 0, 170))
    y = H - band - 10
    for line in lines:
        x = (W - draw.textlength(line, font=font(44))) / 2
        draw.text((x, y), line, font=font(44), fill=INK)
        y += 58
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
    f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x2b2f33,fps={FPS},format=yuv420p"
)


def converted_clip(name: str) -> Path | None:
    """The recorded clip as a 30 fps mp4 in docs/video/clips/, made from the raw webm."""
    mp4 = CLIPS / f"{name}.mp4"
    raw = RAW / f"{name}.webm"
    if raw.exists() and (not mp4.exists() or raw.stat().st_mtime > mp4.stat().st_mtime):
        ff("-i", str(raw), "-an", "-vf", FIT, "-c:v", "libx264", "-crf", "23", str(mp4))
    return mp4 if mp4.exists() else None


def segment(
    work: Path, index: int, still_or_clip: Path, seconds: float, voice: Path | None, over: Path
) -> Path:
    out = work / f"seg{index:03d}.mp4"
    is_clip = still_or_clip.suffix == ".mp4"
    video_in = (
        ["-stream_loop", "-1", "-i", str(still_or_clip)]
        if is_clip
        else ["-loop", "1", "-i", str(still_or_clip)]
    )
    audio_in = ["-i", str(voice)] if voice else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono"]
    ff(
        *video_in,
        "-loop",
        "1",
        "-i",
        str(over),
        *audio_in,
        "-filter_complex",
        f"[0:v]{FIT}[b];[b][1:v]overlay=0:0,format=yuv420p[v];[2:a]apad,aresample=44100[a]",
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-t",
        f"{seconds:.2f}",
        "-r",
        str(FPS),
        "-c:v",
        "libx264",
        "-crf",
        "26",
        "-c:a",
        "aac",
        "-ac",
        "1",
        str(out),
    )
    return out


def main() -> int:
    if not shutil.which("ffmpeg") or not shutil.which("say"):
        print("video-rough: needs ffmpeg and macOS say")
        return 1
    beats = rows(SHOTLIST.read_text(encoding="utf-8"))
    if not beats:
        print("video-rough: no rows in docs/video/SHOTLIST.md")
        return 1
    CLIPS.mkdir(parents=True, exist_ok=True)
    segments: list[Path] = []
    waiting: list[dict[str, str]] = []
    recorded: list[str] = []
    with tempfile.TemporaryDirectory(prefix="second-look-rough-") as tmp:
        work = Path(tmp)
        blank = work / "blank.png"
        Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(blank)
        for i, b in enumerate(beats):
            title = work / f"title{i:03d}.png"
            card(title, f"{b['time']}  {b['clip']}", b["screen"], (24, 60, 72))
            segments.append(segment(work, 2 * i, title, TITLE_S, None, blank))

            voice = work / f"voice{i:03d}.aiff"
            # A stage direction in brackets, such as "(five seconds of quiet)", is not spoken.
            spoken = re.sub(r"\([^)]*\)", " ", b["says"]).replace('"', "")
            subprocess.run(["say", "-o", str(voice), spoken], check=True)
            seconds = max(float(b["seconds"]), duration(voice) + 0.4)
            clip = None if b["needs"] != "screen recording" else converted_clip(b["clip"])
            if clip is None:
                grey = work / f"grey{i:03d}.png"
                what = {
                    "creek footage": "Creek footage goes here",
                    "person on camera": "A person on camera goes here",
                }.get(b["needs"], "Screen recording not made yet")
                card(grey, what, b["screen"], GREY)
                visual = grey
                waiting.append({"time": b["time"], "clip": b["clip"], "needs": b["needs"]})
            else:
                visual = clip
                recorded.append(b["clip"])
            over = work / f"cap{i:03d}.png"
            caption(over, b["says"])
            segments.append(segment(work, 2 * i + 1, visual, seconds, voice, over))
        listing = work / "list.txt"
        listing.write_text("".join(f"file '{s}'\n" for s in segments), encoding="utf-8")
        ff("-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(OUT))
    total = duration(OUT)
    summary = {
        "file": str(OUT.relative_to(ROOT)),
        "committed": False,
        "voice": "scratch, macOS say; Alex replaces it with his own voice",
        "length_s": round(total, 1),
        "length_without_title_cards_s": round(total - TITLE_S * len(beats), 1),
        "beats": len(beats),
        "recorded": recorded,
        "waiting_for_footage_or_recording": waiting,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    minutes, secs = divmod(int(round(total)), 60)
    print(
        f"video-rough: {OUT.relative_to(ROOT)}, {minutes}:{secs:02d} with title cards, "
        f"{len(recorded)} beats recorded, {len(waiting)} waiting"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
