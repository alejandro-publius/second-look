"""Turn a folder of originals plus a labels CSV into EXIF-free, resized JPEGs with manifest rows.

Run: uv run python scripts/ingest_photos.py --originals ~/Downloads/rachel --labels labels.csv \
        --batch rachel1

In: originals (JPEG, PNG, HEIC) and a CSV with columns photo_file, role, feature, gold_label,
scene_id, capture_date, coarse_location, author, license, source_url (notes optional).
Out: photos/<batch>/ph-<batch>-<nn>.jpg, 1600 px on the long side, no EXIF, no ICC, no comments;
rows appended to photos/manifest.csv with the sha256 computed after processing; the originals
copied to data/originals/<batch>/ (gitignored). Originals never land under photos/.

Everything is checked before anything is written. A resulting photo marked synthetic or faces
true stops the whole run (hard rule 6).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from core.content_loader import REAL_LICENSES, ROLES
from core.records import FEATURES

ROOT = Path(__file__).resolve().parents[1]
LONG_SIDE = 1600
JPEG_QUALITY = 85
LABEL_COLUMNS = [
    "photo_file",
    "role",
    "feature",
    "gold_label",
    "scene_id",
    "capture_date",
    "coarse_location",
    "author",
    "license",
    "source_url",
]
MANIFEST_COLUMNS = [
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
GOLD_VALUES = {"present", "absent", "ambiguous", ""}
HEIC_SUFFIXES = {".heic", ".heif"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"} | HEIC_SUFFIXES
BATCH_RE = re.compile(r"^[a-z0-9]{1,20}$")
EXIF_MARKER = b"Exif\x00\x00"


class IngestError(Exception):
    """Every problem found, joined by newlines. Nothing was written."""


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() not in {"", "false", "0", "no"}


def read_labels(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        missing = [c for c in LABEL_COLUMNS if c not in columns]
        if missing:
            raise IngestError(f"labels CSV is missing columns: {missing}")
        return [{k: (v or "").strip() for k, v in row.items() if k} for row in reader]


def check_labels(rows: list[dict[str, str]], originals: Path) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    if not rows:
        problems.append("labels CSV has no rows")
    for n, row in enumerate(rows, 2):
        where = f"labels row {n} ({row.get('photo_file') or 'no file'})"
        file = row["photo_file"]
        if not file:
            problems.append(f"{where}: photo_file is empty")
        elif file in seen:
            problems.append(f"{where}: photo_file listed twice")
        else:
            seen.add(file)
            src = originals / file
            if not src.is_file():
                problems.append(f"{where}: file not found under {originals}")
            elif src.suffix.lower() not in IMAGE_SUFFIXES:
                problems.append(f"{where}: not a JPEG, PNG or HEIC")
        if row["role"] not in ROLES:
            problems.append(f"{where}: role must be one of {sorted(ROLES)}")
        if row["feature"] and row["feature"] not in FEATURES:
            problems.append(f"{where}: feature must be one of {list(FEATURES)} or empty")
        if row["role"] in {"test", "lesson", "practice"} and not row["feature"]:
            problems.append(f"{where}: a {row['role']} photo needs a feature")
        if row["gold_label"] not in GOLD_VALUES:
            problems.append(f"{where}: gold_label must be present, absent, ambiguous or empty")
        if row["license"] not in REAL_LICENSES:
            problems.append(f"{where}: license must be one of {sorted(REAL_LICENSES)}")
        if not row["scene_id"]:
            problems.append(f"{where}: scene_id is empty (same spot, same day is one scene)")
        if not row["author"]:
            problems.append(f"{where}: author is empty")
        if _truthy(row.get("synthetic")):
            problems.append(f"{where}: marked synthetic; no AI images anywhere (hard rule 6)")
        if _truthy(row.get("faces")):
            problems.append(f"{where}: marked faces; no faces anywhere (hard rule 6)")
    return problems


def read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def open_original(src: Path) -> Image.Image:
    """Open a JPEG, PNG or HEIC. HEIC needs pillow_heif, or sips on a Mac."""
    if src.suffix.lower() not in HEIC_SUFFIXES:
        return Image.open(src)
    try:
        import pillow_heif  # noqa: PLC0415

        pillow_heif.register_heif_opener()
        return Image.open(src)
    except ImportError:
        pass
    if sys.platform == "darwin" and shutil.which("sips"):
        tmp = Path(tempfile.mkdtemp(prefix="ingest-heic-")) / (src.stem + ".jpg")
        subprocess.run(
            ["sips", "-s", "format", "jpeg", str(src), "--out", str(tmp)],
            check=True,
            capture_output=True,
        )
        img = Image.open(tmp)
        img.load()
        return img
    raise IngestError(
        f"Cannot read {src.name}: HEIC needs the pillow_heif package or a Mac with sips."
    )


def clean_copy(img: Image.Image) -> Image.Image:
    """Upright pixels only. A fresh image built from raw bytes carries no EXIF, ICC or comments."""
    upright = ImageOps.exif_transpose(img) or img
    rgb = upright.convert("RGB")
    clean = Image.frombytes("RGB", rgb.size, rgb.tobytes())
    if max(clean.size) > LONG_SIDE:
        clean.thumbnail((LONG_SIDE, LONG_SIDE), Image.Resampling.LANCZOS)
    return clean


def assert_no_metadata(path: Path) -> None:
    data = path.read_bytes()
    if EXIF_MARKER in data:
        raise IngestError(f"{path.name} still carries an EXIF segment after processing")
    with Image.open(path) as img:
        if dict(img.getexif()):
            raise IngestError(f"{path.name} still has EXIF tags after processing")
        leaked = {
            k for k in img.info if k in {"exif", "icc_profile", "xmp", "comment", "photoshop"}
        }
        if leaked:
            raise IngestError(f"{path.name} still carries {sorted(leaked)} after processing")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def next_number(existing_ids: set[str], batch: str) -> int:
    prefix = f"ph-{batch}-"
    numbers = [
        int(i[len(prefix) :])
        for i in existing_ids
        if i.startswith(prefix) and i[len(prefix) :].isdigit()
    ]
    return max(numbers, default=0) + 1


def ingest(originals: Path, labels: Path, batch: str, root: Path = ROOT) -> list[dict[str, str]]:
    """Do the whole job. Returns the manifest rows written. Raises IngestError, writes nothing."""
    root = root.resolve()
    originals = originals.resolve()
    photos_dir = root / "photos"
    manifest = photos_dir / "manifest.csv"
    problems: list[str] = []
    if not BATCH_RE.match(batch):
        problems.append("batch must be 1 to 20 lowercase letters or digits, for example rachel1")
    if not originals.is_dir():
        problems.append(f"originals folder not found: {originals}")
    if originals == photos_dir or photos_dir in originals.parents:
        problems.append("originals must not sit under photos/; they never enter the repo")
    if not labels.is_file():
        problems.append(f"labels CSV not found: {labels}")
    if problems:
        raise IngestError("\n".join(problems))
    rows = read_labels(labels)
    problems = check_labels(rows, originals)
    existing = read_manifest(manifest)
    existing_ids = {r["id"] for r in existing}
    existing_files = {r["file"] for r in existing}
    if problems:
        raise IngestError("\n".join(problems))

    out_rows: list[dict[str, str]] = []
    n = next_number(existing_ids, batch)
    with tempfile.TemporaryDirectory(prefix="ingest-") as tmp:
        staged: list[tuple[Path, Path, Path]] = []
        for row in rows:
            photo_id = f"ph-{batch}-{n:02d}"
            rel = f"{batch}/{photo_id}.jpg"
            if photo_id in existing_ids or rel in existing_files:
                raise IngestError(f"id {photo_id} or file {rel} already in the manifest")
            n += 1
            src = originals / row["photo_file"]
            staged_file = Path(tmp) / f"{photo_id}.jpg"
            with open_original(src) as img:
                clean_copy(img).save(staged_file, "JPEG", quality=JPEG_QUALITY, optimize=True)
            assert_no_metadata(staged_file)
            staged.append((src, staged_file, photos_dir / rel))
            out_rows.append(
                {
                    "id": photo_id,
                    "file": rel,
                    "sha256": sha256_of(staged_file),
                    "source_url": row["source_url"],
                    "author": row["author"],
                    "license": row["license"],
                    "capture_date": row["capture_date"],
                    "coarse_location": row["coarse_location"],
                    "scene_id": row["scene_id"],
                    "role": row["role"],
                    "feature": row["feature"],
                    "gold_label": row["gold_label"],
                    "labeller_2": "",
                    "synthetic": "false",
                    "faces": "false",
                    "notes": row.get("notes", ""),
                }
            )
        # Every conversion worked. Now, and only now, write.
        (photos_dir / batch).mkdir(parents=True, exist_ok=True)
        keep = root / "data" / "originals" / batch
        keep.mkdir(parents=True, exist_ok=True)
        for src, staged_file, dest in staged:
            shutil.move(str(staged_file), dest)
            shutil.copy2(src, keep / src.name)
    write_header = not manifest.exists()
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerows(out_rows)
    return out_rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--originals", type=Path, required=True, help="folder of originals")
    parser.add_argument("--labels", type=Path, required=True, help="labels CSV")
    parser.add_argument("--batch", required=True, help="short lowercase name, e.g. rachel1")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        rows: list[dict[str, Any]] = ingest(args.originals, args.labels, args.batch, args.root)
    except IngestError as e:
        print("ingest: refused, nothing written:")
        print(e)
        return 1
    for row in rows:
        gold = row["gold_label"] or ""
        print(f"  {row['id']}  {row['role']:9} {row['feature']:16} {gold:9} photos/{row['file']}")
    ambiguous = sum(1 for r in rows if r["gold_label"] == "ambiguous")
    print(
        f"ingest: {len(rows)} photos into photos/{args.batch}/, {len(rows)} manifest rows "
        f"appended, originals kept in data/originals/{args.batch}/ (gitignored)"
    )
    if ambiguous:
        print(
            f"ingest: {ambiguous} labelled ambiguous; settle or remove them before the key freezes"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
