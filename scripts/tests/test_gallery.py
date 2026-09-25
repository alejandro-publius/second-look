"""The README gallery (UPDATE_27 block 23): sizes, one device frame, and a row for every image.

scripts/check_manifest.py gives every image under photos/ a row in photos/manifest.csv (hard rule
6). The gallery's images live under docs/ instead, so their rows are in results/screens.json, and
each photo a gallery image names must have its photos/manifest.csv row. The first test checks the
committed files. Every test after it breaks one rule in a copy and checks the check says so, and
the last ones check that the gallery script can only read from the live site.
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from scripts import make_gallery
from scripts.make_gallery import check, is_test_flow

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "apps" / "web" / "scripts" / "gallery-guard.mjs"
LIVE = "https://second-look-79t.pages.dev"


def test_the_committed_gallery_keeps_every_rule() -> None:
    assert check(ROOT) == []


def test_the_limits_are_the_ones_the_brief_names() -> None:
    assert make_gallery.SCREEN_MAX_BYTES == 400_000
    assert make_gallery.GIF_MAX_BYTES == 3_000_000
    assert make_gallery.SOCIAL_MAX_BYTES == 1_000_000
    assert make_gallery.SOCIAL_SIZE == (1280, 640)
    assert make_gallery.SCREEN_SIZE == (390 * 2, 844 * 2)


# ------------------------------------------------------------------------------------------------
# A copy of the gallery to break.
# ------------------------------------------------------------------------------------------------


@pytest.fixture
def gallery(tmp_path: Path) -> Path:
    for rel in ["results/screens.json", "photos/manifest.csv", "docs/social-preview.png"]:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, tmp_path / rel)
    for path in (ROOT / "docs" / "lessons").glob("*.webp"):
        (tmp_path / "docs" / "lessons").mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, tmp_path / "docs" / "lessons" / path.name)
    for path in (ROOT / "docs" / "screens").glob("*"):
        if path.suffix in {".webp", ".gif"}:
            (tmp_path / "docs" / "screens").mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, tmp_path / "docs" / "screens" / path.name)
    return tmp_path


def doc_of(root: Path) -> dict[str, Any]:
    return json.loads((root / "results" / "screens.json").read_text(encoding="utf-8"))


def edit(root: Path, change: Callable[[dict[str, Any]], None]) -> None:
    doc = doc_of(root)
    change(doc)
    (root / "results" / "screens.json").write_text(json.dumps(doc), encoding="utf-8")


def row_named(doc: dict[str, Any], name: str) -> dict[str, Any]:
    return next(r for r in doc["images"] if r["name"] == name)


def replace_image(root: Path, name: str, image: Image.Image, fmt: str, **save: Any) -> None:
    """Swap in another picture and keep its row's bytes and sha256 true, so only one rule breaks."""
    rel = row_named(doc_of(root), name)["file"]
    image.save(root / rel, fmt, **save)
    data = (root / rel).read_bytes()

    def update(doc: dict[str, Any]) -> None:
        r = row_named(doc, name)
        r["bytes"], r["sha256"] = len(data), make_gallery.sha256_bytes(data)
        r["width"], r["height"] = image.size
        if r["kind"] in make_gallery.STILLS:
            doc["largest_screen_bytes"] = max(
                x["bytes"] for x in doc["images"] if x["kind"] in make_gallery.STILLS
            )

    edit(root, update)


def says(problems: list[str], words: str) -> bool:
    return any(words in p for p in problems)


def test_the_copy_starts_clean(gallery: Path) -> None:
    assert check(gallery) == []


def test_an_image_without_a_row_fails(gallery: Path) -> None:
    shutil.copy2(gallery / "docs/screens/quick.webp", gallery / "docs/screens/stray.webp")
    assert says(check(gallery), "no row in results/screens.json: docs/screens/stray.webp")


def test_an_image_in_a_folder_below_screens_needs_a_row_too(gallery: Path) -> None:
    (gallery / "docs/screens/more").mkdir()
    shutil.copy2(gallery / "docs/screens/quick.webp", gallery / "docs/screens/more/a.gif")
    assert says(check(gallery), "no row in results/screens.json: docs/screens/more/a.gif")


def test_a_row_without_its_image_fails(gallery: Path) -> None:
    (gallery / "docs/screens/quick.webp").unlink()
    assert says(check(gallery), "quick: docs/screens/quick.webp is missing")


def test_a_screen_over_400_kb_fails(gallery: Path) -> None:
    noise = Image.effect_noise(make_gallery.FRAMED_SIZE, 120).convert("RGB")
    replace_image(gallery, "quick", noise, "WEBP", quality=100)
    assert (gallery / "docs/screens/quick.webp").stat().st_size > 400_000
    assert says(check(gallery), "quick: ")
    assert says(check(gallery), "over the screen limit of 400000")


def test_the_gif_and_the_preview_have_limits(
    gallery: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(make_gallery.LIMITS, "gif", 1000)
    monkeypatch.setitem(make_gallery.LIMITS, "social_preview", 1000)
    problems = check(gallery)
    assert says(problems, "over the gif limit of 1000")
    assert says(problems, "over the social_preview limit of 1000")


def test_a_screen_outside_the_one_frame_fails(gallery: Path) -> None:
    with Image.open(gallery / "docs/screens/quick.webp") as im:
        smaller = im.resize((780, 1688))
    replace_image(gallery, "quick", smaller, "WEBP", quality=80)
    assert says(check(gallery), "not the one device frame")


def test_the_social_preview_must_be_1280_by_640(gallery: Path) -> None:
    with Image.open(gallery / "docs/social-preview.png") as im:
        other = im.convert("RGB").resize((1200, 630))
    replace_image(gallery, "social-preview", other, "PNG")
    assert says(check(gallery), "not (1280, 640)")


def test_bytes_and_sha256_must_match_the_row(gallery: Path) -> None:
    edit(gallery, lambda d: row_named(d, "two").update(bytes=1, sha256="0" * 64))
    problems = check(gallery)
    assert says(problems, "two: ")
    assert says(problems, "bytes on disk, 1 in results/screens.json")
    assert says(problems, "two: sha256 differs")


def test_a_test_flow_screen_from_the_live_site_fails(gallery: Path) -> None:
    edit(gallery, lambda d: row_named(d, "test-item").update(source="live"))
    assert says(check(gallery), "test-item: a test flow image must come from the local mock")


def test_two_is_not_the_test_flow() -> None:
    assert is_test_flow("/t")
    assert is_test_flow("/t?src=poster")
    assert is_test_flow("/t/")
    assert not is_test_flow("/two")
    assert not is_test_flow("/")


def test_an_unknown_source_fails(gallery: Path) -> None:
    edit(gallery, lambda d: row_named(d, "about").update(source="somewhere"))
    assert says(check(gallery), "about: source 'somewhere' is not one of")


def test_alt_text_on_a_test_photo_may_not_hint(gallery: Path) -> None:
    edit(gallery, lambda d: row_named(d, "test-item").update(alt="A pipe over a creek."))
    assert says(check(gallery), "test-item: alt text hints at an answer (['pipe'])")


def test_the_score_screen_is_held_to_the_blind_rule(gallery: Path) -> None:
    edit(gallery, lambda d: row_named(d, "score").update(blind=False))
    assert says(check(gallery), "score: shows photos people answer about")


def test_every_image_has_alt_text(gallery: Path) -> None:
    edit(gallery, lambda d: row_named(d, "credits").update(alt=" "))
    assert says(check(gallery), "credits: no alt text")


def test_a_photo_without_a_manifest_row_fails(gallery: Path) -> None:
    edit(gallery, lambda d: row_named(d, "lesson-pipe-marks").update(photos=["ph-nowhere"]))
    assert says(check(gallery), "shows ph-nowhere, which has no row in photos/manifest.csv")


def test_a_photo_with_faces_fails(gallery: Path) -> None:
    manifest = gallery / "photos" / "manifest.csv"
    photo = row_named(doc_of(gallery), "lesson-pipe-marks")["photos"][0]
    lines = manifest.read_text(encoding="utf-8").splitlines(keepends=True)
    changed = [
        line.replace(",false,false,", ",false,true,", 1) if line.startswith(f"{photo},") else line
        for line in lines
    ]
    assert changed != lines
    manifest.write_text("".join(changed), encoding="utf-8")
    assert says(check(gallery), f"shows {photo}, which has faces")


def test_the_credit_must_be_the_manifest_credit(gallery: Path) -> None:
    edit(gallery, lambda d: row_named(d, "lesson-pipe-marks").update(credit="Photo: someone"))
    edit(gallery, lambda d: row_named(d, "social-preview").update(credit="two photos"))
    problems = check(gallery)
    assert says(problems, "lesson-pipe-marks: its credit does not name")
    assert says(problems, "social-preview: its credit does not name")


@pytest.mark.parametrize("dropped", ["demo", "check-location", "check-question"])
def test_a_dropped_screen_fails(gallery: Path, dropped: str) -> None:
    def drop(doc: dict[str, Any]) -> None:
        doc["images"] = [r for r in doc["images"] if r["name"] != dropped]
        doc["screen_count"] -= 1
        doc["live_count"] -= 1

    edit(gallery, drop)
    (gallery / f"docs/screens/{dropped}.webp").unlink()
    problems = check(gallery)
    assert problems == [f"screens missing from the gallery: [{dropped!r}]"]


def test_a_dropped_gif_fails(gallery: Path) -> None:
    edit(gallery, lambda d: d.update(images=[r for r in d["images"] if r["kind"] != "gif"]))
    (gallery / "docs/screens/two-minute-test.gif").unlink()
    assert says(check(gallery), "0 gif row(s), want 1")


def test_a_screen_without_the_drawn_frame_fails(gallery: Path) -> None:
    # The right size, but a plain picture: no clear corners and no grey bezel.
    plain = Image.new("RGB", make_gallery.FRAMED_SIZE, (200, 210, 205))
    replace_image(gallery, "quick", plain, "WEBP", quality=80)
    assert says(check(gallery), "quick: not inside the one drawn frame")


def test_a_screen_with_filled_corners_fails(gallery: Path) -> None:
    # The same frame laid on white: the bezel is still grey, but the corners are no longer clear.
    with Image.open(gallery / "docs/screens/quick.webp") as im:
        rgba = im.convert("RGBA")
    on_white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    on_white.alpha_composite(rgba)
    replace_image(gallery, "quick", on_white, "WEBP", quality=80)
    assert says(check(gallery), "quick: not inside the one drawn frame")


def test_a_screen_in_another_grey_fails(gallery: Path) -> None:
    # The same screen, drawn again in a frame of another colour.
    with Image.open(gallery / "docs/screens/quick.webp") as im:
        rgba = im.convert("RGBA")
    b = make_gallery.BEZEL
    w, h = make_gallery.SCREEN_SIZE
    screen = rgba.crop((b, b, b + w, b + h))
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(make_gallery, "FRAME_COLOUR", (200, 30, 30))
        red = make_gallery.device_frame(screen)
    replace_image(gallery, "quick", red, "WEBP", quality=80)
    assert says(check(gallery), "quick: not inside the one drawn frame")


def test_an_image_in_the_wrong_format_fails(gallery: Path) -> None:
    # A PNG under a .webp name, with its row kept true to the bytes.
    with Image.open(gallery / "docs/screens/quick.webp") as im:
        copy = im.copy()
    replace_image(gallery, "quick", copy, "PNG")
    assert says(check(gallery), "quick: PNG, not WEBP")


def test_a_lesson_photo_over_400_kb_fails(gallery: Path) -> None:
    noise = Image.effect_noise((780, 1033), 120).convert("RGB")
    replace_image(gallery, "lesson-pipe-marks", noise, "WEBP", quality=100)
    assert (gallery / "docs/lessons/lesson-pipe-marks.webp").stat().st_size > 400_000
    assert says(check(gallery), "over the lesson_photo limit of 400000")


def test_the_gif_and_the_preview_are_held_to_the_blind_rule(gallery: Path) -> None:
    edit(gallery, lambda d: row_named(d, "two-minute-test").update(blind=False))
    edit(gallery, lambda d: row_named(d, "social-preview").update(blind=False))
    problems = check(gallery)
    assert says(problems, "two-minute-test: shows photos people answer about")
    assert says(problems, "social-preview: shows photos people answer about")


def test_a_synthetic_photo_fails(gallery: Path) -> None:
    manifest = gallery / "photos" / "manifest.csv"
    photo = row_named(doc_of(gallery), "lesson-pipe-marks")["photos"][0]
    with manifest.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    hit = [r for r in rows if r["id"] == photo]
    assert len(hit) == 1
    hit[0]["synthetic"] = "true"
    with manifest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    assert says(check(gallery), f"shows {photo}, which is synthetic")


def test_the_gif_frame_count_must_match(gallery: Path) -> None:
    edit(gallery, lambda d: row_named(d, "two-minute-test").update(frames=3))
    problems = check(gallery)
    assert says(problems, "two-minute-test: ")
    assert says(problems, "frames, results/screens.json says 3")
    assert says(problems, "the gif summary does not match its row")


def test_the_counts_must_match_the_rows(gallery: Path) -> None:
    edit(
        gallery,
        lambda d: d.update(
            screen_count=99, live_count=0, local_mock_count=0, largest_screen_bytes=1
        ),
    )
    problems = check(gallery)
    assert says(problems, "screen_count is 99")
    assert says(problems, "live_count is 0")
    assert says(problems, "local_mock_count is 0")
    assert says(problems, "largest_screen_bytes is 1")


def test_an_image_with_exif_fails(gallery: Path) -> None:
    with Image.open(gallery / "docs/screens/quick.webp") as im:
        copy = im.copy()
    exif = Image.Exif()
    exif[0x010F] = "A camera maker"
    replace_image(gallery, "quick", copy, "WEBP", quality=80, exif=exif.tobytes())
    assert says(check(gallery), "quick: carries metadata")


def test_the_same_name_twice_fails(gallery: Path) -> None:
    edit(gallery, lambda d: row_named(d, "about").update(name="privacy"))
    assert says(check(gallery), "the same name on two rows: ['privacy']")


# ------------------------------------------------------------------------------------------------
# make_gallery.py refuses to write an image that breaks a rule, and then writes nothing at all.
# ------------------------------------------------------------------------------------------------


def phone_shot(colour: tuple[int, int, int] = (200, 210, 205)) -> Image.Image:
    return Image.new("RGB", make_gallery.SCREEN_SIZE, colour)


def test_a_screenshot_that_is_not_the_phone_size_is_refused() -> None:
    with pytest.raises(make_gallery.GalleryError, match="not the phone's"):
        make_gallery.device_frame(Image.new("RGB", (390, 844)))


def test_the_frame_is_the_same_rounded_grey_for_every_screen() -> None:
    framed = make_gallery.device_frame(phone_shot())
    assert framed.size == make_gallery.FRAMED_SIZE
    # The corner outside the frame is clear; the top edge is the frame's one grey.
    assert framed.getpixel((0, 0)) == (0, 0, 0, 0)
    edge = framed.getpixel((make_gallery.FRAMED_SIZE[0] // 2, 5))
    assert edge == (*make_gallery.FRAME_COLOUR, 255)
    # The screen sits inside the bezel, untouched.
    middle = (make_gallery.FRAMED_SIZE[0] // 2, make_gallery.FRAMED_SIZE[1] // 2)
    assert framed.getpixel(middle) == (200, 210, 205, 255)


def test_a_still_that_cannot_get_under_its_limit_is_refused() -> None:
    noise = Image.effect_noise((400, 400), 120).convert("RGB")
    with pytest.raises(make_gallery.GalleryError, match="over 1000"):
        make_gallery.webp_under(noise, 1000, "noise")


def test_a_gif_that_cannot_get_under_its_limit_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(make_gallery, "GIF_MAX_BYTES", 1000)
    frames = [(phone_shot(), 500), (phone_shot((20, 20, 20)), 500)]
    with pytest.raises(make_gallery.GalleryError, match="over 1000"):
        make_gallery.make_gif(frames)


def test_a_preview_that_cannot_get_under_its_limit_is_refused() -> None:
    noise = Image.effect_noise(make_gallery.SOCIAL_SIZE, 120).convert("RGB")
    with pytest.raises(make_gallery.GalleryError, match="over 1000"):
        make_gallery.png_under(noise, 1000, "preview")


def test_a_test_flow_screen_from_the_live_site_is_refused() -> None:
    path = make_gallery.SCREENS / "x.webp"
    with pytest.raises(make_gallery.GalleryError, match="must come from the local mock"):
        make_gallery.row("x", path, "/t", "live", b"x")
    assert make_gallery.row("x", path, "/two", "live", b"x")["source"] == "live"


def test_a_broken_run_writes_nothing(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    phone_shot().save(raw / "good.png")
    Image.new("RGB", (100, 100)).save(raw / "bad.png")
    captures = {
        "live_url": LIVE,
        "screens": [
            {"name": "good", "route": "/about", "source": "live", "file": "good.png", "alt": "a"},
            {"name": "bad", "route": "/about", "source": "live", "file": "bad.png", "alt": "b"},
        ],
        "lesson_photos": [],
        "gif_frames": [],
    }
    (raw / "captures.json").write_text(json.dumps(captures), encoding="utf-8")
    out = tmp_path / "out"
    with pytest.raises(make_gallery.GalleryError, match="not the phone's"):
        make_gallery.build(raw, out_root=out)
    assert not out.exists()


# ------------------------------------------------------------------------------------------------
# The gallery script reads the live site and never writes to it.
# ------------------------------------------------------------------------------------------------

LIVE_CASES = [
    ("GET", f"{LIVE}/", True),
    ("HEAD", f"{LIVE}/about", True),
    ("GET", f"{LIVE}/api/two", True),
    ("GET", f"{LIVE}/photos/ph-warmup-03-800.avif", True),
    ("GET", "data:image/png;base64,AAAA", True),
    ("POST", f"{LIVE}/api/test/session", False),
    ("GET", f"{LIVE}/api/test/resume?session_id=x", False),
    ("POST", f"{LIVE}/api/demo/answer", False),
    ("GET", f"{LIVE}/api/demo/answer", False),
    ("POST", f"{LIVE}/api/check/draft", False),
    ("POST", f"{LIVE}/api/quick/example", False),
    ("POST", f"{LIVE}/api/upload", False),
    # Every path on the never list is refused on a GET too, one case per entry, so dropping any
    # one of them from the list turns this red.
    ("GET", f"{LIVE}/api/check/draft", False),
    ("GET", f"{LIVE}/api/quick/example", False),
    ("GET", f"{LIVE}/api/upload", False),
    ("GET", f"{LIVE}/api/photo/ph-x?t=token", False),
    # The Worker writes a row to the production database on any request here, a GET included.
    ("GET", f"{LIVE}/api/skeleton", False),
    ("PUT", f"{LIVE}/", False),
    ("DELETE", f"{LIVE}/api/two", False),
    ("GET", "https://api.enora-oah.eu/fhir/Observation", False),
    ("GET", "https://second-look-api.thealexschroeder.workers.dev/api/two", False),
    ("GET", "not a url", False),
]
LOCAL_ALLOWED = ["http://127.0.0.1:3217", "http://127.0.0.1:8100", "http://localhost:8000"]
LOCAL_CASES = [
    ("http://127.0.0.1:3217/t", True),
    ("http://127.0.0.1:8100/api/test/session", True),
    ("http://localhost:8000/api/test/session", True),
    ("blob:http://127.0.0.1:3217/1", True),
    (f"{LIVE}/api/test/session", False),
    ("http://127.0.0.1:3100/", False),
]


def run_guard() -> dict[str, list[bool]]:
    script = (
        f"import {{ liveRequestAllowed, localRequestAllowed }} from {json.dumps(GUARD.as_uri())};\n"
        f"const live = {json.dumps([[m, u] for m, u, _ in LIVE_CASES])};\n"
        f"const local = {json.dumps([u for u, _ in LOCAL_CASES])};\n"
        f"const origin = {json.dumps(LIVE)};\n"
        f"const allowed = {json.dumps(LOCAL_ALLOWED)};\n"
        "console.log(JSON.stringify({\n"
        "  live: live.map(([m, u]) => liveRequestAllowed(m, u, origin)),\n"
        "  local: local.map((u) => localRequestAllowed(u, allowed)),\n"
        "}));\n"
    )
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    result: dict[str, list[bool]] = json.loads(done.stdout)
    return result


def test_the_live_guard_lets_through_reading_only() -> None:
    got = run_guard()["live"]
    want = [ok for _, _, ok in LIVE_CASES]
    wrong = [case for case, g, w in zip(LIVE_CASES, got, want, strict=True) if g != w]
    assert wrong == []


def test_the_local_run_stays_on_this_machine() -> None:
    got = run_guard()["local"]
    want = [ok for _, ok in LOCAL_CASES]
    wrong = [case for case, g, w in zip(LOCAL_CASES, got, want, strict=True) if g != w]
    assert wrong == []


def test_the_gallery_script_routes_every_request_through_the_guard() -> None:
    source = (ROOT / "apps" / "web" / "scripts" / "gallery.mjs").read_text(encoding="utf-8")
    assert "liveRequestAllowed(req.method(), req.url(), LIVE)" in source
    assert "localRequestAllowed(url, allowed)" in source
    # A refused request fails the run instead of passing quietly.
    assert "if (refused.length)" in source
    assert "process.exit(1)" in source


def test_the_walk_record_shot_is_taken_from_the_top_of_the_page() -> None:
    # CRITIC_06 H03: the shot opened on a line cut in half, with the page title out of the frame.
    # The step itself is tested in apps/web/tests/walk.spec.ts; this checks the gallery takes it
    # after the record shows and before the shot.
    source = (ROOT / "apps" / "web" / "scripts" / "gallery.mjs").read_text(encoding="utf-8")
    imports = 'import { toPageTop, toRegionTop, wholeOnFirstScreen } from "./gallery-view.mjs";'
    assert imports in source
    record = source.index('getByRole("heading", { name: "Your record from the clip" }).waitFor()')
    shot = source.index('gallery("walk-record"')
    assert "await toPageTop(page);" in source[record:shot]


def test_the_walk_shot_fails_unless_its_start_button_is_on_the_first_screen() -> None:
    # CRITIC_11 V01: a note above the button pushed Start the check below the first screen, and
    # the picture of a walk showed no button while its alt text named one. The gallery now fails
    # unless the button is whole on the first screen before it shoots, the step
    # apps/web/tests/walk.spec.ts takes on every walk.
    source = (ROOT / "apps" / "web" / "scripts" / "gallery.mjs").read_text(encoding="utf-8")
    shot = source.index('gallery("walk", route')
    before = source[source.index("const route = `/walk/${firstWalk.id}`;") : shot]
    assert 'await wholeOnFirstScreen(page, button(page, "Start the check"));' in before
    assert "await shoot(page)" in source[shot : shot + 200]
    assert "a button to start the check" in source[shot : shot + 200]


WALK_CITY_ALT = (
    "The walk seen as a city would see it, after answering Artificial for the bank: what this "
    "demo creek needs, in OneAquaHealth's own measures, each with its source."
)


def test_the_walk_city_shot_follows_a_walk_that_reported_only_a_built_bank() -> None:
    # CRITIC_09 Q01: the gallery tapped the first button on every screen, which answers Yes to every
    # yes or no question, so its picture showed dams, pipes and plants the natural clip does not
    # show. It now answers the walk with scripts/gallery-walk.mjs, Artificial for the bank and no
    # other damage, which apps/web/tests/walk.spec.ts runs too, and the alt text says so.
    source = (ROOT / "apps" / "web" / "scripts" / "gallery.mjs").read_text(encoding="utf-8")
    assert 'import { answerWalkPlainly } from "./gallery-walk.mjs";' in source
    progress = source.index('gallery("walk-in-progress"')
    record = source.index('gallery("walk-record"')
    walk = source[progress:record]
    assert 'await answerWalkPlainly(page, content, { bank: "present" });' in walk
    # Nothing else answers a question between the two shots.
    assert ".click()" not in walk
    city = source.index('gallery("walk-city"')
    assert json.dumps(WALK_CITY_ALT) in source[city : city + 400]
    screens = (ROOT / "docs" / "screens" / "README.md").read_text(encoding="utf-8")
    assert f'<img src="walk-city.webp" width="200" alt="{WALK_CITY_ALT}">' in screens
    # CRITIC_11 V02: the visible caption says it too, not the alt text alone.
    assert "<br>The walk as a city sees it, after answering Artificial for the bank<br>" in screens


def test_the_quick_check_shot_shows_the_form_from_a_record_link_on_the_mock() -> None:
    # CRITIC_09 R04: /quick with no spot has no form, since it could never be sent, and the live
    # site has no stored spot. The picture of the form comes from the local mock, from the link the
    # sample record gives, and the gallery names that route.
    source = (ROOT / "apps" / "web" / "scripts" / "gallery.mjs").read_text(encoding="utf-8")
    local = source[source.index("async function localRun") : source.index("async function liveRun")]
    live = source[source.index("async function liveRun") :]
    assert "await page.goto(`${LOCAL}/quick?spot=example`);" in local
    assert 'gallery("quick", "/quick?spot=example", "local mock", await shoot(page),' in local
    assert 'gallery("quick"' not in live
    screens = (ROOT / "docs" / "screens" / "README.md").read_text(encoding="utf-8")
    assert "<br>Quick check<br><code>/quick?spot=example</code> (mock)</td>" in screens


def test_the_walk_city_shot_is_taken_from_the_needs_region() -> None:
    # CRITIC_07 J04: the city view's shot cut the first measure off before its source. The step is
    # tested in apps/web/tests/walk.spec.ts; this checks the gallery takes it before the shot.
    source = (ROOT / "apps" / "web" / "scripts" / "gallery.mjs").read_text(encoding="utf-8")
    city = source.index("await page.waitForURL(/\\/city/);")
    shot = source.index('gallery("walk-city"')
    assert 'await toRegionTop(page, content.locale["city.walk_needs"]);' in source[city:shot]
