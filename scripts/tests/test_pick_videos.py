"""The pick rule: a name is not a label, and a video whose frames failed is picked again."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("pick_videos", ROOT / "scripts" / "pick_videos.py")
assert spec and spec.loader
pick_videos = importlib.util.module_from_spec(spec)
sys.modules["pick_videos"] = pick_videos
spec.loader.exec_module(pick_videos)


def test_a_project_called_concrete_creek_is_not_a_built_bank() -> None:
    text = "the project was named: concrete creek, reclamation of a stream via art."
    assert pick_videos.label_for(text, text) == ("", "", "")


def test_riprap_in_the_description_is_a_built_bank() -> None:
    text = "crews placed riprap along the eroding bank of the creek."
    feature, value, evidence = pick_videos.label_for(text, text)
    assert (feature, value) == ("artificial_bank", "present")
    assert "riprap" in evidence


def test_a_plant_label_never_comes_from_a_description() -> None:
    text = "japanese knotweed has taken over the stream bank."
    assert pick_videos.label_for(text, text) == ("", "", "")


def _candidate(url: str, title: str = "Creek walk") -> dict[str, object]:
    return {
        "id": url.rsplit("=", 1)[-1],
        "source": "youtube",
        "title": title,
        "author": "someone",
        "licence": "Creative Commons Attribution license (reuse allowed)",
        "duration_s": 300,
        "height": 1080,
        "country_if_stated": "",
        "url": url,
        "query": "creek walk",
        "description_excerpt": "a walk along the creek",
    }


def test_a_video_whose_frames_failed_is_dropped_and_another_is_picked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    videos = tmp_path / "videos"
    videos.mkdir()
    a, b = "https://www.youtube.com/watch?v=aaa", "https://www.youtube.com/watch?v=bbb"
    (videos / "candidates.json").write_text(json.dumps([_candidate(a), _candidate(b)]))
    (videos / "failed_videos.json").write_text(json.dumps({a: "only 2 of 40 kept"}))
    for name in ("VIDEOS", "CANDIDATES", "MANIFEST", "PICKED", "FAILURES"):
        attr = {
            "VIDEOS": videos,
            "CANDIDATES": videos / "candidates.json",
            "MANIFEST": videos / "manifest.csv",
            "PICKED": videos / "picked.json",
            "FAILURES": videos / "failed_videos.json",
        }[name]
        monkeypatch.setattr(pick_videos, name, attr)
    assert pick_videos.main(["--offline", "--wanted", "2"]) == 0
    picked = json.loads((videos / "picked.json").read_text())
    assert [k["id"] for k in picked["kept"]] == ["bbb"]
    dropped = {d["id"]: d["why"] for d in picked["dropped"]}
    assert dropped["aaa"].startswith("frames: only 2 of 40")
