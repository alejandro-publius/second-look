// core/fhir_referral.py: the referral and the way back. A pipe on the worth testing list becomes a
// ServiceRequest, real and computed from stored visits; an example Specimen and panel show how a
// laboratory result would return to the same record, tagged example and never counted.

import CONTENT from "../content.json";
import type { PipeCase } from "./act";
import { FHIR_BASE, ORG_ID, SL_SYSTEM, escapeXml, fhirId, oahCoding, slCoding, OAH_OBSERVATION_PROFILE } from "./fhir_emit";
import { instant, type Json } from "./types";

type Resource = Record<string, Json>;
type Bundle = Resource;

export const OAH_SPECIMEN_PROFILE = "http://hl7.eu/fhir/ig/oah/StructureDefinition/specimen-oah";
const OBSERVATION_CATEGORY_SYSTEM = "http://terminology.hl7.org/CodeSystem/observation-category";
const SNOMED_SYSTEM = "http://snomed.info/sct";
const UCUM_SYSTEM = "http://unitsofmeasure.org";
const ID_SYSTEM_REFERRAL = `${FHIR_BASE}/referral`;
const ID_SYSTEM_EXAMPLE = `${FHIR_BASE}/example`;
export const EXAMPLE_TAG_CODE = "example";
const EXAMPLE_WORD = "EXAMPLE";
const EXAMPLE_LAB_ID = "sl-example-lab";
const EXAMPLE_LAB_ROLE_ID = "sl-example-lab-role";
const SPECIMEN_TYPE_CODE = "11713004";
const SPECIMEN_TYPE_DISPLAY = "Water";
const SAMPLE_ML = 500.0;
const PIPE_ITEMS: readonly string[] = CONTENT.rules.pipe_items;
const UCUM_DISPLAYS: Record<string, string> = CONTENT.fhir.ucum_displays;

// The example panel: made up numbers, chosen to be unremarkable. (code, kind, value, unit)
const EXAMPLE_PANEL: [string, "quantity" | "coded", number | string, string | null][] = [
  ["lab-enterobacteriaceae-share", "quantity", 1.8, "%"],
  ["lab-hf183", "coded", "absent", null],
  ["lab-ecoli-cfu", "quantity", 120.0, "[CFU]/dL"],
];

export class ReferralError extends Error {}

const ref = (type: string, id: string): Resource => ({ reference: `${type}/${id}` });
const identifier = (system: string, value: string): Resource => ({ system, value });
const concept = (c: Resource, text?: string): Resource => (text ? { coding: [c], text } : { coding: [c] });
const narrative = (text: string): Resource => ({ status: "generated", div: `<div xmlns="http://www.w3.org/1999/xhtml"><p>${escapeXml(text)}</p></div>` });
const entry = (r: Resource): Resource => ({ fullUrl: `${FHIR_BASE}/${r.resourceType}/${r.id}`, resource: r });
const quantity = (value: number, unit: string): Resource => ({ value, unit: UCUM_DISPLAYS[unit] ?? unit, system: UCUM_SYSTEM, code: unit });

export function exampleTag(): Resource {
  return slCoding(EXAMPLE_TAG_CODE);
}

export function isExample(resource: Resource): boolean {
  const tags = ((resource.meta as Resource | undefined)?.tag ?? []) as Resource[];
  return tags.some((t) => t.system === SL_SYSTEM && t.code === EXAMPLE_TAG_CODE);
}

function resources(bundle: Bundle, type: string): Resource[] {
  return ((bundle.entry ?? []) as Resource[]).map((e) => e.resource as Resource).filter((r) => r && r.resourceType === type);
}

function identifierValue(resource: Resource): string {
  let ident = resource.identifier;
  if (Array.isArray(ident)) ident = (ident[0] ?? {}) as Json;
  return ident && typeof ident === "object" ? String((ident as Resource).value ?? "") : "";
}

function valueCode(observation: Resource): string | null {
  const value = observation.valueCodeableConcept as Resource | undefined;
  const codings = (value?.coding ?? []) as Resource[];
  return codings.length ? String(codings[0].code) : null;
}

export function pipeObservations(bundle: Bundle): Resource[] {
  return resources(bundle, "Observation").filter((obs) => {
    const ident = identifierValue(obs);
    return PIPE_ITEMS.some((item) => ident.endsWith(`-${item}`)) && valueCode(obs) === "present";
  });
}

function dedupe(list: Resource[]): Resource[] {
  const seen = new Set<string>();
  const out: Resource[] = [];
  for (const r of list) {
    const key = `${r.resourceType}/${r.id}`;
    if (!seen.has(key)) {
      seen.add(key);
      out.push(structuredClone(r));
    }
  }
  return out;
}

/** One collection Bundle: the ServiceRequest and everything it points at. */
export function referralBundle(pipe: PipeCase, bundles: Record<string, Bundle>, emittedAt: string): Bundle {
  let shared: Resource[] = [];
  const people: Resource[] = [];
  const responses: Resource[] = [];
  const reasons: Resource[] = [];
  for (const visitId of pipe.visit_ids) {
    const bundle = bundles[visitId];
    if (!bundle) continue;
    const found = pipeObservations(bundle);
    if (found.length === 0) continue;
    if (shared.length === 0) shared = [...resources(bundle, "Organization"), ...resources(bundle, "Location")];
    people.push(...resources(bundle, "Practitioner"));
    const visitQrId = fhirId("sl-qr-visit", visitId);
    responses.push(...resources(bundle, "QuestionnaireResponse").filter((qr) => qr.id === visitQrId));
    reasons.push(...found);
  }
  if (reasons.length === 0) throw new ReferralError(`pipe ${pipe.spot_id}: no stored pipe Observation to refer to`);
  const spotLocationId = fhirId("sl-loc", pipe.spot_id);
  if (!shared.some((loc) => loc.id === spotLocationId)) throw new ReferralError(`pipe ${pipe.spot_id}: the spot Location is not in the stored record`);
  const words =
    `Referral to test the water coming out of the pipe at ${pipe.spot_name}. ` +
    `Reported running after dry weather by ${pipe.observers.length} people who both passed the pipe feature, last on ${pipe.last_seen}.`;
  const serviceRequest: Resource = {
    resourceType: "ServiceRequest",
    id: fhirId("sl-referral", pipe.spot_id),
    text: narrative(words),
    identifier: [identifier(ID_SYSTEM_REFERRAL, pipe.spot_id)],
    status: "active",
    intent: "proposal",
    priority: "routine",
    code: concept(slCoding("test-pipe-outflow")),
    subject: ref("Location", spotLocationId),
    authoredOn: instant(emittedAt),
    requester: ref("Organization", ORG_ID),
    reasonReference: reasons.map((o) => ref("Observation", String(o.id))),
  };
  const all = [...dedupe([...shared, ...people, ...responses, ...reasons]), serviceRequest];
  return { resourceType: "Bundle", id: fhirId("sl-referral-bundle", pipe.spot_id), type: "collection", timestamp: instant(emittedAt), entry: all.map(entry) };
}

function exampleMeta(profile?: string): Resource {
  const meta: Resource = { tag: [exampleTag()] };
  if (profile) meta.profile = [profile];
  return meta;
}

function exampleLab(): Resource {
  return {
    resourceType: "Organization",
    id: EXAMPLE_LAB_ID,
    meta: exampleMeta(),
    text: narrative(`${EXAMPLE_WORD}. A made up laboratory, standing in for a real one.`),
    identifier: [identifier(ID_SYSTEM_EXAMPLE, "example-lab")],
    name: "Example laboratory (not a real laboratory)",
    active: true,
  };
}

function exampleLabRole(): Resource {
  return {
    resourceType: "PractitionerRole",
    id: EXAMPLE_LAB_ROLE_ID,
    meta: exampleMeta(),
    text: narrative(`${EXAMPLE_WORD}. The sampling role at the made up laboratory. Their Specimen profile asks for a PractitionerRole as the collector.`),
    identifier: [identifier(ID_SYSTEM_EXAMPLE, "example-lab-role")],
    active: true,
    organization: ref("Organization", EXAMPLE_LAB_ID),
  };
}

function exampleSpecimen(spotId: string, spotLocationId: string, requestId: string, collectedAt: string): Resource {
  return {
    resourceType: "Specimen",
    id: fhirId("sl-example-specimen", spotId),
    meta: exampleMeta(OAH_SPECIMEN_PROFILE),
    text: narrative(`${EXAMPLE_WORD}. A water sample taken at the pipe, ${SAMPLE_ML} mL, for the referral. No sample has been taken.`),
    identifier: [identifier(ID_SYSTEM_EXAMPLE, `specimen-${spotId}`)],
    status: "available",
    type: concept({ system: SNOMED_SYSTEM, code: SPECIMEN_TYPE_CODE, display: SPECIMEN_TYPE_DISPLAY }),
    subject: ref("Location", spotLocationId),
    request: [ref("ServiceRequest", requestId)],
    collection: { collector: ref("PractitionerRole", EXAMPLE_LAB_ROLE_ID), collectedDateTime: instant(collectedAt), quantity: quantity(SAMPLE_ML, "mL") },
  };
}

/** Python's "%g" for the example numbers: 1.8 stays 1.8, 120.0 becomes 120, 500.0 becomes 500. */
function gFormat(value: number): string {
  return String(Number(value.toPrecision(6)));
}

function exampleObservation(spotId: string, spotName: string, spotLocationId: string, requestId: string, specimenId: string, code: string, kind: "quantity" | "coded", value: number | string, unit: string | null, reportedAt: string): Resource {
  const display = String(slCoding(code).display);
  const out: Resource = {
    resourceType: "Observation",
    id: fhirId("sl-example-obs", spotId, code),
    meta: exampleMeta(OAH_OBSERVATION_PROFILE),
    identifier: [identifier(ID_SYSTEM_EXAMPLE, `obs-${spotId}-${code}`)],
    basedOn: [ref("ServiceRequest", requestId)],
    status: "final",
    category: [concept({ system: OBSERVATION_CATEGORY_SYSTEM, code: "laboratory", display: "Laboratory" })],
    code: concept(slCoding(code)),
    subject: ref("Location", spotLocationId),
    effectiveDateTime: instant(reportedAt),
    performer: [ref("PractitionerRole", EXAMPLE_LAB_ROLE_ID)],
    specimen: ref("Specimen", specimenId),
  };
  let shown: string;
  if (kind === "quantity") {
    if (unit === null || typeof value !== "number") throw new ReferralError(`example ${code}: a quantity needs a number and a UCUM unit`);
    const q = quantity(value, unit);
    out.valueQuantity = q;
    shown = `${gFormat(value)} ${q.unit}`;
  } else {
    if (typeof value !== "string") throw new ReferralError(`example ${code}: a coded value needs a code`);
    out.valueCodeableConcept = concept(oahCoding(value));
    shown = value;
  }
  out.text = narrative(`${EXAMPLE_WORD}. ${display} at ${spotName}: ${shown}. A made up number showing the shape of a laboratory result coming back to the same record.`);
  return out;
}

/** The referral Bundle plus an example Specimen and panel pointing back at it. */
export function exampleLabResult(referral: Bundle, collectedAt: string, reportedAt: string): Bundle {
  const requests = resources(referral, "ServiceRequest");
  if (requests.length !== 1) throw new ReferralError("a referral Bundle holds exactly one ServiceRequest");
  const request = requests[0];
  const spotId = identifierValue(request);
  const spotLocationId = String((request.subject as Resource).reference).split("/", 2)[1];
  const spotName = String(resources(referral, "Location").find((loc) => loc.id === spotLocationId)?.name ?? spotId);
  const specimen = exampleSpecimen(spotId, spotLocationId, String(request.id), collectedAt);
  const panel = EXAMPLE_PANEL.map(([code, kind, value, unit]) =>
    exampleObservation(spotId, spotName, spotLocationId, String(request.id), String(specimen.id), code, kind, value, unit, reportedAt),
  );
  const entries = ((referral.entry ?? []) as Resource[]).map((e) => structuredClone(e));
  for (const r of [exampleLab(), exampleLabRole(), specimen, ...panel]) entries.push(entry(r));
  return { resourceType: "Bundle", id: fhirId("sl-example-result", spotId), meta: exampleMeta(), type: "collection", timestamp: instant(reportedAt), entry: entries };
}
