"""Our own store of validated FHIR JSON, the source of truth the sandbox mirrors (hard rule 10).

One file per visit under data/fhir_store/<visit_id>.json plus a small index that maps a spot to
its visits. data/ is gitignored. No database, no dependency on W1's tables.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.fhir_emit import FhirEmitError, check_bundle, emit_visit, fhir_id
from core.records import TestSitting, VisitRecord

ROOT = Path(__file__).resolve().parents[2]
INDEX_NAME = "index.json"


def store_dir() -> Path:
    """data/fhir_store by default; FHIR_STORE_DIR overrides it (tests use a temp folder)."""
    return Path(os.environ.get("FHIR_STORE_DIR") or ROOT / "data" / "fhir_store")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _index_path() -> Path:
    return store_dir() / INDEX_NAME


def load_index() -> dict[str, Any]:
    return _read_json(_index_path()) or {"spots": {}, "latest": None}


def _bundle_path(visit_id: str) -> Path:
    return store_dir() / f"{fhir_id(visit_id)}.json"


def save_visit_bundle(visit: VisitRecord, *, test_sitting: TestSitting | None = None) -> Path:
    """Emit, check every reference resolves inside the Bundle, then write it. Returns the path."""
    bundle = emit_visit(visit, test_sitting=test_sitting, emitted_at=datetime.now(UTC))
    problems = check_bundle(bundle)
    if problems:
        raise FhirEmitError("; ".join(problems))
    path = _bundle_path(visit.visit_id)
    _write_json(path, bundle)
    index = load_index()
    visits: list[str] = index["spots"].setdefault(visit.spot.spot_id, [])
    if visit.visit_id in visits:
        visits.remove(visit.visit_id)
    visits.append(visit.visit_id)
    index["latest"] = visit.visit_id
    _write_json(_index_path(), index)
    return path


def load_visit_bundle(visit_id: str) -> dict[str, Any] | None:
    return _read_json(_bundle_path(visit_id))


def latest_visit_id_for_spot(spot_id: str) -> str | None:
    visits = load_index()["spots"].get(spot_id) or []
    return visits[-1] if visits else None


def latest_visit_id() -> str | None:
    latest = load_index().get("latest")
    return str(latest) if latest else None


def stored_bundle_paths() -> list[Path]:
    """Every stored visit Bundle, sorted by file name. The index is not a Bundle."""
    root = store_dir()
    if not root.exists():
        return []
    return sorted(p for p in root.glob("*.json") if p.name != INDEX_NAME)
