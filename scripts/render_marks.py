"""Draw every approved mark on its lesson photo, one image per photo, for checking at a glance.

Run: uv run python scripts/render_marks.py

Out: docs/screens/marks/<photo_id>.jpg, the lesson photo with a numbered dot at each mark and
the labels listed under it. Nothing here is served to anyone: the app draws its own marks from
the lesson file. This is a contact sheet for a person reviewing what was approved (Update 11D).

It refuses to run if a mark sits outside the photo or has no label, because then the picture
would not show what the lesson file says.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from scripts import label_photos

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("docs") / "screens" / "marks"
WIDTH = 1000
DOT = 16
STRIP = 34  # one label line under the photo
INK = (17, 17, 17)
PAPER = (255, 255, 255)
DOT_FILL = (214, 69, 44)
DOT_EDGE = (255, 255, 255)
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


class RenderError(Exception):
    """A mark the picture could not honestly show. Nothing was written."""


def font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def manifest_files(root: Path) -> dict[str, str]:
    with (root / "photos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        return {row["id"]: row["file"] for row in csv.DictReader(f)}


def render(root: Path = ROOT) -> list[Path]:
    files = manifest_files(root)
    small, bold = font(19), font(21)
    written: list[Path] = []
    out_dir = root / OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    for target in label_photos.load_mark_targets(root):
        lesson = label_photos.load_lesson(label_photos.lesson_path(root, target.feature))
        marks = label_photos.read_marks(lesson, target)
        rel = files.get(target.photo_id)
        if rel is None:
            raise RenderError(f"{target.photo_id} has marks but no manifest row")
        with Image.open(root / "photos" / rel) as img:
            photo = img.convert("RGB")
        scale = WIDTH / photo.width
        photo = photo.resize((WIDTH, round(photo.height * scale)), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (WIDTH, photo.height + STRIP * (len(marks) + 1)), PAPER)
        canvas.paste(photo, (0, 0))
        draw = ImageDraw.Draw(canvas)
        for n, mark in enumerate(marks, 1):
            x, y, label = float(mark["x"]), float(mark["y"]), str(mark.get("label") or "")
            if not 0.0 <= x <= 1.0 or not 0.0 <= y <= 1.0:
                raise RenderError(f"{target.photo_id} mark {n} sits outside the photo")
            if not label:
                raise RenderError(f"{target.photo_id} mark {n} has no label")
            px, py = x * WIDTH, y * photo.height
            draw.ellipse(
                [px - DOT, py - DOT, px + DOT, py + DOT], fill=DOT_FILL, outline=DOT_EDGE, width=3
            )
            draw.text((px, py), str(n), font=small, fill=PAPER, anchor="mm")
            approved = "yes" if mark.get("approved") is True else "NOT APPROVED"
            line = f"{n}. {label}    approved: {approved} {mark.get('approved_by', '')}"
            draw.text((10, photo.height + STRIP * n - 26), line, font=small, fill=INK)
        head = f"{target.photo_id}  {target.feature}  {target.where}"
        draw.text((10, photo.height + STRIP * (len(marks) + 1) - 26), head, font=bold, fill=INK)
        path = out_dir / f"{target.photo_id}.jpg"
        canvas.save(path, "JPEG", quality=82)
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        written = render(args.root)
    except RenderError as e:
        print(f"render-marks: refused, nothing written: {e}")
        return 1
    for path in written:
        print(f"render-marks: {path.relative_to(args.root)}")
    print(f"render-marks: {len(written)} photo(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
