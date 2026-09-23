// The guided creek check on the Worker (Update 10 answer A3): drafts, follow-ups, finalize, the
// spot view and the quick check, over D1. A port of apps/api/check.py. Every stored answer is the
// human's and comes from a fixed set of values; no free text is ever stored. Follow-up questions
// are chosen by core/followups.ts, code and not a model. A visit becomes a record only through
// buildRecord, which takes human inputs only.

import CONTENT from "./content.json";
import { nearestSpot } from "./core/act";
import { FORM_ITEMS, checkBundle, emitVisit } from "./core/fhir_emit";
import { selectFollowups, type Followup } from "./core/followups";
import { pickActions } from "./core/healthcard";
import { fill, observerLabel } from "./core/labels";
import { pyRound } from "./core/pyround";
import { UNKNOWN, dryStatus, fetchOpenMeteo, type RainStatus } from "./core/rainfall";
import { sha256Hex } from "./core/sha256";
import { instant, isoDate, type AnswerValue, type CheckResult, type FormItem, type Observer, type Spot, type TestSitting, type VisitRecord } from "./core/types";

export interface CheckEnv {
  DB: D1Database;
  PHOTOS: KVNamespace;
  RAIN_FETCH?: (url: string) => Promise<unknown>;
}

export class Invalid extends Error {}
export class NotFound extends Error {}

const COARSE_DECIMALS = 2; // about 1 km
const FOLLOWUP_ANSWERS = new Set(["yes", "no", "cant_tell", "keep", "change", "skipped"]);
const QUICK_TEXT: Record<string, string> = {
  colour: "What colour is the water?",
  smell: "Does it smell?",
  pipe_running: "Is anything coming out of the pipe?",
};
const SLIDER_RE = /^(joy|serenity|anger|fear):([0-5]|not_applicable)$/;
const YESNO_LABEL_KEYS: Record<string, string> = { present: "test.yes", absent: "test.no", cant_tell: "test.cant_tell" };
const LOCALE: Record<string, string> = CONTENT.locale;
const REGION_PLANTS = new Set<string>([...CONTENT.region_plants, "cant_tell"]);
const SOFTWARE_VERSION = "0.1.0";
const NAME_RE = /^[A-Za-z0-9 .,'()/-]+$/;

export const randomHex = (bytes: number) => Array.from(crypto.getRandomValues(new Uint8Array(bytes)), (b) => b.toString(16).padStart(2, "0")).join("");
export const nowIso = () => new Date().toISOString().replace(/\.\d{3}Z$/, "Z");

// Rows ------------------------------------------------------------------------------------------

export interface SpotRow {
  spot_id: string;
  spot_name: string;
  reach_id: string;
  reach_name: string;
  creek_id: string;
  creek_name: string;
  latitude: number | null;
  longitude: number | null;
  coarse: number;
  created_at: string;
}

export interface VisitRow {
  visit_id: string;
  spot_id: string;
  kind: string;
  contributor_token: string | null;
  answered_at: string;
  answers_json: string;
  first_rating: string | null;
  final_rating: string | null;
  photo_ids_json: string;
  followups_json: string;
  site_json: string;
  finalized_at: string | null;
  software_version: string;
}

interface CheckRow {
  visit_id: string;
  rule_id: string;
  asked: number;
  question_text: string | null;
  answer: string | null;
  detail_json: string;
}

interface ObserverRow {
  contributor_token: string;
  scores_json: string;
  tested_on: string;
}

export function spotFromRow(row: SpotRow): Spot {
  return {
    spot_id: row.spot_id,
    spot_name: row.spot_name,
    reach_id: row.reach_id,
    reach_name: row.reach_name,
    creek_id: row.creek_id,
    creek_name: row.creek_name,
    latitude: row.latitude,
    longitude: row.longitude,
    coarse: Boolean(row.coarse),
  };
}

export async function getSpot(db: D1Database, spotId: string): Promise<SpotRow | null> {
  return db.prepare("SELECT * FROM spot WHERE spot_id = ?").bind(spotId).first<SpotRow>();
}

export async function allSpots(db: D1Database): Promise<SpotRow[]> {
  return (await db.prepare("SELECT * FROM spot ORDER BY created_at").all<SpotRow>()).results ?? [];
}

export async function observerFromToken(db: D1Database, token: string | null | undefined): Promise<Observer | null> {
  if (!token) return null;
  const row = await db.prepare("SELECT contributor_token, scores_json, tested_on FROM observer WHERE contributor_token = ?").bind(token).first<ObserverRow>();
  if (row === null) throw new NotFound("We do not know that contributor token. Check it and try again.");
  return observerFromRow(row);
}

export function observerFromRow(row: ObserverRow): Observer {
  const raw = JSON.parse(row.scores_json) as { feature: string; correct: number; total: number }[];
  return {
    contributor_token: row.contributor_token,
    scores: raw.map((s) => ({ feature: s.feature as Observer["scores"][number]["feature"], correct: Math.trunc(Number(s.correct)), total: Math.trunc(Number(s.total)), tested_on: row.tested_on.slice(0, 10) })),
  };
}

/** The observer's test sitting as the record carries it. The sitting id is a hash of the token,
 *  like the Practitioner id, so the token itself never appears. */
export async function sittingFor(db: D1Database, token: string | null | undefined): Promise<TestSitting | null> {
  if (!token) return null;
  const row = await db.prepare("SELECT contributor_token, scores_json, tested_on FROM observer WHERE contributor_token = ?").bind(token).first<ObserverRow>();
  if (row === null) return null;
  const observer = observerFromRow(row);
  if (observer.scores.length === 0) return null;
  return {
    sitting_id: `sitting-${sha256Hex(token).slice(0, 12)}`,
    contributor_token: token,
    completed_at: `${row.tested_on.slice(0, 10)}T00:00:00Z`,
    scores: observer.scores,
  };
}

// Answers ---------------------------------------------------------------------------------------

function formItem(itemId: string): FormItem | null {
  for (const item of FORM_ITEMS) if (item.id === itemId) return item;
  return null;
}

function optionValues(item: FormItem): Set<string> {
  return new Set(((item.options ?? []) as { value: unknown }[]).map((o) => String(o.value)));
}

export function validateAnswers(answers: Record<string, unknown>): Record<string, AnswerValue> {
  const clean: Record<string, AnswerValue> = {};
  for (const [itemId, value] of Object.entries(answers)) {
    const item = formItem(itemId);
    if (item === null) throw new Invalid(`We do not have a question called '${itemId}'.`);
    const kind = item.type;
    if (kind === "choice") {
      if (typeof value !== "string" || !optionValues(item).has(value)) throw new Invalid(`${itemId}: pick one of the listed options.`);
      clean[itemId] = value;
    } else if (kind === "yesno") {
      if (value !== "present" && value !== "absent" && value !== "cant_tell") throw new Invalid(`${itemId}: answer present, absent or cant_tell.`);
      clean[itemId] = value;
    } else if (kind === "multi") {
      const allowed = optionValues(item);
      if (!Array.isArray(value) || value.some((v) => typeof v !== "string" || !allowed.has(v))) throw new Invalid(`${itemId}: choose only from the listed options.`);
      clean[itemId] = value as string[];
    } else if (kind === "number") {
      if (typeof value !== "number" || !Number.isFinite(value)) throw new Invalid(`${itemId}: send a number.`);
      if (value < 0 || value > 100) throw new Invalid(`${itemId}: that number is out of range.`);
      clean[itemId] = value;
    } else if (kind === "pick_region_list") {
      if (!Array.isArray(value) || value.some((v) => typeof v !== "string" || !REGION_PLANTS.has(v))) throw new Invalid(`${itemId}: choose plants from the regional list, or cant_tell.`);
      clean[itemId] = value as string[];
    } else if (kind === "sliders") {
      if (!Array.isArray(value) || value.some((v) => typeof v !== "string" || !SLIDER_RE.test(v))) throw new Invalid(`${itemId}: send entries like joy:3 or fear:not_applicable.`);
      clean[itemId] = value as string[];
    } else {
      throw new Invalid(`${itemId}: this question cannot be answered here.`);
    }
  }
  return clean;
}

export function validateRating(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const item = formItem("overall_rating");
  if (item === null || typeof value !== "string" || !optionValues(item).has(value)) throw new Invalid("The overall rating must be good, moderate or poor.");
  return value;
}

// Spots -----------------------------------------------------------------------------------------

export interface NewSpot {
  name: string;
  latitude: number | null;
  longitude: number | null;
  coarse: boolean;
  creek_name: string | null;
  reach_name: string | null;
}

export interface SpotRef {
  spot_id?: string | null;
  new?: NewSpot | null;
}

function plainPlaceName(raw: unknown, what: string): string | null {
  if (raw === null || raw === undefined) return null;
  if (typeof raw !== "string") throw new Invalid(`${what} must be text.`);
  const v = raw.split(/\s+/).filter(Boolean).join(" ");
  if (!v) throw new Invalid("A name is needed.");
  if (v.length > 80) throw new Invalid(`${what} is too long.`);
  if (!NAME_RE.test(v)) throw new Invalid("Use letters, numbers, spaces and . , ' - ( ) / only.");
  if (/\d{5,}/.test(v)) throw new Invalid("That looks like an address or a code, not a place name.");
  if (v.includes("@")) throw new Invalid("A place name cannot hold an email address.");
  return v;
}

export function parseSpotRef(raw: unknown): SpotRef {
  if (!raw || typeof raw !== "object") throw new Invalid("Say which spot this is, or describe a new one.");
  const r = raw as Record<string, unknown>;
  if (typeof r.spot_id === "string" && r.spot_id) {
    if (r.spot_id.length > 32) throw new Invalid("That spot id is too long.");
    return { spot_id: r.spot_id };
  }
  if (r.new && typeof r.new === "object") {
    const n = r.new as Record<string, unknown>;
    const name = plainPlaceName(n.name, "The spot name");
    if (name === null) throw new Invalid("A name is needed.");
    const num = (v: unknown, lo: number, hi: number, what: string): number | null => {
      if (v === null || v === undefined) return null;
      if (typeof v !== "number" || !Number.isFinite(v) || v < lo || v > hi) throw new Invalid(`${what} is out of range.`);
      return v;
    };
    return {
      new: {
        name,
        latitude: num(n.latitude, -90, 90, "Latitude"),
        longitude: num(n.longitude, -180, 180, "Longitude"),
        coarse: n.coarse === undefined ? true : Boolean(n.coarse),
        creek_name: plainPlaceName(n.creek_name, "The creek name"),
        reach_name: plainPlaceName(n.reach_name, "The reach name"),
      },
    };
  }
  throw new Invalid("Say which spot this is, or describe a new one.");
}

function roundCoarse(value: number | null, coarse: boolean): number | null {
  if (value === null) return null;
  return coarse ? pyRound(value, COARSE_DECIMALS) : pyRound(value, 6);
}

/** An existing spot within 30 metres of a new precise pin. A suggestion, never a merge. */
export async function nearbyExistingSpot(db: D1Database, ref: SpotRef): Promise<{ spot_id: string; spot_name: string; metres: number } | null> {
  if (ref.spot_id || !ref.new) return null;
  if (ref.new.latitude === null || ref.new.longitude === null) return null;
  if (ref.new.coarse) return null;
  const rows = (await db.prepare("SELECT * FROM spot WHERE coarse = 0").all<SpotRow>()).results ?? [];
  const near = nearestSpot(ref.new.latitude, ref.new.longitude, rows.map(spotFromRow));
  if (near === null) return null;
  return { spot_id: near.spot.spot_id, spot_name: near.spot.spot_name, metres: Math.round(near.metres) };
}

export async function resolveSpot(db: D1Database, ref: SpotRef, now: string): Promise<SpotRow> {
  if (ref.spot_id) {
    const row = await getSpot(db, ref.spot_id);
    if (row === null) throw new NotFound("We do not know that spot. Add it as a new spot.");
    return row;
  }
  const n = ref.new!;
  const tail = randomHex(6);
  const row: SpotRow = {
    spot_id: `spot-${tail}`,
    spot_name: n.name.trim(),
    reach_id: `reach-${tail}`,
    reach_name: (n.reach_name ?? n.name).trim(),
    creek_id: `creek-${tail}`,
    creek_name: (n.creek_name ?? n.name).trim(),
    latitude: roundCoarse(n.latitude, n.coarse),
    longitude: roundCoarse(n.longitude, n.coarse),
    coarse: n.coarse ? 1 : 0,
    created_at: now,
  };
  await db
    .prepare("INSERT INTO spot (spot_id, spot_name, reach_id, reach_name, creek_id, creek_name, latitude, longitude, coarse, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
    .bind(row.spot_id, row.spot_name, row.reach_id, row.reach_name, row.creek_id, row.creek_name, row.latitude, row.longitude, row.coarse, row.created_at)
    .run();
  return row;
}

// Follow-ups ------------------------------------------------------------------------------------

function featureNameForParam(value: unknown): string {
  const raw = String(value).trim();
  const fid = raw.replace(/ /g, "_");
  for (const f of CONTENT.feature_list) if (f.id === fid || f.id === raw) return f.name;
  return raw;
}

export function questionText(f: Followup): string {
  const params: Record<string, string | number> = { ...f.params };
  if ("feature" in params) params.feature = featureNameForParam(params.feature);
  return fill(LOCALE[f.question_key] ?? f.question_key, params);
}

const apiKind = (kind: string) => (kind === "look_again" ? "yesno" : kind);

async function photoExists(db: D1Database, photoId: string): Promise<boolean> {
  return (await db.prepare("SELECT photo_id FROM upload WHERE photo_id = ?").bind(photoId).first()) !== null;
}

async function checkPhotoIds(db: D1Database, ids: unknown): Promise<string[]> {
  if (ids === undefined || ids === null) return [];
  if (!Array.isArray(ids) || ids.length > 8 || ids.some((p) => typeof p !== "string")) throw new Invalid("photo_ids must be a short list of photo ids.");
  for (const pid of ids as string[]) if (!(await photoExists(db, pid))) throw new Invalid(`We do not have a photo called '${pid}'. Upload it first.`);
  return [...new Set(ids as string[])];
}

export async function createDraft(env: CheckEnv, body: Record<string, unknown>, now: string) {
  const token = typeof body.contributor_token === "string" && body.contributor_token ? body.contributor_token : null;
  if (token !== null && (token.length < 8 || token.length > 32)) throw new Invalid("That contributor token does not look right.");
  const observer = await observerFromToken(env.DB, token);
  const answers = validateAnswers((body.answers ?? {}) as Record<string, unknown>);
  const firstRating = validateRating(body.first_rating);
  const photoIds = await checkPhotoIds(env.DB, body.photo_ids);
  const ref = parseSpotRef(body.spot);
  // Look before the new spot is made, or it finds itself.
  const nearby = await nearbyExistingSpot(env.DB, ref);
  const spot = await resolveSpot(env.DB, ref, now);
  const rain: RainStatus =
    spot.latitude !== null && spot.longitude !== null
      ? await dryStatus(spot.latitude, spot.longitude, Date.parse(now), env.RAIN_FETCH ?? fetchOpenMeteo)
      : UNKNOWN;
  const chosen = selectFollowups(answers, { rain: rain.status, dry_days: rain.dry_days, mm_in_window: rain.mm_in_window }, observer, [], CONTENT.followups, FORM_ITEMS, false).slice(
    0,
    Math.trunc(Number(CONTENT.followups.max_questions ?? 2)),
  );
  const followups = chosen.map((f) => ({ rule_id: f.rule_id, kind: f.kind, question_key: f.question_key, question_text: questionText(f), params: f.params }));
  const visitId = `visit-${randomHex(8)}`;
  await env.DB.prepare(
    `INSERT INTO visit (visit_id, spot_id, kind, contributor_token, answered_at, answers_json, first_rating, photo_ids_json, followups_json, site_json, software_version)
     VALUES (?, ?, 'check', ?, ?, ?, ?, ?, ?, ?, ?)`,
  )
    .bind(visitId, spot.spot_id, token, now, JSON.stringify(answers), firstRating, JSON.stringify(photoIds), JSON.stringify(followups), JSON.stringify(rain), SOFTWARE_VERSION)
    .run();
  return {
    draft_id: visitId,
    // Not a merge: the app offers this spot first and the person decides.
    nearby_spot: nearby,
    followups: followups.map((f) => ({ rule_id: f.rule_id, question_text: f.question_text, kind: apiKind(f.kind) })),
  };
}

async function cleanFollowupAnswer(db: D1Database, followup: { rule_id: string; kind: string }, value: unknown): Promise<string> {
  const text = String(typeof value === "boolean" ? (value ? "yes" : "no") : value)
    .trim()
    .slice(0, 64);
  if (followup.kind === "photo") {
    if (FOLLOWUP_ANSWERS.has(text)) return text;
    if (!(await photoExists(db, text))) throw new Invalid(`${followup.rule_id}: send the photo id from the upload, or skipped.`);
    return text;
  }
  if (!FOLLOWUP_ANSWERS.has(text)) throw new Invalid(`${followup.rule_id}: answer yes, no, cant_tell, keep, change or skipped.`);
  return text;
}

/** The only way a VisitRecord is made: human inputs only. There is no parameter for a flag, a
 *  model id or raw model text (hard rule 2, core/gate.py). */
export function buildRecord(opts: {
  visit_id: string;
  spot: Spot;
  observer: Observer;
  answered_at: string;
  answers: Record<string, AnswerValue>;
  first_rating: string | null;
  final_rating: string | null;
  checks: CheckResult[];
  photo_ids: string[];
  software_version: string;
}): VisitRecord {
  const copied: Record<string, AnswerValue> = {};
  for (const [key, value] of Object.entries(opts.answers)) copied[String(key)] = Array.isArray(value) ? value.map(String) : value;
  return {
    visit_id: opts.visit_id,
    spot: opts.spot,
    observer: opts.observer,
    answered_at: opts.answered_at,
    answers: copied,
    first_rating: opts.first_rating,
    final_rating: opts.final_rating,
    checks: [...opts.checks],
    photo_ids: opts.photo_ids.map(String),
    software_version: opts.software_version,
  };
}

export async function finalize(env: CheckEnv, body: Record<string, unknown>, now: string) {
  const draftId = String(body.draft_id ?? "");
  const row = await env.DB.prepare("SELECT * FROM visit WHERE visit_id = ?").bind(draftId).first<VisitRow>();
  if (row === null || row.kind !== "check") throw new NotFound("We do not know that draft. Start the check again.");
  if (row.finalized_at !== null) return { visit_id: row.visit_id, spot_id: row.spot_id, fhir_saved: null };
  const followups = JSON.parse(row.followups_json) as { rule_id: string; kind: string; question_text: string; params: Record<string, string | number> }[];
  const byRule = new Map(followups.map((f) => [f.rule_id, f]));
  const given = (body.followup_answers ?? {}) as Record<string, unknown>;
  for (const ruleId of Object.keys(given)) if (!byRule.has(ruleId)) throw new Invalid(`No follow-up called '${ruleId}' was asked in this check.`);
  const finalRating = validateRating(body.final_rating);
  const photoIds: string[] = JSON.parse(row.photo_ids_json);
  const checks: CheckResult[] = [];
  for (const f of followups) {
    const raw = given[f.rule_id];
    const answer = raw !== undefined && raw !== null ? await cleanFollowupAnswer(env.DB, f, raw) : null;
    if (f.kind === "photo" && answer && !FOLLOWUP_ANSWERS.has(answer)) photoIds.push(answer);
    const detail: Record<string, string | number | null> = {};
    for (const [k, v] of Object.entries(f.params)) detail[k] = typeof v === "string" || typeof v === "number" ? v : String(v);
    detail.kind = f.kind;
    checks.push({ rule_id: f.rule_id, asked: true, question_text: f.question_text, answer, detail });
  }
  const spotRow = await getSpot(env.DB, row.spot_id);
  if (spotRow === null) throw new NotFound("The spot for this draft is gone.");
  const observer = (await observerFromToken(env.DB, row.contributor_token)) ?? { contributor_token: `anon${row.visit_id.slice(-12)}`, scores: [] };
  const record = buildRecord({
    visit_id: row.visit_id,
    spot: spotFromRow(spotRow),
    observer,
    answered_at: row.answered_at,
    answers: JSON.parse(row.answers_json),
    first_rating: row.first_rating,
    final_rating: finalRating,
    checks,
    photo_ids: photoIds,
    software_version: row.software_version || SOFTWARE_VERSION,
  });
  const statements = checks.map((c) =>
    env.DB.prepare("INSERT INTO check_result (visit_id, rule_id, asked, question_text, answer, detail_json) VALUES (?, ?, ?, ?, ?, ?)").bind(
      row.visit_id,
      c.rule_id,
      c.asked ? 1 : 0,
      c.question_text ?? null,
      c.answer ?? null,
      JSON.stringify(c.detail),
    ),
  );
  statements.push(
    env.DB.prepare("UPDATE visit SET final_rating = ?, photo_ids_json = ?, finalized_at = ? WHERE visit_id = ?").bind(finalRating, JSON.stringify([...new Set(photoIds)]), now, row.visit_id),
  );
  await env.DB.batch(statements);
  const saved = await saveVisitBundle(env.DB, record, await sittingFor(env.DB, row.contributor_token), now);
  return { visit_id: row.visit_id, spot_id: row.spot_id, fhir_saved: saved };
}

/** Emit, check every reference resolves, then store. A Bundle with a problem is not stored; the
 *  database row is the source of truth either way. */
export async function saveVisitBundle(db: D1Database, record: VisitRecord, sitting: TestSitting | null, now: string): Promise<boolean> {
  const bundle = emitVisit(record, sitting, now);
  if (checkBundle(bundle).length > 0) return false;
  await db
    .prepare("INSERT OR REPLACE INTO fhir_bundle (visit_id, spot_id, bundle_json, created_at) VALUES (?, ?, ?, ?)")
    .bind(record.visit_id, record.spot.spot_id, JSON.stringify(bundle), now)
    .run();
  return true;
}

export async function loadVisitBundle(db: D1Database, visitId: string): Promise<Record<string, unknown> | null> {
  const row = await db.prepare("SELECT bundle_json FROM fhir_bundle WHERE visit_id = ?").bind(visitId).first<{ bundle_json: string }>();
  return row === null ? null : (JSON.parse(row.bundle_json) as Record<string, unknown>);
}

export async function latestBundleForSpot(db: D1Database, spotId: string): Promise<Record<string, unknown> | null> {
  // Insertion order, not the second the row was written in: two visits finalized in the same
  // second would otherwise be told apart by their random ids.
  const row = await db.prepare("SELECT bundle_json FROM fhir_bundle WHERE spot_id = ? ORDER BY rowid DESC LIMIT 1").bind(spotId).first<{ bundle_json: string }>();
  return row === null ? null : (JSON.parse(row.bundle_json) as Record<string, unknown>);
}

export async function latestBundle(db: D1Database): Promise<Record<string, unknown> | null> {
  const row = await db.prepare("SELECT bundle_json FROM fhir_bundle ORDER BY rowid DESC LIMIT 1").first<{ bundle_json: string }>();
  return row === null ? null : (JSON.parse(row.bundle_json) as Record<string, unknown>);
}

// Quick check -----------------------------------------------------------------------------------

const QUICK = {
  colour: ["clear", "muddy", "foam", "coloured", "cant_tell"],
  smell: ["none", "bad", "cant_tell"],
  pipe_running: ["present", "absent", "cant_tell"],
};

export async function quickCheck(env: CheckEnv, spotId: string, body: Record<string, unknown>, now: string) {
  const spot = await getSpot(env.DB, spotId);
  if (spot === null) throw new NotFound("We do not know that spot.");
  const token = typeof body.contributor_token === "string" && body.contributor_token ? body.contributor_token : null;
  await observerFromToken(env.DB, token);
  for (const [key, allowed] of Object.entries(QUICK)) {
    if (typeof body[key] !== "string" || !allowed.includes(body[key] as string)) throw new Invalid(`${key}: pick one of ${allowed.join(", ")}.`);
  }
  const photoIds = await checkPhotoIds(env.DB, typeof body.photo_id === "string" ? [body.photo_id] : []);
  const visitId = `visit-${randomHex(8)}`;
  await env.DB.prepare(
    `INSERT INTO visit (visit_id, spot_id, kind, contributor_token, answered_at, answers_json, photo_ids_json, followups_json, site_json, finalized_at, software_version)
     VALUES (?, ?, 'quick', ?, ?, ?, ?, '[]', '{}', ?, ?)`,
  )
    .bind(visitId, spotId, token, now, JSON.stringify({ colour: body.colour, smell: body.smell, pipe_running: body.pipe_running }), JSON.stringify(photoIds), now, SOFTWARE_VERSION)
    .run();
  return { visit_id: visitId, spot_id: spotId };
}

// The record view -------------------------------------------------------------------------------

function valueLabel(item: FormItem | null, value: AnswerValue): string {
  const values = Array.isArray(value) ? value : [value];
  return values
    .map((v) => {
      if (item !== null && item.type === "yesno" && String(v) in YESNO_LABEL_KEYS) return LOCALE[YESNO_LABEL_KEYS[String(v)]] ?? String(v);
      for (const option of (item?.options ?? []) as { value: unknown; label?: string }[]) if (String(option.value) === String(v)) return String(option.label ?? v);
      return String(v).replace(/_/g, " ");
    })
    .join(", ");
}

export function featureName(featureId: string): string {
  for (const f of CONTENT.feature_list) if (f.id === featureId) return f.name;
  return featureId;
}

function answerViews(row: VisitRow, observer: Observer | null, today: string) {
  const answers = JSON.parse(row.answers_json) as Record<string, AnswerValue>;
  return Object.entries(answers).map(([itemId, value]) => {
    const item = row.kind === "check" ? formItem(itemId) : null;
    let text: string;
    let feature: string | null;
    if (row.kind === "quick") {
      text = QUICK_TEXT[itemId] ?? itemId.replace(/_/g, " ");
      feature = itemId === "pipe_running" ? "pipe_running" : null;
    } else {
      text = item ? String(item.text ?? itemId) : itemId;
      feature = item && item.feature ? String(item.feature) : null;
    }
    let labelText: string | null = null;
    let passed: boolean | null = null;
    if (observer !== null && feature !== null) {
      const score = observer.scores.find((s) => s.feature === feature) ?? null;
      if (score !== null) {
        const label = observerLabel(score, featureName(feature), today, LOCALE);
        labelText = label.text;
        passed = label.passed;
      }
    }
    return { item_id: itemId, text, value, label: valueLabel(item, value), feature, observer_label: labelText, observer_passed: passed };
  });
}

export async function checksFor(db: D1Database, visitId: string): Promise<CheckResult[]> {
  const rows = (await db.prepare("SELECT * FROM check_result WHERE visit_id = ? ORDER BY id").bind(visitId).all<CheckRow>()).results ?? [];
  return rows.map((c) => ({ rule_id: c.rule_id, asked: Boolean(c.asked), question_text: c.question_text, answer: c.answer, detail: JSON.parse(c.detail_json) }));
}

export async function spotView(env: CheckEnv, spotId: string, today: string) {
  const spot = await getSpot(env.DB, spotId);
  if (spot === null) throw new NotFound("We do not know that spot.");
  const visits = (await env.DB.prepare("SELECT * FROM visit WHERE spot_id = ? AND finalized_at IS NOT NULL ORDER BY answered_at DESC").bind(spotId).all<VisitRow>()).results ?? [];
  const observers = new Map<string, Observer | null>();
  const views = [];
  for (const v of visits) {
    const token = v.contributor_token;
    if (token && !observers.has(token)) {
      const row = await env.DB.prepare("SELECT contributor_token, scores_json, tested_on FROM observer WHERE contributor_token = ?").bind(token).first<ObserverRow>();
      observers.set(token, row ? observerFromRow(row) : null);
    }
    const observer = token ? (observers.get(token) ?? null) : null;
    views.push({
      visit_id: v.visit_id,
      kind: v.kind,
      answered_at: instant(v.answered_at),
      answers: answerViews(v, observer, today),
      checks: await checksFor(env.DB, v.visit_id),
      first_rating: v.first_rating,
      final_rating: v.final_rating,
      photo_count: (JSON.parse(v.photo_ids_json) as string[]).length,
      observer_scored: observer !== null,
    });
  }
  return {
    spot: { ...spotFromRow(spot) },
    visits: views,
    health_card: pickActions(CONTENT.sentences as Record<string, unknown>[], spotId),
  };
}

export const todayOf = (now: string) => isoDate(Date.parse(now));
