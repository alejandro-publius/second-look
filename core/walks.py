"""Video walks: a guided creek check made while watching an openly licensed clip (Update 14 3.7).

Pure functions. A walk visit is built on the person's own device from their answers. When the
walk is finished, the phone sends the answers to our store, which keeps the record as a demo for
WALK_KEEP_DAYS days in a table of its own (UPDATE_30 section 1 item 3), so its link opens on any
device. It is never counted and never mirrored to the sandbox. Every resource in its Bundle
carries a demo tag, and its spot, reach and creek ids all start with "walk-", so no stored creek
check can ever collide with one.

The walk itself (the clip, its credit, and the flags the checker raised on its frames at build
time) is a row of content/walks.yaml, written by scripts/build_walks.py.

A walk runs the creek check's follow-up rules on its answers, like the check itself
(walk_followups, walk_checks), and the store keeps the checks that ran with the record.
"""

from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from xml.sax.saxutils import escape

from core.fhir_emit import REPO_URL, emit_visit
from core.followups import Followup, SiteContext, select_followups
from core.records import CheckResult, Observer, Spot, VisitRecord

DEMO_TAG_SYSTEM = f"{REPO_URL}/tags"
DEMO_TAG_CODE = "demo-walk"
DEMO_TAG_DISPLAY = "Demo visit from a video walk. Never counted and never sent to the sandbox."
WALK_PREFIX = "walk-"
RATING_ITEM = "overall_rating"

# The stored demo record of a finished walk (UPDATE_30 section 1 item 3). docs/DATA_HANDLING.md
# says the same numbers in words. worker/src/core/walks.ts holds the same five.
WALK_KEEP_DAYS = 30  # a stored record is deleted this many days after it is stored
WALK_PAST_DAYS = 7  # a walk made offline may wait in the phone's queue this long
WALK_FUTURE_SECONDS = 300  # a phone clock a little ahead is not refused
WALK_DAILY_CAP = 200  # stored walk records per UTC day, on the whole server
WALK_MAX_BYTES = 4096  # the whole request body; every answer a walk can give fits in about 700
ANSWERED_AT_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})")


def walk_spot(walk: Mapping[str, Any]) -> Spot:
    """The one spot a walk has. No position: a clip is not a place anyone stood with a phone."""
    wid = f"{WALK_PREFIX}{walk['id']}"
    return Spot(
        spot_id=f"{wid}-spot",
        spot_name=str(walk["spot_name"]),
        reach_id=f"{wid}-reach",
        reach_name=str(walk["spot_name"]),
        creek_id=wid,
        creek_name=str(walk["creek_name"]),
        latitude=None,
        longitude=None,
        coarse=True,
    )


def utc_stamp(moment: datetime) -> str:
    """Seconds in UTC with a Z, the one spelling both languages write the same way.

    A time with no zone is read as UTC, as core/fhir_emit.py and the Worker read it. astimezone
    alone would read it as this machine's local time, so the id would change with the machine.
    """
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def walk_visit_id(walk_id: str, answered_at: datetime) -> str:
    """Deterministic: the walk and the moment. Answers stay out, so no float ever gets hashed."""
    blob = f"{walk_id}|{utc_stamp(answered_at)}"
    return WALK_PREFIX + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def walk_visit(
    walk: Mapping[str, Any],
    answers: Mapping[str, Any],
    answered_at: datetime,
    language: str = "en",
) -> VisitRecord:
    return VisitRecord(
        visit_id=walk_visit_id(str(walk["id"]), answered_at),
        spot=walk_spot(walk),
        observer=Observer(contributor_token=f"demo-walk-{walk['id']}"),
        answered_at=answered_at,
        answers=dict(answers),
        language=language,
    )


def tag_demo(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """A copy of the Bundle with the demo tag on the Bundle and on every resource in it."""
    out = copy.deepcopy(dict(bundle))
    tag = {"system": DEMO_TAG_SYSTEM, "code": DEMO_TAG_CODE, "display": DEMO_TAG_DISPLAY}
    for node in [out, *(e["resource"] for e in out.get("entry", []))]:
        meta = node.setdefault("meta", {})
        tags = [t for t in meta.get("tag", []) if t.get("system") != DEMO_TAG_SYSTEM]
        tags.append(dict(tag))
        meta["tag"] = tags
    return out


def _rating_changed_note(first: str, final: str) -> str:
    return (
        f"The first overall rating was {first}. "
        f"On the rating check the volunteer changed it to {final}."
    )


def walk_bundle(
    walk: Mapping[str, Any],
    answers: Mapping[str, Any],
    answered_at: datetime,
    final_rating: str | None = None,
    language: str = "en",
) -> dict[str, Any]:
    """The FHIR record of one walk visit, tagged as a demo.

    final_rating is the rating the rating check left (walk_checks). When it differs from the
    walk's own overall rating, the record answers the rating question with it, and the response's
    narrative names the first rating, so the record a city reads carries the rating the person
    kept, not the one they took back (critic round 15 F02). The answers stay as given.
    """
    first = answers.get(RATING_ITEM)
    changed = isinstance(first, str) and final_rating is not None and final_rating != first
    rated = {**answers, RATING_ITEM: final_rating} if changed else answers
    visit = walk_visit(walk, rated, answered_at, language)
    bundle = emit_visit(visit, test_sitting=None, emitted_at=answered_at)
    if changed:
        for entry in bundle["entry"]:
            resource = entry["resource"]
            if resource["resourceType"] == "QuestionnaireResponse":
                div = resource["text"]["div"]
                note = escape(_rating_changed_note(str(first), str(final_rating)))
                resource["text"]["div"] = div.replace("</p></div>", f"</p><p>{note}</p></div>")
    return tag_demo(bundle)


def is_demo(bundle: Mapping[str, Any]) -> bool:
    """True when a Bundle carries the demo tag. The sandbox mirror refuses these."""
    tags = bundle.get("meta", {}).get("tag", [])
    return any(t.get("system") == DEMO_TAG_SYSTEM and t.get("code") == DEMO_TAG_CODE for t in tags)


class WalkRecordError(ValueError):
    """A finished walk the store will not keep. The message is plain and says why."""


def walk_answered_at(text: object, now: datetime) -> datetime:
    """The moment a walk was finished, as the phone sent it, checked against the server's clock.

    An ISO time with a zone, to the second or finer. Not more than WALK_FUTURE_SECONDS ahead of
    the server, and not older than WALK_PAST_DAYS, so a walk made offline can still be sent from
    the queue, but nobody can store a walk dated wherever they like.
    """
    if not isinstance(text, str) or not ANSWERED_AT_RE.fullmatch(text):
        raise WalkRecordError("answered_at must be a time like 2026-09-25T10:00:00Z.")
    moment = datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)
    now = now if now.tzinfo else now.replace(tzinfo=UTC)
    if moment > now + timedelta(seconds=WALK_FUTURE_SECONDS):
        raise WalkRecordError("That walk is dated in the future. Check the phone's clock.")
    if moment < now - timedelta(days=WALK_PAST_DAYS):
        raise WalkRecordError(
            f"That walk is more than {WALK_PAST_DAYS} days old, so it is not stored."
        )
    return moment


def walk_record(
    walk: Mapping[str, Any],
    answers: Mapping[str, Any],
    answered_at: object,
    now: datetime,
    final_rating: str | None = None,
    language: str = "en",
) -> dict[str, Any]:
    """The row the store keeps for a finished walk: its id, its times and its demo Bundle.

    The id is the walk visit's own id, so the stored record is the record the phone built, and
    the same walk sent twice from the queue is one record. The caller checks the answers against
    the form first (apps/api/check.py, worker/src/check.ts), and the final rating with
    walk_checks, whose final rating the Bundle carries.
    """
    at = walk_answered_at(answered_at, now)
    now = now if now.tzinfo else now.replace(tzinfo=UTC)
    return {
        "record_id": walk_visit_id(str(walk["id"]), at),
        "walk_id": str(walk["id"]),
        "answered_at": utc_stamp(at),
        "created_at": utc_stamp(now),
        "delete_after": utc_stamp(now + timedelta(days=WALK_KEEP_DAYS)),
        "bundle": walk_bundle(walk, answers, at, final_rating, language),
    }


# The follow-up questions of a walk (judge walk W01): the creek check's own rules, the same pure
# function, over the walk's answers. A clip is no place anyone stood with a phone and has no
# weather, so rain is unknown and the dry pipe rule fails closed. Nobody took the test on this
# phone for the walk, so there is no score and the low score rule has nothing to read. The
# checker's flag on a clip is the walk's own question, gated at build time (scripts/build_walks.py),
# so no flag goes in here. What is left to fire today is the rating check.
WALK_SITE = SiteContext(rain="unknown")
# The answers each kind of follow-up takes on a walk. A walk uploads nothing, so a photo question,
# which cannot fire without a score anyway, can only be skipped.
WALK_FOLLOWUP_ANSWERS: dict[str, tuple[str, ...]] = {
    "yesno": ("yes", "no", "cant_tell", "skipped"),
    "keep_rating": ("keep", "change", "skipped"),
    "look_again": ("looked", "skipped"),
    "photo": ("skipped",),
}


def walk_followups(
    answers: Mapping[str, Any],
    table: Mapping[str, Any],
    *,
    form_items: Sequence[Mapping[str, Any]],
) -> list[Followup]:
    """The follow-ups a walk asks: select_followups with rain unknown, no score and no flag."""
    return select_followups(
        answers, WALK_SITE, None, (), table, form_items=form_items, checker_enabled=False
    )


def walk_checks(
    answers: Mapping[str, Any],
    followups: Sequence[Followup],
    question_texts: Sequence[str],
    given: Mapping[str, object],
    final_rating: str | None,
) -> tuple[list[CheckResult], str | None]:
    """The checks a finished walk ran, with what the person answered, and its final rating.

    Kept as the creek check keeps them (apps/api/check.py finalize): one CheckResult per follow-up
    asked, its question as the person read it, the answer or None, and the rule's params with its
    kind as the detail. The first rating is the walk's own overall rating. The final rating is the
    first, unless the rating check was answered "change", which must bring the new rating. Raises
    WalkRecordError, with a plain reason, for an answer to a question that was not asked, an
    answer the question does not take, or a final rating that does not follow from the answers.
    The caller checks final_rating is one of the form's ratings.
    """
    if len(question_texts) != len(followups):
        raise WalkRecordError("Every follow-up needs its question.")
    asked = {f.rule_id for f in followups}
    for rule_id in given:
        if rule_id not in asked:
            raise WalkRecordError(f"No follow-up called '{rule_id}' was asked in this walk.")
    first = answers.get(RATING_ITEM)
    first_rating = first if isinstance(first, str) else None
    final = first_rating
    checks: list[CheckResult] = []
    for f, text in zip(followups, question_texts, strict=True):
        raw = given.get(f.rule_id)
        answer: str | None = None
        if raw is not None:
            allowed = WALK_FOLLOWUP_ANSWERS.get(f.kind, ())
            if not isinstance(raw, str) or raw not in allowed:
                raise WalkRecordError(f"{f.rule_id}: answer {', '.join(allowed)}.")
            answer = raw
        if f.kind == "keep_rating" and answer == "change":
            if final_rating is None:
                raise WalkRecordError("A changed rating needs the new rating.")
            final = final_rating
        detail: dict[str, str | float | int | None] = {
            k: (v if isinstance(v, str | int | float) else str(v)) for k, v in f.params.items()
        }
        detail["kind"] = f.kind
        checks.append(
            CheckResult(
                rule_id=f.rule_id, asked=True, question_text=text, answer=answer, detail=detail
            )
        )
    if final_rating is not None and final_rating != final:
        raise WalkRecordError(
            "The final rating can differ from the first only when the rating check says change."
        )
    return checks, final
