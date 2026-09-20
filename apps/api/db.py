"""Engine and session. SQLite locally, Postgres through DATABASE_URL in compose and production."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from apps.api.settings import settings

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
if settings.database_url.startswith("sqlite:///./"):
    Path(settings.database_url.removeprefix("sqlite:///./")).parent.mkdir(
        parents=True, exist_ok=True
    )
_pool_kwargs: dict[str, object] = {"pool_pre_ping": True}
if settings.database_url in {"sqlite://", "sqlite:///:memory:"}:
    # One shared in-memory database across connections, for tests.
    _pool_kwargs = {"poolclass": StaticPool}
engine = create_engine(settings.database_url, connect_args=_connect_args, **_pool_kwargs)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
