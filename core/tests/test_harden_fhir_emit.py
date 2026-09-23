"""The emitter's edge cases: unknown answers, conditional create keys, each check_bundle problem."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.fhir_emit import (
    FHIR_BASE,
    OAH_DISPLAYS,
    OAH_SYSTEM,
    REPO_URL,
    SL_DISPLAYS,
    SL_SYSTEM,
    FhirEmitError,
    _if_none_exist,
    _qr_answers,
    check_bundle,
    code_for_answer,
    emit_visit,
    to_transaction,
)
from core.records import FeatureScore, Observer, Spot, VisitRecord
from core.records import TestSitting as _TestSitting

TESTED_ON = date(2026, 9, 23)
ANSWERED_AT = datetime(2026, 9, 24, 16, 40, tzinfo=UTC)
EMITTED_AT = datetime(2026, 9, 24, 16, 41, tzinfo=UTC)
TAG_CODE = "second-look"
OBS_ID_SYSTEM = f"{FHIR_BASE}/observation"

Answers = dict[str, str | float | list[str]]

# Three mapped answers of three kinds: a coded choice, a multi-select and a number.
MAPPED_ANSWERS: Answers = {
    "bank_type": "present",
    "habitats": ["sand_banks", "riffles"],
    "water_height_m": 0.2,
}


def a_spot() -> Spot:
    return Spot(
        spot_id="spot-harden-1",
        spot_name="Harden Creek, test reach, spot 1",
        reach_id="reach-harden-1",
        reach_name="Harden Creek, test reach",
        creek_id="creek-harden",
        creek_name="Harden Creek",
        latitude=37.87191,
        longitude=-122.25853,
        coarse=False,
    )


def a_visit(answers: Answers) -> VisitRecord:
    return VisitRecord(
        visit_id="visit-harden-1",
        spot=a_spot(),
        observer=Observer(contributor_token="ct_harden_0001"),
        answered_at=ANSWERED_AT,
        answers=answers,
    )


def a_sitting(scores: tuple[FeatureScore, ...]) -> _TestSitting:
    return _TestSitting(
        sitting_id="sitting-harden-1",
        contributor_token="ct_harden_0001",
        completed_at=datetime(2026, 9, 23, 17, 5, tzinfo=UTC),
        scores=scores,
    )


def emitted(answers: Answers) -> dict[str, Any]:
    return emit_visit(a_visit(answers), test_sitting=None, emitted_at=EMITTED_AT)


def resources(bundle: dict[str, Any], resource_type: str) -> list[dict[str, Any]]:
    return [
        e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == resource_type
    ]


def index_of(bundle: dict[str, Any], resource_type: str, nth: int = 0) -> int:
    found = [
        i for i, e in enumerate(bundle["entry"]) if e["resource"]["resourceType"] == resource_type
    ]
    return found[nth]


def broken_copy(bundle: dict[str, Any]) -> dict[str, Any]:
    copied: dict[str, Any] = json.loads(json.dumps(bundle))
    return copied


def observation_answer(bundle: dict[str, Any], text: str) -> dict[str, Any]:
    return next(o for o in resources(bundle, "Observation") if o["code"].get("text") == text)


def visit_response_answers(bundle: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    (visit_qr,) = resources(bundle, "QuestionnaireResponse")
    return {item["linkId"]: item["answer"] for item in visit_qr["item"]}


@pytest.fixture
def good_bundle() -> dict[str, Any]:
    bundle = emitted(MAPPED_ANSWERS)
    assert check_bundle(bundle) == []
    return bundle


# code_for_answer: which answer values get a code


@pytest.mark.parametrize("value", ["serenity", "arundo_donax", "", "Present", "cant tell"])
def test_a_value_with_no_code_gets_none(value: str) -> None:
    assert code_for_answer(value) is None


@pytest.mark.parametrize("code", sorted(SL_DISPLAYS))
def test_every_second_look_code_is_found_from_its_underscore_spelling(code: str) -> None:
    coding = code_for_answer(code.replace("-", "_"))
    assert coding == {"system": SL_SYSTEM, "code": code, "display": SL_DISPLAYS[code]}


@settings(max_examples=300, deadline=None)
@given(
    st.one_of(
        st.sampled_from(sorted(OAH_DISPLAYS) + [c.replace("-", "_") for c in SL_DISPLAYS]),
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz_-ABC ", max_size=24),
    )
)
def test_a_code_is_always_one_of_ours_or_theirs_with_its_own_display(value: str) -> None:
    coding = code_for_answer(value)
    if coding is None:
        assert value not in OAH_DISPLAYS
        assert value.replace("_", "-") not in SL_DISPLAYS
        return
    if coding["system"] == OAH_SYSTEM:
        assert coding == {"system": OAH_SYSTEM, "code": value, "display": OAH_DISPLAYS[value]}
    else:
        assert coding["system"] == SL_SYSTEM
        assert coding["code"] == value.replace("_", "-")
        assert coding["display"] == SL_DISPLAYS[coding["code"]]


# Unknown answer values travel as plain text, never as a made up code


def test_a_choice_with_no_code_is_stored_as_text() -> None:
    bundle = emitted({"water_flow": "roaring"})
    assert check_bundle(bundle) == []
    flow = observation_answer(bundle, "Water flow")
    assert flow["valueCodeableConcept"] == {"text": "roaring"}
    assert "coding" not in flow["valueCodeableConcept"]
    assert flow["code"]["coding"][0]["code"] == "hydrology"
    assert "Water flow at Harden Creek, test reach, spot 1: roaring." in flow["text"]["div"]
    assert visit_response_answers(bundle)["water_flow"] == [{"valueString": "roaring"}]


def test_a_multi_select_value_with_no_code_is_named_by_the_item_code_and_text() -> None:
    bundle = emitted({"habitats": ["sand_banks", "beaver_dam"]})
    assert check_bundle(bundle) == []
    habitats = observation_answer(bundle, "Habitats")
    known, unknown = habitats["component"]
    assert known["code"]["coding"] == [
        {"system": SL_SYSTEM, "code": "sand-banks", "display": "Sand banks"}
    ]
    assert unknown["code"] == {
        "coding": [
            {"system": OAH_SYSTEM, "code": "morophology", "display": OAH_DISPLAYS["morophology"]}
        ],
        "text": "beaver_dam",
    }
    for component in (known, unknown):
        assert component["valueCodeableConcept"]["coding"][0]["code"] == "present"
    assert visit_response_answers(bundle)["habitats"] == [
        {"valueCoding": {"system": SL_SYSTEM, "code": "sand-banks", "display": "Sand banks"}},
        {"valueString": "beaver_dam"},
    ]


def test_a_region_plant_with_no_code_is_a_text_value_on_the_invasive_plant_code() -> None:
    bundle = emitted({"invasive_which": ["arundo_donax"]})
    assert check_bundle(bundle) == []
    (plant,) = observation_answer(bundle, "Which ones?")["component"]
    assert plant["code"]["coding"][0] == {
        "system": SL_SYSTEM,
        "code": "invasive-plant",
        "display": "Invasive plant",
    }
    assert plant["valueCodeableConcept"] == {"text": "arundo_donax"}


def test_an_item_with_an_unknown_code_system_is_refused() -> None:
    items = [
        {
            "id": "odd_item",
            "type": "yesno",
            "text": "Odd",
            "fhir": {"code_system": "snomed", "code": "hydrology"},
        }
    ]
    visit = a_visit({"odd_item": "present"})
    with pytest.raises(FhirEmitError, match=r"^item odd_item: unknown code_system 'snomed'$"):
        emit_visit(visit, test_sitting=None, emitted_at=EMITTED_AT, items=items)


# The test sitting response lists only the features that were scored


def test_a_partial_test_sitting_lists_only_its_features_in_the_fixed_order() -> None:
    scores = (
        FeatureScore(feature="pipe_running", correct=1, tested_on=TESTED_ON),
        FeatureScore(feature="artificial_bank", correct=4, tested_on=TESTED_ON),
    )
    bundle = emit_visit(
        a_visit({"bank_type": "present", "invasive_species": "absent"}),
        test_sitting=a_sitting(scores),
        emitted_at=EMITTED_AT,
    )
    assert check_bundle(bundle) == []
    test_qr, _ = resources(bundle, "QuestionnaireResponse")
    assert [item["linkId"] for item in test_qr["item"]] == ["artificial_bank", "pipe_running"]
    assert [item["item"][0]["answer"] for item in test_qr["item"]] == [
        [{"valueInteger": 4}],
        [{"valueInteger": 1}],
    ]
    assert "scored by code: artificial bank 4 of 4, pipe running 1 of 4." in test_qr["text"]["div"]
    bank = observation_answer(bundle, "Bank type")
    assert "The observer scored 4 of 4 on this feature" in bank["text"]["div"]
    invasive = next(
        o
        for o in resources(bundle, "Observation")
        if o["code"]["coding"][0]["code"] == "invasive-plant"
    )
    assert "scored" not in invasive["text"]["div"], "no score for this feature, no score words"


# _qr_answers: the answer shapes in the visit response


def test_a_boolean_answer_is_a_boolean_not_the_number_one() -> None:
    assert _qr_answers(True) == [{"valueBoolean": True}]
    assert _qr_answers(False) == [{"valueBoolean": False}]
    assert _qr_answers(1) == [{"valueDecimal": 1}]
    assert _qr_answers(0.35) == [{"valueDecimal": 0.35}]


def test_a_list_answer_keeps_each_value_in_order_and_an_empty_list_gives_nothing() -> None:
    assert _qr_answers([]) == []
    assert _qr_answers(["cant_tell", "serenity"]) == [
        {"valueCoding": {"system": SL_SYSTEM, "code": "cant-tell", "display": "Can't tell"}},
        {"valueString": "serenity"},
    ]


# Conditional creates: every resource needs a key, or the transaction is refused


def test_a_resource_without_an_identifier_cannot_become_a_conditional_create(
    good_bundle: dict[str, Any],
) -> None:
    broken = broken_copy(good_bundle)
    del resources(broken, "Organization")[0]["identifier"]
    with pytest.raises(
        FhirEmitError, match=r"^Organization/sl-org: no identifier for a conditional create$"
    ):
        to_transaction(broken, tag_system=REPO_URL, tag_code=TAG_CODE)


def test_an_empty_identifier_list_counts_as_no_identifier(good_bundle: dict[str, Any]) -> None:
    broken = broken_copy(good_bundle)
    resources(broken, "Device")[0]["identifier"] = []
    with pytest.raises(FhirEmitError, match=r"^Device/sl-device: no identifier"):
        to_transaction(broken, tag_system=REPO_URL, tag_code=TAG_CODE)


def test_a_provenance_whose_targets_are_not_in_the_bundle_is_refused(
    good_bundle: dict[str, Any],
) -> None:
    broken = broken_copy(good_bundle)
    resources(broken, "Provenance")[0]["target"] = [{"reference": "Observation/nowhere"}]
    with pytest.raises(
        FhirEmitError,
        match=r"^Provenance/sl-provenance-visit-harden-1: no identifier for a conditional create$",
    ):
        to_transaction(broken, tag_system=REPO_URL, tag_code=TAG_CODE)


def test_the_provenance_key_is_the_first_target_that_has_an_identifier() -> None:
    by_key: dict[str, dict[str, Any]] = {
        "Observation/no-ident": {"resourceType": "Observation", "id": "no-ident"},
        "Observation/half-ident": {
            "resourceType": "Observation",
            "id": "half-ident",
            "identifier": [{"system": OBS_ID_SYSTEM}],
        },
        "Observation/b": {
            "resourceType": "Observation",
            "id": "b",
            "identifier": [{"system": OBS_ID_SYSTEM, "value": "visit-1-b"}],
        },
        "Observation/c": {
            "resourceType": "Observation",
            "id": "c",
            "identifier": [{"system": OBS_ID_SYSTEM, "value": "visit-1-c"}],
        },
    }
    provenance = {
        "resourceType": "Provenance",
        "id": "p",
        "target": [
            {"reference": "Observation/missing"},
            {},
            {"reference": "Observation/no-ident"},
            {"reference": "Observation/half-ident"},
            {"reference": "Observation/b"},
            {"reference": "Observation/c"},
        ],
    }
    assert _if_none_exist(provenance, by_key) == (
        f"Provenance?target:Observation.identifier={OBS_ID_SYSTEM}|visit-1-b"
    )


def test_a_provenance_with_no_target_key_is_refused() -> None:
    with pytest.raises(FhirEmitError, match=r"^Provenance/p: no identifier"):
        _if_none_exist({"resourceType": "Provenance", "id": "p"}, {})


def test_a_single_identifier_object_is_used_as_the_key() -> None:
    response = {
        "resourceType": "QuestionnaireResponse",
        "id": "qr",
        "identifier": {"system": f"{FHIR_BASE}/qr", "value": "visit-1"},
    }
    assert _if_none_exist(response, {}) == (
        f"QuestionnaireResponse?identifier={FHIR_BASE}/qr|visit-1"
    )


def test_only_a_provenance_may_borrow_a_key_from_its_target() -> None:
    observation = {
        "resourceType": "Observation",
        "id": "o",
        "identifier": [{"system": OBS_ID_SYSTEM, "value": "visit-1-o"}],
    }
    not_provenance = {
        "resourceType": "Practitioner",
        "id": "pr",
        "target": [{"reference": "Observation/o"}],
    }
    with pytest.raises(FhirEmitError, match=r"^Practitioner/pr: no identifier"):
        _if_none_exist(not_provenance, {"Observation/o": observation})


# check_bundle names every structural problem


@pytest.mark.parametrize(
    "not_a_bundle",
    [{}, {"resourceType": "Patient"}, {"resourceType": "bundle", "entry": []}],
)
def test_anything_that_is_not_a_bundle_is_refused_at_once(not_a_bundle: dict[str, Any]) -> None:
    assert check_bundle(not_a_bundle) == ["not a Bundle"]


@pytest.mark.parametrize("field", ["subject", "performer", "effectiveDateTime"])
def test_an_observation_missing_a_required_field_is_named(
    good_bundle: dict[str, Any], field: str
) -> None:
    broken = broken_copy(good_bundle)
    i = index_of(broken, "Observation")
    obs = broken["entry"][i]["resource"]
    del obs[field]
    assert check_bundle(broken) == [f"entry[{i}] Observation/{obs['id']}: missing {field}"]


@pytest.mark.parametrize("break_meta", ["empty profile", "no meta"])
def test_an_observation_without_the_indicator_profile_is_named(
    good_bundle: dict[str, Any], break_meta: str
) -> None:
    broken = broken_copy(good_bundle)
    i = index_of(broken, "Observation", 1)
    obs = broken["entry"][i]["resource"]
    if break_meta == "no meta":
        del obs["meta"]
    else:
        obs["meta"]["profile"] = ["http://example.org/some-other-profile"]
    assert check_bundle(broken) == [
        f"entry[{i}] Observation/{obs['id']}: missing the OneAquaHealth indicator profile"
    ]


def test_an_observation_with_no_value_is_named(good_bundle: dict[str, Any]) -> None:
    broken = broken_copy(good_bundle)
    i = index_of(broken, "Observation")
    obs = broken["entry"][i]["resource"]
    del obs["valueCodeableConcept"]
    assert check_bundle(broken) == [
        f"entry[{i}] Observation/{obs['id']}: no value and no component"
    ]


def test_an_observation_with_an_empty_component_list_is_named(good_bundle: dict[str, Any]) -> None:
    broken = broken_copy(good_bundle)
    i = index_of(broken, "Observation", 1)
    obs = broken["entry"][i]["resource"]
    assert obs["code"]["text"] == "Habitats"
    obs["component"] = []
    assert check_bundle(broken) == [
        f"entry[{i}] Observation/{obs['id']}: no value and no component"
    ]


def test_a_patient_in_the_record_is_an_unexpected_resource_type(
    good_bundle: dict[str, Any],
) -> None:
    broken = broken_copy(good_bundle)
    broken["entry"].append(
        {
            "fullUrl": f"{FHIR_BASE}/Patient/p1",
            "resource": {
                "resourceType": "Patient",
                "id": "p1",
                "text": {"status": "generated", "div": "<div>A person</div>"},
            },
        }
    )
    last = len(broken["entry"]) - 1
    assert check_bundle(broken) == [f"entry[{last}] Patient/p1: unexpected resource type"]


def test_a_bundle_with_no_provenance_is_named(good_bundle: dict[str, Any]) -> None:
    broken = broken_copy(good_bundle)
    del broken["entry"][index_of(broken, "Provenance")]
    assert check_bundle(broken) == ["expected one Provenance, found 0"]


def test_a_bundle_with_two_provenances_is_named(good_bundle: dict[str, Any]) -> None:
    broken = broken_copy(good_bundle)
    broken["entry"].append(broken_copy(broken["entry"][index_of(broken, "Provenance")]))
    assert check_bundle(broken) == ["expected one Provenance, found 2"]


def test_several_problems_are_all_named_in_entry_order(good_bundle: dict[str, Any]) -> None:
    broken = broken_copy(good_bundle)
    first, second = index_of(broken, "Observation"), index_of(broken, "Observation", 1)
    del broken["entry"][first]["resource"]["performer"]
    del broken["entry"][second]["resource"]["text"]
    first_id = broken["entry"][first]["resource"]["id"]
    second_id = broken["entry"][second]["resource"]["id"]
    assert check_bundle(broken) == [
        f"entry[{first}] Observation/{first_id}: missing performer",
        f"entry[{second}] Observation/{second_id}: no narrative",
    ]


def test_in_a_transaction_problems_name_the_entry_by_its_urn(good_bundle: dict[str, Any]) -> None:
    tx = to_transaction(good_bundle, tag_system=REPO_URL, tag_code=TAG_CODE)
    assert check_bundle(tx) == []
    i = index_of(tx, "Observation")
    urn = tx["entry"][i]["fullUrl"]
    assert urn.startswith("urn:uuid:")
    del tx["entry"][i]["resource"]["subject"]
    assert check_bundle(tx) == [f"entry[{i}] Observation/{urn}: missing subject"]


def test_in_a_transaction_an_untargeted_observation_is_named_by_its_urn(
    good_bundle: dict[str, Any],
) -> None:
    tx = to_transaction(good_bundle, tag_system=REPO_URL, tag_code=TAG_CODE)
    urn = tx["entry"][index_of(tx, "Observation")]["fullUrl"]
    provenance = tx["entry"][index_of(tx, "Provenance")]["resource"]
    provenance["target"] = [t for t in provenance["target"] if t["reference"] != urn]
    assert check_bundle(tx) == [f"Provenance does not target {urn}"]


# A visit with no mapped answer


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "bug: a visit with no mapped answer gets a Provenance with an empty target list,"
        " which FHIR R4 forbids; check_bundle passes it and to_transaction then refuses it"
    ),
)
def test_a_visit_with_no_mapped_answer_does_not_pass_with_an_empty_provenance() -> None:
    bundle = emitted({"overall_rating": "good"})
    assert resources(bundle, "Observation") == []
    assert check_bundle(bundle) != [], "a Provenance must target at least one resource"
