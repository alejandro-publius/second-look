"""The referral and the way back: golden files, the shape, and the checks broken on purpose."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from core.act import pipes_worth_testing
from core.fhir_emit import ORG_ID, SL_SYSTEM, FhirEmitError, emit_visit
from core.fhir_referral import (
    EXAMPLE_LAB_ROLE_ID,
    EXAMPLE_PANEL,
    EXAMPLE_WORD,
    OAH_SPECIMEN_PROFILE,
    check_example_bundle,
    check_referral_bundle,
    example_lab_result,
    is_example,
    pipe_observations,
    referral_bundle,
)
from core.records import CheckResult, FeatureScore, Observer, Spot, VisitRecord

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = ROOT / "fhir" / "golden"
GOLDEN_REFERRAL = GOLDEN_DIR / "referral-strawberry-creek-1.json"
GOLDEN_EXAMPLE = GOLDEN_DIR / "example-lab-result-strawberry-creek-1.json"

TODAY = date(2026, 9, 25)
EMITTED_AT = datetime(2026, 9, 24, 16, 41, tzinfo=UTC)
REFERRED_AT = datetime(2026, 9, 25, 9, 0, tzinfo=UTC)
COLLECTED_AT = datetime(2026, 9, 26, 10, 30, tzinfo=UTC)
REPORTED_AT = datetime(2026, 9, 29, 15, 0, tzinfo=UTC)

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


def observer(token: str, pipe_correct: int = 4) -> Observer:
    return Observer(
        contributor_token=token,
        scores=(
            FeatureScore(feature="pipe_running", correct=pipe_correct, tested_on=date(2026, 9, 23)),
        ),
    )


def visit(
    visit_id: str, token: str, *, day: int, dry_days: int, pipe_correct: int = 4
) -> VisitRecord:
    return VisitRecord(
        visit_id=visit_id,
        spot=SPOT,
        observer=observer(token, pipe_correct),
        answered_at=datetime(2026, 9, day, 12, 0, tzinfo=UTC),
        answers={"draining_pipes": "present", "water_flow": "slow"},
        checks=(
            CheckResult(
                rule_id="dry_pipe",
                asked=True,
                question_text="It has not rained. Is anything coming out of that pipe?",
                answer="yes",
                detail={"days": dry_days},
            ),
        ),
    )


def two_visits() -> list[VisitRecord]:
    return [
        visit("visit-0002", "alicetoken23456", day=22, dry_days=5),
        visit("visit-0003", "bobtoken23456789", day=23, dry_days=9),
    ]


def bundles_for(visits: list[VisitRecord]) -> dict[str, dict]:
    return {v.visit_id: emit_visit(v, test_sitting=None, emitted_at=EMITTED_AT) for v in visits}


def normalise(bundle: dict) -> str:
    return json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def resources(bundle: dict, resource_type: str) -> list[dict]:
    return [
        e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == resource_type
    ]


@pytest.fixture
def referral() -> dict:
    visits = two_visits()
    pipes = pipes_worth_testing(visits, TODAY)
    assert len(pipes) == 1
    return referral_bundle(pipes[0], bundles_for(visits), emitted_at=REFERRED_AT)


@pytest.fixture
def example(referral: dict) -> dict:
    return example_lab_result(referral, collected_at=COLLECTED_AT, reported_at=REPORTED_AT)


# Golden files, validated by the HL7 validator in make check.


def test_referral_matches_golden(referral: dict) -> None:
    text = normalise(referral)
    if os.environ.get("SL_UPDATE_GOLDEN") == "1":
        GOLDEN_REFERRAL.write_text(text, encoding="utf-8")
    assert GOLDEN_REFERRAL.exists(), "run with SL_UPDATE_GOLDEN=1 once to write the golden"
    assert text == GOLDEN_REFERRAL.read_text(encoding="utf-8")


def test_example_matches_golden(example: dict) -> None:
    text = normalise(example)
    if os.environ.get("SL_UPDATE_GOLDEN") == "1":
        GOLDEN_EXAMPLE.write_text(text, encoding="utf-8")
    assert GOLDEN_EXAMPLE.exists()
    assert text == GOLDEN_EXAMPLE.read_text(encoding="utf-8")


def test_goldens_pass_their_structural_checks() -> None:
    assert check_referral_bundle(json.loads(GOLDEN_REFERRAL.read_text(encoding="utf-8"))) == []
    assert check_example_bundle(json.loads(GOLDEN_EXAMPLE.read_text(encoding="utf-8"))) == []


def test_the_same_inputs_give_the_same_bundles(referral: dict, example: dict) -> None:
    visits = two_visits()
    again = referral_bundle(
        pipes_worth_testing(visits, TODAY)[0], bundles_for(visits), emitted_at=REFERRED_AT
    )
    assert again == referral
    assert example_lab_result(again, collected_at=COLLECTED_AT, reported_at=REPORTED_AT) == example


# The referral is real.


def test_service_request_points_at_the_pipe_and_at_both_people(referral: dict) -> None:
    (request,) = resources(referral, "ServiceRequest")
    assert request["status"] == "active" and request["intent"] == "proposal"
    assert request["subject"] == {"reference": "Location/sl-loc-spot-1"}
    assert request["requester"] == {"reference": f"Organization/{ORG_ID}"}
    assert request["code"]["coding"][0] == {
        "system": SL_SYSTEM,
        "code": "test-pipe-outflow",
        "display": "Test the water coming out of this pipe",
    }
    reasons = [r["reference"] for r in request["reasonReference"]]
    assert reasons == [
        "Observation/sl-obs-visit-0002-draining-pipes",
        "Observation/sl-obs-visit-0003-draining-pipes",
    ]
    performers = {
        o["performer"][0]["reference"]
        for o in resources(referral, "Observation")
        if f"Observation/{o['id']}" in reasons
    }
    assert len(performers) == 2, "two different people, not one person twice"
    assert "EXAMPLE" not in json.dumps(referral)
    assert not any(is_example(e["resource"]) for e in referral["entry"])


def test_referral_holds_only_what_it_needs(referral: dict) -> None:
    types = [e["resource"]["resourceType"] for e in referral["entry"]]
    assert types.count("ServiceRequest") == 1
    assert types.count("Location") == 3, "creek, reach and spot, so the subject resolves"
    assert types.count("Practitioner") == 2
    assert types.count("QuestionnaireResponse") == 2, (
        "the visit responses the Observations derive from"
    )
    assert "Provenance" not in types, "a Provenance would target Observations that are not here"
    assert types[-1] == "ServiceRequest"


def test_a_visit_missing_from_the_store_contributes_nothing() -> None:
    visits = two_visits()
    pipe = pipes_worth_testing(visits, TODAY)[0]
    bundles = bundles_for(visits)
    del bundles["visit-0003"]
    made = referral_bundle(pipe, bundles, emitted_at=REFERRED_AT)
    (request,) = resources(made, "ServiceRequest")
    assert [r["reference"] for r in request["reasonReference"]] == [
        "Observation/sl-obs-visit-0002-draining-pipes"
    ]
    with pytest.raises(FhirEmitError, match="no stored pipe Observation"):
        referral_bundle(pipe, {}, emitted_at=REFERRED_AT)


def test_pipe_observations_ignores_other_items_and_absent_pipes() -> None:
    quiet = VisitRecord(
        visit_id="visit-0009",
        spot=SPOT,
        observer=observer("caroltoken2345"),
        answered_at=datetime(2026, 9, 22, 12, 0, tzinfo=UTC),
        answers={"draining_pipes": "absent", "bank_type": "present"},
    )
    bundle = emit_visit(quiet, test_sitting=None, emitted_at=EMITTED_AT)
    assert len(resources(bundle, "Observation")) == 2
    assert pipe_observations(bundle) == []


# The way back is an example, and says so everywhere.


def test_every_laboratory_resource_is_tagged_and_says_example(example: dict) -> None:
    assert is_example(example), "the Bundle itself"
    lab = [
        e["resource"]
        for e in example["entry"]
        if e["resource"]["resourceType"] in {"Specimen", "PractitionerRole"}
        or e["resource"].get("id") == "sl-example-lab"
        or (e["resource"]["resourceType"] == "Observation" and "specimen" in e["resource"])
    ]
    assert len(lab) == 3 + len(EXAMPLE_PANEL)
    for r in lab:
        assert is_example(r), r["id"]
        assert r["text"]["div"].count(EXAMPLE_WORD) >= 1, r["id"]
    # The real part of the record is carried unchanged and untagged.
    real = [e["resource"] for e in example["entry"] if e["resource"] not in lab]
    assert real and not any(is_example(r) for r in real)


def test_the_result_returns_to_the_same_record(example: dict) -> None:
    (request,) = resources(example, "ServiceRequest")
    (specimen,) = resources(example, "Specimen")
    assert OAH_SPECIMEN_PROFILE in specimen["meta"]["profile"]
    assert specimen["subject"] == request["subject"]
    assert specimen["request"] == [{"reference": f"ServiceRequest/{request['id']}"}]
    assert specimen["collection"]["collector"] == {
        "reference": f"PractitionerRole/{EXAMPLE_LAB_ROLE_ID}"
    }
    assert specimen["type"]["coding"][0]["code"] == "11713004", "Water, from their value set"
    panel = [o for o in resources(example, "Observation") if "specimen" in o]
    assert [o["code"]["coding"][0]["code"] for o in panel] == [code for code, *_ in EXAMPLE_PANEL]
    for o in panel:
        assert o["basedOn"] == [{"reference": f"ServiceRequest/{request['id']}"}]
        assert o["specimen"] == {"reference": f"Specimen/{specimen['id']}"}
        assert o["subject"] == request["subject"]
        assert o["performer"] == [{"reference": f"PractitionerRole/{EXAMPLE_LAB_ROLE_ID}"}]
        assert o["category"][0]["coding"][0]["code"] == "laboratory"
    quantities = [o["valueQuantity"] for o in panel if "valueQuantity" in o]
    assert [q["code"] for q in quantities] == ["%", "[CFU]/dL"]
    coded = [
        o["valueCodeableConcept"]["coding"][0]["code"] for o in panel if "valueCodeableConcept" in o
    ]
    assert coded == ["absent"], "present and absent are their codes, reused"


# The checks, each broken on purpose.


def test_check_referral_rejects_an_example_tag_and_a_missing_reason(referral: dict) -> None:
    tagged = deepcopy(referral)
    tagged["entry"][-1]["resource"]["meta"] = {"tag": [{"system": SL_SYSTEM, "code": "example"}]}
    assert any("must not carry an example" in p for p in check_referral_bundle(tagged))

    dangling = deepcopy(referral)
    dangling["entry"][-1]["resource"]["reasonReference"].append(
        {"reference": "Observation/nowhere"}
    )
    assert any("does not resolve" in p for p in check_referral_bundle(dangling))

    absent = deepcopy(referral)
    for entry in absent["entry"]:
        r = entry["resource"]
        if r["resourceType"] == "Observation":
            r["valueCodeableConcept"]["coding"][0]["code"] = "absent"
    assert any("does not report a pipe present" in p for p in check_referral_bundle(absent))

    stranger = deepcopy(referral)
    stranger["entry"][-1]["resource"]["requester"] = {"reference": "Organization/sl-example-lab"}
    assert any("requester is not our Organization" in p for p in check_referral_bundle(stranger))


def test_check_example_rejects_an_untagged_or_unlabelled_result(example: dict) -> None:
    untagged = deepcopy(example)
    for entry in untagged["entry"]:
        if entry["resource"]["resourceType"] == "Specimen":
            del entry["resource"]["meta"]["tag"]
    assert any("without the example tag" in p for p in check_example_bundle(untagged))

    quiet = deepcopy(example)
    for entry in quiet["entry"]:
        r = entry["resource"]
        if r["resourceType"] == "Observation" and "specimen" in r:
            r["text"]["div"] = r["text"]["div"].replace(EXAMPLE_WORD, "Result")
    assert any(f"does not say {EXAMPLE_WORD}" in p for p in check_example_bundle(quiet))

    elsewhere = deepcopy(example)
    for entry in elsewhere["entry"]:
        r = entry["resource"]
        if r["resourceType"] == "Observation" and "specimen" in r:
            r["subject"] = {"reference": "Location/sl-loc-strawberry-creek"}
    assert any("not the same Location" in p for p in check_example_bundle(elsewhere))

    unbased = deepcopy(example)
    for entry in unbased["entry"]:
        r = entry["resource"]
        if r["resourceType"] == "Observation" and "specimen" in r:
            del r["basedOn"]
    assert any("not basedOn the ServiceRequest" in p for p in check_example_bundle(unbased))

    untagged_bundle = deepcopy(example)
    del untagged_bundle["meta"]
    assert any("Bundle itself" in p for p in check_example_bundle(untagged_bundle))
