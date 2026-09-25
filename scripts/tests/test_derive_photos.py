"""Smaller copies of the warm-up photos: made the same way every time, traced to their source.

Hard rule 6 says every image has a manifest row and CI enforces it. A copy's row lives in
photos/derived/manifest.csv and names the source row and the source's sha256. Each test below
breaks one thing a copy must be and checks that scripts/check_manifest.py says so.
"""

from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Callable
from pathlib import Path

import pytest
from PIL import Image, ImageCms, ImageDraw

from core import content_loader
from scripts import check_manifest, derive_photos

WIDTHS = {"avif": (80, 160), "webp": (80,)}
SOURCE_ID = "ph-warmup-01"


def picture(size: tuple[int, int] = (320, 216)) -> Image.Image:
    """A made-up test pattern with no symmetry, so a crop or a mirror image shows up."""
    w, h = size
    image = Image.linear_gradient("L").resize(size).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((w // 10, h // 5, w // 3, h // 2), fill=(200, 40, 40))
    draw.ellipse((w // 2, h // 3, w - w // 8, h - h // 10), fill=(30, 90, 200))
    draw.line((0, h - 1, w - 1, 0), fill=(250, 250, 0), width=5)
    return image


def row(photo_id: str, file: str, sha: str, role: str = "warmup") -> dict[str, str]:
    base = dict.fromkeys(check_manifest.REQUIRED_COLUMNS, "")
    return {
        **base,
        "id": photo_id,
        "file": file,
        "sha256": sha,
        "author": "Second Look",
        "license": "own-CC-BY-4.0",
        "scene_id": photo_id,
        "role": role,
        "synthetic": "false",
        "faces": "false",
    }


def write_manifest(root: Path, rows: list[dict[str, str]]) -> None:
    with (root / "photos" / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=check_manifest.REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "photos" / "warmup").mkdir(parents=True)
    source = root / "photos" / "warmup" / f"{SOURCE_ID}.jpg"
    picture().save(source, "JPEG", quality=90)
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    write_manifest(root, [row(SOURCE_ID, f"warmup/{SOURCE_ID}.jpg", sha)])
    return root


def make_copies(root: Path) -> list[derive_photos.Copy]:
    copies = derive_photos.derive(root, ids=(SOURCE_ID,), widths=WIDTHS)
    derive_photos.write(root, copies)
    return copies


def derived_rows(root: Path) -> list[dict[str, str]]:
    return content_loader.derived_rows(root)


def save_rows(root: Path, rows: list[dict[str, str]]) -> None:
    path = root / "photos" / "derived" / "manifest.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=content_loader.DERIVED_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def replace_copy(root: Path, rel: str, image: Image.Image, **save: object) -> None:
    """Swap a copy for another image and make its row agree, so only the picture is wrong."""
    buffer = io.BytesIO()
    image.save(buffer, "AVIF" if rel.endswith(".avif") else "WEBP", **save)
    data = buffer.getvalue()
    (root / "photos" / rel).write_bytes(data)
    rows = derived_rows(root)
    for r in rows:
        if r["file"] == rel:
            r.update(
                sha256=hashlib.sha256(data).hexdigest(),
                bytes=str(len(data)),
                width=str(image.width),
                height=str(image.height),
            )
    save_rows(root, rows)


def problems(root: Path, capsys: pytest.CaptureFixture[str]) -> str:
    capsys.readouterr()
    assert check_manifest.main(root) == 1
    return capsys.readouterr().out


def test_copies_of_a_warmup_photo_pass_the_manifest_check(repo: Path) -> None:
    copies = make_copies(repo)
    assert [c.file for c in copies] == [
        "derived/ph-warmup-01-160.avif",
        "derived/ph-warmup-01-80.avif",
        "derived/ph-warmup-01-80.webp",
    ]
    assert check_manifest.main(repo) == 0
    loaded: list[str] = []
    content_loader._load_manifest(repo, loaded)
    assert loaded == []


def test_a_copy_is_the_whole_source_scaled_down_with_the_same_aspect_ratio(repo: Path) -> None:
    for c in make_copies(repo):
        assert c.height == round(c.width * 216 / 320)
        with Image.open(repo / "photos" / c.file) as im:
            assert im.size == (c.width, c.height)


def test_the_copies_are_the_same_bytes_every_time(repo: Path) -> None:
    first = derive_photos.derive(repo, ids=(SOURCE_ID,), widths=WIDTHS)
    second = derive_photos.derive(repo, ids=(SOURCE_ID,), widths=WIDTHS)
    assert [c.data for c in first] == [c.data for c in second]
    derive_photos.write(repo, first)
    assert derive_photos.differences(repo, second) == []


def test_no_exif_or_colour_profile_rides_along_from_the_source(repo: Path) -> None:
    source = repo / "photos" / "warmup" / f"{SOURCE_ID}.jpg"
    exif = Image.Exif()
    exif[0x010F] = "Some Camera Maker"  # Make
    exif[0x0131] = "Some Program"  # Software
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    picture().save(source, "JPEG", quality=90, exif=exif, icc_profile=icc)
    with Image.open(source) as im:
        assert im.getexif() and im.info.get("icc_profile")
    write_manifest(
        repo, [row(SOURCE_ID, f"warmup/{SOURCE_ID}.jpg", check_manifest.sha256_of(source))]
    )
    for c in make_copies(repo):
        with Image.open(repo / "photos" / c.file) as im:
            assert not im.getexif()
            assert not [k for k in check_manifest.METADATA_KEYS if im.info.get(k)]
        assert b"Some Camera Maker" not in c.data
    assert check_manifest.main(repo) == 0


def test_a_test_photo_gets_no_copies(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    make_copies(repo)
    source = repo / "photos" / "warmup" / f"{SOURCE_ID}.jpg"
    write_manifest(
        repo,
        [row(SOURCE_ID, f"warmup/{SOURCE_ID}.jpg", check_manifest.sha256_of(source), "test")],
    )
    with pytest.raises(derive_photos.DeriveError, match="warm-up only"):
        derive_photos.derive(repo, ids=(SOURCE_ID,), widths=WIDTHS)
    assert "copy of a test photo" in problems(repo, capsys)


def test_a_copy_wider_than_its_source_is_refused(repo: Path) -> None:
    with pytest.raises(derive_photos.DeriveError, match="wider than the source"):
        derive_photos.derive(repo, ids=(SOURCE_ID,), widths={"avif": (640,)})


def test_a_copy_that_cannot_fit_the_byte_cap_is_refused(repo: Path) -> None:
    with pytest.raises(derive_photos.DeriveError, match="the floor is"):
        derive_photos.derive(repo, ids=(SOURCE_ID,), widths={"webp": (320,)}, max_bytes=50)


def extra_file(root: Path) -> None:
    (root / "photos" / "derived" / "ph-warmup-01-120.avif").write_bytes(
        (root / "photos" / "derived" / "ph-warmup-01-80.avif").read_bytes()
    )


def stale_source(root: Path) -> None:
    rows = derived_rows(root)
    rows[0]["source_sha256"] = "0" * 64
    save_rows(root, rows)


def unknown_source(root: Path) -> None:
    rows = derived_rows(root)
    rows[0]["source_id"] = "ph-warmup-99"
    save_rows(root, rows)


def wrong_name(root: Path) -> None:
    folder = root / "photos" / "derived"
    (folder / "ph-warmup-01-80.avif").rename(folder / "landing-small.avif")
    rows = derived_rows(root)
    for r in rows:
        if r["file"] == "derived/ph-warmup-01-80.avif":
            r["file"] = "derived/landing-small.avif"
    save_rows(root, rows)


def cropped(root: Path) -> None:
    whole = picture()
    part = whole.crop((16, 11, 304, 205)).resize((160, 108), Image.Resampling.LANCZOS)
    replace_copy(root, "derived/ph-warmup-01-160.avif", part, quality=90)


def squashed(root: Path) -> None:
    replace_copy(root, "derived/ph-warmup-01-160.avif", picture().resize((160, 80)), quality=90)


def with_exif(root: Path) -> None:
    exif = Image.Exif()
    exif[0x010F] = "Some Camera Maker"
    image = picture().resize((160, 108))
    replace_copy(root, "derived/ph-warmup-01-160.avif", image, quality=90, exif=exif)


def edited_bytes(root: Path) -> None:
    path = root / "photos" / "derived" / "ph-warmup-01-80.webp"
    path.write_bytes(path.read_bytes() + b"\0")


def missing_file(root: Path) -> None:
    (root / "photos" / "derived" / "ph-warmup-01-80.webp").unlink()


def stray_avif(root: Path) -> None:
    (root / "photos" / "warmup" / "extra.avif").write_bytes(
        (root / "photos" / "derived" / "ph-warmup-01-80.avif").read_bytes()
    )


@pytest.mark.parametrize(
    ("breakage", "message"),
    [
        (extra_file, "no derived manifest row: photos/derived/ph-warmup-01-120.avif"),
        (stale_source, "copy of another version of warmup/ph-warmup-01.jpg"),
        (unknown_source, "copy of a photo with no manifest row"),
        (wrong_name, "copy not named <source id>-<width>.<format>"),
        (cropped, "copy is not the whole source picture"),
        (squashed, "copy changes the aspect ratio of its source"),
        (with_exif, "copy carries metadata"),
        (edited_bytes, "sha256 mismatch: photos/derived/ph-warmup-01-80.webp"),
        (missing_file, "derived manifest row without file: photos/derived/ph-warmup-01-80.webp"),
        (stray_avif, "no manifest row: photos/warmup/extra.avif"),
    ],
    ids=lambda v: v.__name__ if callable(v) else "",
)
def test_each_broken_copy_fails_the_manifest_check(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    breakage: Callable[[Path], None],
    message: str,
) -> None:
    make_copies(repo)
    assert check_manifest.main(repo) == 0
    breakage(repo)
    assert message in problems(repo, capsys)


def test_a_copy_over_the_byte_cap_fails_the_manifest_check(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    make_copies(repo)
    monkeypatch.setattr(content_loader, "DERIVED_MAX_BYTES", 100)
    assert "copy over 100 bytes" in problems(repo, capsys)


def test_the_content_loader_counts_a_copy_only_through_a_valid_row(repo: Path) -> None:
    make_copies(repo)
    stale_source(repo)
    found: list[str] = []
    content_loader._load_manifest(repo, found)
    assert found == ["photo without manifest row: photos/derived/ph-warmup-01-160.avif"]


def test_the_committed_copies_are_under_the_cap_and_only_of_the_two_warmup_photos() -> None:
    rows = derived_rows(derive_photos.ROOT)
    assert {r["source_id"] for r in rows} == set(derive_photos.SOURCES)
    assert all(int(r["bytes"]) <= content_loader.DERIVED_MAX_BYTES for r in rows)
    assert {(r["format"], int(r["width"])) for r in rows} == {
        (fmt, w) for fmt, widths in derive_photos.WIDTHS.items() for w in widths
    }


# UPDATE_30 section 1 item 1: one phone-size AVIF of every photo of the test, in photos/offline/,
# for the service worker to keep in place of the full-size photos. The same rules as the copies
# above, with the roles of the test and a cap of their own.
OFFLINE_WIDTHS: dict[str, tuple[int, ...]] = {"avif": (160,)}


def make_offline_copies(root: Path, role: str = "test") -> list[derive_photos.Copy]:
    source = root / "photos" / "warmup" / f"{SOURCE_ID}.jpg"
    sha = check_manifest.sha256_of(source)
    write_manifest(root, [row(SOURCE_ID, f"warmup/{SOURCE_ID}.jpg", sha, role)])
    copies = derive_photos.derive(
        root, ids=(SOURCE_ID,), widths=OFFLINE_WIDTHS, spec=derive_photos.OFFLINE
    )
    derive_photos.write(root, copies, content_loader.OFFLINE_DIR)
    return copies


def save_offline_rows(root: Path, rows: list[dict[str, str]]) -> None:
    path = root / "photos" / "offline" / "manifest.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=content_loader.DERIVED_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_an_offline_copy_of_a_test_photo_passes_the_manifest_check(repo: Path) -> None:
    copies = make_offline_copies(repo)
    assert [c.file for c in copies] == ["offline/ph-warmup-01-160.avif"]
    assert content_loader.offline_rows(repo)[0]["source_id"] == SOURCE_ID
    assert check_manifest.main(repo) == 0
    loaded: list[str] = []
    content_loader._load_manifest(repo, loaded)
    assert loaded == []


def test_a_benchmark_photo_gets_no_offline_copy(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    make_offline_copies(repo)
    source = repo / "photos" / "warmup" / f"{SOURCE_ID}.jpg"
    sha = check_manifest.sha256_of(source)
    write_manifest(repo, [row(SOURCE_ID, f"warmup/{SOURCE_ID}.jpg", sha, "benchmark")])
    with pytest.raises(derive_photos.DeriveError, match="offline copies are for the photos of"):
        derive_photos.derive(
            repo, ids=(SOURCE_ID,), widths=OFFLINE_WIDTHS, spec=derive_photos.OFFLINE
        )
    out = problems(repo, capsys)
    assert "copy of a benchmark photo: photos/offline/ph-warmup-01-160.avif" in out


def test_an_offline_copy_over_its_cap_fails_the_manifest_check(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    make_offline_copies(repo)
    monkeypatch.setattr(content_loader, "OFFLINE_MAX_BYTES", 100)
    out = problems(repo, capsys)
    assert "copy over 100 bytes: photos/offline/ph-warmup-01-160.avif" in out


def test_an_offline_copy_without_its_row_fails_both_checks(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    make_offline_copies(repo)
    save_offline_rows(repo, [])
    assert "no offline manifest row: photos/offline/ph-warmup-01-160.avif" in problems(repo, capsys)
    found: list[str] = []
    content_loader._load_manifest(repo, found)
    assert found == ["photo without manifest row: photos/offline/ph-warmup-01-160.avif"]


def test_an_offline_copy_is_avif_only(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    [avif] = make_offline_copies(repo)
    with Image.open(repo / "photos" / "warmup" / f"{SOURCE_ID}.jpg") as source:
        data = derive_photos.encode(derive_photos.scaled(source, 160), "webp", 75)
    (repo / "photos" / "offline" / "ph-warmup-01-160.webp").write_bytes(data)
    extra = {
        **avif.row(),
        "file": "offline/ph-warmup-01-160.webp",
        "format": "webp",
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": str(len(data)),
    }
    save_offline_rows(repo, [*content_loader.offline_rows(repo), extra])
    out = problems(repo, capsys)
    assert "copy not named <source id>-<width>.<format>: photos/offline/ph-warmup-01-160.webp" in (
        out
    )


def test_every_photo_of_the_test_has_its_offline_copy_under_the_cap() -> None:
    """The committed copies: one AVIF of each warm-up, lesson, practice and test photo, made from
    the photo as it is now. build-content.mjs also fails the web build on a missing one."""
    root = derive_photos.ROOT
    rows = content_loader.offline_rows(root)
    by_id = derive_photos.manifest_rows(root)
    wanted = {i for i, r in by_id.items() if r["role"] in content_loader.OFFLINE_ROLES}
    assert sorted(r["source_id"] for r in rows) == sorted(wanted)
    for r in rows:
        assert r["source_sha256"] == by_id[r["source_id"]]["sha256"], r["file"]
        assert r["format"] == "avif", r["file"]
        assert int(r["width"]) == derive_photos.OFFLINE_WIDTH, r["file"]
        assert int(r["bytes"]) <= content_loader.OFFLINE_MAX_BYTES, r["file"]
        assert (root / "photos" / r["file"]).exists(), r["file"]
