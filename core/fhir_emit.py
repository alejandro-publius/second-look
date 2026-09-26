"""Turn one stored visit into FHIR R4 resources (hard rules 10 and 11, docs/fhir_mapping.md).

Pure: the same visit, test sitting and emitted_at always give the same Bundle. The only file
read is content/form.yaml, once, for the item to code mapping. No network, no clock.

Shape (validated by the HL7 validator against the OneAquaHealth guide at the pinned commit):
Organization, Device, three nested Locations (creek, reach, spot), a pseudonymous Practitioner
with one dated qualification, the test sitting and the visit as QuestionnaireResponses, one
Observation per answered form item that has a fhir mapping, and one Provenance that ties every
Observation to the person and the software that produced it.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import yaml

from core.records import FEATURES, SCORE_VALID_DAYS, FeatureScore, TestSitting, VisitRecord

REPO_URL = "https://github.com/alejandro-publius/second-look"
FHIR_BASE = f"{REPO_URL}/fhir"
SL_SYSTEM = f"{FHIR_BASE}/CodeSystem/second-look"
OAH_SYSTEM = "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu"
OAH_LOCATION_PROFILE = "http://hl7.eu/fhir/ig/oah/StructureDefinition/location-oah"
OAH_OBSERVATION_PROFILE = "http://hl7.eu/fhir/ig/oah/StructureDefinition/observation-indicators-oah"
UCUM_SYSTEM = "http://unitsofmeasure.org"
SNOMED_SYSTEM = "http://snomed.info/sct"
PROVENANCE_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/provenance-participant-type"
QUESTIONNAIRE_TEST_URL = f"{FHIR_BASE}/Questionnaire/sl-questionnaire-test"
QUESTIONNAIRE_CHECK_URL = f"{FHIR_BASE}/Questionnaire/sl-questionnaire-check"

ID_SYSTEM_ORG = f"{FHIR_BASE}/org"
ID_SYSTEM_DEVICE = f"{FHIR_BASE}/device"
ID_SYSTEM_LOCATION = f"{FHIR_BASE}/location-id"
ID_SYSTEM_CONTRIBUTOR = f"{FHIR_BASE}/contributor-token"
ID_SYSTEM_QR = f"{FHIR_BASE}/qr"
ID_SYSTEM_OBSERVATION = f"{FHIR_BASE}/observation"

ORG_ID = "sl-org"
DEVICE_ID = "sl-device"

# Displays are the code system's own words (docs/fhir_mapping.md). A test checks this table
# against fhir/fsh/codesystem-second-look.fsh so the two never drift apart.
SL_DISPLAYS: dict[str, str] = {
    "artificial-bank": "Artificial bank",
    "dug-out-channel": "Dug-out channel",
    "invasive-plant": "Invasive plant",
    "pipe-running": "Pipe running",
    "cant-tell": "Can't tell",
    "second-look-test": "Second Look observer test",
    "software": "Second Look software",
    "flat": "Flat channel",
    "u-shape": "U shaped channel",
    "v-shape": "V shaped channel",
    "fast": "Fast flow",
    "slow": "Slow flow",
    "stagnant": "Stagnant or intermittent flow",
    "dry": "Dry channel",
    "sand-banks": "Sand banks",
    "sand-islands": "Sand islands",
    "stone-deposits": "Stone deposits",
    "riffles": "Riffles, rapids or falls",
    "aquatic-vegetation": "Aquatic vegetation",
    "fallen-trees": "Fallen trees",
    "fallen-branches": "Fallen branches",
    "leaf-deposits": "Deposits of fallen leaves",
    "good": "Good overall rating",
    "moderate": "Moderate overall rating",
    "poor": "Poor overall rating",
    # A rating the rating check changed (emit_visit): the Observation and its first rating.
    "overall-rating": "Overall rating",
    "first-rating": "First overall rating",
    # The referral and the way back (core/fhir_referral.py).
    "test-pipe-outflow": "Test the water coming out of this pipe",
    "example": "Example, not a real result",
    "lab-enterobacteriaceae-share": "Enterobacteriaceae, share of 16S reads",
    "lab-hf183": "Human faecal marker HF183",
    "lab-ecoli-cfu": "Escherichia coli, colony forming units",
}

# The OneAquaHealth temporary codes we use, with their displays. A test checks this table
# against the CodeSystem built from the guide at the pinned commit.
OAH_DISPLAYS: dict[str, str] = {
    "present": "Present",
    "absent": "Absent",
    "morophology": "Morphology of the streams",
    "hydrology": "Hydrology of the stream",
    "invasiveOrganisms": "Invasive invertebrate, plants and fish",
    "foam": "Foam/colour/smell",
    "LandUse": "Land use in the margins",
    "riparianVegetation": "Riparian vegetation",
    "trees": "Trees (height >3m)",
    "bushes": "Bushes (height (1.5-3m)",
    "herbaceous": "Herbaceous (height < 1.5m)",
}

UCUM_DISPLAYS: dict[str, str] = {
    "m": "metre",
    "cm": "centimetre",
    "Cel": "degree Celsius",
    "mL": "millilitre",
    "%": "percent",
    "[CFU]/dL": "colony forming units per 100 mL",
}

# The form item the rating check asks about (core/followups.py).
RATING_ITEM = "overall_rating"

_ID_BAD = re.compile(r"[^A-Za-z0-9.\-]")
_FORM_PATH = Path(__file__).resolve().parents[1] / "content" / "form.yaml"


class FhirEmitError(ValueError):
    """The visit cannot become a valid record."""


@cache
def _form_items_from_disk() -> tuple[dict[str, Any], ...]:
    with _FORM_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return tuple(dict(item) for item in data.get("items", []))


def form_items() -> tuple[dict[str, Any], ...]:
    """The form items from content/form.yaml, in the app's order."""
    return _form_items_from_disk()


# Small builders


def fhir_id(*parts: str) -> str:
    """A FHIR id (letters, digits, dot, hyphen, 64 at most), deterministic in its parts."""
    raw = "-".join(parts)
    cleaned = _ID_BAD.sub("-", raw).strip("-")
    if len(cleaned) <= 64:
        return cleaned
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{cleaned[:51]}-{digest}"


def _coding(system: str, code: str, display: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"system": system, "code": code}
    if display is not None:
        out["display"] = display
    return out


def sl_coding(code: str) -> dict[str, Any]:
    return _coding(SL_SYSTEM, code, SL_DISPLAYS[code])


def oah_coding(code: str) -> dict[str, Any]:
    return _coding(OAH_SYSTEM, code, OAH_DISPLAYS[code])


def _concept(coding: dict[str, Any], text: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"coding": [coding]}
    if text:
        out["text"] = text
    return out


def _ref(resource_type: str, resource_id: str) -> dict[str, str]:
    return {"reference": f"{resource_type}/{resource_id}"}


def _identifier(system: str, value: str) -> dict[str, str]:
    return {"system": system, "value": value}


def _narrative(text: str) -> dict[str, str]:
    return {
        "status": "generated",
        "div": f'<div xmlns="http://www.w3.org/1999/xhtml"><p>{escape(text)}</p></div>',
    }


def _instant(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    value = value.astimezone(UTC).replace(microsecond=0)
    return value.isoformat().replace("+00:00", "Z")


def _full_url(resource: Mapping[str, Any]) -> str:
    return f"{FHIR_BASE}/{resource['resourceType']}/{resource['id']}"


def _entry(resource: dict[str, Any]) -> dict[str, Any]:
    return {"fullUrl": _full_url(resource), "resource": resource}


def code_for_answer(value: str) -> dict[str, Any] | None:
    """The coding for one coded answer value, or None when we have no code for it."""
    if value == "cant_tell":
        return sl_coding("cant-tell")
    if value in OAH_DISPLAYS:
        return oah_coding(value)
    hyphenated = value.replace("_", "-")
    if hyphenated in SL_DISPLAYS:
        return sl_coding(hyphenated)
    return None


def _value_concept(value: str) -> dict[str, Any]:
    coding = code_for_answer(value)
    return _concept(coding) if coding else {"text": value}


def _item_code(item: Mapping[str, Any]) -> dict[str, Any]:
    fhir = item["fhir"]
    if fhir["code_system"] == "sl":
        return sl_coding(fhir["code"])
    if fhir["code_system"] == "oah":
        return oah_coding(fhir["code"])
    raise FhirEmitError(f"item {item['id']}: unknown code_system {fhir['code_system']!r}")


def _item_category(item: Mapping[str, Any]) -> dict[str, Any]:
    fhir = item["fhir"]
    return oah_coding(fhir.get("category") or fhir["code"])


def _quantity(value: float, unit: str) -> dict[str, Any]:
    return {
        "value": value,
        "unit": UCUM_DISPLAYS.get(unit, unit),
        "system": UCUM_SYSTEM,
        "code": unit,
    }


# Resources


def _organization() -> dict[str, Any]:
    return {
        "resourceType": "Organization",
        "id": ORG_ID,
        "text": _narrative("Second Look project. Issues the observer test and keeps the record."),
        "identifier": [_identifier(ID_SYSTEM_ORG, "second-look")],
        "name": "Second Look project",
        "active": True,
    }


def _device(version: str) -> dict[str, Any]:
    return {
        "resourceType": "Device",
        "id": DEVICE_ID,
        "text": _narrative(f"Second Look web app, version {version}. Assembled this record."),
        "identifier": [_identifier(ID_SYSTEM_DEVICE, "second-look-web")],
        "status": "active",
        "type": _concept(sl_coding("software")),
        "deviceName": [{"name": "Second Look web app", "type": "user-friendly-name"}],
        "version": [{"value": version}],
    }


def _location(
    *,
    location_id: str,
    identifier: str,
    name: str,
    kind: str,
    part_of: str | None = None,
    position: tuple[float, float] | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "resourceType": "Location",
        "id": location_id,
        "meta": {"profile": [OAH_LOCATION_PROFILE]},
        "text": _narrative(f"{name}. A {kind} used in Second Look creek checks."),
        "identifier": [_identifier(ID_SYSTEM_LOCATION, identifier)],
        "name": name,
        "mode": "instance",
        "type": [_concept(_coding(SNOMED_SYSTEM, "420531007", "River"))],
    }
    if description:
        out["description"] = description
    if position is not None:
        out["position"] = {"latitude": position[0], "longitude": position[1]}
    if part_of:
        out["partOf"] = _ref("Location", part_of)
    return out


def _locations(visit: VisitRecord) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    spot = visit.spot
    creek_id = fhir_id("sl-loc", spot.creek_id)
    reach_id = fhir_id("sl-loc", spot.reach_id)
    spot_id = fhir_id("sl-loc", spot.spot_id)
    position: tuple[float, float] | None = None
    if spot.latitude is not None and spot.longitude is not None:
        digits = 2 if spot.coarse else 5
        position = (round(spot.latitude, digits), round(spot.longitude, digits))
    creek = _location(
        location_id=creek_id, identifier=spot.creek_id, name=spot.creek_name, kind="creek"
    )
    reach = _location(
        location_id=reach_id,
        identifier=spot.reach_id,
        name=spot.reach_name,
        kind="reach",
        part_of=creek_id,
    )
    point = _location(
        location_id=spot_id,
        identifier=spot.spot_id,
        name=spot.spot_name,
        kind="spot",
        part_of=reach_id,
        position=position,
        description="Coarse position, about 1 km." if position and spot.coarse else None,
    )
    return creek, reach, point


def _practitioner_id(contributor_token: str) -> str:
    digest = hashlib.sha256(contributor_token.encode("utf-8")).hexdigest()[:12]
    return f"sl-practitioner-{digest}"


def _tested_on(visit: VisitRecord, test_sitting: TestSitting | None) -> date | None:
    scores: Sequence[FeatureScore] = test_sitting.scores if test_sitting else visit.observer.scores
    if not scores:
        return None
    return max(s.tested_on for s in scores)


def _practitioner(visit: VisitRecord, tested_on: date | None) -> dict[str, Any]:
    token = visit.observer.contributor_token
    words = "Volunteer observer, known only by a random contributor token."
    qualification: list[dict[str, Any]] = []
    if tested_on is not None:
        valid_until = tested_on + timedelta(days=SCORE_VALID_DAYS)
        words += f" Took the Second Look test on {tested_on.isoformat()}."
        words += f" The score counts until {valid_until.isoformat()}."
        qualification.append(
            {
                "code": _concept(sl_coding("second-look-test")),
                "period": {"start": tested_on.isoformat(), "end": valid_until.isoformat()},
                "issuer": _ref("Organization", ORG_ID),
            }
        )
    out: dict[str, Any] = {
        "resourceType": "Practitioner",
        "id": _practitioner_id(token),
        "text": _narrative(words),
        # The token itself is a credential: the public record carries only a hash of it.
        "identifier": [_identifier(ID_SYSTEM_CONTRIBUTOR, _practitioner_id(token))],
        "active": True,
    }
    if qualification:
        out["qualification"] = qualification
    return out


def _test_response(sitting: TestSitting, practitioner_id: str) -> dict[str, Any]:
    by_feature = {s.feature: s for s in sitting.scores}
    items: list[dict[str, Any]] = []
    words: list[str] = []
    for feature in FEATURES:
        score = by_feature.get(feature)
        if score is None:
            continue
        items.append(
            {
                "linkId": feature,
                "item": [
                    {"linkId": f"{feature}.score", "answer": [{"valueInteger": score.correct}]}
                ],
            }
        )
        words.append(f"{feature.replace('_', ' ')} {score.correct} of {score.total}")
    return {
        "resourceType": "QuestionnaireResponse",
        "id": fhir_id("sl-qr-test", sitting.sitting_id),
        "text": _narrative("Observer test sitting, scored by code: " + ", ".join(words) + "."),
        "identifier": _identifier(ID_SYSTEM_QR, sitting.sitting_id),
        "questionnaire": QUESTIONNAIRE_TEST_URL,
        "status": "completed",
        "authored": _instant(sitting.completed_at),
        "author": _ref("Practitioner", practitioner_id),
        "item": items,
    }


def _qr_answers(value: str | float | list[str]) -> list[dict[str, Any]]:
    if isinstance(value, bool):
        return [{"valueBoolean": value}]
    if isinstance(value, int | float):
        return [{"valueDecimal": value}]
    if isinstance(value, str):
        coding = code_for_answer(value)
        return [{"valueCoding": coding}] if coding else [{"valueString": value}]
    out: list[dict[str, Any]] = []
    for element in value:
        out.extend(_qr_answers(element))
    return out


def _visit_response(
    visit: VisitRecord, practitioner_id: str, items: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    qr_items: list[dict[str, Any]] = []
    for item in items:
        if item["id"] not in visit.answers or item.get("type") == "sliders":
            continue
        answers = _qr_answers(visit.answers[item["id"]])
        if answers:
            qr_items.append({"linkId": item["id"], "answer": answers})
    return {
        "resourceType": "QuestionnaireResponse",
        "id": fhir_id("sl-qr-visit", visit.visit_id),
        "text": _narrative(
            f"Creek check at {visit.spot.spot_name} on {_instant(visit.answered_at)}, "
            f"{len(qr_items)} items answered."
        ),
        "identifier": _identifier(ID_SYSTEM_QR, visit.visit_id),
        "questionnaire": QUESTIONNAIRE_CHECK_URL,
        "status": "completed",
        "authored": _instant(visit.answered_at),
        "author": _ref("Practitioner", practitioner_id),
        "item": qr_items,
    }


def _components(item: Mapping[str, Any], values: Sequence[str]) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    if item.get("type") == "multi":
        for value in values:
            coding = code_for_answer(value)
            code = _concept(coding) if coding else _concept(_item_code(item), value)
            components.append(
                {"code": code, "valueCodeableConcept": _concept(oah_coding("present"))}
            )
        return components
    for value in values:
        components.append(
            {"code": _concept(_item_code(item)), "valueCodeableConcept": _value_concept(value)}
        )
    return components


def _observation(
    visit: VisitRecord,
    item: Mapping[str, Any],
    value: str | float | list[str],
    *,
    practitioner_id: str,
    spot_location_id: str,
    visit_qr_id: str,
    score: FeatureScore | None,
) -> dict[str, Any] | None:
    """One Observation for one answered item, or None when a list answer is empty."""
    fhir = item["fhir"]
    words = f"{item.get('text', item['id'])} at {visit.spot.spot_name}: "
    value_part: dict[str, Any]
    if isinstance(value, bool):
        raise FhirEmitError(
            f"item {item['id']}: boolean answers are not allowed, use present/absent"
        )
    if isinstance(value, list):
        if not value:
            return None
        value_part = {"component": _components(item, value)}
        words += ", ".join(str(v).replace("_", " ") for v in value) + "."
    elif isinstance(value, int | float):
        unit = fhir.get("unit") or item.get("unit")
        if not unit:
            raise FhirEmitError(f"item {item['id']}: a number needs a UCUM unit in form.yaml")
        value_part = {"valueQuantity": _quantity(float(value), unit)}
        words += f"{value} {UCUM_DISPLAYS.get(unit, unit)}."
    else:
        value_part = {"valueCodeableConcept": _value_concept(value)}
        words += value.replace("_", " ") + "."
    if score is not None:
        words += (
            f" The observer scored {score.correct} of {score.total} on this feature,"
            f" tested {score.tested_on.isoformat()}."
        )
    out: dict[str, Any] = {
        "resourceType": "Observation",
        "id": fhir_id("sl-obs", visit.visit_id, item["id"]),
        "meta": {"profile": [OAH_OBSERVATION_PROFILE]},
        "text": _narrative(words),
        "identifier": [_identifier(ID_SYSTEM_OBSERVATION, f"{visit.visit_id}-{item['id']}")],
        "status": "final",
        "category": [_concept(_item_category(item))],
        "code": _concept(_item_code(item), item.get("text")),
        "subject": _ref("Location", spot_location_id),
        "effectiveDateTime": _instant(visit.answered_at),
        "performer": [_ref("Practitioner", practitioner_id)],
    }
    out.update(value_part)
    out["derivedFrom"] = [_ref("QuestionnaireResponse", visit_qr_id)]
    return out


def _rating_change(
    visit: VisitRecord, form: Sequence[Mapping[str, Any]]
) -> tuple[str, str, Mapping[str, Any]] | None:
    """The first and the kept overall rating, and the form item, when the two differ.

    The first is the rating the check stored as first (VisitRecord.first_rating), or the answer
    given. The kept one is the rating the rating check left (final_rating), or the answer given.
    Nothing when the rating was not answered: the record never adds a rating nobody gave.
    """
    item = next((i for i in form if i["id"] == RATING_ITEM), None)
    given = visit.answers.get(RATING_ITEM)
    if item is None or not isinstance(given, str):
        return None
    first = visit.first_rating or given
    kept = visit.final_rating or given
    return (first, kept, item) if first != kept else None


def _rating_observation(
    visit: VisitRecord,
    item: Mapping[str, Any],
    first: str,
    kept: str,
    *,
    practitioner_id: str,
    spot_location_id: str,
    visit_qr_id: str,
) -> dict[str, Any]:
    """The Observation of an overall rating the rating check changed.

    The form maps the overall rating to no Observation: the QuestionnaireResponse carries it.
    When the rating check changed it, the record adds this one. Its value is the rating the
    person kept, and one component, coded first-rating, holds the rating they gave first, so the
    change stays in the record. A rating that did not change adds no Observation and no
    component: the answer in the QuestionnaireResponse is then both the first and the kept one.
    Worker port: worker/src/core/fhir_emit.ts ratingObservation.
    """
    if item.get("fhir"):
        raise FhirEmitError(f"item {item['id']}: a changed rating needs the item mapped to none")
    words = (
        f"{item.get('text', item['id'])} at {visit.spot.spot_name}: {kept.replace('_', ' ')}."
        f" The first rating was {first.replace('_', ' ')}."
        f" On the rating check the volunteer changed it to {kept.replace('_', ' ')}."
    )
    return {
        "resourceType": "Observation",
        "id": fhir_id("sl-obs", visit.visit_id, item["id"]),
        "meta": {"profile": [OAH_OBSERVATION_PROFILE]},
        "text": _narrative(words),
        "identifier": [_identifier(ID_SYSTEM_OBSERVATION, f"{visit.visit_id}-{item['id']}")],
        "status": "final",
        "code": _concept(sl_coding("overall-rating"), item.get("text")),
        "subject": _ref("Location", spot_location_id),
        "effectiveDateTime": _instant(visit.answered_at),
        "performer": [_ref("Practitioner", practitioner_id)],
        "valueCodeableConcept": _value_concept(kept),
        "component": [
            {
                "code": _concept(sl_coding("first-rating")),
                "valueCodeableConcept": _value_concept(first),
            }
        ],
        "derivedFrom": [_ref("QuestionnaireResponse", visit_qr_id)],
    }


def _provenance(
    visit: VisitRecord,
    *,
    observations: Sequence[Mapping[str, Any]],
    practitioner_id: str,
    visit_qr_id: str,
    test_qr_id: str | None,
    emitted_at: datetime,
) -> dict[str, Any]:
    entities = [{"role": "source", "what": _ref("QuestionnaireResponse", visit_qr_id)}]
    # The last sentence names only the sources in entity (round 09 Q02).
    sources = "The source is the visit."
    if test_qr_id:
        entities.append({"role": "source", "what": _ref("QuestionnaireResponse", test_qr_id)})
        sources = "The sources are the visit and the observer test sitting."
    return {
        "resourceType": "Provenance",
        "id": fhir_id("sl-provenance", visit.visit_id),
        "text": _narrative(
            f"{len(observations)} observations from one creek check, answered by the volunteer "
            f"and assembled by the Second Look software. {sources}"
        ),
        "target": [_ref("Observation", o["id"]) for o in observations],
        "recorded": _instant(emitted_at),
        "agent": [
            {
                "type": _concept(_coding(PROVENANCE_TYPE_SYSTEM, "author")),
                "who": _ref("Practitioner", practitioner_id),
            },
            {
                "type": _concept(_coding(PROVENANCE_TYPE_SYSTEM, "assembler")),
                "who": _ref("Device", DEVICE_ID),
            },
        ],
        "entity": entities,
    }


# Public functions


def emit_visit(
    visit: VisitRecord,
    *,
    test_sitting: TestSitting | None,
    emitted_at: datetime,
    items: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """One collection Bundle for one visit. Deterministic in its inputs.

    `items` defaults to content/form.yaml; tests may pass their own.
    """
    form = tuple(items) if items is not None else form_items()
    # A rating the rating check changed: the record answers the kept one and keeps the first in
    # its own Observation (_rating_observation). The stored answers stay as given.
    change = _rating_change(visit, form)
    if change is not None:
        visit = visit.model_copy(update={"answers": {**visit.answers, RATING_ITEM: change[1]}})
    creek, reach, spot = _locations(visit)
    tested_on = _tested_on(visit, test_sitting)
    practitioner = _practitioner(visit, tested_on)
    practitioner_id = practitioner["id"]
    test_qr = _test_response(test_sitting, practitioner_id) if test_sitting else None
    visit_qr = _visit_response(visit, practitioner_id, form)
    scores: dict[str, FeatureScore] = {
        s.feature: s for s in (test_sitting.scores if test_sitting else visit.observer.scores)
    }
    observations: list[dict[str, Any]] = []
    for item in form:
        if not item.get("fhir") or item["id"] not in visit.answers:
            continue
        obs = _observation(
            visit,
            item,
            visit.answers[item["id"]],
            practitioner_id=practitioner_id,
            spot_location_id=spot["id"],
            visit_qr_id=visit_qr["id"],
            score=scores.get(str(item.get("feature") or "")),
        )
        if obs is not None:
            observations.append(obs)
    if change is not None:
        first, kept, rating_item = change
        observations.append(
            _rating_observation(
                visit,
                rating_item,
                first,
                kept,
                practitioner_id=practitioner_id,
                spot_location_id=spot["id"],
                visit_qr_id=visit_qr["id"],
            )
        )
    provenance = _provenance(
        visit,
        observations=observations,
        practitioner_id=practitioner_id,
        visit_qr_id=visit_qr["id"],
        test_qr_id=test_qr["id"] if test_qr else None,
        emitted_at=emitted_at,
    )
    resources: list[dict[str, Any]] = [
        _organization(),
        _device(visit.software_version),
        creek,
        reach,
        spot,
        practitioner,
    ]
    if test_qr:
        resources.append(test_qr)
    resources.append(visit_qr)
    resources.extend(observations)
    resources.append(provenance)
    return {
        "resourceType": "Bundle",
        "id": fhir_id("sl-visit", visit.visit_id),
        "type": "collection",
        "timestamp": _instant(emitted_at),
        "entry": [_entry(r) for r in resources],
    }


def _rewrite_references(node: Any, urn_for: Mapping[str, str]) -> Any:
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key == "reference" and isinstance(value, str) and value in urn_for:
                out[key] = urn_for[value]
            else:
                out[key] = _rewrite_references(value, urn_for)
        return out
    if isinstance(node, list):
        return [_rewrite_references(v, urn_for) for v in node]
    return node


def _first_identifier(resource: Mapping[str, Any]) -> tuple[str, str] | None:
    ident = resource.get("identifier")
    if isinstance(ident, list):
        ident = ident[0] if ident else None
    if not isinstance(ident, dict) or "system" not in ident or "value" not in ident:
        return None
    return str(ident["system"]), str(ident["value"])


def _if_none_exist(resource: Mapping[str, Any], by_key: Mapping[str, Mapping[str, Any]]) -> str:
    """The conditional create search for one resource, as "Type?params" (the form HAPI accepts).

    Everything we emit has an identifier except Provenance, which has none in R4. The
    Provenance is found through the identifier of its first target Observation instead.
    """
    rtype = resource["resourceType"]
    ident = _first_identifier(resource)
    if ident is not None:
        return f"{rtype}?identifier={ident[0]}|{ident[1]}"
    if resource["resourceType"] == "Provenance":
        for target in resource.get("target", []):
            target_resource = by_key.get(target.get("reference", ""))
            if target_resource is None:
                continue
            target_ident = _first_identifier(target_resource)
            if target_ident is not None:
                return f"{rtype}?target:Observation.identifier={target_ident[0]}|{target_ident[1]}"
    raise FhirEmitError(
        f"{resource['resourceType']}/{resource.get('id')}: no identifier for a conditional create"
    )


def to_transaction(bundle: Mapping[str, Any], *, tag_system: str, tag_code: str) -> dict[str, Any]:
    """A transaction Bundle of conditional creates, every resource tagged as ours (hard rule 10).

    Entry fullUrls are deterministic urn:uuid values and every internal reference points at
    them, so any server can rewrite them to its own ids. Resource ids are dropped because a
    conditional create lets the server pick the id; the identifiers carry our keys.
    """
    entries = list(bundle.get("entry", []))
    by_key: dict[str, Mapping[str, Any]] = {}
    urn_for: dict[str, str] = {}
    for entry in entries:
        resource = entry["resource"]
        key = f"{resource['resourceType']}/{resource['id']}"
        by_key[key] = resource
        seed = entry.get("fullUrl") or f"{FHIR_BASE}/{key}"
        urn_for[key] = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, seed)}"
    out_entries: list[dict[str, Any]] = []
    for entry in entries:
        original = entry["resource"]
        key = f"{original['resourceType']}/{original['id']}"
        resource = _rewrite_references(deepcopy(original), urn_for)
        resource.pop("id", None)
        meta = resource.setdefault("meta", {})
        tags = [t for t in meta.get("tag", []) if t.get("system") != tag_system]
        tags.append({"system": tag_system, "code": tag_code})
        meta["tag"] = tags
        out_entries.append(
            {
                "fullUrl": urn_for[key],
                "resource": resource,
                "request": {
                    "method": "POST",
                    "url": original["resourceType"],
                    "ifNoneExist": _if_none_exist(original, by_key),
                },
            }
        )
    return {
        "resourceType": "Bundle",
        "id": f"{bundle.get('id', 'sl-bundle')}-transaction",
        "type": "transaction",
        "entry": out_entries,
    }


def entry_label(index: int, entry: Mapping[str, Any]) -> str:
    """How a structural problem names its resource: "entry[3] Observation/sl-obs-1"."""
    resource = entry.get("resource", {})
    rtype = resource.get("resourceType")
    return f"entry[{index}] {rtype}/{resource.get('id', entry.get('fullUrl', '?'))}"


def bundle_keys(bundle: Mapping[str, Any]) -> set[str]:
    """Every string a reference inside this Bundle may point at."""
    keys: set[str] = set()
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if bundle.get("type") == "transaction":
            keys.add(entry.get("fullUrl", ""))
        else:
            keys.add(f"{resource.get('resourceType')}/{resource.get('id')}")
            keys.add(entry.get("fullUrl", ""))
    return keys


def reference_problems(bundle: Mapping[str, Any]) -> list[str]:
    """Every reference that does not resolve inside the Bundle, named by its path."""
    keys = bundle_keys(bundle)
    problems: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "reference" and isinstance(value, str):
                    if value not in keys:
                        problems.append(f"{path}: reference {value} does not resolve in the Bundle")
                else:
                    walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{path}[{i}]")

    for i, entry in enumerate(bundle.get("entry", [])):
        walk(entry.get("resource", {}), entry_label(i, entry))
    return problems


def check_bundle(bundle: Mapping[str, Any]) -> list[str]:
    """Structural problems a stored Bundle must not have. Empty list means it is fine.

    Every fullUrl is unique, every reference resolves inside the Bundle, there is exactly one
    Provenance and it targets
    every Observation, and every Observation carries the profile, a subject, a performer and a
    time. The HL7 validator is the judge of the rest.
    """
    problems: list[str] = []
    if bundle.get("resourceType") != "Bundle":
        return ["not a Bundle"]
    entries = list(bundle.get("entry", []))
    problems.extend(reference_problems(bundle))
    # bdl-7: two entries with one fullUrl make every reference to it ambiguous.
    seen_urls: set[str] = set()
    for i, entry in enumerate(entries):
        url = str(entry.get("fullUrl", ""))
        if url and url in seen_urls:
            problems.append(f"{entry_label(i, entry)}: fullUrl {url} appears twice")
        seen_urls.add(url)

    observations: list[str] = []
    provenances: list[Mapping[str, Any]] = []
    for i, entry in enumerate(entries):
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType")
        label = entry_label(i, entry)
        if rtype == "Observation":
            observations.append(
                f"Observation/{resource.get('id')}"
                if bundle.get("type") != "transaction"
                else entry.get("fullUrl", "")
            )
            for field in ("subject", "performer", "effectiveDateTime"):
                if field not in resource:
                    problems.append(f"{label}: missing {field}")
            if OAH_OBSERVATION_PROFILE not in resource.get("meta", {}).get("profile", []):
                problems.append(f"{label}: missing the OneAquaHealth indicator profile")
            if not any(k.startswith("value") for k in resource) and not resource.get("component"):
                problems.append(f"{label}: no value and no component")
        elif rtype == "Provenance":
            provenances.append(resource)
        elif rtype not in {
            "Organization",
            "Device",
            "Location",
            "Practitioner",
            "QuestionnaireResponse",
        }:
            problems.append(f"{label}: unexpected resource type")
        if rtype != "Bundle" and "text" not in resource:
            problems.append(f"{label}: no narrative")
    if len(provenances) != 1:
        problems.append(f"expected one Provenance, found {len(provenances)}")
    else:
        targets = {t.get("reference") for t in provenances[0].get("target", [])}
        for obs in observations:
            if obs not in targets:
                problems.append(f"Provenance does not target {obs}")
    return problems
