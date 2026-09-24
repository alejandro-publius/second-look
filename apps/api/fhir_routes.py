"""Public read-only FHIR routes: a record as FHIR JSON, the validator verdict, and /api/two.

W1 includes `router` with a guarded import. Nothing here touches W1's tables. Their sandbox is
read at most once per second with a User-Agent that names the repo, and what we fetch is cached
on disk under data/sandbox_cache (gitignored), never in git (Update 02 section 4).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

from apps.api import fhir_store
from core.fhir_emit import OAH_SYSTEM, REPO_URL, SL_SYSTEM

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_BUNDLE = ROOT / "fhir" / "golden" / "visit-strawberry-creek-1.json"
VALIDATION_RESULTS = ROOT / "results" / "fhir_validation.json"

SANDBOX_DEFAULT_BASE = "https://sandbox.hl7europe.eu/oneaquahealth/fhir"
SANDBOX_USER_AGENT = f"second-look (+{REPO_URL})"
SANDBOX_MIN_INTERVAL_SECONDS = 1.0
SANDBOX_TIMEOUT_SECONDS = 10.0
CACHE_LIFETIME = timedelta(hours=1)
# One water chemistry Observation their guide publishes for the Almyros monitoring reach.
THEIRS_LOCATION = "Location/Loc-Almyros"
THEIRS_CODE = "dissolved-oxygen"

router = APIRouter()

_last_request_monotonic: float | None = None
_sleep = time.sleep


def sandbox_base_url() -> str:
    return os.environ.get("SANDBOX_BASE_URL", SANDBOX_DEFAULT_BASE).rstrip("/")


def cache_dir() -> Path:
    return Path(os.environ.get("SANDBOX_CACHE_DIR") or ROOT / "data" / "sandbox_cache")


def theirs_query() -> dict[str, str]:
    return {
        "subject": THEIRS_LOCATION,
        "code": f"{OAH_SYSTEM}|{os.environ.get('SANDBOX_THEIRS_CODE', THEIRS_CODE)}",
        "_sort": "-date",
        "_count": "1",
    }


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _wait_for_slot() -> None:
    """At most one request per second to their sandbox (hard rule 10)."""
    global _last_request_monotonic
    now = time.monotonic()
    if _last_request_monotonic is not None:
        remaining = SANDBOX_MIN_INTERVAL_SECONDS - (now - _last_request_monotonic)
        if remaining > 0:
            _sleep(remaining)
    _last_request_monotonic = time.monotonic()


def fetch_theirs_live() -> dict[str, Any] | None:
    """One GET to their sandbox. None when it does not answer with an Observation."""
    _wait_for_slot()
    try:
        with httpx.Client(
            timeout=SANDBOX_TIMEOUT_SECONDS,
            headers={"User-Agent": SANDBOX_USER_AGENT, "Accept": "application/fhir+json"},
        ) as client:
            response = client.get(f"{sandbox_base_url()}/Observation", params=theirs_query())
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    try:
        body = response.json()
    except ValueError:
        return None
    if not isinstance(body, dict):
        return None
    if body.get("resourceType") == "Observation":
        return body
    for entry in body.get("entry", []) if body.get("resourceType") == "Bundle" else []:
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Observation":
            return dict(resource)
    return None


def _cache_path() -> Path:
    key = hashlib.sha256(json.dumps(theirs_query(), sort_keys=True).encode()).hexdigest()[:16]
    return cache_dir() / f"theirs-{key}.json"


def _read_cache() -> tuple[dict[str, Any], datetime] | None:
    path = _cache_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(data["fetched_at"])
        observation = data["observation"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=UTC)
    if not isinstance(observation, dict):
        return None
    return observation, fetched_at


def _write_cache(observation: dict[str, Any], fetched_at: datetime) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"fetched_at": fetched_at.isoformat(), "observation": observation}, indent=2),
        encoding="utf-8",
    )


def theirs() -> tuple[dict[str, Any] | None, str, datetime]:
    """Their Observation, how we got it (ok, cached, down) and when it was fetched."""
    now = _now()
    cached = _read_cache()
    if cached is not None and now - cached[1] < CACHE_LIFETIME:
        return cached[0], "cached", cached[1]
    live = fetch_theirs_live()
    if live is None:
        return None, "down", now
    _write_cache(live, now)
    return live, "ok", now


def _observations(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        e["resource"]
        for e in bundle.get("entry", [])
        if e.get("resource", {}).get("resourceType") == "Observation"
    ]


def _place_of(bundle: dict[str, Any], obs: dict[str, Any] | None) -> str | None:
    """The name of the Location an Observation is about, from the same Bundle, not its raw id."""
    reference = str((obs or {}).get("subject", {}).get("reference", ""))
    if not reference.startswith("Location/"):
        return None
    wanted = reference.removeprefix("Location/")
    for e in bundle.get("entry", []):
        r = e.get("resource", {})
        if r.get("resourceType") == "Location" and r.get("id") == wanted:
            name = r.get("name")
            return name if isinstance(name, str) else None
    return None


def ours() -> tuple[dict[str, Any] | None, bool, str | None]:
    """One of our Observations: a feature answer from the latest stored visit.

    With no visit stored, the golden visit, which was made by hand for this demo. The second value
    says so, so the page can label it and never pass it off as a volunteer's answer (review
    REVIEW_03 R33). The third is the name of the place the Observation is about.
    """
    bundle: dict[str, Any] | None = None
    latest = fhir_store.latest_visit_id()
    if latest:
        bundle = fhir_store.load_visit_bundle(latest)
    example = bundle is None
    if bundle is None and GOLDEN_BUNDLE.exists():
        bundle = json.loads(GOLDEN_BUNDLE.read_text(encoding="utf-8"))
    if bundle is None:
        return None, example, None
    observations = _observations(bundle)
    pick = observations[0] if observations else None
    for obs in observations:
        if obs.get("code", {}).get("coding", [{}])[0].get("system") == SL_SYSTEM:
            pick = obs
            break
    return pick, example, _place_of(bundle, pick)


@router.get("/api/spot/{spot_id}/fhir")
def spot_fhir(spot_id: str) -> dict[str, Any]:
    """The latest visit at a spot as a FHIR collection Bundle."""
    visit_id = fhir_store.latest_visit_id_for_spot(spot_id)
    bundle = fhir_store.load_visit_bundle(visit_id) if visit_id else None
    if bundle is None:
        raise HTTPException(status_code=404, detail="no FHIR record for this spot yet")
    return bundle


@router.get("/api/fhir/Bundle/{visit_id}")
def visit_bundle(visit_id: str) -> dict[str, Any]:
    bundle = fhir_store.load_visit_bundle(visit_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="no FHIR record for this visit")
    return bundle


@router.get("/api/fhir/validation")
def validation() -> dict[str, Any]:
    """results/fhir_validation.json: guide commit, validator version and the verdict."""
    if not VALIDATION_RESULTS.exists():
        raise HTTPException(status_code=404, detail="no validation results yet")
    data = json.loads(VALIDATION_RESULTS.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


@router.get("/api/two")
def two() -> dict[str, Any]:
    """One volunteer Observation of ours beside one lab Observation from their sandbox."""
    their_observation, status, fetched_at = theirs()
    observation, example, place = ours()
    return {
        "ours": observation,
        "ours_example": example,
        "ours_place": place,
        "theirs": their_observation,
        "theirs_status": status,
        "fetched_at": fetched_at.isoformat().replace("+00:00", "Z"),
    }
