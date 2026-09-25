"""Tables. Study tables follow the master brief section 6 plus the Update 04 W1 columns.

Nothing here holds a name, an email, an address or a precise location the person did not place.
JSON-shaped values are stored as text so the same schema runs on SQLite and Postgres.
The Alembic migration in apps/api/migrations/versions mirrors these classes; change both together.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Column, DateTime, Text
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


def _tz_column(nullable: bool = False, index: bool = False) -> Column:
    return Column(DateTime(timezone=True), nullable=nullable, index=index)


class SkeletonPing(SQLModel, table=True):
    """P1 walking skeleton: one row written and read back through the real database."""

    __tablename__ = "skeleton_ping"

    id: int | None = Field(default=None, primary_key=True)
    note: str = Field(max_length=64)
    created_at: datetime = Field(default_factory=utcnow, sa_column=_tz_column())


class RandomizationCounter(SQLModel, table=True):
    """One row. next_position is taken and bumped inside one statement, so two sessions
    arriving together never share a slot. seed is the stored seed the allocator replays from."""

    __tablename__ = "randomization_counter"

    id: int = Field(default=1, primary_key=True)
    seed: str = Field(max_length=64)
    next_position: int = 0


class StudySession(SQLModel, table=True):
    """One usability test sitting. The id is random; nothing links it to a person."""

    __tablename__ = "session"

    id: str = Field(primary_key=True, max_length=32)
    arm: str = Field(max_length=16)
    block_id: int
    item_order: str = Field(sa_column=Column(Text, nullable=False))  # JSON list of item ids
    consent_version: str = Field(max_length=32)
    content_hash: str = Field(max_length=64)
    build_hash: str = Field(max_length=64)
    consent_at: datetime = Field(sa_column=_tz_column())
    started_at: datetime = Field(sa_column=_tz_column())
    lesson_seconds: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    completed_at: datetime | None = Field(default=None, sa_column=_tz_column(nullable=True))
    client_token_hash: str = Field(max_length=64)
    ua_class: str = Field(max_length=16)
    is_test: bool = False
    source_label: str = Field(max_length=16)
    hidden_field_filled: bool = False
    post_lock: bool = False
    prior_experience: str | None = Field(default=None, max_length=8)
    warmup_choice: str | None = Field(default=None, max_length=16)
    # How many answers the browser says it took that never reached us, after it tried to resend.
    # Above zero means the sitting is incomplete; see docs/analysis_plan.md exclusions.
    unsent_count: int = 0


class ItemResponse(SQLModel, table=True):
    """One answer to one test item. The pair (session_id, item_id) is the key, so a repeat
    cannot change the first answer."""

    __tablename__ = "response"

    session_id: str = Field(primary_key=True, max_length=32, foreign_key="session.id")
    item_id: str = Field(primary_key=True, max_length=16)
    # `answer` is the confirmed choice, the one that is scored. In docs/analysis_plan.md it is
    # called final_choice, and rt_ms is called t_confirm_ms. The three below are description only.
    answer: str = Field(max_length=16)
    rt_ms: int
    position: int
    first_choice: str | None = Field(default=None, max_length=16)
    t_first_ms: int | None = None
    n_changes: int = 0
    received_at: datetime = Field(sa_column=_tz_column())


class ObserverRow(SQLModel, table=True):
    """A volunteer who chose to keep their score. Never linked to a session id."""

    __tablename__ = "observer"

    contributor_token: str = Field(primary_key=True, max_length=32)
    scores_json: str = Field(sa_column=Column(Text, nullable=False))
    tested_on: date


class SpotRow(SQLModel, table=True):
    """A point on a creek. Coordinates round to about 1 km unless the person placed the pin."""

    __tablename__ = "spot"

    spot_id: str = Field(primary_key=True, max_length=32)
    spot_name: str = Field(max_length=80)
    reach_id: str = Field(max_length=40)
    reach_name: str = Field(max_length=80)
    creek_id: str = Field(max_length=40)
    creek_name: str = Field(max_length=80)
    latitude: float | None = None
    longitude: float | None = None
    coarse: bool = True
    created_at: datetime = Field(sa_column=_tz_column())


class VisitRow(SQLModel, table=True):
    """A guided check (kind = check) or a 20 second return check (kind = quick).
    A draft has finalized_at empty until POST /api/check/finalize."""

    __tablename__ = "visit"

    visit_id: str = Field(primary_key=True, max_length=32)
    spot_id: str = Field(max_length=32, foreign_key="spot.spot_id", index=True)
    kind: str = Field(max_length=8)
    contributor_token: str | None = Field(default=None, max_length=32)
    answered_at: datetime = Field(sa_column=_tz_column())
    answers_json: str = Field(sa_column=Column(Text, nullable=False))
    first_rating: str | None = Field(default=None, max_length=16)
    final_rating: str | None = Field(default=None, max_length=16)
    photo_ids_json: str = Field(sa_column=Column(Text, nullable=False))
    followups_json: str = Field(sa_column=Column(Text, nullable=False))
    site_json: str = Field(sa_column=Column(Text, nullable=False))
    finalized_at: datetime | None = Field(default=None, sa_column=_tz_column(nullable=True))
    software_version: str = Field(default="0.1.0", max_length=16)


class CheckResultRow(SQLModel, table=True):
    """One follow-up rule that ran during a visit and what the person answered."""

    __tablename__ = "check_result"

    id: int | None = Field(default=None, primary_key=True)
    visit_id: str = Field(max_length=32, foreign_key="visit.visit_id", index=True)
    rule_id: str = Field(max_length=32)
    asked: bool = True
    question_text: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    answer: str | None = Field(default=None, max_length=64)
    detail_json: str = Field(sa_column=Column(Text, nullable=False))


class UploadRow(SQLModel, table=True):
    """A re-encoded photo on private disk. token_hash guards the read; the token itself is
    given only to the uploader. scripts/cleanup_uploads.py deletes rows and files after 30 days."""

    __tablename__ = "upload"

    photo_id: str = Field(primary_key=True, max_length=32)
    file: str = Field(max_length=255)
    token_hash: str = Field(max_length=64)
    content_type: str = Field(max_length=32)
    size_bytes: int
    created_at: datetime = Field(sa_column=_tz_column(index=True))


class SandboxCache(SQLModel, table=True):
    """What GET /api/two last fetched from the sandbox (W3 writes it). Never in git."""

    __tablename__ = "sandbox_cache"

    cache_key: str = Field(primary_key=True, max_length=255)
    body: str = Field(sa_column=Column(Text, nullable=False))
    status: str = Field(max_length=16)
    fetched_at: datetime = Field(sa_column=_tz_column())


class InaturalistCache(SQLModel, table=True):
    """A short summary of iNaturalist sightings near one creek, as scripts/cache_inaturalist.py
    fetched it: per listed plant, a count, the latest date and a link. Context only; nothing
    counts it and nothing decides from it. Never in git."""

    __tablename__ = "inaturalist_cache"

    creek: str = Field(primary_key=True, max_length=255)
    body: str = Field(sa_column=Column(Text, nullable=False))
    fetched_at: datetime = Field(sa_column=_tz_column())


class WalkRecordRow(SQLModel, table=True):
    """A finished video walk's demo record (UPDATE_30 section 1 item 3), so its link opens on any
    device. A table of its own: nothing that counts, maps or mirrors creek checks reads it. The
    answers are coded values from the form's lists; no token, no position, no free text. Deleted
    after delete_after, 30 days after it was stored (apps/api/walk_store.py)."""

    __tablename__ = "walk_record"

    record_id: str = Field(primary_key=True, max_length=32)
    walk_id: str = Field(max_length=16)
    answered_at: datetime = Field(sa_column=_tz_column())
    answers_json: str = Field(sa_column=Column(Text, nullable=False))
    bundle_json: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(sa_column=_tz_column(index=True))
    delete_after: datetime = Field(sa_column=_tz_column(index=True))
