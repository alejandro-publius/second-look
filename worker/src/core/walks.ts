// Port of core/walks.py. A walk visit is built on the person's device. A finished walk is kept by
// the store as a demo record for WALK_KEEP_DAYS days, in a table of its own, and is never counted
// and never mirrored. Proved equal to Python by worker/golden/walks.json.

import { REPO_URL, emitVisit, escapeXml } from "./fhir_emit";
import { selectFollowups, type Followup, type SiteContext } from "./followups";
import { sha256Hex } from "./sha256";
import { instant, parseInstant, type AnswerValue, type CheckResult, type FormItem, type Json, type Spot, type VisitRecord } from "./types";

export const DEMO_TAG_SYSTEM = `${REPO_URL}/tags`;
export const DEMO_TAG_CODE = "demo-walk";
export const DEMO_TAG_DISPLAY = "Demo visit from a video walk. Never counted and never sent to the sandbox.";
export const WALK_PREFIX = "walk-";
const RATING_ITEM = "overall_rating";

// The stored demo record of a finished walk (UPDATE_30 section 1 item 3), the same five numbers
// as core/walks.py.
export const WALK_KEEP_DAYS = 30;
export const WALK_PAST_DAYS = 7;
export const WALK_FUTURE_SECONDS = 300;
export const WALK_DAILY_CAP = 200;
export const WALK_MAX_BYTES = 4096;
const ANSWERED_AT_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$/;
const DAY_MS = 86_400_000;

export interface WalkRef {
  id: string;
  spot_name: string;
  creek_name: string;
}

type Resource = { [key: string]: Json };

export function walkSpot(walk: WalkRef): Spot {
  const wid = `${WALK_PREFIX}${walk.id}`;
  return {
    spot_id: `${wid}-spot`,
    spot_name: walk.spot_name,
    reach_id: `${wid}-reach`,
    reach_name: walk.spot_name,
    creek_id: wid,
    creek_name: walk.creek_name,
    latitude: null,
    longitude: null,
    coarse: true,
  };
}

export function walkVisitId(walkId: string, answeredAt: string): string {
  return WALK_PREFIX + sha256Hex(`${walkId}|${instant(answeredAt)}`).slice(0, 16);
}

export function walkVisit(walk: WalkRef, answers: Record<string, AnswerValue>, answeredAt: string, language = "en"): VisitRecord {
  return {
    visit_id: walkVisitId(walk.id, answeredAt),
    spot: walkSpot(walk),
    observer: { contributor_token: `demo-walk-${walk.id}`, scores: [], test_sitting_id: null },
    answered_at: instant(answeredAt),
    answers: { ...answers },
    first_rating: null,
    final_rating: null,
    checks: [],
    photo_ids: [],
    software_version: "0.1.0",
    language,
  };
}

export function tagDemo(bundle: Resource): Resource {
  const out = JSON.parse(JSON.stringify(bundle)) as Resource;
  const tag = { system: DEMO_TAG_SYSTEM, code: DEMO_TAG_CODE, display: DEMO_TAG_DISPLAY };
  const nodes: Resource[] = [out, ...((out.entry as Resource[] | undefined) ?? []).map((e) => e.resource as Resource)];
  for (const node of nodes) {
    const meta = ((node.meta as Resource | undefined) ?? {}) as Resource;
    const kept = ((meta.tag as Resource[] | undefined) ?? []).filter((t) => t.system !== DEMO_TAG_SYSTEM);
    meta.tag = [...kept, { ...tag }];
    node.meta = meta;
  }
  return out;
}

function ratingChangedNote(first: string, final: string): string {
  return `The first overall rating was ${first}. On the rating check the volunteer changed it to ${final}.`;
}

/** The FHIR record of one walk visit, tagged as a demo. finalRating is the rating the rating check
 *  left (walkChecks): when it differs from the walk's own overall rating, the record answers the
 *  rating question with it and the response's narrative names the first rating (critic round 15
 *  F02). The answers stay as given. As core/walks.py walk_bundle. */
export function walkBundle(walk: WalkRef, answers: Record<string, AnswerValue>, answeredAt: string, finalRating: string | null = null, language = "en"): Resource {
  const first = answers[RATING_ITEM];
  const changed = typeof first === "string" && finalRating !== null && finalRating !== first;
  const rated = changed ? { ...answers, [RATING_ITEM]: finalRating as string } : answers;
  const bundle = emitVisit(walkVisit(walk, rated, answeredAt, language), null, instant(answeredAt)) as Resource;
  if (changed) {
    for (const entry of bundle.entry as Resource[]) {
      const resource = entry.resource as Resource;
      if (resource.resourceType !== "QuestionnaireResponse") continue;
      const text = resource.text as Resource;
      const note = escapeXml(ratingChangedNote(first as string, finalRating as string));
      text.div = String(text.div).replace("</p></div>", `</p><p>${note}</p></div>`);
    }
  }
  return tagDemo(bundle);
}

export function isDemo(bundle: Resource): boolean {
  const tags = (((bundle.meta as Resource | undefined)?.tag as Resource[] | undefined) ?? []);
  return tags.some((t) => t.system === DEMO_TAG_SYSTEM && t.code === DEMO_TAG_CODE);
}

/** A finished walk the store will not keep. The message is plain and says why. */
export class WalkRecordError extends Error {}

/** The moment a walk was finished, as the phone sent it, checked against the server's clock:
 *  a time with a zone, at most WALK_FUTURE_SECONDS ahead, at most WALK_PAST_DAYS old. */
export function walkAnsweredAt(text: unknown, now: string): string {
  if (typeof text !== "string" || !ANSWERED_AT_RE.test(text)) throw new WalkRecordError("answered_at must be a time like 2026-09-25T10:00:00Z.");
  const at = parseInstant(text);
  const clock = parseInstant(now);
  if (at > clock + WALK_FUTURE_SECONDS * 1000) throw new WalkRecordError("That walk is dated in the future. Check the phone's clock.");
  if (at < clock - WALK_PAST_DAYS * DAY_MS) throw new WalkRecordError(`That walk is more than ${WALK_PAST_DAYS} days old, so it is not stored.`);
  return instant(at);
}

export interface WalkRecordRow {
  record_id: string;
  walk_id: string;
  answered_at: string;
  created_at: string;
  delete_after: string;
  bundle: Resource;
}

/** The row the store keeps for a finished walk. Its id is the walk visit's own id, so the stored
 *  record is the one the phone built, and the same walk sent twice is one record. The caller
 *  checks the answers against the form first (worker/src/check.ts validateAnswers), and the final
 *  rating with walkChecks, whose final rating the Bundle carries. */
export function walkRecord(walk: WalkRef, answers: Record<string, AnswerValue>, answeredAt: unknown, now: string, finalRating: string | null = null, language = "en"): WalkRecordRow {
  const at = walkAnsweredAt(answeredAt, now);
  const clock = parseInstant(now);
  return {
    record_id: walkVisitId(walk.id, at),
    walk_id: walk.id,
    answered_at: at,
    created_at: instant(clock),
    delete_after: instant(clock + WALK_KEEP_DAYS * DAY_MS),
    bundle: walkBundle(walk, answers, at, finalRating, language),
  };
}

// The follow-up questions of a walk (judge walk W01): the creek check's own rules over the walk's
// answers, as core/walks.py. A clip has no place and no weather, so rain is unknown and the dry
// pipe rule fails closed; nobody took the test for the walk, so there is no score; the checker's
// flag on a clip is the walk's own build-time question, so no flag goes in. Proved equal to
// Python by worker/golden/walks.json.
export const WALK_SITE: SiteContext = { rain: "unknown" };
/** The answers each kind of follow-up takes on a walk. A walk uploads nothing. */
export const WALK_FOLLOWUP_ANSWERS: Record<string, readonly string[]> = {
  yesno: ["yes", "no", "cant_tell", "skipped"],
  keep_rating: ["keep", "change", "skipped"],
  look_again: ["looked", "skipped"],
  photo: ["skipped"],
};

/** The follow-ups a walk asks: selectFollowups with rain unknown, no score and no flag. */
export function walkFollowups(answers: Record<string, AnswerValue>, table: Record<string, unknown>, formItems: FormItem[]): Followup[] {
  return selectFollowups(answers, WALK_SITE, null, [], table, formItems, false);
}

/** The checks a finished walk ran, with what the person answered, and its final rating, kept as
 *  the creek check keeps them. Throws WalkRecordError with the same plain reasons as Python. The
 *  caller checks finalRating is one of the form's ratings. */
export function walkChecks(
  answers: Record<string, AnswerValue>,
  followups: Followup[],
  questionTexts: string[],
  given: Record<string, unknown>,
  finalRating: string | null,
): { checks: CheckResult[]; final_rating: string | null } {
  if (questionTexts.length !== followups.length) throw new WalkRecordError("Every follow-up needs its question.");
  const asked = new Set(followups.map((f) => f.rule_id));
  for (const ruleId of Object.keys(given)) {
    if (!asked.has(ruleId)) throw new WalkRecordError(`No follow-up called '${ruleId}' was asked in this walk.`);
  }
  const first = answers[RATING_ITEM];
  const firstRating = typeof first === "string" ? first : null;
  let final = firstRating;
  const checks: CheckResult[] = followups.map((f, i) => {
    const raw = given[f.rule_id];
    let answer: string | null = null;
    if (raw !== undefined && raw !== null) {
      const allowed = WALK_FOLLOWUP_ANSWERS[f.kind] ?? [];
      if (typeof raw !== "string" || !allowed.includes(raw)) throw new WalkRecordError(`${f.rule_id}: answer ${allowed.join(", ")}.`);
      answer = raw;
    }
    if (f.kind === "keep_rating" && answer === "change") {
      if (finalRating === null) throw new WalkRecordError("A changed rating needs the new rating.");
      final = finalRating;
    }
    const detail: Record<string, string | number | null> = {};
    for (const [k, v] of Object.entries(f.params)) detail[k] = typeof v === "string" || typeof v === "number" ? v : String(v);
    detail.kind = f.kind;
    return { rule_id: f.rule_id, asked: true, question_text: questionTexts[i], answer, detail };
  });
  if (finalRating !== null && finalRating !== final) throw new WalkRecordError("The final rating can differ from the first only when the rating check says change.");
  return { checks, final_rating: final };
}
