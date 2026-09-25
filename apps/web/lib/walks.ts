// Video walks (Update 14 3.7). The record is built here by the same emitter the Worker runs,
// proved equal to Python by the golden vectors. While the walk is being made its answers wait in
// IndexedDB beside the creek check's offline queue (lib/offline.ts), keyed by the walk's id, so
// Back, a reload or a closed tab opens it where it was (UPDATE_30 section 1 item 2). Once it is
// finished, the offline queue sends it to our store, which keeps it as a demo record for 30 days
// so its link opens on any device (item 3). It is never counted and never sent to the sandbox.
import { checkBundle } from "../../../worker/src/core/fhir_emit";
import { MEASURE_FOR_FEATURE, findingsFromVisits, needsFromFindings, type Finding, type Need } from "../../../worker/src/core/act";
import { walkBundle, walkVisit, type WalkRef } from "../../../worker/src/core/walks";
import type { AnswerValue, VisitRecord } from "../../../worker/src/core/types";
// The approved sentences as the Worker's ports read them. core_content.json carries no gold key;
// the full worker/src/content.json does, and must never be imported here.
import CORE_CONTENT from "../../../worker/src/core/core_content.json";
import type { AnswerValue as FormAnswer } from "./api";
import { content, type Walk } from "./content";
import { loadWalkState } from "./offline";

/** Answers as the emitter takes them. FormQuestion sends every value in one of these shapes. */
export type WalkAnswers = Record<string, AnswerValue>;

/** A finished walk: its answers and when it was finished, from this device or from the store. */
export interface WalkVisitSaved {
  walk_id: string;
  answers: Record<string, FormAnswer>;
  answered_at: string;
}

function ref(walk: Walk): WalkRef {
  return { id: walk.id, spot_name: walk.spot_name, creek_name: walk.creek_name };
}

export function buildRecord(walk: Walk, answers: Record<string, FormAnswer>, answeredAt: string) {
  const bundle = walkBundle(ref(walk), answers as WalkAnswers, answeredAt);
  return { bundle, problems: bundleProblems(bundle) };
}

/** The references inside a Bundle that do not resolve, by the emitter's own check. */
export function bundleProblems(bundle: Record<string, unknown>): string[] {
  return checkBundle(bundle as never);
}

/** The walk this device finished for one clip, or none. Start again forgets it. */
export async function finishedWalk(walkId: string): Promise<WalkVisitSaved | null> {
  const state = await loadWalkState(walkId);
  if (!state || !state.answered_at) return null;
  return { walk_id: walkId, answers: state.answers, answered_at: state.answered_at };
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

/**
 * The demo creek for /city: what the walks found, and what the creek needs. The walks are the one
 * this device finished and any stored record whose link was opened; one walk is counted once.
 */
export function demoCreek(walk: Walk, saved: WalkVisitSaved[]): { visits: VisitRecord[]; findings: Finding[]; needs: Need[] } {
  const byId = new Map<string, VisitRecord>();
  for (const v of saved.filter((x) => x.walk_id === walk.id)) {
    const visit = walkVisit(ref(walk), v.answers as WalkAnswers, v.answered_at);
    byId.set(visit.visit_id, visit);
  }
  const visits = [...byId.values()];
  const findingKeyFor: Record<string, string> = {};
  for (const item of content.form.items) if (item.feature) findingKeyFor[item.id] = item.feature;
  const findings = findingsFromVisits(visits, findingKeyFor);
  // The approved sentences, with their sources, as the Worker has them; an unapproved one is absent.
  const needs = needsFromFindings(findings, CORE_CONTENT.sentences as Record<string, unknown>[]);
  return { visits, findings, needs };
}
