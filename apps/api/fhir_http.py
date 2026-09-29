"""How a FHIR resource leaves the Python API. The same as worker/src/fhir_http.ts.

FHIR R4 names application/fhir+json as the media type for JSON, and our Library entry lists the
read only endpoint under it. So the routes that answer with a resource send that type, and an
error on them is an OperationOutcome, the resource FHIR uses to say what went wrong. The tests on
both sides hold the same OperationOutcome, letter for letter.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from core.fhir_emit import _narrative

FHIR_JSON = "application/fhir+json; charset=utf-8"
PLAIN_JSON = "application/json; charset=utf-8"
# FHIR's own issue types (the IssueType value set), one per answer this API gives.
ISSUE_CODES = {404: "not-found", 409: "conflict", 413: "too-long", 422: "invalid", 429: "throttled"}


def operation_outcome(status: int, sentence: str) -> dict[str, Any]:
    """The error as FHIR says it: one issue, with the same plain sentence the other routes give
    in detail. Any status without its own issue type is an exception, which is what a 500 is."""
    return {
        "resourceType": "OperationOutcome",
        "text": _narrative(sentence),
        "issue": [
            {
                "severity": "error",
                "code": ISSUE_CODES.get(status, "exception"),
                "details": {"text": sentence},
            }
        ],
    }


def fhir_media_type(accept: str | None) -> str:
    """The media type for a FHIR answer. A browser that opens the link asks for text/html first,
    and some browsers save a type they do not know as a file, so it gets the same bytes as plain
    JSON and shows them in the tab. Everyone else gets FHIR's type."""
    return PLAIN_JSON if "text/html" in (accept or "").lower() else FHIR_JSON


def fhir_response(request: Request, resource: dict[str, Any], status: int = 200) -> JSONResponse:
    """A FHIR resource as the answer, under FHIR's own media type."""
    return JSONResponse(
        content=resource,
        status_code=status,
        media_type=fhir_media_type(request.headers.get("accept")),
        headers={"Vary": "Accept"},
    )


def fhir_error(request: Request, status: int, sentence: str) -> JSONResponse:
    """An error on a FHIR route: an OperationOutcome with the status and the plain sentence."""
    return fhir_response(request, operation_outcome(status, sentence), status)
