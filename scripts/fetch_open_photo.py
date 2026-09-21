"""Fetch one chosen open photo, run it through the normal ingest, and record its evidence.

Run: uv run python scripts/fetch_open_photo.py \
        https://commons.wikimedia.org/wiki/File:Kanggaokeng_Creek_20150430a.jpg \
        --feature artificial_bank --role test

     uv run python scripts/fetch_open_photo.py \
        https://www.inaturalist.org/observations/75908450 \
        --feature invasive_plant --role lesson

Takes a Wikimedia Commons file page or an iNaturalist observation page, asks that API for the
author, the licence and the source's own words, downloads the one image, and hands it to
scripts/ingest_photos.py. Ingest does the resizing, the EXIF stripping and the manifest row, so
there is only ever one ingest path. The row carries author, licence, source_url and
label_evidence.

It refuses, and writes nothing, when the licence is not CC0, CC BY or CC BY-SA, when the licence
version has no entry in the manifest allowlist, when an iNaturalist record is not research grade,
or when a plant is not on the Cal-IPC Inventory. Refusing beats guessing (hard rule 6).

It never sets a label. gold_label stays empty until a person labels the photo.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import tempfile
import urllib.parse
from datetime import date
from pathlib import Path

import httpx

from scripts.find_open_photos import (
    COMMONS_API,
    INAT_API,
    ROOT,
    USER_AGENT,
    Candidate,
    RateLimit,
    Search,
    cal_ipc_index,
    commons_candidates,
    get_json,
    inat_candidates,
    plain_text,
)
from scripts.ingest_photos import IngestError, ingest

COMMONS_PAGE_RE = re.compile(r"commons\.wikimedia\.org/wiki/(File:.+)$", re.IGNORECASE)
COMMONS_UPLOAD_RE = re.compile(r"upload\.wikimedia\.org/wikipedia/commons/(?:thumb/)?.+?/([^/]+)$")
INAT_OBSERVATION_RE = re.compile(r"inaturalist\.org/observations/(\d+)")
# Only a date the source itself attaches to the sighting. A date inside a caption could be
# about anything, so we leave capture_date empty rather than guess.
DATE_RE = re.compile(r"observed (\d{4})-(\d{2})-(\d{2})")
MAX_BYTES = 80 * 1024 * 1024
CONTENT_TYPES = {"image/jpeg": ".jpg", "image/png": ".png"}


class FetchError(Exception):
    """Why we refused. Nothing was downloaded and nothing was written."""


def commons_title(url: str) -> str | None:
    match = COMMONS_PAGE_RE.search(url)
    if match:
        return urllib.parse.unquote(match.group(1)).replace("_", " ")
    match = COMMONS_UPLOAD_RE.search(url)
    if match:
        return "File:" + urllib.parse.unquote(match.group(1)).replace("_", " ")
    return None


def load_commons(client: httpx.Client, limiter: RateLimit, title: str, feature: str) -> Candidate:
    payload = get_json(
        client,
        COMMONS_API,
        {
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|user|extmetadata",
            "iiurlwidth": "320",
            "format": "json",
            "formatversion": "2",
        },
        limiter,
    )
    found = commons_candidates(payload, Search("commons", title, "picked"), feature)
    if not found:
        raise FetchError(
            f"{title}: Commons gives no usable photo here. Either the page is not a JPEG or PNG, "
            "or the licence is not CC0, CC BY or CC BY-SA, or nobody is named as the author."
        )
    return found[0]


def load_inat(
    client: httpx.Client,
    limiter: RateLimit,
    observation_id: str,
    feature: str,
    cal_ipc: dict[str, dict[str, str]],
) -> Candidate:
    payload = get_json(client, f"{INAT_API}/{observation_id}", {}, limiter)
    found = inat_candidates(
        payload, Search("inat_taxon", observation_id, "picked"), feature, cal_ipc
    )
    if not found:
        raise FetchError(
            f"observation {observation_id}: iNaturalist gives no usable photo here. Either the "
            "record is not research grade, or no photo on it is CC0, CC BY or CC BY-SA."
        )
    return found[0]


def cal_ipc_evidence(text: str, cal_ipc: dict[str, dict[str, str]]) -> str:
    """The Cal-IPC line for the first listed species the source's own words name."""
    low = text.lower()
    for key, entry in cal_ipc.items():
        if key in low:
            return (
                f" The source names {entry['latin_name']}, which is on the Cal-IPC Inventory "
                f"with rating {entry['rating']}: {entry['link']}"
            )
    return ""


def capture_date(candidate: Candidate) -> str:
    match = DATE_RE.search(candidate.evidence)
    if not match:
        return ""
    year, month, day = (int(p) for p in match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return ""


def coarse_place(place: str) -> str:
    """Keep a place name coarse: the last three parts, so a town and a state, not a street."""
    parts = [p.strip() for p in place.split(",") if p.strip()]
    return ", ".join(parts[-3:])


def download(client: httpx.Client, limiter: RateLimit, url: str, folder: Path) -> Path:
    limiter.wait()
    with client.stream("GET", url, timeout=60.0) as response:
        response.raise_for_status()
        kind = response.headers.get("content-type", "").split(";")[0].strip().lower()
        suffix = CONTENT_TYPES.get(kind)
        if suffix is None:
            raise FetchError(f"{url} came back as {kind or 'no content type'}, not a JPEG or PNG")
        out = folder / f"source{suffix}"
        size = 0
        with out.open("wb") as f:
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise FetchError(
                        f"{url} is over {MAX_BYTES // (1024 * 1024)} MB, so we stopped"
                    )
                f.write(chunk)
    return out


def fetch(
    url: str,
    feature: str,
    role: str,
    batch: str = "open",
    scene: str = "",
    location: str = "",
    notes: str = "",
    extra_evidence: str = "",
    root: Path = ROOT,
    client: httpx.Client | None = None,
    limiter: RateLimit | None = None,
) -> dict[str, str]:
    """Download one photo, return the manifest row ingest wrote.

    Raises FetchError or IngestError, and then nothing has been written.
    """
    limiter = limiter or RateLimit()
    cal_ipc = cal_ipc_index(root)
    owned = client is None
    client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    try:
        title = commons_title(url)
        observation = INAT_OBSERVATION_RE.search(url)
        if title:
            candidate = load_commons(client, limiter, title, feature)
            source_id = f"commons-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:40]}"
        elif observation:
            candidate = load_inat(client, limiter, observation.group(1), feature, cal_ipc)
            source_id = f"inat-{observation.group(1)}"
        else:
            raise FetchError(
                f"{url}: give a Wikimedia Commons file page or an iNaturalist observation page."
            )
        if not candidate.licence.manifest:
            raise FetchError(
                f"{candidate.page_url}: the licence is {candidate.licence.label}, which the "
                "manifest allowlist has no entry for. Pick a CC0, CC BY 4.0 or CC BY-SA 4.0 photo."
            )
        evidence = candidate.evidence
        if feature == "invasive_plant" and "cal-ipc.org" not in evidence:
            evidence += cal_ipc_evidence(f"{candidate.title} {candidate.words}", cal_ipc)
        if feature == "invasive_plant" and "cal-ipc.org" not in evidence:
            raise FetchError(
                f"{candidate.page_url}: a plant photo needs a species that is on the Cal-IPC "
                "Inventory, and the source does not name one. Leave it out."
            )
        if extra_evidence:
            evidence = f"{evidence} {extra_evidence.strip()}"
        with tempfile.TemporaryDirectory(prefix="fetch-open-photo-") as tmp:
            folder = Path(tmp)
            image = download(client, limiter, candidate.image_url, folder)
            labels = folder / "labels.csv"
            row = {
                "photo_file": image.name,
                "role": role,
                # The warm-up pair belongs to no feature, so the manifest keeps that cell empty.
                "feature": "" if feature == "warmup" else feature,
                "gold_label": "",  # a person labels, never this script
                "scene_id": scene or source_id,
                "capture_date": capture_date(candidate),
                "coarse_location": location or coarse_place(candidate.place),
                "author": candidate.author,
                "license": candidate.licence.manifest,
                "source_url": candidate.page_url,
                "notes": notes or plain_text(candidate.words, 160),
                "label_evidence": plain_text(evidence, 700),
            }
            with labels.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)
            written = ingest(folder, labels, batch, root)
        return written[0]
    finally:
        if owned:
            client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("url", help="a Commons file page or an iNaturalist observation page")
    parser.add_argument(
        "--feature",
        required=True,
        choices=["artificial_bank", "dug_out_channel", "invasive_plant", "pipe_running", "warmup"],
    )
    parser.add_argument(
        "--role", required=True, choices=["warmup", "lesson", "practice", "test", "benchmark"]
    )
    parser.add_argument("--batch", default="open", help="manifest id batch, default open")
    parser.add_argument("--scene", default="", help="scene id, when it shares a spot with another")
    parser.add_argument("--location", default="", help="coarse location, town or county")
    parser.add_argument("--notes", default="", help="a note for the manifest row")
    parser.add_argument("--evidence", default="", help="anything else the source supports")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        row = fetch(
            args.url,
            args.feature,
            args.role,
            batch=args.batch,
            scene=args.scene,
            location=args.location,
            notes=args.notes,
            extra_evidence=args.evidence,
            root=args.root,
        )
    except (FetchError, IngestError) as e:
        print("fetch-open-photo: refused, nothing written:")
        print(e)
        return 1
    except httpx.HTTPError as e:
        print(f"fetch-open-photo: the source did not answer: {e}")
        return 1
    print(f"fetch-open-photo: {row['id']} at photos/{row['file']}")
    print(f"  author:   {row['author']}")
    print(f"  licence:  {row['license']}")
    print(f"  source:   {row['source_url']}")
    print(f"  evidence: {row['label_evidence']}")
    print("  gold_label is empty on purpose. A person labels it with scripts/label_photos.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
