"""Every image under photos/ must have a manifest row with a matching sha256 (hard rule 6)."""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from core import content_loader

ROOT = Path(__file__).resolve().parents[1]
# One list with core/content_loader.py, so an image type one of them skips cannot hide here.
IMAGE_SUFFIXES = content_loader.IMAGE_SUFFIXES
DERIVED_DIR = content_loader.DERIVED_DIR
DERIVED_FORMATS = {".avif": ("avif", "AVIF"), ".webp": ("webp", "WEBP")}
OFFLINE_DIR = content_loader.OFFLINE_DIR
# One small AVIF per photo: the smallest format, and every browser that runs the site shows it.
OFFLINE_FORMATS = {".avif": ("avif", "AVIF")}
# What a smaller copy may not carry. The AVIF colour box (colr, nclx) is not on the list: it says
# how to decode the colours, and it names nothing and no one.
METADATA_KEYS = ("exif", "xmp", "XML:com.adobe.xmp", "icc_profile", "comment")
# Same picture, same framing: the copy and its source, both grey and 64 pixels wide, differ by
# at most this much on average (0 to 255). The real copies differ by under 2; cropping 2 per cent
# off each edge already gives 9, and a mirror image over 40.
SAME_PICTURE_MAX_DIFF = 4.0
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
# Laid stone keeps out of the test set. The official app gives it a bank type of its own, the
# River Habitat Survey calls it reinforcement, and content/form.yaml calls none of the three
# natural, so a laid stone photo has no single right answer to mark. It is fine in a lesson,
# where the caption can say so. These are the words a source uses for it.
LAID_STONE = (
    "riprap",
    "rip-rap",
    "rip rap",
    "gabion",
    "laid stone",
    "laid stones",
    "stone pitching",
    "pitched stone",
    "rock armour",
    "rock armor",
    "dry stone",
    "drystone",
)
# One source of truth: core/content_loader.py. A second copy drifted once already.
LICENSE_ALLOWLIST = content_loader.LICENSE_ALLOWLIST


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _thumb(image: Image.Image, size: tuple[int, int] | None = None) -> Image.Image:
    grey = image.convert("L")
    return grey.resize(size or (64, round(64 * grey.height / grey.width)), Image.Resampling.BOX)


def picture_difference(copy: Image.Image, source: Image.Image) -> float:
    """Mean grey difference between two small thumbnails. Near 0 means the same framing."""
    a = _thumb(source)
    b = _thumb(copy, a.size)
    return float(ImageStat.Stat(ImageChops.difference(a, b)).mean[0])


# The folders of copies: the smaller copies the landing page shows (Update 22) and the phone-size
# copies the test uses offline (UPDATE_30).
COPY_FOLDERS = (DERIVED_DIR, OFFLINE_DIR)


def copy_rules(folder: str) -> tuple[set[str], int, dict[str, tuple[str, str]]]:
    """A folder's roles, byte cap and formats, read when asked so a test can change them."""
    if folder == DERIVED_DIR:
        return content_loader.DERIVED_ROLES, content_loader.DERIVED_MAX_BYTES, DERIVED_FORMATS
    return content_loader.OFFLINE_ROLES, content_loader.OFFLINE_MAX_BYTES, OFFLINE_FORMATS


def check_derived(root: Path, by_id: dict[str, dict[str, str]], images: list[Path]) -> list[str]:
    """Every smaller copy traces to a manifest row and its sha256, and is what its row says."""
    return check_copies(root, by_id, images, DERIVED_DIR)


def check_copies(
    root: Path, by_id: dict[str, dict[str, str]], images: list[Path], folder: str
) -> list[str]:
    """The copies in photos/<folder>/ against that folder's manifest, its roles and its cap."""
    roles, max_bytes, formats = copy_rules(folder)
    problems: list[str] = []
    rows = content_loader.copy_rows(root, folder)
    if rows:
        missing_cols = [c for c in content_loader.DERIVED_COLUMNS if c not in rows[0]]
        if missing_cols:
            return [f"photos/{folder}/manifest.csv missing columns: {missing_cols}"]
    by_file = {row["file"]: row for row in rows}
    for img in images:
        rel = img.relative_to(root / "photos").as_posix()
        row = by_file.get(rel)
        if row is None:
            problems.append(f"no {folder} manifest row: photos/{rel}")
            continue
        source = by_id.get(row["source_id"])
        if source is None:
            problems.append(f"copy of a photo with no manifest row: photos/{rel}")
            continue
        if row["source_sha256"] != source["sha256"]:
            problems.append(f"copy of another version of {source['file']}: photos/{rel}")
        if source["role"] not in roles:
            problems.append(f"copy of a {source['role']} photo: photos/{rel}")
        if row["sha256"] != sha256_of(img):
            problems.append(f"sha256 mismatch: photos/{rel}")
        size = img.stat().st_size
        if row["bytes"] != str(size):
            problems.append(f"byte count mismatch: photos/{rel}")
        if size > max_bytes:
            problems.append(f"copy over {max_bytes} bytes: photos/{rel} ({size})")
        fmt, pil_format = formats.get(img.suffix.lower(), ("", ""))
        if rel != f"{folder}/{row['source_id']}-{row['width']}.{fmt}":
            problems.append(f"copy not named <source id>-<width>.<format>: photos/{rel}")
        source_path = root / "photos" / source["file"]
        if not source_path.exists():
            continue
        with Image.open(img) as copy, Image.open(source_path) as original:
            if copy.format != pil_format or row["format"] != fmt:
                problems.append(f"format is not {row['format']}: photos/{rel}")
            if [str(copy.width), str(copy.height)] != [row["width"], row["height"]]:
                problems.append(f"size is not {row['width']}x{row['height']}: photos/{rel}")
            if copy.width > original.width:
                problems.append(f"copy wider than its source: photos/{rel}")
            if abs(copy.height - copy.width * original.height / original.width) > 1:
                problems.append(f"copy changes the aspect ratio of its source: photos/{rel}")
            carried = [k for k in METADATA_KEYS if copy.info.get(k)]
            if carried or len(copy.getexif()):
                problems.append(f"copy carries metadata: photos/{rel} ({carried or ['exif']})")
            diff = picture_difference(copy, original)
            if diff > SAME_PICTURE_MAX_DIFF:
                problems.append(
                    f"copy is not the whole source picture: photos/{rel} (differs by {diff:.1f})"
                )
    for rel in by_file:
        if not (root / "photos" / rel).exists():
            problems.append(f"{folder} manifest row without file: photos/{rel}")
    return problems


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
    # Smaller copies answer to their own manifest, which names the source row.
    by_id = {row["id"]: row for row in rows if row.get("id")}
    derived: list[Path] = []
    for folder in COPY_FOLDERS:
        copies = [p for p in images if p.relative_to(root / "photos").parts[0] == folder]
        problems.extend(check_copies(root, by_id, copies, folder))
        derived.extend(copies)
    for img in images:
        if img in derived:
            continue
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
        # For a plant we say is there, the species has to be on the Cal-IPC inventory, with the
        # link. A plant photo labelled absent says no listed species is in it, so there is no
        # profile page to point at and none is asked for (Update 11b step 6).
        if row["role"] == "test":
            words = f"{row.get('notes', '')} {evidence}".lower()
            found = sorted({w for w in LAID_STONE if w in words})
            if found:
                problems.append(f"laid stone named on a test photo: photos/{rel} ({found})")
        plant_present = row["feature"] == "invasive_plant" and row["gold_label"] != "absent"
        if plant_present and evidence and CAL_IPC not in evidence:
            problems.append(f"label_evidence has no Cal-IPC link: photos/{rel}")
    for rel in by_file:
        if not (root / "photos" / rel).exists():
            problems.append(f"manifest row without file: photos/{rel}")
    if problems:
        print("\n".join(problems))
        print(f"manifest-check: {len(problems)} problem(s)")
        return 1
    print(
        f"manifest-check: {len(images) - len(derived)} image(s) and {len(derived)} smaller "
        "copies, all with matching rows"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
