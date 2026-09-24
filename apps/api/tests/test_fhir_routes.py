"""The FHIR routes. Every HTTP call to their sandbox is mocked with respx; none is real."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api import fhir_routes, fhir_store
from apps.api.tests.test_fhir_store import make_visit
from core.fhir_emit import OAH_SYSTEM, SL_SYSTEM

ROOT = Path(__file__).resolve().parents[3]
SANDBOX = "https://sandbox.test/fhir"


def their_observation() -> dict:
    """Shaped like the Almyros lab results their guide publishes, with made-up numbers."""
    return {
        "resourceType": "Observation",
        "id": "Obs-Almyros-DissolvedOxygen-2020",
        "meta": {
            "profile": [
                "http://hl7.eu/fhir/ig/oah/StructureDefinition/observation-with-component-oah"
            ]
        },
        "status": "final",
        "code": {
            "coding": [
                {"system": OAH_SYSTEM, "code": "dissolved-oxygen", "display": "Dissolved Oxygen"}
            ],
            "text": "Dissolved Oxygen",
        },
        "subject": {"reference": "Location/Loc-Almyros"},
        "effectivePeriod": {"start": "2020-01-01", "end": "2020-12-31"},
        "performer": [{"display": "A government chemical service"}],
        "component": [
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-statistics",
                            "code": "median",
                            "display": "Median",
                        }
                    ]
                },
                "valueQuantity": {
                    "value": 5.6,
                    "unit": "milligram per liter",
                    "system": "http://unitsofmeasure.org",
                    "code": "mg/L",
                },
            }
        ],
    }


def search_bundle(*resources: dict) -> dict:
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(resources),
        "entry": [{"resource": r} for r in resources],
    }


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FHIR_STORE_DIR", str(tmp_path / "fhir_store"))
    monkeypatch.setenv("SANDBOX_CACHE_DIR", str(tmp_path / "sandbox_cache"))
    monkeypatch.setenv("SANDBOX_BASE_URL", SANDBOX)
    monkeypatch.setattr(fhir_routes, "_last_request_monotonic", None)
    app = FastAPI()
    app.include_router(fhir_routes.router)
    return TestClient(app)


def test_spot_and_visit_routes_serve_the_stored_bundle(client: TestClient) -> None:
    assert client.get("/api/spot/spot-1/fhir").status_code == 404
    assert client.get("/api/fhir/Bundle/visit-0001").status_code == 404
    fhir_store.save_visit_bundle(make_visit("visit-0001", "spot-1"))
    fhir_store.save_visit_bundle(make_visit("visit-0002", "spot-1"))
    by_spot = client.get("/api/spot/spot-1/fhir")
    assert by_spot.status_code == 200
    assert by_spot.json()["id"] == "sl-visit-visit-0002", "latest visit wins"
    by_visit = client.get("/api/fhir/Bundle/visit-0001")
    assert by_visit.status_code == 200
    assert by_visit.json()["id"] == "sl-visit-visit-0001"
    assert by_visit.json()["type"] == "collection"


def test_validation_route_returns_the_results_file(client: TestClient) -> None:
    response = client.get("/api/fhir/validation")
    if not (ROOT / "results" / "fhir_validation.json").exists():
        assert response.status_code == 404
        return
    assert response.status_code == 200
    body = response.json()
    assert body["ig_commit"] == "b907cf0"
    assert body["validator_version"] == "6.10.4"
    assert "errors" in body and "files" in body


@respx.mock
def test_two_fetches_theirs_once_then_serves_the_cache(client: TestClient) -> None:
    route = respx.get(f"{SANDBOX}/Observation").mock(
        return_value=httpx.Response(200, json=search_bundle(their_observation()))
    )
    first = client.get("/api/two")
    assert first.status_code == 200
    body = first.json()
    assert body["theirs_status"] == "ok"
    assert body["theirs"]["code"]["coding"][0]["code"] == "dissolved-oxygen"
    assert body["ours"]["resourceType"] == "Observation"
    assert body["ours"]["code"]["coding"][0]["system"] == SL_SYSTEM, "golden feature answer"
    # No visit is stored, so ours is the hand-made golden visit, and the route says so (R33).
    assert body["ours_example"] is True
    assert body["ours_place"] == "Strawberry Creek, campus reach, spot 1"
    assert body["fetched_at"].endswith("Z")
    request = route.calls.last.request
    assert request.headers["User-Agent"] == (
        "second-look (+https://github.com/alejandro-publius/second-look)"
    )
    assert request.url.params["subject"] == "Location/Loc-Almyros"
    assert request.url.params["code"] == f"{OAH_SYSTEM}|dissolved-oxygen"

    second = client.get("/api/two").json()
    assert second["theirs_status"] == "cached"
    assert second["theirs"] == body["theirs"]
    assert second["fetched_at"] == body["fetched_at"]
    assert route.call_count == 1


@respx.mock
def test_two_says_down_and_returns_ours_alone(client: TestClient) -> None:
    respx.get(f"{SANDBOX}/Observation").mock(side_effect=httpx.ConnectError("no route"))
    body = client.get("/api/two").json()
    assert body["theirs_status"] == "down"
    assert body["theirs"] is None
    assert body["ours"]["resourceType"] == "Observation"


@respx.mock
def test_two_treats_a_server_error_or_empty_search_as_down(client: TestClient) -> None:
    route = respx.get(f"{SANDBOX}/Observation").mock(return_value=httpx.Response(503))
    assert client.get("/api/two").json()["theirs_status"] == "down"
    route.mock(return_value=httpx.Response(200, json=search_bundle()))
    assert client.get("/api/two").json()["theirs_status"] == "down"
    route.mock(return_value=httpx.Response(200, text="not json"))
    assert client.get("/api/two").json()["theirs_status"] == "down"


@respx.mock
def test_two_prefers_our_latest_stored_observation(client: TestClient) -> None:
    respx.get(f"{SANDBOX}/Observation").mock(
        return_value=httpx.Response(200, json=search_bundle(their_observation()))
    )
    fhir_store.save_visit_bundle(make_visit("visit-0009", "spot-9"))
    body = client.get("/api/two").json()
    assert body["ours"]["id"] == "sl-obs-visit-0009-bank-type"
    assert body["ours_example"] is False, "a stored visit is a volunteer's answer, not the example"
    assert body["ours_place"] == "Strawberry Creek, campus reach, spot 1"


@respx.mock
def test_stale_cache_is_refetched(client: TestClient, tmp_path: Path) -> None:
    route = respx.get(f"{SANDBOX}/Observation").mock(
        return_value=httpx.Response(200, json=search_bundle(their_observation()))
    )
    client.get("/api/two")
    cache_file = next((tmp_path / "sandbox_cache").glob("theirs-*.json"))
    stale = json.loads(cache_file.read_text())
    stale["fetched_at"] = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    cache_file.write_text(json.dumps(stale))
    assert client.get("/api/two").json()["theirs_status"] == "ok"
    assert route.call_count == 2


@respx.mock
def test_requests_are_spaced_one_second_apart(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    respx.get(f"{SANDBOX}/Observation").mock(return_value=httpx.Response(503))
    waits: list[float] = []
    monkeypatch.setattr(fhir_routes, "_sleep", waits.append)
    client.get("/api/two")
    client.get("/api/two")
    assert len(waits) == 1
    assert 0 < waits[0] <= 1.0
