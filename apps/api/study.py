"""The usability test: sessions, answers, scores, counts and the export. No route code here."""

from __future__ import annotations

import csv
import io
import json
import random
import secrets
import zipfile
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from apps.api import content
from apps.api.db import as_utc
from apps.api.models import ItemResponse, ObserverRow, RandomizationCounter, StudySession
from apps.api.security import sha256_hex
from apps.api.settings import settings
from core.allocator import arm_for_position
from core.lock import is_before_lock
from core.records import TestAnswer
from core.scoring import is_correct, score_sitting

SOURCE_LABELS = ("poster", "chat", "friends", "creek_group", "other")
UA_CLASSES = ("phone", "tablet", "desktop", "other")
ARMS = ("untrained", "trained")
TOKEN_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no 0, o, 1, l or i, so it can be read aloud
TOKEN_LENGTH = 16

SESSIONS_COLUMNS = [
    "session_id",
    "arm",
    "block_id",
    "source_label",
    "ua_class",
    "consent_version",
    "content_hash",
    "build_hash",
    "started_at_utc",
    "lesson_seconds_total",
    "completed_at_utc",
    "test_seconds",
    "is_test",
    "post_lock",
    "hidden_field_filled",
    "client_token_hash",
    "prior_experience",
    "warmup_choice",
    "unsent_count",
]
RESPONSES_COLUMNS = [
    "session_id",
    "item_id",
    "feature",
    "gold",
    "answer",
    "correct",
    "rt_ms",
    "position",
    # Update 07 section 1.3. answer is the confirmed choice and rt_ms is the time to confirm, so
    # they are repeated here under the names the analysis plan uses. The rest is description only.
    "first_choice",
    "final_choice",
    "t_first_ms",
    "t_confirm_ms",
    "n_changes",
]


class SessionBody(BaseModel):
    consent_version: str = Field(min_length=1, max_length=32)
    content_hash: str = Field(default="", max_length=64)
    build_hash: str = Field(default="", max_length=64)
    source_label: str | None = Field(default=None, max_length=64)
    hidden_field: str | None = Field(default=None, max_length=4096)
    client_token_hash: str = Field(min_length=8, max_length=128)
    ua_class: str | None = Field(default=None, max_length=64)
    warmup_choice: str | None = Field(default=None, max_length=16)


class ResponseBody(BaseModel):
    """`answer` is the confirmed choice, the one that is scored. The rest describes how the person
    got there: what they picked first, when, and how many times they changed it before Next."""

    session_id: str = Field(min_length=1, max_length=32)
    item_id: str = Field(min_length=1, max_length=16)
    answer: TestAnswer
    rt_ms: int = Field(ge=0, le=3_600_000)
    position: int = Field(ge=0, le=63)
    first_choice: TestAnswer | None = None
    t_first_ms: int | None = Field(default=None, ge=0, le=3_600_000)
    n_changes: int = Field(default=0, ge=0, le=999)


class LessonDoneBody(BaseModel):
    session_id: str = Field(min_length=1, max_length=32)
    lesson_seconds: dict[str, float] = Field(default_factory=dict, max_length=64)


class CompleteBody(BaseModel):
    """`answered_count` is how many items the browser says the person answered. If we hold fewer,
    we reply with the ids we are missing and complete nothing, so the browser can send them again
    from its own copy. `final` says the browser has tried and cannot close the gap."""

    session_id: str = Field(min_length=1, max_length=32)
    prior_experience: Literal["yes", "no"] | None = None
    keep_score: bool = False
    answered_count: int = Field(default=0, ge=0, le=64)
    final: bool = False


class NotFound(Exception):
    """Raised with a plain sentence for the person."""


class Conflict(Exception):
    """Raised when a repeat answer differs from the first."""


def coerce_source(raw: str | None) -> str:
    return raw if raw in SOURCE_LABELS else "other"


def coerce_ua(raw: str | None) -> str:
    return raw if raw in UA_CLASSES else "other"


def coerce_warmup(raw: str | None) -> str | None:
    if raw is None:
        return None
    return raw if raw in content.warmup_ids() else None


def new_contributor_token() -> str:
    return "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(TOKEN_LENGTH))


def ensure_counter(db: Session) -> None:
    """Creates the single counter row if it is missing. Safe to call from several processes."""
    if db.get(RandomizationCounter, 1) is not None:
        return
    seed = settings.randomization_seed or secrets.token_hex(16)
    db.add(RandomizationCounter(id=1, seed=seed, next_position=0))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


def take_position(db: Session) -> tuple[int, str]:
    """Takes the next slot in one UPDATE ... RETURNING statement. The row lock it takes holds
    until the caller commits, so the session insert and the slot are one unit of work."""
    stmt = (
        update(RandomizationCounter)
        .where(RandomizationCounter.id == 1)  # type: ignore[arg-type]
        .values(next_position=RandomizationCounter.next_position + 1)
        .returning(RandomizationCounter.next_position, RandomizationCounter.seed)  # type: ignore[call-overload]
    )
    row = db.execute(stmt).first()
    if row is None:
        db.rollback()
        ensure_counter(db)
        row = db.execute(stmt).first()
        if row is None:
            raise RuntimeError("randomization counter could not be created")
    return int(row[0]) - 1, str(row[1])


def create_session(db: Session, body: SessionBody, *, now: datetime, is_test: bool) -> StudySession:
    token_hash = sha256_hex(body.client_token_hash)[:32]
    earlier = db.exec(
        select(StudySession)
        .where(StudySession.client_token_hash == token_hash)
        .order_by(StudySession.started_at)  # type: ignore[arg-type]
    ).first()
    if earlier is not None and not is_test:
        # This browser already has an arm. Reloading must not let anyone shop for the other one.
        position, seed = take_position(db)
        arm, block_id = earlier.arm, earlier.block_id
    else:
        position, seed = take_position(db)
        arm, block_id = arm_for_position(seed, position, k=len(ARMS))
    session_id = secrets.token_hex(16)
    order = content.test_item_ids()
    random.Random(f"{seed}|order|{session_id}").shuffle(order)
    row = StudySession(
        id=session_id,
        arm=arm,
        block_id=block_id,
        item_order=json.dumps(order),
        consent_version=body.consent_version,
        content_hash=body.content_hash[:64],
        build_hash=body.build_hash[:64],
        consent_at=now,
        started_at=now,
        client_token_hash=token_hash,
        ua_class=coerce_ua(body.ua_class),
        is_test=is_test,
        source_label=coerce_source(body.source_label),
        hidden_field_filled=bool(body.hidden_field and body.hidden_field.strip()),
        post_lock=not is_before_lock(now),
        warmup_choice=coerce_warmup(body.warmup_choice),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _get_session(db: Session, session_id: str) -> StudySession:
    row = db.get(StudySession, session_id)
    if row is None:
        raise NotFound("We do not know that session. Start again from the first screen.")
    return row


def record_response(db: Session, body: ResponseBody, *, now: datetime) -> None:
    """Idempotent on (session_id, item_id). Same answer again is fine; a different one is refused
    and the first answer stays."""
    _get_session(db, body.session_id)
    if content.gold_for(body.item_id) is None:
        raise NotFound("We do not know that test item.")
    key = (body.session_id, body.item_id)
    existing = db.get(ItemResponse, key)
    if existing is None:
        db.add(
            ItemResponse(
                session_id=body.session_id,
                item_id=body.item_id,
                answer=body.answer,
                rt_ms=body.rt_ms,
                position=body.position,
                first_choice=body.first_choice,
                t_first_ms=body.t_first_ms,
                n_changes=body.n_changes,
                received_at=now,
            )
        )
        try:
            db.commit()
            return
        except IntegrityError:
            db.rollback()
            existing = db.get(ItemResponse, key)
            if existing is None:
                raise
    if existing.answer != body.answer:
        raise Conflict("This photo already has an answer. The first answer stays.")


def record_lesson(db: Session, body: LessonDoneBody) -> None:
    row = _get_session(db, body.session_id)
    clean = {str(k)[:32]: round(float(v), 1) for k, v in body.lesson_seconds.items()}
    row.lesson_seconds = json.dumps(clean)
    db.add(row)
    db.commit()


def missing_items(db: Session, row: StudySession) -> list[str]:
    """The item ids in this sitting's order that we hold no answer for."""
    held = {
        r.item_id
        for r in db.exec(select(ItemResponse).where(ItemResponse.session_id == row.id)).all()
    }
    return [item_id for item_id in json.loads(row.item_order) if item_id not in held]


def complete_session(db: Session, body: CompleteBody, *, now: datetime) -> dict[str, Any]:
    """The end screen does not appear until we hold every answer. If the browser says it took
    more answers than we hold, we name the ones we are missing and complete nothing, so it can
    send them again. Responses are idempotent, so a resend is safe. Only a browser that has
    tried and failed sends `final`, and then the gap is recorded as unsent_count."""
    row = _get_session(db, body.session_id)
    gap = missing_items(db, row)
    if gap and not body.final and row.completed_at is None:
        held = len(json.loads(row.item_order)) - len(gap)
        if body.answered_count > held:
            return {"need_resend": gap, "stored_count": held}
    answers = {
        r.item_id: r.answer
        for r in db.exec(select(ItemResponse).where(ItemResponse.session_id == row.id)).all()
    }
    scores = score_sitting(answers, content.get_content().test_items, now.date())  # type: ignore[arg-type]
    if row.completed_at is None:
        row.completed_at = now
        row.prior_experience = body.prior_experience
        row.unsent_count = max(0, body.answered_count - len(answers))
        db.add(row)
    result: dict[str, Any] = {
        "scores": [{"feature": s.feature, "correct": s.correct, "total": s.total} for s in scores],
        "correct_total": sum(s.correct for s in scores),
    }
    if body.keep_score:
        token = new_contributor_token()
        db.add(
            ObserverRow(
                contributor_token=token,
                scores_json=json.dumps(result["scores"]),
                tested_on=now.date(),
            )
        )
        result["contributor_token"] = token
    db.commit()
    return result


def counts(db: Session) -> dict[str, Any]:
    """Counts only, QA sessions left out. by_source counts completed sessions."""
    by_arm: dict[str, dict[str, int]] = {}
    for arm in ARMS:
        base = (
            select(func.count())
            .select_from(StudySession)
            .where(
                StudySession.arm == arm,
                StudySession.is_test == False,  # noqa: E712
            )
        )
        randomized = db.exec(base).one()
        completed = db.exec(base.where(StudySession.completed_at.isnot(None))).one()  # type: ignore[union-attr]
        by_arm[arm] = {"randomized": int(randomized), "completed": int(completed)}
    by_source = dict.fromkeys(SOURCE_LABELS, 0)
    rows = db.exec(
        select(StudySession.source_label, func.count())
        .where(StudySession.is_test == False, StudySession.completed_at.isnot(None))  # type: ignore[union-attr]  # noqa: E712
        .group_by(StudySession.source_label)
    ).all()
    for label, n in rows:
        by_source[coerce_source(label)] += int(n)
    post_lock = db.exec(
        select(func.count())
        .select_from(StudySession)
        .where(
            StudySession.is_test == False,  # noqa: E712
            StudySession.post_lock == True,  # noqa: E712
        )
    ).one()
    return {"by_arm": by_arm, "by_source": by_source, "post_lock": int(post_lock)}


def _iso(value: datetime | None) -> str:
    dt = as_utc(value)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else ""


def _flag(value: bool) -> int:
    return 1 if value else 0


def export_zip(db: Session) -> bytes:
    """sessions.csv and responses.csv in the schema from docs/CONTRACTS.md. Booleans are 0 or 1."""
    sessions = db.exec(select(StudySession).order_by(StudySession.started_at)).all()  # type: ignore[arg-type]
    responses = db.exec(
        select(ItemResponse).order_by(ItemResponse.session_id, ItemResponse.position)  # type: ignore[arg-type]
    ).all()
    first_response_at: dict[str, datetime] = {}
    for r in responses:
        received = as_utc(r.received_at)
        if received is None:
            continue
        current = first_response_at.get(r.session_id)
        if current is None or received < current:
            first_response_at[r.session_id] = received

    sessions_csv = io.StringIO()
    writer = csv.writer(sessions_csv)
    writer.writerow(SESSIONS_COLUMNS)
    for s in sessions:
        lesson_total = ""
        if s.lesson_seconds:
            lesson_total = str(round(sum(json.loads(s.lesson_seconds).values()), 1))
        test_seconds = ""
        completed = as_utc(s.completed_at)
        first = first_response_at.get(s.id)
        if completed is not None and first is not None:
            test_seconds = str(round((completed - first).total_seconds(), 1))
        writer.writerow(
            [
                s.id,
                s.arm,
                s.block_id,
                s.source_label,
                s.ua_class,
                s.consent_version,
                s.content_hash,
                s.build_hash,
                _iso(s.started_at),
                lesson_total,
                _iso(s.completed_at),
                test_seconds,
                _flag(s.is_test),
                _flag(s.post_lock),
                _flag(s.hidden_field_filled),
                s.client_token_hash,
                s.prior_experience or "",
                s.warmup_choice or "",
                s.unsent_count,
            ]
        )

    responses_csv = io.StringIO()
    writer = csv.writer(responses_csv)
    writer.writerow(RESPONSES_COLUMNS)
    for r in responses:
        gold = content.gold_for(r.item_id)
        feature = content.feature_for_test_item(r.item_id) or ""
        answer: TestAnswer = r.answer  # type: ignore[assignment]
        correct = _flag(gold is not None and is_correct(answer, gold))
        writer.writerow(
            [
                r.session_id,
                r.item_id,
                feature,
                gold or "",
                r.answer,
                correct,
                r.rt_ms,
                r.position,
                r.first_choice or "",
                r.answer,
                "" if r.t_first_ms is None else r.t_first_ms,
                r.rt_ms,
                r.n_changes,
            ]
        )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("sessions.csv", sessions_csv.getvalue())
        zf.writestr("responses.csv", responses_csv.getvalue())
    return buffer.getvalue()


def resume_state(db: Session, session_id: str, *, now: datetime) -> dict[str, Any]:
    """What a reloading browser needs: the same arm, the same item order, what we already hold,
    and the score if the sitting is already finished. Creates nothing and changes nothing, so a
    reload can never make a second session row or mint a second contributor token."""
    row = _get_session(db, session_id)
    answered = [
        r.item_id
        for r in db.exec(
            select(ItemResponse)
            .where(ItemResponse.session_id == row.id)
            .order_by(ItemResponse.position)  # type: ignore[arg-type]
        ).all()
    ]
    state: dict[str, Any] = {
        "session_id": row.id,
        "arm": row.arm,
        "item_order": json.loads(row.item_order),
        "lesson_first": row.arm == "trained",
        "lesson_done": bool(row.lesson_seconds),
        "answered": answered,
        "completed": row.completed_at is not None,
    }
    if row.completed_at is not None:
        answers = {
            r.item_id: r.answer
            for r in db.exec(select(ItemResponse).where(ItemResponse.session_id == row.id)).all()
        }
        scores = score_sitting(answers, content.get_content().test_items, now.date())  # type: ignore[arg-type]
        state["scores"] = [
            {"feature": s.feature, "correct": s.correct, "total": s.total} for s in scores
        ]
        state["correct_total"] = sum(s.correct for s in scores)
    return state
