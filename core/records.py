"""Shared data model for a volunteer, a spot and a visit. Pure data, no I/O.

Owned by the integrator. Every workstream imports from here instead of redefining shapes.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FeatureId = Literal["artificial_bank", "dug_out_channel", "invasive_plant", "pipe_running"]
FEATURES: tuple[FeatureId, ...] = (
    "artificial_bank",
    "dug_out_channel",
    "invasive_plant",
    "pipe_running",
)

AnswerValue = Literal["present", "absent", "cant_tell"]
TestAnswer = Literal["yes", "no", "cant_tell"]
Arm = Literal["untrained", "trained"]
GoldLabel = Literal["present", "absent"]

SCORE_VALID_DAYS = 90
ITEMS_PER_FEATURE = 4


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FeatureScore(Frozen):
    """Raw 'k of 4' for one feature from one test sitting."""

    feature: FeatureId
    correct: int = Field(ge=0, le=ITEMS_PER_FEATURE)
    total: int = ITEMS_PER_FEATURE
    tested_on: date

    def expired_on(self, today: date) -> bool:
        return (today - self.tested_on).days > SCORE_VALID_DAYS


class Observer(Frozen):
    """A volunteer, known only by a random contributor token."""

    contributor_token: str = Field(min_length=8, max_length=64)
    scores: tuple[FeatureScore, ...] = ()
    test_sitting_id: str | None = None

    def score_for(self, feature: FeatureId) -> FeatureScore | None:
        for s in self.scores:
            if s.feature == feature:
                return s
        return None


class Spot(Frozen):
    """A point on a reach of a creek. Three nested Locations in FHIR."""

    spot_id: str
    spot_name: str
    reach_id: str
    reach_name: str
    creek_id: str
    creek_name: str
    latitude: float | None = None
    longitude: float | None = None
    coarse: bool = True


class CheckResult(Frozen):
    """One follow-up rule that ran during a visit."""

    rule_id: str
    asked: bool
    question_text: str | None = None
    answer: str | None = None
    detail: dict[str, str | float | int | None] = Field(default_factory=dict)


class VisitRecord(Frozen):
    """Everything a guided check stores. Answers are the human's, never a model's."""

    visit_id: str
    spot: Spot
    observer: Observer
    answered_at: datetime
    answers: dict[str, str | float | list[str]]
    first_rating: str | None = None
    final_rating: str | None = None
    checks: tuple[CheckResult, ...] = ()
    photo_ids: tuple[str, ...] = ()
    software_version: str = "0.1.0"


class TestSitting(Frozen):
    """A completed observer test, scored by code from the gold key."""

    sitting_id: str
    contributor_token: str | None
    completed_at: datetime
    scores: tuple[FeatureScore, ...]
