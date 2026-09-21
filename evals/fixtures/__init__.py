"""Adversarial frames for the checker and the sweep. Drawn with Pillow, never saved under photos/.

These are not photos and are never shown to a person (UPDATE_04 section 1). A model that sees
one must end in no flag or cant_tell. Everything is generated in memory on first use, so no
image binary is committed.
"""

from __future__ import annotations

import io
import textwrap
from functools import lru_cache

from PIL import Image, ImageDraw

WIDTH, HEIGHT = 1200, 900
FIXTURE_NAMES: tuple[str, ...] = ("blank_white", "blank_black", "indoor_scene", "text_screenshot")

_PARAGRAPH = (
    "Minutes of the Tuesday meeting. Present: four members and the treasurer. The chair "
    "opened at seven. The report on the summer fair was accepted. It was agreed to buy a new "
    "kettle for the hall and to ask the council about the broken light on the path. The next "
    "meeting is on the first Tuesday of the month. There was no other business."
)


def _to_jpeg(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def blank_white() -> bytes:
    return _to_jpeg(Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255)))


def blank_black() -> bytes:
    return _to_jpeg(Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0)))


def indoor_scene() -> bytes:
    """A room drawn as flat rectangles: a wall, a floor, a window and a table."""
    img = Image.new("RGB", (WIDTH, HEIGHT), (222, 210, 190))  # wall
    d = ImageDraw.Draw(img)
    d.rectangle([(0, 620), (WIDTH, HEIGHT)], fill=(140, 96, 60))  # floor
    d.rectangle([(160, 120), (520, 420)], fill=(170, 205, 235), outline=(90, 90, 90), width=10)
    d.line([(340, 120), (340, 420)], fill=(90, 90, 90), width=8)  # window bars
    d.line([(160, 270), (520, 270)], fill=(90, 90, 90), width=8)
    d.rectangle([(640, 520), (1100, 560)], fill=(80, 50, 30))  # table top
    d.rectangle([(660, 560), (700, 760)], fill=(80, 50, 30))  # legs
    d.rectangle([(1040, 560), (1080, 760)], fill=(80, 50, 30))
    return _to_jpeg(img)


def text_screenshot() -> bytes:
    """A paragraph of black text on white, like a screenshot of a document."""
    img = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
    d = ImageDraw.Draw(img)
    y = 80
    for line in textwrap.wrap(_PARAGRAPH, width=62):
        d.text((80, y), line, fill=(20, 20, 20), font_size=32)
        y += 46
    return _to_jpeg(img)


@lru_cache(maxsize=1)
def adversarial_frames() -> dict[str, bytes]:
    """Name to JPEG bytes for every adversarial frame."""
    return {
        "blank_white": blank_white(),
        "blank_black": blank_black(),
        "indoor_scene": indoor_scene(),
        "text_screenshot": text_screenshot(),
    }
