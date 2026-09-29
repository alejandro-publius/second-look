"""The routes that answer with a FHIR resource: FHIR's media type, and an OperationOutcome for an
error (audit finding api-fhir-5). worker/test/golden.test.ts and worker/test/e2e.mjs hold the same
checks for the Worker, with the same OperationOutcome, letter for letter."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api import fhir_store
from apps.api.fhir_http import FHIR_JSON, PLAIN_JSON, fhir_media_type, operation_outcome
from apps.api.tests.test_fhir_store import make_visit

BROWSER = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
FHIR_ROUTES = (
    "/api/spot/{id}/fhir",
    "/api/fhir/Bundle/{id}",
    "/api/fhir/referral/{id}",
    "/api/fhir/referral/{id}/example-result",
    "/api/walk/{id}/fhir",
)


def test_an_error_as_an_operation_outcome_the_same_as_the_worker() -> None:
    assert operation_outcome(404, "no FHIR record for this visit") == {
        "resourceType": "OperationOutcome",
        "text": {
            "status": "generated",
            "div": '<div xmlns="http://www.w3.org/1999/xhtml">'
            "<p>no FHIR record for this visit</p></div>",
        },
        "issue": [
            {
                "severity": "error",
                "code": "not-found",
                "details": {"text": "no FHIR record for this visit"},
            }
        ],
    }
    codes = [
        operation_outcome(s, "x")["issue"][0]["code"] for s in (404, 409, 413, 422, 429, 500, 503)
    ]
    assert codes == [
        "not-found",
        "conflict",
        "too-long",
        "invalid",
        "throttled",
        "exception",
        "exception",
    ]
    assert operation_outcome(404, "a <b> & c")["text"]["div"] == (
        '<div xmlns="http://www.w3.org/1999/xhtml"><p>a &lt;b&gt; &amp; c</p></div>'
    )


def test_fhirs_media_type_and_plain_json_for_a_browser_that_opens_the_link() -> None:
    assert FHIR_JSON == "application/fhir+json; charset=utf-8"
    for accept in (None, "", "*/*", "application/fhir+json", "application/json"):
        assert fhir_media_type(accept) == FHIR_JSON, accept
    for accept in (BROWSER, "TEXT/HTML"):
        assert fhir_media_type(accept) == PLAIN_JSON, accept


@pytest.mark.parametrize("route", FHIR_ROUTES)
def test_a_missing_record_is_an_operation_outcome_on_every_fhir_route(
    client: TestClient, route: str
) -> None:
    missing = client.get(route.format(id="walk-0000000000000000"))
    assert missing.status_code == 404
    assert missing.headers["content-type"] == FHIR_JSON
    assert missing.headers["vary"] == "Accept"
    body = missing.json()
    assert "detail" not in body
    sentence = body["issue"][0]["details"]["text"]
    assert len(sentence) > 10
    assert body == operation_outcome(404, sentence), "one issue, and nothing but the sentence"
    opened = client.get(route.format(id="walk-0000000000000000"), headers={"accept": BROWSER})
    assert opened.status_code == 404
    assert opened.headers["content-type"] == PLAIN_JSON
    assert opened.json() == body, "the same bytes, shown in the tab"


def test_a_stored_visit_goes_out_under_fhirs_media_type(client: TestClient) -> None:
    fhir_store.save_visit_bundle(make_visit("visit-0001", "spot-1"))
    for address in ("/api/fhir/Bundle/visit-0001", "/api/spot/spot-1/fhir"):
        found = client.get(address)
        assert found.status_code == 200
        assert found.headers["content-type"] == FHIR_JSON
        assert found.json()["resourceType"] == "Bundle"
        asked = client.get(address, headers={"accept": "application/fhir+json"})
        assert asked.headers["content-type"] == FHIR_JSON, "what a FHIR client asks for"
        opened = client.get(address, headers={"accept": BROWSER})
        assert opened.headers["content-type"] == PLAIN_JSON
        assert opened.json() == found.json()
    # What is not a FHIR resource stays plain JSON.
    assert client.get("/api/fhir/validation").headers["content-type"] == "application/json"
    assert client.get("/api/spot/spot-nowhere").json() == {"detail": "We do not know that spot."}


@pytest.mark.parametrize(
    "address",
    [
        "/api/spot/%E0%A4%A",
        "/api/walk/%ff",
        "/api/city/%",
        "/api/photo/%E0%A4%A?t=x",
        "/api/spot/%E0%A4%A/fhir",
        "/api/fhir/Bundle/%",
        "/api/fhir/referral/%E0%A4%A",
    ],
)
def test_a_broken_percent_code_in_the_address_is_a_plain_404(
    client: TestClient, address: str
) -> None:
    """Audit finding privacy-security-4 was a 500 on the Worker. The Python API never had it:
    its router reads a broken code as letters. This keeps it so."""
    answer = client.get(address)
    assert answer.status_code == 404, answer.text
    assert "error" not in answer.json()
    assert "Traceback" not in answer.text and "Error" not in answer.text
    # The iNaturalist line answers any creek name, known or not, with an empty view: no 500 here
    # either, and nothing but the view.
    empty = client.get("/api/inaturalist/%E0%A4%A")
    assert empty.status_code == 200
    assert empty.json()["status"] == "none" and "error" not in empty.json()
