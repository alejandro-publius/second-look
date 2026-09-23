"""The referral and the way back (Update 10 tier 1 item 2).

A pipe on the "worth testing" list becomes a FHIR ServiceRequest: its subject is the pipe's
Location, its reasons are the Observations of the two people who saw it running in dry weather,
its requester is our Organization. That part is real. It is computed from stored visits and from
nothing else, and it is never stored itself, so it can never be counted as a finding.

The way back is an example. A Specimen under their SpecimenOah profile and three Observations
under their indicator profile show how a laboratory result would return to the same record: they
point at the same ServiceRequest and the same Location. Their roadmap names microbial
metagenomics, so the panel is a small one of that kind. Every example resource carries the
`example` tag in meta.tag, opens its narrative with the word EXAMPLE, lives in no store and is
counted by nothing. The numbers in it are made up to show the shape of a result.

Pure. No file or network I/O, no clock: the caller passes every time.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import datetime
from typing import Any

from core.act import PipeCase
from core.fhir_emit import (
    FHIR_BASE,
    OAH_OBSERVATION_PROFILE,
    ORG_ID,
    SL_SYSTEM,
    SNOMED_SYSTEM,
    FhirEmitError,
    _concept,
    _entry,
    _identifier,
    _instant,
    _narrative,
    _quantity,
    _ref,
    entry_label,
    fhir_id,
    oah_coding,
    reference_problems,
    sl_coding,
)
from core.followups import PIPE_ITEMS

OAH_SPECIMEN_PROFILE = "http://hl7.eu/fhir/ig/oah/StructureDefinition/specimen-oah"
OBSERVATION_CATEGORY_SYSTEM = "http://terminology.hl7.org/CodeSystem/observation-category"
ID_SYSTEM_REFERRAL = f"{FHIR_BASE}/referral"
ID_SYSTEM_EXAMPLE = f"{FHIR_BASE}/example"
EXAMPLE_TAG_CODE = "example"
EXAMPLE_WORD = "EXAMPLE"
EXAMPLE_LAB_ID = "sl-example-lab"
EXAMPLE_LAB_ROLE_ID = "sl-example-lab-role"
# Water, from their SpecimenTypeOahVs.
SPECIMEN_TYPE_CODE = "11713004"
SPECIMEN_TYPE_DISPLAY = "Water"
SAMPLE_ML = 500.0

# The example panel: made up numbers, chosen to be unremarkable. (code, kind, value, unit)
EXAMPLE_PANEL: tuple[tuple[str, str, float | str, str | None], ...] = (
    ("lab-enterobacteriaceae-share", "quantity", 1.8, "%"),
    ("lab-hf183", "coded", "absent", None),
    ("lab-ecoli-cfu", "quantity", 120.0, "[CFU]/dL"),
)


def example_tag() -> dict[str, Any]:
    return sl_coding(EXAMPLE_TAG_CODE)


def is_example(resource: Mapping[str, Any]) -> bool:
    """True when a resource carries our example tag."""
    for tag in resource.get("meta", {}).get("tag", []):
        if tag.get("system") == SL_SYSTEM and tag.get("code") == EXAMPLE_TAG_CODE:
            return True
    return False


def _resources(bundle: Mapping[str, Any], resource_type: str) -> list[dict[str, Any]]:
    return [
        e["resource"]
        for e in bundle.get("entry", [])
        if e.get("resource", {}).get("resourceType") == resource_type
    ]


def _identifier_value(resource: Mapping[str, Any]) -> str:
    ident = resource.get("identifier")
    if isinstance(ident, list):
        ident = ident[0] if ident else {}
    return str(ident.get("value", "")) if isinstance(ident, dict) else ""


def _value_code(observation: Mapping[str, Any]) -> str | None:
    value = observation.get("valueCodeableConcept", {})
    codings = value.get("coding", []) if isinstance(value, dict) else []
    return str(codings[0].get("code")) if codings else None


def pipe_observations(bundle: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The Observations in one visit Bundle that report a pipe item present."""
    out: list[dict[str, Any]] = []
    for obs in _resources(bundle, "Observation"):
        ident = _identifier_value(obs)
        if any(ident.endswith(f"-{item}") for item in PIPE_ITEMS) and _value_code(obs) == "present":
            out.append(obs)
    return out


def _dedupe(resources: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for r in resources:
        key = f"{r['resourceType']}/{r['id']}"
        if key not in seen:
            seen.add(key)
            out.append(deepcopy(dict(r)))
    return out


def referral_bundle(
    pipe: PipeCase, bundles: Mapping[str, Mapping[str, Any]], *, emitted_at: datetime
) -> dict[str, Any]:
    """One collection Bundle: the ServiceRequest and everything it points at.

    `bundles` maps a visit id to its stored visit Bundle. A visit whose Bundle is missing from the
    store contributes nothing. At least one pipe Observation must remain, or there is no referral.
    """
    shared: list[dict[str, Any]] = []
    people: list[dict[str, Any]] = []
    responses: list[dict[str, Any]] = []
    reasons: list[dict[str, Any]] = []
    for visit_id in pipe.visit_ids:
        bundle = bundles.get(visit_id)
        if bundle is None:
            continue
        found = pipe_observations(bundle)
        if not found:
            continue
        if not shared:
            shared = _resources(bundle, "Organization") + _resources(bundle, "Location")
        people.extend(_resources(bundle, "Practitioner"))
        visit_qr_id = fhir_id("sl-qr-visit", visit_id)
        responses.extend(
            qr for qr in _resources(bundle, "QuestionnaireResponse") if qr["id"] == visit_qr_id
        )
        reasons.extend(found)
    if not reasons:
        raise FhirEmitError(f"pipe {pipe.spot_id}: no stored pipe Observation to refer to")
    spot_location_id = fhir_id("sl-loc", pipe.spot_id)
    if not any(loc["id"] == spot_location_id for loc in shared):
        raise FhirEmitError(f"pipe {pipe.spot_id}: the spot Location is not in the stored record")
    n_people = len(pipe.observers)
    words = (
        f"Referral to test the water coming out of the pipe at {pipe.spot_name}. "
        f"Reported running after dry weather by {n_people} people who both passed the pipe "
        f"feature, last on {pipe.last_seen.isoformat()}."
    )
    service_request: dict[str, Any] = {
        "resourceType": "ServiceRequest",
        "id": fhir_id("sl-referral", pipe.spot_id),
        "text": _narrative(words),
        "identifier": [_identifier(ID_SYSTEM_REFERRAL, pipe.spot_id)],
        "status": "active",
        "intent": "proposal",
        "priority": "routine",
        "code": _concept(sl_coding("test-pipe-outflow")),
        "subject": _ref("Location", spot_location_id),
        "authoredOn": _instant(emitted_at),
        "requester": _ref("Organization", ORG_ID),
        "reasonReference": [_ref("Observation", o["id"]) for o in reasons],
    }
    resources = _dedupe([*shared, *people, *responses, *reasons]) + [service_request]
    return {
        "resourceType": "Bundle",
        "id": fhir_id("sl-referral-bundle", pipe.spot_id),
        "type": "collection",
        "timestamp": _instant(emitted_at),
        "entry": [_entry(r) for r in resources],
    }


def _example_meta(profile: str | None = None) -> dict[str, Any]:
    meta: dict[str, Any] = {"tag": [example_tag()]}
    if profile:
        meta["profile"] = [profile]
    return meta


def _example_lab() -> dict[str, Any]:
    return {
        "resourceType": "Organization",
        "id": EXAMPLE_LAB_ID,
        "meta": _example_meta(),
        "text": _narrative(f"{EXAMPLE_WORD}. A made up laboratory, standing in for a real one."),
        "identifier": [_identifier(ID_SYSTEM_EXAMPLE, "example-lab")],
        "name": "Example laboratory (not a real laboratory)",
        "active": True,
    }


def _example_lab_role() -> dict[str, Any]:
    return {
        "resourceType": "PractitionerRole",
        "id": EXAMPLE_LAB_ROLE_ID,
        "meta": _example_meta(),
        "text": _narrative(
            f"{EXAMPLE_WORD}. The sampling role at the made up laboratory. Their Specimen profile "
            "asks for a PractitionerRole as the collector."
        ),
        "identifier": [_identifier(ID_SYSTEM_EXAMPLE, "example-lab-role")],
        "active": True,
        "organization": _ref("Organization", EXAMPLE_LAB_ID),
    }


def _example_specimen(
    spot_id: str, spot_location_id: str, request_id: str, collected_at: datetime
) -> dict[str, Any]:
    return {
        "resourceType": "Specimen",
        "id": fhir_id("sl-example-specimen", spot_id),
        "meta": _example_meta(OAH_SPECIMEN_PROFILE),
        "text": _narrative(
            f"{EXAMPLE_WORD}. A water sample taken at the pipe, {SAMPLE_ML:g} mL, "
            f"for the referral. No sample has been taken."
        ),
        "identifier": [_identifier(ID_SYSTEM_EXAMPLE, f"specimen-{spot_id}")],
        "status": "available",
        "type": _concept(
            {"system": SNOMED_SYSTEM, "code": SPECIMEN_TYPE_CODE, "display": SPECIMEN_TYPE_DISPLAY}
        ),
        "subject": _ref("Location", spot_location_id),
        "request": [_ref("ServiceRequest", request_id)],
        "collection": {
            "collector": _ref("PractitionerRole", EXAMPLE_LAB_ROLE_ID),
            "collectedDateTime": _instant(collected_at),
            "quantity": _quantity(SAMPLE_ML, "mL"),
        },
    }


def _example_observation(
    *,
    spot_id: str,
    spot_name: str,
    spot_location_id: str,
    request_id: str,
    specimen_id: str,
    code: str,
    kind: str,
    value: float | str,
    unit: str | None,
    reported_at: datetime,
) -> dict[str, Any]:
    display = sl_coding(code)["display"]
    out: dict[str, Any] = {
        "resourceType": "Observation",
        "id": fhir_id("sl-example-obs", spot_id, code),
        "meta": _example_meta(OAH_OBSERVATION_PROFILE),
        "identifier": [_identifier(ID_SYSTEM_EXAMPLE, f"obs-{spot_id}-{code}")],
        "basedOn": [_ref("ServiceRequest", request_id)],
        "status": "final",
        "category": [
            _concept(
                {
                    "system": OBSERVATION_CATEGORY_SYSTEM,
                    "code": "laboratory",
                    "display": "Laboratory",
                }
            )
        ],
        "code": _concept(sl_coding(code)),
        "subject": _ref("Location", spot_location_id),
        "effectiveDateTime": _instant(reported_at),
        "performer": [_ref("PractitionerRole", EXAMPLE_LAB_ROLE_ID)],
        "specimen": _ref("Specimen", specimen_id),
    }
    if kind == "quantity":
        if unit is None or not isinstance(value, int | float):
            raise FhirEmitError(f"example {code}: a quantity needs a number and a UCUM unit")
        out["valueQuantity"] = _quantity(float(value), unit)
        shown = f"{value:g} {out['valueQuantity']['unit']}"
    else:
        if not isinstance(value, str):
            raise FhirEmitError(f"example {code}: a coded value needs a code")
        out["valueCodeableConcept"] = _concept(oah_coding(value))
        shown = value
    out["text"] = _narrative(
        f"{EXAMPLE_WORD}. {display} at {spot_name}: {shown}. A made up number showing the shape "
        "of a laboratory result coming back to the same record."
    )
    return out


def example_lab_result(
    referral: Mapping[str, Any], *, collected_at: datetime, reported_at: datetime
) -> dict[str, Any]:
    """The referral Bundle plus an example Specimen and panel pointing back at it.

    Everything the referral held is kept so every reference still resolves; everything new is
    tagged as an example, and so is the Bundle itself.
    """
    requests = _resources(referral, "ServiceRequest")
    if len(requests) != 1:
        raise FhirEmitError("a referral Bundle holds exactly one ServiceRequest")
    request = requests[0]
    spot_id = _identifier_value(request)
    spot_location_id = request["subject"]["reference"].split("/", 1)[1]
    spot_name = next(
        (
            loc.get("name", spot_id)
            for loc in _resources(referral, "Location")
            if loc["id"] == spot_location_id
        ),
        spot_id,
    )
    specimen = _example_specimen(spot_id, spot_location_id, request["id"], collected_at)
    panel = [
        _example_observation(
            spot_id=spot_id,
            spot_name=str(spot_name),
            spot_location_id=spot_location_id,
            request_id=request["id"],
            specimen_id=specimen["id"],
            code=code,
            kind=kind,
            value=value,
            unit=unit,
            reported_at=reported_at,
        )
        for code, kind, value, unit in EXAMPLE_PANEL
    ]
    entries = [deepcopy(dict(e)) for e in referral.get("entry", [])]
    for resource in (_example_lab(), _example_lab_role(), specimen, *panel):
        entries.append(_entry(resource))
    return {
        "resourceType": "Bundle",
        "id": fhir_id("sl-example-result", spot_id),
        "meta": _example_meta(),
        "type": "collection",
        "timestamp": _instant(reported_at),
        "entry": entries,
    }


# Structural checks. The HL7 validator is the judge of the rest.


def check_referral_bundle(bundle: Mapping[str, Any]) -> list[str]:
    """A referral is real: one ServiceRequest, every reason a present pipe Observation in the
    Bundle, subject a Location in the Bundle, requester our Organization, and no example tag
    anywhere."""
    problems = reference_problems(bundle)
    entries = list(bundle.get("entry", []))
    requests = _resources(bundle, "ServiceRequest")
    if len(requests) != 1:
        problems.append(f"expected one ServiceRequest, found {len(requests)}")
        return problems
    request = requests[0]
    observations = {f"Observation/{o['id']}": o for o in _resources(bundle, "Observation")}
    reasons = request.get("reasonReference", [])
    if not reasons:
        problems.append("ServiceRequest has no reasonReference")
    for reason in reasons:
        obs = observations.get(reason.get("reference", ""))
        if obs is None:
            continue  # already reported by reference_problems
        if _value_code(obs) != "present":
            problems.append(f"reason {reason['reference']} does not report a pipe present")
        ident = _identifier_value(obs)
        if not any(ident.endswith(f"-{item}") for item in PIPE_ITEMS):
            problems.append(f"reason {reason['reference']} is not a pipe item")
    if request.get("requester", {}).get("reference") != f"Organization/{ORG_ID}":
        problems.append("ServiceRequest requester is not our Organization")
    if not str(request.get("subject", {}).get("reference", "")).startswith("Location/"):
        problems.append("ServiceRequest subject is not a Location")
    for i, entry in enumerate(entries):
        if is_example(entry.get("resource", {})):
            problems.append(f"{entry_label(i, entry)}: a referral must not carry an example")
    if is_example(bundle):
        problems.append("a referral Bundle must not carry the example tag")
    return problems


def check_example_bundle(bundle: Mapping[str, Any]) -> list[str]:
    """Every laboratory resource is tagged and says EXAMPLE, sits under the right profile, and
    points back at the one ServiceRequest, the Specimen and the same Location."""
    problems = reference_problems(bundle)
    if not is_example(bundle):
        problems.append("the example Bundle itself must carry the example tag")
    requests = _resources(bundle, "ServiceRequest")
    if len(requests) != 1:
        problems.append(f"expected one ServiceRequest, found {len(requests)}")
        return problems
    request_ref = f"ServiceRequest/{requests[0]['id']}"
    subject_ref = requests[0].get("subject", {}).get("reference")
    specimens = _resources(bundle, "Specimen")
    if len(specimens) != 1:
        problems.append(f"expected one Specimen, found {len(specimens)}")
        return problems
    specimen = specimens[0]
    specimen_ref = f"Specimen/{specimen['id']}"
    lab_observations = [o for o in _resources(bundle, "Observation") if "specimen" in o]
    if not lab_observations:
        problems.append("no laboratory Observation in the example")
    for i, entry in enumerate(bundle.get("entry", [])):
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType")
        label = entry_label(i, entry)
        laboratory = rtype in {"Specimen", "PractitionerRole"} or (
            rtype == "Organization" and resource.get("id") == EXAMPLE_LAB_ID
        )
        if rtype == "Observation" and "specimen" in resource:
            laboratory = True
        if not laboratory:
            continue
        if not is_example(resource):
            problems.append(f"{label}: laboratory resource without the example tag")
        div = resource.get("text", {}).get("div", "")
        if EXAMPLE_WORD not in div:
            problems.append(f"{label}: narrative does not say {EXAMPLE_WORD}")
    if OAH_SPECIMEN_PROFILE not in specimen.get("meta", {}).get("profile", []):
        problems.append("Specimen is not under their SpecimenOah profile")
    if specimen.get("subject", {}).get("reference") != subject_ref:
        problems.append("Specimen subject is not the ServiceRequest subject")
    collector = specimen.get("collection", {}).get("collector", {}).get("reference", "")
    if not collector.startswith("PractitionerRole/"):
        problems.append("Specimen collector is not a PractitionerRole")
    if "collectedDateTime" not in specimen.get("collection", {}):
        problems.append("Specimen has no collectedDateTime")
    for obs in lab_observations:
        label = f"Observation/{obs['id']}"
        if OAH_OBSERVATION_PROFILE not in obs.get("meta", {}).get("profile", []):
            problems.append(f"{label}: missing the OneAquaHealth indicator profile")
        if request_ref not in [b.get("reference") for b in obs.get("basedOn", [])]:
            problems.append(f"{label}: not basedOn the ServiceRequest")
        if obs.get("specimen", {}).get("reference") != specimen_ref:
            problems.append(f"{label}: does not point at the Specimen")
        if obs.get("subject", {}).get("reference") != subject_ref:
            problems.append(f"{label}: subject is not the same Location as the referral")
        if not any(k.startswith("value") for k in obs):
            problems.append(f"{label}: no value")
    return problems
