"""The walk rule: one per country, the densest window, and the gate decides the one question."""

from __future__ import annotations

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
