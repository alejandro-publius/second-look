"""Ingest strips every trace of EXIF, resizes, hashes after processing and writes correct rows."""

from __future__ import annotations

import csv
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from scripts import ingest_photos
from scripts.ingest_photos import MANIFEST_COLUMNS, IngestError, ingest

GPS_IFD = 0x8825
EXIF_MARKER = b"Exif\x00\x00"


def gray_jpeg_with_gps(
    path: Path, size: tuple[int, int] = (2400, 1600), orientation: int = 1
) -> None:
    img = Image.new("RGB", size, (128, 128, 128))
    exif = Image.Exif()
    exif[0x0110] = "FakePhone 9"
    exif[0x0112] = orientation
    exif[0x0132] = "2026:09:20 10:00:00"
    exif[GPS_IFD] = {1: "N", 2: (37.0, 52.0, 30.0), 3: "W", 4: (122.0, 15.0, 10.0), 6: 40.0}
    img.save(path, "JPEG", exif=exif)


def png_with_text(path: Path) -> None:
    from PIL import PngImagePlugin

    img = Image.new("RGB", (900, 1200), (100, 100, 100))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Comment", "taken at 37.87,-122.26")
    img.save(path, "PNG", pnginfo=meta)


def write_labels(path: Path, rows: list[dict[str, str]]) -> None:
    columns = ingest_photos.LABEL_COLUMNS + ["notes", "synthetic", "faces"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in columns})


def label_row(
    file: str, role: str = "test", feature: str = "pipe_running", **extra: str
) -> dict[str, str]:
    row = {
        "photo_file": file,
        "role": role,
        "feature": feature,
        "gold_label": "present",
        "scene_id": f"scene-{file}",
        "capture_date": "2026-09-20",
        "coarse_location": "Strawberry Creek, Berkeley",
        "author": "Rachel Selbrede",
        "license": "own-CC-BY-4.0",
        "source_url": "",
    }
    row.update(extra)
    return row


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "photos" / "placeholders").mkdir(parents=True)
    ph = root / "photos" / "placeholders" / "ph-test-01.jpg"
    Image.new("RGB", (120, 90), (128, 128, 128)).save(ph, "JPEG")
    with (root / "photos" / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        w.writeheader()
        w.writerow(
            {
                "id": "ph-test-01",
                "file": "placeholders/ph-test-01.jpg",
                "sha256": hashlib.sha256(ph.read_bytes()).hexdigest(),
                "license": "placeholder",
                "role": "test",
                "feature": "artificial_bank",
                "gold_label": "present",
                "synthetic": "false",
                "faces": "false",
            }
        )
    return root


@pytest.fixture()
def originals(tmp_path: Path) -> Path:
    folder = tmp_path / "from_rachel"
    folder.mkdir()
    gray_jpeg_with_gps(folder / "IMG_0001.jpg")
    gray_jpeg_with_gps(folder / "IMG_0002.JPG", size=(800, 600))
    png_with_text(folder / "shot3.png")
    assert EXIF_MARKER in (folder / "IMG_0001.jpg").read_bytes()
    return folder


def manifest_rows(root: Path) -> list[dict[str, str]]:
    with (root / "photos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_ingest_strips_exif_resizes_and_writes_rows(repo: Path, originals: Path) -> None:
    labels = originals.parent / "labels.csv"
    write_labels(
        labels,
        [
            label_row("IMG_0001.jpg", notes="wide shot"),
            label_row(
                "IMG_0002.JPG", role="lesson", feature="artificial_bank", gold_label="absent"
            ),
            label_row("shot3.png", role="warmup", feature="", gold_label=""),
        ],
    )
    rows = ingest(originals, labels, "rachel1", repo)

    assert [r["id"] for r in rows] == ["ph-rachel1-01", "ph-rachel1-02", "ph-rachel1-03"]
    for row in rows:
        out = repo / "photos" / row["file"]
        assert out.exists() and out.suffix == ".jpg"
        data = out.read_bytes()
        assert EXIF_MARKER not in data, f"{row['id']} still has an EXIF segment"
        assert b"37.87" not in data and b"FakePhone" not in data
        with Image.open(out) as img:
            assert dict(img.getexif()) == {}
            assert img.getexif().get_ifd(GPS_IFD) == {}
            assert "exif" not in img.info and "comment" not in img.info
            assert max(img.size) <= 1600
        assert row["sha256"] == hashlib.sha256(data).hexdigest(), (
            "hash must be of the processed file"
        )
        assert row["synthetic"] == "false" and row["faces"] == "false" and row["labeller_2"] == ""

    with Image.open(repo / "photos" / rows[0]["file"]) as img:
        assert img.size == (1600, 1067)
    with Image.open(repo / "photos" / rows[1]["file"]) as img:
        assert img.size == (800, 600), "small originals are not enlarged"

    written = manifest_rows(repo)
    assert written[0]["id"] == "ph-test-01", "existing rows are kept"
    assert [r["id"] for r in written[1:]] == [r["id"] for r in rows]
    by_id = {r["id"]: r for r in written}
    assert by_id["ph-rachel1-01"]["role"] == "test"
    assert by_id["ph-rachel1-01"]["feature"] == "pipe_running"
    assert by_id["ph-rachel1-01"]["gold_label"] == "present"
    assert by_id["ph-rachel1-01"]["notes"] == "wide shot"
    assert by_id["ph-rachel1-01"]["license"] == "own-CC-BY-4.0"
    assert by_id["ph-rachel1-01"]["file"] == "rachel1/ph-rachel1-01.jpg"
    assert by_id["ph-rachel1-02"]["gold_label"] == "absent"
    assert by_id["ph-rachel1-03"]["feature"] == "" and by_id["ph-rachel1-03"]["role"] == "warmup"

    kept = sorted(p.name for p in (repo / "data" / "originals" / "rachel1").iterdir())
    assert kept == ["IMG_0001.jpg", "IMG_0002.JPG", "shot3.png"]
    assert EXIF_MARKER in (repo / "data" / "originals" / "rachel1" / "IMG_0001.jpg").read_bytes()
    under_photos = [p for p in (repo / "photos").rglob("*") if p.is_file()]
    assert all(p.suffix in {".jpg", ".csv"} for p in under_photos)
    assert not any(p.name.startswith("IMG_") for p in under_photos), "originals never under photos/"


def test_second_batch_continues_numbering(repo: Path, originals: Path) -> None:
    labels = originals.parent / "labels.csv"
    write_labels(labels, [label_row("IMG_0001.jpg")])
    ingest(originals, labels, "rachel1", repo)
    write_labels(labels, [label_row("IMG_0002.JPG", scene_id="other")])
    rows = ingest(originals, labels, "rachel1", repo)
    assert rows[0]["id"] == "ph-rachel1-02"
    assert len(manifest_rows(repo)) == 3


def test_orientation_tag_is_applied_before_stripping(repo: Path, tmp_path: Path) -> None:
    folder = tmp_path / "rot"
    folder.mkdir()
    gray_jpeg_with_gps(folder / "sideways.jpg", size=(2000, 1000), orientation=6)
    labels = tmp_path / "labels.csv"
    write_labels(labels, [label_row("sideways.jpg")])
    rows = ingest(folder, labels, "rot", repo)
    with Image.open(repo / "photos" / rows[0]["file"]) as img:
        assert img.size == (800, 1600), "rotated upright, then resized"
        assert dict(img.getexif()) == {}


def test_refuses_synthetic_or_faces_and_writes_nothing(repo: Path, originals: Path) -> None:
    labels = originals.parent / "labels.csv"
    before = (repo / "photos" / "manifest.csv").read_bytes()
    write_labels(labels, [label_row("IMG_0001.jpg", synthetic="true")])
    with pytest.raises(IngestError, match="synthetic"):
        ingest(originals, labels, "rachel1", repo)
    write_labels(labels, [label_row("IMG_0001.jpg", faces="TRUE")])
    with pytest.raises(IngestError, match="faces"):
        ingest(originals, labels, "rachel1", repo)
    assert (repo / "photos" / "manifest.csv").read_bytes() == before
    assert not (repo / "photos" / "rachel1").exists()
    assert not (repo / "data").exists()


def test_refuses_bad_rows_all_at_once(repo: Path, originals: Path) -> None:
    labels = originals.parent / "labels.csv"
    write_labels(
        labels,
        [
            label_row("missing.jpg"),
            label_row("IMG_0001.jpg", license="placeholder"),
            label_row("IMG_0002.JPG", role="portrait"),
            label_row("shot3.png", gold_label="maybe", feature="tree"),
            label_row("IMG_0001.jpg"),
        ],
    )
    with pytest.raises(IngestError) as e:
        ingest(originals, labels, "rachel1", repo)
    text = str(e.value)
    for needle in ("not found", "license", "role", "gold_label", "feature", "listed twice"):
        assert needle in text, f"expected a complaint about {needle}"
    assert not (repo / "photos" / "rachel1").exists()


def test_refuses_originals_under_photos(repo: Path) -> None:
    inside = repo / "photos" / "incoming"
    inside.mkdir()
    gray_jpeg_with_gps(inside / "a.jpg")
    labels = repo / "labels.csv"
    write_labels(labels, [label_row("a.jpg")])
    with pytest.raises(IngestError, match="never enter the repo"):
        ingest(inside, labels, "rachel1", repo)


def test_refuses_bad_batch_name_and_missing_columns(
    repo: Path, originals: Path, tmp_path: Path
) -> None:
    labels = tmp_path / "labels.csv"
    write_labels(labels, [label_row("IMG_0001.jpg")])
    with pytest.raises(IngestError, match="batch must be"):
        ingest(originals, labels, "Rachel Day-1", repo)
    (tmp_path / "short.csv").write_text("photo_file,role\nIMG_0001.jpg,test\n", encoding="utf-8")
    with pytest.raises(IngestError, match="missing columns"):
        ingest(originals, tmp_path / "short.csv", "rachel1", repo)


def test_cli_refusal_exits_1_and_success_exits_0(
    repo: Path, originals: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    labels = originals.parent / "labels.csv"
    write_labels(labels, [label_row("IMG_0001.jpg", synthetic="yes")])
    args = [
        "--originals",
        str(originals),
        "--labels",
        str(labels),
        "--batch",
        "r1",
        "--root",
        str(repo),
    ]
    assert ingest_photos.main(args) == 1
    assert "refused, nothing written" in capsys.readouterr().out
    write_labels(labels, [label_row("IMG_0001.jpg")])
    assert ingest_photos.main(args) == 0
    assert "1 photos into photos/r1/" in capsys.readouterr().out


@pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("sips"), reason="needs sips")
def test_heic_through_sips(repo: Path, tmp_path: Path) -> None:
    folder = tmp_path / "heic"
    folder.mkdir()
    gray_jpeg_with_gps(folder / "src.jpg")
    proc = subprocess.run(
        [
            "sips",
            "-s",
            "format",
            "heic",
            str(folder / "src.jpg"),
            "--out",
            str(folder / "IMG.HEIC"),
        ],
        capture_output=True,
    )
    if proc.returncode != 0 or not (folder / "IMG.HEIC").exists():
        pytest.skip("sips could not write HEIC on this machine")
    (folder / "src.jpg").unlink()
    labels = tmp_path / "labels.csv"
    write_labels(labels, [label_row("IMG.HEIC")])
    rows = ingest(folder, labels, "heic", repo)
    out = repo / "photos" / rows[0]["file"]
    assert EXIF_MARKER not in out.read_bytes()
    with Image.open(out) as img:
        assert img.format == "JPEG" and dict(img.getexif()) == {} and max(img.size) <= 1600
