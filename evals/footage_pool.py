"""The footage pool as it really is: searched, screened, kept, and the walks built from it.

No model is involved in any number here, so the file is real, not synthetic, and the README may
cite it (hard rule 12). Reads videos/candidates.json, videos/failed_videos.json,
videos/frames.json, photos/manifest.csv and content/walks.yaml.

Run: uv run python evals/footage_pool.py     writes results/footage_pool.json
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "footage_pool.json"


def reason_group(reason: str) -> str:
    """The first words of a drop reason, so "person: vision found 1 people" counts as person."""
    for key in ("person", "text on screen", "plate or number", "blank", "no water", "near dupl"):
        if reason.startswith(key):
            return {"near dupl": "near duplicate", "text on screen": "text on screen"}.get(key, key)
    return "other"


def build(root: Path = ROOT) -> dict[str, Any]:
    def load(rel: str, default: Any) -> Any:
        path = root / rel
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

    candidates = load("videos/candidates.json", [])
    failed = load("videos/failed_videos.json", {})
    frames = load("videos/frames.json", {"per_video": []})
    with (root / "photos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("role") == "benchmark"]
    with (root / "videos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        videos = {r["id"]: r for r in csv.DictReader(f)}
    walks_path = root / "content" / "walks.yaml"
    walks = (yaml.safe_load(walks_path.read_text(encoding="utf-8")) or {}).get("walks", [])

    kept_videos = sorted({r["scene_id"].removeprefix("video-") for r in rows})
    countries = sorted(
        {videos[v]["country"] for v in kept_videos if videos.get(v, {}).get("country")}
    )
    drops: Counter[str] = Counter()
    for v in frames.get("per_video", []):
        for d in v.get("dropped", []):
            drops[reason_group(d["reason"])] += 1
    failed_reasons: Counter[str] = Counter(
        "download failed" if why.startswith("download") else "too few frames passed the screen"
        for why in failed.values()
    )
    return {
        "real": True,
        "synthetic": False,
        "script": "evals/footage_pool.py",
        "candidates": len(candidates),
        "videos_failed": len(failed),
        "videos_failed_by_reason": dict(failed_reasons),
        "videos_kept": len(kept_videos),
        "frames_kept": len(rows),
        "frames_labelled": sum(1 for r in rows if r.get("gold_label")),
        "frames_unlabelled": sum(1 for r in rows if not r.get("gold_label")),
        "countries_kept": len(countries),
        "country_names": countries,
        "frames_dropped_in_last_cut": dict(drops.most_common()),
        "walks": len(walks),
        "walk_countries": sorted({w["country"] for w in walks}),
        "walks_with_a_checker_question": sum(1 for w in walks if w["checker"]["question"]),
    }


def main() -> int:
    doc = build()
    OUT.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"footage-pool: {doc['candidates']} candidates, {doc['videos_kept']} videos kept from "
        f"{doc['countries_kept']} countries, {doc['frames_kept']} frames, {doc['walks']} walks"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
