"""Golden vectors: inputs and expected outputs the TypeScript ports must reproduce exactly.

  uv run python evals/golden_vectors.py            writes worker/golden/*.json
  uv run python evals/golden_vectors.py --check    exits 1 when a committed file is stale

Update 10 answer A3. Python stays the reference implementation; anything a judge touches live
runs on the Worker. So the Python code writes these vectors, worker/test/golden.test.ts runs the
TypeScript over the same inputs and compares, and CI fails when the two disagree. The HL7
validator then checks the TypeScript emitter's output too, because it does not care which
language wrote the JSON.

Every input is a plain JSON document. Records go through pydantic's JSON mode so dates and
datetimes are strings; the TypeScript side reads them back the same way the Worker would from
its database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from core import act, followups, healthcard, labels, regions, walks
from core.content_loader import load_content
from core.fhir_emit import check_bundle, emit_visit, fhir_id
from core.fhir_referral import example_lab_result, referral_bundle
from core.records import (
    FEATURES,
    CheckResult,
    FeatureScore,
    Observer,
    Spot,
    TestSitting,
    VisitRecord,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "worker" / "golden"
TODAY = date(2026, 9, 25)
EMITTED_AT = datetime(2026, 9, 24, 16, 41, tzinfo=UTC)


def dump(model: Any) -> Any:
    """A pydantic model, or a list or dict of them, as plain JSON data."""
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    if isinstance(model, list | tuple):
        return [dump(m) for m in model]
    if isinstance(model, dict):
        return {k: dump(v) for k, v in model.items()}
    return model


def case(name: str, inputs: dict[str, Any], expected: Any) -> dict[str, Any]:
    return {"name": name, "input": inputs, "expected": dump(expected)}


# Fixtures shared across vectors

SPOT = Spot(
    spot_id="spot-1",
    spot_name="Strawberry Creek, campus reach, spot 1",
    reach_id="campus-reach",
    reach_name="Strawberry Creek, campus reach",
    creek_id="strawberry-creek",
    creek_name="Strawberry Creek",
    latitude=37.8719,
    longitude=-122.2585,
    coarse=False,
)
COARSE_SPOT = Spot(
    spot_id="codornices-lower-2",
    spot_name="Codornices Creek, lower reach, spot 2",
    reach_id="codornices-lower",
    reach_name="Codornices Creek, lower reach",
    creek_id="codornices-creek",
    creek_name="Codornices Creek",
    latitude=37.88123,
    longitude=-122.29987,
    coarse=True,
)


def scores(*correct: int, tested_on: date = date(2026, 9, 23)) -> tuple[FeatureScore, ...]:
    return tuple(
        FeatureScore(feature=f, correct=c, tested_on=tested_on)
        for f, c in zip(FEATURES, correct, strict=True)
    )


def observer(token: str, *correct: int, tested_on: date = date(2026, 9, 23)) -> Observer:
    return Observer(contributor_token=token, scores=scores(*correct, tested_on=tested_on))


def visit(
    visit_id: str,
    token: str,
    *,
    spot: Spot = SPOT,
    day: int = 22,
    answers: dict[str, Any] | None = None,
    dry_days: int | None = None,
    dry_answer: str = "yes",
    correct: tuple[int, int, int, int] = (4, 4, 4, 4),
    tested_on: date = date(2026, 9, 23),
    first_rating: str | None = None,
    final_rating: str | None = None,
) -> VisitRecord:
    checks: tuple[CheckResult, ...] = ()
    if dry_days is not None:
        checks = (
            CheckResult(
                rule_id="dry_pipe",
                asked=True,
                question_text="It has not rained. Is anything coming out of that pipe?",
                answer=dry_answer,
                detail={"days": dry_days, "kind": "yesno"},
            ),
        )
    return VisitRecord(
        visit_id=visit_id,
        spot=spot,
        observer=observer(token, *correct, tested_on=tested_on),
        answered_at=datetime(2026, 9, day, 12, 0, tzinfo=UTC),
        answers=answers if answers is not None else {"draining_pipes": "present"},
        checks=checks,
        first_rating=first_rating,
        final_rating=final_rating,
    )


# Vectors


def followup_vectors(table: dict[str, Any], form_items: list[dict[str, Any]]) -> dict[str, Any]:
    def run(
        name: str, answers: dict[str, Any], site: followups.SiteContext, obs: Observer | None
    ) -> dict[str, Any]:
        chosen = followups.select_followups(
            answers, site, obs, [], table, form_items=form_items, checker_enabled=False
        )
        return case(
            name,
            {
                "answers": answers,
                "site": dump(site),
                "observer": dump(obs),
                "checker_enabled": False,
            },
            chosen,
        )

    dry = followups.SiteContext(rain="dry", dry_days=5, mm_in_window=0.0)
    wet = followups.SiteContext(rain="wet", dry_days=0, mm_in_window=7.2)
    unknown = followups.SiteContext(rain="unknown")
    zero = followups.SiteContext(rain="dry", dry_days=0, mm_in_window=0.0)
    good_with_issues = {
        "overall_rating": "good",
        "bank_type": "present",
        "draining_pipes": "present",
        "invasive_species": "absent",
        "sewage_discharge": "present",
    }
    weak = observer("weaktoken2345678", 2, 4, 1, 2)
    strong = observer("strongtoken23456", 4, 4, 4, 4)
    return {
        "function": "core.followups.select_followups",
        "cases": [
            run("dry pipe and rating check, in priority order", good_with_issues, dry, None),
            run("wet weather asks no dry pipe question", good_with_issues, wet, None),
            run("unknown rain fails closed", {"draining_pipes": "present"}, unknown, None),
            run("zero dry days reads as a guess", {"draining_pipes": "present"}, zero, None),
            run(
                "sewage discharge alone is a pipe item",
                {"sewage_discharge": "present", "overall_rating": "poor"},
                dry,
                None,
            ),
            run(
                "rating good with no issue asks nothing",
                {"overall_rating": "good", "bank_type": "absent"},
                wet,
                None,
            ),
            run(
                "low score photo for the weakest absent feature",
                {
                    "bank_type": "absent",
                    "invasive_species": "absent",
                    "draining_pipes": "absent",
                    "overall_rating": "moderate",
                },
                wet,
                weak,
            ),
            run(
                "a strong observer is not asked for a photo",
                {"bank_type": "absent", "invasive_species": "absent", "overall_rating": "moderate"},
                wet,
                strong,
            ),
            run("the cap is two: dry pipe and rating beat low score", good_with_issues, dry, weak),
            run("nothing at all", {}, unknown, None),
            run(
                "present answers do not ask for a photo",
                {"bank_type": "present", "invasive_species": "present"},
                wet,
                weak,
            ),
        ],
    }


def label_vectors(locale: dict[str, str]) -> dict[str, Any]:
    score = FeatureScore(feature="artificial_bank", correct=4, tested_on=date(2026, 9, 23))
    stale = FeatureScore(feature="pipe_running", correct=3, tested_on=date(2026, 6, 1))
    edge_ok = FeatureScore(feature="pipe_running", correct=3, tested_on=date(2026, 6, 27))
    edge_out = FeatureScore(feature="pipe_running", correct=3, tested_on=date(2026, 6, 26))
    low = FeatureScore(feature="dug_out_channel", correct=2, tested_on=date(2026, 9, 1))
    sub = {k: v for k, v in locale.items() if k.startswith("label.")}

    def run(name: str, s: FeatureScore | None, feature_name: str, today: date) -> dict[str, Any]:
        return case(
            name,
            {
                "score": dump(s),
                "feature_name": feature_name,
                "today": today.isoformat(),
                "locale": sub,
            },
            labels.observer_label(s, feature_name, today, locale),
        )

    return {
        "function": "core.labels.observer_label",
        "cases": [
            run("four of four, passed", score, "Built banks", TODAY),
            run("expired after ninety days", stale, "Pipes and sewage signs", TODAY),
            run("exactly ninety days still counts", edge_ok, "Pipes and sewage signs", TODAY),
            run("ninety one days is expired", edge_out, "Pipes and sewage signs", TODAY),
            run("two of four does not pass", low, "Dug-out channel", TODAY),
            run("no score, empty label", None, "Built banks", TODAY),
            run(
                "a december date",
                FeatureScore(feature="invasive_plant", correct=3, tested_on=date(2026, 12, 1)),
                "Plants that do not belong",
                date(2026, 12, 20),
            ),
        ],
    }


def healthcard_vectors(sentences: list[dict[str, Any]]) -> dict[str, Any]:
    source = "OneAquaHealth indicator factsheet"

    def s(
        sid: str, audience: str, text: str, approved: Any = True, src: Any = source
    ) -> dict[str, Any]:
        return {"id": sid, "audience": audience, "text": text, "source": src, "approved": approved}

    full = [
        s("p1", "person", "Wash your hands after touching the water."),
        s("p2", "person", "Keep out of the water after heavy rain.", src="Bay Area guidance"),
        s("pet1", "pet", "Keep dogs on a lead near outfalls."),
        s("c1", "city", "Replant the margins with native trees."),
        s("c2", "city", "Fix the sewer connections that run in dry weather."),
        s("c3", "city", "Reconnect the floodplain where the channel was dug out."),
    ]
    half = full + [
        s("c4", "city", "Not yet checked.", approved=False),
        s("p3", "person", "  ", approved=True),
    ]
    missing_pet = [x for x in full if x["audience"] != "pet"]
    cases = []
    for seed in ("spot-1", "spot-2", "codornices-lower-2", "a", "zz-top-9"):
        cases.append(
            case(
                f"seed {seed}",
                {"sentences": full, "seed": seed},
                healthcard.pick_actions(full, seed),
            )
        )
    cases.append(
        case(
            "unapproved and blank sentences are skipped",
            {"sentences": half, "seed": "spot-1"},
            healthcard.pick_actions(half, "spot-1"),
        )
    )
    cases.append(
        case(
            "no pet sentence, no card",
            {"sentences": missing_pet, "seed": "spot-1"},
            healthcard.pick_actions(missing_pet, "spot-1"),
        )
    )
    cases.append(
        case(
            "the repository's own list today",
            {"sentences": sentences, "seed": "spot-1"},
            healthcard.pick_actions(sentences, "spot-1"),
        )
    )
    return {"function": "core.healthcard.pick_actions", "cases": cases}


def act_vectors(
    finding_key_for: dict[str, str], sentences_approved: list[dict[str, Any]]
) -> dict[str, Any]:
    far = Spot(
        **{**SPOT.model_dump(), "spot_id": "spot-far", "latitude": 37.89, "longitude": -122.28}
    )
    near = Spot(
        **{
            **SPOT.model_dump(),
            "spot_id": "spot-near",
            "latitude": 37.87312,
            "longitude": -122.26041,
        }
    )
    nameless = Spot(
        **{**SPOT.model_dump(), "spot_id": "spot-none", "latitude": None, "longitude": None}
    )
    spots = [far, near, nameless, SPOT]

    def nearest(
        name: str, lat: float, lon: float, within: float = act.SAME_SPOT_METRES
    ) -> dict[str, Any]:
        found = act.nearest_spot(lat, lon, spots, within)
        expected = (
            None
            if found is None
            else {"spot_id": found.spot.spot_id, "metres": round(found.metres, 3)}
        )
        return case(
            name,
            {"latitude": lat, "longitude": lon, "spots": dump(spots), "within": within},
            expected,
        )

    visits_two = [
        visit("v1", "alicetoken23456", day=22, dry_days=5),
        visit("v2", "alicetoken23456", day=23, dry_days=6),
        visit("v3", "bobtoken23456789", day=23, dry_days=9),
    ]
    mixed = [
        visit(
            "v4",
            "alicetoken23456",
            answers={
                "bank_type": "present",
                "draining_pipes": "present",
                "barriers": "present",
                "invasive_species": "present",
            },
        ),
        visit(
            "v5",
            "caroltoken2345",
            answers={"bank_type": "present", "draining_pipes": "absent"},
            correct=(2, 4, 4, 2),
        ),
        visit(
            "v6",
            "davetoken234567",
            spot=COARSE_SPOT,
            answers={"bank_type": "present"},
            tested_on=date(2026, 5, 1),
        ),
    ]
    weak_pipes = [
        visit("v7", "alicetoken23456", dry_days=5, correct=(4, 4, 4, 2)),
        visit("v8", "bobtoken23456789", dry_days=5, correct=(4, 4, 4, 3)),
    ]
    no_answer = [
        visit("v9", "alicetoken23456", dry_days=5, dry_answer="no"),
        visit("v10", "bobtoken23456789", dry_days=5),
    ]
    expired = [
        visit("v11", "alicetoken23456", dry_days=5, tested_on=date(2026, 5, 1)),
        visit("v12", "bobtoken23456789", dry_days=5),
    ]
    approved = [s for s in sentences_approved]

    def findings(
        name: str, vs: list[VisitRecord], mapping: dict[str, str] | None
    ) -> dict[str, Any]:
        return case(
            name,
            {"visits": dump(vs), "finding_key_for": mapping},
            act.findings_from_visits(vs, mapping),
        )

    def pipes(name: str, vs: list[VisitRecord]) -> dict[str, Any]:
        return case(
            name,
            {"visits": dump(vs), "today": TODAY.isoformat()},
            act.pipes_worth_testing(vs, TODAY),
        )

    found_mixed = act.findings_from_visits(mixed, finding_key_for)

    # The downstream note (Update 10C): every reach below a finding gets one plain line.
    def reach(slug: str, flows_into: str | None) -> regions.Reach:
        return regions.Reach(
            slug=slug, name=slug.capitalize(), creek_slug="c", flows_into=flows_into
        )

    joined = regions.Creek(
        slug="c",
        name="Creek",
        reaches=(reach("top", "middle"), reach("middle", "bottom"), reach("bottom", None)),
    )
    apart = regions.Creek(
        slug="c",
        name="Creek",
        reaches=(reach("top", None), reach("middle", None), reach("bottom", None)),
    )
    elsewhere = regions.Reach(slug="x", name="X", creek_slug="elsewhere", flows_into=None)
    bay = regions.creeks_from_regions(load_content(ROOT, strict=True).regions)
    strawberry = regions.creek_by_slug("strawberry-creek", bay)
    assert strawberry is not None
    labels = {"pipe_running": "pipes and sewage signs", "artificial_bank": "built banks"}
    one_person = act.findings_from_visits([visit("v20", "alicetoken23456", day=5)], finding_key_for)
    two_people = act.findings_from_visits(
        [visit("v21", "alicetoken23456", day=22), visit("v22", "bobtoken23456789", day=23)],
        finding_key_for,
    )
    assert len(one_person) == 1 and len(two_people) == 1

    def creek_doc(c: regions.Creek) -> dict[str, Any]:
        return {
            "slug": c.slug,
            "name": c.name,
            "source": c.source,
            "reaches": [
                {
                    "slug": r.slug,
                    "name": r.name,
                    "flows_into": r.flows_into,
                    "bbox": list(r.bbox) if r.bbox else None,
                }
                for r in c.reaches
            ],
        }

    def notes(
        name: str,
        findings: list[act.Finding],
        reach_of: dict[str, regions.Reach | None],
        creek: regions.Creek,
        note_labels: dict[str, str],
    ) -> dict[str, Any]:
        return case(
            name,
            {
                "findings": dump(findings),
                "reach_of": {k: (r.slug if r is not None else None) for k, r in reach_of.items()},
                "creek": creek_doc(creek),
                "labels": note_labels,
            },
            act.notes_below(findings, reach_of, creek, note_labels),
        )

    notes_cases = [
        notes(
            "top of a joined creek: middle and bottom get the line",
            two_people,
            {SPOT.spot_id: joined.reach("top")},
            joined,
            labels,
        ),
        notes(
            "no flows_into anywhere: no line",
            two_people,
            {SPOT.spot_id: apart.reach("top")},
            apart,
            labels,
        ),
        notes(
            "the bottom reach has nothing below it",
            two_people,
            {SPOT.spot_id: joined.reach("bottom")},
            joined,
            labels,
        ),
        notes(
            "an unknown reach, a coarse pin: no line",
            two_people,
            {SPOT.spot_id: None},
            joined,
            labels,
        ),
        notes("a spot the map does not know: no line", two_people, {}, joined, labels),
        notes(
            "no label: the finding key with spaces",
            one_person,
            {SPOT.spot_id: joined.reach("top")},
            joined,
            {},
        ),
        notes(
            "strawberry creek, the south fork through the campus",
            found_mixed,
            {SPOT.spot_id: strawberry.reach("south-fork-campus"), COARSE_SPOT.spot_id: None},
            strawberry,
            labels,
        ),
    ]
    # The reach of another creek is not this creek's business; Reach carries its creek slug.
    notes_cases.append(
        case(
            "a reach of another creek: no line",
            {
                "findings": dump(two_people),
                "reach_of": {SPOT.spot_id: elsewhere.slug},
                "creek": creek_doc(joined),
                "labels": labels,
                "foreign_reach": dump(elsewhere),
            },
            act.notes_below(two_people, {SPOT.spot_id: elsewhere}, joined, labels),
        )
    )
    line_cases = [
        case(
            "one person, a single digit day",
            {
                "finding": dump(one_person[0]),
                "feature_name": "a pipe running",
                "reaches_below": ["middle", "bottom"],
            },
            act.downstream_note(one_person[0], "a pipe running", ["middle", "bottom"]),
        ),
        case(
            "two people",
            {
                "finding": dump(two_people[0]),
                "feature_name": "pipes and sewage signs",
                "reaches_below": ["west-culvert"],
            },
            act.downstream_note(two_people[0], "pipes and sewage signs", ["west-culvert"]),
        ),
        case(
            "no reach below: an empty map",
            {"finding": dump(two_people[0]), "feature_name": "built banks", "reaches_below": []},
            act.downstream_note(two_people[0], "built banks", []),
        ),
    ]
    return {
        "function": "core.act",
        "notes_below": notes_cases,
        "downstream_note": line_cases,
        "nearest_spot": [
            nearest("a few metres away", 37.8731, -122.2604),
            nearest("a kilometre away", 37.8719, -122.27),
            nearest("on the spot", 37.8719, -122.2585),
            nearest("wide net", 37.8719, -122.27, within=3000.0),
        ],
        "metres_between": [
            case(
                "campus to codornices",
                {"lat1": 37.8719, "lon1": -122.2585, "lat2": 37.88123, "lon2": -122.29987},
                round(act.metres_between(37.8719, -122.2585, 37.88123, -122.29987), 3),
            ),
            case(
                "same point",
                {"lat1": 37.8719, "lon1": -122.2585, "lat2": 37.8719, "lon2": -122.2585},
                0.0,
            ),
        ],
        "looks_like_a_test_name": [
            case(n, {"name": n}, act.looks_like_a_test_name(n))
            for n in (
                "test spot",
                "Strawberry Creek at the footbridge",
                "asdf",
                "123",
                "...",
                "",
                "Testing 1 2 3",
                "Codornices Creek",
                "DEMO",
                "Foo Bar Creek",
                "The Test Creek trail",
                "Rio Tinto",
            )
        ],
        "findings_from_visits": [
            findings("one person twice and another once", visits_two, finding_key_for),
            findings("without the form mapping a pipe item is not a finding key", visits_two, None),
            findings("form item keys map to features, coarse spot apart", mixed, finding_key_for),
            findings(
                "absent and cant tell are not findings",
                [
                    visit(
                        "v13",
                        "alicetoken23456",
                        answers={"draining_pipes": "absent", "bank_type": "cant_tell"},
                    )
                ],
                finding_key_for,
            ),
        ],
        "needs_from_findings": [
            case(
                "approved city sentences only",
                {"findings": dump(found_mixed), "sentences": approved},
                act.needs_from_findings(found_mixed, approved),
            ),
            case(
                "nothing approved",
                {
                    "findings": dump(found_mixed),
                    "sentences": [{**s, "approved": False} for s in approved],
                },
                act.needs_from_findings(found_mixed, [{**s, "approved": False} for s in approved]),
            ),
        ],
        "pipes_worth_testing": [
            pipes("two people who passed", visits_two),
            pipes("one did not pass", weak_pipes),
            pipes("one said nothing came out", no_answer),
            pipes("an expired score does not count", expired),
        ],
    }


def region_vectors(regions_raw: dict[str, Any]) -> dict[str, Any]:
    creeks = regions.creeks_from_regions(regions_raw)
    strawberry = regions.creek_by_slug("strawberry-creek", creeks)
    assert strawberry is not None

    def sp(lat: float | None, lon: float | None, coarse: bool, name: str = "A spot") -> Spot:
        return Spot(
            spot_id="s",
            spot_name=name,
            reach_id="r",
            reach_name=name,
            creek_id="c",
            creek_name=name,
            latitude=lat,
            longitude=lon,
            coarse=coarse,
        )

    def place(name: str, s: Spot) -> dict[str, Any]:
        p = regions.place_spot(s, creeks)
        expected = (
            None
            if p is None
            else {"creek_slug": p.creek.slug, "reach_slug": p.reach.slug if p.reach else None}
        )
        return case(name, {"spot": dump(s)}, expected)

    return {
        "function": "core.regions",
        "place_spot": [
            place("faculty glade, precise", sp(37.8716, -122.256, False)),
            place("same point coarse", sp(37.87, -122.26, True)),
            place("coarse but named reach", sp(37.87, -122.26, True, "Strawberry Creek Park")),
            place("north fork", sp(37.875, -122.26, False)),
            place("the park", sp(37.8666, -122.2885, False)),
            place("codornices", sp(37.89, -122.28, False, "Codornices Creek")),
            place(
                "no coordinates, named creek", sp(None, None, True, "Strawberry Creek footbridge")
            ),
            place("no coordinates, nothing", sp(None, None, True, "Somewhere")),
        ],
        "reaches_below": [
            case(
                r.slug,
                {"creek_slug": "strawberry-creek", "reach_slug": r.slug},
                [x.slug for x in regions.reaches_below(r, strawberry)],
            )
            for r in strawberry.reaches
        ],
    }


def fhir_vectors() -> dict[str, Any]:
    golden_visit = VisitRecord(
        visit_id="visit-0001",
        spot=SPOT,
        observer=Observer(
            contributor_token="ct_7f3a9c2e",
            scores=scores(4, 2, 3, 4),
            test_sitting_id="test-sitting-0001",
        ),
        answered_at=datetime(2026, 9, 24, 16, 40, tzinfo=UTC),
        answers={
            "bank_type": "present",
            "channel_form": "u_shape",
            "invasive_species": "present",
            "draining_pipes": "cant_tell",
            "water_height_m": 0.2,
            "overall_rating": "moderate",
        },
        first_rating="good",
        final_rating="moderate",
        software_version="0.1.0",
    )
    sitting = TestSitting(
        sitting_id="test-sitting-0001",
        contributor_token="ct_7f3a9c2e",
        completed_at=datetime(2026, 9, 23, 17, 5, tzinfo=UTC),
        scores=scores(4, 2, 3, 4),
    )
    second = VisitRecord(
        visit_id="7c1e2d3f-4a5b-4c6d-8e9f-0a1b2c3d4e5f",
        spot=COARSE_SPOT,
        observer=Observer(contributor_token="ct_0b1c2d3e4f5a"),
        answered_at=datetime(2026, 9, 26, 9, 15, 30, tzinfo=UTC),
        answers={
            "habitats": ["sand_banks", "riffles"],
            "natural_debris": [],
            "water_flow": "slow",
            "water_height_m": 0.35,
            "invasive_species": "cant_tell",
            "invasive_which": ["cant_tell"],
            "vegetation_type_left": "trees",
            "impervious_right": "present",
            "feelings": ["serenity"],
            "overall_rating": "good",
        },
    )
    long_id = VisitRecord(
        visit_id="visit-" + "x" * 70,
        spot=Spot(
            **{
                **SPOT.model_dump(),
                "spot_id": "spot with spaces & odd/chars",
                "spot_name": 'A <bridge> & a "quote"',
            }
        ),
        observer=observer("longtoken2345678", 4, 3, 2, 1, tested_on=date(2026, 9, 1)),
        answered_at=datetime(2026, 9, 27, 8, 0, 0, 500000, tzinfo=UTC),
        answers={"bank_type": "present", "water_height_m": 1.0, "draining_pipes": "present"},
        checks=(
            CheckResult(
                rule_id="dry_pipe", asked=True, question_text="q", answer="yes", detail={"days": 3}
            ),
        ),
        photo_ids=("up-1", "up-2"),
        software_version="0.2.0",
    )

    def run(name: str, v: VisitRecord, ts: TestSitting | None, at: datetime) -> dict[str, Any]:
        bundle = emit_visit(v, test_sitting=ts, emitted_at=at)
        assert check_bundle(bundle) == []
        return case(
            name,
            {
                "visit": dump(v),
                "test_sitting": dump(ts),
                "emitted_at": at.isoformat().replace("+00:00", "Z"),
            },
            bundle,
        )

    # The referral and the way back, from two people who passed and saw the pipe running.
    pipe_visits = [
        visit("visit-0002", "alicetoken23456", day=22, dry_days=5),
        visit("visit-0003", "bobtoken23456789", day=23, dry_days=9),
    ]
    pipe = act.pipes_worth_testing(pipe_visits, TODAY)[0]
    stored = {
        v.visit_id: emit_visit(v, test_sitting=None, emitted_at=EMITTED_AT) for v in pipe_visits
    }
    referred_at = datetime(2026, 9, 25, 9, 0, tzinfo=UTC)
    referral = referral_bundle(pipe, stored, emitted_at=referred_at)
    example = example_lab_result(
        referral,
        collected_at=datetime(2026, 9, 26, 10, 30, tzinfo=UTC),
        reported_at=datetime(2026, 9, 29, 15, 0, tzinfo=UTC),
    )
    referral_cases = [
        case(
            "referral for the pipe two people who passed saw running",
            {"pipe": dump(pipe), "bundles": stored, "emitted_at": "2026-09-25T09:00:00Z"},
            referral,
        ),
        case(
            "the example result pointing back at that referral",
            {
                "referral": referral,
                "collected_at": "2026-09-26T10:30:00Z",
                "reported_at": "2026-09-29T15:00:00Z",
            },
            example,
        ),
    ]
    return {
        "function": "core.fhir_emit.emit_visit",
        "referral": referral_cases,
        "cases": [
            run(
                "the golden strawberry creek visit with its sitting",
                golden_visit,
                sitting,
                EMITTED_AT,
            ),
            run(
                "a coarse pin, lists, a number, no sitting",
                second,
                None,
                datetime(2026, 9, 26, 9, 16, tzinfo=UTC),
            ),
            run(
                "long id, odd characters, whole number, checks and photos",
                long_id,
                None,
                datetime(2026, 9, 27, 8, 1, tzinfo=UTC),
            ),
        ],
    }


def walk_vectors() -> dict[str, Any]:
    """Update 14 3.7: a walk visit, built on the device, tagged as a demo on every resource."""
    walk = {"id": "v03", "spot_name": "The stretch in the clip", "creek_name": "A creek in a clip"}

    def run(name: str, answers: dict[str, Any], at: datetime) -> dict[str, Any]:
        bundle = walks.walk_bundle(walk, answers, at)
        assert check_bundle(bundle) == [] and walks.is_demo(bundle)
        return case(
            name,
            {
                "walk": walk,
                "answers": answers,
                "answered_at": at.isoformat().replace("+00:00", "Z"),
            },
            bundle,
        )

    return {
        "function": "core.walks.walk_bundle",
        "cases": [
            run(
                "a walk with a built bank, a pipe and a number",
                {"bank_type": "present", "draining_pipes": "present", "water_height_m": 1.0},
                datetime(2026, 9, 24, 16, 5, 9, tzinfo=UTC),
            ),
            run(
                "a walk where the person saw nothing and skipped the rest",
                {"bank_type": "absent"},
                datetime(2026, 9, 25, 8, 0, 0, 750000, tzinfo=UTC),
            ),
        ],
    }


def helper_vectors() -> dict[str, Any]:
    texts = [
        "",
        "a",
        "ct_7f3a9c2e",
        "alicetoken23456",
        "spot-1:city",
        "The quick brown fox jumps over the lazy dog",
        "é ü 日本",
    ]
    rounds = [
        (0.125, 2),
        (37.875, 2),
        (2.675, 2),
        (0.015625, 5),
        (1.005, 2),
        (37.87312, 2),
        (-122.26041, 2),
        (37.87312, 5),
        (-122.26041, 6),
        (0.3, 6),
        (37.8719, 5),
        (1.0, 2),
        (2.5, 0),
        (3.5, 0),
        (-0.125, 2),
    ]
    return {
        "function": "helpers",
        "sha256": [
            case(t, {"text": t}, hashlib.sha256(t.encode("utf-8")).hexdigest()) for t in texts
        ],
        "round": [case(f"{x} to {n}", {"value": x, "digits": n}, round(x, n)) for x, n in rounds],
        "fhir_id": [
            case(name, {"parts": parts}, fhir_id(*parts))
            for name, parts in (
                ("plain", ["sl-loc", "spot-1"]),
                ("spaces and symbols", ["sl-obs", "visit 1", "bank type"]),
                ("long, hashed tail", ["sl-visit", "visit-" + "x" * 70]),
                ("leading and trailing junk", ["--sl", "spot--"]),
            )
        ],
    }


def build() -> dict[str, dict[str, Any]]:
    content = load_content(ROOT, strict=True)
    form_items = list(content.form.get("items", []))
    finding_key_for = {i["id"]: i["feature"] for i in form_items if i.get("feature")}
    approved = [
        {
            "id": "city_fix_sewers",
            "audience": "city",
            "text": "Find and fix leaking sewers.",
            "source": "Policy Brief page 9",
            "approved": True,
        },
        {
            "id": "city_replant_margins",
            "audience": "city",
            "text": "Replant both margins.",
            "source": "Policy Brief page 9",
            "approved": True,
        },
        {
            "id": "city_remove_barriers",
            "audience": "city",
            "text": "Remove barriers.",
            "source": "Policy Brief page 9",
            "approved": False,
        },
        {
            "id": "person_wash",
            "audience": "person",
            "text": "Wash your hands.",
            "source": "Factsheet",
            "approved": True,
        },
    ]
    return {
        "followups": followup_vectors(content.followups, form_items),
        "labels": label_vectors(content.locale),
        "healthcard": healthcard_vectors(list(content.sentences)),
        "act": act_vectors(finding_key_for, approved),
        "regions": region_vectors(content.regions),
        "fhir_emit": fhir_vectors(),
        "walks": walk_vectors(),
        "helpers": helper_vectors(),
    }


def render(doc: dict[str, Any]) -> str:
    return (
        json.dumps(
            {"generated_by": "evals/golden_vectors.py", **doc},
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--check", action="store_true", help="fail if a committed vector file is stale"
    )
    args = parser.parse_args(argv)
    docs = build()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stale: list[str] = []
    for name, doc in docs.items():
        path = OUT_DIR / f"{name}.json"
        text = render(doc)
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path.name)
        else:
            path.write_text(text, encoding="utf-8")
    if args.check:
        if stale:
            print(f"golden-vectors: stale: {', '.join(stale)}. Run evals/golden_vectors.py.")
            return 1
        print(f"golden-vectors: {len(docs)} files current")
        return 0
    counts = sum(len(v) for doc in docs.values() for k, v in doc.items() if isinstance(v, list))
    print(f"golden-vectors: {len(docs)} files, {counts} cases into {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
