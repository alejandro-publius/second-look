// Video walks (Update 14 3.7). The record is built here by the same emitter the Worker runs,
// proved equal to Python by the golden vectors. While the walk is being made its answers wait in
// IndexedDB beside the creek check's offline queue (lib/offline.ts), keyed by the walk's id, so
// Back, a reload or a closed tab opens it where it was (UPDATE_30 section 1 item 2). Once it is
// finished, the offline queue sends it to our store, which keeps it as a demo record for 30 days
// so its link opens on any device (item 3). It is never counted and never sent to the sandbox.
import { checkBundle } from "../../../worker/src/core/fhir_emit";
import { MEASURE_FOR_FEATURE, findingsFromVisits, needsFromFindings, type Finding, type Need } from "../../../worker/src/core/act";
import type { Followup as RuleFollowup } from "../../../worker/src/core/followups";
import { walkBundle, walkChecks, walkFollowups, walkVisit, type WalkRef } from "../../../worker/src/core/walks";
import type { AnswerValue, CheckResult, FormItem as CoreFormItem, VisitRecord } from "../../../worker/src/core/types";
// The approved sentences as the Worker's ports read them. core_content.json carries no gold key;
// the full worker/src/content.json does, and must never be imported here.
import CORE_CONTENT from "../../../worker/src/core/core_content.json";
import type { AnswerValue as FormAnswer, Followup } from "./api";
import { content, featureById, type Walk } from "./content";
import { loadWalkState } from "./offline";
import { t } from "./t";

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

/** The walk's FHIR record, as the store builds it: with the rating the rating check left, which
 *  the record answers the rating question with when it was changed (critic round 15 F02). */
export function buildRecord(walk: Walk, answers: Record<string, FormAnswer>, answeredAt: string, finalRating: string | null = null) {
  const bundle = walkBundle(ref(walk), answers as WalkAnswers, answeredAt, finalRating);
  return { bundle, problems: bundleProblems(bundle) };
}

/** The references inside a Bundle that do not resolve, by the emitter's own check. */
export function bundleProblems(bundle: Record<string, unknown>): string[] {
  return checkBundle(bundle as never);
}

/**
 * The follow-up questions a walk asks (judge walk W01): the creek check's own rules over the walk's
 * answers, through the same port the store runs (worker/src/core/walks.ts walkFollowups), with each
 * question worded as the store words it (worker/src/check.ts questionText): the locale string
 * filled from the rule's params, a feature by its name. Rain is unknown for a clip, so the dry
 * pipe question is never asked; the rating check is.
 */
export function walkQuestions(answers: Record<string, FormAnswer>): { rule: RuleFollowup; card: Followup }[] {
  const chosen = walkFollowups(answers as WalkAnswers, CORE_CONTENT.followups as Record<string, unknown>, CORE_CONTENT.form_items as CoreFormItem[]);
  return chosen.map((rule) => {
    const params: Record<string, string | number> = { ...rule.params };
    if ("feature" in params) {
      const raw = String(params.feature).trim();
      params.feature = featureById(raw.replace(/ /g, "_"))?.name ?? raw;
    }
    return { rule, card: { rule_id: rule.rule_id, question_text: t(rule.question_key, params), kind: rule.kind } };
  });
}

/** What the store keeps for a walk's follow-ups, and what its record shows under "Checks that ran". */
export interface WalkKept {
  checks: CheckResult[];
  first_rating: string | null;
  final_rating: string | null;
}

/**
 * The follow-up answers to send with a finished walk, and the checks they make, as the store will
 * keep them (worker/src/core/walks.ts walkChecks). Answers to a question the answers no longer ask,
 * after the person went back and changed them, are left out, and a new rating goes only with a
 * rating check answered "change", so what is sent is always what the store takes.
 */
export function settleFollowups(
  answers: Record<string, FormAnswer>,
  given: Record<string, string>,
  finalRating: string | null,
): { followup_answers: Record<string, string>; final_rating: string | null; kept: WalkKept } {
  const asked = walkQuestions(answers);
  const followup_answers: Record<string, string> = {};
  for (const q of asked) {
    const answer = given[q.rule.rule_id];
    if (answer === undefined) continue;
    // A change with no new rating is no answer yet: the picker was opened and nothing picked.
    if (q.rule.kind === "keep_rating" && answer === "change" && finalRating === null) continue;
    followup_answers[q.rule.rule_id] = answer;
  }
  const changed = asked.some((q) => q.rule.kind === "keep_rating" && followup_answers[q.rule.rule_id] === "change");
  const final_rating = changed ? finalRating : null;
  const rules = asked.map((q) => q.rule);
  const texts = asked.map((q) => q.card.question_text);
  let out: { checks: CheckResult[]; final_rating: string | null };
  try {
    out = walkChecks(answers as WalkAnswers, rules, texts, followup_answers, final_rating);
  } catch {
    // Only an answer the buttons never give gets here; the questions are kept, unanswered.
    out = walkChecks(answers as WalkAnswers, rules, texts, {}, null);
    return { followup_answers: {}, final_rating: null, kept: { checks: out.checks, first_rating: firstRating(answers), final_rating: out.final_rating } };
  }
  return { followup_answers, final_rating, kept: { checks: out.checks, first_rating: firstRating(answers), final_rating: out.final_rating } };
}

function firstRating(answers: Record<string, FormAnswer>): string | null {
  return typeof answers.overall_rating === "string" ? answers.overall_rating : null;
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
