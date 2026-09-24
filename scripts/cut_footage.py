"""Cut the open footage into the clips the video uses (UPDATE_22 section 6 item 3).

Reads docs/video/footage_fetched.json (written by scripts/fetch_footage.py) and the files it
downloaded to ~/second-look-media/. Every item still kept becomes one clip in
~/second-look-media/clips/, named after its beat and its title, for example
`gauge-strawberrycreek9.mp4`:

- 1920 by 1080, H.264 (libx264, yuv420p), 30 frames a second, no audio stream;
- a video gives one stretch of 6 to 10 seconds, the steadiest one: the first second is skipped,
  frame to frame change is measured as the mean absolute difference of small grey frames taken
  10 times a second, and the window with the lowest total change wins;
- a photo gives 6 seconds with a slow push-in, from the whole 16:9 frame to 8 percent closer,
  drawn by Pillow with a sub-pixel crop box so the picture never jumps a pixel;
- both are scaled to cover 16:9 and cropped in the centre, never stretched and never padded;
- a small credit line sits in the lower left corner: title, author, licence, Wikimedia Commons.

Every clip is checked with ffprobe (size, codec, pixel format, duration, no audio) and the check is
written back into docs/video/footage_fetched.json. Media stays outside the repository.

ffmpeg on this Mac has no drawtext filter, so the credit is drawn with Pillow in the self hosted
Atkinson Hyperlegible Next (from apps/web/node_modules), or Arial if that is not installed.

Run: uv run python scripts/cut_footage.py
     uv run python scripts/cut_footage.py --media ~/second-look-media --clips /another/folder
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from scripts.fetch_footage import FETCHED, MEDIA, ROOT

W, H, FPS = 1920, 1080, 30
SKIP_S = 1.0
MIN_S, MAX_S = 6.0, 10.0
PHOTO_S = 6.0
PUSH_IN = 1.08
SAMPLE_FPS = 10
SAMPLE_W, SAMPLE_H = 160, 90
BLANK_STD = 12.0  # the same line scripts/make_frames.py draws for a blank frame
CRF = "20"
FIT = "scale to cover 16:9, then crop the centre; never stretched, never padded"
FONTS = (
    ROOT
    / "apps/web/node_modules/@fontsource-variable/atkinson-hyperlegible-next/files"
    / "atkinson-hyperlegible-next-latin-wght-normal.woff2",
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
)
CREDIT_SIZE = 28
CREDIT_MARGIN = 28


class CutError(Exception):
    """A clip that could not be made to the rules. Nothing is written for it."""


# ---- pure parts -------------------------------------------------------------------------------


def clip_name(beat: str, title: str) -> str:
    """A stable file name with the beat first: `pipes-florhamparksewerageutilityoutfall.mp4`."""
    stem = re.sub(r"\.[A-Za-z0-9]{2,4}$", "", title).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    if len(slug) > 48:
        slug = slug[:49].rsplit("-", 1)[0]
    return f"{beat}-{slug}.mp4"


def credit_text(title: str, author: str, licence: str) -> str:
    stem = re.sub(r"\.[A-Za-z0-9]{2,4}$", "", title)
    return f'"{stem}" by {author}, {licence}, Wikimedia Commons'


def window_seconds(duration_s: float, skip_s: float = SKIP_S) -> float:
    """How long the clip is: as long as the video allows after the first second, 6 to 10 s."""
    room = math.floor((duration_s - skip_s - 0.2) * 10) / 10
    if room < MIN_S:
        raise CutError(f"only {room:.1f} s after the first second; a clip needs {MIN_S:.0f}")
    return min(MAX_S, room)


def frame_changes(frames: np.ndarray) -> np.ndarray:
    """Mean absolute difference between each frame and the next, for grey frames (n, h, w)."""
    if len(frames) < 2:
        return np.zeros(0)
    f = frames.astype(np.int16)
    return np.abs(np.diff(f, axis=0)).mean(axis=(1, 2)).astype(float)


def usable_samples(frames: np.ndarray, blank_std: float = BLANK_STD) -> np.ndarray:
    """True for a sample worth showing. A black or near uniform frame (a fade, a title
    background) barely changes from one frame to the next, so without this it would win."""
    if len(frames) == 0:
        return np.zeros(0, dtype=bool)
    std: np.ndarray = frames.reshape(len(frames), -1).astype(np.float32).std(axis=1)
    return std >= blank_std


def steadiest_window(
    changes: Sequence[float] | np.ndarray,
    rate: float,
    seconds: float,
    skip_s: float = SKIP_S,
    usable: Sequence[bool] | np.ndarray | None = None,
) -> float:
    """The start, in seconds, of the stretch with the lowest total change.

    changes[i] is the change from sample i to sample i + 1, with `rate` samples a second. A window
    of `seconds` holds round(seconds * rate) changes. It never starts inside the first `skip_s`
    seconds, never runs past the end, and never holds a sample that `usable` marks False (one
    flag per sample, so one more than there are changes). On a tie the earlier window wins.
    """
    n = round(seconds * rate)
    first = math.ceil(skip_s * rate)
    last = len(changes) - n
    if n <= 0 or last < first:
        raise CutError(f"{len(changes) / rate:.1f} s of video has no {seconds:.1f} s window")
    total = np.concatenate([[0.0], np.cumsum(np.asarray(changes, dtype=float))])
    sums = total[first + n : last + n + 1] - total[first : last + 1]
    if usable is not None:
        bad = np.concatenate([[0], np.cumsum(~np.asarray(usable, dtype=bool))])
        # Samples start .. start + n inclusive must all be usable.
        blank = bad[first + n + 1 : last + n + 2] - bad[first : last + 1]
        if len(blank) != len(sums):
            raise CutError("usable needs one flag per sample, one more than the changes")
        if not np.any(blank == 0):
            raise CutError(f"no {seconds:.1f} s window without a blank frame")
        sums = np.where(blank == 0, sums, np.inf)
    return (first + int(np.argmin(sums))) / rate


def cover_box(src_w: int, src_h: int) -> tuple[float, float, float, float]:
    """The largest 16:9 box in the middle of the source: the crop that fills the frame."""
    if src_w * H >= src_h * W:
        bw, bh = src_h * W / H, float(src_h)
    else:
        bw, bh = float(src_w), src_w * H / W
    x, y = (src_w - bw) / 2, (src_h - bh) / 2
    return (x, y, x + bw, y + bh)


def push_in_boxes(
    src_w: int, src_h: int, frames: int, end_zoom: float = PUSH_IN
) -> list[tuple[float, float, float, float]]:
    """One crop box per frame, from the whole 16:9 frame to `end_zoom` times closer.

    The zoom grows by the same ratio every frame (end_zoom ** t), so the push-in looks even from
    start to end. The boxes are floats: Pillow resamples them, so there is no whole-pixel jump.
    """
    x0, y0, x1, y1 = cover_box(src_w, src_h)
    cx, cy, bw, bh = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
    boxes = []
    for i in range(frames):
        z = end_zoom ** (i / max(1, frames - 1))
        w, h = bw / z, bh / z
        boxes.append((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
    return boxes


def probe_problems(probe: dict[str, Any], seconds: float) -> list[str]:
    """What is wrong with a clip, from ffprobe's JSON. An empty list means it keeps the rules."""
    streams = probe.get("streams") or []
    video = [s for s in streams if s.get("codec_type") == "video"]
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    problems = []
    if len(video) != 1:
        return [f"{len(video)} video streams"]
    v = video[0]
    if (v.get("width"), v.get("height")) != (W, H):
        problems.append(f"size {v.get('width')}x{v.get('height')}")
    if v.get("codec_name") != "h264":
        problems.append(f"codec {v.get('codec_name')}")
    if v.get("pix_fmt") != "yuv420p":
        problems.append(f"pixel format {v.get('pix_fmt')}")
    if audio:
        problems.append(f"{len(audio)} audio streams")
    duration = float((probe.get("format") or {}).get("duration") or 0)
    if not (MIN_S - 0.05 <= duration <= MAX_S + 0.05):
        problems.append(f"duration {duration:.2f} s is outside {MIN_S:.0f} to {MAX_S:.0f}")
    elif abs(duration - seconds) > 0.1:
        problems.append(f"duration {duration:.2f} s, asked for {seconds:.2f}")
    return problems


# ---- ffmpeg and Pillow ------------------------------------------------------------------------


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONTS:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def credit_overlay(text: str) -> Image.Image:
    """A transparent frame with the credit in the lower left corner, on a soft dark box."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    f = font(CREDIT_SIZE)
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=f) <= W * 0.6:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    line_h = CREDIT_SIZE + 8
    width = max(draw.textlength(line, font=f) for line in lines)
    top = H - CREDIT_MARGIN - line_h * len(lines)
    draw.rectangle(
        [CREDIT_MARGIN - 12, top - 8, CREDIT_MARGIN + width + 12, H - CREDIT_MARGIN + 4],
        fill=(0, 0, 0, 130),
    )
    for i, line in enumerate(lines):
        draw.text((CREDIT_MARGIN, top + i * line_h), line, font=f, fill=(255, 255, 255, 235))
    return img


def ffprobe(path: Path) -> dict[str, Any]:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    result: dict[str, Any] = json.loads(out)
    return result


def grey_frames(path: Path) -> np.ndarray:
    raw = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-an",
            "-vf",
            f"fps={SAMPLE_FPS},scale={SAMPLE_W}:{SAMPLE_H}:flags=area,format=gray",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "-",
        ],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(-1, SAMPLE_H, SAMPLE_W)


def cut_video(src: Path, out: Path, credit: Path) -> dict[str, Any]:
    duration = float(ffprobe(src)["format"]["duration"])
    seconds = window_seconds(duration)
    grey = grey_frames(src)
    changes = frame_changes(grey)
    usable = usable_samples(grey)
    start = steadiest_window(changes, SAMPLE_FPS, seconds, usable=usable)
    n = round(seconds * SAMPLE_FPS)
    first = round(start * SAMPLE_FPS)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            f"{start:.2f}",
            "-i",
            str(src),
            "-i",
            str(credit),
            "-filter_complex",
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={W}:{H},setsar=1,fps={FPS}[b];[b][1:v]overlay=0:0,format=yuv420p[v]",
            "-map",
            "[v]",
            "-an",
            "-t",
            f"{seconds:.2f}",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            CRF,
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(out),
        ],
        check=True,
    )
    return {
        "seconds": seconds,
        "start_s": start,
        "source_duration_s": round(duration, 2),
        "window_change": round(float(np.sum(changes[first : first + n])), 2),
        "mean_change_whole_video": round(float(np.mean(changes)), 3) if len(changes) else 0.0,
        "mean_change_in_window": round(float(np.mean(changes[first : first + n])), 3),
        "blank_seconds_skipped": round(float(np.sum(~usable)) / SAMPLE_FPS, 1),
    }


def cut_photo(src: Path, out: Path, credit_img: Image.Image) -> dict[str, Any]:
    frames = round(PHOTO_S * FPS)
    with Image.open(src) as opened:
        # The camera's own rotation tag decides which way is up, as on the Commons page.
        img = ImageOps.exif_transpose(opened).convert("RGB")
    # Bring the source down once to 1.5 times the frame, which still leaves room for the zoom.
    x0, y0, x1, y1 = cover_box(*img.size)
    scale = min(1.0, 1.5 * W / (x1 - x0))
    if scale < 1.0:
        img = img.resize(
            (round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS
        )
    boxes = push_in_boxes(img.width, img.height, frames)
    proc = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{W}x{H}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            CRF,
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(out),
        ],
        stdin=subprocess.PIPE,
    )
    assert proc.stdin is not None
    try:
        for box in boxes:
            frame = img.resize((W, H), Image.Resampling.BICUBIC, box=box).convert("RGBA")
            frame.alpha_composite(credit_img)
            proc.stdin.write(frame.convert("RGB").tobytes())
    finally:
        proc.stdin.close()
        if proc.wait() != 0:
            raise CutError(f"ffmpeg failed on {src.name}")
    return {"seconds": PHOTO_S, "push_in": f"1.00 to {PUSH_IN:.2f}, even ratio per frame"}


def screen_people(clip: Path, work: Path) -> dict[str, Any]:
    """Hard rule 6, no faces: Apple Vision looks at two frames a second, on this Mac only.

    A face is a problem. A person seen from behind, with no face, is written down, not refused.
    Off macOS, or without pyobjc-framework-Vision, the screen says it did not run.
    """
    try:
        import Vision
        from Foundation import NSURL
    except ImportError:
        return {"ran": False, "why": "Apple Vision is not importable here"}
    folder = work / f"{clip.stem}-frames"
    folder.mkdir(exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-vf", "fps=2", str(folder / "%03d.png")],
        check=True,
    )
    faces_at, people_at = [], []
    frames = sorted(folder.glob("*.png"))
    for i, frame in enumerate(frames):
        handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(
            NSURL.fileURLWithPath_(str(frame)), None
        )
        faces = Vision.VNDetectFaceRectanglesRequest.alloc().init()
        humans = Vision.VNDetectHumanRectanglesRequest.alloc().init()
        humans.setUpperBodyOnly_(False)
        ok, _error = handler.performRequests_error_([faces, humans], None)
        if not ok:
            raise CutError(f"Vision could not read {frame.name}")
        if faces.results():
            faces_at.append(i / 2)
        if any(o.confidence() >= 0.3 for o in (humans.results() or [])):
            people_at.append(i / 2)
    shutil.rmtree(folder, ignore_errors=True)
    return {"ran": True, "frames": len(frames), "faces_at_s": faces_at, "people_at_s": people_at}


def cut_item(item: dict[str, Any], media: Path, clips: Path, work: Path) -> dict[str, Any]:
    src = media / item["file"]
    name = clip_name(item["beat"], item["title"])
    out = clips / name
    text = credit_text(item["title"], item["author"], item["licence_csv"])
    overlay = credit_overlay(text)
    entry: dict[str, Any] = {
        "title": item["title"],
        "beat": item["beat"],
        "kind": item["kind"],
        "clip": name,
        "credit": text,
        "fit": FIT,
        "source_sha1": item["sha1"],
    }
    if item["kind"] == "video":
        png = work / f"{name}.png"
        overlay.save(png)
        entry.update(cut_video(src, out, png))
    else:
        entry.update(cut_photo(src, out, overlay))
    probe = ffprobe(out)
    v = next(s for s in probe["streams"] if s.get("codec_type") == "video")
    entry["probe"] = {
        "width": v.get("width"),
        "height": v.get("height"),
        "codec": v.get("codec_name"),
        "pix_fmt": v.get("pix_fmt"),
        "duration_s": round(float(probe["format"]["duration"]), 3),
        "audio_streams": sum(1 for s in probe["streams"] if s.get("codec_type") == "audio"),
        "bytes": out.stat().st_size,
    }
    entry["problems"] = probe_problems(probe, entry["seconds"])
    entry["people_screen"] = screen_people(out, work)
    if entry["people_screen"].get("faces_at_s"):
        entry["problems"].append(f"a face at {entry['people_screen']['faces_at_s']} s")
    entry["ok"] = not entry["problems"]
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--media", type=Path, default=MEDIA)
    parser.add_argument("--clips", type=Path, default=None, help="default: MEDIA/clips")
    parser.add_argument("--manifest", type=Path, default=FETCHED)
    args = parser.parse_args(argv)
    media = args.media.expanduser()
    clips = (args.clips or media / "clips").expanduser()
    # Where the clips go is checked first: refusing the repository needs no ffmpeg, and CI has none.
    if clips.resolve().is_relative_to(ROOT.resolve()):
        print(f"cut-footage: {clips} is inside the repository; clips must stay outside it")
        return 1
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("cut-footage: needs ffmpeg and ffprobe")
        return 1
    clips.mkdir(parents=True, exist_ok=True)
    fetched = json.loads(args.manifest.read_text(encoding="utf-8"))
    done = []
    work = clips / ".work"
    work.mkdir(exist_ok=True)
    try:
        for item in fetched["items"]:
            if not item.get("kept"):
                why = item.get("reason")
                print(f"cut-footage: skipped {item['title']}, dropped at fetch: {why}")
                continue
            entry = cut_item(item, media, clips, work)
            done.append(entry)
            state = "ok" if entry["ok"] else "PROBLEM " + "; ".join(entry["problems"])
            print(f"cut-footage: {entry['clip']}, {entry['probe']['duration_s']:.2f} s, {state}")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    fetched["clips"] = done
    fetched["clips_folder"] = str(clips).replace(str(Path.home()), "~", 1)
    args.manifest.write_text(
        json.dumps(fetched, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    bad = [e for e in done if not e["ok"]]
    print(f"cut-footage: {len(done) - len(bad)} of {len(done)} clips keep the rules")
    return 1 if bad or not done else 0


if __name__ == "__main__":
    sys.exit(main())
