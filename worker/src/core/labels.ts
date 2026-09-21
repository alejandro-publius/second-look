// core/labels.py: what the analyst sees beside an answer. Raw k of 4 and the test date, or the
// expired sentence. No blended grade, no probability. Text from the locale.

import CONTENT from "../content.json";
import { daysBetween, parseDate, type FeatureScore } from "./types";

export const HUMAN_PASS_MIN: number = CONTENT.rules.human_pass_min;
export const SCORE_VALID_DAYS: number = CONTENT.rules.score_valid_days;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const KEY_SCORE = "label.score";
export const KEY_EXPIRED = "label.expired";

export interface Label {
  text: string;
  expired: boolean;
  passed: boolean | null;
}

/** "Sep 23" style, fixed English month names so the output does not depend on any locale. */
export function shortDate(day: string): string {
  const d = new Date(parseDate(day));
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}`;
}

export function expiredOn(score: FeatureScore, today: string): boolean {
  return daysBetween(score.tested_on, today) > SCORE_VALID_DAYS;
}

/** str.format with named fields, for the locale strings. */
export function fill(template: string, params: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (whole, name: string) => (name in params ? String(params[name]) : whole));
}

export function observerLabel(
  score: FeatureScore | null,
  featureName: string,
  today: string,
  locale: Record<string, string>,
): Label {
  if (score === null) return { text: "", expired: false, passed: null };
  const tested = shortDate(score.tested_on);
  const params = { correct: score.correct, total: score.total, feature: featureName, date: tested };
  if (expiredOn(score, today)) {
    return { text: fill(locale[KEY_EXPIRED], params), expired: true, passed: null };
  }
  return { text: fill(locale[KEY_SCORE], params), expired: false, passed: score.correct >= HUMAN_PASS_MIN };
}
