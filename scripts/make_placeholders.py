"""Generate labelled gray placeholder images and their manifest rows (hard rule 6).

Not photos. Each block says PLACEHOLDER, its id, role and feature in large text, so no one can
mistake it for a creek. Preflight fails while any of these sit in a test, lesson, practice or
warm-up slot. Run: uv run python scripts/make_placeholders.py
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw

from core.records import FEATURES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "photos" / "placeholders"
MANIFEST = ROOT / "photos" / "manifest.csv"
COLUMNS = [
    "id",
    "file",
    "sha256",
    "source_url",
    "author",
    "license",
    "capture_date",
    "coarse_location",
    "scene_id",
    "role",
    "feature",
    "gold_label",
    "labeller_2",
    "synthetic",
    "faces",
    "notes",
]


def plan() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    n = 0
    for feature in FEATURES:
        for gold in ("present", "present", "absent", "absent"):
            n += 1
            rows.append(
                {"id": f"ph-test-{n:02d}", "role": "test", "feature": feature, "gold_label": gold}
            )
    for feature in FEATURES:
        for pair in ("a", "b"):
            for side, gold in (("1", "absent"), ("2", "present")):
                rows.append(
                    {
                        "id": f"ph-lesson-{feature}-{pair}{side}",
                        "role": "lesson",
                        "feature": feature,
                        "gold_label": gold,
                    }
                )
        rows.append(
            {
                "id": f"ph-practice-{feature}",
                "role": "practice",
                "feature": feature,
                "gold_label": "present",
            }
        )
    rows.append({"id": "ph-warmup-01", "role": "warmup", "feature": "", "gold_label": ""})
    rows.append({"id": "ph-warmup-02", "role": "warmup", "feature": "", "gold_label": ""})
    rows.append({"id": "ph-spare-01", "role": "benchmark", "feature": "", "gold_label": ""})
    rows.append({"id": "ph-spare-02", "role": "benchmark", "feature": "", "gold_label": ""})
    return rows


def draw(path: Path, row: dict[str, str]) -> None:
    img = Image.new("RGB", (1200, 900), (128, 128, 128))
    d = ImageDraw.Draw(img)
    lines = [
        "PLACEHOLDER",
        "not a photo",
        row["id"],
        f"role: {row['role']}",
        f"feature: {row['feature'] or 'none'}",
    ]
    y = 120
    for i, line in enumerate(lines):
        size = 96 if i == 0 else 56
        d.text((80, y), line, fill=(30, 30, 30), font_size=size)
        y += size + 40
    d.rectangle([(20, 20), (1179, 879)], outline=(60, 60, 60), width=8)
    img.save(path, "JPEG", quality=80)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows_out: list[dict[str, str]] = []
    for i, row in enumerate(plan(), 1):
        file = OUT / f"{row['id']}.jpg"
        draw(file, row)
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        rows_out.append(
            {
                "id": row["id"],
                "file": f"placeholders/{row['id']}.jpg",
                "sha256": digest,
                "source_url": "",
                "author": "Second Look (generated gray placeholder)",
                "license": "placeholder",
                "capture_date": "",
                "coarse_location": "",
                "scene_id": f"placeholder-{i:02d}",
                "role": row["role"],
                "feature": row["feature"],
                "gold_label": row["gold_label"],
                "labeller_2": "",
                "synthetic": "false",
                "faces": "false",
                "notes": "gray block until a real photo lands",
            }
        )
    with MANIFEST.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows_out)
    print(f"wrote {len(rows_out)} placeholders and manifest rows")


if __name__ == "__main__":
    main()
