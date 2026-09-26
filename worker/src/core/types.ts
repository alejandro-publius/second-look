// The shared shapes, as core/records.py has them and as pydantic writes them to JSON: dates are
// "YYYY-MM-DD" strings, instants are ISO strings in UTC. The Worker reads the same shapes back
// from its database, so nothing here is a second model of a visit.

export type FeatureId = "artificial_bank" | "dug_out_channel" | "invasive_plant" | "pipe_running";

export interface FeatureScore {
  feature: FeatureId;
  correct: number;
  total: number;
  tested_on: string;
}

export interface Observer {
  contributor_token: string;
  scores: FeatureScore[];
  test_sitting_id?: string | null;
}

export interface Spot {
  spot_id: string;
  spot_name: string;
  reach_id: string;
  reach_name: string;
  creek_id: string;
  creek_name: string;
  latitude: number | null;
  longitude: number | null;
  coarse: boolean;
}

export type Detail = Record<string, string | number | null>;

export interface CheckResult {
  rule_id: string;
  asked: boolean;
  question_text?: string | null;
  answer?: string | null;
  detail: Detail;
}

export type AnswerValue = string | number | boolean | string[];

export interface VisitRecord {
  visit_id: string;
  spot: Spot;
  observer: Observer;
  answered_at: string;
  answers: Record<string, AnswerValue>;
  first_rating?: string | null;
  final_rating?: string | null;
  checks: CheckResult[];
  photo_ids: string[];
  software_version: string;
  /** The language the questions were shown in, a BCP 47 tag; the record states it (UPDATE_32). */
  language?: string;
}

export interface TestSitting {
  sitting_id: string;
  contributor_token: string | null;
  completed_at: string;
  scores: FeatureScore[];
}

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
export type FormItem = Record<string, any>;

export function scoreFor(observer: Observer, feature: string): FeatureScore | null {
  for (const s of observer.scores) if (s.feature === feature) return s;
  return null;
}

// Dates and instants, in UTC only.

export function parseDate(day: string): number {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(day);
  if (!m) throw new Error(`not a date: ${day}`);
  return Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

export function isoDate(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10);
}

export function daysBetween(earlier: string, later: string): number {
  return Math.round((parseDate(later) - parseDate(earlier)) / 86_400_000);
}

export function addDays(day: string, days: number): string {
  return isoDate(parseDate(day) + days * 86_400_000);
}

/** An ISO instant, however many fraction digits it carries, as milliseconds. Naive means UTC. */
export function parseInstant(iso: string): number {
  let text = iso.replace(/(\.\d{3})\d+/, "$1");
  if (!/([zZ]|[+-]\d{2}:?\d{2})$/.test(text)) text += "Z";
  const ms = Date.parse(text);
  if (Number.isNaN(ms)) throw new Error(`not an instant: ${iso}`);
  return ms;
}

/** The instant as core.fhir_emit._instant prints it: seconds, UTC, a Z. */
export function instant(iso: string | number): string {
  const ms = typeof iso === "number" ? iso : parseInstant(iso);
  return new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");
}

/** The UTC calendar day of an instant, the way datetime.date() gives it for an aware UTC time. */
export function dayOf(iso: string): string {
  return isoDate(parseInstant(iso));
}

export function compareStrings(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}
