"""Creek check endpoints. Thin: the work is in apps/api/check.py. /api/two and every /fhir
route belong to W3 (apps/api/fhir_routes.py)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from apps.api import check
from apps.api import city as city_mod
from apps.api.deps import DB, Now
from apps.api.security import READ_LIMIT, STUDY_LIMIT, UPLOAD_LIMIT, rate_limited

router = APIRouter(prefix="/api")


@router.post("/check/draft", dependencies=[Depends(rate_limited(STUDY_LIMIT))])
def draft(body: check.DraftBody, db: DB, now: Now) -> dict[str, Any]:
    return check.create_draft(db, body, now=now)


@router.post("/check/finalize", dependencies=[Depends(rate_limited(STUDY_LIMIT))])
def finalize(body: check.FinalizeBody, db: DB, now: Now) -> dict[str, Any]:
    return check.finalize(db, body, now=now)


@router.get("/spot/{spot_id}", dependencies=[Depends(rate_limited(READ_LIMIT))])
def spot(spot_id: str, db: DB, now: Now) -> dict[str, Any]:
    return check.spot_view(db, spot_id, today=now.date())


@router.get("/city/{creek_id}", dependencies=[Depends(rate_limited(READ_LIMIT))])
def city(creek_id: str, db: DB, now: Now) -> dict[str, Any]:
    """The analyst's view. Every number in it carries the visit ids behind it."""
    return city_mod.city_view(db, creek_id, today=now.date())


@router.get("/fhir/referral/{spot_id}", dependencies=[Depends(rate_limited(READ_LIMIT))])
def referral(spot_id: str, db: DB, now: Now) -> dict[str, Any]:
    """A ServiceRequest for a pipe on the worth testing list. 404 with the reason otherwise."""
    return city_mod.referral_view(db, spot_id, now=now)


@router.get(
    "/fhir/referral/{spot_id}/example-result", dependencies=[Depends(rate_limited(READ_LIMIT))]
)
def example_result(spot_id: str, db: DB, now: Now) -> dict[str, Any]:
    """How a laboratory result would return to that record. An example, tagged as one."""
    return city_mod.example_result_view(db, spot_id, now=now)


@router.post("/quick/{spot_id}", dependencies=[Depends(rate_limited(STUDY_LIMIT))])
def quick(spot_id: str, body: check.QuickBody, db: DB, now: Now) -> dict[str, Any]:
    return check.quick_check(db, spot_id, body, now=now)


@router.post("/upload", dependencies=[Depends(rate_limited(UPLOAD_LIMIT))])
async def upload(file: UploadFile, db: DB, now: Now) -> dict[str, str]:
    # Read one byte past the cap so an oversized file is refused before it is decoded.
    data = await file.read(check.MAX_UPLOAD_BYTES + 1)
    if len(data) > check.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="That photo is over 8 MB. Send a smaller one.")
    return check.store_upload(db, data, now=now)


@router.get("/photo/{photo_id}", dependencies=[Depends(rate_limited(READ_LIMIT))])
def photo(photo_id: str, db: DB, t: str | None = None) -> FileResponse:
    path = check.photo_path(db, photo_id, t)
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, no-store", "Content-Disposition": "inline"},
    )
