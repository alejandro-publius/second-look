"""Download the twelve picked videos into a cache outside this repository.

A video file is never committed. The cache lives at ~/second-look-cache/videos by default and
nothing in the build depends on it being there: `scripts/make_frames.py` reads it, writes the
frames it keeps into photos/benchmark/, and those frames are what the repository carries.

Quality is capped at 720p on purpose. The frames are saved at 1280 px on the long side, so a
2160p download would cost gigabytes and change nothing on screen.

Run: uv run python scripts/fetch_videos.py
     uv run python scripts/fetch_videos.py --only v01 v02
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "videos" / "manifest.csv"
FAILURES = ROOT / "videos" / "failed_videos.json"
DEFAULT_CACHE = Path.home() / "second-look-cache" / "videos"
MAX_HEIGHT = 720


def rows() -> list[dict[str, str]]:
    import csv

    with MANIFEST.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fetch(url: str, dest: Path) -> tuple[bool, str]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "uv",
        "run",
        "yt-dlp",
        "--no-warnings",
        "--no-playlist",
        "-f",
        f"bestvideo[height<={MAX_HEIGHT}]+bestaudio/best[height<={MAX_HEIGHT}]/best",
        "--merge-output-format",
        "mp4",
        "-o",
        str(dest),
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if proc.returncode != 0 or not dest.exists():
        tail = (proc.stderr or proc.stdout).strip().splitlines()
        return False, tail[-1] if tail else "yt-dlp failed"
    return True, ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--only", nargs="*", default=None, help="manifest ids to fetch")
    args = parser.parse_args(argv)
    if not MANIFEST.exists():
        print("fetch-videos: videos/manifest.csv is missing; run scripts/pick_videos.py first")
        return 1
    if shutil.which("ffmpeg") is None:
        print("fetch-videos: ffmpeg is not installed; brew install ffmpeg")
        return 1

    got, failed, skipped = 0, [], 0
    # A video that cannot be fetched is picked again, the same way as one whose frames failed.
    failures = json.loads(FAILURES.read_text(encoding="utf-8")) if FAILURES.exists() else {}
    for row in rows():
        if args.only and row["id"] not in args.only:
            continue
        dest = args.cache / row["cache_file"]
        if dest.exists() and dest.stat().st_size > 0:
            skipped += 1
            continue
        ok, why = fetch(row["source_url"], dest)
        if ok:
            got += 1
            print(f"  {row['id']}: {dest.stat().st_size / 1_000_000:.0f} MB")
        else:
            failed.append((row["id"], why))
            failures[row["source_url"]] = f"download failed: {why}"[:200]
            print(f"  {row['id']}: FAILED, {why}")
    if failed:
        FAILURES.write_text(
            json.dumps(failures, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    total = (
        sum(p.stat().st_size for p in args.cache.glob("*.mp4")) / 1_000_000
        if args.cache.exists()
        else 0
    )
    print(
        f"fetch-videos: {got} downloaded, {skipped} already in the cache, {len(failed)} failed; "
        f"{total:.0f} MB in {args.cache}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
