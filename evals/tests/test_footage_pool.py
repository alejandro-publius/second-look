"""The footage pool numbers: a video a person turned down is counted as that, not as the screen."""

from __future__ import annotations

import json
from pathlib import Path

from evals import footage_pool


def test_each_way_a_video_fails_is_its_own_group(tmp_path: Path) -> None:
    (tmp_path / "videos").mkdir()
    (tmp_path / "photos").mkdir()
    (tmp_path / "content").mkdir()
    failed = {
        "https://a": "download failed: sign in to confirm you are not a bot",
        "https://b": "checked by eye: a montage of stock clips, not one creek",
        "https://c": "only 2 of 40 sampled frames show water with no person or text, under 6",
        "https://d": "only 0 of 12 sampled frames show water with no person or text, under 6",
    }
    (tmp_path / "videos" / "failed_videos.json").write_text(json.dumps(failed))
    (tmp_path / "photos" / "manifest.csv").write_text("id,role,scene_id,gold_label\n")
    (tmp_path / "videos" / "manifest.csv").write_text("id,country\n")
    (tmp_path / "content" / "walks.yaml").write_text("walks: []\n")
    doc = footage_pool.build(tmp_path)
    assert doc["videos_failed"] == 4
    assert doc["videos_failed_by_reason"] == {
        "download failed": 1,
        "checked by eye": 1,
        "too few frames passed the screen": 2,
    }
