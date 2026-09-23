"""The guided creek check: drafts, follow-ups, finalize, the spot view, quick checks, uploads.

Every stored answer is the human's and comes from a fixed set of values. No free text is ever
stored. Follow-up questions are chosen by core.followups (code, not a model). A visit becomes a
VisitRecord only through core.gate.build_record.
"""

from __future__ import annotations

import io
import json
import re
import secrets
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, select

from apps.api import content, core_calls
from apps.api.db import as_utc
from apps.api.models import CheckResultRow, ObserverRow, SpotRow, UploadRow, VisitRow
from apps.api.security import sha256_hex
from apps.api.settings import settings
from core import act
from core.records import CheckResult, FeatureId, FeatureScore, Observer, Spot, TestSitting

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_IMAGE_SIDE = 1600
JPEG_QUALITY = 85
COARSE_DECIMALS = 2  # about 1 km
FOLLOWUP_ANSWERS = {"yes", "no", "cant_tell", "keep", "change", "skipped"}
QUICK_TEXT = {
    "colour": "What colour is the water?",
    "smell": "Does it smell?",
    "pipe_running": "Is anything coming out of the pipe?",
}
SLIDER_RE = re.compile(r"^(joy|serenity|anger|fear):([0-5]|not_applicable)$")
YESNO_LABEL_KEYS = {"present": "test.yes", "absent": "test.no", "cant_tell": "test.cant_tell"}

AnswerValue = str | float | list[str]


class Invalid(Exception):
    """A body that does not fit the form. The message is plain and names the item."""


class NotFound(Exception):
    pass


class NewSpot(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name", "creek_name", "reach_name")
    @classmethod
    def _plain_place_name(cls, v: str | None) -> str | None:
        """A place name only: letters, numbers, spaces and . , ' - ( ) / and no digits run
        longer than four. The name is published in the record and copied into the FHIR
        narrative, so a street address or a person's details must not fit through here."""
        if v is None:
            return v
        v = " ".join(v.split())
        if not v:
            raise ValueError("A name is needed.")
        if not re.fullmatch(r"[A-Za-z0-9 .,'()/-]+", v):
            raise ValueError("Use letters, numbers, spaces and . , ' - ( ) / only.")
        if re.search(r"\d{5,}", v):
            raise ValueError("That looks like an address or a code, not a place name.")
        if "@" in v:
            raise ValueError("A place name cannot hold an email address.")
        return v

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    coarse: bool = True
    creek_name: str | None = Field(default=None, max_length=80)
    reach_name: str | None = Field(default=None, max_length=80)


class SpotRef(BaseModel):
    spot_id: str | None = Field(default=None, min_length=1, max_length=32)
    new: NewSpot | None = None


class DraftBody(BaseModel):
    contributor_token: str | None = Field(default=None, min_length=8, max_length=32)
    spot: SpotRef
    answers: dict[str, AnswerValue] = Field(default_factory=dict)
    first_rating: str | None = Field(default=None, max_length=16)
    photo_ids: list[str] = Field(default_factory=list, max_length=8)


class FinalizeBody(BaseModel):
    draft_id: str = Field(min_length=1, max_length=32)
    followup_answers: dict[str, str | float | bool] = Field(default_factory=dict)
    final_rating: str | None = Field(default=None, max_length=16)


class QuickBody(BaseModel):
    contributor_token: str | None = Field(default=None, min_length=8, max_length=32)
    colour: Literal["clear", "muddy", "foam", "coloured", "cant_tell"]
    smell: Literal["none", "bad", "cant_tell"]
    pipe_running: Literal["present", "absent", "cant_tell"]
    photo_id: str | None = Field(default=None, max_length=32)


class _SafeParams(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


# Answers ---------------------------------------------------------------------------------------


def _option_values(item: dict[str, Any]) -> set[str]:
    return {str(o["value"]) for o in item.get("options", []) or []}


def validate_answers(answers: dict[str, AnswerValue]) -> dict[str, AnswerValue]:
    """Every key is a form item id and every value is one the form allows. Nothing else passes."""
    clean: dict[str, AnswerValue] = {}
    plants: set[str] | None = None
    for item_id, value in answers.items():
        item = content.form_item(item_id)
        if item is None:
            raise Invalid(f"We do not have a question called {item_id!r}.")
        kind = item.get("type")
        if kind in ("choice",):
            if not isinstance(value, str) or value not in _option_values(item):
                raise Invalid(f"{item_id}: pick one of the listed options.")
        elif kind == "yesno":
            if value not in ("present", "absent", "cant_tell"):
                raise Invalid(f"{item_id}: answer present, absent or cant_tell.")
        elif kind == "multi":
            allowed = _option_values(item)
            if not isinstance(value, list) or any(v not in allowed for v in value):
                raise Invalid(f"{item_id}: choose only from the listed options.")
        elif kind == "number":
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise Invalid(f"{item_id}: send a number.")
            if not (0 <= float(value) <= 100):
                raise Invalid(f"{item_id}: that number is out of range.")
            value = float(value)
        elif kind == "pick_region_list":
            if plants is None:
                plants = content.region_plant_names() | {"cant_tell"}
            if not isinstance(value, list) or any(v not in plants for v in value):
                raise Invalid(f"{item_id}: choose plants from the regional list, or cant_tell.")
        elif kind == "sliders":
            if not isinstance(value, list) or any(
                not isinstance(v, str) or not SLIDER_RE.match(v) for v in value
            ):
                raise Invalid(f"{item_id}: send entries like joy:3 or fear:not_applicable.")
        else:
            raise Invalid(f"{item_id}: this question cannot be answered here.")
        clean[item_id] = value
    return clean


def validate_rating(value: str | None) -> str | None:
    if value is None:
        return None
    item = content.form_item("overall_rating")
    if item is None or value not in _option_values(item):
        raise Invalid("The overall rating must be good, moderate or poor.")
    return value


# Spots and observers ---------------------------------------------------------------------------


def _round_coarse(value: float | None, coarse: bool) -> float | None:
    if value is None:
        return None
    return round(value, COARSE_DECIMALS) if coarse else round(value, 6)


def nearby_existing_spot(db: Session, ref: SpotRef) -> dict[str, Any] | None:
    """An existing spot within 30 metres of a new pin, so the app can offer it first.

    A suggestion, never a merge. Two spots twenty five metres apart can be two real places, and
    quietly folding one into the other would lose a visit nobody could get back. Update 10
    tier 1 item 3; the arithmetic is core.act.nearest_spot, which is pure and tested.
    """
    if ref.spot_id or ref.new is None:
        return None
    if ref.new.latitude is None or ref.new.longitude is None:
        return None
    # Only precise pins can be compared. A coarse spot is deliberately rounded to about a
    # kilometre for privacy, so asking whether it is within thirty metres of anything is noise,
    # and answering would offer the wrong spot far more often than the right one.
    if ref.new.coarse:
        return None
    existing = [
        spot_from_row(r)
        for r in db.exec(select(SpotRow).where(SpotRow.coarse == False)).all()  # noqa: E712
    ]
    near = act.nearest_spot(ref.new.latitude, ref.new.longitude, existing)
    if near is None:
        return None
    return {
        "spot_id": near.spot.spot_id,
        "spot_name": near.spot.spot_name,
        "metres": round(near.metres),
    }


def resolve_spot(db: Session, ref: SpotRef, *, now: datetime) -> SpotRow:
    if ref.spot_id:
        row = db.get(SpotRow, ref.spot_id)
        if row is None:
            raise NotFound("We do not know that spot. Add it as a new spot.")
        return row
    if ref.new is None:
        raise Invalid("Say which spot this is, or describe a new one.")
    new = ref.new
    tail = secrets.token_hex(6)
    row = SpotRow(
        spot_id=f"spot-{tail}",
        spot_name=new.name.strip(),
        reach_id=f"reach-{tail}",
        reach_name=(new.reach_name or new.name).strip(),
        creek_id=f"creek-{tail}",
        creek_name=(new.creek_name or new.name).strip(),
        latitude=_round_coarse(new.latitude, new.coarse),
        longitude=_round_coarse(new.longitude, new.coarse),
        coarse=new.coarse,
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def spot_from_row(row: SpotRow) -> Spot:
    return Spot(
        spot_id=row.spot_id,
        spot_name=row.spot_name,
        reach_id=row.reach_id,
        reach_name=row.reach_name,
        creek_id=row.creek_id,
        creek_name=row.creek_name,
        latitude=row.latitude,
        longitude=row.longitude,
        coarse=row.coarse,
    )


def observer_from_token(db: Session, token: str | None) -> Observer | None:
    if not token:
        return None
    row = db.get(ObserverRow, token)
    if row is None:
        raise NotFound("We do not know that contributor token. Check it and try again.")
    scores = []
    for s in json.loads(row.scores_json):
        fid: FeatureId = s["feature"]
        scores.append(
            FeatureScore(
                feature=fid,
                correct=int(s["correct"]),
                total=int(s["total"]),
                tested_on=row.tested_on,
            )
        )
    return Observer(contributor_token=token, scores=tuple(scores))


def _check_photo_ids(db: Session, photo_ids: list[str]) -> list[str]:
    for pid in photo_ids:
        if db.get(UploadRow, pid) is None:
            raise Invalid(f"We do not have a photo called {pid!r}. Upload it first.")
    return list(dict.fromkeys(photo_ids))


# Follow-ups -------------------------------------------------------------------------------------


def _feature_name_for_param(value: object) -> str:
    """W5 passes the feature id with spaces; show the name from features.yaml instead."""
    raw = str(value).strip()
    fid = raw.replace(" ", "_")
    for f in content.get_content().features:
        if f.get("id") in (fid, raw):
            return str(f.get("name", raw))
    return raw


def question_text(view: core_calls.FollowupView) -> str:
    locale = content.get_content().locale
    params = dict(view.params)
    if "feature" in params:
        params["feature"] = _feature_name_for_param(params["feature"])
    template = locale.get(view.question_key, view.question_key)
    return template.format_map(_SafeParams(params))


def _api_kind(kind: str) -> str:
    return "yesno" if kind == "look_again" else kind


def create_draft(db: Session, body: DraftBody, *, now: datetime) -> dict[str, Any]:
    observer = observer_from_token(db, body.contributor_token)
    answers = validate_answers(body.answers)
    first_rating = validate_rating(body.first_rating)
    photo_ids = _check_photo_ids(db, body.photo_ids)
    # Look before the new spot is made, or it finds itself.
    nearby = nearby_existing_spot(db, body.spot)
    spot = resolve_spot(db, body.spot, now=now)
    rain = core_calls.rain_status(spot.latitude, spot.longitude, now)
    c = content.get_content()
    chosen = core_calls.select_followups(
        answers,
        rain,
        observer,
        table=c.followups,
        form_items=c.form.get("items", []),
        checker_enabled=settings.checker_enabled,
    )
    followups = [
        {
            "rule_id": f.rule_id,
            "kind": f.kind,
            "question_key": f.question_key,
            "question_text": question_text(f),
            "params": f.params,
        }
        for f in chosen
    ]
    visit_id = f"visit-{secrets.token_hex(8)}"
    db.add(
        VisitRow(
            visit_id=visit_id,
            spot_id=spot.spot_id,
            kind="check",
            contributor_token=body.contributor_token,
            answered_at=now,
            answers_json=json.dumps(answers),
            first_rating=first_rating,
            photo_ids_json=json.dumps(photo_ids),
            followups_json=json.dumps(followups),
            site_json=json.dumps(rain.as_dict()),
        )
    )
    db.commit()
    return {
        "draft_id": visit_id,
        # Not a merge: the app offers this spot first and the person decides.
        "nearby_spot": nearby,
        "followups": [
            {
                "rule_id": f["rule_id"],
                "question_text": f["question_text"],
                "kind": _api_kind(str(f["kind"])),
            }
            for f in followups
        ],
    }


def _clean_followup_answer(db: Session, followup: dict[str, Any], value: str | float | bool) -> str:
    if isinstance(value, bool):
        value = "yes" if value else "no"
    text = str(value).strip()[:64]
    if followup["kind"] == "photo":
        if text in FOLLOWUP_ANSWERS:
            return text
        if db.get(UploadRow, text) is None:
            raise Invalid(f"{followup['rule_id']}: send the photo id from the upload, or skipped.")
        return text
    if text not in FOLLOWUP_ANSWERS:
        raise Invalid(f"{followup['rule_id']}: answer yes, no, cant_tell, keep, change or skipped.")
    return text


def finalize(db: Session, body: FinalizeBody, *, now: datetime) -> dict[str, Any]:
    row = db.get(VisitRow, body.draft_id)
    if row is None or row.kind != "check":
        raise NotFound("We do not know that draft. Start the check again.")
    if row.finalized_at is not None:
        return {"visit_id": row.visit_id, "spot_id": row.spot_id, "fhir_saved": None}
    followups: list[dict[str, Any]] = json.loads(row.followups_json)
    by_rule = {f["rule_id"]: f for f in followups}
    for rule_id in body.followup_answers:
        if rule_id not in by_rule:
            raise Invalid(f"No follow-up called {rule_id!r} was asked in this check.")
    final_rating = validate_rating(body.final_rating)
    photo_ids: list[str] = json.loads(row.photo_ids_json)
    checks: list[CheckResult] = []
    for f in followups:
        raw = body.followup_answers.get(f["rule_id"])
        answer = _clean_followup_answer(db, f, raw) if raw is not None else None
        if f["kind"] == "photo" and answer and answer not in FOLLOWUP_ANSWERS:
            photo_ids.append(answer)
        detail: dict[str, str | float | int | None] = {
            k: (v if isinstance(v, str | int | float) else str(v)) for k, v in f["params"].items()
        }
        detail["kind"] = f["kind"]
        checks.append(
            CheckResult(
                rule_id=f["rule_id"],
                asked=True,
                question_text=f["question_text"],
                answer=answer,
                detail=detail,
            )
        )
    spot_row = db.get(SpotRow, row.spot_id)
    if spot_row is None:
        raise NotFound("The spot for this draft is gone.")
    observer = observer_from_token(db, row.contributor_token) or Observer(
        contributor_token=f"anon{row.visit_id[-12:]}"
    )
    record = core_calls.build_record(
        visit_id=row.visit_id,
        spot=spot_from_row(spot_row),
        observer=observer,
        answered_at=as_utc(row.answered_at) or now,
        answers=json.loads(row.answers_json),
        first_rating=row.first_rating,
        final_rating=final_rating,
        checks=checks,
        photo_ids=photo_ids,
    )
    for c in checks:
        db.add(
            CheckResultRow(
                visit_id=row.visit_id,
                rule_id=c.rule_id,
                asked=c.asked,
                question_text=c.question_text,
                answer=c.answer,
                detail_json=json.dumps(c.detail),
            )
        )
    row.final_rating = final_rating
    row.photo_ids_json = json.dumps(list(dict.fromkeys(photo_ids)))
    row.finalized_at = now
    db.add(row)
    db.commit()
    saved = core_calls.save_visit_bundle(
        record, test_sitting=sitting_for(db, row.contributor_token)
    )
    return {"visit_id": row.visit_id, "spot_id": row.spot_id, "fhir_saved": saved is not None}


def sitting_for(db: Session, token: str | None) -> TestSitting | None:
    """The observer's test sitting as the record carries it: the per feature k of 4, structured,
    so a reader of the FHIR does not have to parse a narrative to find the score. The sitting id
    is a hash of the token, like the Practitioner id, so the token itself never appears."""
    if not token:
        return None
    row = db.get(ObserverRow, token)
    if row is None:
        return None
    observer = observer_from_token(db, token)
    if observer is None or not observer.scores:
        return None
    return TestSitting(
        sitting_id=f"sitting-{sha256_hex(token)[:12]}",
        contributor_token=token,
        completed_at=datetime.combine(row.tested_on, datetime.min.time(), tzinfo=UTC),
        scores=observer.scores,
    )


def quick_check(db: Session, spot_id: str, body: QuickBody, *, now: datetime) -> dict[str, Any]:
    spot = db.get(SpotRow, spot_id)
    if spot is None:
        raise NotFound("We do not know that spot.")
    observer_from_token(db, body.contributor_token)
    photo_ids = _check_photo_ids(db, [body.photo_id] if body.photo_id else [])
    visit_id = f"visit-{secrets.token_hex(8)}"
    db.add(
        VisitRow(
            visit_id=visit_id,
            spot_id=spot_id,
            kind="quick",
            contributor_token=body.contributor_token,
            answered_at=now,
            answers_json=json.dumps(
                {"colour": body.colour, "smell": body.smell, "pipe_running": body.pipe_running}
            ),
            photo_ids_json=json.dumps(photo_ids),
            followups_json="[]",
            site_json="{}",
            finalized_at=now,
        )
    )
    db.commit()
    return {"visit_id": visit_id, "spot_id": spot_id}


# The record view -------------------------------------------------------------------------------


def _value_label(item: dict[str, Any] | None, value: AnswerValue, locale: dict[str, str]) -> str:
    values = value if isinstance(value, list) else [value]
    labels: list[str] = []
    for v in values:
        if item is not None and item.get("type") == "yesno" and str(v) in YESNO_LABEL_KEYS:
            labels.append(locale.get(YESNO_LABEL_KEYS[str(v)], str(v)))
            continue
        found = None
        for option in (item or {}).get("options", []) or []:
            if str(option.get("value")) == str(v):
                found = str(option.get("label", v))
                break
        labels.append(found if found is not None else str(v).replace("_", " "))
    return ", ".join(labels)


def _answer_views(
    row: VisitRow, observer: Observer | None, today: date, locale: dict[str, str]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    answers: dict[str, AnswerValue] = json.loads(row.answers_json)
    for item_id, value in answers.items():
        item = content.form_item(item_id) if row.kind == "check" else None
        if row.kind == "quick":
            text = QUICK_TEXT.get(item_id, item_id.replace("_", " "))
            feature: str | None = "pipe_running" if item_id == "pipe_running" else None
        else:
            text = str(item.get("text", item_id)) if item else item_id
            feature = str(item["feature"]) if item and item.get("feature") else None
        label_text: str | None = None
        passed: bool | None = None
        if observer is not None and feature is not None:
            fid: FeatureId = feature  # type: ignore[assignment]
            label = core_calls.observer_label(
                observer.score_for(fid), content.feature_name(feature), today, locale
            )
            if label is not None:
                label_text, passed = label.text, label.passed
        out.append(
            {
                "item_id": item_id,
                "text": text,
                "value": value,
                "label": _value_label(item, value, locale),
                "feature": feature,
                "observer_label": label_text,
                "observer_passed": passed,
            }
        )
    return out


def _iso(value: datetime | None) -> str | None:
    dt = as_utc(value)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def spot_view(db: Session, spot_id: str, *, today: date) -> dict[str, Any]:
    spot = db.get(SpotRow, spot_id)
    if spot is None:
        raise NotFound("We do not know that spot.")
    locale = content.get_content().locale
    visits = db.exec(
        select(VisitRow)
        .where(VisitRow.spot_id == spot_id, VisitRow.finalized_at.isnot(None))  # type: ignore[union-attr]
        .order_by(VisitRow.answered_at.desc())  # type: ignore[attr-defined]
    ).all()
    observers: dict[str, Observer | None] = {}
    visit_views: list[dict[str, Any]] = []
    for v in visits:
        token = v.contributor_token
        if token and token not in observers:
            row = db.get(ObserverRow, token)
            observers[token] = observer_from_token(db, token) if row else None
        observer = observers.get(token) if token else None
        checks = db.exec(select(CheckResultRow).where(CheckResultRow.visit_id == v.visit_id)).all()
        visit_views.append(
            {
                "visit_id": v.visit_id,
                "kind": v.kind,
                "answered_at": _iso(v.answered_at),
                "answers": _answer_views(v, observer, today, locale),
                "checks": [
                    {
                        "rule_id": c.rule_id,
                        "asked": c.asked,
                        "question_text": c.question_text,
                        "answer": c.answer,
                        "detail": json.loads(c.detail_json),
                    }
                    for c in checks
                ],
                "first_rating": v.first_rating,
                "final_rating": v.final_rating,
                "photo_count": len(json.loads(v.photo_ids_json)),
                "observer_scored": observer is not None,
            }
        )
    return {
        "spot": {
            "spot_id": spot.spot_id,
            "spot_name": spot.spot_name,
            "reach_id": spot.reach_id,
            "reach_name": spot.reach_name,
            "creek_id": spot.creek_id,
            "creek_name": spot.creek_name,
            "latitude": spot.latitude,
            "longitude": spot.longitude,
            "coarse": spot.coarse,
        },
        "visits": visit_views,
        "health_card": core_calls.pick_actions(content.get_content().sentences, spot_id),
    }


# Uploads ----------------------------------------------------------------------------------------


def sniff_image(head: bytes) -> str | None:
    """The real type from the first bytes. Anything else is refused whatever the name says."""
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def store_upload(db: Session, data: bytes, *, now: datetime) -> dict[str, str]:
    """Re-encodes to a fresh JPEG (no EXIF, no ICC, at most 1600 px) and hands back the id and
    the one token that can read it."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise Invalid("That photo is over 8 MB. Please send a smaller one.")
    if sniff_image(data[:16]) is None:
        raise Invalid("Only JPEG, PNG or WebP photos can be uploaded.")
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            out = img.convert("RGB")
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise Invalid("We could not read that photo. Try another one.") from exc
    out.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    photo_id = f"up-{secrets.token_hex(8)}"
    token = secrets.token_urlsafe(24)
    target = upload_dir() / f"{photo_id}.jpg"
    out.save(target, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    db.add(
        UploadRow(
            photo_id=photo_id,
            file=target.name,
            token_hash=sha256_hex(token),
            content_type="image/jpeg",
            size_bytes=target.stat().st_size,
            created_at=now,
        )
    )
    db.commit()
    return {"photo_id": photo_id, "token": token}


def photo_path(db: Session, photo_id: str, token: str | None) -> Path:
    """The file, only when the token matches in constant time. Otherwise NotFound."""
    import hmac

    row = db.get(UploadRow, photo_id)
    if row is None or not token:
        raise NotFound("Not found.")
    if not hmac.compare_digest(sha256_hex(token), row.token_hash):
        raise NotFound("Not found.")
    path = upload_dir() / row.file
    if not path.is_file():
        raise NotFound("Not found.")
    return path
