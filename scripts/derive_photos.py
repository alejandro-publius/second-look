"""Smaller copies of the two warm-up photos, for the landing page and the poster.

Update 22 section 1 answer 2. The same photo with the same framing: each copy is the whole source
scaled down, never cropped, as AVIF and WebP, with no EXIF, XMP or colour profile. Every copy gets
a row in photos/derived/manifest.csv that names its source row and the source's sha256, and
scripts/check_manifest.py checks all of it in CI (hard rule 6). The JPEG originals are not touched.

Each copy starts at a fixed quality and steps down by 5 until it fits under the byte cap, never
below a floor. The same source and the same Pillow give the same bytes: the AVIF encoder runs on
one thread, because its output changes with the thread count.

    uv run python scripts/derive_photos.py          write the copies and their manifest
    uv run python scripts/derive_photos.py --check  exit 1 if the committed copies differ
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from core.content_loader import DERIVED_COLUMNS, DERIVED_DIR, DERIVED_MAX_BYTES, DERIVED_ROLES

ROOT = Path(__file__).resolve().parents[1]
# The two photos the landing page and the poster show first. Nothing else gets copies.
SOURCES = ("ph-warmup-03", "ph-warmup-04")
# Never wider than the source. WebP stops at 800: the brook photo is so detailed that a 1200 wide
# WebP stays above the cap until its quality is poor, and WebP is only for browsers without AVIF.
WIDTHS = {"avif": (480, 800, 1200), "webp": (480, 800)}
START_QUALITY = {"avif": 60, "webp": 75}
FLOOR_QUALITY = {"avif": 40, "webp": 60}
QUALITY_STEP = 5
AVIF_SPEED = 4


class DeriveError(Exception):
    pass


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


def fit(image: Image.Image, fmt: str, max_bytes: int) -> tuple[bytes, int]:
    quality = START_QUALITY[fmt]
    while True:
        data = encode(image, fmt, quality)
        if len(data) <= max_bytes:
            return data, quality
        if quality - QUALITY_STEP < FLOOR_QUALITY[fmt]:
            raise DeriveError(
                f"{fmt} at {image.width} wide is {len(data)} bytes at quality {quality}, "
                f"over {max_bytes}, and the floor is {FLOOR_QUALITY[fmt]}"
            )
        quality -= QUALITY_STEP


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_rows(root: Path, ids: tuple[str, ...]) -> list[dict[str, str]]:
    with (root / "photos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        by_id = {row["id"]: row for row in csv.DictReader(f)}
    rows = []
    for source_id in ids:
        row = by_id.get(source_id)
        if row is None:
            raise DeriveError(f"no manifest row for {source_id}")
        if row["role"] not in DERIVED_ROLES:
            raise DeriveError(f"{source_id} is a {row['role']} photo; copies are for warm-up only")
        if sha256_of(root / "photos" / row["file"]) != row["sha256"]:
            raise DeriveError(f"{row['file']} does not match its manifest sha256")
        rows.append(row)
    return rows


def derive(
    root: Path = ROOT,
    ids: tuple[str, ...] = SOURCES,
    widths: dict[str, tuple[int, ...]] | None = None,
    max_bytes: int = DERIVED_MAX_BYTES,
) -> list[Copy]:
    """Every copy, in memory. Nothing is written."""
    widths = widths or WIDTHS
    copies = []
    for row in source_rows(root, ids):
        with Image.open(root / "photos" / row["file"]) as source:
            source.load()
            for fmt, sizes in widths.items():
                for width in sizes:
                    image = scaled(source, width)
                    data, quality = fit(image, fmt, max_bytes)
                    copies.append(
                        Copy(
                            file=f"{DERIVED_DIR}/{row['id']}-{width}.{fmt}",
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


def write(root: Path, copies: list[Copy]) -> None:
    folder = root / "photos" / DERIVED_DIR
    folder.mkdir(parents=True, exist_ok=True)
    keep = {Path(c.file).name for c in copies} | {"manifest.csv"}
    for old in folder.iterdir():
        if old.is_file() and old.name not in keep:
            old.unlink()
    for c in copies:
        (root / "photos" / c.file).write_bytes(c.data)
    with (folder / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
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
    args = parser.parse_args(argv)
    try:
        copies = derive()
    except DeriveError as e:
        print(f"derive-photos: {e}")
        return 1
    if args.check:
        problems = differences(ROOT, copies)
        print("\n".join(problems) or f"derive-photos: {len(copies)} copies match")
        return 1 if problems else 0
    write(ROOT, copies)
    for c in copies:
        print(f"{c.file}  {c.width}x{c.height}  q{c.quality}  {len(c.data)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
