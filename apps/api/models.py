"""Tables. Study tables follow the master brief section 6 plus Update 04 W1 columns."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class SkeletonPing(SQLModel, table=True):
    """P1 walking skeleton: one row written and read back through the real database."""

    __tablename__ = "skeleton_ping"

    id: int | None = Field(default=None, primary_key=True)
    note: str = Field(max_length=64)
    created_at: datetime = Field(default_factory=utcnow)
