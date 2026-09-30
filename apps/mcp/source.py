"""Where the MCP server reads our records from: the read only API, or a local export of it.

Both sources answer the same four questions with the same JSON documents, so every tool in
apps/mcp/server.py is written once. The API source calls our own endpoints and nothing else, with
a user agent that names the repository. It refuses an id that is not one plain path segment, so
an id such as ../skeleton or ..%2Ftwo can never reach another route. The export source reads a
folder that scripts/export_records.py wrote, so the server also runs with no network at all.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

import httpx

from core.fhir_emit import REPO_URL

USER_AGENT = f"second-look-mcp (+{REPO_URL})"
TIMEOUT_SECONDS = 15.0
DEFAULT_API = "https://second-look-api.thealexschroeder.workers.dev"
ID_RE = re.compile(r"[A-Za-z0-9._-]+")


class SourceError(Exception):
    """The record could not be read. The message is plain and names what was asked for."""


class Source(Protocol):
    def describe(self) -> str: ...

    def creeks(self) -> list[dict[str, Any]]: ...

    def city(self, creek: str) -> dict[str, Any]: ...

    def spot(self, spot_id: str) -> dict[str, Any]: ...

    def bundle(self, visit_id: str) -> dict[str, Any]: ...


def _safe_name(value: str) -> str:
    """A file name from an id: letters, digits, dot and hyphen only, so no id can climb out of
    the export folder."""
    cleaned = "".join(ch if ch.isalnum() or ch in ".-_" else "-" for ch in value).strip(".-")
    if not cleaned:
        raise SourceError(f"{value!r} is not an id")
    return cleaned


def _path_id(value: str) -> str:
    """An id as one segment of our own route: letters, digits, dot, underscore and hyphen, and
    never "." or "..". Anything else is refused, not cleaned: "../skeleton", "..%2Ftwo" or
    "x%3Fy" would otherwise climb to another Worker route or carry a query."""
    if not ID_RE.fullmatch(value) or value in {".", ".."}:
        raise SourceError(f"{value!r} is not an id")
    return quote(value, safe="")


def _reason(body: Any) -> str:
    """The API's own sentence for a 404: `detail` on the plain routes, and the first issue of the
    OperationOutcome on the routes that answer with a FHIR resource (apps/api/fhir_http.py)."""
    if not isinstance(body, dict):
        return ""
    if body.get("resourceType") == "OperationOutcome":
        issues = body.get("issue")
        first = issues[0] if isinstance(issues, list) and issues else None
        details = first.get("details") if isinstance(first, dict) else None
        text = details.get("text") if isinstance(details, dict) else None
        return text if isinstance(text, str) else ""
    detail = body.get("detail", "")
    return detail if isinstance(detail, str) else ""


class ExportSource:
    """A folder written by scripts/export_records.py: creeks.json, city/<creek>.json,
    spot/<id>.json and fhir/<visit>.json."""

    def __init__(self, folder: Path | str) -> None:
        self.folder = Path(folder)
        if not (self.folder / "creeks.json").exists():
            raise SourceError(f"{self.folder} holds no creeks.json; run scripts/export_records.py")

    def describe(self) -> str:
        return f"local export at {self.folder}"

    def _read(self, relative: str, what: str) -> dict[str, Any]:
        path = self.folder / relative
        if not path.exists():
            raise SourceError(f"no record for {what}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise SourceError(f"{relative} is not a JSON object")
        return data

    def creeks(self) -> list[dict[str, Any]]:
        listed = self._read("creeks.json", "the creek list").get("creeks", [])
        return list(listed) if isinstance(listed, list) else []

    def city(self, creek: str) -> dict[str, Any]:
        return self._read(f"city/{_safe_name(creek)}.json", f"creek {creek!r}")

    def spot(self, spot_id: str) -> dict[str, Any]:
        return self._read(f"spot/{_safe_name(spot_id)}.json", f"spot {spot_id!r}")

    def bundle(self, visit_id: str) -> dict[str, Any]:
        return self._read(f"fhir/{_safe_name(visit_id)}.json", f"visit {visit_id!r}")


class ApiSource:
    """Our own read only endpoints over HTTP. Calls nothing else, and _path_id checks every id."""

    def __init__(self, base_url: str = DEFAULT_API, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(
            timeout=TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )

    def describe(self) -> str:
        return f"read only API at {self.base_url}"

    def _get(self, path: str, what: str) -> dict[str, Any]:
        try:
            response = self._client.get(f"{self.base_url}{path}")
        except httpx.HTTPError as exc:
            raise SourceError(f"the API did not answer for {what}: {type(exc).__name__}") from exc
        if response.status_code == 404:
            detail = ""
            try:
                detail = _reason(response.json())
            except ValueError:
                pass
            raise SourceError(detail or f"no record for {what}")
        if response.status_code != 200:
            raise SourceError(f"the API answered {response.status_code} for {what}")
        data = response.json()
        if not isinstance(data, dict):
            raise SourceError(f"the API gave something that is not a JSON object for {what}")
        return data

    def creeks(self) -> list[dict[str, Any]]:
        listed = self._get("/api/creeks", "the creek list").get("creeks", [])
        return list(listed) if isinstance(listed, list) else []

    def city(self, creek: str) -> dict[str, Any]:
        return self._get(f"/api/city/{_path_id(creek)}", f"creek {creek!r}")

    def spot(self, spot_id: str) -> dict[str, Any]:
        return self._get(f"/api/spot/{_path_id(spot_id)}", f"spot {spot_id!r}")

    def bundle(self, visit_id: str) -> dict[str, Any]:
        return self._get(f"/api/fhir/Bundle/{_path_id(visit_id)}", f"visit {visit_id!r}")
