"""The counts behind docs/DATA_CARD.md: what the photo and footage sets hold and what is labelled.

No model is involved in any number here. Every count is read from the committed manifests, so the
file is real, not synthetic, and the data card may cite it (hard rule 12). Reads
photos/manifest.csv, videos/manifest.csv and docs/video/footage.csv.

Run: uv run python evals/data_card.py            writes results/data_card.json
     uv run python evals/data_card.py --check    fails unless the committed file is what it writes
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "data_card.json"
ROLES = ("test", "lesson", "practice", "warmup", "benchmark")
HOSTS = {
    "commons.wikimedia.org": "Wikimedia Commons",
    "www.inaturalist.org": "iNaturalist",
    "www.youtube.com": "YouTube",
}


def source_of(url: str) -> str:
    """The collection a file came from, by the host of its source page."""
    host = urlparse(url.strip()).netloc.lower()
    return HOSTS.get(host, host or "unknown")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def counted(values: list[str]) -> dict[str, int]:
    """A Counter as a plain dict with sorted keys, so the file is the same run after run."""
    return dict(sorted(Counter(values).items()))


def is_yes(value: str | None) -> bool:
    return (value or "").strip().lower() in {"true", "yes", "1"}


def role_block(rows: list[dict[str, str]]) -> dict[str, Any]:
    labelled = [r for r in rows if r.get("gold_label", "").strip()]
    per_feature: dict[str, dict[str, int]] = {}
    for r in labelled:
        cell = per_feature.setdefault(r.get("feature", "").strip() or "none", {})
        label = r["gold_label"].strip()
        cell[label] = cell.get(label, 0) + 1
    return {
        "rows": len(rows),
        "labelled": len(labelled),
        "unlabelled": len(rows) - len(labelled),
        "present": sum(1 for r in labelled if r["gold_label"].strip() == "present"),
        "absent": sum(1 for r in labelled if r["gold_label"].strip() == "absent"),
        "per_feature": dict(sorted(per_feature.items())),
        "by_source": counted([source_of(r.get("source_url", "")) for r in rows]),
        "by_licence": counted([r.get("license", "").strip() for r in rows]),
    }


def build(root: Path = ROOT) -> dict[str, Any]:
    photos = read_csv(root / "photos" / "manifest.csv")
    videos = read_csv(root / "videos" / "manifest.csv")
    film = read_csv(root / "docs" / "video" / "footage.csv")
    roles = {role: role_block([r for r in photos if r.get("role") == role]) for role in ROLES}
    other = sorted({r.get("role", "") for r in photos} - set(ROLES))
    return {
        "real": True,
        "synthetic": False,
        "script": "evals/data_card.py",
        "photos": {
            "rows": len(photos),
            "labelled": sum(1 for r in photos if r.get("gold_label", "").strip()),
            "with_label_evidence": sum(1 for r in photos if r.get("label_evidence", "").strip()),
            "with_second_label": sum(1 for r in photos if r.get("labeller_2", "").strip()),
            "marked_synthetic": sum(1 for r in photos if is_yes(r.get("synthetic"))),
            "marked_with_faces": sum(1 for r in photos if is_yes(r.get("faces"))),
            "by_source": counted([source_of(r.get("source_url", "")) for r in photos]),
            "by_licence": counted([r.get("license", "").strip() for r in photos]),
            "other_roles": other,
            **roles,
        },
        "videos": {
            "rows": len(videos),
            "labelled": sum(1 for r in videos if r.get("label_value", "").strip()),
            "countries": len({r.get("country", "").strip() for r in videos} - {""}),
            "by_source": counted([source_of(r.get("source_url", "")) for r in videos]),
            "by_licence": counted([r.get("license", "").strip() for r in videos]),
        },
        "film_footage": {
            "rows": len(film),
            "by_kind": counted([r.get("kind", "").strip() for r in film]),
            "by_source": counted([source_of(r.get("source_page", "")) for r in film]),
            "by_licence": counted([r.get("licence", "").strip() for r in film]),
        },
    }


def dumps(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if results/ is out of date")
    args = parser.parse_args(argv)
    text = dumps(build())
    if args.check:
        now = OUT.read_text(encoding="utf-8") if OUT.is_file() else ""
        if now != text:
            print("data-card: results/data_card.json is out of date; run evals/data_card.py")
            return 1
        print("data-card: results/data_card.json matches the manifests")
        return 0
    OUT.write_text(text, encoding="utf-8")
    doc = json.loads(text)
    print(
        f"data-card: {doc['photos']['rows']} photo rows, {doc['photos']['labelled']} labelled, "
        f"{doc['videos']['rows']} videos, {doc['film_footage']['rows']} film clips and photos"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
