"""Write our records as plain JSON files, the local export the MCP server can read offline.

  uv run python scripts/export_records.py --out data/export

Out: creeks.json, city/<creek>.json, spot/<spot_id>.json, fhir/<visit_id>.json. The same documents
the read only API serves, so apps/mcp/source.py reads either one with the same code. Nothing here
is a new number: every file is what GET /api/creeks, /api/city/{creek}, /api/spot/{id} and
/api/fhir/Bundle/{id} would have returned at the moment of the export.

data/ is gitignored. An export holds no name, no address and no token: the same rule as the API.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from apps.api import check, fhir_store
from apps.api import city as city_mod
from apps.api.models import SpotRow
from apps.mcp.source import _safe_name

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "export"


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def export(db: Session, out: Path, *, now: datetime) -> dict[str, int]:
    """Every creek, city view, spot record and stored Bundle. Returns the counts written."""
    today = now.date()
    creeks = city_mod.creeks_view(db)
    _write(out / "creeks.json", {**creeks, "exported_at": now.isoformat()})
    visit_ids: list[str] = []
    for creek in creeks["creeks"]:
        view = city_mod.city_view(db, creek["creek"], today=today)
        _write(out / "city" / f"{_safe_name(creek['creek'])}.json", view)
        visit_ids.extend(v for v in view["visit_ids"] if v not in visit_ids)
    spots = 0
    for row in db.exec(select(SpotRow)).all():
        view = check.spot_view(db, row.spot_id, today=today)
        view["place"] = city_mod.place_for_spot(db, row.spot_id)
        view["downstream_notes"] = city_mod.notes_for_spot(db, row.spot_id, today=today)
        _write(out / "spot" / f"{_safe_name(row.spot_id)}.json", view)
        spots += 1
    bundles = 0
    for visit_id in visit_ids:
        bundle = fhir_store.load_visit_bundle(visit_id)
        if bundle is None:
            continue
        _write(out / "fhir" / f"{_safe_name(visit_id)}.json", bundle)
        bundles += 1
    return {"creeks": len(creeks["creeks"]), "spots": spots, "bundles": bundles}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="folder to write into")
    args = parser.parse_args(argv)
    from apps.api.db import engine, init_db

    init_db()
    with Session(engine) as db:
        counts = export(db, Path(args.out), now=datetime.now(UTC))
    print(
        f"export-records: {counts['creeks']} creeks, {counts['spots']} spots, "
        f"{counts['bundles']} bundles into {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
