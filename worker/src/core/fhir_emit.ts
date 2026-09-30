// core/fhir_emit.py: one stored visit as FHIR R4 resources, byte for byte the same JSON as
// Python writes for the same inputs, proved by golden/fhir_emit.json. The tables (systems,
// displays, form items) come from content.json, so the two emitters read one source.

import CONTENT from "./core_content.json";
import { pyRound } from "./pyround";
import { sha256Hex } from "./sha256";
import { addDays, instant, type AnswerValue, type FeatureScore, type FormItem, type Json, type TestSitting, type VisitRecord } from "./types";

const FHIR = CONTENT.fhir;
export const REPO_URL: string = FHIR.repo_url;
export const FHIR_BASE = `${REPO_URL}/fhir`;
export const SL_SYSTEM: string = FHIR.sl_system;
export const OAH_SYSTEM: string = FHIR.oah_system;
export const OAH_LOCATION_PROFILE: string = FHIR.oah_location_profile;
export const OAH_OBSERVATION_PROFILE: string = FHIR.oah_observation_profile;
const UCUM_SYSTEM = "http://unitsofmeasure.org";
const SNOMED_SYSTEM = "http://snomed.info/sct";
const PROVENANCE_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/provenance-participant-type";
const QUESTIONNAIRE_TEST_URL = `${FHIR_BASE}/Questionnaire/sl-questionnaire-test`;
const QUESTIONNAIRE_CHECK_URL = `${FHIR_BASE}/Questionnaire/sl-questionnaire-check`;
const ID_SYSTEM_ORG = `${FHIR_BASE}/org`;
const ID_SYSTEM_DEVICE = `${FHIR_BASE}/device`;
const ID_SYSTEM_LOCATION = `${FHIR_BASE}/location-id`;
const ID_SYSTEM_CONTRIBUTOR = `${FHIR_BASE}/contributor-token`;
const ID_SYSTEM_QR = `${FHIR_BASE}/qr`;
const ID_SYSTEM_OBSERVATION = `${FHIR_BASE}/observation`;
export const ORG_ID = "sl-org";
export const DEVICE_ID = "sl-device";
const SL_DISPLAYS: Record<string, string> = FHIR.sl_displays;
const OAH_DISPLAYS: Record<string, string> = FHIR.oah_displays;
const UCUM_DISPLAYS: Record<string, string> = FHIR.ucum_displays;
const FEATURES: readonly string[] = CONTENT.rules.features_in_order;
const SCORE_VALID_DAYS: number = CONTENT.rules.score_valid_days;
export const FORM_ITEMS: FormItem[] = CONTENT.form_items as FormItem[];

type Resource = Record<string, Json>;

export class FhirEmitError extends Error {}

// Small builders

/** A FHIR id (letters, digits, dot, hyphen, 64 at most), deterministic in its parts. */
export function fhirId(...parts: string[]): string {
  const raw = parts.join("-");
  const cleaned = raw.replace(/[^A-Za-z0-9.-]/g, "-").replace(/^-+|-+$/g, "");
  if (cleaned.length <= 64) return cleaned;
  return `${cleaned.slice(0, 51)}-${sha256Hex(raw).slice(0, 12)}`;
}

function coding(system: string, code: string, display?: string): Resource {
  const out: Resource = { system, code };
  if (display !== undefined) out.display = display;
  return out;
}

export function slCoding(code: string): Resource {
  if (!(code in SL_DISPLAYS)) throw new FhirEmitError(`no Second Look display for ${code}`);
  return coding(SL_SYSTEM, code, SL_DISPLAYS[code]);
}

export function oahCoding(code: string): Resource {
  if (!(code in OAH_DISPLAYS)) throw new FhirEmitError(`no OneAquaHealth display for ${code}`);
  return coding(OAH_SYSTEM, code, OAH_DISPLAYS[code]);
}

function concept(c: Resource, text?: string | null): Resource {
  const out: Resource = { coding: [c] };
  if (text) out.text = text;
  return out;
}

const ref = (type: string, id: string): Resource => ({ reference: `${type}/${id}` });
const identifier = (system: string, value: string): Resource => ({ system, value });

/** xml.sax.saxutils.escape: ampersand first, then the angle brackets. */
export function escapeXml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** The human-readable summary. lang marks the words' own language (always English here) for a
 *  resource that states a language, as the validator and W3C ask (UPDATE_32 section 2). */
function narrative(text: string, lang: string | null = null): Resource {
  const attrs = lang ? ` lang="${lang}" xml:lang="${lang}"` : "";
  return { status: "generated", div: `<div xmlns="http://www.w3.org/1999/xhtml"${attrs}><p>${escapeXml(text)}</p></div>` };
}

/** How Python prints a float in an f-string: a whole number keeps its ".0". Every number the
 *  API stores is a float, so this is the honest reading of a JSON number here. */
export function pyFloat(value: number): string {
  if (Number.isInteger(value) && Math.abs(value) < 1e16) return `${value}.0`;
  return String(value);
}

function fullUrl(resource: Resource): string {
  return `${FHIR_BASE}/${resource.resourceType}/${resource.id}`;
}

const entry = (resource: Resource): Resource => ({ fullUrl: fullUrl(resource), resource });

export function codeForAnswer(value: string): Resource | null {
  if (value === "cant_tell") return slCoding("cant-tell");
  if (value in OAH_DISPLAYS) return oahCoding(value);
  const hyphenated = value.replace(/_/g, "-");
  if (hyphenated in SL_DISPLAYS) return slCoding(hyphenated);
  return null;
}

function valueConcept(value: string): Resource {
  const c = codeForAnswer(value);
  return c ? concept(c) : { text: value };
}

function itemCode(item: FormItem): Resource {
  const fhir = item.fhir;
  if (fhir.code_system === "sl") return slCoding(fhir.code);
  if (fhir.code_system === "oah") return oahCoding(fhir.code);
  throw new FhirEmitError(`item ${item.id}: unknown code_system ${JSON.stringify(fhir.code_system)}`);
}

function itemCategory(item: FormItem): Resource {
  return oahCoding(item.fhir.category || item.fhir.code);
}

/** core/fhir_emit.py _finding: what an answer to this item found, in a few words, or no words
 *  when the form has none. Our own feature code's display (Artificial bank), else the short
 *  phrase content/form.yaml keeps under fhir.finding. */
function finding(item: FormItem): string {
  const fhir = item.fhir;
  if (fhir.code_system === "sl") return String(slCoding(fhir.code).display);
  const phrase = fhir.finding;
  return typeof phrase === "string" ? phrase.trim() : "";
}

/** core/fhir_emit.py _item_label: the finding, then the app's own name in brackets. The app's
 *  name is its short name for the question (Bank Type), else the question, else the item's id.
 *  With no finding the app's name stands alone. */
function itemLabel(item: FormItem): string {
  const name = String(item.name || item.text || item.id);
  const found = finding(item);
  return found ? `${found} (${name})` : name;
}

/** core/fhir_emit.py _value_words: an answer in the words of its coded display (Can't tell),
 *  else as it was given. */
function valueWords(value: unknown): string {
  const c = typeof value === "string" ? codeForAnswer(value) : null;
  return c ? String(c.display) : String(value).replace(/_/g, " ");
}

function quantity(value: number, unit: string): Resource {
  return { value, unit: UCUM_DISPLAYS[unit] ?? unit, system: UCUM_SYSTEM, code: unit };
}

// Resources

function organization(): Resource {
  return {
    resourceType: "Organization",
    id: ORG_ID,
    text: narrative("Second Look project. Issues the observer test and keeps the record."),
    identifier: [identifier(ID_SYSTEM_ORG, "second-look")],
    name: "Second Look project",
    active: true,
  };
}

function device(version: string): Resource {
  return {
    resourceType: "Device",
    id: DEVICE_ID,
    text: narrative(`Second Look web app, version ${version}. Assembled this record.`),
    identifier: [identifier(ID_SYSTEM_DEVICE, "second-look-web")],
    status: "active",
    type: concept(slCoding("software")),
    deviceName: [{ name: "Second Look web app", type: "user-friendly-name" }],
    version: [{ value: version }],
  };
}

function location(opts: {
  locationId: string;
  identifier: string;
  name: string;
  kind: string;
  partOf?: string | null;
  position?: [number, number] | null;
  description?: string | null;
}): Resource {
  const out: Resource = {
    resourceType: "Location",
    id: opts.locationId,
    meta: { profile: [OAH_LOCATION_PROFILE] },
    text: narrative(`${opts.name}. A ${opts.kind} used in Second Look creek checks.`),
    identifier: [identifier(ID_SYSTEM_LOCATION, opts.identifier)],
    name: opts.name,
    mode: "instance",
    type: [concept(coding(SNOMED_SYSTEM, "420531007", "River"))],
  };
  if (opts.description) out.description = opts.description;
  if (opts.position) out.position = { latitude: opts.position[0], longitude: opts.position[1] };
  if (opts.partOf) out.partOf = ref("Location", opts.partOf);
  return out;
}

function locations(visit: VisitRecord): [Resource, Resource, Resource] {
  const spot = visit.spot;
  const creekId = fhirId("sl-loc", spot.creek_id);
  const reachId = fhirId("sl-loc", spot.reach_id);
  const spotId = fhirId("sl-loc", spot.spot_id);
  let position: [number, number] | null = null;
  if (spot.latitude !== null && spot.longitude !== null) {
    const digits = spot.coarse ? 2 : 5;
    position = [pyRound(spot.latitude, digits), pyRound(spot.longitude, digits)];
  }
  const creek = location({ locationId: creekId, identifier: spot.creek_id, name: spot.creek_name, kind: "creek" });
  const reach = location({ locationId: reachId, identifier: spot.reach_id, name: spot.reach_name, kind: "reach", partOf: creekId });
  const point = location({
    locationId: spotId,
    identifier: spot.spot_id,
    name: spot.spot_name,
    kind: "spot",
    partOf: reachId,
    position,
    description: position && spot.coarse ? "Coarse position, about 1 km." : null,
  });
  return [creek, reach, point];
}

export function practitionerId(contributorToken: string): string {
  return `sl-practitioner-${sha256Hex(contributorToken).slice(0, 12)}`;
}

function testedOn(visit: VisitRecord, sitting: TestSitting | null): string | null {
  const scores = sitting ? sitting.scores : visit.observer.scores;
  if (scores.length === 0) return null;
  return scores.map((s) => s.tested_on).reduce((a, b) => (b > a ? b : a));
}

function practitioner(visit: VisitRecord, tested: string | null): Resource {
  const token = visit.observer.contributor_token;
  let words = "Volunteer observer, known only by a random contributor token.";
  const qualification: Resource[] = [];
  if (tested !== null) {
    const validUntil = addDays(tested, SCORE_VALID_DAYS);
    words += ` Took the Second Look test on ${tested}.`;
    words += ` The score counts until ${validUntil}.`;
    qualification.push({
      code: concept(slCoding("second-look-test")),
      period: { start: tested, end: validUntil },
      issuer: ref("Organization", ORG_ID),
    });
  }
  const out: Resource = {
    resourceType: "Practitioner",
    id: practitionerId(token),
    text: narrative(words),
    identifier: [identifier(ID_SYSTEM_CONTRIBUTOR, practitionerId(token))],
    active: true,
  };
  if (qualification.length) out.qualification = qualification;
  return out;
}

function testResponse(sitting: TestSitting, pid: string): Resource {
  const byFeature = new Map(sitting.scores.map((s) => [s.feature, s]));
  const items: Resource[] = [];
  const words: string[] = [];
  for (const feature of FEATURES) {
    const score = byFeature.get(feature as FeatureScore["feature"]);
    if (!score) continue;
    items.push({ linkId: feature, item: [{ linkId: `${feature}.score`, answer: [{ valueInteger: score.correct }] }] });
    words.push(`${feature.replace(/_/g, " ")} ${score.correct} of ${score.total}`);
  }
  return {
    resourceType: "QuestionnaireResponse",
    id: fhirId("sl-qr-test", sitting.sitting_id),
    text: narrative(`Observer test sitting, scored by code: ${words.join(", ")}.`),
    identifier: identifier(ID_SYSTEM_QR, sitting.sitting_id),
    questionnaire: QUESTIONNAIRE_TEST_URL,
    status: "completed",
    authored: instant(sitting.completed_at),
    author: ref("Practitioner", pid),
    item: items,
  };
}

function qrAnswers(value: AnswerValue): Resource[] {
  if (typeof value === "boolean") return [{ valueBoolean: value }];
  if (typeof value === "number") return [{ valueDecimal: value }];
  if (typeof value === "string") {
    const c = codeForAnswer(value);
    return c ? [{ valueCoding: c }] : [{ valueString: value }];
  }
  const out: Resource[] = [];
  for (const element of value) out.push(...qrAnswers(element));
  return out;
}

function visitResponse(visit: VisitRecord, pid: string, items: FormItem[]): Resource {
  const qrItems: Resource[] = [];
  for (const item of items) {
    if (!(item.id in visit.answers) || item.type === "sliders") continue;
    const answers = qrAnswers(visit.answers[item.id]);
    if (answers.length) qrItems.push({ linkId: item.id, answer: answers });
  }
  return {
    resourceType: "QuestionnaireResponse",
    id: fhirId("sl-qr-visit", visit.visit_id),
    // The language the volunteer saw the questions in (UPDATE_32 section 2).
    language: visit.language ?? "en",
    text: narrative(
      `Creek check at ${visit.spot.spot_name} on ${instant(visit.answered_at)}, ${qrItems.length} items answered.` +
        ((visit.language ?? "en") === "en" ? "" : ` The questions were shown in language ${visit.language}.`),
      "en",
    ),
    identifier: identifier(ID_SYSTEM_QR, visit.visit_id),
    questionnaire: QUESTIONNAIRE_CHECK_URL,
    status: "completed",
    authored: instant(visit.answered_at),
    author: ref("Practitioner", pid),
    item: qrItems,
  };
}

function components(item: FormItem, values: string[]): Resource[] {
  const out: Resource[] = [];
  if (item.type === "multi") {
    for (const value of values) {
      const c = codeForAnswer(value);
      const code = c ? concept(c) : concept(itemCode(item), value);
      out.push({ code, valueCodeableConcept: concept(oahCoding("present")) });
    }
    return out;
  }
  for (const value of values) out.push({ code: concept(itemCode(item)), valueCodeableConcept: valueConcept(value) });
  return out;
}

function observation(
  visit: VisitRecord,
  item: FormItem,
  value: AnswerValue,
  pid: string,
  spotLocationId: string,
  visitQrId: string,
  score: FeatureScore | null,
): Resource | null {
  const fhir = item.fhir;
  // What was found, then the app's name for the question: Artificial bank (Bank Type).
  const label = itemLabel(item);
  let words = `${label} at ${visit.spot.spot_name}: `;
  let valuePart: Resource;
  if (typeof value === "boolean") {
    throw new FhirEmitError(`item ${item.id}: boolean answers are not allowed, use present/absent`);
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return null;
    valuePart = { component: components(item, value) };
    // A display may hold a comma (Riffles, rapids or falls), so a semicolon parts the list.
    words += value.map((v) => valueWords(v)).join("; ") + ".";
  } else if (typeof value === "number") {
    const unit = fhir.unit || item.unit;
    if (!unit) throw new FhirEmitError(`item ${item.id}: a number needs a UCUM unit in form.yaml`);
    valuePart = { valueQuantity: quantity(value, unit) };
    words += `${pyFloat(value)} ${UCUM_DISPLAYS[unit] ?? unit}.`;
  } else {
    valuePart = { valueCodeableConcept: valueConcept(value) };
    words += valueWords(value) + ".";
  }
  if (score !== null) {
    words += ` The observer scored ${score.correct} of ${score.total} on this feature, tested ${score.tested_on}.`;
  }
  const out: Resource = {
    resourceType: "Observation",
    id: fhirId("sl-obs", visit.visit_id, item.id),
    meta: { profile: [OAH_OBSERVATION_PROFILE] },
    text: narrative(words),
    identifier: [identifier(ID_SYSTEM_OBSERVATION, `${visit.visit_id}-${item.id}`)],
    status: "final",
    category: [concept(itemCategory(item))],
    code: concept(itemCode(item), label),
    subject: ref("Location", spotLocationId),
    effectiveDateTime: instant(visit.answered_at),
    performer: [ref("Practitioner", pid)],
    ...valuePart,
    derivedFrom: [ref("QuestionnaireResponse", visitQrId)],
  };
  return out;
}

// The form item the rating check asks about (core/followups.py).
const RATING_ITEM = "overall_rating";

/** core/fhir_emit.py _rating_change: the first and the kept overall rating, and the form item,
 *  when the two differ. Nothing when the rating was not answered. */
function ratingChange(visit: VisitRecord, items: FormItem[]): { first: string; kept: string; item: FormItem } | null {
  const item = items.find((i) => i.id === RATING_ITEM);
  const given = visit.answers[RATING_ITEM];
  if (item === undefined || typeof given !== "string") return null;
  const first = visit.first_rating || given;
  const kept = visit.final_rating || given;
  return first !== kept ? { first, kept, item } : null;
}

/** core/fhir_emit.py _rating_observation: the Observation of an overall rating the rating check
 *  changed. Its value is the rating kept; one component, coded first-rating, holds the rating
 *  given first. A rating that did not change adds no Observation and no component. */
function ratingObservation(visit: VisitRecord, item: FormItem, first: string, kept: string, pid: string, spotLocationId: string, visitQrId: string): Resource {
  if (item.fhir) throw new FhirEmitError(`item ${item.id}: a changed rating needs the item mapped to none`);
  // The app has no short name for this question, so the code's own display names the record.
  // The question itself is one step away, in the Questionnaire the visit response names.
  const label = String(slCoding("overall-rating").display);
  const words =
    `${label} at ${visit.spot.spot_name}: ${valueWords(kept)}.` +
    ` The first answer was ${valueWords(first)}.` +
    ` On the rating check the volunteer changed it to ${valueWords(kept)}.`;
  return {
    resourceType: "Observation",
    id: fhirId("sl-obs", visit.visit_id, item.id),
    meta: { profile: [OAH_OBSERVATION_PROFILE] },
    text: narrative(words),
    identifier: [identifier(ID_SYSTEM_OBSERVATION, `${visit.visit_id}-${item.id}`)],
    status: "final",
    code: concept(slCoding("overall-rating"), label),
    subject: ref("Location", spotLocationId),
    effectiveDateTime: instant(visit.answered_at),
    performer: [ref("Practitioner", pid)],
    valueCodeableConcept: valueConcept(kept),
    component: [{ code: concept(slCoding("first-rating")), valueCodeableConcept: valueConcept(first) }],
    derivedFrom: [ref("QuestionnaireResponse", visitQrId)],
  };
}

function provenance(visit: VisitRecord, observations: Resource[], pid: string, visitQrId: string, testQrId: string | null, emittedAt: string): Resource {
  const entities: Resource[] = [{ role: "source", what: ref("QuestionnaireResponse", visitQrId) }];
  // The last sentence names only the sources in entity (round 09 Q02).
  let sources = "The source is the visit.";
  if (testQrId) {
    entities.push({ role: "source", what: ref("QuestionnaireResponse", testQrId) });
    sources = "The sources are the visit and the observer test sitting.";
  }
  return {
    resourceType: "Provenance",
    id: fhirId("sl-provenance", visit.visit_id),
    text: narrative(
      `${observations.length} observations from one creek check, answered by the volunteer and assembled by the Second Look software. ${sources}`,
    ),
    target: observations.map((o) => ref("Observation", String(o.id))),
    recorded: instant(emittedAt),
    agent: [
      { type: concept(coding(PROVENANCE_TYPE_SYSTEM, "author")), who: ref("Practitioner", pid) },
      { type: concept(coding(PROVENANCE_TYPE_SYSTEM, "assembler")), who: ref("Device", DEVICE_ID) },
    ],
    entity: entities,
  };
}

/** One collection Bundle for one visit. Deterministic in its inputs. */
export function emitVisit(visit: VisitRecord, testSitting: TestSitting | null, emittedAt: string, items: FormItem[] = FORM_ITEMS): Resource {
  // A rating the rating check changed: the record answers the kept one and keeps the first in
  // its own Observation (ratingObservation). The stored answers stay as given.
  const change = ratingChange(visit, items);
  if (change !== null) visit = { ...visit, answers: { ...visit.answers, [RATING_ITEM]: change.kept } };
  const [creek, reach, spot] = locations(visit);
  const tested = testedOn(visit, testSitting);
  const person = practitioner(visit, tested);
  const pid = String(person.id);
  const testQr = testSitting ? testResponse(testSitting, pid) : null;
  const visitQr = visitResponse(visit, pid, items);
  const scores = new Map<string, FeatureScore>();
  for (const s of testSitting ? testSitting.scores : visit.observer.scores) scores.set(s.feature, s);
  const observations: Resource[] = [];
  for (const item of items) {
    if (!item.fhir || !(item.id in visit.answers)) continue;
    const obs = observation(visit, item, visit.answers[item.id], pid, String(spot.id), String(visitQr.id), scores.get(String(item.feature ?? "")) ?? null);
    if (obs !== null) observations.push(obs);
  }
  if (change !== null) observations.push(ratingObservation(visit, change.item, change.first, change.kept, pid, String(spot.id), String(visitQr.id)));
  const prov = provenance(visit, observations, pid, String(visitQr.id), testQr ? String(testQr.id) : null, emittedAt);
  const resources: Resource[] = [organization(), device(visit.software_version), creek, reach, spot, person];
  if (testQr) resources.push(testQr);
  resources.push(visitQr, ...observations, prov);
  return {
    resourceType: "Bundle",
    id: fhirId("sl-visit", visit.visit_id),
    type: "collection",
    timestamp: instant(emittedAt),
    entry: resources.map(entry),
  };
}

/** Structural problems a stored Bundle must not have. Empty list means it is fine. */
export function checkBundle(bundle: Resource): string[] {
  const problems: string[] = [];
  if (bundle.resourceType !== "Bundle") return ["not a Bundle"];
  const entries = (bundle.entry ?? []) as Resource[];
  // bdl-7: two entries with one fullUrl make every reference to it ambiguous.
  const seenUrls = new Set<string>();
  entries.forEach((e, i) => {
    const url = String(e.fullUrl ?? "");
    const r = (e.resource ?? {}) as Resource;
    if (url && seenUrls.has(url)) problems.push(`entry[${i}] ${String(r.resourceType)}/${r.id ?? e.fullUrl ?? "?"}: fullUrl ${url} appears twice`);
    seenUrls.add(url);
  });
  const keys = new Set<string>();
  for (const e of entries) {
    const r = (e.resource ?? {}) as Resource;
    if (bundle.type === "transaction") keys.add(String(e.fullUrl ?? ""));
    else {
      keys.add(`${r.resourceType}/${r.id}`);
      keys.add(String(e.fullUrl ?? ""));
    }
  }
  const walk = (node: Json, path: string) => {
    if (Array.isArray(node)) node.forEach((v, i) => walk(v, `${path}[${i}]`));
    else if (node && typeof node === "object") {
      for (const [key, value] of Object.entries(node)) {
        if (key === "reference" && typeof value === "string") {
          if (!keys.has(value)) problems.push(`${path}: reference ${value} does not resolve in the Bundle`);
        } else walk(value, `${path}.${key}`);
      }
    }
  };
  const observations: string[] = [];
  const provenances: Resource[] = [];
  entries.forEach((e, i) => {
    const r = (e.resource ?? {}) as Resource;
    const rtype = String(r.resourceType);
    const label = `entry[${i}] ${rtype}/${r.id ?? e.fullUrl ?? "?"}`;
    walk(r, label);
    if (rtype === "Observation") {
      observations.push(bundle.type !== "transaction" ? `Observation/${r.id}` : String(e.fullUrl ?? ""));
      for (const field of ["subject", "performer", "effectiveDateTime"]) if (!(field in r)) problems.push(`${label}: missing ${field}`);
      const profiles = ((r.meta as Resource | undefined)?.profile ?? []) as string[];
      if (!profiles.includes(OAH_OBSERVATION_PROFILE)) problems.push(`${label}: missing the OneAquaHealth indicator profile`);
      if (!Object.keys(r).some((k) => k.startsWith("value")) && !r.component) problems.push(`${label}: no value and no component`);
    } else if (rtype === "Provenance") provenances.push(r);
    else if (!["Organization", "Device", "Location", "Practitioner", "QuestionnaireResponse"].includes(rtype)) {
      problems.push(`${label}: unexpected resource type`);
    }
    if (rtype !== "Bundle" && !("text" in r)) problems.push(`${label}: no narrative`);
  });
  if (provenances.length !== 1) problems.push(`expected one Provenance, found ${provenances.length}`);
  else {
    const targets = new Set(((provenances[0].target ?? []) as Resource[]).map((t) => t.reference));
    for (const obs of observations) if (!targets.has(obs)) problems.push(`Provenance does not target ${obs}`);
  }
  return problems;
}
