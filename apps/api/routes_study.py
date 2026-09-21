"""The usability test endpoints and the demo answer. Thin: the work is in apps/api/study.py."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from apps.api import content, study
from apps.api.deps import DB, Now
from apps.api.security import DEMO_LIMIT, READ_LIMIT, STUDY_LIMIT, rate_limited, same_secret
from apps.api.settings import settings
from core.records import TestAnswer
from core.scoring import is_correct

router = APIRouter(prefix="/api")


class DemoBody(BaseModel):
    item_id: str = Field(min_length=1, max_length=16)
    answer: TestAnswer


@router.post("/test/session", dependencies=[Depends(rate_limited(STUDY_LIMIT))])
def create_session(body: study.SessionBody, db: DB, now: Now, request: Request) -> dict[str, Any]:
    qa_key = settings.qa_key
    is_test = settings.secret_is_usable(qa_key) and same_secret(
        request.headers.get("x-qa-key"), qa_key
    )
    row = study.create_session(db, body, now=now, is_test=is_test)
    return {
        "session_id": row.id,
        "arm": row.arm,
        "item_order": json.loads(row.item_order),
        "lesson_first": row.arm == "trained",
    }


@router.post("/test/response", dependencies=[Depends(rate_limited(STUDY_LIMIT))])
def record_response(body: study.ResponseBody, db: DB, now: Now) -> dict[str, bool]:
    study.record_response(db, body, now=now)
    return {"ok": True}


@router.post("/test/lesson-done", dependencies=[Depends(rate_limited(STUDY_LIMIT))])
def lesson_done(body: study.LessonDoneBody, db: DB) -> dict[str, bool]:
    study.record_lesson(db, body)
    return {"ok": True}


@router.post("/test/complete", dependencies=[Depends(rate_limited(STUDY_LIMIT))])
def complete(body: study.CompleteBody, db: DB, now: Now) -> dict[str, Any]:
    return study.complete_session(db, body, now=now)


@router.get("/test/counts", dependencies=[Depends(rate_limited(READ_LIMIT))])
def counts(db: DB) -> dict[str, Any]:
    return study.counts(db)


@router.get("/test/export", dependencies=[Depends(rate_limited(READ_LIMIT))])
def export(db: DB, token: str | None = None) -> Response:
    expected = settings.export_token
    if not settings.secret_is_usable(expected) or not same_secret(token, expected):
        raise HTTPException(status_code=404, detail="Not found.")
    return Response(
        content=study.export_zip(db),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="second-look-export.zip"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/demo/answer", dependencies=[Depends(rate_limited(DEMO_LIMIT))])
def demo_answer(body: DemoBody) -> dict[str, Any]:
    """Judge mode. Takes no database session on purpose: there is nothing to store."""
    gold = content.gold_for(body.item_id)
    if gold is None:
        raise HTTPException(status_code=404, detail="We do not know that test item.")
    return {"correct": is_correct(body.answer, gold), "gold": gold}


@router.get("/content/hash", dependencies=[Depends(rate_limited(READ_LIMIT))])
def content_hash() -> dict[str, str]:
    return {"content_hash": content.get_content().content_hash(), "build_hash": settings.build_hash}
