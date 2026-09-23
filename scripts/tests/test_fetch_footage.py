"""The footage fetch refuses a changed licence, and records what it kept (UPDATE_22 6.2).

No test here touches a real API. Every request is mocked.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from scripts import fetch_footage
from scripts.fetch_footage import (
    FOOTAGE_CSV,
    LICENCE_URLS,
    Row,
    fetch_row,
    licence_check,
    licence_key,
    read_rows,
)
from scripts.find_open_photos import COMMONS_API

FILE_URL = "https://upload.wikimedia.org/wikipedia/commons/a/aa/Creek.webm"
BODY = b"not really a video, only bytes to hash"


class NoWait:
    """A limiter that counts the requests it let through."""

    def __init__(self) -> None:
        self.calls = 0

    def wait(self) -> None:
        self.calls += 1


def row(licence: str = "CC BY-SA 4.0", author: str = "Coro") -> Row:
    return Row(
        kind="video",
        beat="natural",
        title="Creek.webm",
        source_page="https://commons.wikimedia.org/wiki/File:Creek.webm",
        file_url=FILE_URL,
        author=author,
        licence=licence,
        duration_s="10",
        use="test",
    )


def info(licence: str = "CC BY-SA 4.0", sha1: str | None = None) -> dict[str, Any]:
    return {
        "url": FILE_URL,
        "size": len(BODY),
        "sha1": sha1 if sha1 is not None else hashlib.sha1(BODY).hexdigest(),
        "width": 1920,
        "height": 1080,
        "duration": 10.01,
        "extmetadata": {
            "LicenseShortName": {"value": licence},
            "Artist": {"value": '<a href="//commons.wikimedia.org/wiki/User:Coro">Coro</a>'},
        },
    }


def payload(**kwargs: Any) -> dict[str, Any]:
    return {"query": {"pages": [{"title": "File:Creek.webm", "imageinfo": [info(**kwargs)]}]}}


def test_the_same_licence_in_another_spelling_is_the_same() -> None:
    assert licence_key("CC BY-SA 4.0") == licence_key("CC-BY-SA-4.0") == "cc by-sa 4.0"
    assert licence_key("CC0") == licence_key("CC0 1.0")
    assert licence_key("Public domain") == licence_key("PD")


def test_a_changed_licence_is_refused() -> None:
    check = licence_check(row("CC BY-SA 4.0"), info("CC BY-NC-SA 4.0"))
    assert check["kept"] is False
    assert "licence changed" in check["reason"]
    assert "CC BY-NC-SA 4.0" in check["reason"]


def test_a_new_version_of_the_licence_is_a_change_too() -> None:
    assert licence_check(row("CC BY-SA 3.0"), info("CC BY-SA 4.0"))["kept"] is False


def test_a_page_with_no_licence_is_refused() -> None:
    check = licence_check(row(), info(""))
    assert check["kept"] is False
    assert "nothing" in check["reason"]


def test_the_same_licence_is_kept_and_the_author_is_read_from_the_page() -> None:
    check = licence_check(row(), info())
    assert check["kept"] is True
    assert check["artist_commons"] == "Coro"
    assert check["author_named_on_page"] is True


@respx.mock
def test_a_changed_licence_downloads_nothing(tmp_path: Path) -> None:
    respx.get(COMMONS_API).mock(return_value=httpx.Response(200, json=payload(licence="GFDL")))
    download = respx.get(FILE_URL).mock(return_value=httpx.Response(200, content=BODY))
    with httpx.Client() as client:
        entry = fetch_row(row(), client, NoWait(), tmp_path)  # type: ignore[arg-type]
    assert entry["kept"] is False
    assert "licence changed" in entry["reason"]
    assert download.call_count == 0
    assert list(tmp_path.iterdir()) == []


@respx.mock
def test_a_kept_item_is_downloaded_with_its_size_and_hash(tmp_path: Path) -> None:
    respx.get(COMMONS_API).mock(return_value=httpx.Response(200, json=payload()))
    respx.get(FILE_URL).mock(return_value=httpx.Response(200, content=BODY))
    limiter = NoWait()
    with httpx.Client() as client:
        entry = fetch_row(row(), client, limiter, tmp_path)  # type: ignore[arg-type]
    assert entry["kept"] is True, entry
    assert entry["bytes"] == len(BODY)
    assert entry["sha1"] == hashlib.sha1(BODY).hexdigest()
    assert (tmp_path / "Creek.webm").read_bytes() == BODY
    assert entry["licence_url"] == LICENCE_URLS["cc by-sa 4.0"]
    assert limiter.calls == 2  # the API, then the file: each one waits its turn


@respx.mock
def test_a_file_whose_hash_does_not_match_commons_is_dropped(tmp_path: Path) -> None:
    respx.get(COMMONS_API).mock(return_value=httpx.Response(200, json=payload(sha1="0" * 40)))
    respx.get(FILE_URL).mock(return_value=httpx.Response(200, content=BODY))
    with httpx.Client() as client:
        entry = fetch_row(row(), client, NoWait(), tmp_path)  # type: ignore[arg-type]
    assert entry["kept"] is False
    assert "sha1" in entry["reason"]


@respx.mock
def test_a_file_already_there_is_not_downloaded_again(tmp_path: Path) -> None:
    (tmp_path / "Creek.webm").write_bytes(BODY)
    respx.get(COMMONS_API).mock(return_value=httpx.Response(200, json=payload()))
    download = respx.get(FILE_URL).mock(return_value=httpx.Response(200, content=BODY))
    with httpx.Client() as client:
        entry = fetch_row(row(), client, NoWait(), tmp_path)  # type: ignore[arg-type]
    assert entry["kept"] is True
    assert entry["downloaded"] is False
    assert download.call_count == 0


@respx.mock  # no request can leave, even if the guard below were broken
def test_media_inside_the_repository_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    inside = fetch_footage.ROOT / "docs" / "video" / "media-guard-probe"
    out = tmp_path / "fetched.json"
    try:
        code = fetch_footage.main(["--media", str(inside), "--out", str(out)])
    finally:
        created = inside.exists()
        if created:
            shutil.rmtree(inside)
    assert code == 1
    assert "outside" in capsys.readouterr().out
    assert not created
    assert not out.exists()


def test_every_row_in_the_csv_has_a_licence_we_know_and_a_commons_page() -> None:
    rows = read_rows(FOOTAGE_CSV)
    assert len(rows) == 13
    for r in rows:
        assert licence_key(r.licence) in LICENCE_URLS, r.licence
        assert fetch_footage.commons_title(r.source_page).startswith("File:")


def test_the_committed_manifest_holds_no_media_and_names_every_row() -> None:
    fetched = json.loads(fetch_footage.FETCHED.read_text(encoding="utf-8"))
    titles = {r.title for r in read_rows(FOOTAGE_CSV)}
    assert {e["title"] for e in fetched["items"]} == titles
    assert fetched["committed_media"] is False
    media = Path(fetched["media_folder"]).expanduser().resolve()
    assert not media.is_relative_to(fetch_footage.ROOT.resolve())
    assert fetched["kept"] == sum(1 for e in fetched["items"] if e["kept"])
    for e in fetched["items"]:
        if e["kept"]:
            assert e["licence_same"] is True
            assert e["sha1"] == e["sha1_commons"]
            assert e["bytes"] > 0
