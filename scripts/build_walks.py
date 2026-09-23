"""Video walks: pick four clips by rule, cut them, and gate the checker's flags at build time.

Update 14 section 3 item 7. A walk is a 30 to 45 second clip, under 20 MB, cut from an openly
licensed creek video, served from our own origin with its credit on screen. The person does the
guided creek check while watching. The checker's flags for the clip are worked out here, at build
time, from the footage run's answers on the clip's own frames, and go through core/gate.py with
the committed pass table. At most one becomes a question, and the page shows it only after the
person has answered. A footage run that is not real gives no flag at all.

The rule, with no taste in it:

1. A video qualifies when its frames passed the screen (it has benchmark rows) and it names a
   country.
2. One walk per country. Within a country the video with the most kept frames wins, then the
   shorter video.
3. Four walks, countries taken in order of kept frames.
4. A clip plays every frame, not the one in four the frame screen saw, so every second of the
   video goes through Vision, and the clip is the window (40 seconds, else 35, else 30) in which
   every second has no person, face or text and which holds the most kept frames. A second within
   3 seconds of a frame a person dropped by eye (videos/review.json) is never clean, because
   Vision missed what they saw. A video with no such window cannot be a walk, and the next video
   in that country is tried. Sound is dropped: a clip needs no voice, and a stranger's voice is
   not ours to publish.

Writes content/walks.yaml (committed) and apps/web/public/walks/<id>.mp4 (never committed; the
.gitignore refuses every video file). With --no-clips it writes only the yaml, which is what CI
and a machine without the cache can do. With --clips-only it cuts every clip the yaml names again
and deletes any other clip in that folder.

Run: uv run python scripts/build_walks.py
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

from core.gate import parse_flags
from core.records import FEATURES
from scripts.make_frames import license_code

ROOT = Path(__file__).resolve().parents[1]
VIDEOS = ROOT / "videos" / "manifest.csv"
PHOTOS = ROOT / "photos" / "manifest.csv"
FOOTAGE = ROOT / "results" / "footage_latest.json"
PASS_TABLE = ROOT / "results" / "model_pass_table.json"
# A person looked at every kept frame; the frames they dropped are named "<source_url>@<second>".
REVIEW = ROOT / "videos" / "review.json"
# A figure a person saw in one frame is in the seconds around it too, so those seconds go as well.
REVIEW_MARGIN_S = 3
OUT_YAML = ROOT / "content" / "walks.yaml"
OUT_CLIPS = ROOT / "apps" / "web" / "public" / "walks"
DEFAULT_CACHE = Path.home() / "second-look-cache" / "videos"
WANTED = 4
WINDOW_S = 40
MAX_BYTES = 20_000_000


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def frame_seconds(photo_id: str) -> int:
    """v08-00123 was cut at 123 seconds."""
    return int(photo_id.rsplit("-", 1)[1])


def ranked_by_country(
    videos: list[dict[str, str]], frames: dict[str, list[str]]
) -> list[list[dict[str, str]]]:
    """Per country, the videos that kept frames, best first; countries by their best video."""
    by_country: dict[str, list[dict[str, str]]] = defaultdict(list)
    for v in videos:
        if frames.get(v["id"]) and v.get("country"):
            by_country[v["country"]].append(v)
    ranked = []
    for vs in by_country.values():
        vs.sort(key=lambda v: (-len(frames[v["id"]]), float(v.get("duration_s") or 0)))
        ranked.append(vs)
    ranked.sort(key=lambda vs: (-len(frames[vs[0]["id"]]), vs[0]["country"]))
    return ranked


def choose_walks(
    videos: list[dict[str, str]], frames: dict[str, list[str]], wanted: int = WANTED
) -> list[dict[str, str]]:
    """The first choice in each country, before any clip is screened."""
    return [vs[0] for vs in ranked_by_country(videos, frames)][:wanted]


def clean_window(
    kept_seconds: list[int],
    clean: set[int],
    duration_s: float,
    lengths: tuple[int, ...] = (40, 35, 30),
) -> tuple[int, int] | None:
    """The window, longest first, in which every second is clean (with one second either side)
    and which holds the most kept frames. None when no window of 30 seconds is clean."""
    for length in lengths:
        best: tuple[int, int] | None = None
        for start in range(0, max(0, int(duration_s) - length) + 1):
            if not all(t in clean for t in range(max(0, start - 1), start + length + 1)):
                continue
            count = sum(1 for k in kept_seconds if start <= k < start + length)
            if count and (best is None or count > best[0]):
                best = (count, start)
        if best is not None:
            return best[1], length
    return None


def screen_seconds(src: Path, cache_dir: Path) -> set[int]:
    """Every second of a video through Vision: the seconds with no person, face or text.

    A clip plays every frame, not the one in four seconds the frame screen saw, so a walk is cut
    only from seconds that pass here. The answer is cached next to the video, outside the repo.
    """
    memo = cache_dir / "screens" / f"{src.name}.json"
    if memo.exists() and json.loads(memo.read_text())["mtime"] == src.stat().st_mtime:
        return set(json.loads(memo.read_text())["clean"])
    from scripts.make_frames import VisionScreen

    vision = VisionScreen()
    clean: set[int] = set()
    with tempfile.TemporaryDirectory(prefix="second-look-seconds-") as tmp:
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-i", str(src), "-vf", "fps=1,scale=640:-2",
             f"{tmp}/s%05d.jpg"],
            check=True,
        )  # fmt: skip
        for frame in sorted(Path(tmp).glob("s*.jpg")):
            people, faces, lines, _labels = vision.look(frame)
            if not (people or faces or lines):
                clean.add(int(frame.stem[1:]) - 1)
    memo.parent.mkdir(parents=True, exist_ok=True)
    memo.write_text(json.dumps({"mtime": src.stat().st_mtime, "clean": sorted(clean)}))
    return clean


def reviewed_seconds(review_frames: dict[str, str], source_url: str) -> set[int]:
    """Every second within REVIEW_MARGIN_S of a frame a person dropped from this video.

    Vision missed these (a small figure far off, a hand at the edge), so a clip must not show
    them either. The keys are "<source_url>@<second>", as scripts/make_frames.py reads them.
    """
    near: set[int] = set()
    for key in review_frames:
        url, _, second = key.rpartition("@")
        if url != source_url:
            continue
        if not second.isdigit():
            raise SystemExit(f"walks: {REVIEW} names a frame with no second: {key}")
        at = int(second)
        near.update(range(max(0, at - REVIEW_MARGIN_S), at + REVIEW_MARGIN_S + 1))
    return near


def best_window(seconds: list[int], duration_s: float, window: int = WINDOW_S) -> int:
    """The start of the window holding the most kept frames, the earliest when tied."""
    best_start, best_count = 0, -1
    for start in sorted(seconds):
        begin = max(0, min(start - 2, int(duration_s) - window))
        count = sum(1 for s in seconds if begin <= s < begin + window)
        if count > best_count:
            best_start, best_count = begin, count
    return best_start


def majority(answers: list[str]) -> str:
    counts = Counter(answers).most_common()
    if not counts or (len(counts) > 1 and counts[0][1] == counts[1][1]):
        return "cant_tell"
    return counts[0][0]


def gated_flags(
    answers: list[dict[str, Any]], frame_ids: set[str], pass_table: dict[str, Any]
) -> dict[str, Any]:
    """Majority yes answers on the clip's frames, through the real gate. One question at most."""
    grouped: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    notes: dict[tuple[str, str, str], str] = {}
    for a in answers:
        if a["frame"] not in frame_ids or a.get("malformed"):
            continue
        key = (a["model"], a["frame"], a["feature"])
        grouped[key].append(a["answer"])
        if a["answer"] == "yes" and a.get("note"):
            notes.setdefault(key, a["note"])
    kept: Counter[str] = Counter()
    kept_note: dict[str, str] = {}
    drops: Counter[str] = Counter()
    for (model, frame, feature), got in sorted(grouped.items()):
        if majority(got) != "yes":
            continue
        note = notes.get((model, frame, feature), "no note")
        candidate = {"feature": feature, "confidence": 1.0, "note": note}
        flags, reasons = parse_flags(candidate, model_id=model, pass_table=pass_table)
        for f in flags:
            kept[f.feature] += 1
            kept_note.setdefault(f.feature, f.note)
        for r in reasons:
            drops[r.split(": ", 1)[-1]] += 1
    question = None
    if kept:
        feature = sorted(kept, key=lambda f: (-kept[f], FEATURES.index(f)))[0]
        question = {"feature": feature, "note": kept_note[feature]}
    return {
        "pass_table_real": pass_table.get("real") is True,
        "kept": dict(kept),
        "dropped": sum(drops.values()),
        "drop_reasons": dict(drops.most_common()),
        "question": question,
    }


def walk_checker(
    footage: dict[str, Any], frame_ids: set[str], pass_table: dict[str, Any]
) -> dict[str, Any]:
    """The checker entry for one walk. A footage run that is not real gives no flag at all.

    A synthetic run's answers and notes were made up by the fake client, so none of them may
    reach the gate, let alone become a question, whatever the pass table says.
    """
    if footage.get("real") is not True:
        return {
            "pass_table_real": pass_table.get("real") is True,
            "kept": {},
            "dropped": 0,
            "drop_reasons": {},
            "question": None,
            "footage_run": "synthetic",
            "reason": "the footage run is synthetic, so no flag is taken",
        }
    checker = gated_flags(footage.get("answers", []), frame_ids, pass_table)
    checker["footage_run"] = "real"
    return checker


def cut_clip(src: Path, dest: Path, start: int, seconds: int = WINDOW_S) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    for crf in (28, 32, 36):
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error", "-ss", str(start), "-t", str(seconds),
            "-i", str(src), "-an", "-vf", "scale=-2:720", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-map_metadata", "-1", str(dest),
        ]  # fmt: skip
        subprocess.run(cmd, check=True)
        if dest.stat().st_size < MAX_BYTES:
            return dest.stat().st_size
    raise SystemExit(f"walks: {dest.name} is still over {MAX_BYTES} bytes at crf 36")


def cut_named_clips(cache: Path) -> int:
    """For a deploy: the committed walks, cut again from the cache. The clips are never in git.

    Every clip the yaml names is cut again, even when a file is already there, because an old
    file may be another window or a walk that has since changed. Any other clip in the folder
    belongs to a walk that is gone, so it is deleted and never shipped.
    """
    walks = (yaml.safe_load(OUT_YAML.read_text(encoding="utf-8")) or {}).get("walks", [])
    by_id = {v["id"]: v for v in read_csv(VIDEOS)}
    named = {(OUT_CLIPS.parent / w["clip"]["file"]).resolve() for w in walks}
    if OUT_CLIPS.exists():
        for old in sorted(OUT_CLIPS.glob("*.mp4")):
            if old.resolve() not in named:
                old.unlink()
                print(f"walks: deleted {old.name}, which no walk in {OUT_YAML.name} names")
    for w in walks:
        dest = OUT_CLIPS.parent / w["clip"]["file"]
        video = by_id.get(w["id"])
        src = cache / video["cache_file"] if video else None
        if src is None or not src.exists():
            # A clip that cannot be cut again from its source is not shipped as it was.
            dest.unlink(missing_ok=True)
            print(f"walks: {w['id']} has no source in {cache}; run scripts/fetch_videos.py")
            return 1
        cut_clip(src, dest, int(w["clip"]["start_s"]), int(w["clip"]["seconds"]))
    print(f"walks: {len(walks)} clips cut again in apps/web/public/walks")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument(
        "--no-clips",
        action="store_true",
        help="screen and choose, but write no mp4 (needs the cache)",
    )
    parser.add_argument(
        "--clips-only",
        action="store_true",
        help="cut the clips content/walks.yaml already names, choosing nothing again (deploys)",
    )
    args = parser.parse_args(argv)
    if args.clips_only:
        return cut_named_clips(args.cache)

    videos = read_csv(VIDEOS)
    frames: dict[str, list[str]] = defaultdict(list)
    for row in read_csv(PHOTOS):
        if row.get("role") == "benchmark" and row.get("scene_id", "").startswith("video-"):
            frames[row["scene_id"].removeprefix("video-")].append(row["id"])
    footage = json.loads(FOOTAGE.read_text(encoding="utf-8")) if FOOTAGE.exists() else {}
    table = json.loads(PASS_TABLE.read_text(encoding="utf-8")) if PASS_TABLE.exists() else {}
    review = json.loads(REVIEW.read_text(encoding="utf-8")) if REVIEW.exists() else {}
    review_frames: dict[str, str] = review.get("frames", {})
    if shutil.which("ffmpeg") is None:
        print("walks: ffmpeg is not installed; brew install ffmpeg")
        return 1

    walks: list[dict[str, Any]] = []
    skipped: list[str] = []
    for country_videos in ranked_by_country(videos, frames):
        if len(walks) == WANTED:
            break
        picked = None
        for v in country_videos:
            src = args.cache / v["cache_file"]
            if not src.exists():
                print(f"walks: {src} is not in the cache; run scripts/fetch_videos.py")
                return 1
            ids = sorted(frames[v["id"]], key=frame_seconds)
            # Vision's clean seconds, less the seconds near any frame a person dropped by eye.
            clean = screen_seconds(src, args.cache.parent) - reviewed_seconds(
                review_frames, v["source_url"]
            )
            window = clean_window(
                [frame_seconds(i) for i in ids], clean, float(v["duration_s"] or 0)
            )
            if window is None:
                skipped.append(f"{v['id']}: no 30 second stretch with no person, face or text")
                continue
            picked = (v, ids, window)
            break
        if picked is None:
            continue
        v, ids, (start, seconds) = picked
        in_clip = [i for i in ids if start <= frame_seconds(i) < start + seconds]
        checker = walk_checker(footage, set(in_clip), table)
        walk = {
            "id": v["id"],
            "title": v["title"],
            "author": v["author"],
            "license": license_code(v["license"]),
            "source_url": v["source_url"],
            "country": v["country"],
            "creek_name": f"A creek in {v['country']}",
            "spot_name": "The stretch in the clip",
            "clip": {
                "file": f"walks/{v['id']}.mp4",
                "start_s": start,
                "seconds": seconds,
                "screened": "every second checked by Vision: no person, face or text",
            },
            "poster_photo_id": in_clip[0],
            "frames_in_clip": in_clip,
            "checker": checker,
        }
        if not args.no_clips:
            size = cut_clip(src, OUT_CLIPS / f"{v['id']}.mp4", start, seconds)
            span = f"{start} s to {start + seconds} s"
            print(f"  {v['id']} {v['country']}: {span}, {size / 1e6:.1f} MB")
        walks.append(walk)

    header = (
        "# Written by scripts/build_walks.py. Do not edit by hand: change the rule there.\n"
        "# The clips themselves are never committed; the script cuts them from the cache.\n"
    )
    OUT_YAML.write_text(
        header + yaml.safe_dump({"walks": walks}, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    countries = [w["country"] for w in walks]
    for line in skipped:
        print(f"walks: passed over {line}")
    print(f"walks: {len(walks)} walks from {len(set(countries))} countries: {', '.join(countries)}")
    if len(walks) < WANTED:
        # Not an error: the rule found fewer countries than Update 14 asks for, and says so.
        print(
            f"walks: {WANTED - len(walks)} short of {WANTED}; no kept video names another country"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
