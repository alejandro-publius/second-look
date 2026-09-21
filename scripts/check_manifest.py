"""Every image under photos/ must have a manifest row with a matching sha256 (hard rule 6)."""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
REQUIRED_COLUMNS = [
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
    "label_evidence",
]
CAL_IPC = "cal-ipc.org"
LICENSE_ALLOWLIST = {
    "CC0-1.0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "public-domain",
    "own-CC-BY-4.0",
    "placeholder",
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main(root: Path = ROOT) -> int:
    problems: list[str] = []
    manifest = root / "photos" / "manifest.csv"
    if not manifest.exists():
        print("manifest-check: photos/manifest.csv missing")
        return 1
    with manifest.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        rows = list(reader)
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in columns]
    if missing_cols:
        problems.append(f"manifest missing columns: {missing_cols}")
    by_file = {row["file"]: row for row in rows if row.get("file")}
    images = [p for p in (root / "photos").rglob("*") if p.suffix.lower() in IMAGE_SUFFIXES]
    for img in images:
        rel = str(img.relative_to(root / "photos"))
        row = by_file.get(rel)
        if row is None:
            problems.append(f"no manifest row: photos/{rel}")
            continue
        if row["sha256"] != sha256_of(img):
            problems.append(f"sha256 mismatch: photos/{rel}")
        if row["license"] not in LICENSE_ALLOWLIST:
            problems.append(f"license not on allowlist: photos/{rel} ({row['license']})")
        if row["synthetic"].strip().lower() not in {"false", "0", ""}:
            problems.append(f"synthetic must be false: photos/{rel}")
        if row["faces"].strip().lower() not in {"false", "0", ""}:
            problems.append(f"faces must be false: photos/{rel}")
        evidence = row.get("label_evidence", "").strip()
        # A photo from someone else's collection has to say where the source itself supports the
        # label: a research grade identification, a caption, a category (Update 09 section 1).
        if row["source_url"].strip() and row["license"] != "placeholder" and not evidence:
            problems.append(f"label_evidence is empty on a photo from a source: photos/{rel}")
        # For a plant, the species has to be on the Cal-IPC inventory, with the link.
        if row["feature"] == "invasive_plant" and evidence and CAL_IPC not in evidence:
            problems.append(f"label_evidence has no Cal-IPC link: photos/{rel}")
    for rel in by_file:
        if not (root / "photos" / rel).exists():
            problems.append(f"manifest row without file: photos/{rel}")
    if problems:
        print("\n".join(problems))
        print(f"manifest-check: {len(problems)} problem(s)")
        return 1
    print(f"manifest-check: {len(images)} image(s), all with matching rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
