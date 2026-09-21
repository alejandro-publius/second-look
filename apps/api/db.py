"""Engine and session. SQLite locally, Postgres through DATABASE_URL in compose and production.

Alembic (apps/api/migrations) owns the schema in deployments. init_db() creates the same tables
directly for tests and for a first local run.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from apps.api.settings import settings


def make_engine(url: str) -> Engine:
    connect_args: dict[str, object] = {}
    pool_kwargs: dict[str, object] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        # Many threads share the file; wait up to 30 s for a writer instead of failing.
        connect_args = {"check_same_thread": False, "timeout": 30}
        if url.startswith("sqlite:///./"):
            Path(url.removeprefix("sqlite:///./")).parent.mkdir(parents=True, exist_ok=True)
        if url in {"sqlite://", "sqlite:///:memory:"}:
            # One shared in-memory database across connections.
            pool_kwargs = {"poolclass": StaticPool}
    return create_engine(url, connect_args=connect_args, **pool_kwargs)


engine: Engine = make_engine(settings.database_url)


def init_db() -> None:
    import apps.api.models  # noqa: F401  (registers every table on the metadata)

    SQLModel.metadata.create_all(engine)


def reset_db() -> None:
    """Drop and recreate every table. Tests only."""
    import apps.api.models  # noqa: F401

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes. Everything we store is UTC, so say so."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
