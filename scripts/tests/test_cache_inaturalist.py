"""The Mac job behind the iNaturalist context line: what it asks, how it paces and names itself,
what it counts, what it stores, and that a failure stores nothing. No request leaves the machine:
every one goes to an httpx.MockTransport."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from scripts import cache_inaturalist as cache
from scripts.find_open_photos import MIN_SECONDS, RateLimit

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = (ROOT / "worker" / "schema.sql").read_text(encoding="utf-8")
BLACKBERRY = cache.Plant(61317, "Himalayan blackberry", "Rubus armeniacus")
IVY = cache.Plant(55882, "English ivy", "Hedera helix")
D1 = date(2023, 9, 24)
GLADE = cache.Location("sl-loc-glade", 37.8716, -122.256)
PARK = cache.Location("sl-loc-park", 37.8666, -122.2885)


def obs(oid: int, taxon: int, observed: str, grade: str = "research", **extra: Any) -> dict:
    return {
        "id": oid,
        "quality_grade": grade,
        "observed_on": observed,
        "taxon": {"id": taxon, "ancestor_ids": extra.get("ancestors", [])},
    }


# --------------------------------------------------------------------------------------------
# What to ask about


def pack(tmp_path: Path, name: str, text: str) -> Path:
    (tmp_path / f"{name}.yaml").write_text(text, encoding="utf-8")
    return tmp_path


def test_only_plants_with_a_taxon_id_are_asked_about(tmp_path: Path) -> None:
    pack(
        tmp_path,
        "bay",
        """
invasive_plants:
  - {common_name: Himalayan blackberry, latin_name: Rubus armeniacus, inaturalist_taxon_id: 61317}
  - {common_name: No id yet, latin_name: Nothing yet}
  - {common_name: A yes, latin_name: X, inaturalist_taxon_id: true}
  - {common_name: A minus, latin_name: Y, inaturalist_taxon_id: -4}
creeks:
  - {slug: strawberry-creek, name: Strawberry Creek}
""",
    )
    pack(tmp_path, "empty", "invasive_plants: []\ncreeks: []\n")
    assert cache.listed_plants(tmp_path) == {"bay": [BLACKBERRY], "empty": []}
    assert cache.pack_creeks(tmp_path) == {"strawberry-creek": "bay"}


def test_the_draft_list_carries_a_taxon_id_for_every_plant() -> None:
    drafts = ROOT / "content" / "drafts" / "regions"
    listed = cache.listed_plants(drafts)["california-bay-area"]
    assert len(listed) == 11
    assert {p.latin_name: p.taxon_id for p in listed}["Rubus armeniacus"] == 61317


def test_a_creek_gets_its_own_packs_list_and_an_unknown_creek_every_list() -> None:
    plants = {"bay": [BLACKBERRY], "crete": [IVY]}
    named = {"strawberry-creek": "bay"}
    assert cache.plants_for("strawberry-creek", plants, named) == [BLACKBERRY]
    assert cache.plants_for("creek-1a2b", plants, named) == [BLACKBERRY, IVY]


def test_three_years_back_and_a_leap_day() -> None:
    assert cache.since(date(2026, 9, 24)) == date(2023, 9, 24)
    assert cache.since(date(2028, 2, 29)) == date(2025, 2, 28)


def test_the_query_is_research_grade_the_listed_taxa_the_circle_and_the_years() -> None:
    q = cache.query(GLADE, [BLACKBERRY, IVY], D1, 2)
    assert q["quality_grade"] == "research"
    assert q["taxon_id"] == "61317,55882"
    assert (q["lat"], q["lng"], q["radius"]) == (37.8716, -122.256, 0.3)
    assert q["d1"] == "2023-09-24"
    assert q["page"] == 2


def test_the_spots_are_the_locations_with_a_position_in_the_bundles() -> None:
    bundle = {
        "entry": [
            {"resource": {"resourceType": "Location", "id": "sl-loc-creek"}},
            {
                "resource": {
                    "resourceType": "Location",
                    "id": "sl-loc-spot-1",
                    "position": {"latitude": 37.87, "longitude": -122.26},
                }
            },
            {"resource": {"resourceType": "Observation", "id": "o1"}},
        ]
    }
    assert cache.locations_in_bundle(bundle) == [cache.Location("sl-loc-spot-1", 37.87, -122.26)]


# --------------------------------------------------------------------------------------------
# What it counts


def test_an_observation_near_two_spots_counts_once_and_only_real_ones_count() -> None:
    near_glade = [
        obs(1, 61317, "2025-12-11"),
        obs(2, 61317, "2024-05-01"),
        obs(3, 55882, "2025-01-02"),
        obs(4, 61317, "2025-06-01", grade="needs_id"),
        obs(5, 61317, "2023-09-23"),  # a day before the three years
        obs(6, 99999, "2025-06-01"),  # not on the list
        obs(7, 1449266, "2025-07-01", ancestors=[61317]),  # a subspecies of a listed plant
    ]
    near_park = [obs(1, 61317, "2025-12-11")]  # the same observation, seen from the next spot
    out = cache.summarise(near_glade + near_park, [BLACKBERRY, IVY], [GLADE, PARK], D1)
    assert [(s["name"], s["count"], s["last_observed"]) for s in out["species"]] == [
        ("Himalayan blackberry", 3, "2025-12-11"),
        ("English ivy", 1, "2025-01-02"),
    ]
    assert out["species"][0]["url"] == "https://www.inaturalist.org/observations?id=1,2,7"
    assert (out["since"], out["radius_m"], out["locations"]) == ("2023-09-24", 300, 2)


def test_no_sightings_is_an_empty_list_not_a_zero_row() -> None:
    assert cache.summarise([], [BLACKBERRY], [GLADE], D1)["species"] == []


def test_a_long_list_links_the_newest() -> None:
    url = cache.link(list(range(1, cache.MAX_LINK_IDS + 51)))
    ids = [int(i) for i in parse_qs(urlsplit(url).query)["id"][0].split(",")]
    assert len(ids) == cache.MAX_LINK_IDS
    assert min(ids) == 51 and max(ids) == cache.MAX_LINK_IDS + 50


def test_the_pages_are_followed_and_a_flood_is_refused() -> None:
    pages = {1: [obs(1, 61317, "2025-01-01")], 2: [obs(2, 61317, "2025-01-02")]}

    def get(_url: str, params: dict[str, Any]) -> dict[str, Any]:
        return {"total_results": 2, "results": pages.get(params["page"], [])}

    assert [o["id"] for o in cache.observations_near(GLADE, [BLACKBERRY], D1, get)] == [1, 2]

    def flood(_url: str, params: dict[str, Any]) -> dict[str, Any]:
        return {"total_results": 10**6, "results": [obs(params["page"], 61317, "2025-01-01")]}

    with pytest.raises(cache.FetchFailed):
        cache.observations_near(GLADE, [BLACKBERRY], D1, flood)


def test_the_sql_round_trips_quotes_through_the_real_schema() -> None:
    db = sqlite3.connect(":memory:")
    db.executescript(SCHEMA)
    summary = {"species": [{"name": "Cape ivy's cousin", "count": 1}]}
    db.executescript(cache.insert_sql("strawberry-creek", summary, "2026-09-24T07:45:00Z"))
    body, when = db.execute(
        "SELECT body, fetched_at FROM inaturalist_cache WHERE creek = 'strawberry-creek'"
    ).fetchone()
    assert json.loads(body) == summary and when == "2026-09-24T07:45:00Z"


# --------------------------------------------------------------------------------------------
# The whole run, against a mock of our site and of iNaturalist


class Counting(RateLimit):
    """The real limiter with no sleep, counting how often it was asked to wait and how long a
    gap the script asked it to keep."""

    waits = 0
    gaps: list[float] = []

    def __init__(self, min_seconds: float = MIN_SECONDS) -> None:
        Counting.gaps.append(min_seconds)
        super().__init__(min_seconds=min_seconds, sleeper=lambda _s: None)

    def wait(self) -> None:
        Counting.waits += 1
        super().wait()


def bundle(spot: str, lat: float, lng: float) -> dict[str, Any]:
    loc = {"resourceType": "Location", "id": spot, "position": {"latitude": lat, "longitude": lng}}
    return {"resourceType": "Bundle", "entry": [{"resource": loc}]}


def run(
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    *,
    plants: list[cache.Plant],
    inat_status: int = 200,
) -> tuple[int, list[httpx.Request], list[str]]:
    requests: list[httpx.Request] = []
    stored: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if request.url.host == "api.inaturalist.org":
            if inat_status != 200:
                return httpx.Response(inat_status, json={"error": "down"})
            return httpx.Response(
                200, json={"total_results": 1, "results": [obs(9, 61317, "2025-12-11")]}
            )
        if path == "/api/creeks":
            links = ["/api/fhir/Bundle/v1", "/api/fhir/Bundle/v2"]
            return httpx.Response(
                200, json={"creeks": [{"creek": "strawberry-creek", "fhir": links}]}
            )
        if path == "/api/fhir/Bundle/v1":
            return httpx.Response(200, json=bundle("sl-loc-spot-1", 37.8716, -122.256))
        if path == "/api/fhir/Bundle/v2":
            return httpx.Response(200, json=bundle("sl-loc-spot-1", 37.8716, -122.256))
        if path == "/api/inaturalist/strawberry-creek":
            return httpx.Response(
                200, json={"status": "cached", "fetched_at": "2026-09-24T07:45:00Z"}
            )
        return httpx.Response(404, json={"detail": "not in the mock"})

    Counting.waits = 0
    Counting.gaps = []
    monkeypatch.setattr(cache, "TRANSPORT", httpx.MockTransport(handler))
    monkeypatch.setattr(cache, "RateLimit", Counting)
    monkeypatch.setattr(cache, "store", stored.append)
    monkeypatch.setattr(cache, "listed_plants", lambda: {"california-bay-area": plants})
    return cache.main(argv), requests, stored


def test_a_good_run_stores_one_row_per_creek_and_reads_it_back(monkeypatch) -> None:
    code, requests, stored = run(monkeypatch, [], plants=[BLACKBERRY])
    assert code == 0
    assert len(stored) == 1 and "INSERT OR REPLACE INTO inaturalist_cache" in stored[0]
    assert "'strawberry-creek'" in stored[0] and "Himalayan blackberry" in stored[0]
    # The same spot in two Bundles is asked about once.
    inat = [r for r in requests if r.url.host == "api.inaturalist.org"]
    assert len(inat) == 1
    assert inat[0].url.params["quality_grade"] == "research"
    assert inat[0].url.params["radius"] == "0.3"
    assert requests[-1].url.path == "/api/inaturalist/strawberry-creek"


def test_every_request_names_the_project_and_waits_its_turn(monkeypatch) -> None:
    code, requests, _ = run(monkeypatch, ["--dry-run"], plants=[BLACKBERRY])
    assert code == 0
    assert requests
    for r in requests:
        assert re.match(
            r"SecondLookInatContext/\S+ \(Second Look, https://github\.com/",
            r.headers["user-agent"],
        )
    assert Counting.waits == len(requests), "one limiter wait per request"
    assert Counting.gaps and all(g >= 1.0 for g in Counting.gaps), "at most one a second"


def test_a_dry_run_prints_and_stores_nothing(monkeypatch, capsys) -> None:
    code, _, stored = run(monkeypatch, ["--dry-run"], plants=[BLACKBERRY])
    assert code == 0 and stored == []
    out = capsys.readouterr().out
    assert "INSERT OR REPLACE INTO inaturalist_cache" in out
    assert "nothing stored" in out


def test_when_inaturalist_is_down_nothing_is_stored_and_the_last_copy_stays(monkeypatch) -> None:
    code, _, stored = run(monkeypatch, [], plants=[BLACKBERRY], inat_status=503)
    assert code == 1
    assert stored == []


def test_with_no_listed_plant_inaturalist_is_never_asked(monkeypatch, capsys) -> None:
    code, requests, stored = run(monkeypatch, [], plants=[])
    assert code == 0 and stored == []
    assert not [r for r in requests if r.url.host == "api.inaturalist.org"]
    assert "no listed plant with a taxon id" in capsys.readouterr().out
