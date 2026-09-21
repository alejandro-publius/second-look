"""Uploads: real type only, 8 MB cap, EXIF gone, token guarded read, 30 day cleanup."""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
from pathlib import Path

from PIL import Image
from sqlmodel import Session, select

from apps.api import check
from apps.api.db import engine
from apps.api.models import UploadRow
from apps.api.tests.conftest import freeze_now
from scripts import cleanup_uploads


def _jpeg_with_exif(size=(2400, 1200)) -> bytes:
    img = Image.new("RGB", size, (90, 120, 80))
    exif = Image.Exif()
    exif[0x010F] = "Fake Phone Maker"
    exif[0x0110] = "Fake Phone 12"
    exif[0x9003] = "2026:09:20 10:11:12"
    exif[0x8825] = {1: "N", 3: "W"}  # GPS IFD with the hemisphere tags
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (40, 30), (1, 2, 3, 128)).save(buf, format="PNG")
    return buf.getvalue()


def _upload(client, data: bytes, name="photo.jpg", content_type="image/jpeg"):
    return client.post("/api/upload", files={"file": (name, data, content_type)})


def test_upload_strips_exif_downsizes_and_serves_only_with_the_token(client):
    original = _jpeg_with_exif()
    assert b"Fake Phone Maker" in original
    r = _upload(client, original)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"photo_id", "token"}
    stored = Path(check.upload_dir()) / f"{body['photo_id']}.jpg"
    raw = stored.read_bytes()
    assert b"Fake Phone Maker" not in raw and b"Exif" not in raw
    with Image.open(stored) as img:
        assert img.format == "JPEG"
        assert max(img.size) == 1600
        assert not img.getexif()
    assert client.get(f"/api/photo/{body['photo_id']}").status_code == 404
    assert client.get(f"/api/photo/{body['photo_id']}?t=wrong-token").status_code == 404
    ok = client.get(f"/api/photo/{body['photo_id']}?t={body['token']}")
    assert ok.status_code == 200
    assert ok.headers["content-type"] == "image/jpeg"
    assert ok.headers["cache-control"] == "private, no-store"
    assert ok.content == raw
    assert client.get("/api/photo/up-none?t=x").status_code == 404


def test_png_is_accepted_and_becomes_jpeg(client):
    body = _upload(client, _png(), name="shot.png", content_type="image/png").json()
    with Image.open(check.upload_dir() / f"{body['photo_id']}.jpg") as img:
        assert img.format == "JPEG" and img.mode == "RGB"


def test_type_is_checked_by_bytes_not_by_name(client):
    fake = b"GIF89a" + b"\x00" * 100
    r = _upload(client, fake, name="looks-like.jpg", content_type="image/jpeg")
    assert r.status_code == 422
    assert "JPEG, PNG or WebP" in r.json()["detail"]
    html = b"<html><body>hi</body></html>"
    assert _upload(client, html, name="page.png", content_type="image/png").status_code == 422
    broken = b"\xff\xd8\xff" + b"not really a jpeg"
    assert _upload(client, broken).status_code == 422
    with Session(engine) as db:
        assert db.exec(select(UploadRow)).all() == []


def test_over_eight_megabytes_is_refused(client):
    big = b"\xff\xd8\xff" + b"\x00" * (check.MAX_UPLOAD_BYTES + 10)
    r = _upload(client, big)
    assert r.status_code == 413
    assert "8 MB" in r.json()["detail"]


def test_sniff_image():
    assert check.sniff_image(b"\xff\xd8\xff\xe0" + b"\x00" * 12) == "image/jpeg"
    assert check.sniff_image(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8) == "image/png"
    assert check.sniff_image(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"
    assert check.sniff_image(b"RIFF\x00\x00\x00\x00WAVEfmt ") is None
    assert check.sniff_image(b"") is None


def test_cleanup_deletes_uploads_older_than_thirty_days(client):
    freeze_now(datetime(2026, 8, 1, tzinfo=UTC))
    old = _upload(client, _png(), name="a.png", content_type="image/png").json()
    freeze_now(datetime(2026, 9, 20, tzinfo=UTC))
    fresh = _upload(client, _png(), name="b.png", content_type="image/png").json()
    orphan = check.upload_dir() / "up-orphan.jpg"
    orphan.write_bytes(b"x")
    old_time = (datetime(2026, 7, 1, tzinfo=UTC)).timestamp()
    import os

    os.utime(orphan, (old_time, old_time))
    now = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    with Session(engine) as db:
        dry = cleanup_uploads.cleanup(db, check.upload_dir(), now=now, days=30, dry_run=True)
    assert dry == {"rows": 1, "files": 1, "orphans": 1}
    assert (check.upload_dir() / f"{old['photo_id']}.jpg").exists()
    with Session(engine) as db:
        done = cleanup_uploads.cleanup(db, check.upload_dir(), now=now, days=30, dry_run=False)
    assert done == {"rows": 1, "files": 1, "orphans": 1}
    assert not (check.upload_dir() / f"{old['photo_id']}.jpg").exists()
    assert not orphan.exists()
    assert (check.upload_dir() / f"{fresh['photo_id']}.jpg").exists()
    with Session(engine) as db:
        assert [u.photo_id for u in db.exec(select(UploadRow)).all()] == [fresh["photo_id"]]
    assert client.get(f"/api/photo/{old['photo_id']}?t={old['token']}").status_code == 404
    assert client.get(f"/api/photo/{fresh['photo_id']}?t={fresh['token']}").status_code == 200
    assert now - timedelta(days=30) > datetime(2026, 8, 1, tzinfo=UTC)
