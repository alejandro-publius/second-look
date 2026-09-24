"""Fetch iNaturalist sightings of the region's listed invasive plants near each creek, on the Mac,
and store a short summary per creek in D1 for the context line on the record page and /city.

For every creek with a record, this reads the creek's Locations (the spots with a position) from
our own public API: /api/creeks, then the FHIR Bundles it links. Then it asks iNaturalist's public
API once per Location for research-grade observations of the plants on that region pack's invasive
list (content/regions/*.yaml, each with its `inaturalist_taxon_id`), within RADIUS_KM of the
Location, observed in the last YEARS years. At most one request a second, with a user agent that
names this project. It keeps, per plant, how many observations, the most recent date and a link to
those observations on inaturalist.org, and stores that with the fetch time in the D1 table
`inaturalist_cache`, the same way scripts/cache_their_records.py stores /two's record. A creek
whose fetch fails stores nothing, so its last good copy stays.

A creek whose region pack lists no plant with a taxon id is not asked about and not stored: the
page then says "no recent sightings on record". Today the approved Bay Area pack lists none; the
draft list in content/drafts/regions/ carries the ids for when Rachel approves it.

The summary is context. Nothing counts it and nothing decides from it: this file imports nothing
from core/gate.py or core/followups.py (docs/adr/0011-inaturalist-context.md).

  uv run python scripts/cache_inaturalist.py            fetch, store, then read the route back
  uv run python scripts/cache_inaturalist.py --dry-run  fetch and print the SQL, store nothing
  ... --locations FILE   read {creek: [{id, latitude, longitude}]} from FILE, not the site
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.cache_their_records import sql_literal, store  # noqa: E402
from scripts.find_open_photos import CONTACT, INAT_API, PROJECT_URL, RateLimit  # noqa: E402

SITE = "https://second-look-79t.pages.dev"
REGIONS = ROOT / "content" / "regions"
USER_AGENT = f"SecondLookInatContext/0.1 (Second Look, {PROJECT_URL}; contact {CONTACT})"
RADIUS_KM = 0.3
YEARS = 3
PER_PAGE = 200
MAX_PAGES = 10  # 2000 observations near one spot; past that the count would be a guess
MAX_LINK_IDS = 300  # a longer id list makes a link too long to open; the newest are linked
OBSERVATIONS_PAGE = "https://www.inaturalist.org/observations"

GetJson = Callable[[str, dict[str, Any]], dict[str, Any]]
# None in use; a test puts an httpx.MockTransport here so nothing leaves the machine.
TRANSPORT: httpx.BaseTransport | None = None


@dataclass(frozen=True)
class Plant:
    taxon_id: int
    name: str  # Cal-IPC's common name, the one the region pack shows
    latin_name: str


@dataclass(frozen=True)
class Location:
    id: str
    latitude: float
    longitude: float


class FetchFailed(RuntimeError):
    """iNaturalist did not answer, or answered with more than MAX_PAGES pages near one spot."""


# --------------------------------------------------------------------------------------------
# What to ask about


def listed_plants(regions_dir: Path = REGIONS) -> dict[str, list[Plant]]:
    """Each region pack's invasive plants that carry an iNaturalist taxon id, by pack name."""
    out: dict[str, list[Plant]] = {}
    for path in sorted(regions_dir.glob("*.yaml")):
        pack = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        plants = []
        for p in pack.get("invasive_plants") or []:
            tid = p.get("inaturalist_taxon_id")
            if isinstance(tid, int) and not isinstance(tid, bool) and tid > 0:
                plants.append(
                    Plant(tid, str(p.get("common_name", "")), str(p.get("latin_name", "")))
                )
        out[path.stem] = plants
    return out


def pack_creeks(regions_dir: Path = REGIONS) -> dict[str, str]:
    """Creek slug to the region pack that names it."""
    out: dict[str, str] = {}
    for path in sorted(regions_dir.glob("*.yaml")):
        pack = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for creek in pack.get("creeks") or []:
            if creek.get("slug"):
                out[str(creek["slug"])] = path.stem
    return out


def plants_for(
    creek: str, plants: Mapping[str, list[Plant]], creeks: Mapping[str, str]
) -> list[Plant]:
    """The creek's own pack's list. A creek no pack names gets every pack's list, like the form."""
    if creek in creeks:
        return list(plants.get(creeks[creek], []))
    seen: dict[int, Plant] = {}
    for listed in plants.values():
        for p in listed:
            seen.setdefault(p.taxon_id, p)
    return list(seen.values())


def since(today: date, years: int = YEARS) -> date:
    """The same day `years` back; 29 February becomes the 28th."""
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(year=today.year - years, day=28)


# --------------------------------------------------------------------------------------------
# Where to ask


def locations_in_bundle(bundle: Mapping[str, Any]) -> list[Location]:
    """The Locations in one visit Bundle that have a position: the spots."""
    out = []
    for entry in bundle.get("entry") or []:
        r = entry.get("resource") or {}
        pos = r.get("position") or {}
        if r.get("resourceType") != "Location" or "latitude" not in pos or "longitude" not in pos:
            continue
        out.append(Location(str(r.get("id")), float(pos["latitude"]), float(pos["longitude"])))
    return out


def creek_locations(site: str, get: Callable[[str], dict[str, Any]]) -> dict[str, list[Location]]:
    """Every creek on our site, with the Locations of its spots, read from our own public API."""
    base = site.rstrip("/")
    out: dict[str, list[Location]] = {}
    for creek in get(f"{base}/api/creeks").get("creeks") or []:
        found: dict[str, Location] = {}
        for link in creek.get("fhir") or []:
            for loc in locations_in_bundle(get(f"{base}{link}")):
                found.setdefault(loc.id, loc)
        out[str(creek["creek"])] = sorted(found.values(), key=lambda x: x.id)
    return out


def locations_from_file(path: Path) -> dict[str, list[Location]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(creek): [
            Location(str(x["id"]), float(x["latitude"]), float(x["longitude"])) for x in locs
        ]
        for creek, locs in raw.items()
    }


# --------------------------------------------------------------------------------------------
# Asking iNaturalist


def query(loc: Location, plants: Iterable[Plant], d1: date, page: int) -> dict[str, Any]:
    """The query for one Location: research grade, the listed taxa, the circle, the years."""
    return {
        "quality_grade": "research",
        "taxon_id": ",".join(str(p.taxon_id) for p in plants),
        "lat": loc.latitude,
        "lng": loc.longitude,
        "radius": RADIUS_KM,
        "d1": d1.isoformat(),
        "per_page": PER_PAGE,
        "page": page,
        "order_by": "observed_on",
        "order": "desc",
    }


def observations_near(
    loc: Location, plants: list[Plant], d1: date, get: GetJson
) -> list[dict[str, Any]]:
    """Every research-grade observation of the listed plants near one Location, page by page."""
    out: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        body = get(INAT_API, query(loc, plants, d1, page))
        results = list(body.get("results") or [])
        out += results
        total = int(body.get("total_results") or 0)
        if len(out) >= total or not results:
            return out
    raise FetchFailed(f"more than {MAX_PAGES * PER_PAGE} observations near {loc.id}")


def listed_taxon(obs: Mapping[str, Any], plants: list[Plant]) -> Plant | None:
    """The listed plant an observation is of: its own taxon, or one it sits under (a subspecies)."""
    taxon = obs.get("taxon") or {}
    lineage = {taxon.get("id"), *(taxon.get("ancestor_ids") or [])}
    for p in plants:
        if p.taxon_id in lineage:
            return p
    return None


def link(ids: list[int]) -> str:
    """Those observations on inaturalist.org, by id. Past MAX_LINK_IDS, the newest ones."""
    newest = sorted(ids, reverse=True)[:MAX_LINK_IDS]
    ids_text = ",".join(str(i) for i in sorted(newest))
    return f"{OBSERVATIONS_PAGE}?" + urlencode({"id": ids_text}, safe=",")


def summarise(
    observations: Iterable[Mapping[str, Any]],
    plants: list[Plant],
    locations: list[Location],
    d1: date,
) -> dict[str, Any]:
    """Per listed plant: how many observations, the latest date, and a link. Pure.

    An observation near two spots is counted once. Only research grade observations of a listed
    plant, observed on or after d1, are counted, whatever iNaturalist sent.
    """
    ids: dict[int, set[int]] = {}
    latest: dict[int, str] = {}
    for obs in observations:
        if obs.get("quality_grade") != "research":
            continue
        observed = str(obs.get("observed_on") or "")
        if not observed or observed < d1.isoformat():
            continue
        plant = listed_taxon(obs, plants)
        if plant is None or not isinstance(obs.get("id"), int):
            continue
        ids.setdefault(plant.taxon_id, set()).add(int(obs["id"]))
        latest[plant.taxon_id] = max(latest.get(plant.taxon_id, ""), observed)
    species: list[dict[str, Any]] = []
    for p in plants:
        seen = sorted(ids.get(p.taxon_id, set()))
        if not seen:
            continue
        species.append(
            {
                "taxon_id": p.taxon_id,
                "name": p.name,
                "latin_name": p.latin_name,
                "count": len(seen),
                "last_observed": latest[p.taxon_id],
                "url": link(seen),
                "linked": min(len(seen), MAX_LINK_IDS),
            }
        )
    species.sort(key=lambda s: (-s["count"], s["name"]))
    return {
        "since": d1.isoformat(),
        "radius_m": round(RADIUS_KM * 1000),
        "years": YEARS,
        "locations": len(locations),
        "taxa": [p.taxon_id for p in plants],
        "source": INAT_API,
        "species": species,
    }


def insert_sql(creek: str, summary: Mapping[str, Any], fetched_at: str) -> str:
    body = json.dumps(summary, separators=(",", ":"), ensure_ascii=False)
    return (
        "INSERT OR REPLACE INTO inaturalist_cache (creek, body, fetched_at) VALUES "
        f"({sql_literal(creek)}, {sql_literal(body)}, {sql_literal(fetched_at)});\n"
    )


def fetch_creek(
    locations: list[Location], plants: list[Plant], d1: date, get: GetJson
) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    for loc in locations:
        observations += observations_near(loc, plants, d1, get)
    return summarise(observations, plants, locations, d1)


def read_back(site: str, creek: str) -> dict[str, Any]:
    """What our own route now answers for the creek, to prove the row landed."""
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20, transport=TRANSPORT) as c:
        response = c.get(f"{site.rstrip('/')}/api/inaturalist/{quote(creek, safe='')}")
    response.raise_for_status()
    return dict(response.json())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="fetch and print, store nothing")
    parser.add_argument("--site", default=SITE, help="where to read the creeks and read back")
    parser.add_argument("--locations", type=Path, default=None, help="creek Locations as JSON")
    args = parser.parse_args(argv)

    limiter = RateLimit()
    client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30.0, transport=TRANSPORT)
    with client:

        def get(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
            # Our own site and iNaturalist alike: one request a second, no faster.
            limiter.wait()
            response = client.get(url, params=params or {})
            response.raise_for_status()
            return dict(response.json())

        creeks = (
            locations_from_file(args.locations)
            if args.locations
            else creek_locations(args.site, get)
        )
        plants = listed_plants()
        named = pack_creeks()
        d1 = since(datetime.now(UTC).date())
        stored: list[tuple[str, str]] = []
        failed = 0
        for creek, locations in sorted(creeks.items()):
            listed = plants_for(creek, plants, named)
            if not locations or not listed:
                why = (
                    "no spot with a position"
                    if not locations
                    else "no listed plant with a taxon id"
                )
                print(f"cache-inaturalist: {creek}: {why}; nothing asked, nothing stored")
                continue
            try:
                summary = fetch_creek(locations, listed, d1, get)
            except (httpx.HTTPError, FetchFailed, ValueError) as exc:
                failed += 1
                print(f"cache-inaturalist: {creek}: {exc}; the last stored copy stays")
                continue
            fetched_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            stored.append((creek, insert_sql(creek, summary, fetched_at)))
            kinds = ", ".join(f"{s['name']} {s['count']}" for s in summary["species"]) or "none"
            print(f"cache-inaturalist: {creek}: {len(locations)} Locations asked; seen: {kinds}")

    sql = "".join(line for _, line in stored)
    if args.dry_run:
        print(sql, end="")
        print(f"cache-inaturalist: dry run, {len(stored)} creek(s) fetched, nothing stored")
        return 1 if failed else 0
    if stored:
        store(sql)
        for creek, _ in stored:
            back = read_back(args.site, creek)
            if back.get("status") != "cached" or not back.get("fetched_at"):
                print(f"cache-inaturalist: stored {creek}, but the route says {back.get('status')}")
                failed += 1
    print(f"cache-inaturalist: {len(stored)} creek(s) stored, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
