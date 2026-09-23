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
3. Drops a frame through two local screens, either of which is enough. Apple's Vision
   framework (macOS, through pyobjc) finds people, faces and any line of text it can read, which
   covers title cards, captions, watermarks, plates and house numbers; its scene labels drop a
   frame with no water in view, and a near uniform frame is dropped as blank. OpenCV's Haar
   cascades, HOG people detector and a plate shaped rectangle test run second. This is a screen,
   not a promise, and a person looks at every kept frame before a commit.
4. Keeps at most --per-video frames, spread across the video rather than bunched at the front.
5. A video that keeps fewer than MIN_KEPT_PER_VIDEO frames is not mostly footage of water and
   banks, which Update 14 section 3 item 3 asks for. Its frames are thrown away and its link is
   written to videos/failed_videos.json, which scripts/pick_videos.py reads to pick again.

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


FAILURES = VIDEOS / "failed_videos.json"
# A person looks at every kept frame; what they drop is written here and honoured on every run.
REVIEW = VIDEOS / "review.json"
MIN_KEPT_PER_VIDEO = 6
# Scene labels from Vision's classifier that mean water is in view, and the confidence it needs.
# Small creeks often come back as wetland rather than water, so wetland counts.
WATER_LABELS = frozenset(
    {
        "water",
        "liquid",
        "water_body",
        "waterways",
        "river",
        "creek",
        "stream",
        "wetland",
        "waterfall",
        "canal",
        "pond",
        "puddle",
        "rapids",
    }
)
WATER_MIN = 0.2
BLANK_STD = 12.0


def vision_verdict(
    people: int, faces: int, text_lines: list[str], labels: dict[str, float], grey_std: float
) -> str | None:
    """Why a frame is dropped, from what Vision saw, or None to keep it. Pure, so it is tested."""
    if people or faces:
        return f"person: vision found {people} people and {faces} faces"
    if text_lines:
        shown = "; ".join(text_lines)[:60]
        return f"text on screen (a title, caption, watermark, plate or number): {shown}"
    if grey_std < BLANK_STD:
        return "blank: a near uniform frame, such as a fade or a title background"
    water = max((v for k, v in labels.items() if k in WATER_LABELS), default=0.0)
    if water < WATER_MIN:
        return f"no water in view: the best water label scored {water:.2f}"
    return None


class VisionScreen:
    """Apple's Vision framework, on this Mac, with nothing sent anywhere."""

    def __init__(self) -> None:
        try:
            import Vision
            from Foundation import NSURL
        except ImportError as e:
            raise FrameError(
                "Vision is not importable. Frames are cut on macOS with pyobjc-framework-Vision "
                "(uv sync installs it there); nothing else in the build needs it"
            ) from e
        self.vision = Vision
        self.nsurl = NSURL

    def look(self, path: Path) -> tuple[int, int, list[str], dict[str, float]]:
        v = self.vision
        handler = v.VNImageRequestHandler.alloc().initWithURL_options_(
            self.nsurl.fileURLWithPath_(str(path)), None
        )
        humans = v.VNDetectHumanRectanglesRequest.alloc().init()
        humans.setUpperBodyOnly_(False)
        faces = v.VNDetectFaceRectanglesRequest.alloc().init()
        text = v.VNRecognizeTextRequest.alloc().init()
        text.setRecognitionLevel_(0)  # accurate
        text.setUsesLanguageCorrection_(False)
        classify = v.VNClassifyImageRequest.alloc().init()
        ok, _error = handler.performRequests_error_([humans, faces, text, classify], None)
        if not ok:
            raise FrameError(f"Vision could not read {path}")
        people = sum(1 for o in (humans.results() or []) if o.confidence() >= 0.3)
        face_count = len(faces.results() or [])
        lines = []
        for o in text.results() or []:
            best = o.topCandidates_(1)
            if best and best[0].confidence() >= 0.3:
                lines.append(str(best[0].string()))
        labels = {
            str(o.identifier()): float(o.confidence())
            for o in (classify.results() or [])
            if o.confidence() >= 0.05
        }
        return people, face_count, lines, labels

    def reason_to_drop(self, path: Path) -> str | None:
        with Image.open(path) as image:
            grey_std = float(np.asarray(image.convert("L"), dtype=np.float32).std())
        people, faces, lines, labels = self.look(path)
        return vision_verdict(people, faces, lines, labels, grey_std)


class Screens:
    """Vision first, then OpenCV. Either one is enough to drop a frame."""

    def __init__(self, *screens: Any) -> None:
        self.screens = screens

    def reason_to_drop(self, path: Path) -> str | None:
        for screen in self.screens:
            reason = screen.reason_to_drop(path)
            if reason is not None:
                return str(reason)
        return None


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

    Three passes, any one of which drops the frame:

    1. OpenCV's Haar cascades for faces, profiles, upper bodies and whole bodies.
    2. OpenCV's HOG people detector, which catches a whole person walking where a cascade
       trained on a front-facing head does not.
    3. A plate and number test, which is cruder on purpose: a small bright rectangle with a lot
       of dark marks inside it is the shape a licence plate or a door number makes, and a frame
       with one is dropped whether or not it really is one.

    Nothing here is a promise that a frame has no person in it. It is a screen that keeps the
    obvious cases out of a pool nobody has looked at yet. We would rather lose a good frame
    than show a stranger's car. This needs OpenCV 4.x: version 5 dropped the cascades and the
    HOG detector from the Python wheel, so `pyproject.toml` pins it below 5.
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
            cascade = cv2.CascadeClassifier(str(path))
            if not cascade.empty():
                self.cascades.append((name, cascade))
        if not self.cascades:
            raise FrameError(
                "OpenCV has no Haar cascades here, so frames cannot be screened for people. "
                "Version 5 dropped them; install opencv-python-headless 4.x"
            )
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())  # type: ignore[attr-defined]

    def reason_to_drop(self, path: Path) -> str | None:
        cv2 = self.cv2
        image = cv2.imread(str(path))
        if image is None:
            return "unreadable"
        grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        flat = cv2.equalizeHist(grey)
        for name, cascade in self.cascades:
            found = cascade.detectMultiScale(
                flat, scaleFactor=1.08, minNeighbors=6, minSize=(28, 28)
            )
            if len(found) > 0:
                return f"person: {name.replace('haarcascade_', '').replace('.xml', '')}"
        people, _weights = self.hog.detectMultiScale(
            grey, winStride=(8, 8), padding=(8, 8), scale=1.05
        )
        if len(people) > 0:
            return "person: hog people detector"
        if self._plate_like(grey):
            return "plate or number: a small bright rectangle with dense dark marks"
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
        # A new image built from the pixels only, so no EXIF, ICC or comment block survives.
        clean = Image.frombytes("RGB", image.size, image.tobytes())
        dest.parent.mkdir(parents=True, exist_ok=True)
        clean.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True)
        out_w, out_h = clean.size
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    return digest, out_w, out_h


def license_code(text: str) -> str:
    """The manifest's licence code for the words a source used.

    YouTube's "Creative Commons Attribution license (reuse allowed)" is CC BY 3.0, the only
    Creative Commons licence YouTube offers. Commons writes "CC BY 3.0" and the like. Anything this
    cannot map is returned as it came, and make manifest-check then refuses it by name.
    """
    low = text.strip().lower()
    if low.startswith("creative commons attribution license"):
        return "CC-BY-3.0"
    if low in {"cc0", "cc0 1.0", "cc-zero"}:
        return "CC0-1.0"
    parts = low.replace("-", " ").split()
    if len(parts) == 3 and parts[:2] == ["cc", "by"] and parts[2] in {"2.0", "3.0", "4.0"}:
        return f"CC-BY-{parts[2]}"
    return text


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
                "license": license_code(video.license),
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
    screen: Any,
    dry_run: bool,
    review: dict[str, str] | None = None,
) -> tuple[VideoResult, list[dict[str, str]]]:
    review = review or {}
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
            by_eye = review.get(f"{video.source_url}@{int(at_s)}")
            if by_eye:
                result.dropped.append(Dropped(f"checked by eye: {by_eye}", at_s))
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


def prune_video_manifest(failures: dict[str, str], path: Path = MANIFEST) -> int:
    """videos/manifest.csv lists only the videos in use: a failed video's row goes."""
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    kept = [r for r in rows if r.get("source_url", "") not in failures]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(kept)
    return len(rows) - len(kept)


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
        screen = Screens(VisionScreen(), PeopleAndPlates())
    except FrameError as e:
        print(f"frames: refused: {e}")
        return 1

    if not args.dry_run:
        for old in FRAMES_DIR.glob("*.jpg"):
            old.unlink()

    all_rows: list[dict[str, str]] = []
    results: list[VideoResult] = []
    failures: dict[str, str] = (
        json.loads(FAILURES.read_text(encoding="utf-8")) if FAILURES.exists() else {}
    )
    reviewed = json.loads(REVIEW.read_text(encoding="utf-8")) if REVIEW.exists() else {}
    for url, why in reviewed.get("videos", {}).items():
        failures.setdefault(url, f"checked by eye: {why}")
    frame_review: dict[str, str] = reviewed.get("frames", {})
    for video in videos:
        if video.source_url in failures:
            print(f"  {video.id}: skipped, already failed: {failures[video.source_url][:80]}")
            continue
        try:
            result, rows = process_video(
                video,
                args.cache,
                args.every,
                args.per_video,
                args.hash_distance,
                screen,
                args.dry_run,
                frame_review,
            )
        except FrameError as e:
            print(f"frames: refused: {e}")
            return 1
        results.append(result)
        if len(result.kept) < MIN_KEPT_PER_VIDEO:
            failures[video.source_url] = (
                f"only {len(result.kept)} of {result.sampled} sampled frames show water with no "
                f"person or text, under {MIN_KEPT_PER_VIDEO}, so it is not mostly water and banks"
            )
            for row in rows:
                (FRAMES_DIR / Path(row["file"]).name).unlink(missing_ok=True)
            print(f"  {video.id}: sampled {result.sampled}, kept {len(result.kept)}: FAILED")
            continue
        all_rows.extend(rows)
        print(f"  {video.id}: sampled {result.sampled}, kept {len(result.kept)}")

    report: dict[str, Any] = {
        "videos": len(videos),
        "frames_kept": len(all_rows),
        "labelled": sum(1 for r in all_rows if r["gold_label"]),
        "unlabelled": sum(1 for r in all_rows if not r["gold_label"]),
        "failed_videos": sum(1 for r in results if len(r.kept) < MIN_KEPT_PER_VIDEO),
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
    FAILURES.write_text(
        json.dumps(failures, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    prune_video_manifest(failures)
    merge_photo_manifest(all_rows)
    (VIDEOS / "frames.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    dropped_people = sum(
        1 for r in results for d in r.dropped if d.reason.startswith(("person", "plate", "text"))
    )
    print(
        f"frames: {len(all_rows)} frames from {len(videos)} videos "
        f"({report['labelled']} labelled, {report['unlabelled']} unlabelled); "
        f"{dropped_people} dropped for a person, a plate or text; "
        f"{report['failed_videos']} videos failed and are in videos/failed_videos.json; "
        f"rows merged into photos/manifest.csv; videos/frames.json written"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
