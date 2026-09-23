"""The one place the API calls W5's core modules and W3's FHIR store.

Every function imports its target inside the body, so the API imports and serves while those
modules are still being written, and tests replace these names with fakes. When a module is
missing the fallback fails closed: no follow-up is asked, rain is unknown, no label, no health
card. The record builder has no fallback on purpose (hard rule 2): a visit is only finalized
through core.gate.build_record.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from core.records import CheckResult, FeatureScore, Observer, Spot, TestSitting, VisitRecord

log = logging.getLogger("apps.api")


@dataclass(frozen=True)
class RainView:
    status: str = "unknown"  # dry, wet or unknown
    mm_in_window: float | None = None
    dry_days: int | None = None
    source: str = "unknown"

    def as_dict(self) -> dict[str, str | float | int | None]:
        return {
            "status": self.status,
            "mm_in_window": self.mm_in_window,
            "dry_days": self.dry_days,
            "source": self.source,
        }


@dataclass(frozen=True)
class FollowupView:
    rule_id: str
    kind: str  # yesno, keep_rating, look_again or photo
    question_key: str
    params: dict[str, str | int | float] = field(default_factory=dict)


@dataclass(frozen=True)
class LabelView:
    text: str
    expired: bool
    passed: bool | None


class RecordBuilderMissing(RuntimeError):
    """core.gate is not installed, so no VisitRecord can be made."""


def rain_status(latitude: float | None, longitude: float | None, now: datetime) -> RainView:
    """core.rainfall.dry_status, or unknown when the module or the coordinates are missing."""
    if latitude is None or longitude is None:
        return RainView()
    try:
        from core.rainfall import dry_status
    except ImportError:
        return RainView()
    from apps.api.settings import settings

    try:
        status = dry_status(
            latitude,
            longitude,
            now,
            dry_mm=settings.rainfall_dry_mm,
            window_hours=settings.rainfall_window_hours,
        )
    except Exception as exc:  # any failure means unknown, so the dry pipe question is skipped
        log.warning("rainfall lookup failed: %s", type(exc).__name__)
        return RainView()
    return RainView(
        status=str(status.status),
        mm_in_window=status.mm_in_window,
        dry_days=status.dry_days,
        source=str(status.source),
    )


def select_followups(
    answers: Mapping[str, str | float | list[str]],
    rain: RainView,
    observer: Observer | None,
    *,
    table: Mapping[str, Any],
    form_items: Sequence[Mapping[str, Any]],
    checker_enabled: bool,
) -> list[FollowupView]:
    """core.followups.select_followups with no flags: the checker is wired by W6 through the
    gate, never here. Missing module means no follow-up is asked."""
    try:
        from core.followups import SiteContext
        from core.followups import select_followups as core_select
    except ImportError:
        return []
    site = SiteContext(
        rain=rain.status if rain.status in ("dry", "wet") else "unknown",  # type: ignore[arg-type]
        dry_days=rain.dry_days,
        mm_in_window=rain.mm_in_window,
    )
    chosen = core_select(
        answers,
        site,
        observer,
        [],
        table,
        form_items=form_items,
        checker_enabled=checker_enabled,
    )
    return [
        FollowupView(
            rule_id=str(f.rule_id),
            kind=str(f.kind),
            question_key=str(f.question_key),
            params=dict(f.params),
        )
        for f in chosen[: int(table.get("max_questions", 2))]
    ]


def observer_label(
    score: FeatureScore | None, feature_name: str, today: date, locale: Mapping[str, str]
) -> LabelView | None:
    """core.labels.observer_label. None when there is no score or no module."""
    if score is None:
        return None
    try:
        from core.labels import observer_label as core_label
    except ImportError:
        return None
    label = core_label(score, feature_name, today, locale)
    return LabelView(text=str(label.text), expired=bool(label.expired), passed=label.passed)


def pick_actions(sentences: Sequence[Mapping[str, Any]], seed: str) -> dict[str, Any] | None:
    """core.healthcard.pick_actions as a plain dict, or None."""
    try:
        from core.healthcard import pick_actions as core_pick
    except ImportError:
        return None
    card = core_pick(sentences, seed)
    if card is None:
        return None
    return {
        "person": card.person,
        "pet": card.pet,
        "city": card.city,
        "sources": list(card.sources),
    }


def build_record(
    *,
    visit_id: str,
    spot: Spot,
    observer: Observer,
    answered_at: datetime,
    answers: Mapping[str, str | float | list[str]],
    first_rating: str | None,
    final_rating: str | None,
    checks: Sequence[CheckResult],
    photo_ids: Sequence[str],
) -> VisitRecord:
    """core.gate.build_record. No fallback: without the gate there is no record."""
    try:
        from core.gate import build_record as core_build
    except ImportError as exc:
        raise RecordBuilderMissing("core.gate is not installed") from exc
    return core_build(
        visit_id=visit_id,
        spot=spot,
        observer=observer,
        answered_at=answered_at,
        answers=answers,
        first_rating=first_rating,
        final_rating=final_rating,
        checks=checks,
        photo_ids=photo_ids,
    )


def save_visit_bundle(visit: VisitRecord, test_sitting: TestSitting | None = None) -> Path | None:
    """apps.api.fhir_store.save_visit_bundle (W3). None when the store is not there yet or
    refuses the visit; the database row is the source of truth either way."""
    try:
        from apps.api.fhir_store import save_visit_bundle as store
    except ImportError:
        return None
    try:
        path = store(visit, test_sitting=test_sitting)
    except Exception as exc:
        log.warning("fhir store refused visit %s: %s", visit.visit_id, type(exc).__name__)
        return None
    _audit_record_written(visit, path)
    return path


def _audit_record_written(visit: VisitRecord, path: Path) -> None:
    """One hash chained audit line per stored record (Update 02 section 6). Never raises."""
    try:
        from apps.api.settings import settings
        from scripts.audit_log import append

        append(
            "record_written",
            {"visit_id": visit.visit_id, "spot_id": visit.spot.spot_id, "file": path.name},
            path=Path(settings.audit_log_path),
        )
    except Exception as exc:
        log.warning("audit append skipped for %s: %s", visit.visit_id, type(exc).__name__)
