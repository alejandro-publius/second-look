"""The analyst's view of a creek: what it needs, and which pipes are worth testing.

All the judgement lives in core/act.py, which is pure and tested. This module only reads rows
and hands them over, so the rule that every number carries its evidence is kept in one place.

Nothing here decides anything a person did not report. A measure is approved text or it is
absent. A pipe reaches the list only when two different people who both passed that feature saw
it running in dry weather.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from sqlmodel import Session, select

from apps.api import content
from apps.api.check import NotFound, observer_from_token, spot_from_row
from apps.api.db import as_utc
from apps.api.models import CheckResultRow, ObserverRow, SpotRow, VisitRow
from core.act import (
    Finding,
    findings_from_visits,
    looks_like_a_test_name,
    needs_from_findings,
    pipes_worth_testing,
)
from core.records import CheckResult, Observer, VisitRecord


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
