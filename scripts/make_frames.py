"""Frames out of open creek footage, for the benchmark pool (Update 14 section 3 item 4).

In: videos/manifest.csv, the twelve videos we picked, and a cache of the video files somewhere
outside this repo (default ~/second-look-cache/videos). A video file is never committed.

Out: photos/benchmark/<video id>-<seconds>.jpg, resized, one manifest row each with role
benchmark, the source video and the timestamp, plus videos/frames.json with what was dropped
and why.

What it does to each video, in order:

1. Samples one frame every --every seconds with ffmpeg.
2. Drops a frame that looks like one we already kept, by a difference hash (dHash) inside
   --hash-distance bits. Neighbouring seconds of a slow pan are the same picture.
3. Drops a frame with a person in it, or with something that reads like a licence plate or a
   house number, using OpenCV's own Haar cascades and a small high contrast rectangle test.
   This is a screen, not a promise: it keeps at most a frame that nobody has looked at yet, so
   the people frames never reach the pool by accident. Anything it is unsure about is dropped.
4. Keeps at most --per-video frames, spread across the video rather than bunched at the front.

Run: uv run python scripts/make_frames.py            do it
     uv run python scripts/make_frames.py --dry-run  say what it would do and write nothing

Nothing here labels a frame. A frame's label comes from the video's own description, through
videos/manifest.csv, and a video whose description supports no label gives unlabelled frames
that are only ever used for agreement between models. docs/REAL_VS_SYNTHETIC.md says so.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
VIDEOS = ROOT / "videos"
MANIFEST = VIDEOS / "manifest.csv"
PHOTO_MANIFEST = ROOT / "photos" / "manifest.csv"
FRAMES_DIR = ROOT / "photos" / "benchmark"
DEFAULT_CACHE = Path.home() / "second-look-cache" / "videos"
LONG_SIDE = 1280
JPEG_QUALITY = 82
HASH_SIZE = 8

PHOTO_COLUMNS = [
    "id",
    "file",
    "sha256",
    "source_url",
    "author",
    "license",
    "capture_date",
    "coarse_location",
    "scene_id",
    "role",
    "feature",
    "gold_label",
    "labeller_2",
    "synthetic",
    "faces",
    "notes",
    "label_evidence",
]


class FrameError(Exception):
    """Refused. Nothing was written."""


@dataclass
class Video:
    id: str
    title: str
    author: str
    license: str
    source_url: str
    country: str
    duration_s: float
    cache_file: str
    label_feature: str
    label_value: str
    label_evidence: str
    notes: str


@dataclass
class Dropped:
    reason: str
    at_s: float


@dataclass
class VideoResult:
    video_id: str
    sampled: int = 0
    kept: list[float] = field(default_factory=list)
    dropped: list[Dropped] = field(default_factory=list)


def read_videos(path: Path) -> list[Video]:
    if not path.exists():
        raise FrameError(f"{path} is missing; pick the videos first")
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    videos: list[Video] = []
    for row in rows:
        videos.append(
            Video(
                id=row["id"].strip(),
                title=row["title"].strip(),
                author=row["author"].strip(),
                license=row["license"].strip(),
                source_url=row["source_url"].strip(),
                country=row.get("country", "").strip(),
                duration_s=float(row.get("duration_s") or 0),
                cache_file=row.get("cache_file", "").strip(),
                label_feature=row.get("label_feature", "").strip(),
                label_value=row.get("label_value", "").strip(),
                label_evidence=row.get("label_evidence", "").strip(),
                notes=row.get("notes", "").strip(),
            )
        )
    return videos


def dhash(image: Image.Image, size: int = HASH_SIZE) -> int:
    """A difference hash. Two pictures of the same thing land within a few bits of each other."""
    small = image.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    pixels = np.asarray(small, dtype=np.int16)
    bits = pixels[:, 1:] > pixels[:, :-1]
    out = 0
    for bit in bits.flatten():
        out = (out << 1) | int(bit)
    return out


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def sample_times(duration_s: float, every_s: float) -> list[float]:
    """Times to grab, skipping the first and last seconds, which are often titles or fades."""
    start = min(3.0, max(0.0, duration_s * 0.02))
    end = max(start, duration_s - 3.0)
    times: list[float] = []
    t = start
    while t <= end:
        times.append(round(t, 2))
        t += every_s
    return times


def grab_frame(video: Path, at_s: float, into: Path) -> Path | None:
    """One frame at one time, through ffmpeg. Returns the file, or None if ffmpeg found none."""
    out = into / f"f{int(at_s * 100):09d}.jpg"
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-loglevel",
        "error",
        "-ss",
        f"{at_s:.2f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        "-y",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        return None
    return out


class PeopleAndPlates:
    """A local screen for people, licence plates and house numbers. It errs on the side of no.

    OpenCV ships Haar cascades for faces, upper bodies and whole bodies. They miss things, so
    the plate and number test is a second, cruder pass: a small bright rectangle with a lot of
    dark edges inside it is the shape a plate or a door number makes, and a frame with one is
    dropped whether or not it really is one. We would rather lose a good frame than show a
    stranger's car.
    """

    def __init__(self) -> None:
        import cv2

        self.cv2 = cv2
        base = Path(cv2.data.haarcascades)  # type: ignore[attr-defined]
        names = [
            "haarcascade_frontalface_default.xml",
            "haarcascade_profileface.xml",
            "haarcascade_upperbody.xml",
            "haarcascade_fullbody.xml",
        ]
        self.cascades = []
        for name in names:
            path = base / name
            if not path.exists():
                continue
            cascade = cv2.CascadeClassifier(str(path))  # type: ignore[attr-defined]
            if not cascade.empty():
                self.cascades.append((name, cascade))
        if not self.cascades:
            raise FrameError("OpenCV has no Haar cascades on this machine; cannot screen frames")

    def reason_to_drop(self, path: Path) -> str | None:
        cv2 = self.cv2
        image = cv2.imread(str(path))
        if image is None:
            return "unreadable"
        grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        grey = cv2.equalizeHist(grey)
        for name, cascade in self.cascades:
            found = cascade.detectMultiScale(
                grey, scaleFactor=1.08, minNeighbors=6, minSize=(28, 28)
            )
            if len(found) > 0:
                return f"person: {name.replace('haarcascade_', '').replace('.xml', '')}"
        if self._plate_like(grey):
            return "plate or number: a small bright rectangle with dense dark edges"
        return None

    def _plate_like(self, grey: Any) -> bool:
        cv2 = self.cv2
        height, width = grey.shape[:2]
        area = float(height * width)
        edges = cv2.Canny(grey, 90, 200)
        closed = cv2.morphologyEx(
            edges, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
        )
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if h == 0 or w == 0:
                continue
            ratio = w / float(h)
            share = (w * h) / area
            # A plate is wider than it is tall, small in the frame, and full of dark marks.
            if not (1.8 <= ratio <= 6.5):
                continue
            if not (0.0008 <= share <= 0.03):
                continue
            patch = grey[y : y + h, x : x + w]
            if patch.size == 0:
                continue
            ink = float((patch < 90).mean())
            bright = float((patch > 150).mean())
            if ink > 0.14 and bright > 0.25:
                return True
        return False


def resize_and_save(src: Path, dest: Path) -> tuple[str, int, int]:
    """Resize to LONG_SIDE, strip everything that is not pixels, and hash what we wrote."""
    with Image.open(src) as opened:
        image = opened.convert("RGB")
        width, height = image.size
        scale = LONG_SIDE / float(max(width, height))
        if scale < 1:
            image = image.resize(
                (round(width * scale), round(height * scale)), Image.Resampling.LANCZOS
            )
        clean = Image.new("RGB", image.size)
        clean.putdata(list(image.getdata()))
        dest.parent.mkdir(parents=True, exist_ok=True)
        clean.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True)
        out_w, out_h = clean.size
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    return digest, out_w, out_h


def frame_rows(
    video: Video, kept: list[tuple[float, Path, str]], cache_name: str
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for at_s, path, digest in kept:
        evidence = (
            f"Frame at {at_s:.0f} s of {video.source_url}. {video.label_evidence}"
            if video.label_evidence
            else (
                f"Frame at {at_s:.0f} s of {video.source_url}. The description supports no label "
                "for this feature, so the frame is unlabelled and is used only for agreement "
                "between models."
            )
        )
        rows.append(
            {
                "id": path.stem,
                "file": f"benchmark/{path.name}",
                "sha256": digest,
                "source_url": video.source_url,
                "author": video.author,
                "license": video.license,
                "capture_date": "",
                "coarse_location": video.country,
                "scene_id": f"video-{video.id}",
                "role": "benchmark",
                "feature": video.label_feature,
                "gold_label": video.label_value,
                "labeller_2": "",
                "synthetic": "false",
                "faces": "false",
                "notes": (
                    f'Frame at {at_s:.0f} s of the video "{video.title}" ({cache_name}). '
                    f"{video.notes}"
                ).strip(),
                "label_evidence": evidence.strip(),
            }
        )
    return rows


def process_video(
    video: Video,
    cache: Path,
    every_s: float,
    per_video: int,
    hash_distance: int,
    screen: PeopleAndPlates,
    dry_run: bool,
) -> tuple[VideoResult, list[dict[str, str]]]:
    result = VideoResult(video_id=video.id)
    source = cache / video.cache_file
    if not source.exists():
        raise FrameError(f"{source} is not in the cache; download it before running this")
    kept: list[tuple[float, Path, str]] = []
    hashes: list[int] = []
    with tempfile.TemporaryDirectory(prefix="second-look-frames-") as tmp:
        work = Path(tmp)
        for at_s in sample_times(video.duration_s, every_s):
            grabbed = grab_frame(source, at_s, work)
            result.sampled += 1
            if grabbed is None:
                result.dropped.append(Dropped("ffmpeg found no frame", at_s))
                continue
            with Image.open(grabbed) as image:
                digest_bits = dhash(image)
            if any(hamming(digest_bits, seen) <= hash_distance for seen in hashes):
                result.dropped.append(Dropped("near duplicate of a frame we kept", at_s))
                continue
            reason = screen.reason_to_drop(grabbed)
            if reason is not None:
                result.dropped.append(Dropped(reason, at_s))
                continue
            hashes.append(digest_bits)
            dest = FRAMES_DIR / f"{video.id}-{int(at_s):05d}.jpg"
            if dry_run:
                kept.append((at_s, dest, ""))
            else:
                digest, _, _ = resize_and_save(grabbed, dest)
                kept.append((at_s, dest, digest))
            result.kept.append(at_s)
    if len(kept) > per_video:
        # Spread the keepers across the video instead of taking the first ones.
        step = len(kept) / float(per_video)
        chosen_index = {int(i * step) for i in range(per_video)}
        for index, (_at_s, dest, _) in enumerate(kept):
            if index not in chosen_index and not dry_run and dest.exists():
                dest.unlink()
        kept = [item for index, item in enumerate(kept) if index in chosen_index]
        result.kept = [at_s for at_s, _, _ in kept]
    return result, frame_rows(video, kept, source.name)


def merge_photo_manifest(rows: list[dict[str, str]]) -> int:
    """Replace every benchmark row that came from a video, keep everything else untouched."""
    with PHOTO_MANIFEST.open(newline="", encoding="utf-8") as f:
        existing = list(csv.DictReader(f))
    keep = [r for r in existing if not r.get("scene_id", "").startswith("video-")]
    out = keep + rows
    with PHOTO_MANIFEST.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PHOTO_COLUMNS)
        writer.writeheader()
        for row in out:
            writer.writerow({c: row.get(c, "") for c in PHOTO_COLUMNS})
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="where the videos are")
    parser.add_argument("--every", type=float, default=4.0, help="seconds between samples")
    parser.add_argument("--per-video", type=int, default=15, help="most frames from one video")
    parser.add_argument(
        "--hash-distance", type=int, default=8, help="dHash bits that count as the same"
    )
    parser.add_argument("--dry-run", action="store_true", help="write nothing")
    args = parser.parse_args(argv)

    if shutil.which("ffmpeg") is None:
        print("frames: ffmpeg is not installed; brew install ffmpeg")
        return 1
    try:
        videos = read_videos(MANIFEST)
        screen = PeopleAndPlates()
    except FrameError as e:
        print(f"frames: refused: {e}")
        return 1

    if not args.dry_run:
        for old in FRAMES_DIR.glob("*.jpg"):
            old.unlink()

    all_rows: list[dict[str, str]] = []
    results: list[VideoResult] = []
    for video in videos:
        try:
            result, rows = process_video(
                video,
                args.cache,
                args.every,
                args.per_video,
                args.hash_distance,
                screen,
                args.dry_run,
            )
        except FrameError as e:
            print(f"frames: refused: {e}")
            return 1
        results.append(result)
        all_rows.extend(rows)
        print(f"  {video.id}: sampled {result.sampled}, kept {len(result.kept)}")

    report: dict[str, Any] = {
        "videos": len(videos),
        "frames_kept": len(all_rows),
        "labelled": sum(1 for r in all_rows if r["gold_label"]),
        "unlabelled": sum(1 for r in all_rows if not r["gold_label"]),
        "per_video": [
            {
                "video_id": r.video_id,
                "sampled": r.sampled,
                "kept": len(r.kept),
                "dropped": [{"reason": d.reason, "at_s": d.at_s} for d in r.dropped],
            }
            for r in results
        ],
    }
    if args.dry_run:
        print(json.dumps({k: v for k, v in report.items() if k != "per_video"}, indent=2))
        print("frames: dry run, nothing written")
        return 0
    merge_photo_manifest(all_rows)
    (VIDEOS / "frames.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dropped_people = sum(
        1 for r in results for d in r.dropped if d.reason.startswith(("person", "plate"))
    )
    print(
        f"frames: {len(all_rows)} frames from {len(videos)} videos "
        f"({report['labelled']} labelled, {report['unlabelled']} unlabelled); "
        f"{dropped_people} dropped for a person or a plate; "
        f"rows merged into photos/manifest.csv; videos/frames.json written"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
