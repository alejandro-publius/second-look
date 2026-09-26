"""The five Devpost gallery images and their captions (UPDATE_32 section 5).

Each image is 1500 by 1000 (3:2), under 5 MB, and is made only from the phone screenshots that
`make screens` wrote to docs/screens/, framed on a plain background with one short title. Nothing is
drawn in: every pixel of a screen is a real screenshot. results/screens.json says where each screen
came from: the live site for the read only pages, and this commit's production build with the fake
API for the test flow and the sample record, so no screenshot adds a sitting or a visit to the
study.

  uv run python scripts/make_devpost_gallery.py          write docs/submission/gallery/*.png
  uv run python scripts/make_devpost_gallery.py --check  fail if an image is missing or off size
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "docs" / "screens"
OUT = ROOT / "docs" / "submission" / "gallery"
SIZE = (1500, 1000)
MAX_BYTES = 5_000_000
BACKGROUND = (238, 243, 239)
INK = (18, 38, 30)
MUTED = (70, 88, 80)
FONT_FILES = ("/System/Library/Fonts/HelveticaNeue.ttc", "/System/Library/Fonts/Helvetica.ttc")

# file, screens shown side by side, title, the one-line caption for docs/devpost.md
GALLERY: list[tuple[str, list[str], str, str]] = [
    (
        "1-which-creek.png",
        ["landing-guess"],
        "Which creek is healthier?",
        (
            "The first screen: two real creeks and one question. The tidy park hides a "
            "concrete channel."
        ),
    ),
    (
        "2-lesson-card.png",
        ["lesson-card"],
        "What people assume, and what is there",
        "A lesson card: numbered marks on a real photo show what to look for before the test.",
    ),
    (
        "3-score.png",
        ["score"],
        "A score for each kind of damage",
        (
            "The score screen: one gauge for each of the four features, so a volunteer sees "
            "what to practise."
        ),
    ),
    (
        "4-record-and-fhir.png",
        ["spot-record", "spot-fhir"],
        "Each answer beside the observer's score",
        (
            "A creek record shows each answer beside the observer's score, and View as FHIR "
            "shows the same record in OneAquaHealth's profiles."
        ),
    ),
    (
        "5-city.png",
        ["walk-city"],
        "What the creek needs",
        (
            "The city view: what the creek needs, in OneAquaHealth's own restoration "
            "measures, each with its source."
        ),
    ),
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for f in FONT_FILES:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def _sources() -> dict[str, str]:
    doc = json.loads((ROOT / "results" / "screens.json").read_text(encoding="utf-8"))
    return {i["name"]: i.get("source", "") for i in doc.get("images", []) if "name" in i}


def compose(names: list[str], title: str, sources: dict[str, str]) -> Image.Image:
    canvas = Image.new("RGB", SIZE, BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.text((60, 48), title, font=_font(52), fill=INK)
    where = sorted({sources.get(n, "") for n in names} - {""})
    note = {
        "live": "Screenshot of the live site, second-look-79t.pages.dev",
        "local mock": "Screenshot of the site's production build, with no data sent anywhere",
    }
    line = "; ".join(note.get(w, w) for w in where)
    draw.text((60, 118), line, font=_font(24), fill=MUTED)
    top, bottom = 170, SIZE[1] - 30
    height = bottom - top
    phones = [Image.open(SCREENS / f"{n}.webp").convert("RGBA") for n in names]
    scaled = [p.resize((round(p.width * height / p.height), height), Image.LANCZOS) for p in phones]
    gap = 60
    total = sum(p.width for p in scaled) + gap * (len(scaled) - 1)
    x = (SIZE[0] - total) // 2
    for p in scaled:
        canvas.paste(p, (x, top), p)
        x += p.width + gap
    return canvas


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    problems: list[str] = []
    if args.check:
        for file, *_ in GALLERY:
            path = OUT / file
            if not path.exists():
                problems.append(f"{file} is missing")
                continue
            with Image.open(path) as im:
                if im.size != SIZE:
                    problems.append(f"{file} is {im.size}, not {SIZE}")
            if path.stat().st_size >= MAX_BYTES:
                problems.append(f"{file} is not under 5 MB")
        for p in problems:
            print(f"devpost-gallery: {p}", file=sys.stderr)
        print(f"devpost-gallery: {len(GALLERY) - len(problems)} of {len(GALLERY)} images good")
        return 1 if problems else 0
    OUT.mkdir(parents=True, exist_ok=True)
    sources = _sources()
    for file, names, title, _caption in GALLERY:
        img = compose(names, title, sources)
        img.save(OUT / file, optimize=True)
        print(f"devpost-gallery: {file} {img.size} {(OUT / file).stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
