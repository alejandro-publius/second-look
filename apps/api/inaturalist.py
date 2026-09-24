"""GET /api/inaturalist/{creek}: the iNaturalist context line for one creek, from the stored copy.

scripts/cache_inaturalist.py asks iNaturalist on the Mac once a day and stores a short summary
per creek in the `inaturalist_cache` table: per plant on the region's invasive list, how many
research-grade observations lay near the creek's spots, the latest date, and a link to them. This
reads that copy back. It never asks iNaturalist itself. worker/src/inaturalist.ts is the same
route on the Worker, and the two answer in the same shape.

Context only, by construction. The summary is withheld until a finished check at a real spot on
the creek has answered the invasive plant question. The gate is per creek, not per person:
nothing here knows who is asking, so once that first answer is in, anyone who opens the record
page or /city sees the line, a later volunteer who has not checked this creek yet included. It
keeps the line from leading the first answer on a creek, not every later one (review REVIEW_03
R07, docs/DECISIONS.md). Nothing counts it, and this module imports nothing that decides: not
core/gate.py, not core/followups.py, not apps/api/check.py, which reaches both.
scripts/tests/test_inaturalist.py checks that.
"""

from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session, select

from apps.api import content
from apps.api.db import as_utc
from apps.api.models import InaturalistCache, SpotRow, VisitRow
from core.act import looks_like_a_test_name
from core.records import Spot
from core.regions import Creek, creek_by_slug, creeks_from_regions, place_spot

# The form item that asks about invasive plants (content/form.yaml).
INVASIVE_ITEM = "invasive_species"
SOURCE = "https://www.inaturalist.org"
TERMS = "https://www.inaturalist.org/pages/terms"
LINK_PREFIX = "https://www.inaturalist.org/observations"


def _spot(row: SpotRow) -> Spot:
    return Spot(
        spot_id=row.spot_id,
        spot_name=row.spot_name,
        reach_id=row.reach_id,
        reach_name=row.reach_name,
        creek_id=row.creek_id,
        creek_name=row.creek_name,
        latitude=row.latitude,
        longitude=row.longitude,
        coarse=row.coarse,
    )


def creek_spots(db: Session, creek_ref: str) -> tuple[str, list[SpotRow]]:
    """The cache key for a creek reference and the real spots on that creek.

    The same reading as /api/city: a readable slug from the region pack, or a stored creek id whose
    spots all sit on one creek of the pack. A spot whose name reads like a test is left out.
    """
    known: list[Creek] = creeks_from_regions(content.get_content().regions)
    creek = creek_by_slug(creek_ref, known)
    rows = list(db.exec(select(SpotRow)).all())
    placed = {r.spot_id: place_spot(_spot(r), known) for r in rows}
    if creek is not None:
        slug = creek.slug
        spots = [r for r in rows if (p := placed[r.spot_id]) is not None and p.creek.slug == slug]
    else:
        spots = [r for r in rows if r.creek_id == creek_ref]
        on = {p.creek.slug for r in spots if (p := placed[r.spot_id]) is not None}
        creek = creek_by_slug(on.pop(), known) if len(on) == 1 else None
    real = [r for r in spots if not looks_like_a_test_name(r.spot_name)]
    return (creek.slug if creek is not None else creek_ref), real


def invasive_answered(db: Session, spot_ids: list[str]) -> bool:
    """True when a finished visit at one of these spots answered the invasive plant question."""
    if not spot_ids:
        return False
    rows = db.exec(
        select(VisitRow.answers_json).where(
            VisitRow.spot_id.in_(spot_ids),  # type: ignore[attr-defined]
            VisitRow.finalized_at.isnot(None),  # type: ignore[union-attr]
        )
    ).all()
    for raw in rows:
        answers = json.loads(raw)
        if isinstance(answers, dict) and answers.get(INVASIVE_ITEM) not in (None, ""):
            return True
    return False


def clean_species(raw: object) -> list[dict[str, Any]]:
    """Only the fields the page shows, and only links that go to iNaturalist's observations."""
    out: list[dict[str, Any]] = []
    for s in raw if isinstance(raw, list) else []:
        if not isinstance(s, dict):
            continue
        url = str(s.get("url") or "")
        count = s.get("count")
        # A bool is an int to Python but not a count; the Worker drops it too.
        if isinstance(count, bool) or not isinstance(count, int):
            continue
        if not url.startswith(LINK_PREFIX) or count < 1:
            continue
        out.append(
            {
                "taxon_id": s.get("taxon_id"),
                "name": str(s.get("name") or ""),
                "latin_name": str(s.get("latin_name") or ""),
                "count": count,
                "last_observed": str(s.get("last_observed") or ""),
                "url": url,
            }
        )
    return out


def _iso(row: InaturalistCache) -> str:
    when = as_utc(row.fetched_at)
    assert when is not None
    return when.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def inaturalist_view(db: Session, creek_ref: str) -> dict[str, Any]:
    key, spots = creek_spots(db, creek_ref)
    shown = invasive_answered(db, [s.spot_id for s in spots])
    row = db.get(InaturalistCache, key)
    body: dict[str, Any] = {}
    if row is not None:
        try:
            parsed = json.loads(row.body)
            body = parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            body = {}
    return {
        "creek": key,
        "shown": shown,
        "status": "cached" if row is not None else "none",
        "fetched_at": _iso(row) if row is not None else None,
        "since": body.get("since"),
        "radius_m": body.get("radius_m"),
        # Withheld until a finished check on this creek has answered the invasive plant question.
        "species": clean_species(body.get("species")) if shown else [],
        "source": SOURCE,
        "terms": TERMS,
    }
