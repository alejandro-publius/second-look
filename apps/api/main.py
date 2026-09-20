"""Second Look API. W1 extends this. Nothing here stores anything about a person."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlmodel import Session, func, select

from apps.api.db import get_session, init_db
from apps.api.models import SkeletonPing


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(
    title="Second Look API", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None
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
