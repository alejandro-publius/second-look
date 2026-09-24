"""Frame the gallery, and make the two-minute test GIF and the social preview (UPDATE_27 block 23).

In: the raw phone screenshots that apps/web/scripts/gallery.mjs wrote to apps/web/screens/gallery/,
and its captures.json, which says what each one shows, its route and where it came from: the live
site (read only pages) or a local build with the mock API (the test flow and the sample record).

Out:
- docs/screens/<name>.webp: every screen in the same drawn device frame, each under 400 KB.
- docs/lessons/lesson-<name>-marks.webp: two lesson photos with their marks, cropped from the lesson
  card, with the photo's author and licence printed under it.
- docs/screens/two-minute-test.gif: consent to the score screen, under 3 MB, in the same frame.
- docs/social-preview.png: 1280 by 640, under 1 MB, the two warm-up photos and the site's own font.
- results/screens.json: one row per image with its name, route, bytes and source, and the counts.

Every limit is checked before a file is written: an image that cannot get under its limit stops the
run instead of landing in docs/. scripts/tests/test_gallery.py checks the committed files again.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "apps" / "web" / "screens" / "gallery"
# Where the outputs go, relative to the repository.
SCREENS = Path("docs/screens")
# The two lesson photos are crops from a lesson card, not screens, so they live apart from them.
LESSONS = Path("docs/lessons")
SOCIAL = Path("docs/social-preview.png")
RESULTS = Path("results/screens.json")
MANIFEST = Path("photos/manifest.csv")
ITEMS = ROOT / "content" / "test_items.yaml"
# The font the site serves, self hosted from this package (apps/web/app/fonts.ts). Pillow reads the
# variable WOFF2 directly, so the preview uses the same file, set to a bold weight on its axis.
FONT = (
    ROOT
    / "apps/web/node_modules/@fontsource-variable/atkinson-hyperlegible-next/files"
    / "atkinson-hyperlegible-next-latin-wght-normal.woff2"
)
FONT_NAME = "Atkinson Hyperlegible Next (the site's self hosted WOFF2, read by Pillow)"

# The phone: 390 by 844 CSS pixels at 2x.
SCREEN_SIZE = (780, 1688)
# The drawn device frame: a rounded rectangle in one neutral grey, no notch, no marks.
BEZEL = 28
SCREEN_RADIUS = 60
OUTER_RADIUS = SCREEN_RADIUS + BEZEL
FRAME_COLOUR = (48, 48, 48)
# How far a lossy WebP may move the bezel's grey before the check calls it another frame.
FRAME_TOLERANCE = 8
FRAMED_SIZE = (SCREEN_SIZE[0] + 2 * BEZEL, SCREEN_SIZE[1] + 2 * BEZEL)
# The GIF is drawn smaller than the stills (376 pixels wide, about the width a README shows it
# at), with the most colours per frame that keep it under its limit.
GIF_SCALE = 0.45
GIF_COLOURS = (160, 128, 96, 64)

# Colours from apps/web/styles/tokens.css.
BG = (0xF4, 0xF6, 0xF5)
INK = (0x14, 0x21, 0x1E)
INK_SOFT = (0x4B, 0x5B, 0x57)

SCREEN_MAX_BYTES = 400_000
GIF_MAX_BYTES = 3_000_000
SOCIAL_MAX_BYTES = 1_000_000
SOCIAL_SIZE = (1280, 640)
WEBP_QUALITIES = (86, 80, 74, 68, 62)
# live: the live site. local mock: a local build with the mock API. photos: drawn from the
# committed photos, with no screen in it (the social preview).
SOURCES = ("live", "local mock", "photos")
# The kinds held to the 400 KB limit.
STILLS = ("screen", "lesson_photo")
# Screens that show a warm-up or test photo, so their alt text may not hint at an answer. The GIF
# and the social preview show them too and are always held to the same rule.
BLIND_SCREENS = frozenset({"landing", "landing-guess", "test-item", "score"})
BLIND_KINDS = frozenset({"gif", "social_preview"})


class GalleryError(Exception):
    """An image that breaks a rule. Nothing is written for it."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def licence_words(licence: str) -> str:
    """CC-BY-SA-2.0 as people write it: CC BY-SA 2.0."""
    if licence == "public-domain":
        return "public domain"
    if licence.startswith("CC0"):
        return "CC0 1.0"
    parts = licence.removeprefix("own-").split("-")
    if parts[0] == "CC" and len(parts) >= 3:
        return f"CC {'-'.join(parts[1:-1])} {parts[-1]}"
    return licence


def source_site(url: str) -> str:
    host = urlparse(url).netloc
    return "Wikimedia Commons" if host.endswith("wikimedia.org") else host


def manifest_rows(root: Path = ROOT) -> dict[str, dict[str, str]]:
    with (root / MANIFEST).open(newline="", encoding="utf-8") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


def credit_body(row: dict[str, str]) -> str:
    """The credit a CC BY photo asks for: the author, the licence and where it came from."""
    return f"{row['author']}, {licence_words(row['license'])}, {source_site(row['source_url'])}"


def credit_for(row: dict[str, str], lead: str = "Photo") -> str:
    return f"{lead}: {credit_body(row)}"


def font(size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    face = ImageFont.truetype(str(FONT), size)
    face.set_variation_by_axes([weight])
    return face


def rounded_mask(size: tuple[int, int], radius: int, scale: int = 4) -> Image.Image:
    """An anti-aliased rounded rectangle, drawn large and scaled down."""
    w, h = size
    big = Image.new("L", (w * scale, h * scale), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, w * scale - 1, h * scale - 1), radius=radius * scale, fill=255
    )
    return big.resize(size, Image.Resampling.LANCZOS)


_MASKS: dict[str, Image.Image] = {}


def device_frame(screen: Image.Image) -> Image.Image:
    """The screenshot inside the drawn phone. The screen must be exactly the phone's size."""
    if screen.size != SCREEN_SIZE:
        raise GalleryError(f"screenshot is {screen.size}, not the phone's {SCREEN_SIZE}")
    if not _MASKS:
        _MASKS["outer"] = rounded_mask(FRAMED_SIZE, OUTER_RADIUS)
        _MASKS["screen"] = rounded_mask(SCREEN_SIZE, SCREEN_RADIUS)
    framed = Image.new("RGBA", FRAMED_SIZE, (0, 0, 0, 0))
    framed.paste(Image.new("RGBA", FRAMED_SIZE, (*FRAME_COLOUR, 255)), (0, 0), _MASKS["outer"])
    framed.paste(screen.convert("RGBA"), (BEZEL, BEZEL), _MASKS["screen"])
    return framed


def webp_under(image: Image.Image, limit: int, what: str) -> tuple[bytes, int]:
    """The best quality WebP that fits under the limit, or a GalleryError."""
    size = 0
    for quality in WEBP_QUALITIES:
        buf = io.BytesIO()
        image.save(buf, "WEBP", quality=quality, method=6)
        data = buf.getvalue()
        size = len(data)
        if size <= limit:
            return data, quality
    raise GalleryError(f"{what}: {size} bytes at quality {WEBP_QUALITIES[-1]}, over {limit}")


def lesson_sheet(crop: Image.Image, credit: str) -> Image.Image:
    """The lesson photo as it sits on the card, with its credit line under it."""
    pad = 32
    size = 26
    face = font(size)
    while face.getlength(credit) > crop.width and size > 16:
        size -= 1
        face = font(size)
    sheet = Image.new("RGB", (crop.width + 2 * pad, crop.height + 2 * pad + size + 16), BG)
    sheet.paste(crop.convert("RGB"), (pad, pad))
    ImageDraw.Draw(sheet).text(
        (pad, pad + crop.height + 16), credit, font=face, fill=INK_SOFT, anchor="la"
    )
    return sheet


def gif_frame(small: Image.Image, colours: int) -> Image.Image:
    """One GIF frame: a palette of at most 255 colours, and index 255 for the clear corners."""
    alpha = small.getchannel("A")
    flat = Image.new("RGB", small.size, FRAME_COLOUR)
    flat.paste(small, (0, 0), alpha)
    paletted = flat.quantize(
        colors=colours, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
    )
    palette = (paletted.getpalette() or [])[: colours * 3]
    paletted.putpalette(palette + [0] * (768 - len(palette)))
    paletted.paste(255, (0, 0), alpha.point(lambda a: 255 if a < 128 else 0))
    paletted.info["transparency"] = 255
    return paletted


def make_gif(frames: list[tuple[Image.Image, int]]) -> tuple[bytes, int, int, int]:
    """The GIF bytes, its frame count, its length in milliseconds and the colours per frame.

    The most colours that fit under the limit, or a GalleryError.
    """
    if len(frames) < 2:
        raise GalleryError("the GIF needs at least two frames")
    size = (round(FRAMED_SIZE[0] * GIF_SCALE), round(FRAMED_SIZE[1] * GIF_SCALE))
    small = [device_frame(im).resize(size, Image.Resampling.LANCZOS) for im, _ in frames]
    durations = [ms for _, ms in frames]
    got = 0
    for colours in GIF_COLOURS:
        images = [gif_frame(im, colours) for im in small]
        buf = io.BytesIO()
        images[0].save(
            buf,
            "GIF",
            save_all=True,
            append_images=images[1:],
            duration=durations,
            loop=0,
            disposal=1,
            transparency=255,
            optimize=False,
        )
        data = buf.getvalue()
        got = len(data)
        if got <= GIF_MAX_BYTES:
            return data, len(images), sum(durations), colours
    raise GalleryError(
        f"two-minute-test.gif: {got} bytes at {GIF_COLOURS[-1]} colours, over {GIF_MAX_BYTES}"
    )


def social_preview(left: Path, right: Path, credits: list[str]) -> Image.Image:
    """1280 by 640: the question over the two warm-up photos, and the name."""
    w, h = SOCIAL_SIZE
    margin, gap = 56, 32
    img = Image.new("RGB", SOCIAL_SIZE, BG)
    draw = ImageDraw.Draw(img)
    draw.text((margin, 40), "Which creek is healthier?", font=font(68, 700), fill=INK, anchor="la")
    top, bottom = 150, 520
    photo_w = (w - 2 * margin - gap) // 2
    mask = rounded_mask((photo_w, bottom - top), 24)
    for i, path in enumerate((left, right)):
        with Image.open(path) as src:
            photo = ImageOps.fit(
                ImageOps.exif_transpose(src).convert("RGB"),
                (photo_w, bottom - top),
                Image.Resampling.LANCZOS,
            )
        img.paste(photo, (margin + i * (photo_w + gap), top), mask)
    draw.text((margin, 588), "Second Look", font=font(44, 700), fill=INK, anchor="ls")
    small = font(18)
    for i, line in enumerate(credits):
        draw.text((w - margin, 562 + i * 26), line, font=small, fill=INK_SOFT, anchor="rs")
    return img


def png_under(image: Image.Image, limit: int, what: str) -> tuple[bytes, str]:
    """Full colour if it fits, else a 256 colour palette with dithering, else a GalleryError."""
    tries: list[tuple[str, Image.Image]] = [
        ("full colour", image),
        ("256 colours", image.quantize(colors=256, dither=Image.Dither.FLOYDSTEINBERG)),
    ]
    size = 0
    for label, candidate in tries:
        buf = io.BytesIO()
        candidate.save(buf, "PNG", optimize=True)
        data = buf.getvalue()
        size = len(data)
        if size <= limit:
            return data, label
    raise GalleryError(f"{what}: {size} bytes, over {limit}")


def is_test_flow(route: str) -> bool:
    """The two-minute test lives at /t. /two, /t-shirt or anything else is not it."""
    path = urlparse(route).path.rstrip("/")
    return path == "/t" or path.startswith("/t/")


def row(name: str, file: Path, route: str, source: str, data: bytes, **extra: Any) -> dict:
    if source not in SOURCES:
        raise GalleryError(f"{name}: source {source!r} is not one of {SOURCES}")
    if is_test_flow(route) and source != "local mock":
        raise GalleryError(f"{name}: a test flow screen must come from the local mock")
    return {
        "name": name,
        "file": file.as_posix(),
        "route": route,
        "source": source,
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        **extra,
    }


def build(raw: Path, out_root: Path = ROOT) -> dict[str, Any]:
    """Every output in memory first, so a broken rule writes nothing."""
    captures = json.loads((raw / "captures.json").read_text(encoding="utf-8"))
    manifest = manifest_rows()
    outputs: dict[Path, bytes] = {}
    rows: list[dict[str, Any]] = []

    for shot in captures["screens"]:
        with Image.open(raw / shot["file"]) as im:
            framed = device_frame(im)
        data, quality = webp_under(framed, SCREEN_MAX_BYTES, shot["name"])
        path = SCREENS / f"{shot['name']}.webp"
        outputs[path] = data
        rows.append(
            row(
                shot["name"],
                path,
                shot["route"],
                shot["source"],
                data,
                kind="screen",
                width=FRAMED_SIZE[0],
                height=FRAMED_SIZE[1],
                webp_quality=quality,
                alt=shot["alt"],
                blind=shot["name"] in BLIND_SCREENS,
            )
        )

    for lesson in captures["lesson_photos"]:
        photo = manifest.get(lesson["photo_id"])
        if photo is None:
            raise GalleryError(f"{lesson['name']}: {lesson['photo_id']} has no manifest row")
        with Image.open(raw / lesson["file"]) as im:
            sheet = lesson_sheet(im, credit_for(photo))
        data, quality = webp_under(sheet, SCREEN_MAX_BYTES, lesson["name"])
        LESSONS.mkdir(parents=True, exist_ok=True)
        path = LESSONS / f"{lesson['name']}.webp"
        outputs[path] = data
        feature = str(lesson.get("feature_name") or lesson["feature"]).lower()
        rows.append(
            row(
                lesson["name"],
                path,
                "/t",
                "local mock",
                data,
                kind="lesson_photo",
                width=sheet.width,
                height=sheet.height,
                webp_quality=quality,
                photos=[lesson["photo_id"]],
                credit=credit_for(photo),
                alt=f"A lesson photo on {feature}, with its numbered marks, what each one "
                "points at, and the photo credit.",
                blind=False,
            )
        )

    frames = []
    for f in captures["gif_frames"]:
        with Image.open(raw / f["file"]) as im:
            frames.append((im.copy(), int(f["ms"])))
    gif, count, ms, colours = make_gif(frames)
    gif_path = SCREENS / "two-minute-test.gif"
    outputs[gif_path] = gif
    with Image.open(io.BytesIO(gif)) as g:
        gif_size = g.size
    gif_row = row(
        "two-minute-test",
        gif_path,
        "/t",
        "local mock",
        gif,
        kind="gif",
        width=gif_size[0],
        height=gif_size[1],
        frames=count,
        seconds=round(ms / 1000, 1),
        colours_per_frame=colours,
        alt="The two-minute test on a phone, from the consent screen through the four lessons "
        "and the sixteen photos to the score screen.",
        blind=True,
    )
    rows.append(gif_row)

    items = yaml.safe_load(ITEMS.read_text(encoding="utf-8"))
    warmup_ids = [w["photo_id"] for w in items["warmup"]]
    warm = [manifest[i] for i in warmup_ids]
    credits = [
        credit_for(r, f"{side} photo") for side, r in zip(("Left", "Right"), warm, strict=True)
    ]
    preview = social_preview(
        ROOT / "photos" / warm[0]["file"], ROOT / "photos" / warm[1]["file"], credits
    )
    social, png_colours = png_under(preview, SOCIAL_MAX_BYTES, "social-preview.png")
    outputs[SOCIAL] = social
    social_row = row(
        "social-preview",
        SOCIAL,
        "/",
        "photos",
        social,
        kind="social_preview",
        width=SOCIAL_SIZE[0],
        height=SOCIAL_SIZE[1],
        font=FONT_NAME,
        png_colours=png_colours,
        photos=warmup_ids,
        credit="; ".join(credits),
        alt="Two creek photos side by side under the question Which creek is healthier?, "
        "and the name Second Look.",
        blind=True,
    )
    rows.append(social_row)

    screens = [r for r in rows if r["kind"] == "screen"]
    summary = {
        "generated_by": "make screens: apps/web/scripts/gallery.mjs, then scripts/make_gallery.py",
        "live_url": captures["live_url"],
        "phone": {"css_width": 390, "css_height": 844, "scale": 2},
        "screen_format": "webp",
        "limits_bytes": {
            "screen": SCREEN_MAX_BYTES,
            "gif": GIF_MAX_BYTES,
            "social_preview": SOCIAL_MAX_BYTES,
        },
        "screen_count": len(screens),
        "live_count": sum(1 for r in screens if r["source"] == "live"),
        "local_mock_count": sum(1 for r in screens if r["source"] == "local mock"),
        "largest_screen_bytes": max(r["bytes"] for r in rows if r["kind"] in STILLS),
        "gif": {"bytes": gif_row["bytes"], "frames": count, "seconds": gif_row["seconds"]},
        "social_preview": {"bytes": social_row["bytes"], "font": FONT_NAME},
        "images": rows,
    }
    for rel, data in outputs.items():
        (out_root / rel).parent.mkdir(parents=True, exist_ok=True)
        (out_root / rel).write_bytes(data)
    return summary


# ------------------------------------------------------------------------------------------------
# The check of what is committed. scripts/tests/test_gallery.py runs it on every make check.
# ------------------------------------------------------------------------------------------------

# Words that name or hint at what a test or warm-up question asks. The alt text of an image that
# shows such a photo never uses them (hard rule 17). The lesson images may: they teach.
HINT_WORDS = (
    "artificial",
    "natural",
    "concrete",
    "wall",
    "stone",
    "built",
    "bank",
    "erod",
    "straight",
    "channel",
    "canal",
    "ditch",
    "dug",
    "culvert",
    "meander",
    "bend",
    "invasive",
    "native",
    "weed",
    "ivy",
    "bramble",
    "blackberr",
    "pipe",
    "outfall",
    "outlet",
    "drain",
    "sewer",
    "tidy",
    "tidier",
    "messy",
    "messier",
)
# Every screen a person or judge reaches must stay in the gallery (UPDATE_27 block 23).
REQUIRED_SCREENS = frozenset(
    {
        "landing",
        "landing-guess",
        "consent",
        "lesson-card",
        "test-item",
        "score",
        "demo",
        "warmup",
        "accessibility",
        "offline",
        "share",
        "judges",
        "walks",
        "walk",
        "walk-in-progress",
        "walk-record",
        "check-start",
        "check-location",
        "check-question",
        "quick",
        "spot-record",
        "spot-fhir",
        "city",
        "two",
        "how-we-know",
        "credits",
        "privacy",
        "about",
        "poster",
    }
)
LIMITS = {
    "screen": SCREEN_MAX_BYTES,
    "lesson_photo": SCREEN_MAX_BYTES,
    "gif": GIF_MAX_BYTES,
    "social_preview": SOCIAL_MAX_BYTES,
}
FORMATS = {"screen": "WEBP", "lesson_photo": "WEBP", "gif": "GIF", "social_preview": "PNG"}
METADATA_KEYS = ("exif", "xmp", "XML:com.adobe.xmp", "icc_profile", "comment")


def gallery_files(root: Path) -> set[str]:
    """The images this gallery owns: every WebP and GIF under docs/screens, and the preview."""
    screens = root / SCREENS
    found = {
        p.relative_to(root).as_posix()
        for p in screens.rglob("*")
        if p.suffix.lower() in {".webp", ".gif"}
    }
    social = root / SOCIAL
    if social.exists():
        found.add(social.relative_to(root).as_posix())
    return found


def in_the_drawn_frame(image: Image.Image) -> bool:
    """True when a screen sits in the frame device_frame draws: the corners clear, and the
    middle of each side of the bezel the frame's one grey. The size alone does not say so."""
    rgba = image.convert("RGBA")
    w, h = rgba.size

    def at(x: int, y: int) -> tuple[int, ...]:
        pixel = rgba.getpixel((x, y))
        return pixel if isinstance(pixel, tuple) else (-1, -1, -1, -1)  # fails the check

    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    if any(at(x, y)[3] != 0 for x, y in corners):
        return False
    half = BEZEL // 2
    sides = [(w // 2, half), (w // 2, h - 1 - half), (half, h // 2), (w - 1 - half, h // 2)]
    for x, y in sides:
        r, g, b, a = at(x, y)
        off = max(abs(r - FRAME_COLOUR[0]), abs(g - FRAME_COLOUR[1]), abs(b - FRAME_COLOUR[2]))
        if a != 255 or off > FRAME_TOLERANCE:
            return False
    return True


def hints_in(text: str) -> list[str]:
    low = text.lower()
    return sorted({w for w in HINT_WORDS if w in low})


def check_row(root: Path, r: dict[str, Any], manifest: dict[str, dict[str, str]]) -> list[str]:
    name = r.get("name", "?")
    kind = r.get("kind", "")
    out: list[str] = []
    if kind not in LIMITS:
        return [f"{name}: kind {kind!r} is not one of {sorted(LIMITS)}"]
    if r.get("source") not in SOURCES:
        out.append(f"{name}: source {r.get('source')!r} is not one of {SOURCES}")
    if is_test_flow(str(r.get("route", ""))) and r.get("source") != "local mock":
        out.append(f"{name}: a test flow image must come from the local mock, not {r['source']}")
    alt = str(r.get("alt", "")).strip()
    if not alt:
        out.append(f"{name}: no alt text")
    if r.get("blind") and hints_in(alt):
        out.append(f"{name}: alt text hints at an answer ({hints_in(alt)})")
    if (kind in BLIND_KINDS or name in BLIND_SCREENS) and not r.get("blind"):
        out.append(f"{name}: shows photos people answer about, so it must be marked blind")
    for photo_id in r.get("photos", []):
        photo = manifest.get(photo_id)
        if photo is None:
            out.append(f"{name}: shows {photo_id}, which has no row in photos/manifest.csv")
            continue
        if photo["faces"].strip().lower() not in {"false", "0", ""}:
            out.append(f"{name}: shows {photo_id}, which has faces")
        if photo["synthetic"].strip().lower() not in {"false", "0", ""}:
            out.append(f"{name}: shows {photo_id}, which is synthetic")
        if credit_body(photo) not in str(r.get("credit", "")):
            out.append(f"{name}: its credit does not name {photo_id}'s author and licence")
    path = root / str(r.get("file", ""))
    if not path.is_file():
        return [*out, f"{name}: {r.get('file')} is missing"]
    data = path.read_bytes()
    if len(data) != r.get("bytes"):
        out.append(f"{name}: {len(data)} bytes on disk, {r.get('bytes')} in results/screens.json")
    if sha256_bytes(data) != r.get("sha256"):
        out.append(f"{name}: sha256 differs from results/screens.json")
    if len(data) > LIMITS[kind]:
        out.append(f"{name}: {len(data)} bytes, over the {kind} limit of {LIMITS[kind]}")
    with Image.open(io.BytesIO(data)) as im:
        if im.format != FORMATS[kind]:
            out.append(f"{name}: {im.format}, not {FORMATS[kind]}")
        if [im.width, im.height] != [r.get("width"), r.get("height")]:
            out.append(f"{name}: {im.width}x{im.height}, not what results/screens.json says")
        if kind == "screen" and im.size != FRAMED_SIZE:
            out.append(f"{name}: {im.size}, not the one device frame {FRAMED_SIZE}")
        elif kind == "screen" and not in_the_drawn_frame(im):
            out.append(f"{name}: not inside the one drawn frame (clear corners, grey bezel)")
        if kind == "social_preview" and im.size != SOCIAL_SIZE:
            out.append(f"{name}: {im.size}, not {SOCIAL_SIZE}")
        if kind == "gif":
            frames = getattr(im, "n_frames", 1)
            if frames < 2 or frames != r.get("frames"):
                out.append(f"{name}: {frames} frames, results/screens.json says {r.get('frames')}")
        carried = [k for k in METADATA_KEYS if im.info.get(k)]
        if carried or len(im.getexif()):
            out.append(f"{name}: carries metadata ({carried or ['exif']})")
    return out


def check(root: Path = ROOT) -> list[str]:
    """Every rule the gallery keeps, on the committed files. Empty means all is well."""
    results = root / RESULTS
    if not results.exists():
        return ["results/screens.json is missing: run make screens"]
    doc = json.loads(results.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = doc.get("images", [])
    manifest = manifest_rows(root)
    problems: list[str] = []
    names = [r.get("name") for r in rows]
    files = [r.get("file") for r in rows]
    for label, values in (("name", names), ("file", files)):
        doubled = sorted({v for v in values if values.count(v) > 1}, key=str)
        if doubled:
            problems.append(f"the same {label} on two rows: {doubled}")
    # Hard rule 6: every image has a row. scripts/check_manifest.py covers photos/; this covers
    # the gallery, and each photo a gallery row names must have its photos/manifest.csv row.
    for f in sorted(gallery_files(root) - set(files)):
        problems.append(f"no row in results/screens.json: {f}")
    for r in rows:
        problems.extend(check_row(root, r, manifest))
    screens = [r for r in rows if r.get("kind") == "screen"]
    missing = sorted(REQUIRED_SCREENS - {r.get("name") for r in screens})
    if missing:
        problems.append(f"screens missing from the gallery: {missing}")
    for kind, want in (("lesson_photo", 2), ("gif", 1), ("social_preview", 1)):
        got = sum(1 for r in rows if r.get("kind") == kind)
        if got != want:
            problems.append(f"{got} {kind} row(s), want {want}")
    counts = {
        "screen_count": len(screens),
        "live_count": sum(1 for r in screens if r.get("source") == "live"),
        "local_mock_count": sum(1 for r in screens if r.get("source") == "local mock"),
        "largest_screen_bytes": max(
            (r.get("bytes", 0) for r in rows if r.get("kind") in STILLS), default=0
        ),
    }
    for key, value in counts.items():
        if doc.get(key) != value:
            problems.append(f"{key} is {doc.get(key)}, the rows say {value}")
    gif = next((r for r in rows if r.get("kind") == "gif"), {})
    if gif and doc.get("gif") != {k: gif.get(k) for k in ("bytes", "frames", "seconds")}:
        problems.append("the gif summary does not match its row")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=RAW, help="where gallery.mjs wrote its PNGs")
    parser.add_argument("--check", action="store_true", help="check the committed files only")
    args = parser.parse_args(argv)
    if args.check:
        problems = check()
        for p in problems:
            print(f"gallery-check: {p}")
        print(f"gallery-check: {len(problems)} problem(s)")
        return 1 if problems else 0
    try:
        summary = build(args.raw)
    except GalleryError as err:
        print(f"make-gallery: {err}")
        return 1
    (ROOT / RESULTS).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        f"make-gallery: {summary['screen_count']} screens ({summary['live_count']} live, "
        f"{summary['local_mock_count']} local mock), largest {summary['largest_screen_bytes']} "
        f"bytes; GIF {summary['gif']['bytes']} bytes, {summary['gif']['frames']} frames; "
        f"social preview {summary['social_preview']['bytes']} bytes"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
