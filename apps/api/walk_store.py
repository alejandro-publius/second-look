"""A finished video walk's demo record (UPDATE_30 section 1 item 3). worker/src/walk_store.ts is
the port the live site runs.

The phone sends a walk's answers once the walk is finished. They are checked against the form
(apps/api/check.validate_answers), the record is built by core.walks.walk_record, which golden
vectors prove equal in both languages, and the row goes into walk_record, a table of its own. So
nothing that counts, maps or mirrors creek checks can see it: not the study counts, not a real
creek's city view, not the sandbox mirror, which reads data/fhir_store only. Every resource in its
Bundle carries the demo tag.

The guards: the body is at most WALK_MAX_BYTES and holds the walk id, the answers and the time
only; at most WALK_DAILY_CAP records a day; each record is deleted WALK_KEEP_DAYS days after it is
stored, on the next store after that date, and is never served after it.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, time
from typing import Any

from pydantic import TypeAdapter, ValidationError
from sqlmodel import Session, col, func, select

from apps.api import check, content
from apps.api.db import as_utc
from apps.api.models import WalkRecordRow
from core.fhir_emit import check_bundle
from core.walks import (
    WALK_DAILY_CAP,
    WALK_KEEP_DAYS,
    WALK_MAX_BYTES,
    WalkRecordError,
    utc_stamp,
    walk_record,
)

BODY_KEYS = frozenset({"walk_id", "answers", "answered_at"})
RECORD_ID_RE = re.compile(r"walk-[0-9a-f]{16}")
_ANSWERS = TypeAdapter(dict[str, check.AnswerValue])


class TooLarge(Exception):
    """The body is over WALK_MAX_BYTES. 413."""


class Conflict(Exception):
    """The same walk and second with other answers: two people finished one clip at once. 409."""


class TooMany(Exception):
    """The daily cap on stored walk records is reached. 429."""


def _answers_text(answers: dict[str, Any]) -> str:
    """The answers as one string with the keys in order, so a walk sent twice compares equal."""
    return json.dumps(answers, sort_keys=True, separators=(",", ":"))


def _stored(row: WalkRecordRow) -> dict[str, str]:
    return {
        "record_id": row.record_id,
        "walk_id": row.walk_id,
        "answered_at": utc_stamp(as_utc(row.answered_at) or row.answered_at),
        "delete_after": utc_stamp(as_utc(row.delete_after) or row.delete_after),
    }


def purge_expired(db: Session, now: datetime) -> int:
    """Deletes every walk record past its date. Returns how many went."""
    rows = db.exec(select(WalkRecordRow).where(col(WalkRecordRow.delete_after) <= now)).all()
    for row in rows:
        db.delete(row)
    db.commit()
    return len(rows)


def parse_body(raw: bytes) -> dict[str, Any]:
    """The request body, when it is small, JSON, one object, and holds only what a walk sends."""
    if len(raw) > WALK_MAX_BYTES:
        raise TooLarge("That walk is too large to store.")
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise check.Invalid("That was not JSON.") from exc
    if not isinstance(body, dict):
        raise check.Invalid("Send the walk as one JSON object.")
    for key in body:
        if key not in BODY_KEYS:
            raise check.Invalid(f"A walk has no field called '{key}'.")
    return body


def store_walk(db: Session, raw: bytes, *, now: datetime) -> dict[str, str]:
    """POST /api/walk: stores a finished walk's record and returns its id. The same walk sent
    again, as the phone's queue may, returns the same id and stores nothing new."""
    body = parse_body(raw)
    walk_id = body.get("walk_id")
    walk = content.walk_by_id(walk_id) if isinstance(walk_id, str) else None
    if walk is None:
        raise check.NotFound("We do not know that walk.")
    given = body.get("answers")
    if not isinstance(given, dict):
        raise check.Invalid("answers must be an object of question ids and answers.")
    try:
        typed = _ANSWERS.validate_python(given)
    except ValidationError as exc:
        raise check.Invalid("Every answer must be a value from the form's lists.") from exc
    answers = check.validate_answers(typed)
    try:
        row = walk_record(walk, answers, body.get("answered_at"), now)
    except WalkRecordError as exc:
        raise check.Invalid(str(exc)) from exc
    if check_bundle(row["bundle"]):
        raise check.Invalid("That walk would make a record with a broken link inside it.")
    text = _answers_text(answers)
    purge_expired(db, now)
    existing = db.get(WalkRecordRow, row["record_id"])
    if existing is not None:
        if existing.walk_id == row["walk_id"] and existing.answers_json == text:
            return _stored(existing)
        raise Conflict(
            "Another walk of this clip was stored in the same second. "
            "Start again and finish it once more."
        )
    day_start = datetime.combine(now.astimezone(UTC).date(), time.min, tzinfo=UTC)
    today = db.exec(
        select(func.count())
        .select_from(WalkRecordRow)
        .where(col(WalkRecordRow.created_at) >= day_start)
    ).one()
    if int(today) >= WALK_DAILY_CAP:
        raise TooMany(
            "The demo store has taken all the walks it can for today. "
            "Your record is still on this page; try again tomorrow."
        )
    stored = WalkRecordRow(
        record_id=row["record_id"],
        walk_id=row["walk_id"],
        answered_at=_instant(row["answered_at"]),
        answers_json=text,
        bundle_json=json.dumps(row["bundle"], sort_keys=True),
        created_at=_instant(row["created_at"]),
        delete_after=_instant(row["delete_after"]),
    )
    db.add(stored)
    db.commit()
    return {k: row[k] for k in ("record_id", "walk_id", "answered_at", "delete_after")}


def walk_view(db: Session, record_id: str, *, now: datetime) -> dict[str, Any]:
    """GET /api/walk/{record_id}: one stored walk record, until its delete date."""
    gone = (
        f"We have no stored walk record called '{record_id[:40]}'. "
        f"A walk record is deleted {WALK_KEEP_DAYS} days after it is stored."
    )
    if not RECORD_ID_RE.fullmatch(record_id):
        raise check.NotFound(gone)
    row = db.get(WalkRecordRow, record_id)
    if row is None or (as_utc(row.delete_after) or now) <= now:
        raise check.NotFound(gone)
    return {
        **_stored(row),
        "answers": json.loads(row.answers_json),
        "bundle": json.loads(row.bundle_json),
    }


def _instant(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))
