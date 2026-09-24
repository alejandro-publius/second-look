"""GET /api/inaturalist/{creek}: the context line reads the stored copy, withholds the sightings
until a finished check on the creek has answered the invasive plant question, drops links that
leave iNaturalist, and moves no number on the city view."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlmodel import Session

from apps.api import core_calls
from apps.api.db import engine
from apps.api.models import InaturalistCache
from apps.api.tests.conftest import freeze_now
from apps.api.tests.test_check import GOOD_ANSWERS, NEW_SPOT, _dry
from apps.api.tests.test_city import a_visit, creek_of

NOW = datetime(2026, 9, 25, 15, 0, tzinfo=UTC)
FETCHED = datetime(2026, 9, 24, 7, 45, tzinfo=UTC)
SUMMARY = {
    "since": "2023-09-24",
    "radius_m": 300,
    "species": [
        {
            "taxon_id": 61317,
            "name": "Himalayan blackberry",
            "latin_name": "Rubus armeniacus",
            "count": 3,
            "last_observed": "2025-12-11",
            "url": "https://www.inaturalist.org/observations?id=1,2,3",
        },
        {
            "taxon_id": 1,
            "name": "A link that leaves iNaturalist",
            "latin_name": "x",
            "count": 1,
            "last_observed": "2025-01-01",
            "url": "https://example.org/",
        },
        {
            "taxon_id": 2,
            "name": "No sightings",
            "latin_name": "y",
            "count": 0,
            "last_observed": "",
            "url": "https://www.inaturalist.org/observations?id=",
        },
        {
            "taxon_id": 3,
            "name": "A yes, not a count",
            "latin_name": "z",
            "count": True,
            "last_observed": "2025-02-02",
            "url": "https://www.inaturalist.org/observations?id=4",
        },
    ],
}
NO_INVASIVE = {k: v for k, v in GOOD_ANSWERS.items() if k != "invasive_species"}


def store(creek: str, body: dict | str = SUMMARY) -> None:
    with Session(engine) as db:
        text = body if isinstance(body, str) else json.dumps(body)
        db.merge(InaturalistCache(creek=creek, body=text, fetched_at=FETCHED))
        db.commit()


def answered_creek(client, monkeypatch) -> str:
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    return a_visit(client, token=None, spot=NEW_SPOT, answers=GOOD_ANSWERS)["spot_id"]


def test_nothing_stored_says_so_and_shows_no_species(client, monkeypatch):
    answered_creek(client, monkeypatch)
    out = client.get("/api/inaturalist/strawberry-creek").json()
    assert out["creek"] == "strawberry-creek"
    assert out["shown"] is True
    assert out["status"] == "none"
    assert out["fetched_at"] is None
    assert out["species"] == []
    assert out["terms"] == "https://www.inaturalist.org/pages/terms"


def test_a_stored_summary_comes_back_with_its_fetch_time_and_only_real_sightings(
    client, monkeypatch
):
    answered_creek(client, monkeypatch)
    store("strawberry-creek")
    out = client.get("/api/inaturalist/strawberry-creek").json()
    assert out["status"] == "cached"
    assert out["fetched_at"] == "2026-09-24T07:45:00Z"
    assert out["since"] == "2023-09-24" and out["radius_m"] == 300
    assert [(s["name"], s["count"], s["last_observed"]) for s in out["species"]] == [
        ("Himalayan blackberry", 3, "2025-12-11")
    ]
    assert out["species"][0]["url"].startswith("https://www.inaturalist.org/observations")


def test_an_empty_or_broken_copy_shows_no_species(client, monkeypatch):
    answered_creek(client, monkeypatch)
    store("strawberry-creek", {"since": "2023-09-24", "radius_m": 300, "species": []})
    empty = client.get("/api/inaturalist/strawberry-creek").json()
    assert (empty["status"], empty["species"]) == ("cached", [])
    store("strawberry-creek", "not json")
    broken = client.get("/api/inaturalist/strawberry-creek").json()
    assert (broken["status"], broken["species"]) == ("cached", [])


def test_the_sightings_wait_until_the_invasive_plant_question_is_answered(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    spot = a_visit(client, token=None, spot=NEW_SPOT, answers=NO_INVASIVE)["spot_id"]
    store("strawberry-creek")
    before = client.get("/api/inaturalist/strawberry-creek").json()
    assert before["shown"] is False
    assert before["species"] == [], "withheld even though a copy is stored"
    # Someone answers the question on the same creek: now the line may be shown.
    a_visit(client, token=None, spot={"spot_id": spot}, answers=GOOD_ANSWERS)
    after = client.get("/api/inaturalist/strawberry-creek").json()
    assert after["shown"] is True
    assert [s["name"] for s in after["species"]] == ["Himalayan blackberry"]


def test_a_check_left_unfinished_does_not_open_the_line(client, monkeypatch):
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    body = {"spot": NEW_SPOT, "answers": GOOD_ANSWERS, "first_rating": "good", "photo_ids": []}
    assert client.post("/api/check/draft", json=body).status_code == 200
    store("strawberry-creek")
    out = client.get("/api/inaturalist/strawberry-creek").json()
    assert (out["shown"], out["species"]) == (False, [])


def test_a_pin_that_reads_like_a_test_does_not_open_the_line(client, monkeypatch):
    """The same pins /city keeps out of its numbers are kept out of this too."""
    monkeypatch.setattr(core_calls, "rain_status", _dry)
    freeze_now(NOW)
    test_pin = {"new": {**NEW_SPOT["new"], "name": "test"}}
    a_visit(client, token=None, spot=test_pin, answers=GOOD_ANSWERS)
    store("strawberry-creek")
    out = client.get("/api/inaturalist/strawberry-creek").json()
    assert (out["shown"], out["species"]) == (False, [])


def test_a_stored_creek_id_reads_the_same_row_as_its_slug(client, monkeypatch):
    spot = answered_creek(client, monkeypatch)
    store("strawberry-creek")
    out = client.get(f"/api/inaturalist/{creek_of(client, spot)}").json()
    assert out["creek"] == "strawberry-creek"
    assert out["status"] == "cached"


def test_an_unknown_creek_is_answered_and_shows_nothing(client):
    out = client.get("/api/inaturalist/nowhere").json()
    assert (out["shown"], out["status"], out["species"]) == (False, "none", [])


def test_no_number_on_the_city_view_moves(client, monkeypatch):
    answered_creek(client, monkeypatch)
    before = client.get("/api/city/strawberry-creek").json()
    store("strawberry-creek")
    after = client.get("/api/city/strawberry-creek").json()
    assert after == before
    assert "Himalayan" not in json.dumps(after)


def test_the_route_is_read_only(client):
    assert client.post("/api/inaturalist/strawberry-creek", json={}).status_code == 405
    assert client.delete("/api/inaturalist/strawberry-creek").status_code == 405
