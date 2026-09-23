"""The walk rule: one per country, the densest window, and the gate decides the one question."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts import build_walks as bw


def v(vid: str, country: str, duration: float = 300) -> dict[str, str]:
    return {"id": vid, "country": country, "duration_s": str(duration)}


def test_one_walk_per_country_the_video_with_most_frames_wins() -> None:
    videos = [
        v("v01", "Chile"),
        v("v02", "Chile"),
        v("v03", "Peru"),
        v("v04", ""),
        v("v05", "Italy"),
    ]
    frames = {"v01": ["a"] * 6, "v02": ["a"] * 9, "v03": ["a"] * 7, "v04": ["a"] * 20, "v05": []}
    chosen = bw.choose_walks(videos, frames, wanted=4)
    # v04 names no country and v05 kept no frames, so neither can be a walk.
    assert [c["id"] for c in chosen] == ["v02", "v03"]


def test_the_window_holds_the_most_kept_frames() -> None:
    assert bw.best_window([10, 100, 104, 108, 112, 300], duration_s=400) == 98
    # Never past the end of the video.
    assert bw.best_window([395], duration_s=400) == 360


def ans(model: str, frame: str, feature: str, answer: str) -> dict[str, object]:
    return {"model": model, "frame": frame, "feature": feature, "answer": answer, "note": "n"}


def test_a_synthetic_pass_table_makes_no_question() -> None:
    answers = [ans("m", "f1", "pipe_running", "yes") for _ in range(3)]
    out = bw.gated_flags(answers, {"f1"}, {"real": False, "models": {}})
    assert out["question"] is None and out["dropped"] == 1


def test_a_passed_feature_gives_one_question_and_frames_outside_the_clip_do_not_count() -> None:
    table = {"real": True, "models": {"m": {"pipe_running": {"passed": True}}}}
    answers = [ans("m", "f1", "pipe_running", "yes") for _ in range(2)]
    answers += [ans("m", "f1", "pipe_running", "no")]
    answers += [ans("m", "f9", "pipe_running", "yes") for _ in range(3)]
    out = bw.gated_flags(answers, {"f1"}, table)
    assert out["question"] == {"feature": "pipe_running", "note": "n"}
    assert out["kept"] == {"pipe_running": 1}


def test_a_split_vote_is_not_a_yes() -> None:
    table = {"real": True, "models": {"m": {"pipe_running": {"passed": True}}}}
    answers = [ans("m", "f1", "pipe_running", "yes"), ans("m", "f1", "pipe_running", "no")]
    assert bw.gated_flags(answers, {"f1"}, table)["question"] is None


PASSED = {"real": True, "models": {"m": {"pipe_running": {"passed": True}}}}


def test_a_footage_run_that_is_not_real_gives_no_flag_even_when_the_table_passes() -> None:
    """The fake client's notes must never become a walk question, whatever the pass table says."""
    answers = [ans("m", "f1", "pipe_running", "yes") for _ in range(3)]
    for footage in ({"real": False, "answers": answers}, {"answers": answers}, {}):
        out = bw.walk_checker(footage, {"f1"}, PASSED)
        assert out["question"] is None
        assert out["kept"] == {} and out["dropped"] == 0 and out["drop_reasons"] == {}
        assert out["footage_run"] == "synthetic"
        assert out["reason"] == "the footage run is synthetic, so no flag is taken"
    real = bw.walk_checker({"real": True, "answers": answers}, {"f1"}, PASSED)
    assert real["question"] == {"feature": "pipe_running", "note": "n"}
    assert real["footage_run"] == "real" and "reason" not in real


URL = "https://www.youtube.com/watch?v=aaa"


def test_the_seconds_near_a_frame_dropped_by_eye_are_never_clean() -> None:
    review = {
        f"{URL}@30": "a small figure far off",
        f"{URL}@1": "a hand at the edge",
        "https://www.youtube.com/watch?v=bbb@60": "another video",
    }
    assert bw.reviewed_seconds(review, URL) == set(range(0, 5)) | set(range(27, 34))
    assert bw.reviewed_seconds(review, "https://elsewhere") == set()


def test_a_review_key_with_no_second_is_refused() -> None:
    with pytest.raises(SystemExit):
        bw.reviewed_seconds({f"{URL}@later": "x"}, URL)


def _walk_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A one video repo in tmp_path, with every path build_walks reads or writes pointed at it."""
    videos = tmp_path / "videos.csv"
    videos.write_text(
        "id,title,author,license,source_url,country,duration_s,cache_file\n"
        f"v01,A creek,Someone,CC BY 4.0,{URL},Chile,120,v01.mp4\n",
        encoding="utf-8",
    )
    photos = tmp_path / "photos.csv"
    lines = ["id,role,scene_id"] + [f"v01-{s:05d},benchmark,video-v01" for s in range(10, 110, 10)]
    photos.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "v01.mp4").write_bytes(b"not really a video")
    for name, path in {
        "VIDEOS": videos,
        "PHOTOS": photos,
        "FOOTAGE": tmp_path / "footage.json",
        "PASS_TABLE": tmp_path / "pass_table.json",
        "REVIEW": tmp_path / "review.json",
        "OUT_YAML": tmp_path / "walks.yaml",
        "OUT_CLIPS": tmp_path / "public" / "walks",
    }.items():
        monkeypatch.setattr(bw, name, path)
    monkeypatch.setattr(bw.shutil, "which", lambda _name: "/usr/bin/ffmpeg")
    monkeypatch.setattr(bw, "screen_seconds", lambda _src, _cache: set(range(0, 120)))
    return cache


def test_the_clip_window_keeps_clear_of_what_a_person_saw_and_a_fake_run_asks_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = _walk_tree(tmp_path, monkeypatch)
    (tmp_path / "review.json").write_text(json.dumps({"frames": {f"{URL}@30": "a figure"}}))
    (tmp_path / "pass_table.json").write_text(json.dumps(PASSED))
    yes = [ans("m", "v01-00050", "pipe_running", "yes") for _ in range(3)]
    (tmp_path / "footage.json").write_text(json.dumps({"real": False, "answers": yes}))
    assert bw.main(["--no-clips", "--cache", str(cache)]) == 0
    (walk,) = yaml.safe_load((tmp_path / "walks.yaml").read_text())["walks"]
    start, seconds = walk["clip"]["start_s"], walk["clip"]["seconds"]
    # Vision found every second clean, so only the review keeps the clip off seconds 27 to 33.
    assert not set(range(start - 1, start + seconds + 1)) & set(range(27, 34))
    assert walk["checker"]["question"] is None and walk["checker"]["footage_run"] == "synthetic"


def _clip_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, list[str]]:
    cache = _walk_tree(tmp_path, monkeypatch)
    walks = {
        "walks": [{"id": "v01", "clip": {"file": "walks/v01.mp4", "start_s": 5, "seconds": 40}}]
    }
    (tmp_path / "walks.yaml").write_text(yaml.safe_dump(walks))
    clips = tmp_path / "public" / "walks"
    clips.mkdir(parents=True)
    cut: list[str] = []

    def fake_cut(src: Path, dest: Path, start: int, seconds: int = 40) -> int:
        cut.append(f"{src.name}>{dest.name}@{start}+{seconds}")
        dest.write_bytes(b"fresh")
        return 5

    monkeypatch.setattr(bw, "cut_clip", fake_cut)
    return cache, cut


def test_clips_only_cuts_every_named_clip_again_and_deletes_the_rest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache, cut = _clip_tree(tmp_path, monkeypatch)
    clips = tmp_path / "public" / "walks"
    (clips / "v01.mp4").write_bytes(b"an old cut of another window")
    (clips / "v09.mp4").write_bytes(b"a walk that is gone")
    (clips / "README.txt").write_text("not a clip")
    assert bw.main(["--clips-only", "--cache", str(cache)]) == 0
    assert cut == ["v01.mp4>v01.mp4@5+40"], "a clip already on disk is cut again"
    assert (clips / "v01.mp4").read_bytes() == b"fresh"
    assert not (clips / "v09.mp4").exists(), "a clip no walk names is deleted"
    assert (clips / "README.txt").exists(), "only clips are deleted"


def test_clips_only_with_no_source_fails_and_leaves_no_old_clip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache, cut = _clip_tree(tmp_path, monkeypatch)
    (cache / "v01.mp4").unlink()
    (tmp_path / "public" / "walks" / "v01.mp4").write_bytes(b"an old cut")
    assert bw.main(["--clips-only", "--cache", str(cache)]) == 1
    assert cut == [] and not (tmp_path / "public" / "walks" / "v01.mp4").exists()
