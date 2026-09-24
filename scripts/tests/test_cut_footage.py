"""The pure parts of the footage cutter (UPDATE_22 6.3): the window, the push-in, the checks."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from scripts import cut_footage
from scripts.cut_footage import (
    MAX_S,
    MIN_S,
    CutError,
    clip_name,
    cover_box,
    credit_text,
    frame_changes,
    probe_problems,
    push_in_boxes,
    steadiest_window,
    usable_samples,
    window_seconds,
)

RATE = 10


def series(seconds: float, level: float) -> list[float]:
    return [level] * round(seconds * RATE)


def test_the_steadiest_window_is_the_one_with_the_least_change() -> None:
    # 2 s shaky, 6 s calm, 4 s shaky: a 5 s window must sit inside the calm stretch.
    changes = series(2, 9.0) + series(6, 1.0) + series(4, 9.0)
    start = steadiest_window(changes, RATE, 5.0)
    assert 2.0 <= start <= 3.0
    assert start == 2.0  # the earliest of the equal windows


def test_a_dip_inside_a_long_window_counts_by_its_total() -> None:
    # One very calm second is not enough: the window with the lowest total wins.
    changes = series(1, 5.0) + series(1, 0.0) + series(5, 8.0) + series(8, 2.0)
    start = steadiest_window(changes, RATE, 6.0)
    assert start >= 7.0


def test_the_first_second_is_never_used() -> None:
    # The calmest stretch is the first second; the picker must start after it.
    changes = series(1, 0.0) + series(10, 3.0)
    assert steadiest_window(changes, RATE, 6.0) >= 1.0
    assert steadiest_window(changes, RATE, 6.0, skip_s=2.5) >= 2.5


def test_the_window_never_runs_past_the_end() -> None:
    changes = series(3, 5.0) + series(4, 0.0)  # calm only at the very end
    start = steadiest_window(changes, RATE, 6.0)
    assert start + 6.0 <= len(changes) / RATE + 1e-9


def test_a_black_stretch_never_wins() -> None:
    # A black opening barely changes. Marked unusable, it must lose to real footage.
    changes = series(9, 0.0) + series(12, 4.0)
    usable = [False] * 91 + [True] * (len(changes) + 1 - 91)
    assert steadiest_window(changes, RATE, 6.0) < 9.0  # without the flags it would win
    start = steadiest_window(changes, RATE, 6.0, usable=usable)
    assert start >= 9.1


def test_usable_samples_marks_black_and_flat_frames() -> None:
    rng = np.random.default_rng(1)
    frames = np.stack(
        [
            np.zeros((9, 16), np.uint8),
            np.full((9, 16), 128, np.uint8),
            rng.integers(0, 255, (9, 16), dtype=np.uint8),
        ]
    )
    assert usable_samples(frames).tolist() == [False, False, True]


def test_no_window_at_all_is_an_error() -> None:
    with pytest.raises(CutError):
        steadiest_window(series(5, 1.0), RATE, 6.0)
    with pytest.raises(CutError):
        steadiest_window(series(10, 1.0), RATE, 6.0, usable=[False] * 101)


def test_frame_changes_is_the_mean_absolute_difference() -> None:
    a = np.zeros((2, 2), np.uint8)
    b = np.full((2, 2), 10, np.uint8)
    c = np.array([[10, 30], [10, 30]], np.uint8)
    assert frame_changes(np.stack([a, b, c])).tolist() == [10.0, 10.0]


def test_the_clip_length_keeps_6_to_10_seconds() -> None:
    assert window_seconds(72.0) == MAX_S
    assert window_seconds(9.52) == pytest.approx(8.3)
    assert MIN_S <= window_seconds(8.64) <= MAX_S
    with pytest.raises(CutError):
        window_seconds(6.5)


def test_the_push_in_is_even_centred_16_by_9_and_inside_the_photo() -> None:
    boxes = push_in_boxes(2592, 1944, 180)
    assert len(boxes) == 180
    assert boxes[0] == pytest.approx(cover_box(2592, 1944))
    widths = [x1 - x0 for x0, _, x1, _ in boxes]
    assert widths[0] / widths[-1] == pytest.approx(1.08)
    ratios = [widths[i] / widths[i + 1] for i in range(len(widths) - 1)]
    assert max(ratios) - min(ratios) < 1e-9  # the same step every frame: no jump
    for x0, y0, x1, y1 in boxes:
        assert (x1 - x0) / (y1 - y0) == pytest.approx(16 / 9)
        assert (x0 + x1) / 2 == pytest.approx(1296) and (y0 + y1) / 2 == pytest.approx(972)
        assert x0 >= 0 and y0 >= 0 and x1 <= 2592 and y1 <= 1944


def test_cover_crops_and_never_stretches() -> None:
    assert cover_box(1920, 1080) == (0, 0, 1920, 1080)
    x0, y0, x1, y1 = cover_box(1080, 1920)  # an upright source keeps its width
    assert (x1 - x0, round(y1 - y0)) == (1080, 608)


def test_clip_names_are_stable_and_start_with_the_beat() -> None:
    assert clip_name("gauge", "StrawberryCreek9.JPG") == "gauge-strawberrycreek9.mp4"
    long = clip_name("action", "Salmon River wood jam & side channel restoration project at X.webm")
    assert long == "action-salmon-river-wood-jam-side-channel-restoration.mp4"


def test_the_credit_names_title_author_licence_and_commons() -> None:
    text = credit_text("StrawberryCreek3.JPG", "Coro", "CC BY-SA 3.0")
    assert text == '"StrawberryCreek3" by Coro, CC BY-SA 3.0, Wikimedia Commons'


def good_probe(**change: object) -> dict[str, Any]:
    video: dict[str, object] = {
        "codec_type": "video",
        "codec_name": "h264",
        "pix_fmt": "yuv420p",
        "width": 1920,
        "height": 1080,
    }
    video.update(change)
    return {"streams": [video], "format": {"duration": "8.000"}}


def test_the_probe_check_passes_a_good_clip_and_names_each_fault() -> None:
    assert probe_problems(good_probe(), 8.0) == []
    assert probe_problems(good_probe(width=1280, height=720), 8.0) == ["size 1280x720"]
    assert probe_problems(good_probe(codec_name="vp9"), 8.0) == ["codec vp9"]
    assert probe_problems(good_probe(pix_fmt="yuv444p"), 8.0) == ["pixel format yuv444p"]
    with_audio = good_probe()
    with_audio["streams"] = [*good_probe()["streams"], {"codec_type": "audio"}]
    assert probe_problems(with_audio, 8.0) == ["1 audio streams"]
    long = good_probe()
    long["format"] = {"duration": "12.0"}
    assert "outside" in probe_problems(long, 12.0)[0]
    assert "asked for" in probe_problems(good_probe(), 7.0)[0]


def test_clips_inside_the_repository_are_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # An empty manifest, so even a broken guard would cut nothing into the repository.
    manifest = tmp_path / "fetched.json"
    manifest.write_text(json.dumps({"items": []}), encoding="utf-8")
    inside = cut_footage.ROOT / "docs" / "video" / "clips-guard-probe"
    try:
        code = cut_footage.main(["--clips", str(inside), "--manifest", str(manifest)])
    finally:
        created = inside.exists()
        if created:
            shutil.rmtree(inside)
    assert code == 1
    assert "outside" in capsys.readouterr().out
    assert not created
