"""Smaller copies of photos: the two warm-up photos for the landing page and the poster, and one
phone-size copy of every photo of the test for the service worker to keep offline.

Update 22 section 1 answer 2. The same photo with the same framing: each copy is the whole source
scaled down, never cropped, as AVIF and WebP, with no EXIF, XMP or colour profile. Every copy gets
a row in photos/derived/manifest.csv that names its source row and the source's sha256, and
scripts/check_manifest.py checks all of it in CI (hard rule 6). The JPEG originals are not touched.

UPDATE_30 section 1 item 1. The offline copies are made the same way, one AVIF 640 wide of every
warm-up, lesson, practice and test photo, in photos/offline/ with a manifest of the same columns.
Pages never show them while they have a network: the service worker precaches them in place of
the JPEGs, so a first visit downloads about 1.5 MB of photos instead of about 23 MB, and hands a
copy to the page only when a photo cannot be fetched.

Each copy starts at a fixed quality and steps down by 5 until it fits under the byte cap, never
below a floor. The same source and the same Pillow give the same bytes: the AVIF encoder runs on
one thread, because its output changes with the thread count.

    uv run python scripts/derive_photos.py                  write both sets and their manifests
    uv run python scripts/derive_photos.py --set offline    write only the offline copies
    uv run python scripts/derive_photos.py --check          exit 1 if the committed copies differ
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from core.content_loader import (
    DERIVED_COLUMNS,
    DERIVED_DIR,
    DERIVED_MAX_BYTES,
    DERIVED_ROLES,
    OFFLINE_DIR,
    OFFLINE_MAX_BYTES,
    OFFLINE_ROLES,
)

ROOT = Path(__file__).resolve().parents[1]
# The two photos the landing page and the poster show first. Nothing else gets these copies.
SOURCES = ("ph-warmup-03", "ph-warmup-04")
# Never wider than the source. WebP stops at 800: the brook photo is so detailed that a 1200 wide
# WebP stays above the cap until its quality is poor, and WebP is only for browsers without AVIF.
# AVIF has a 660 wide copy for the phones Lighthouse models (412 wide at 1.75x, so 649 pixels at
# 90vw), which otherwise fetch the 800: the same quality, a third fewer bytes (UPDATE_29 4.3).
WIDTHS = {"avif": (480, 660, 800, 1200), "webp": (480, 800)}
START_QUALITY = {"avif": 60, "webp": 75}
FLOOR_QUALITY = {"avif": 40, "webp": 60}
QUALITY_STEP = 5
AVIF_SPEED = 4
# A test photo fills a phone's column, about 360 CSS pixels wide, so 640 is sharp at nearly twice
# that. At quality 50 the 38 copies come to about 1.5 MB, which leaves the pages, their scripts and
# their fonts room under the 3 MB a first visit may download in the background.
OFFLINE_WIDTH = 640


class DeriveError(Exception):
    pass


@dataclass(frozen=True)
class CopySet:
    """One folder of copies: which roles may have them, how wide, and how they are fitted."""

    folder: str
    roles: set[str]
    widths: dict[str, tuple[int, ...]]
    start: dict[str, int]
    floor: dict[str, int]
    max_bytes: int
    why_roles: str = field(default="")


DERIVED = CopySet(
    DERIVED_DIR,
    DERIVED_ROLES,
    WIDTHS,
    START_QUALITY,
    FLOOR_QUALITY,
    DERIVED_MAX_BYTES,
    "copies are for warm-up only",
)
OFFLINE = CopySet(
    OFFLINE_DIR,
    OFFLINE_ROLES,
    {"avif": (OFFLINE_WIDTH,)},
    {"avif": 50},
    {"avif": 30},
    OFFLINE_MAX_BYTES,
    "offline copies are for the photos of the test only",
)
SETS = {"derived": DERIVED, "offline": OFFLINE}


@dataclass(frozen=True)
class Copy:
    file: str
    source_id: str
    source_sha256: str
    data: bytes
    fmt: str
    width: int
    height: int
    quality: int

    def row(self) -> dict[str, str]:
        return {
            "file": self.file,
            "source_id": self.source_id,
            "source_sha256": self.source_sha256,
            "sha256": hashlib.sha256(self.data).hexdigest(),
            "format": self.fmt,
            "width": str(self.width),
            "height": str(self.height),
            "quality": str(self.quality),
            "bytes": str(len(self.data)),
        }


def encode(image: Image.Image, fmt: str, quality: int) -> bytes:
    buffer = io.BytesIO()
    if fmt == "avif":
        image.save(buffer, "AVIF", quality=quality, speed=AVIF_SPEED, max_threads=1)
    elif fmt == "webp":
        image.save(buffer, "WEBP", quality=quality, method=6)
    else:
        raise DeriveError(f"unknown format {fmt}")
    return buffer.getvalue()


def scaled(source: Image.Image, width: int) -> Image.Image:
    """The whole source at this width, same aspect ratio, with nothing carried over but pixels."""
    if width > source.width:
        raise DeriveError(f"{width} is wider than the source ({source.width})")
    height = round(width * source.height / source.width)
    resized = source.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
    # A fresh image from the pixels alone, so no EXIF, XMP or profile rides along from the source.
    return Image.frombytes("RGB", resized.size, resized.tobytes())


def fit(image: Image.Image, fmt: str, max_bytes: int, spec: CopySet = DERIVED) -> tuple[bytes, int]:
    quality = spec.start[fmt]
    while True:
        data = encode(image, fmt, quality)
        if len(data) <= max_bytes:
            return data, quality
        if quality - QUALITY_STEP < spec.floor[fmt]:
            raise DeriveError(
                f"{fmt} at {image.width} wide is {len(data)} bytes at quality {quality}, "
                f"over {max_bytes}, and the floor is {spec.floor[fmt]}"
            )
        quality -= QUALITY_STEP


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_rows(root: Path) -> dict[str, dict[str, str]]:
    with (root / "photos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


def source_rows(root: Path, ids: tuple[str, ...], spec: CopySet = DERIVED) -> list[dict[str, str]]:
    by_id = manifest_rows(root)
    rows = []
    for source_id in ids:
        row = by_id.get(source_id)
        if row is None:
            raise DeriveError(f"no manifest row for {source_id}")
        if row["role"] not in spec.roles:
            raise DeriveError(f"{source_id} is a {row['role']} photo; {spec.why_roles}")
        if sha256_of(root / "photos" / row["file"]) != row["sha256"]:
            raise DeriveError(f"{row['file']} does not match its manifest sha256")
        rows.append(row)
    return rows


def offline_ids(root: Path) -> tuple[str, ...]:
    """Every photo the two-minute test can show: the warm-up, the lesson, practice and the test."""
    return tuple(sorted(i for i, r in manifest_rows(root).items() if r["role"] in OFFLINE_ROLES))


def derive(
    root: Path = ROOT,
    ids: tuple[str, ...] | None = None,
    widths: dict[str, tuple[int, ...]] | None = None,
    max_bytes: int | None = None,
    spec: CopySet = DERIVED,
) -> list[Copy]:
    """Every copy of one set, in memory. Nothing is written."""
    if ids is None:
        ids = SOURCES if spec is DERIVED else offline_ids(root)
    widths = widths or spec.widths
    cap = spec.max_bytes if max_bytes is None else max_bytes
    copies = []
    for row in source_rows(root, ids, spec):
        with Image.open(root / "photos" / row["file"]) as source:
            source.load()
            for fmt, sizes in widths.items():
                for width in sizes:
                    image = scaled(source, width)
                    data, quality = fit(image, fmt, cap, spec)
                    copies.append(
                        Copy(
                            file=f"{spec.folder}/{row['id']}-{width}.{fmt}",
                            source_id=row["id"],
                            source_sha256=row["sha256"],
                            data=data,
                            fmt=fmt,
                            width=image.width,
                            height=image.height,
                            quality=quality,
                        )
                    )
    return sorted(copies, key=lambda c: c.file)


def write(root: Path, copies: list[Copy], folder: str = DERIVED_DIR) -> None:
    target = root / "photos" / folder
    target.mkdir(parents=True, exist_ok=True)
    keep = {Path(c.file).name for c in copies} | {"manifest.csv"}
    for old in target.iterdir():
        if old.is_file() and old.name not in keep:
            old.unlink()
    for c in copies:
        (root / "photos" / c.file).write_bytes(c.data)
    with (target / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DERIVED_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(c.row() for c in copies)


def differences(root: Path, copies: list[Copy]) -> list[str]:
    """What differs between these copies and the committed ones."""
    problems = []
    for c in copies:
        path = root / "photos" / c.file
        if not path.exists():
            problems.append(f"missing: photos/{c.file}")
        elif path.read_bytes() != c.data:
            problems.append(f"differs: photos/{c.file}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare with the committed copies")
    parser.add_argument("--set", choices=["derived", "offline", "both"], default="both")
    args = parser.parse_args(argv)
    names = ["derived", "offline"] if args.set == "both" else [args.set]
    status = 0
    for name in names:
        spec = SETS[name]
        try:
            copies = derive(spec=spec)
        except DeriveError as e:
            print(f"derive-photos: {e}")
            return 1
        if args.check:
            problems = differences(ROOT, copies)
            print("\n".join(problems) or f"derive-photos: {len(copies)} {name} copies match")
            status = status or (1 if problems else 0)
            continue
        write(ROOT, copies, spec.folder)
        for c in copies:
            print(f"{c.file}  {c.width}x{c.height}  q{c.quality}  {len(c.data)} bytes")
        print(
            f"derive-photos: {len(copies)} {name} copies, {sum(len(c.data) for c in copies)} bytes"
        )
    return status


if __name__ == "__main__":
    sys.exit(main())
