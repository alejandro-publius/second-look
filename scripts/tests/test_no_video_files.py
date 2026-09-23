"""Update 14: never commit a video file. The walks are cut from a cache outside the repository."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIDEO = (".mp4", ".webm", ".mov", ".mkv", ".ogv", ".avi", ".m4v")


def test_no_video_file_is_tracked() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split("\0")
    assert [p for p in tracked if p.lower().endswith(VIDEO)] == []


def test_the_ignore_file_refuses_a_walk_clip() -> None:
    probe = subprocess.run(
        ["git", "check-ignore", "-q", "apps/web/public/walks/v01.mp4"], cwd=ROOT, check=False
    )
    assert probe.returncode == 0
