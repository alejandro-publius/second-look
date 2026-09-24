"""Ask iNaturalist about each of its photos in photos/manifest.csv, and write down what it says.

The lesson, the practice and the test show plant photos from iNaturalist observations. The credits
page says which of them are research grade and which were observed in California, and it says so
from what iNaturalist itself answered, not from our notes. So this script asks iNaturalist once per
observation, at most one request a second, with a user agent that names this project, and writes
the answers to results/inat_photos.json. It changes no photo and no manifest row.

"In California" means iNaturalist puts the observation inside its place 14, the state of
California. "Research grade" means the observation's quality_grade is "research" today.

  uv run python scripts/verify_inat_photos.py           ask iNaturalist, write the results file
  uv run python scripts/verify_inat_photos.py --check   offline: every iNaturalist row has an answer
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.find_open_photos import (  # noqa: E402
    CALIFORNIA_PLACE_ID,
    CONTACT,
    INAT_API,
    PROJECT_URL,
    RateLimit,
    get_json,
    inat_author,
    licence_from_inat,
)

MANIFEST = ROOT / "photos" / "manifest.csv"
RESULTS = ROOT / "results" / "inat_photos.json"
USER_AGENT = f"SecondLookInatCheck/0.1 (Second Look, {PROJECT_URL}; contact {CONTACT})"
OBSERVATION_RE = re.compile(r"inaturalist\.org/observations/(\d+)")


def inat_rows(manifest: Path = MANIFEST) -> list[dict[str, str]]:
    """The manifest rows whose source is an iNaturalist observation, in file order."""
    with manifest.open(newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if OBSERVATION_RE.search(r.get("source_url", ""))]


def observation_id(row: dict[str, str]) -> int:
    match = OBSERVATION_RE.search(row["source_url"])
    if match is None:
        raise ValueError(f"{row['id']}: not an iNaturalist observation")
    return int(match.group(1))


def verdict(row: dict[str, str], observation: dict[str, Any] | None) -> dict[str, Any]:
    """What iNaturalist says about one manifest photo. None means iNaturalist has no such record."""
    oid = observation_id(row)
    out: dict[str, Any] = {
        "photo_id": row["id"],
        "role": row.get("role", ""),
        "observation_id": oid,
        "observation_url": f"https://www.inaturalist.org/observations/{oid}",
        "manifest_author": row.get("author", ""),
        "manifest_license": row.get("license", ""),
    }
    if observation is None:
        return {
            **out,
            "found": False,
            "quality_grade": None,
            "research_grade": False,
            "in_california": False,
            "place_guess": None,
            "taxon": None,
            "author_and_licence_match": False,
        }
    user = observation.get("user") or {}
    photos = observation.get("photos") or []
    # The manifest keeps one photo of the observation. It is credited right when one of the
    # observation's photos carries the same author and the same licence the manifest names.
    match = False
    for photo in photos:
        licence = licence_from_inat(photo.get("license_code"))
        if licence is None or licence.manifest != row.get("license", ""):
            continue
        if inat_author(photo, user) == row.get("author", ""):
            match = True
            break
    places = [int(p) for p in observation.get("place_ids") or [] if str(p).isdigit()]
    grade = str(observation.get("quality_grade") or "")
    return {
        **out,
        "found": True,
        "quality_grade": grade,
        "research_grade": grade == "research",
        "in_california": CALIFORNIA_PLACE_ID in places,
        "place_guess": str(observation.get("place_guess") or ""),
        "taxon": str((observation.get("taxon") or {}).get("name") or ""),
        "author_and_licence_match": match,
    }


def summarise(photos: list[dict[str, Any]], checked_at: str) -> dict[str, Any]:
    return {
        "checked_at": checked_at,
        "source": f"{INAT_API}/<observation id>",
        "user_agent": USER_AGENT,
        "california_place_id": CALIFORNIA_PLACE_ID,
        "photos": photos,
        "summary": {
            "photos": len(photos),
            "found": sum(1 for p in photos if p["found"]),
            "research_grade": sum(1 for p in photos if p["research_grade"]),
            "in_california": sum(1 for p in photos if p["in_california"]),
            "research_grade_in_california": sum(
                1 for p in photos if p["research_grade"] and p["in_california"]
            ),
            "author_and_licence_match": sum(1 for p in photos if p["author_and_licence_match"]),
        },
    }


def check(results: Path = RESULTS, manifest: Path = MANIFEST) -> list[str]:
    """Offline: every iNaturalist row in the manifest has an answer, for the same observation."""
    if not results.is_file():
        return [f"{results.name} is missing: run scripts/verify_inat_photos.py"]
    doc = json.loads(results.read_text(encoding="utf-8"))
    answered = {p["photo_id"]: p for p in doc.get("photos", [])}
    problems = []
    for row in inat_rows(manifest):
        got = answered.get(row["id"])
        if got is None:
            problems.append(f"{row['id']} has no iNaturalist answer in {results.name}")
        elif got.get("observation_id") != observation_id(row):
            problems.append(f"{row['id']}: {results.name} checked a different observation")
    return problems


def fetch(client: httpx.Client, limiter: RateLimit, oid: int) -> dict[str, Any] | None:
    payload = get_json(client, f"{INAT_API}/{oid}", {}, limiter)
    found = payload.get("results") or []
    return dict(found[0]) if found else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="offline: compare with the manifest")
    args = parser.parse_args(argv)
    if args.check:
        problems = check()
        for p in problems:
            print(f"verify-inat-photos: {p}")
        if not problems:
            print(f"verify-inat-photos: every iNaturalist photo has an answer in {RESULTS.name}")
        return 1 if problems else 0

    rows = inat_rows()
    limiter = RateLimit()
    photos = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for row in rows:
            photos.append(verdict(row, fetch(client, limiter, observation_id(row))))
    checked_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    doc = summarise(photos, checked_at)
    RESULTS.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    s = doc["summary"]
    print(
        f"verify-inat-photos: {s['photos']} photos asked, {s['research_grade']} research grade, "
        f"{s['in_california']} in California, {s['author_and_licence_match']} with the author "
        f"and licence the manifest names; wrote {RESULTS.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
