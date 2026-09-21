// core/act.py: turning a creek's record into what the creek needs, which pipes are worth testing,
// and the two pin guards. Pure. Every number carries the visit ids it was counted from.

import CONTENT from "../content.json";
import { HUMAN_PASS_MIN, shortDate } from "./labels";
import { reachesBelow, type Creek, type Reach } from "./regions";
import { compareStrings, dayOf, daysBetween, scoreFor, type Spot, type VisitRecord } from "./types";

const FEATURES: readonly string[] = CONTENT.rules.features_in_order;
const SCORE_VALID_DAYS: number = CONTENT.rules.score_valid_days;
export const MEASURE_FOR_FEATURE: Record<string, string[]> = CONTENT.rules.measure_for_feature;
export const DRY_PIPE_RULE = "dry_pipe";
export const PIPE_OBSERVERS_NEEDED: number = CONTENT.rules.pipe_observers_needed;
export const SAME_SPOT_METRES: number = CONTENT.rules.same_spot_metres;
const EARTH_RADIUS_M = 6_371_000.0;
const TEST_NAME_WORDS = new Set<string>(CONTENT.rules.test_name_words);

export interface Finding {
  spot_id: string;
  feature: string;
  observers: string[];
  visit_ids: string[];
  first_seen: string;
  last_seen: string;
  passed_observers: string[];
}

export interface Need {
  sentence_id: string;
  text: string;
  source: string;
  because: string[];
  visit_ids: string[];
}

export interface PipeCase {
  spot_id: string;
  spot_name: string;
  observers: string[];
  visit_ids: string[];
  dry_days: number[];
  last_seen: string;
}

/** Our answers say present or absent; a yes is the same thing from the quick check. Python's set
 *  test also lets 1 through, because 1 == True there. */
function present(value: unknown): boolean {
  return value === "present" || value === "yes" || value === true || value === 1;
}

function passedFeature(v: VisitRecord, feature: string, today: string): boolean {
  if (!FEATURES.includes(feature)) return false;
  const score = scoreFor(v.observer, feature);
  if (score === null || daysBetween(score.tested_on, today) > SCORE_VALID_DAYS) return false;
  return score.correct >= HUMAN_PASS_MIN;
}

export function findingsFromVisits(visits: VisitRecord[], findingKeyFor: Record<string, string> | null): Finding[] {
  const lookup = findingKeyFor ?? {};
  const seen = new Map<string, Finding>();
  for (const v of visits) {
    for (const [answerKey, value] of Object.entries(v.answers)) {
      const feature = lookup[answerKey] ?? answerKey;
      if (!(feature in MEASURE_FOR_FEATURE) || !present(value)) continue;
      const key = `${v.spot.spot_id}\u0000${feature}`;
      const day = dayOf(v.answered_at);
      let row = seen.get(key);
      if (!row) {
        row = { spot_id: v.spot.spot_id, feature, observers: [], visit_ids: [], first_seen: day, last_seen: day, passed_observers: [] };
        seen.set(key, row);
      }
      const token = v.observer.contributor_token;
      if (!row.observers.includes(token)) row.observers.push(token);
      if (!row.passed_observers.includes(token) && passedFeature(v, feature, day)) row.passed_observers.push(token);
      row.visit_ids.push(v.visit_id);
      if (day < row.first_seen) row.first_seen = day;
      if (day > row.last_seen) row.last_seen = day;
    }
  }
  return [...seen.values()].sort((a, b) => compareStrings(a.spot_id, b.spot_id) || compareStrings(a.feature, b.feature));
}

export function needsFromFindings(findings: Finding[], sentences: Record<string, unknown>[]): Need[] {
  const approved = new Map<string, Record<string, unknown>>();
  for (const s of sentences) if (s.approved === true && s.audience === "city") approved.set(String(s.id), s);
  const wanted = new Map<string, { because: string[]; visits: string[] }>();
  for (const f of findings) {
    for (const sentenceId of MEASURE_FOR_FEATURE[f.feature] ?? []) {
      if (!approved.has(sentenceId)) continue;
      let row = wanted.get(sentenceId);
      if (!row) {
        row = { because: [], visits: [] };
        wanted.set(sentenceId, row);
      }
      if (!row.because.includes(f.feature)) row.because.push(f.feature);
      row.visits.push(...f.visit_ids);
    }
  }
  return [...wanted.entries()]
    .sort(([a], [b]) => compareStrings(a, b))
    .map(([sentenceId, row]) => {
      const s = approved.get(sentenceId)!;
      return {
        sentence_id: sentenceId,
        text: String(s.text ?? ""),
        source: String(s.source ?? ""),
        because: row.because,
        visit_ids: [...new Set(row.visits)],
      };
    });
}

function dryPipeDays(v: VisitRecord): number | null {
  for (const c of v.checks) {
    if (c.rule_id !== DRY_PIPE_RULE || !c.asked || c.answer !== "yes") continue;
    const days = c.detail.days;
    if (typeof days === "number" && Number.isInteger(days) && days >= 1) return days;
  }
  return null;
}

export function pipesWorthTesting(visits: VisitRecord[], today: string): PipeCase[] {
  const bySpot = new Map<string, PipeCase>();
  for (const v of visits) {
    const days = dryPipeDays(v);
    if (days === null || !passedFeature(v, "pipe_running", today)) continue;
    const day = dayOf(v.answered_at);
    let row = bySpot.get(v.spot.spot_id);
    if (!row) {
      row = { spot_id: v.spot.spot_id, spot_name: v.spot.spot_name, observers: [], visit_ids: [], dry_days: [], last_seen: day };
      bySpot.set(v.spot.spot_id, row);
    }
    if (!row.observers.includes(v.observer.contributor_token)) row.observers.push(v.observer.contributor_token);
    row.visit_ids.push(v.visit_id);
    row.dry_days.push(days);
    if (day > row.last_seen) row.last_seen = day;
  }
  return [...bySpot.values()]
    .sort((a, b) => compareStrings(a.spot_id, b.spot_id))
    .filter((row) => row.observers.length >= PIPE_OBSERVERS_NEEDED);
}

/** Great circle distance in metres. Good to a metre at the scale of one creek. */
export function metresBetween(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const rad = (d: number) => (d * Math.PI) / 180;
  const p1 = rad(lat1);
  const p2 = rad(lat2);
  const dp = rad(lat2 - lat1);
  const dl = rad(lon2 - lon1);
  const a = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1.0, Math.sqrt(a)));
}

export interface NearbySpot {
  spot: Spot;
  metres: number;
}

export function nearestSpot(latitude: number, longitude: number, spots: Spot[], within = SAME_SPOT_METRES): NearbySpot | null {
  let best: NearbySpot | null = null;
  for (const s of spots) {
    if (s.latitude === null || s.longitude === null) continue;
    const d = metresBetween(latitude, longitude, s.latitude, s.longitude);
    if (d <= within && (best === null || d < best.metres)) best = { spot: s, metres: d };
  }
  return best;
}

/** True when a spot name reads like someone trying the form out. Flagged, never deleted. */
export function looksLikeATestName(name: string): boolean {
  const cleaned = Array.from(name.toLowerCase(), (ch) => (/[\p{L}\p{N}]/u.test(ch) || /\s/.test(ch) ? ch : " ")).join("");
  const words = cleaned.split(/\s+/).filter((w) => w.length > 0);
  if (words.length === 0) return true;
  if (words.some((w) => TEST_NAME_WORDS.has(w))) return true;
  return !/\p{L}/u.test(name);
}

export interface DownstreamNote {
  reach_slug: string;
  reach_name: string;
  from_reach_slug: string;
  from_reach_name: string;
  feature: string;
  line: string;
  observers: number;
  visit_ids: string[];
}

/** One plain line for each reach below a finding: who reported and when, nothing about what the
 *  water will do to anybody. core.act.downstream_note. */
export function downstreamNote(finding: Finding, featureName: string, reachSlugs: string[]): Record<string, string> {
  const n = finding.observers.length;
  const people = n === 1 ? "one person" : `${n} people`;
  const line = `Upstream of here, ${people} reported ${featureName} on ${shortDate(finding.last_seen)}.`;
  return Object.fromEntries(reachSlugs.map((slug) => [slug, line]));
}

/** core.act.notes_below: the note for every reach below every finding on this creek. A finding
 *  on an unknown reach gives no note; a reach with no flows_into gives none either. */
export function notesBelow(findings: Finding[], reachOfSpot: Record<string, Reach | null | undefined>, creek: Creek, labels: Record<string, string>): DownstreamNote[] {
  const out: DownstreamNote[] = [];
  for (const f of findings) {
    const reach = reachOfSpot[f.spot_id];
    if (!reach) continue;
    if (!creek.reaches.some((r) => r.slug === reach.slug)) continue;
    const below = reachesBelow(reach, creek);
    if (below.length === 0) continue;
    const label = labels[f.feature] ?? f.feature.replace(/_/g, " ");
    const lines = downstreamNote(f, label, below.map((r) => r.slug));
    for (const r of below) {
      out.push({
        reach_slug: r.slug,
        reach_name: r.name,
        from_reach_slug: reach.slug,
        from_reach_name: reach.name,
        feature: f.feature,
        line: lines[r.slug],
        observers: f.observers.length,
        visit_ids: f.visit_ids,
      });
    }
  }
  return out;
}
