"""The frame pipeline: the parts that decide what is kept and what a row says.

ffmpeg and OpenCV are exercised where they are cheap to exercise and stubbed where they are not.
The point of these tests is the policy, not the codecs: a near duplicate is dropped, a frame the
screen dislikes is dropped, a label only ever comes from the video row, and an unlabelled frame
says so in its own evidence field.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from scripts import make_frames


def a_picture(seed: int, size: tuple[int, int] = (160, 120)) -> Image.Image:
    rng = np.random.default_rng(seed)
    return Image.fromarray(rng.integers(0, 255, (size[1], size[0], 3), dtype=np.uint8))


def test_the_same_picture_hashes_the_same_and_a_different_one_does_not() -> None:
    one = a_picture(1)
    same = one.copy()
    other = a_picture(2)
    assert make_frames.dhash(one) == make_frames.dhash(same)
    assert make_frames.hamming(make_frames.dhash(one), make_frames.dhash(other)) > 8


def test_a_slightly_brighter_copy_is_still_a_near_duplicate() -> None:
    """A slow pan gives frames that differ in exposure, not in content."""
    one = a_picture(3)
    brighter = Image.eval(one, lambda v: min(255, v + 12))
    distance = make_frames.hamming(make_frames.dhash(one), make_frames.dhash(brighter))
    assert distance <= 8


def test_sample_times_skips_the_ends_and_steps_by_every() -> None:
    times = make_frames.sample_times(duration_s=60.0, every_s=10.0)
    assert times[0] >= 1.0
    assert times[-1] <= 57.0
    assert all(round(b - a, 2) == 10.0 for a, b in zip(times, times[1:], strict=False))


def test_a_very_short_video_still_gives_one_time() -> None:
    assert make_frames.sample_times(duration_s=2.0, every_s=4.0) == [0.04]


def a_video(**over: object) -> make_frames.Video:
    fields: dict[str, object] = {
        "id": "w01",
        "title": "A concrete flood channel in the city",
        "author": "Someone",
        "license": "CC-BY-4.0",
        "source_url": "https://example.org/video",
        "country": "Portugal",
        "duration_s": 120.0,
        "cache_file": "w01.mp4",
        "label_feature": "artificial_bank",
        "label_value": "present",
        "label_evidence": "The description says: the stream runs in a concrete flood channel.",
        "notes": "",
    }
    fields.update(over)
    return make_frames.Video(**fields)  # type: ignore[arg-type]


def test_a_labelled_frame_carries_the_feature_the_value_and_the_description() -> None:
    rows = make_frames.frame_rows(
        a_video(), [(12.0, Path("photos/benchmark/w01-00012.jpg"), "aa")], "w01.mp4"
    )
    row = rows[0]
    assert row["role"] == "benchmark"
    assert row["feature"] == "artificial_bank"
    assert row["gold_label"] == "present"
    assert row["scene_id"] == "video-w01"
    assert "concrete flood channel" in row["label_evidence"]
    assert "Frame at 12 s" in row["label_evidence"]
    assert row["synthetic"] == "false" and row["faces"] == "false"


def test_an_unlabelled_frame_says_the_description_supported_no_label() -> None:
    video = a_video(label_feature="", label_value="", label_evidence="")
    rows = make_frames.frame_rows(
        video, [(5.0, Path("photos/benchmark/w01-00005.jpg"), "bb")], "w01.mp4"
    )
    row = rows[0]
    assert row["feature"] == "" and row["gold_label"] == ""
    assert "supports no label" in row["label_evidence"]
    assert "agreement between models" in row["label_evidence"]


def test_the_screen_drops_a_frame_it_cannot_read(tmp_path: Path) -> None:
    screen = make_frames.PeopleAndPlates()
    broken = tmp_path / "not-an-image.jpg"
    broken.write_bytes(b"this is not a jpeg")
    assert screen.reason_to_drop(broken) == "unreadable"


def test_the_screen_lets_a_plain_picture_of_nothing_through(tmp_path: Path) -> None:
    screen = make_frames.PeopleAndPlates()
    plain = tmp_path / "grey.jpg"
    Image.new("RGB", (640, 480), (110, 120, 105)).save(plain, "JPEG")
    assert screen.reason_to_drop(plain) is None


def test_the_screen_drops_a_bright_rectangle_full_of_dark_marks(tmp_path: Path) -> None:
    """The shape a licence plate or a door number makes. It is dropped whether or not it is one."""
    image = Image.new("RGB", (800, 600), (90, 100, 95))
    plate = Image.new("RGB", (120, 34), (245, 245, 240))
    for x in range(6, 114, 14):
        for y in range(6, 28):
            for dx in range(7):
                plate.putpixel((x + dx, y), (20, 20, 20))
    image.paste(plate, (340, 300))
    path = tmp_path / "plate.jpg"
    image.save(path, "JPEG", quality=95)
    screen = make_frames.PeopleAndPlates()
    reason = screen.reason_to_drop(path)
    assert reason is not None and reason.startswith("plate or number")


def test_reading_the_video_manifest_refuses_when_it_is_missing(tmp_path: Path) -> None:
    with pytest.raises(make_frames.FrameError):
        make_frames.read_videos(tmp_path / "nothing.csv")


def test_merging_replaces_only_the_rows_that_came_from_a_video(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=make_frames.PHOTO_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {"id": "ph-bank-01", "file": "bank/a.jpg", "role": "test", "scene_id": "commons-a"}
        )
        writer.writerow(
            {
                "id": "old-frame",
                "file": "benchmark/old.jpg",
                "role": "benchmark",
                "scene_id": "video-w09",
            }
        )
    monkeypatch.setattr(make_frames, "PHOTO_MANIFEST", manifest)
    new = make_frames.frame_rows(
        a_video(), [(1.0, Path("photos/benchmark/w01-00001.jpg"), "cc")], "w01.mp4"
    )
    make_frames.merge_photo_manifest(new)
    with manifest.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ids = [r["id"] for r in rows]
    assert "ph-bank-01" in ids, "a photo that did not come from a video is left alone"
    assert "old-frame" not in ids, "the old frames from videos are replaced"
    assert "w01-00001" in ids


WATERY = {"water": 0.8, "outdoor": 0.9}


def test_vision_keeps_a_frame_of_water_with_nobody_and_no_text() -> None:
    assert make_frames.vision_verdict(0, 0, [], WATERY, 40.0) is None


def test_vision_drops_a_person_even_with_water_in_view() -> None:
    reason = make_frames.vision_verdict(1, 0, [], WATERY, 40.0)
    assert reason is not None and reason.startswith("person")


def test_vision_drops_a_face_it_found_without_a_body() -> None:
    reason = make_frames.vision_verdict(0, 1, [], WATERY, 40.0)
    assert reason is not None and reason.startswith("person")


def test_vision_drops_any_readable_text_because_it_can_give_the_answer_away() -> None:
    reason = make_frames.vision_verdict(0, 0, ["Project will stabilize the bank"], WATERY, 40.0)
    assert reason is not None and reason.startswith("text on screen")


def test_vision_drops_a_blank_fade() -> None:
    reason = make_frames.vision_verdict(0, 0, [], WATERY, 3.0)
    assert reason is not None and reason.startswith("blank")


def test_vision_drops_a_frame_with_no_water_label_over_the_line() -> None:
    reason = make_frames.vision_verdict(0, 0, [], {"forest": 0.9, "water": 0.1}, 40.0)
    assert reason is not None and reason.startswith("no water")


def test_a_small_creek_that_vision_calls_wetland_counts_as_water() -> None:
    assert make_frames.vision_verdict(0, 0, [], {"wetland": 0.46}, 40.0) is None


def test_the_screens_drop_when_any_one_screen_drops() -> None:
    class Keep:
        def reason_to_drop(self, path: Path) -> str | None:
            return None

    class Drop:
        def reason_to_drop(self, path: Path) -> str | None:
            return "person: test"

    assert make_frames.Screens(Keep(), Keep()).reason_to_drop(Path("x")) is None
    assert make_frames.Screens(Keep(), Drop()).reason_to_drop(Path("x")) == "person: test"
