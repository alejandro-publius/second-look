"""The emitter: golden files, structural rules, code tables and the transaction shape."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from core.fhir_emit import (
    FHIR_BASE,
    OAH_DISPLAYS,
    OAH_OBSERVATION_PROFILE,
    OAH_SYSTEM,
    REPO_URL,
    SL_DISPLAYS,
    SL_SYSTEM,
    UCUM_SYSTEM,
    FhirEmitError,
    _practitioner_id,
    check_bundle,
    code_for_answer,
    emit_visit,
    fhir_id,
    form_items,
    to_transaction,
)
from core.records import (
    FEATURES,
    FeatureScore,
    Observer,
    Spot,
    VisitRecord,
)
from core.records import (
    TestSitting as _TestSitting,
)

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = ROOT / "fhir" / "golden"
GOLDEN_COLLECTION = GOLDEN_DIR / "visit-strawberry-creek-1.json"
GOLDEN_TRANSACTION = GOLDEN_DIR / "visit-strawberry-creek-1.transaction.json"
TAG_CODE = "second-look"

TESTED_ON = date(2026, 9, 23)
EMITTED_AT = datetime(2026, 9, 24, 16, 41, tzinfo=UTC)


def strawberry_scores() -> tuple[FeatureScore, ...]:
    return tuple(
        FeatureScore(feature=f, correct=c, tested_on=TESTED_ON)
        for f, c in zip(FEATURES, (4, 2, 3, 4), strict=True)
    )


def strawberry_spot() -> Spot:
    return Spot(
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


def strawberry_visit() -> VisitRecord:
    """The worked example from docs/fhir_mapping.md, on the real form item ids."""
    return VisitRecord(
        visit_id="visit-0001",
        spot=strawberry_spot(),
        observer=Observer(
            contributor_token="ct_7f3a9c2e",
            scores=strawberry_scores(),
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


def strawberry_sitting() -> _TestSitting:
    return _TestSitting(
        sitting_id="test-sitting-0001",
        contributor_token="ct_7f3a9c2e",
        completed_at=datetime(2026, 9, 23, 17, 5, tzinfo=UTC),
        scores=strawberry_scores(),
    )


def second_visit() -> VisitRecord:
    """A different visit: a multi-select, a number, a can't tell, no test sitting, coarse pin."""
    return VisitRecord(
        visit_id="7c1e2d3f-4a5b-4c6d-8e9f-0a1b2c3d4e5f",
        spot=Spot(
            spot_id="codornices-lower-2",
            spot_name="Codornices Creek, lower reach, spot 2",
            reach_id="codornices-lower",
            reach_name="Codornices Creek, lower reach",
            creek_id="codornices-creek",
            creek_name="Codornices Creek",
            latitude=37.88123,
            longitude=-122.29987,
            coarse=True,
        ),
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


def normalise(bundle: dict) -> str:
    return json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def resources(bundle: dict, resource_type: str) -> list[dict]:
    return [
        e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == resource_type
    ]


def by_type(bundle: dict) -> list[str]:
    return [e["resource"]["resourceType"] for e in bundle["entry"]]


@pytest.fixture
def golden_bundle() -> dict:
    return emit_visit(strawberry_visit(), test_sitting=strawberry_sitting(), emitted_at=EMITTED_AT)


# Golden files


def test_collection_matches_golden(golden_bundle: dict) -> None:
    text = normalise(golden_bundle)
    if os.environ.get("SL_UPDATE_GOLDEN") == "1":
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        GOLDEN_COLLECTION.write_text(text, encoding="utf-8")
    assert GOLDEN_COLLECTION.exists(), "run with SL_UPDATE_GOLDEN=1 once to write the golden"
    assert text == GOLDEN_COLLECTION.read_text(encoding="utf-8")


def test_transaction_matches_golden(golden_bundle: dict) -> None:
    text = normalise(to_transaction(golden_bundle, tag_system=REPO_URL, tag_code=TAG_CODE))
    if os.environ.get("SL_UPDATE_GOLDEN") == "1":
        GOLDEN_TRANSACTION.write_text(text, encoding="utf-8")
    assert GOLDEN_TRANSACTION.exists()
    assert text == GOLDEN_TRANSACTION.read_text(encoding="utf-8")


def test_golden_files_pass_the_structural_check() -> None:
    for path in (GOLDEN_COLLECTION, GOLDEN_TRANSACTION):
        assert check_bundle(json.loads(path.read_text(encoding="utf-8"))) == []


def test_re_emitting_gives_the_same_bundle(golden_bundle: dict) -> None:
    again = emit_visit(strawberry_visit(), test_sitting=strawberry_sitting(), emitted_at=EMITTED_AT)
    assert again == golden_bundle


# Shape of the Strawberry Creek record


def test_entry_order_and_counts(golden_bundle: dict) -> None:
    assert golden_bundle["type"] == "collection"
    assert golden_bundle["id"] == "sl-visit-visit-0001"
    assert by_type(golden_bundle) == [
        "Organization",
        "Device",
        "Location",
        "Location",
        "Location",
        "Practitioner",
        "QuestionnaireResponse",
        "QuestionnaireResponse",
        "Observation",
        "Observation",
        "Observation",
        "Observation",
        "Observation",
        "Observation",
        "Provenance",
    ]
    assert check_bundle(golden_bundle) == []


def test_locations_nest_creek_reach_spot(golden_bundle: dict) -> None:
    creek, reach, spot = resources(golden_bundle, "Location")
    for loc in (creek, reach, spot):
        assert loc["meta"]["profile"] == [
            "http://hl7.eu/fhir/ig/oah/StructureDefinition/location-oah"
        ]
        assert loc["mode"] == "instance"
        assert loc["identifier"][0]["system"] == f"{FHIR_BASE}/location-id"
        assert loc["name"]
    assert "partOf" not in creek
    assert reach["partOf"]["reference"] == f"Location/{creek['id']}"
    assert spot["partOf"]["reference"] == f"Location/{reach['id']}"
    assert spot["position"] == {"latitude": 37.8719, "longitude": -122.2585}


def test_practitioner_is_pseudonymous_with_a_dated_qualification(golden_bundle: dict) -> None:
    (practitioner,) = resources(golden_bundle, "Practitioner")
    assert "name" not in practitioner
    assert practitioner["identifier"] == [
        {"system": f"{FHIR_BASE}/contributor-token", "value": _practitioner_id("ct_7f3a9c2e")}
    ]
    (qualification,) = practitioner["qualification"]
    assert qualification["code"]["coding"][0] == {
        "system": SL_SYSTEM,
        "code": "second-look-test",
        "display": "Second Look observer test",
    }
    assert qualification["period"] == {"start": "2026-09-23", "end": "2026-12-22"}
    assert qualification["issuer"] == {"reference": "Organization/sl-org"}
    assert "ct_7f3a9c2e" not in practitioner["text"]["div"]


def test_device_carries_the_software_version(golden_bundle: dict) -> None:
    (device,) = resources(golden_bundle, "Device")
    assert device["version"] == [{"value": "0.1.0"}]
    assert device["type"]["coding"][0]["code"] == "software"


def test_test_sitting_response_holds_per_feature_scores(golden_bundle: dict) -> None:
    test_qr, visit_qr = resources(golden_bundle, "QuestionnaireResponse")
    assert test_qr["questionnaire"] == f"{FHIR_BASE}/Questionnaire/sl-questionnaire-test"
    assert test_qr["status"] == "completed"
    assert test_qr["authored"] == "2026-09-23T17:05:00Z"
    assert test_qr["author"]["reference"].startswith("Practitioner/")
    scores = {
        item["linkId"]: item["item"][0]["answer"][0]["valueInteger"] for item in test_qr["item"]
    }
    assert scores == {
        "artificial_bank": 4,
        "dug_out_channel": 2,
        "invasive_plant": 3,
        "pipe_running": 4,
    }
    assert all(item["item"][0]["linkId"] == f"{item['linkId']}.score" for item in test_qr["item"])


def test_visit_response_link_ids_are_form_item_ids(golden_bundle: dict) -> None:
    _, visit_qr = resources(golden_bundle, "QuestionnaireResponse")
    assert visit_qr["questionnaire"] == f"{FHIR_BASE}/Questionnaire/sl-questionnaire-check"
    assert visit_qr["authored"] == "2026-09-24T16:40:00Z"
    form_ids = [item["id"] for item in form_items()]
    link_ids = [item["linkId"] for item in visit_qr["item"]]
    assert link_ids == [
        "channel_form",
        "bank_type",
        "draining_pipes",
        "water_height_m",
        "invasive_species",
        "overall_rating",
    ]
    assert link_ids == [i for i in form_ids if i in link_ids], "form order is kept"
    answers = {item["linkId"]: item["answer"][0] for item in visit_qr["item"]}
    assert answers["bank_type"]["valueCoding"]["code"] == "present"
    assert answers["draining_pipes"]["valueCoding"] == {
        "system": SL_SYSTEM,
        "code": "cant-tell",
        "display": "Can't tell",
    }
    assert answers["water_height_m"] == {"valueDecimal": 0.2}
    assert answers["overall_rating"]["valueCoding"]["code"] == "moderate"


def test_one_observation_per_mapped_answer(golden_bundle: dict) -> None:
    observations = resources(golden_bundle, "Observation")
    codes = [
        (o["code"]["coding"][0]["system"], o["code"]["coding"][0]["code"]) for o in observations
    ]
    assert codes == [
        (OAH_SYSTEM, "morophology"),
        (SL_SYSTEM, "artificial-bank"),
        (SL_SYSTEM, "pipe-running"),
        (OAH_SYSTEM, "hydrology"),
        (SL_SYSTEM, "invasive-plant"),
        (SL_SYSTEM, "overall-rating"),
    ]
    _, visit_qr = resources(golden_bundle, "QuestionnaireResponse")
    (practitioner,) = resources(golden_bundle, "Practitioner")
    spot = resources(golden_bundle, "Location")[2]
    for obs in observations:
        assert obs["meta"]["profile"] == [OAH_OBSERVATION_PROFILE]
        assert obs["status"] == "final"
        assert obs["subject"] == {"reference": f"Location/{spot['id']}"}
        assert obs["performer"] == [{"reference": f"Practitioner/{practitioner['id']}"}]
        assert obs["effectiveDateTime"] == "2026-09-24T16:40:00Z"
        assert obs["derivedFrom"] == [{"reference": f"QuestionnaireResponse/{visit_qr['id']}"}]
        assert obs["text"]["status"] == "generated"
    *mapped, rating = observations
    assert all(o["category"][0]["coding"][0]["system"] == OAH_SYSTEM for o in mapped)
    # The form maps the overall rating to no Observation (fhir is null). This one is there only
    # because the rating check changed the rating: first good, kept moderate.
    assert not any("overall" in o["id"] for o in mapped)
    assert rating["id"] == "sl-obs-visit-0001-overall-rating"


def test_observation_values_use_the_code_systems_own_displays(golden_bundle: dict) -> None:
    observations = {o["id"]: o for o in resources(golden_bundle, "Observation")}
    bank = observations["sl-obs-visit-0001-bank-type"]
    assert bank["valueCodeableConcept"]["coding"] == [
        {"system": OAH_SYSTEM, "code": "present", "display": "Present"}
    ]
    assert bank["category"][0]["coding"][0]["code"] == "morophology"
    pipe = observations["sl-obs-visit-0001-draining-pipes"]
    assert pipe["valueCodeableConcept"]["coding"][0]["code"] == "cant-tell"
    assert pipe["category"][0]["coding"][0]["code"] == "hydrology"
    invasive = observations["sl-obs-visit-0001-invasive-species"]
    assert invasive["category"][0]["coding"][0]["code"] == "invasiveOrganisms"
    height = observations["sl-obs-visit-0001-water-height-m"]
    assert height["valueQuantity"] == {
        "value": 0.2,
        "unit": "metre",
        "system": UCUM_SYSTEM,
        "code": "m",
    }
    # The observer's score for the feature is stated in the narrative, in plain words.
    assert "4 of 4" in bank["text"]["div"]
    assert "tested 2026-09-23" in bank["text"]["div"]


def test_provenance_ties_answers_to_the_person_and_the_software(golden_bundle: dict) -> None:
    (provenance,) = resources(golden_bundle, "Provenance")
    observations = resources(golden_bundle, "Observation")
    assert provenance["target"] == [{"reference": f"Observation/{o['id']}"} for o in observations]
    assert provenance["recorded"] == "2026-09-24T16:41:00Z"
    agents = {a["type"]["coding"][0]["code"]: a["who"]["reference"] for a in provenance["agent"]}
    assert agents["author"].startswith("Practitioner/")
    assert agents["assembler"] == "Device/sl-device"
    test_qr, visit_qr = resources(golden_bundle, "QuestionnaireResponse")
    assert provenance["entity"] == [
        {"role": "source", "what": {"reference": f"QuestionnaireResponse/{visit_qr['id']}"}},
        {"role": "source", "what": {"reference": f"QuestionnaireResponse/{test_qr['id']}"}},
    ]


SITTING_SENTENCE = "The sources are the visit and the observer test sitting."
VISIT_ONLY_SENTENCE = "The source is the visit."


def test_provenance_narrative_names_the_test_sitting_only_when_there_is_one(
    golden_bundle: dict,
) -> None:
    # Round 09 Q02: the narrative said a test sitting was a source even when entity had none.
    (with_sitting,) = resources(golden_bundle, "Provenance")
    assert len(with_sitting["entity"]) == 2
    assert with_sitting["text"]["div"].endswith(f"{SITTING_SENTENCE}</p></div>")
    for visit in (second_visit(), strawberry_visit()):
        bundle = emit_visit(visit, test_sitting=None, emitted_at=EMITTED_AT)
        (without,) = resources(bundle, "Provenance")
        assert len(without["entity"]) == 1
        assert without["text"]["div"].endswith(f"{VISIT_ONLY_SENTENCE}</p></div>")
        assert "test sitting" not in without["text"]["div"]


def test_every_domain_resource_has_a_generated_narrative(golden_bundle: dict) -> None:
    for entry in golden_bundle["entry"]:
        text = entry["resource"]["text"]
        assert text["status"] == "generated"
        # A resource that states a language marks its narrative's own language too (UPDATE_32).
        lang = ' lang="en" xml:lang="en"' if "language" in entry["resource"] else ""
        assert text["div"].startswith(f'<div xmlns="http://www.w3.org/1999/xhtml"{lang}>')
        assert chr(0x2014) not in text["div"] and chr(0x2013) not in text["div"]


def test_full_urls_match_resource_ids(golden_bundle: dict) -> None:
    for entry in golden_bundle["entry"]:
        resource = entry["resource"]
        assert entry["fullUrl"] == f"{FHIR_BASE}/{resource['resourceType']}/{resource['id']}"
        assert re.fullmatch(r"[A-Za-z0-9.\-]{1,64}", resource["id"])


# A second visit checks the structural rules


def test_second_visit_structure() -> None:
    bundle = emit_visit(second_visit(), test_sitting=None, emitted_at=EMITTED_AT)
    assert check_bundle(bundle) == []
    assert by_type(bundle).count("QuestionnaireResponse") == 1, "no test sitting, no test response"
    (practitioner,) = resources(bundle, "Practitioner")
    assert "qualification" not in practitioner, "no score, no qualification"
    observations = {o["id"].rsplit("-", 1)[-1]: o for o in resources(bundle, "Observation")}
    # habitats: one Observation, one component per selected value, coded from our CodeSystem
    habitats_text = next(i.get("name") or i["text"] for i in form_items() if i["id"] == "habitats")
    habitats = next(
        o for o in resources(bundle, "Observation") if o["code"]["text"] == habitats_text
    )
    assert "valueCodeableConcept" not in habitats
    assert [c["code"]["coding"][0]["code"] for c in habitats["component"]] == [
        "sand-banks",
        "riffles",
    ]
    assert all(c["code"]["coding"][0]["system"] == SL_SYSTEM for c in habitats["component"])
    assert all(
        c["valueCodeableConcept"]["coding"][0]["code"] == "present" for c in habitats["component"]
    )
    # an empty multi-select is not an Observation
    assert not any(
        o["code"].get("text") == "Natural debris" for o in resources(bundle, "Observation")
    )
    # a number
    height = next(o for o in resources(bundle, "Observation") if "valueQuantity" in o)
    assert height["valueQuantity"]["value"] == 0.35
    assert height["valueQuantity"]["code"] == "m"
    # a can't tell with no score: no score sentence in the narrative
    invasive = next(
        o
        for o in resources(bundle, "Observation")
        if o["code"]["coding"][0]["code"] == "invasive-plant" and "valueCodeableConcept" in o
    )
    assert invasive["valueCodeableConcept"]["coding"][0]["code"] == "cant-tell"
    assert "scored" not in invasive["text"]["div"]
    # a value that is one of their codes keeps their system and display
    trees = next(
        o for o in resources(bundle, "Observation") if o["code"]["text"] == "Vegetation Type (Left)"
    )
    assert trees["valueCodeableConcept"]["coding"][0] == {
        "system": OAH_SYSTEM,
        "code": "trees",
        "display": "Trees (height >3m)",
    }
    # sliders and the overall rating have fhir null and produce no Observation
    texts = {o["code"].get("text") for o in resources(bundle, "Observation")}
    assert "Which feelings best describe your experience?" not in texts
    assert "Overall, how would you rate this stream?" not in texts
    assert "pipe" not in "".join(observations)  # not answered, not emitted
    # the coarse pin is rounded to about 1 km
    spot = resources(bundle, "Location")[2]
    assert spot["position"] == {"latitude": 37.88, "longitude": -122.3}
    (provenance,) = resources(bundle, "Provenance")
    assert len(provenance["entity"]) == 1
    assert len(provenance["target"]) == len(resources(bundle, "Observation"))


def test_qualification_comes_from_observer_scores_without_a_sitting() -> None:
    visit = strawberry_visit()
    bundle = emit_visit(visit, test_sitting=None, emitted_at=EMITTED_AT)
    (practitioner,) = resources(bundle, "Practitioner")
    assert practitioner["qualification"][0]["period"] == {
        "start": "2026-09-23",
        "end": "2026-12-22",
    }
    assert by_type(bundle).count("QuestionnaireResponse") == 1


def test_number_without_unit_is_refused() -> None:
    items = [
        {
            "id": "odd_number",
            "type": "number",
            "text": "Odd",
            "fhir": {"code_system": "oah", "code": "hydrology"},
        }
    ]
    visit = strawberry_visit().model_copy(update={"answers": {"odd_number": 3.0}})
    with pytest.raises(FhirEmitError):
        emit_visit(visit, test_sitting=None, emitted_at=EMITTED_AT, items=items)


def test_naive_datetimes_are_treated_as_utc() -> None:
    visit = strawberry_visit().model_copy(
        update={"answered_at": datetime(2026, 9, 24, 16, 40, 12, 345)}
    )
    bundle = emit_visit(visit, test_sitting=None, emitted_at=EMITTED_AT)
    assert resources(bundle, "Observation")[0]["effectiveDateTime"] == "2026-09-24T16:40:12Z"


# Code tables must match the FSH and the guide


def test_check_questionnaire_fsh_mirrors_the_form() -> None:
    """The guide's Questionnaire must list every form item, in order, or the validator rejects
    our responses (linkIds, order and answer options are all checked)."""
    fsh = (ROOT / "fhir" / "fsh" / "questionnaires-second-look.fsh").read_text(encoding="utf-8")
    check = fsh[fsh.index("Instance: sl-questionnaire-check") :]
    link_ids = re.findall(r'^\* item\[\d+\]\.linkId = "([^"]+)"', check, flags=re.MULTILINE)
    expected = [item["id"] for item in form_items() if item["type"] != "sliders"]
    assert link_ids == expected
    for item in form_items():
        if item["type"] in {"sliders", "number", "pick_region_list"}:
            continue
        block_start = check.index(f'.linkId = "{item["id"]}"')
        block = check[block_start:]
        next_item = re.search(r"^\* item\[\d+\]\.linkId", block[1:], flags=re.MULTILINE)
        block = block[: next_item.start() + 1] if next_item else block
        values = (
            ["present", "absent", "cant_tell"]
            if item["type"] == "yesno"
            else [str(o["value"]) for o in item["options"]]
        )
        for value in values:
            coding = code_for_answer(value)
            assert coding is not None, (item["id"], value)
            assert f"#{coding['code']} " in block, (item["id"], value)


def test_sliders_are_not_carried_in_the_response() -> None:
    bundle = emit_visit(second_visit(), test_sitting=None, emitted_at=EMITTED_AT)
    (visit_qr,) = resources(bundle, "QuestionnaireResponse")
    assert "feelings" not in [item["linkId"] for item in visit_qr["item"]]
    assert "overall_rating" in [item["linkId"] for item in visit_qr["item"]]


def test_sl_displays_match_the_fsh_codesystem() -> None:
    fsh = (ROOT / "fhir" / "fsh" / "codesystem-second-look.fsh").read_text(encoding="utf-8")
    in_fsh = dict(re.findall(r'^\* #(\S+) "([^"]*)"', fsh, flags=re.MULTILINE))
    assert in_fsh == SL_DISPLAYS


def test_oah_displays_match_the_built_guide() -> None:
    built = ROOT / "fhir/build/ig/fsh-generated/resources/CodeSystem-temporarySystem-oah-eu.json"
    if not built.exists():
        pytest.skip("guide not built; scripts/fhir_build.sh writes it")
    concepts = {c["code"]: c["display"] for c in json.loads(built.read_text())["concept"]}
    for code, display in OAH_DISPLAYS.items():
        assert concepts[code] == display, code


def test_every_coded_form_option_has_a_code() -> None:
    missing: list[str] = []
    for item in form_items():
        if not item.get("fhir"):
            continue
        for option in item.get("options", []):
            value = str(option["value"])
            if code_for_answer(value) is None:
                missing.append(f"{item['id']}:{value}")
    assert missing == []


def test_fhir_id_is_safe_and_stable() -> None:
    assert fhir_id("sl-obs", "visit_1", "bank_type") == "sl-obs-visit-1-bank-type"
    long = fhir_id("sl-obs", "x" * 100)
    assert len(long) <= 64
    assert long == fhir_id("sl-obs", "x" * 100)
    assert re.fullmatch(r"[A-Za-z0-9.\-]{1,64}", long)


# Transaction shape


def test_transaction_is_conditional_creates_with_our_tag(golden_bundle: dict) -> None:
    tx = to_transaction(golden_bundle, tag_system=REPO_URL, tag_code=TAG_CODE)
    assert tx["type"] == "transaction"
    assert len(tx["entry"]) == len(golden_bundle["entry"])
    urns = set()
    for entry, original in zip(tx["entry"], golden_bundle["entry"], strict=True):
        assert entry["fullUrl"].startswith("urn:uuid:")
        urns.add(entry["fullUrl"])
        request = entry["request"]
        assert request["method"] == "POST"
        assert request["url"] == original["resource"]["resourceType"]
        assert "ifNoneExist" in request
        assert "?" not in request["url"] and "$" not in request["ifNoneExist"]
        resource = entry["resource"]
        assert "id" not in resource
        assert {"system": REPO_URL, "code": TAG_CODE} in resource["meta"]["tag"]
    assert len(urns) == len(tx["entry"])
    # identifiers drive the conditional creates, Provenance through its first target
    requests = {e["request"]["url"]: e["request"]["ifNoneExist"] for e in tx["entry"]}
    assert requests["Practitioner"] == (
        f"Practitioner?identifier={FHIR_BASE}/contributor-token|" + _practitioner_id("ct_7f3a9c2e")
    )
    assert requests["Provenance"].startswith(
        f"Provenance?target:Observation.identifier={FHIR_BASE}/observation|"
    )
    for entry in tx["entry"]:
        assert entry["request"]["ifNoneExist"].startswith(entry["request"]["url"] + "?")

    # every internal reference now points at an entry urn
    text = json.dumps(tx)
    assert "Location/sl-loc" not in text and "Practitioner/sl-" not in text
    assert check_bundle(tx) == []


def test_transaction_is_deterministic(golden_bundle: dict) -> None:
    a = to_transaction(golden_bundle, tag_system=REPO_URL, tag_code=TAG_CODE)
    b = to_transaction(golden_bundle, tag_system=REPO_URL, tag_code=TAG_CODE)
    assert a == b


def test_transaction_leaves_the_collection_untouched(golden_bundle: dict) -> None:
    before = json.dumps(golden_bundle, sort_keys=True)
    to_transaction(golden_bundle, tag_system=REPO_URL, tag_code=TAG_CODE)
    assert json.dumps(golden_bundle, sort_keys=True) == before


# check_bundle catches broken records


def test_check_bundle_reports_dangling_reference(golden_bundle: dict) -> None:
    broken = json.loads(json.dumps(golden_bundle))
    resources(broken, "Observation")[0]["subject"]["reference"] = "Location/nowhere"
    problems = check_bundle(broken)
    assert any("Location/nowhere" in p for p in problems)


def test_check_bundle_reports_untargeted_observation(golden_bundle: dict) -> None:
    broken = json.loads(json.dumps(golden_bundle))
    resources(broken, "Provenance")[0]["target"].pop()
    problems = check_bundle(broken)
    assert any("does not target" in p for p in problems)


def test_check_bundle_reports_missing_narrative(golden_bundle: dict) -> None:
    broken = json.loads(json.dumps(golden_bundle))
    del resources(broken, "Device")[0]["text"]
    assert any("no narrative" in p for p in check_bundle(broken))


def test_the_contributor_token_itself_never_appears_in_the_record(golden_bundle: dict) -> None:
    """The token is what a person uses to attach their score, so the public record holds only a
    one way hash of it. Anyone who reads the record must not be able to become that person."""
    text = json.dumps(golden_bundle)
    assert "ct_7f3a9c2e" not in text
    assert _practitioner_id("ct_7f3a9c2e") in text


def test_check_bundle_reports_a_fullurl_used_twice(golden_bundle: dict) -> None:
    broken = json.loads(json.dumps(golden_bundle))
    broken["entry"].append(json.loads(json.dumps(broken["entry"][2])))
    assert any("appears twice" in p for p in check_bundle(broken))


def _rating_observations(bundle: dict) -> list[dict]:
    return [o for o in resources(bundle, "Observation") if o["id"].endswith("-overall-rating")]


def _answered_rating(bundle: dict) -> str:
    visit_qr = resources(bundle, "QuestionnaireResponse")[-1]
    item = next(i for i in visit_qr["item"] if i["linkId"] == "overall_rating")
    return str(item["answer"][0]["valueCoding"]["code"])


def test_a_rating_changed_at_the_rating_check_is_the_value_and_the_first_is_a_component() -> None:
    """The app stores the first rating as the answer; the rating check leaves the final one. The
    record answers the kept rating, in the QuestionnaireResponse and in the value of the rating
    Observation, and keeps the first rating in that Observation as a first-rating component."""
    visit = second_visit().model_copy(update={"first_rating": "good", "final_rating": "poor"})
    assert visit.answers["overall_rating"] == "good"
    bundle = emit_visit(visit, test_sitting=None, emitted_at=EMITTED_AT)
    assert check_bundle(bundle) == []
    assert _answered_rating(bundle) == "poor"
    (rating,) = _rating_observations(bundle)
    assert rating["code"]["coding"] == [
        {"system": SL_SYSTEM, "code": "overall-rating", "display": "Overall rating"}
    ]
    assert rating["valueCodeableConcept"]["coding"] == [
        {"system": SL_SYSTEM, "code": "poor", "display": "Poor overall rating"}
    ]
    assert rating["component"] == [
        {
            "code": {
                "coding": [
                    {"system": SL_SYSTEM, "code": "first-rating", "display": "First overall rating"}
                ]
            },
            "valueCodeableConcept": {
                "coding": [{"system": SL_SYSTEM, "code": "good", "display": "Good overall rating"}]
            },
        }
    ]
    assert "The first rating was good" in rating["text"]["div"]
    (provenance,) = resources(bundle, "Provenance")
    assert {"reference": f"Observation/{rating['id']}"} in provenance["target"]
    # The stored answers stay as given.
    assert visit.answers["overall_rating"] == "good"


@pytest.mark.parametrize(
    ("first", "final"), [("good", "good"), ("good", None), (None, None), (None, "good")]
)
def test_a_rating_the_check_did_not_change_adds_no_rating_observation(
    first: str | None, final: str | None
) -> None:
    visit = second_visit().model_copy(update={"first_rating": first, "final_rating": final})
    bundle = emit_visit(visit, test_sitting=None, emitted_at=EMITTED_AT)
    assert _rating_observations(bundle) == []
    assert _answered_rating(bundle) == "good"
    assert bundle == emit_visit(second_visit(), test_sitting=None, emitted_at=EMITTED_AT)


def test_a_final_rating_with_no_rating_answered_adds_no_rating() -> None:
    answers = {k: v for k, v in second_visit().answers.items() if k != "overall_rating"}
    visit = second_visit().model_copy(
        update={"answers": answers, "first_rating": None, "final_rating": "poor"}
    )
    bundle = emit_visit(visit, test_sitting=None, emitted_at=EMITTED_AT)
    assert _rating_observations(bundle) == []
    assert "poor" not in json.dumps(bundle)
