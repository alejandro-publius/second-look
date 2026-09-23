"""Where the MCP server reads our records from: the read only API, or a local export of it.

Both sources answer the same four questions with the same JSON documents, so every tool in
apps/mcp/server.py is written once. The API source calls our own endpoints and nothing else, with
a user agent that names the repository. The export source reads a folder that
scripts/export_records.py wrote, so the server also runs with no network at all.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

import httpx

from core.fhir_emit import REPO_URL

USER_AGENT = f"second-look-mcp (+{REPO_URL})"
TIMEOUT_SECONDS = 15.0
DEFAULT_API = "https://second-look-api.thealexschroeder.workers.dev"


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
    """Our own read only endpoints over HTTP. Calls nothing else."""

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
                detail = str(response.json().get("detail", ""))
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
        return self._get(f"/api/city/{httpx.URL(path=creek).path}", f"creek {creek!r}")

    def spot(self, spot_id: str) -> dict[str, Any]:
        return self._get(f"/api/spot/{httpx.URL(path=spot_id).path}", f"spot {spot_id!r}")

    def bundle(self, visit_id: str) -> dict[str, Any]:
        return self._get(f"/api/fhir/Bundle/{httpx.URL(path=visit_id).path}", f"visit {visit_id!r}")
