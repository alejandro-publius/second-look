"""The referral and the way back refuse broken input, one break at a time, with the right words."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.act import PipeCase, pipes_worth_testing
from core.fhir_emit import (
    FHIR_BASE,
    ORG_ID,
    SL_SYSTEM,
    UCUM_SYSTEM,
    FhirEmitError,
    emit_visit,
    reference_problems,
)
from core.fhir_referral import (
    EXAMPLE_LAB_ID,
    EXAMPLE_LAB_ROLE_ID,
    EXAMPLE_PANEL,
    EXAMPLE_TAG_CODE,
    EXAMPLE_WORD,
    _example_observation,
    _identifier_value,
    check_example_bundle,
    check_referral_bundle,
    example_lab_result,
    example_tag,
    is_example,
    pipe_observations,
    referral_bundle,
)
from core.records import CheckResult, FeatureScore, Observer, Spot, VisitRecord

TODAY = date(2026, 9, 25)
EMITTED_AT = datetime(2026, 9, 24, 16, 41, tzinfo=UTC)
REFERRED_AT = datetime(2026, 9, 25, 9, 0, tzinfo=UTC)
COLLECTED_AT = datetime(2026, 9, 26, 10, 30, tzinfo=UTC)
REPORTED_AT = datetime(2026, 9, 29, 15, 0, tzinfo=UTC)

# A tag system that is not ours, like the sandbox run tag another tool might add.
OTHER_SYSTEM = "http://example.org/fhir/CodeSystem/sandbox-run"

REQUEST = "ServiceRequest/sl-referral-spot-1"
SPECIMEN = "Specimen/sl-example-specimen-spot-1"
SPOT_LOCATION = "Location/sl-loc-spot-1"
CREEK_LOCATION = "Location/sl-loc-strawberry-creek"
REASON_2 = "Observation/sl-obs-visit-0002-draining-pipes"
REASON_3 = "Observation/sl-obs-visit-0003-draining-pipes"

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


def _visit(visit_id: str, token: str, *, day: int, dry_days: int) -> VisitRecord:
    return VisitRecord(
        visit_id=visit_id,
        spot=SPOT,
        observer=Observer(
            contributor_token=token,
            scores=(FeatureScore(feature="pipe_running", correct=4, tested_on=date(2026, 9, 23)),),
        ),
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


def _visits() -> list[VisitRecord]:
    return [
        _visit("visit-0002", "alicetoken23456", day=22, dry_days=5),
        _visit("visit-0003", "bobtoken23456789", day=23, dry_days=9),
    ]


def _stored(visits: list[VisitRecord]) -> dict[str, dict[str, Any]]:
    return {v.visit_id: emit_visit(v, test_sitting=None, emitted_at=EMITTED_AT) for v in visits}


def _pipe(visits: list[VisitRecord]) -> PipeCase:
    (pipe,) = pipes_worth_testing(visits, TODAY)
    return pipe


def _key(resource: dict[str, Any]) -> str:
    return f"{resource['resourceType']}/{resource['id']}"


def _of_type(bundle: dict[str, Any], resource_type: str) -> list[dict[str, Any]]:
    return [
        e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == resource_type
    ]


def _only(bundle: dict[str, Any], resource_type: str) -> dict[str, Any]:
    (resource,) = _of_type(bundle, resource_type)
    return resource


def _get(bundle: dict[str, Any], reference: str) -> dict[str, Any]:
    (resource,) = [e["resource"] for e in bundle["entry"] if _key(e["resource"]) == reference]
    return resource


def _drop(bundle: dict[str, Any], reference: str) -> dict[str, Any]:
    out = deepcopy(bundle)
    out["entry"] = [e for e in out["entry"] if _key(e["resource"]) != reference]
    return out


def _with_copy_of(bundle: dict[str, Any], reference: str, new_id: str) -> dict[str, Any]:
    out = deepcopy(bundle)
    twin = deepcopy(_get(out, reference))
    twin["id"] = new_id
    out["entry"].append(
        {"fullUrl": f"{FHIR_BASE}/{twin['resourceType']}/{new_id}", "resource": twin}
    )
    return out


def _lab_observations(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return [o for o in _of_type(bundle, "Observation") if "specimen" in o]


def _lab_obs(*, code: str, kind: str, value: float | str, unit: str | None) -> dict[str, Any]:
    return _example_observation(
        spot_id="spot-1",
        spot_name="Spot one",
        spot_location_id="sl-loc-spot-1",
        request_id="sl-referral-spot-1",
        specimen_id="sl-example-specimen-spot-1",
        code=code,
        kind=kind,
        value=value,
        unit=unit,
        reported_at=REPORTED_AT,
    )


@pytest.fixture
def referral() -> dict[str, Any]:
    visits = _visits()
    return referral_bundle(_pipe(visits), _stored(visits), emitted_at=REFERRED_AT)


@pytest.fixture
def example(referral: dict[str, Any]) -> dict[str, Any]:
    return example_lab_result(referral, collected_at=COLLECTED_AT, reported_at=REPORTED_AT)


# is_example: our system and our code, on one tag.


def test_is_example_looks_past_other_tags_to_find_ours() -> None:
    resource = {
        "meta": {
            "tag": [
                {"system": OTHER_SYSTEM, "code": "run-7"},
                {"system": SL_SYSTEM, "code": "test-pipe-outflow"},
                {"system": SL_SYSTEM, "code": EXAMPLE_TAG_CODE},
            ]
        }
    }
    assert is_example(resource)
    assert is_example({"meta": {"tag": [example_tag()]}})


def test_is_example_needs_our_system_and_the_example_code_on_the_same_tag() -> None:
    assert not is_example({})
    assert not is_example({"meta": {"profile": ["http://hl7.eu/fhir/ig/oah"]}})
    assert not is_example(
        {"meta": {"tag": [{"system": OTHER_SYSTEM, "code": EXAMPLE_TAG_CODE}]}}
    ), "someone else's example tag is not ours"
    assert not is_example({"meta": {"tag": [{"system": SL_SYSTEM, "code": "test-pipe-outflow"}]}})
    split = {"meta": {"tag": [{"system": SL_SYSTEM}, {"code": EXAMPLE_TAG_CODE}]}}
    assert not is_example(split), "the system and the code must sit on one tag"


@settings(max_examples=200, deadline=None, database=None)
@given(
    tags=st.lists(
        st.fixed_dictionaries(
            {
                "system": st.sampled_from([SL_SYSTEM, OTHER_SYSTEM]),
                "code": st.sampled_from([EXAMPLE_TAG_CODE, "test-pipe-outflow", "run-7"]),
            }
        ),
        max_size=5,
    )
)
def test_is_example_is_true_exactly_when_one_tag_is_ours(tags: list[dict[str, str]]) -> None:
    ours = {"system": SL_SYSTEM, "code": EXAMPLE_TAG_CODE}
    assert is_example({"meta": {"tag": tags}}) is (ours in tags)


# Identifiers: a list of them, or a single one as a QuestionnaireResponse has.


def test_identifier_value_reads_a_single_identifier_or_the_first_in_a_list() -> None:
    assert _identifier_value({"identifier": {"system": "s", "value": "visit-0002"}}) == "visit-0002"
    assert _identifier_value({"identifier": [{"value": "first"}, {"value": "second"}]}) == "first"
    assert _identifier_value({"identifier": [{"value": 7}]}) == "7"


def test_identifier_value_is_empty_when_there_is_no_identifier_to_read() -> None:
    assert _identifier_value({}) == ""
    assert _identifier_value({"identifier": []}) == ""
    assert _identifier_value({"identifier": [{"system": "s"}]}) == ""
    assert _identifier_value({"identifier": "visit-0002"}) == "", (
        "a bare string is not an Identifier"
    )


def test_a_pipe_observation_with_a_single_identifier_still_counts() -> None:
    bundle = _stored(_visits())["visit-0002"]
    obs = _get(bundle, REASON_2)
    obs["identifier"] = obs["identifier"][0]
    assert pipe_observations(bundle) == [obs]
    del obs["identifier"]
    assert pipe_observations(bundle) == [], "no identifier, so no way to tell it is a pipe item"


# referral_bundle: only visits that saw the pipe running count, and the spot must be stored.


def test_a_stored_visit_without_the_pipe_present_adds_no_reason_person_or_response() -> None:
    visits = _visits()
    stored = _stored(visits)
    _get(stored["visit-0002"], REASON_2)["valueCodeableConcept"]["coding"][0]["code"] = "absent"
    made = referral_bundle(_pipe(visits), stored, emitted_at=REFERRED_AT)
    request = _only(made, "ServiceRequest")
    assert [r["reference"] for r in request["reasonReference"]] == [REASON_3]
    assert [qr["id"] for qr in _of_type(made, "QuestionnaireResponse")] == [
        "sl-qr-visit-visit-0003"
    ]
    assert _of_type(made, "Practitioner") == _of_type(stored["visit-0003"], "Practitioner")
    assert len(_of_type(made, "Location")) == 3, "the shared part comes from the visit that counts"
    assert check_referral_bundle(made) == []


def test_a_referral_needs_the_spot_location_in_the_stored_record() -> None:
    visits = _visits()
    stored = {vid: _drop(b, SPOT_LOCATION) for vid, b in _stored(visits).items()}
    with pytest.raises(
        FhirEmitError, match=r"^pipe spot-1: the spot Location is not in the stored record$"
    ):
        referral_bundle(_pipe(visits), stored, emitted_at=REFERRED_AT)


# example_lab_result: one ServiceRequest to point back at.


def test_the_way_back_needs_exactly_one_service_request(referral: dict[str, Any]) -> None:
    for broken in (
        _drop(referral, REQUEST),
        _with_copy_of(referral, REQUEST, "sl-referral-spot-1-again"),
    ):
        with pytest.raises(FhirEmitError, match="exactly one ServiceRequest"):
            example_lab_result(broken, collected_at=COLLECTED_AT, reported_at=REPORTED_AT)


# _example_observation: the value must fit its kind.


def test_an_example_quantity_needs_a_number_and_a_unit() -> None:
    message = r"^example lab-ecoli-cfu: a quantity needs a number and a UCUM unit$"
    with pytest.raises(FhirEmitError, match=message):
        _lab_obs(code="lab-ecoli-cfu", kind="quantity", value=120.0, unit=None)
    with pytest.raises(FhirEmitError, match=message):
        _lab_obs(code="lab-ecoli-cfu", kind="quantity", value="120", unit="[CFU]/dL")


def test_an_example_coded_value_needs_a_code() -> None:
    with pytest.raises(FhirEmitError, match=r"^example lab-hf183: a coded value needs a code$"):
        _lab_obs(code="lab-hf183", kind="coded", value=0.0, unit=None)


def test_an_example_observation_says_example_and_shows_its_value() -> None:
    share = _lab_obs(code="lab-enterobacteriaceae-share", kind="quantity", value=2, unit="%")
    assert share["valueQuantity"] == {
        "value": 2.0,
        "unit": "percent",
        "system": UCUM_SYSTEM,
        "code": "%",
    }
    assert isinstance(share["valueQuantity"]["value"], float)
    assert share["text"]["div"].count(EXAMPLE_WORD) == 1
    assert "at Spot one: 2 percent." in share["text"]["div"]
    assert "valueCodeableConcept" not in share

    marker = _lab_obs(code="lab-hf183", kind="coded", value="present", unit=None)
    assert marker["valueCodeableConcept"]["coding"][0]["code"] == "present"
    assert "at Spot one: present." in marker["text"]["div"]
    assert "valueQuantity" not in marker


# check_referral_bundle, broken one way at a time.


def test_check_referral_needs_exactly_one_service_request(referral: dict[str, Any]) -> None:
    assert check_referral_bundle(_drop(referral, REQUEST)) == [
        "expected one ServiceRequest, found 0"
    ]
    twice = _with_copy_of(referral, REQUEST, "sl-referral-spot-1-again")
    assert check_referral_bundle(twice) == ["expected one ServiceRequest, found 2"]


def test_check_referral_needs_a_reason(referral: dict[str, Any]) -> None:
    request = _only(referral, "ServiceRequest")
    del request["reasonReference"]
    assert check_referral_bundle(referral) == ["ServiceRequest has no reasonReference"]
    request["reasonReference"] = []
    assert check_referral_bundle(referral) == ["ServiceRequest has no reasonReference"]


def test_check_referral_rejects_a_reason_that_is_not_a_pipe_item(referral: dict[str, Any]) -> None:
    obs = _get(referral, REASON_2)
    for value in ("visit-0002-bank_type", "visit-0002-draining_pipes_old", "visit-0002"):
        obs["identifier"][0]["value"] = value
        assert check_referral_bundle(referral) == [f"reason {REASON_2} is not a pipe item"], value


def test_check_referral_takes_either_pipe_item_as_a_reason(referral: dict[str, Any]) -> None:
    _get(referral, REASON_2)["identifier"][0]["value"] = "visit-0002-sewage_discharge"
    assert check_referral_bundle(referral) == []


def test_check_referral_needs_a_location_as_the_subject(referral: dict[str, Any]) -> None:
    request = _only(referral, "ServiceRequest")
    request["subject"] = {"reference": f"Organization/{ORG_ID}"}
    assert check_referral_bundle(referral) == ["ServiceRequest subject is not a Location"]
    del request["subject"]
    assert check_referral_bundle(referral) == ["ServiceRequest subject is not a Location"]


def test_check_referral_rejects_the_example_tag_on_the_bundle(referral: dict[str, Any]) -> None:
    referral["meta"] = {"tag": [example_tag()]}
    assert check_referral_bundle(referral) == ["a referral Bundle must not carry the example tag"]


def test_the_way_back_can_never_pass_as_a_referral(example: dict[str, Any]) -> None:
    problems = check_referral_bundle(example)
    assert "a referral Bundle must not carry the example tag" in problems
    tagged = [p for p in problems if p.endswith(": a referral must not carry an example")]
    assert len(tagged) == 3 + len(EXAMPLE_PANEL), "the lab, its role, the Specimen and the panel"


@pytest.mark.xfail(
    strict=True,
    reason="bug: a reason that resolves to a non-Observation is skipped, not reported",
)
def test_check_referral_rejects_a_reason_that_points_at_a_location(
    referral: dict[str, Any],
) -> None:
    _only(referral, "ServiceRequest")["reasonReference"] = [{"reference": SPOT_LOCATION}]
    assert reference_problems(referral) == [], "the reference resolves, so nothing else reports it"
    assert check_referral_bundle(referral) != [], "a Location is not a pipe Observation"


@pytest.mark.xfail(
    strict=True,
    reason="bug: a reason given by fullUrl is never checked for present or for a pipe item",
)
def test_check_referral_rejects_an_absent_pipe_reached_by_its_full_url(
    referral: dict[str, Any],
) -> None:
    _get(referral, REASON_2)["valueCodeableConcept"]["coding"][0]["code"] = "absent"
    request = _only(referral, "ServiceRequest")
    request["reasonReference"][0] = {"reference": f"{FHIR_BASE}/{REASON_2}"}
    assert reference_problems(referral) == [], "a fullUrl reference resolves in a collection"
    assert any("does not report a pipe present" in p for p in check_referral_bundle(referral))


@pytest.mark.xfail(
    strict=True,
    reason="bug: a reason with no reference is skipped, not reported",
)
def test_check_referral_rejects_a_reason_with_no_reference(referral: dict[str, Any]) -> None:
    _only(referral, "ServiceRequest")["reasonReference"] = [{"display": "a pipe"}]
    assert check_referral_bundle(referral) != [], "a display is not a pipe Observation"


# check_example_bundle, broken one way at a time.


def test_check_example_passes_the_example_it_is_made_for(example: dict[str, Any]) -> None:
    assert check_example_bundle(example) == []


def test_a_referral_is_not_an_example(referral: dict[str, Any]) -> None:
    assert check_example_bundle(referral) == [
        "the example Bundle itself must carry the example tag",
        "expected one Specimen, found 0",
    ]


def test_check_example_needs_exactly_one_service_request(example: dict[str, Any]) -> None:
    none = _drop(example, REQUEST)
    assert reference_problems(none), "the Specimen and the panel still point at it"
    assert check_example_bundle(none) == [
        *reference_problems(none),
        "expected one ServiceRequest, found 0",
    ]
    twice = _with_copy_of(example, REQUEST, "sl-referral-spot-1-again")
    assert check_example_bundle(twice) == ["expected one ServiceRequest, found 2"]


def test_check_example_needs_exactly_one_specimen(example: dict[str, Any]) -> None:
    none = _drop(example, SPECIMEN)
    assert reference_problems(none), "the panel still points at it"
    assert check_example_bundle(none) == [
        *reference_problems(none),
        "expected one Specimen, found 0",
    ]
    twice = _with_copy_of(example, SPECIMEN, "sl-example-specimen-spot-1-again")
    assert check_example_bundle(twice) == ["expected one Specimen, found 2"]


def test_check_example_needs_a_laboratory_observation(example: dict[str, Any]) -> None:
    bare = deepcopy(example)
    lab = {_key(o) for o in _lab_observations(bare)}
    assert len(lab) == len(EXAMPLE_PANEL)
    bare["entry"] = [e for e in bare["entry"] if _key(e["resource"]) not in lab]
    assert check_example_bundle(bare) == ["no laboratory Observation in the example"]


def test_check_example_holds_the_lab_and_its_role_to_the_example_rules(
    example: dict[str, Any],
) -> None:
    for reference in (f"Organization/{EXAMPLE_LAB_ID}", f"PractitionerRole/{EXAMPLE_LAB_ROLE_ID}"):
        resource = _get(example, reference)
        del resource["meta"]
        resource["text"]["div"] = resource["text"]["div"].replace(EXAMPLE_WORD, "Note")
    problems = check_example_bundle(example)
    assert [p.split(" ", 1)[1] for p in problems] == [
        f"Organization/{EXAMPLE_LAB_ID}: laboratory resource without the example tag",
        f"Organization/{EXAMPLE_LAB_ID}: narrative does not say {EXAMPLE_WORD}",
        f"PractitionerRole/{EXAMPLE_LAB_ROLE_ID}: laboratory resource without the example tag",
        f"PractitionerRole/{EXAMPLE_LAB_ROLE_ID}: narrative does not say {EXAMPLE_WORD}",
    ]


def test_check_example_needs_the_specimen_under_their_profile(example: dict[str, Any]) -> None:
    _only(example, "Specimen")["meta"]["profile"] = []
    assert check_example_bundle(example) == ["Specimen is not under their SpecimenOah profile"]


def test_check_example_needs_the_specimen_at_the_referral_location(
    example: dict[str, Any],
) -> None:
    _only(example, "Specimen")["subject"] = {"reference": CREEK_LOCATION}
    assert check_example_bundle(example) == ["Specimen subject is not the ServiceRequest subject"]


def test_check_example_needs_a_practitioner_role_as_the_collector(
    example: dict[str, Any],
) -> None:
    collection = _only(example, "Specimen")["collection"]
    collection["collector"] = {"reference": f"Organization/{EXAMPLE_LAB_ID}"}
    assert check_example_bundle(example) == ["Specimen collector is not a PractitionerRole"]


def test_check_example_needs_a_collection_time(example: dict[str, Any]) -> None:
    del _only(example, "Specimen")["collection"]["collectedDateTime"]
    assert check_example_bundle(example) == ["Specimen has no collectedDateTime"]


def test_check_example_reports_a_specimen_with_no_collection_at_all(
    example: dict[str, Any],
) -> None:
    del _only(example, "Specimen")["collection"]
    assert check_example_bundle(example) == [
        "Specimen collector is not a PractitionerRole",
        "Specimen has no collectedDateTime",
    ]


def test_check_example_needs_each_result_under_the_indicator_profile(
    example: dict[str, Any],
) -> None:
    first = _lab_observations(example)[0]
    first["meta"]["profile"] = []
    assert check_example_bundle(example) == [
        f"{_key(first)}: missing the OneAquaHealth indicator profile"
    ]


def test_check_example_needs_each_result_to_point_at_the_specimen(
    example: dict[str, Any],
) -> None:
    first = _lab_observations(example)[0]
    first["specimen"] = {"reference": SPOT_LOCATION}
    assert check_example_bundle(example) == [f"{_key(first)}: does not point at the Specimen"]


def test_check_example_needs_a_value_on_each_result(example: dict[str, Any]) -> None:
    panel = _lab_observations(example)
    for obs in panel:
        for key in [k for k in obs if k.startswith("value")]:
            del obs[key]
    assert check_example_bundle(example) == [f"{_key(o)}: no value" for o in panel]
