"""Edges of the FHIR emitter that mutation testing (make mutation) found no test for.

A coarse pin says it is coarse and a precise one is kept to five decimals; an id stays inside the
FHIR limits; a number's unit may sit on the form item or in its fhir block, and a unit with no
plain name is shown by its code; a list answer reads as a list; the qualification is dated from
the sitting passed in; the transaction replaces our old tag and keeps everyone else's; and a
broken reference or a doubled fullUrl is named by where it is.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, date, datetime
from typing import Any

import pytest

from core.fhir_emit import (
    FhirEmitError,
    check_bundle,
    emit_visit,
    fhir_id,
    reference_problems,
    to_transaction,
)
from core.records import FEATURES, FeatureScore, Observer, Spot, VisitRecord
from core.records import TestSitting as Sitting

EMITTED_AT = datetime(2026, 9, 24, 16, 41, tzinfo=UTC)
TAG_SYSTEM = "https://github.com/alejandro-publius/second-look"
ITEMS: list[dict[str, Any]] = [
    {
        "id": "depth_cm",
        "type": "number",
        "text": "Water depth",
        "unit": "cm",
        "fhir": {"code_system": "oah", "code": "hydrology"},
    },
    {
        "id": "water_temp",
        "type": "number",
        "text": "Water temperature",
        "unit": "cm",
        "fhir": {"code_system": "oah", "code": "hydrology", "unit": "Cel"},
    },
    {
        "id": "turbidity",
        "type": "number",
        "fhir": {"code_system": "oah", "code": "hydrology", "unit": "[NTU]"},
    },
    {
        "id": "habitats",
        "type": "multi",
        "text": "Habitats",
        "fhir": {"code_system": "oah", "code": "morophology"},
    },
]


def spot(**over: Any) -> Spot:
    fields: dict[str, Any] = {
        "spot_id": "spot-1",
        "spot_name": "Below the footbridge",
        "reach_id": "campus-reach",
        "reach_name": "Campus reach",
        "creek_id": "strawberry-creek",
        "creek_name": "Strawberry Creek",
        "latitude": 37.87191234,
        "longitude": -122.25851234,
        "coarse": False,
    }
    fields.update(over)
    return Spot(**fields)


def scores(tested_on: date) -> tuple[FeatureScore, ...]:
    return tuple(FeatureScore(feature=f, correct=3, tested_on=tested_on) for f in FEATURES)


def visit(answers: dict[str, Any] | None = None, **spot_over: Any) -> VisitRecord:
    return VisitRecord(
        visit_id="visit-0001",
        spot=spot(**spot_over),
        observer=Observer(contributor_token="ct_7f3a9c2e", scores=scores(date(2026, 9, 1))),
        answered_at=datetime(2026, 9, 24, 16, 40, tzinfo=UTC),
        answers=answers if answers is not None else {"depth_cm": 12.0},
    )


def emit(v: VisitRecord, sitting: Sitting | None = None) -> dict[str, Any]:
    return emit_visit(v, test_sitting=sitting, emitted_at=EMITTED_AT, items=ITEMS)


def the(bundle: dict[str, Any], rtype: str, id_part: str = "") -> dict[str, Any]:
    found = [
        e["resource"]
        for e in bundle["entry"]
        if e["resource"]["resourceType"] == rtype and id_part in e["resource"]["id"]
    ]
    assert len(found) == 1, [r["id"] for r in found]
    return found[0]


def narrative(resource: dict[str, Any]) -> str:
    match = re.search(r"<p>(.*)</p>", resource["text"]["div"])
    assert match
    return match.group(1)


# Where the spot is, and how exactly


def test_a_coarse_pin_is_rounded_to_two_decimals_and_says_it_is_coarse() -> None:
    point = the(emit(visit(coarse=True)), "Location", "spot-1")
    assert point["position"] == {"latitude": 37.87, "longitude": -122.26}
    assert point["description"] == "Coarse position, about 1 km."


def test_a_placed_pin_keeps_five_decimals_and_no_coarse_note() -> None:
    point = the(emit(visit(coarse=False)), "Location", "spot-1")
    assert point["position"] == {"latitude": 37.87191, "longitude": -122.25851}
    assert "description" not in point


@pytest.mark.parametrize("missing", ["latitude", "longitude"])
def test_half_a_position_is_no_position(missing: str) -> None:
    point = the(emit(visit(coarse=True, **{missing: None})), "Location", "spot-1")
    assert "position" not in point
    assert "description" not in point


# Ids


def test_an_id_loses_its_bad_characters_and_its_edge_hyphens() -> None:
    assert fhir_id(" spot 1 ") == "spot-1"
    assert fhir_id("--x--", "y") == "x---y"


def test_an_id_of_64_characters_is_kept_and_a_longer_one_is_cut_with_a_digest() -> None:
    assert fhir_id("a" * 64) == "a" * 64
    long = "a" * 65
    cut = fhir_id(long)
    digest = hashlib.sha256(long.encode("utf-8")).hexdigest()[:12]
    assert cut == "a" * 51 + "-" + digest
    assert len(cut) == 64
    assert fhir_id("a" * 70 + "b") != fhir_id("a" * 70 + "c")


# Numbers, units and lists


def test_the_unit_may_sit_on_the_form_item() -> None:
    obs = the(emit(visit({"depth_cm": 12.0})), "Observation", "depth-cm")
    assert obs["valueQuantity"] == {
        "value": 12.0,
        "unit": "centimetre",
        "system": "http://unitsofmeasure.org",
        "code": "cm",
    }
    assert narrative(obs) == "Water depth at Below the footbridge: 12.0 centimetre."


def test_the_unit_in_the_fhir_block_comes_first() -> None:
    obs = the(emit(visit({"water_temp": 14.5})), "Observation", "water-temp")
    assert obs["valueQuantity"]["code"] == "Cel"
    assert obs["valueQuantity"]["unit"] == "degree Celsius"


def test_a_unit_with_no_plain_name_is_shown_by_its_code_and_an_item_by_its_id() -> None:
    obs = the(emit(visit({"turbidity": 3.0})), "Observation", "turbidity")
    assert obs["valueQuantity"]["unit"] == "[NTU]"
    assert narrative(obs) == "turbidity at Below the footbridge: 3.0 [NTU]."


def test_a_list_answer_reads_as_a_list() -> None:
    obs = the(emit(visit({"habitats": ["sand_banks", "stone_deposits"]})), "Observation")
    # Each value in the words of its coded display, parted by a semicolon.
    assert narrative(obs) == "Habitats at Below the footbridge: Sand banks; Stone deposits."
    assert len(obs["component"]) == 2


def test_a_refused_answer_names_its_item() -> None:
    items = [{**ITEMS[0], "unit": None}]
    with pytest.raises(FhirEmitError) as caught:
        emit_visit(visit(), test_sitting=None, emitted_at=EMITTED_AT, items=items)
    assert str(caught.value) == "item depth_cm: a number needs a UCUM unit in form.yaml"
    # A stored record is validated, which turns true into 1.0; a copy is not, so true survives.
    with pytest.raises(FhirEmitError) as caught:
        emit(visit().model_copy(update={"answers": {"depth_cm": True}}))
    assert str(caught.value) == (
        "item depth_cm: boolean answers are not allowed, use present/absent"
    )


# The qualification


def test_the_qualification_is_dated_from_the_sitting_passed_in() -> None:
    sitting = Sitting(
        sitting_id="test-sitting-0002",
        contributor_token=None,
        completed_at=datetime(2026, 9, 20, 9, 0, tzinfo=UTC),
        scores=scores(date(2026, 9, 20)),
    )
    practitioner = the(emit(visit(), sitting), "Practitioner")
    assert practitioner["qualification"][0]["period"]["start"] == "2026-09-20"
    without = the(emit(visit()), "Practitioner")
    assert without["qualification"][0]["period"]["start"] == "2026-09-01"


# The transaction and the structural check


def test_the_transaction_replaces_our_old_tag_and_keeps_everyone_elses() -> None:
    bundle = emit(visit())
    other = {"system": "https://example.org/other", "code": "kept"}
    for entry in bundle["entry"]:
        entry["resource"].setdefault("meta", {})["tag"] = [
            {"system": TAG_SYSTEM, "code": "an-old-run"},
            other,
        ]
    tx = to_transaction(bundle, tag_system=TAG_SYSTEM, tag_code="second-look")
    for entry in tx["entry"]:
        assert entry["resource"]["meta"]["tag"] == [
            other,
            {"system": TAG_SYSTEM, "code": "second-look"},
        ]
    assert check_bundle(tx) == []


def test_a_broken_reference_is_named_by_where_it_is() -> None:
    bundle = emit(visit())
    index, obs = next(
        (i, e["resource"])
        for i, e in enumerate(bundle["entry"])
        if e["resource"]["resourceType"] == "Observation"
    )
    obs["performer"] = [{"reference": "Practitioner/nobody"}]
    assert reference_problems(bundle) == [
        f"entry[{index}] Observation/{obs['id']}.performer[0]: "
        "reference Practitioner/nobody does not resolve in the Bundle"
    ]


def test_a_doubled_full_url_is_named_by_its_entry() -> None:
    bundle = emit(visit())
    last = len(bundle["entry"]) - 1
    bundle["entry"][last]["fullUrl"] = bundle["entry"][0]["fullUrl"]
    resource = bundle["entry"][last]["resource"]
    expected = (
        f"entry[{last}] {resource['resourceType']}/{resource['id']}: "
        f"fullUrl {bundle['entry'][0]['fullUrl']} appears twice"
    )
    assert expected in check_bundle(bundle)
