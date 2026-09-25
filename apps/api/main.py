"""Second Look API.

Nothing here stores anything about a person beyond what docs/CONTRACTS.md lists. Production
runs `uvicorn apps.api.main:app --no-access-log --proxy-headers`: the access log is the one
place a client address would appear, and the filters in apps/api/security.py drop or redact
it anyway in case the flag is forgotten.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session, func, select

from apps.api import check, core_calls, study, walk_store
from apps.api.content import get_content
from apps.api.db import engine, get_session, init_db
from apps.api.models import SkeletonPing
from apps.api.routes_check import router as check_router
from apps.api.routes_study import router as study_router
from apps.api.security import SecurityHeaders, install_log_filters
from apps.api.settings import settings

install_log_filters()
log = logging.getLogger("apps.api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    with Session(engine) as db:
        study.ensure_counter(db)
    get_content()  # fails loudly if the test set does not add up
    yield


app = FastAPI(
    title="Second Look API", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.public_web_origin],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-QA-Key"],
    max_age=600,
)
app.add_middleware(SecurityHeaders)  # added last, so it wraps CORS and every error response

app.include_router(study_router)
app.include_router(check_router)
try:
    from apps.api.fhir_routes import router as fhir_router  # W3

    app.include_router(fhir_router)
except ImportError:  # W3 not landed yet; the rest of the API still serves
    log.warning("fhir routes not installed")


@app.exception_handler(study.NotFound)
@app.exception_handler(check.NotFound)
def _not_found(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(study.Conflict)
def _conflict(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(check.Invalid)
def _invalid(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# A finished walk's record (apps/api/walk_store.py): the same answers the Worker gives.
@app.exception_handler(walk_store.TooLarge)
def _walk_too_large(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=413, content={"detail": str(exc)})


@app.exception_handler(walk_store.Conflict)
def _walk_conflict(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(walk_store.TooMany)
def _walk_too_many(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": str(exc)})


@app.exception_handler(core_calls.RecordBuilderMissing)
def _no_builder(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "The record builder is not installed, so this check cannot be saved."},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/skeleton/ping")
def skeleton_ping(session: Annotated[Session, Depends(get_session)]) -> dict[str, int]:
    session.add(SkeletonPing(note="walking skeleton"))
    session.commit()
    count = session.exec(select(func.count()).select_from(SkeletonPing)).one()
    return {"rows": int(count)}
