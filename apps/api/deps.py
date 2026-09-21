"""Shared FastAPI dependencies. Tests override get_now to freeze the clock."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from apps.api.db import get_session


def get_now() -> datetime:
    return datetime.now(UTC)


DB = Annotated[Session, Depends(get_session)]
Now = Annotated[datetime, Depends(get_now)]
