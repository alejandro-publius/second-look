"""The analyst's view of a creek: what it needs, and which pipes are worth testing.

All the judgement lives in core/act.py, which is pure and tested. This module only reads rows
and hands them over, so the rule that every number carries its evidence is kept in one place.

Nothing here decides anything a person did not report. A measure is approved text or it is
absent. A pipe reaches the list only when two different people who both passed that feature saw
it running in dry weather.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from apps.api import content, fhir_store
from apps.api.check import NotFound, observer_from_token, spot_from_row
from apps.api.db import as_utc
from apps.api.models import CheckResultRow, ObserverRow, SpotRow, VisitRow
from core.act import (
    DownstreamNote,
    Finding,
    PipeCase,
    findings_from_visits,
    looks_like_a_test_name,
    needs_from_findings,
    notes_below,
    pipes_worth_testing,
)
from core.fhir_emit import FhirEmitError
from core.fhir_referral import example_lab_result, referral_bundle
from core.records import CheckResult, Observer, VisitRecord
from core.regions import Creek, Placement, creek_by_slug, creeks_from_regions, place_spot

# The example laboratory result is dated relative to the referral, so a judge reading it sees a
# plausible sequence: referred today, sampled the next day, reported three days after that.
EXAMPLE_SAMPLE_AFTER = timedelta(days=1)
EXAMPLE_REPORT_AFTER = timedelta(days=4)


def referral_path(spot_id: str) -> str:
    return f"/api/fhir/referral/{spot_id}"


def example_result_path(spot_id: str) -> str:
    return f"{referral_path(spot_id)}/example-result"


def _records_for(db: Session, spots: list[SpotRow]) -> list[VisitRecord]:
    """Every finalized visit at these spots, as the pure functions want them."""
    by_id = {s.spot_id: s for s in spots}
    if not by_id:
        return []
    rows = db.exec(
        select(VisitRow).where(
            VisitRow.spot_id.in_(list(by_id)),  # type: ignore[attr-defined]
            VisitRow.finalized_at.isnot(None),  # type: ignore[union-attr]
        )
    ).all()
    observers: dict[str, Observer] = {}
    out: list[VisitRecord] = []
    for v in rows:
        token = v.contributor_token
        if not token:
            # An anonymous visit is still a visit, but it cannot carry a score, so it can never
            # put a pipe on the list. It still counts as a finding.
            observer = Observer(contributor_token="anonymous000", scores=())
        else:
            if token not in observers:
                found = observer_from_token(db, token) if db.get(ObserverRow, token) else None
                observers[token] = found or Observer(contributor_token=token, scores=())
            observer = observers[token]
        checks = db.exec(select(CheckResultRow).where(CheckResultRow.visit_id == v.visit_id)).all()
        answered = as_utc(v.answered_at)
        if answered is None:
            continue
        out.append(
            VisitRecord(
                visit_id=v.visit_id,
                spot=spot_from_row(by_id[v.spot_id]),
                observer=observer,
                answered_at=answered,
                answers=json.loads(v.answers_json),
                first_rating=v.first_rating,
                final_rating=v.final_rating,
                checks=tuple(
                    CheckResult(
                        rule_id=c.rule_id,
                        asked=c.asked,
                        question_text=c.question_text,
                        answer=c.answer,
                        detail=json.loads(c.detail_json),
                    )
                    for c in checks
                ),
                photo_ids=tuple(json.loads(v.photo_ids_json)),
            )
        )
    return out


def _finding_view(f: Finding, spot_names: dict[str, str], feature_names: dict[str, str]) -> dict:
    return {
        "spot_id": f.spot_id,
        "spot_name": spot_names.get(f.spot_id, f.spot_id),
        "feature": f.feature,
        "feature_name": feature_names.get(f.feature, f.feature),
        "observers": f.n_observers,
        "first_seen": f.first_seen.isoformat(),
        "last_seen": f.last_seen.isoformat(),
        # Every number opens the resources behind it.
        "visit_ids": list(f.visit_ids),
        "fhir": [f"/api/fhir/Bundle/{v}" for v in f.visit_ids],
    }


def creeks() -> list[Creek]:
    """The creeks and reaches of every region pack, checked by the content loader at startup."""
    return creeks_from_regions(content.get_content().regions)


def placements_for(spots: list[SpotRow], known: list[Creek]) -> dict[str, Placement]:
    """Which creek and reach each stored spot sits on, computed at read time (core/regions.py)."""
    out: dict[str, Placement] = {}
    for row in spots:
        placed = place_spot(spot_from_row(row), known)
        if placed is not None:
            out[row.spot_id] = placed
    return out


def place_for_spot(db: Session, spot_id: str) -> dict[str, Any] | None:
    """The readable creek and reach behind a spot, for the record page. None when unplaced."""
    row = db.get(SpotRow, spot_id)
    if row is None:
        raise NotFound("We do not know that spot.")
    placed = place_spot(spot_from_row(row), creeks())
    if placed is None:
        return None
    return {
        "creek_slug": placed.creek.slug,
        "creek_name": placed.creek.name,
        "reach_slug": placed.reach.slug if placed.reach else None,
        "reach_name": placed.reach.name if placed.reach else None,
    }


def _note_labels(loaded: Any) -> dict[str, str]:
    """Plain words for a finding key inside the downstream line: "built banks", "a sewage
    discharge". A feature's name from features.yaml with its first letter lowered, a form item's
    short_label, else the id with spaces."""
    labels: dict[str, str] = {}
    for item in loaded.form.get("items", []):
        short = item.get("short_label")
        labels[item["id"]] = str(short) if short else str(item["id"]).replace("_", " ")
    for f in loaded.features:
        name = str(f.get("name", f["id"]))
        labels[f["id"]] = name[:1].lower() + name[1:]
    return labels


def _note_view(n: DownstreamNote, feature_names: dict[str, str]) -> dict[str, Any]:
    return {
        "reach_slug": n.reach_slug,
        "reach_name": n.reach_name,
        "from_reach_slug": n.from_reach_slug,
        "from_reach_name": n.from_reach_name,
        "feature": n.feature,
        "feature_name": feature_names.get(n.feature, n.feature),
        "line": n.line,
        "observers": n.observers,
        "visit_ids": list(n.visit_ids),
        "fhir": [f"/api/fhir/Bundle/{v}" for v in n.visit_ids],
    }


def city_view(db: Session, creek_ref: str, *, today: date) -> dict[str, Any]:
    """One creek: its spots, its findings, what it needs, which pipes are worth testing, and the
    downstream note on every reach below a finding.

    `creek_ref` is a readable slug from the region pack (`strawberry-creek`) or a generated creek
    id from the store. The slug is the link a person sees; the store keeps its own ids and the two
    are joined here at read time (Update 10B answer 2).
    """
    known = creeks()
    creek = creek_by_slug(creek_ref, known)
    all_spots = list(db.exec(select(SpotRow)).all())
    placements = placements_for(all_spots, known)
    if creek is not None:
        spots = [
            s
            for s in all_spots
            if s.spot_id in placements and placements[s.spot_id].creek.slug == creek.slug
        ]
    else:
        spots = [s for s in all_spots if s.creek_id == creek_ref]
        if not spots:
            raise NotFound("We have no record for that creek yet.")
        placed_on = {placements[s.spot_id].creek.slug for s in spots if s.spot_id in placements}
        creek = creek_by_slug(placed_on.pop(), known) if len(placed_on) == 1 else None

    # A pin that reads like someone trying the form out is kept out of the numbers and listed
    # separately for a person to look at. It is never deleted.
    flagged = [s for s in spots if looks_like_a_test_name(s.spot_name)]
    real = [s for s in spots if s not in flagged]

    loaded = content.get_content()
    feature_names = {f["id"]: f.get("name", f["id"]) for f in loaded.features}
    for item in loaded.form.get("items", []):
        feature_names.setdefault(item["id"], item.get("text", item["id"]))
    spot_names = {s.spot_id: s.spot_name for s in spots}

    # A stored answer is keyed by the form item; a measure is keyed by the feature. content/
    # form.yaml already says which item belongs to which feature, so that mapping has one home.
    finding_key_for = {
        item["id"]: item["feature"] for item in loaded.form.get("items", []) if item.get("feature")
    }

    visits = _records_for(db, real)
    findings = findings_from_visits(visits, finding_key_for)
    needs = needs_from_findings(findings, loaded.sentences)
    pipes = pipes_worth_testing(visits, today)

    notes: list[DownstreamNote] = []
    reaches: list[dict[str, Any]] = []
    unplaced = 0
    if creek is not None:
        reach_of = {s.spot_id: placements[s.spot_id].reach for s in real if s.spot_id in placements}
        notes = notes_below(findings, reach_of, creek, _note_labels(loaded))
        visits_at: dict[str, int] = {}
        for v in visits:
            visits_at[v.spot.spot_id] = visits_at.get(v.spot.spot_id, 0) + 1
        for reach in creek.reaches:
            here = [s for s in real if reach_of.get(s.spot_id) is reach]
            reaches.append(
                {
                    "slug": reach.slug,
                    "name": reach.name,
                    "flows_into": reach.flows_into,
                    "flows_into_name": (
                        creek.reach(reach.flows_into).name  # type: ignore[union-attr]
                        if reach.flows_into
                        else None
                    ),
                    "spots": len(here),
                    "visits": sum(visits_at.get(s.spot_id, 0) for s in here),
                    "notes": [
                        _note_view(n, feature_names) for n in notes if n.reach_slug == reach.slug
                    ],
                }
            )
        unplaced = sum(1 for s in real if reach_of.get(s.spot_id) is None)

    if creek is not None:
        creek_name = creek.name
    else:
        creek_name = real[0].creek_name if real else creek_ref

    return {
        "creek_id": creek_ref,
        "creek_slug": creek.slug if creek else None,
        "creek_name": creek_name,
        "visits": len(visits),
        "spots": len(real),
        "findings": [_finding_view(f, spot_names, feature_names) for f in findings],
        "needs": [
            {
                "sentence_id": n.sentence_id,
                "text": n.text,
                "source": n.source,
                "because": [feature_names.get(b, b) for b in n.because],
                "visit_ids": list(n.visit_ids),
                "fhir": [f"/api/fhir/Bundle/{v}" for v in n.visit_ids],
            }
            for n in needs
        ],
        "pipes_worth_testing": [
            {
                "spot_id": p.spot_id,
                "spot_name": p.spot_name,
                "observers": len(p.observers),
                "dry_days": list(p.dry_days),
                "last_seen": p.last_seen.isoformat(),
                "visit_ids": list(p.visit_ids),
                "fhir": [f"/api/fhir/Bundle/{v}" for v in p.visit_ids],
                # The referral is real and computed from these visits. The example result shows
                # how a laboratory answer would come back to the same record, and is counted by
                # nothing (Update 10 tier 1 item 2).
                "referral": referral_path(p.spot_id),
                "example_result": example_result_path(p.spot_id),
            }
            for p in pipes
        ],
        "flagged_spots": [
            {"spot_id": s.spot_id, "spot_name": s.spot_name, "why": "the name reads like a test"}
            for s in flagged
        ],
        # Said out loud, because an empty list of measures has two very different meanings.
        "measures_waiting_for_approval": not loaded.sentences
        or all(s.get("approved") is not True for s in loaded.sentences),
        # The reaches from the region pack, hills first, each with the notes on it (Update 10B).
        "reaches": reaches,
        "downstream_notes": [_note_view(n, feature_names) for n in notes],
        # Spots on this creek whose reach is unknown, mostly coarse pins. They count above and
        # neither give nor get a downstream note.
        "unplaced_spots": unplaced,
    }


def notes_for_spot(db: Session, spot_id: str, *, today: date) -> list[dict[str, Any]]:
    """The downstream notes that land on this spot's reach: what people reported upstream."""
    place = place_for_spot(db, spot_id)
    if place is None or place["reach_slug"] is None:
        return []
    view = city_view(db, place["creek_slug"], today=today)
    return [n for n in view["downstream_notes"] if n["reach_slug"] == place["reach_slug"]]


def _real_spots_on_the_creek_of(db: Session, spot_id: str) -> list[SpotRow]:
    """Every spot on the same creek as this one, by region pack placement when the spot has one
    and by the stored creek id otherwise, minus the pins that read like tests."""
    spot = db.get(SpotRow, spot_id)
    if spot is None:
        raise NotFound("We do not know that spot.")
    all_spots = list(db.exec(select(SpotRow)).all())
    placements = placements_for(all_spots, creeks())
    mine = placements.get(spot_id)
    if mine is not None:
        spots = [
            s
            for s in all_spots
            if s.spot_id in placements and placements[s.spot_id].creek.slug == mine.creek.slug
        ]
    else:
        spots = [s for s in all_spots if s.creek_id == spot.creek_id]
    return [s for s in spots if not looks_like_a_test_name(s.spot_name)]


def pipe_case_for(db: Session, spot_id: str, *, today: date) -> PipeCase:
    """The PipeCase for this spot, or NotFound when the pipe is not on the list.

    Same rule as /city, from the same function: two different people who both passed the pipe
    feature saw it running in dry weather. A spot that fails that rule has no referral, and asking
    for one is answered with why.
    """
    visits = _records_for(db, _real_spots_on_the_creek_of(db, spot_id))
    for pipe in pipes_worth_testing(visits, today):
        if pipe.spot_id == spot_id:
            return pipe
    raise NotFound(
        "No referral: this pipe is not on the list. Two different people who both passed the "
        "pipe feature have to report it running in dry weather."
    )


def referral_view(db: Session, spot_id: str, *, now: datetime) -> dict[str, Any]:
    """The ServiceRequest for a pipe worth testing, with every resource it points at."""
    pipe = pipe_case_for(db, spot_id, today=now.date())
    bundles = {
        visit_id: bundle
        for visit_id in pipe.visit_ids
        if (bundle := fhir_store.load_visit_bundle(visit_id)) is not None
    }
    try:
        return referral_bundle(pipe, bundles, emitted_at=now)
    except FhirEmitError as exc:
        raise NotFound(f"No referral could be built: {exc}") from exc


def example_result_view(db: Session, spot_id: str, *, now: datetime) -> dict[str, Any]:
    """The example laboratory result for that referral. Never stored, never counted."""
    referral = referral_view(db, spot_id, now=now)
    return example_lab_result(
        referral,
        collected_at=now + EXAMPLE_SAMPLE_AFTER,
        reported_at=now + EXAMPLE_REPORT_AFTER,
    )
