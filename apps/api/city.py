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
    Finding,
    PipeCase,
    findings_from_visits,
    looks_like_a_test_name,
    needs_from_findings,
    pipes_worth_testing,
)
from core.fhir_emit import FhirEmitError
from core.fhir_referral import example_lab_result, referral_bundle
from core.records import CheckResult, Observer, VisitRecord

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


def city_view(db: Session, creek_id: str, *, today: date) -> dict[str, Any]:
    """One creek: its spots, its findings, what it needs and which pipes are worth testing."""
    spots = list(db.exec(select(SpotRow).where(SpotRow.creek_id == creek_id)).all())
    if not spots:
        raise NotFound("We have no record for that creek yet.")

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

    return {
        "creek_id": creek_id,
        "creek_name": real[0].creek_name if real else creek_id,
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
    }


def _real_spots_on_the_creek_of(db: Session, spot_id: str) -> list[SpotRow]:
    spot = db.get(SpotRow, spot_id)
    if spot is None:
        raise NotFound("We do not know that spot.")
    spots = list(db.exec(select(SpotRow).where(SpotRow.creek_id == spot.creek_id)).all())
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
