// Video walks, on the device only (Update 14 3.7). The record is built here by the same emitter
// the Worker runs, proved equal to Python by the golden vectors, and it is never sent anywhere:
// not to our store, not to the sandbox, not into any count. It lives in this tab's session
// storage so /city can show it as a demo creek, and goes when the tab closes.
import { checkBundle } from "../../../worker/src/core/fhir_emit";
import { findingsFromVisits, needsFromFindings, type Finding, type Need } from "../../../worker/src/core/act";
import { walkBundle, walkVisit, type WalkRef } from "../../../worker/src/core/walks";
import type { AnswerValue, VisitRecord } from "../../../worker/src/core/types";
import WORKER_CONTENT from "../../../worker/src/content.json";
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

/** The demo creek for /city: what the walks made on this device found, and what the creek needs. */
export function demoCreek(walk: Walk): { visits: VisitRecord[]; findings: Finding[]; needs: Need[] } {
  const visits = savedWalkVisits()
    .filter((v) => v.walk_id === walk.id)
    .map((v) => walkVisit(ref(walk), v.answers, v.answered_at));
  const findingKeyFor: Record<string, string> = {};
  for (const item of content.form.items) if (item.feature) findingKeyFor[item.id] = item.feature;
  const findings = findingsFromVisits(visits, findingKeyFor);
  // The approved sentences, with their sources, as the Worker has them; an unapproved one is absent.
  const needs = needsFromFindings(findings, WORKER_CONTENT.sentences as Record<string, unknown>[]);
  return { visits, findings, needs };
}
