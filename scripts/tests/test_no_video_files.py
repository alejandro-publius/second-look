"""Update 14 and UPDATE_22: never commit a video file. The walks and the video's creek footage
are cut from caches outside the repository (~/second-look-cache, ~/second-look-media)."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIDEO = (".mp4", ".webm", ".mov", ".mkv", ".ogv", ".avi", ".m4v", ".mpg", ".mpeg", ".flv", ".wmv")


def tracked() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [p for p in out.split("\0") if p]


def looks_like_video(head: bytes) -> bool:
    """The first bytes of a video container, whatever the file is called."""
    return (
        head[4:8] == b"ftyp"  # mp4, mov, m4v, 3gp
        or head[:4] == b"\x1a\x45\xdf\xa3"  # webm, mkv
        or (head[:4] == b"RIFF" and head[8:12] == b"AVI ")
        or head[:4] == b"OggS"
        or head[:3] == b"FLV"
        or head[:4] == b"\x00\x00\x01\xba"  # MPEG program stream
    )


def test_no_video_file_is_tracked() -> None:
    assert [p for p in tracked() if p.lower().endswith(VIDEO)] == []


def test_no_tracked_file_is_a_video_under_another_name() -> None:
    found = []
    for p in tracked():
        path = ROOT / p
        if path.is_file():
            with path.open("rb") as f:
                if looks_like_video(f.read(12)):
                    found.append(p)
    assert found == []


def test_the_sniffer_knows_each_container() -> None:
    assert looks_like_video(b"\x00\x00\x00\x20ftypisom")
    assert looks_like_video(b"\x1a\x45\xdf\xa3\x01\x00\x00\x00")
    assert looks_like_video(b"RIFF\x00\x00\x00\x00AVI LIST")
    assert not looks_like_video(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0d")
    assert not looks_like_video(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00")


def test_the_ignore_file_refuses_every_clip_the_video_makes() -> None:
    for path in (
        "apps/web/public/walks/v01.mp4",
        "docs/video/clips/01-landing.mp4",
        "docs/video/clips/raw/extra-check.webm",
        "docs/video/rough_cut_scratch_voice.mp4",
        "docs/video/rough_cut.mp4",
        "docs/video/anything.mov",
    ):
        probe = subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT, check=False)
        assert probe.returncode == 0, path
