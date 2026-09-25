// Video walks, on the device only (Update 14 3.7). The record is built here by the same emitter
// the Worker runs, proved equal to Python by the golden vectors, and it is never sent anywhere:
// not to our store, not to the sandbox, not into any count. It lives in this tab's session
// storage so /city can show it as a demo creek, and goes when the tab closes.
import { checkBundle } from "../../../worker/src/core/fhir_emit";
import { MEASURE_FOR_FEATURE, findingsFromVisits, needsFromFindings, type Finding, type Need } from "../../../worker/src/core/act";
import { walkBundle, walkVisit, type WalkRef } from "../../../worker/src/core/walks";
import type { AnswerValue, VisitRecord } from "../../../worker/src/core/types";
// The approved sentences as the Worker's ports read them. core_content.json carries no gold key;
// the full worker/src/content.json does, and must never be imported here.
import CORE_CONTENT from "../../../worker/src/core/core_content.json";
import { content, type Walk } from "./content";

const KEY = "second-look.walks";

/** Answers as the emitter takes them. FormQuestion sends every value in one of these shapes. */
export type WalkAnswers = Record<string, AnswerValue>;

export interface WalkVisitSaved {
  walk_id: string;
  answers: Record<string, AnswerValue>;
  answered_at: string;
}

function ref(walk: Walk): WalkRef {
  return { id: walk.id, spot_name: walk.spot_name, creek_name: walk.creek_name };
}

export function buildRecord(walk: Walk, answers: Record<string, AnswerValue>, answeredAt: string) {
  const bundle = walkBundle(ref(walk), answers, answeredAt);
  return { bundle, problems: checkBundle(bundle as never) };
}

export function saveWalkVisit(v: WalkVisitSaved): void {
  try {
    const all = savedWalkVisits().filter((x) => !(x.walk_id === v.walk_id && x.answered_at === v.answered_at));
    sessionStorage.setItem(KEY, JSON.stringify([...all, v]));
  } catch {
    // Private windows can refuse storage. The record on screen still stands; /city just has less.
  }
}

export function savedWalkVisits(): WalkVisitSaved[] {
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as WalkVisitSaved[]) : [];
  } catch {
    return [];
  }
}

/**
 * The last walk this tab finished for one clip, as a JSON string so React can compare it from one
 * render to the next, or null when there is none. The walk page opens on its record, so the
 * browser's Back from the city view no longer loses it (CRITIC_10 S01).
 */
export function lastWalkVisitJson(walkId: string): string | null {
  const mine = savedWalkVisits().filter((v) => v.walk_id === walkId);
  return mine.length ? JSON.stringify(mine[mine.length - 1]) : null;
}

/** Start again: forgets the walks this tab finished for one clip. The other clips keep theirs. */
export function clearWalkVisits(walkId: string): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(savedWalkVisits().filter((v) => v.walk_id !== walkId)));
  } catch {
    // Private windows can refuse storage. The screen still goes back to the start.
  }
}

/** True when one of OneAquaHealth's measures answers this finding. A plant has none (CRITIC_06 H01). */
export function hasMeasure(feature: string): boolean {
  return Object.prototype.hasOwnProperty.call(MEASURE_FOR_FEATURE, feature);
}

/** The feature the walk's city view uses for its example when the walks found nothing to fix. */
export const EXAMPLE_FEATURE = "artificial_bank";

/**
 * What one reported finding would ask of a city: the same function the city view runs on real
 * findings, over one made-up finding, so the measures and their sources come from the act rules
 * and the approved sentences, never from words written here (CRITIC_09 Q01).
 */
export function exampleNeeds(feature: string = EXAMPLE_FEATURE): Need[] {
  const finding: Finding = { spot_id: "example", feature, observers: [], visit_ids: [], first_seen: "", last_seen: "", passed_observers: [] };
  return needsFromFindings([finding], CORE_CONTENT.sentences as Record<string, unknown>[]);
}

/** The demo creek for /city: what the walks made on this device found, and what the creek needs. */
export function demoCreek(walk: Walk): { visits: VisitRecord[]; findings: Finding[]; needs: Need[] } {
  const visits = savedWalkVisits()
    .filter((v) => v.walk_id === walk.id)
    .map((v) => walkVisit(ref(walk), v.answers, v.answered_at));
  const findingKeyFor: Record<string, string> = {};
  for (const item of content.form.items) if (item.feature) findingKeyFor[item.id] = item.feature;
  const findings = findingsFromVisits(visits, findingKeyFor);
  // The approved sentences, with their sources, as the Worker has them; an unapproved one is absent.
  const needs = needsFromFindings(findings, CORE_CONTENT.sentences as Record<string, unknown>[]);
  return { visits, findings, needs };
}
