// The analyst's view on the Worker: a port of apps/api/city.py. All the judgement lives in
// core/act.ts, which is pure and proved against Python by golden vectors; this only reads rows
// and hands them over, so the rule that every number carries its evidence is kept in one place.

import CONTENT from "./content.json";
import { findingsFromVisits, looksLikeATestName, needsFromFindings, notesBelow, pipesWorthTesting, type DownstreamNote, type Finding, type PipeCase } from "./core/act";
import { FORM_ITEMS } from "./core/fhir_emit";
import { exampleLabResult, referralBundle, ReferralError } from "./core/fhir_referral";
import { CREEKS, creekBySlug, placeSpot, reachOf, type Creek, type Placement } from "./core/regions";
import type { Observer, VisitRecord } from "./core/types";
import { NotFound, allSpots, checksFor, getSpot, loadVisitBundle, observerFromRow, spotFromRow, type CheckEnv, type SpotRow, type VisitRow } from "./check";

const DAY_MS = 86_400_000;
const EXAMPLE_SAMPLE_AFTER = 1 * DAY_MS;
const EXAMPLE_REPORT_AFTER = 4 * DAY_MS;

export const referralPath = (spotId: string) => `/api/fhir/referral/${spotId}`;
export const exampleResultPath = (spotId: string) => `${referralPath(spotId)}/example-result`;
const bundleLinks = (ids: string[]) => ids.map((v) => `/api/fhir/Bundle/${v}`);

const FEATURE_NAMES: Record<string, string> = Object.fromEntries(CONTENT.feature_list.map((f) => [f.id, f.name]));
for (const item of FORM_ITEMS) if (!(item.id in FEATURE_NAMES)) FEATURE_NAMES[item.id] = String(item.text ?? item.id);
const FINDING_KEY_FOR: Record<string, string> = Object.fromEntries(FORM_ITEMS.filter((i) => i.feature).map((i) => [i.id, String(i.feature)]));

/** Plain words for a finding key inside the downstream line: "built banks", "a sewage discharge". */
const NOTE_LABELS: Record<string, string> = (() => {
  const labels: Record<string, string> = {};
  for (const item of FORM_ITEMS) labels[item.id] = item.short_label ? String(item.short_label) : String(item.id).replace(/_/g, " ");
  for (const f of CONTENT.feature_list) labels[f.id] = f.name.slice(0, 1).toLowerCase() + f.name.slice(1);
  return labels;
})();

export async function recordsFor(env: CheckEnv, spots: SpotRow[]): Promise<VisitRecord[]> {
  if (spots.length === 0) return [];
  const byId = new Map(spots.map((s) => [s.spot_id, s]));
  const placeholders = spots.map(() => "?").join(",");
  const rows = (await env.DB.prepare(`SELECT * FROM visit WHERE spot_id IN (${placeholders}) AND finalized_at IS NOT NULL ORDER BY answered_at`).bind(...spots.map((s) => s.spot_id)).all<VisitRow>()).results ?? [];
  const observers = new Map<string, Observer>();
  const out: VisitRecord[] = [];
  for (const v of rows) {
    let observer: Observer;
    if (!v.contributor_token) {
      // An anonymous visit is still a visit, but it cannot carry a score, so it can never put a
      // pipe on the list. It still counts as a finding.
      observer = { contributor_token: "anonymous000", scores: [] };
    } else {
      if (!observers.has(v.contributor_token)) {
        const row = await env.DB.prepare("SELECT contributor_token, scores_json, tested_on FROM observer WHERE contributor_token = ?").bind(v.contributor_token).first<{ contributor_token: string; scores_json: string; tested_on: string }>();
        observers.set(v.contributor_token, row ? observerFromRow(row) : { contributor_token: v.contributor_token, scores: [] });
      }
      observer = observers.get(v.contributor_token)!;
    }
    out.push({
      visit_id: v.visit_id,
      spot: spotFromRow(byId.get(v.spot_id)!),
      observer,
      answered_at: v.answered_at,
      answers: JSON.parse(v.answers_json),
      first_rating: v.first_rating,
      final_rating: v.final_rating,
      checks: await checksFor(env.DB, v.visit_id),
      photo_ids: JSON.parse(v.photo_ids_json),
      software_version: v.software_version,
    });
  }
  return out;
}

export function placementsFor(spots: SpotRow[]): Map<string, Placement> {
  const out = new Map<string, Placement>();
  for (const row of spots) {
    const placed = placeSpot(spotFromRow(row), CREEKS);
    if (placed) out.set(row.spot_id, placed);
  }
  return out;
}

export async function placeForSpot(env: CheckEnv, spotId: string) {
  const row = await getSpot(env.DB, spotId);
  if (row === null) throw new NotFound("We do not know that spot.");
  const placed = placeSpot(spotFromRow(row), CREEKS);
  if (placed === null) return null;
  return { creek_slug: placed.creek.slug, creek_name: placed.creek.name, reach_slug: placed.reach?.slug ?? null, reach_name: placed.reach?.name ?? null };
}

function findingView(f: Finding, spotNames: Map<string, string>) {
  return {
    spot_id: f.spot_id,
    spot_name: spotNames.get(f.spot_id) ?? f.spot_id,
    feature: f.feature,
    feature_name: FEATURE_NAMES[f.feature] ?? f.feature,
    observers: f.observers.length,
    passed_observers: f.passed_observers.length,
    first_seen: f.first_seen,
    last_seen: f.last_seen,
    visit_ids: f.visit_ids,
    fhir: bundleLinks(f.visit_ids),
  };
}

function noteView(n: DownstreamNote) {
  return {
    reach_slug: n.reach_slug,
    reach_name: n.reach_name,
    from_reach_slug: n.from_reach_slug,
    from_reach_name: n.from_reach_name,
    feature: n.feature,
    feature_name: FEATURE_NAMES[n.feature] ?? n.feature,
    line: n.line,
    observers: n.observers,
    visit_ids: n.visit_ids,
    fhir: bundleLinks(n.visit_ids),
  };
}

export async function cityView(env: CheckEnv, creekRef: string, today: string) {
  let creek: Creek | null = creekBySlug(creekRef);
  const all = await allSpots(env.DB);
  const placements = placementsFor(all);
  let spots: SpotRow[];
  if (creek !== null) {
    const slug = creek.slug;
    spots = all.filter((s) => placements.get(s.spot_id)?.creek.slug === slug);
  } else {
    spots = all.filter((s) => s.creek_id === creekRef);
    if (spots.length === 0) throw new NotFound("We have no record for that creek yet.");
    const placedOn = new Set(spots.map((s) => placements.get(s.spot_id)?.creek.slug).filter((x): x is string => Boolean(x)));
    creek = placedOn.size === 1 ? creekBySlug([...placedOn][0]) : null;
  }
  const flagged = spots.filter((s) => looksLikeATestName(s.spot_name));
  const real = spots.filter((s) => !flagged.includes(s));
  const spotNames = new Map(spots.map((s) => [s.spot_id, s.spot_name]));
  const visits = await recordsFor(env, real);
  const findings = findingsFromVisits(visits, FINDING_KEY_FOR);
  const needs = needsFromFindings(findings, CONTENT.sentences as Record<string, unknown>[]);
  const pipes = pipesWorthTesting(visits, today);

  let notes: DownstreamNote[] = [];
  const reaches: unknown[] = [];
  let unplaced = 0;
  if (creek !== null) {
    const reachOfSpot: Record<string, ReturnType<typeof reachOf>> = {};
    for (const s of real) if (placements.has(s.spot_id)) reachOfSpot[s.spot_id] = placements.get(s.spot_id)!.reach;
    notes = notesBelow(findings, reachOfSpot, creek, NOTE_LABELS);
    const visitsAt = new Map<string, number>();
    for (const v of visits) visitsAt.set(v.spot.spot_id, (visitsAt.get(v.spot.spot_id) ?? 0) + 1);
    for (const reach of creek.reaches) {
      const here = real.filter((s) => reachOfSpot[s.spot_id] === reach);
      reaches.push({
        slug: reach.slug,
        name: reach.name,
        flows_into: reach.flows_into,
        flows_into_name: reach.flows_into ? (reachOf(creek, reach.flows_into)?.name ?? null) : null,
        spots: here.length,
        visits: here.reduce((n, s) => n + (visitsAt.get(s.spot_id) ?? 0), 0),
        notes: notes.filter((n) => n.reach_slug === reach.slug).map(noteView),
      });
    }
    unplaced = real.filter((s) => !reachOfSpot[s.spot_id]).length;
  }
  const sentences = CONTENT.sentences as Record<string, unknown>[];
  return {
    creek_id: creekRef,
    creek_slug: creek?.slug ?? null,
    creek_name: creek ? creek.name : real.length ? real[0].creek_name : creekRef,
    visits: visits.length,
    visit_ids: visits.map((v) => v.visit_id),
    fhir: bundleLinks(visits.map((v) => v.visit_id)),
    spots: real.length,
    findings: findings.map((f) => findingView(f, spotNames)),
    needs: needs.map((n) => ({ sentence_id: n.sentence_id, text: n.text, source: n.source, because: n.because.map((b) => FEATURE_NAMES[b] ?? b), visit_ids: n.visit_ids, fhir: bundleLinks(n.visit_ids) })),
    pipes_worth_testing: pipes.map((p) => ({
      spot_id: p.spot_id,
      spot_name: p.spot_name,
      observers: p.observers.length,
      dry_days: p.dry_days,
      last_seen: p.last_seen,
      visit_ids: p.visit_ids,
      fhir: bundleLinks(p.visit_ids),
      referral: referralPath(p.spot_id),
      example_result: exampleResultPath(p.spot_id),
    })),
    flagged_spots: flagged.map((s) => ({ spot_id: s.spot_id, spot_name: s.spot_name, why: "the name reads like a test" })),
    measures_waiting_for_approval: sentences.length === 0 || sentences.every((s) => s.approved !== true),
    reaches,
    downstream_notes: notes.map(noteView),
    unplaced_spots: unplaced,
  };
}

export async function notesForSpot(env: CheckEnv, spotId: string, today: string) {
  const place = await placeForSpot(env, spotId);
  if (place === null || place.reach_slug === null) return [];
  const view = await cityView(env, place.creek_slug, today);
  return view.downstream_notes.filter((n) => n.reach_slug === place.reach_slug);
}

export async function creeksView(env: CheckEnv) {
  const all = await allSpots(env.DB);
  const placements = placementsFor(all);
  const groups = new Map<string, { creek: string; creek_slug: string | null; name: string; spots: SpotRow[] }>();
  for (const row of all) {
    if (looksLikeATestName(row.spot_name)) continue;
    const placed = placements.get(row.spot_id);
    const key = placed ? placed.creek.slug : row.creek_id;
    if (!groups.has(key)) groups.set(key, { creek: key, creek_slug: placed ? placed.creek.slug : null, name: placed ? placed.creek.name : row.creek_name, spots: [] });
    groups.get(key)!.spots.push(row);
  }
  const out = [];
  for (const group of groups.values()) {
    const visits = await recordsFor(env, group.spots);
    out.push({
      creek: group.creek,
      creek_slug: group.creek_slug,
      name: group.name,
      spots: group.spots.length,
      visits: visits.length,
      visit_ids: visits.map((v) => v.visit_id),
      fhir: bundleLinks(visits.map((v) => v.visit_id)),
      record: `/api/city/${group.creek}`,
    });
  }
  out.sort((a, b) => Number(a.creek_slug === null) - Number(b.creek_slug === null) || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
  return { creeks: out };
}

async function realSpotsOnTheCreekOf(env: CheckEnv, spotId: string): Promise<SpotRow[]> {
  const spot = await getSpot(env.DB, spotId);
  if (spot === null) throw new NotFound("We do not know that spot.");
  const all = await allSpots(env.DB);
  const placements = placementsFor(all);
  const mine = placements.get(spotId);
  const spots = mine ? all.filter((s) => placements.get(s.spot_id)?.creek.slug === mine.creek.slug) : all.filter((s) => s.creek_id === spot.creek_id);
  return spots.filter((s) => !looksLikeATestName(s.spot_name));
}

export async function pipeCaseFor(env: CheckEnv, spotId: string, today: string): Promise<PipeCase> {
  const visits = await recordsFor(env, await realSpotsOnTheCreekOf(env, spotId));
  for (const pipe of pipesWorthTesting(visits, today)) if (pipe.spot_id === spotId) return pipe;
  throw new NotFound("No referral: this pipe is not on the list. Two different people who both passed the pipe feature have to report it running in dry weather.");
}

export async function referralView(env: CheckEnv, spotId: string, now: string) {
  const pipe = await pipeCaseFor(env, spotId, now.slice(0, 10));
  const bundles: Record<string, Record<string, unknown>> = {};
  for (const visitId of pipe.visit_ids) {
    const bundle = await loadVisitBundle(env.DB, visitId);
    if (bundle) bundles[visitId] = bundle;
  }
  try {
    return referralBundle(pipe, bundles as never, now);
  } catch (err) {
    if (err instanceof ReferralError) throw new NotFound(`No referral could be built: ${err.message}`);
    throw err;
  }
}

export async function exampleResultView(env: CheckEnv, spotId: string, now: string) {
  const referral = await referralView(env, spotId, now);
  const at = Date.parse(now);
  return exampleLabResult(referral, new Date(at + EXAMPLE_SAMPLE_AFTER).toISOString(), new Date(at + EXAMPLE_REPORT_AFTER).toISOString());
}
