"""Download the open creek footage for the video, after checking each licence again.

UPDATE_22 section 6 item 2. Reads docs/video/footage.csv (the planner's list: 6 videos and
7 photos from Wikimedia Commons). For every row it asks the Commons API for the file's licence,
author, size and sha1 (action=query, prop=imageinfo, iiprop=extmetadata|url|size|sha1). When the
licence on the source page is no longer the one in the CSV, the item is dropped and the script
says so. Otherwise the file is downloaded to ~/second-look-media/, outside the repository, and its
sha1 is checked against the one Commons gives.

At most one request a second, with a named User-Agent. A file already there with the right sha1
is not downloaded again.

What the repository keeps is text only: docs/video/footage_fetched.json, with the licence check,
the size and the hash of every item. No media file is ever committed. scripts/cut_footage.py adds
the clip checks to the same file.

Run: uv run python scripts/fetch_footage.py
     uv run python scripts/fetch_footage.py --media ~/second-look-media
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
import sys
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from scripts.find_open_photos import COMMONS_API, RateLimit

ROOT = Path(__file__).resolve().parents[1]
FOOTAGE_CSV = ROOT / "docs" / "video" / "footage.csv"
FETCHED = ROOT / "docs" / "video" / "footage_fetched.json"
MEDIA = Path(os.environ.get("SECOND_LOOK_MEDIA", str(Path.home() / "second-look-media")))
USER_AGENT = (
    "second-look/1.0 (https://github.com/alejandro-publius/second-look; "
    "footage for a hackathon video)"
)
MAX_BYTES = 800 * 1024 * 1024

# The licence's own page, for the credits. Keys are the tidy form licence_key() gives.
LICENCE_URLS = {
    "cc by 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "cc by-sa 3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
    "cc by-sa 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "cc0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "public domain": "https://creativecommons.org/publicdomain/mark/1.0/",
}
# Two spellings of the same licence. Anything else that differs is a change.
SAME_LICENCE = {"cc0 1.0": "cc0", "pd": "public domain", "public domain mark 1.0": "public domain"}
PAGE_RE = re.compile(r"commons\.wikimedia\.org/wiki/(File:.+)$", re.IGNORECASE)


class FootageError(Exception):
    """A row the script cannot use. Nothing is downloaded for it."""


@dataclass(frozen=True)
class Row:
    kind: str
    beat: str
    title: str
    source_page: str
    file_url: str
    author: str
    licence: str
    duration_s: str
    use: str


def read_rows(path: Path = FOOTAGE_CSV) -> list[Row]:
    with path.open(newline="", encoding="utf-8") as f:
        return [Row(**{k: (v or "").strip() for k, v in r.items()}) for r in csv.DictReader(f)]


def licence_key(name: str) -> str:
    """One spelling per licence: lower case, single spaces, hyphens kept inside BY-SA."""
    tidy = re.sub(r"\s+", " ", name.replace("_", " ")).strip().lower()
    tidy = re.sub(r"-(?=\d)", " ", tidy)
    tidy = re.sub(r"^cc[ -]by[ -]sa", "cc by-sa", tidy)
    tidy = re.sub(r"^cc[ -]by(?!-sa)", "cc by", tidy)
    tidy = re.sub(r"^cc[ -]?zero", "cc0", tidy)
    return SAME_LICENCE.get(tidy, tidy)


def licence_url(name: str) -> str:
    url = LICENCE_URLS.get(licence_key(name))
    if url is None:
        raise FootageError(f"no licence page known for {name!r}")
    return url


def commons_title(source_page: str) -> str:
    match = PAGE_RE.search(source_page)
    if not match:
        raise FootageError(f"{source_page} is not a Wikimedia Commons file page")
    return urllib.parse.unquote(match.group(1)).replace("_", " ")


def plain(value: str) -> str:
    """The text inside a Commons HTML field, without tags."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def page_info(payload: dict[str, Any]) -> dict[str, Any]:
    """The one file's imageinfo from an API answer, or a FootageError saying what is missing."""
    pages = (payload.get("query") or {}).get("pages") or []
    if not pages or pages[0].get("missing") or not pages[0].get("imageinfo"):
        raise FootageError("Commons has no such file any more")
    info: dict[str, Any] = pages[0]["imageinfo"][0]
    return info


def meta(info: dict[str, Any], key: str) -> str:
    return plain(str(((info.get("extmetadata") or {}).get(key) or {}).get("value", "")))


def licence_check(row: Row, info: dict[str, Any]) -> dict[str, Any]:
    """Is the licence on the source page still the one in the CSV? Refuses on any change."""
    on_page = meta(info, "LicenseShortName")
    artist = meta(info, "Artist")
    same = bool(on_page) and licence_key(on_page) == licence_key(row.licence)
    reason = "" if same else f"licence changed: the CSV says {row.licence!r}, Commons now says "
    if not same:
        reason += repr(on_page) if on_page else "nothing"
    return {
        "licence_csv": row.licence,
        "licence_commons": on_page,
        "licence_same": same,
        "artist_commons": artist,
        "author_named_on_page": row.author.lower() in artist.lower() if artist else False,
        "kept": same,
        "reason": reason,
    }


def safe_name(title: str) -> str:
    """The Commons file name as a plain file name: no slashes, spaces as underscores."""
    name = title.removeprefix("File:").replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9._()&,-]", "_", name)


def sha1_of(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(client: httpx.Client, limiter: RateLimit, url: str, out: Path) -> None:
    limiter.wait()
    part = out.with_suffix(out.suffix + ".part")
    size = 0
    with client.stream("GET", url, timeout=120.0) as response:
        response.raise_for_status()
        with part.open("wb") as f:
            for chunk in response.iter_bytes(1 << 20):
                size += len(chunk)
                if size > MAX_BYTES:
                    part.unlink(missing_ok=True)
                    raise FootageError(f"{url} is over {MAX_BYTES // (1024 * 1024)} MB")
                f.write(chunk)
    part.replace(out)


def fetch_row(row: Row, client: httpx.Client, limiter: RateLimit, media: Path) -> dict[str, Any]:
    """Check one row's licence, then download it if the licence still holds."""
    entry: dict[str, Any] = {
        "kind": row.kind,
        "beat": row.beat,
        "title": row.title,
        "author": row.author,
        "source_page": row.source_page,
    }
    try:
        title = commons_title(row.source_page)
        limiter.wait()
        response = client.get(
            COMMONS_API,
            params={
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "titles": title,
                "prop": "imageinfo",
                "iiprop": "extmetadata|url|size|sha1",
                "iiextmetadatafilter": "LicenseShortName|Artist|LicenseUrl|ObjectName",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        info = page_info(response.json())
    except (FootageError, httpx.HTTPError, ValueError) as err:
        entry.update({"kept": False, "reason": f"licence not checked: {err}"})
        return entry
    entry.update(licence_check(row, info))
    entry["licence_url"] = LICENCE_URLS.get(licence_key(row.licence), "")
    entry["sha1_commons"] = info.get("sha1", "")
    entry["bytes_commons"] = info.get("size")
    entry["width"] = info.get("width")
    entry["height"] = info.get("height")
    if info.get("duration") is not None:
        entry["duration_s"] = round(float(info["duration"]), 2)
    if not entry["kept"]:
        return entry
    out = media / safe_name(title)
    entry["file"] = out.name
    try:
        if not (out.exists() and sha1_of(out) == entry["sha1_commons"]):
            download(client, limiter, str(info.get("url") or row.file_url), out)
            entry["downloaded"] = True
        else:
            entry["downloaded"] = False
    except (FootageError, httpx.HTTPError, OSError) as err:
        entry.update({"kept": False, "reason": f"download failed: {err}"})
        return entry
    entry["bytes"] = out.stat().st_size
    entry["sha1"] = sha1_of(out)
    if entry["sha1"] != entry["sha1_commons"]:
        entry.update(
            {"kept": False, "reason": "the downloaded file's sha1 is not the one Commons gives"}
        )
    return entry


def manifest(entries: list[dict[str, Any]], media: Path) -> dict[str, Any]:
    kept = [e for e in entries if e.get("kept")]
    return {
        "source": "docs/video/footage.csv",
        "checked_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "user_agent": USER_AGENT,
        "media_folder": str(media).replace(str(Path.home()), "~", 1),
        "committed_media": False,
        "items_in_csv": len(entries),
        "kept": len(kept),
        "dropped": [
            {"title": e["title"], "reason": e.get("reason", "")}
            for e in entries
            if not e.get("kept")
        ],
        "video_licence": "CC BY-SA 4.0",
        "items": entries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--media", type=Path, default=MEDIA)
    parser.add_argument("--csv", type=Path, default=FOOTAGE_CSV)
    parser.add_argument("--out", type=Path, default=FETCHED)
    args = parser.parse_args(argv)
    media = args.media.expanduser()
    if media.resolve().is_relative_to(ROOT.resolve()):
        print(f"fetch-footage: {media} is inside the repository; media must stay outside it")
        return 1
    media.mkdir(parents=True, exist_ok=True)
    limiter = RateLimit()
    entries = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for row in read_rows(args.csv):
            entry = fetch_row(row, client, limiter, media)
            entries.append(entry)
            if entry.get("kept"):
                print(
                    f"fetch-footage: kept {row.title}, {entry['bytes']} bytes, sha1 {entry['sha1']}"
                )
            else:
                print(f"fetch-footage: DROPPED {row.title}: {entry['reason']}")
    out = manifest(entries, media)
    old: dict[str, Any] = {}
    if args.out.exists():
        old = json.loads(args.out.read_text(encoding="utf-8"))
    # Keep the clip checks scripts/cut_footage.py wrote for a file that has not changed.
    clips = {c["title"]: c for c in old.get("clips", []) if isinstance(c, dict)}
    same = {e["title"]: e.get("sha1") for e in entries if e.get("kept")}
    out["clips"] = [c for t, c in clips.items() if same.get(t) and c.get("source_sha1") == same[t]]
    if out["clips"] and old.get("clips_folder"):
        out["clips_folder"] = old["clips_folder"]
    args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"fetch-footage: {out['kept']} of {len(entries)} kept, manifest {args.out.name}")
    return 0 if out["kept"] else 1


if __name__ == "__main__":
    sys.exit(main())
