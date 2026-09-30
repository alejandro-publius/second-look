"""The walk rule: one per country, the densest window, and the gate decides the one question."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
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


def test_a_creek_name_reads_with_the_where_the_country_takes_it() -> None:
    # REVIEW_03 R41: "A creek in United Kingdom" read wrong on /walk.
    assert bw.creek_name("Russia") == "A creek in Russia"
    assert bw.creek_name("United Kingdom") == "A creek in the United Kingdom"
    assert bw.creek_name("United States") == "A creek in the United States"
    assert bw.creek_name("Netherlands") == "A creek in the Netherlands"
    assert bw.creek_name("Czech Republic") == "A creek in the Czech Republic"
    assert bw.creek_name("Chile") == "A creek in Chile"


def test_the_committed_walks_carry_the_creek_name_the_rule_writes() -> None:
    walks = yaml.safe_load(bw.OUT_YAML.read_text(encoding="utf-8"))["walks"]
    assert walks
    for w in walks:
        assert w["creek_name"] == bw.creek_name(w["country"]), w["id"]


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
        "id,title,author,license,source_url,country,duration_s,cache_file,lang\n"
        f"v01,A creek,Someone,CC BY 4.0,{URL},Chile,120,v01.mp4,en\n",
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


def test_the_walk_carries_the_language_of_its_title_and_author(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # WCAG 3.1.2: a screen reader says a Russian title right only when the page marks it ru. The
    # lang column of videos/manifest.csv travels into the walk, and a row with none is refused
    # rather than read as English.
    cache = _walk_tree(tmp_path, monkeypatch)
    (tmp_path / "pass_table.json").write_text(json.dumps(PASSED))
    yes = [ans("m", "v01-00050", "pipe_running", "yes") for _ in range(3)]
    (tmp_path / "footage.json").write_text(json.dumps({"real": False, "answers": yes}))
    assert bw.main(["--no-clips", "--cache", str(cache)]) == 0
    (walk,) = yaml.safe_load((tmp_path / "walks.yaml").read_text())["walks"]
    assert walk["lang"] == "en"

    videos = bw.VIDEOS
    videos.write_text(videos.read_text(encoding="utf-8").replace(",en\n", ",\n"), encoding="utf-8")
    with pytest.raises(SystemExit, match="has no lang"):
        bw.main(["--no-clips", "--cache", str(cache)])


def test_the_committed_walks_name_the_language_their_title_is_in() -> None:
    walks = yaml.safe_load(bw.OUT_YAML.read_text(encoding="utf-8"))["walks"]
    videos = {v["id"]: v for v in bw.read_csv(bw.VIDEOS)}
    assert walks
    for w in walks:
        assert w["lang"] == videos[w["id"]]["lang"], w["id"]
        assert w["lang"] == ("ru" if re.search(r"[\u0400-\u04FF]", w["title"]) else "en"), w["id"]


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


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="cuts a real clip: needs ffmpeg and ffprobe",
)
def test_a_clip_is_cut_at_540_lines_h264_and_about_1_mbps(tmp_path: Path) -> None:
    """Judge walk W05: at 720 lines and 2.5 Mbps a clip stalled on a 1.6 Mbps phone line.

    The source here is the hardest kind to squeeze, moving noise at 720 lines, so an encoder with
    no ceiling would spend far more than 1 Mbps on it. The cut must come out 540 lines, H.264,
    no sound, and near 1 Mbps for the whole clip.
    """
    src = tmp_path / "busy.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
            "-i", "testsrc2=size=1280x720:rate=30:duration=10", "-vf", "noise=alls=60:allf=t",
            "-c:v", "libx264", "-preset", "ultrafast", "-qp", "12", str(src),
        ],
        check=True,
    )  # fmt: skip
    dest = tmp_path / "walks" / "clip.mp4"
    size = bw.cut_clip(src, dest, 1, 8)
    probe = json.loads(
        subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "stream=codec_type,codec_name,height:format=duration", "-of", "json", str(dest),
            ],
            capture_output=True, text=True, check=True,
        ).stdout
    )  # fmt: skip
    streams = probe["streams"]
    assert [s["codec_type"] for s in streams] == ["video"], "a clip carries no sound"
    assert streams[0]["codec_name"] == "h264" and streams[0]["height"] == 540
    kbps = size * 8 / float(probe["format"]["duration"]) / 1000
    assert 500 < kbps <= 1250, f"{kbps:.0f} kbps, not about 1 Mbps"
