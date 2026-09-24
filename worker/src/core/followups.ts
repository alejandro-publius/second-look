// core/followups.py: follow-up questions chosen by code and never by a model (hard rule 3). A pure
// function of the human's answers, the site context, the observer's scores, the gate's flags and
// the priority table. Two questions at most. The checker is not wired on the Worker, so it passes
// no flags and checker_flag never fires there; the rule is ported whole so the golden vectors
// hold it to the Python, including that a flag on a feature the form has no item for asks nothing.

import CONTENT from "./core_content.json";
import { scoreFor, type AnswerValue, type FormItem, type Observer } from "./types";

export const DEFAULT_MAX_QUESTIONS = 2;
export const LOW_SCORE_MAX_CORRECT: number = CONTENT.rules.low_score_max_correct;
const FEATURES: readonly string[] = CONTENT.rules.features_in_order;
const PIPE_ITEMS: readonly string[] = CONTENT.rules.pipe_items;
const RATING_ISSUE_ITEMS: readonly string[] = CONTENT.rules.rating_issue_items;
const PRESENT = "present";
const ABSENT = "absent";
const BEST_RATING = "good";
const RATING_ITEM = "overall_rating";

export interface SiteContext {
  rain: "dry" | "wet" | "unknown";
  dry_days?: number | null;
  mm_in_window?: number | null;
}

export type FollowupKind = "yesno" | "keep_rating" | "look_again" | "photo";

export interface Followup {
  rule_id: string;
  kind: FollowupKind;
  question_key: string;
  params: Record<string, string | number>;
}

/** A Flag from core/gate.py, as the gate returns it. Only the gate makes one. */
export interface Flag {
  feature: string;
  confidence: number;
  note: string;
  region?: [number, number, number, number] | null;
}

type Answers = Record<string, AnswerValue>;
type Rule = Record<string, unknown>;

function itemById(formItems: FormItem[], id: string): FormItem | null {
  for (const item of formItems) if (item.id === id) return item;
  return null;
}

/** Plain label for something the person reported: short_label, the chosen option's label, the
 *  item text, else the id with spaces. Never model text. */
function issueLabel(item: FormItem | null, itemId: string, value: unknown): string {
  if (item === null) return itemId.replace(/_/g, " ");
  const short = item.short_label;
  if (typeof short === "string" && short.trim()) return short.trim();
  for (const option of (item.options ?? []) as Record<string, unknown>[]) {
    if (option && option.value === value) {
      const label = option.label;
      if (typeof label === "string" && label.trim()) return label.trim();
    }
  }
  const text = item.text;
  if (typeof text === "string" && text.trim()) return text.trim();
  return itemId.replace(/_/g, " ");
}

function dryPipe(rule: Rule, answers: Answers, site: SiteContext): Followup | null {
  if (site.rain !== "dry") return null;
  if (site.dry_days === null || site.dry_days === undefined || site.dry_days < 1) return null;
  if (!PIPE_ITEMS.some((item) => answers[item] === PRESENT)) return null;
  return {
    rule_id: "dry_pipe",
    kind: "yesno",
    question_key: String(rule.question_key ?? "followup.dry_pipe"),
    params: { days: Math.trunc(site.dry_days) },
  };
}

function ratingCheck(rule: Rule, answers: Answers, formItems: FormItem[]): Followup | null {
  if (answers[RATING_ITEM] !== BEST_RATING) return null;
  const issues: string[] = [];
  for (const itemId of RATING_ISSUE_ITEMS) {
    const value = answers[itemId];
    if (value === PRESENT) issues.push(issueLabel(itemById(formItems, itemId), itemId, value));
  }
  if (issues.length === 0) return null;
  return {
    rule_id: "rating_check",
    kind: "keep_rating",
    question_key: String(rule.question_key ?? "followup.rating_check"),
    params: { issues: issues.join(", "), first_rating: BEST_RATING },
  };
}

/** The features the creek check asks about: each one that a form item names. */
function askedFeatures(formItems: FormItem[]): Set<string> {
  const asked = new Set<string>();
  for (const item of formItems) if (typeof item.feature === "string" && FEATURES.includes(item.feature)) asked.add(item.feature);
  return asked;
}

function checkerFlag(rule: Rule, flags: Flag[], checkerEnabled: boolean, formItems: FormItem[]): Followup | null {
  if (!checkerEnabled) return null;
  // A flag on a feature the check has no question for (the dug-out channel today) makes nothing
  // eligible: the person was never asked about it, so there is nothing to look at again
  // (CRITIC_06 H02).
  const asked = askedFeatures(formItems);
  let chosen: Flag | null = null;
  for (const flag of flags) {
    if (!asked.has(flag.feature)) continue;
    // Python's max() keeps the first of equal confidences, so only a surer flag replaces it.
    if (chosen === null || flag.confidence > chosen.confidence) chosen = flag;
  }
  if (chosen === null) return null;
  return {
    rule_id: "checker_flag",
    kind: "look_again",
    question_key: String(rule.question_key ?? "followup.checker_flag"),
    params: { note: chosen.note, feature: chosen.feature },
  };
}

function lowScore(rule: Rule, answers: Answers, observer: Observer | null, formItems: FormItem[]): Followup | null {
  if (observer === null) return null;
  let best: [number, number, string, string] | null = null;
  formItems.forEach((item, position) => {
    const feature = item.feature;
    const itemId = item.id;
    if (typeof feature !== "string" || !FEATURES.includes(feature) || typeof itemId !== "string") return;
    if (answers[itemId] !== ABSENT) return;
    const score = scoreFor(observer, feature);
    if (score === null || score.correct > LOW_SCORE_MAX_CORRECT) return;
    const key: [number, number, string, string] = [score.correct, position, itemId, feature];
    if (best === null || lessThan(key, best)) best = key;
  });
  if (best === null) return null;
  const [correct, , itemId, feature] = best as [number, number, string, string];
  return {
    rule_id: "low_score",
    kind: "photo",
    question_key: String(rule.question_key ?? "followup.low_score"),
    params: { feature: feature.replace(/_/g, " "), feature_id: feature, item_id: itemId, correct },
  };
}

function lessThan(a: [number, number, string, string], b: [number, number, string, string]): boolean {
  for (let i = 0; i < 4; i++) {
    if (a[i] === b[i]) continue;
    return a[i] < b[i];
  }
  return false;
}

function rulesInPriority(table: Record<string, unknown>): Rule[] {
  const rules = table.rules;
  if (!Array.isArray(rules)) return [];
  const typed = rules.filter((r): r is Rule => r !== null && typeof r === "object" && typeof (r as Rule).id === "string");
  return typed.sort((a, b) => {
    const pa = Math.trunc(Number(a.priority ?? 0));
    const pb = Math.trunc(Number(b.priority ?? 0));
    if (pa !== pb) return pa - pb;
    return String(a.id) < String(b.id) ? -1 : String(a.id) > String(b.id) ? 1 : 0;
  });
}

/** Pure. At most table.max_questions (2). Priority order from the table. No model call. */
export function selectFollowups(
  answers: Answers,
  site: SiteContext,
  observer: Observer | null,
  flags: Flag[],
  table: Record<string, unknown>,
  formItems: FormItem[],
  checkerEnabled = false,
): Followup[] {
  const cap = Math.trunc(Number(table.max_questions ?? DEFAULT_MAX_QUESTIONS));
  if (cap <= 0) return [];
  const chosen: Followup[] = [];
  for (const rule of rulesInPriority(table)) {
    if (chosen.length >= cap) break;
    let followup: Followup | null = null;
    switch (rule.id) {
      case "dry_pipe":
        followup = dryPipe(rule, answers, site);
        break;
      case "rating_check":
        followup = ratingCheck(rule, answers, formItems);
        break;
      case "checker_flag":
        // A Flag can only make this question eligible. The Worker passes none today.
        followup = checkerFlag(rule, flags, checkerEnabled, formItems);
        break;
      case "low_score":
        followup = lowScore(rule, answers, observer, formItems);
        break;
      default:
        followup = null;
    }
    if (followup !== null && chosen.every((f) => f.rule_id !== followup!.rule_id)) chosen.push(followup);
  }
  return chosen.slice(0, cap);
}
