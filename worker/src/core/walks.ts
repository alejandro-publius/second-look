// Port of core/walks.py. A walk visit is built on the person's device. A finished walk is kept by
// the store as a demo record for WALK_KEEP_DAYS days, in a table of its own, and is never counted
// and never mirrored. Proved equal to Python by worker/golden/walks.json.

import { REPO_URL, emitVisit } from "./fhir_emit";
import { sha256Hex } from "./sha256";
import { instant, parseInstant, type AnswerValue, type Json, type Spot, type VisitRecord } from "./types";

export const DEMO_TAG_SYSTEM = `${REPO_URL}/tags`;
export const DEMO_TAG_CODE = "demo-walk";
export const DEMO_TAG_DISPLAY = "Demo visit from a video walk. Never counted and never sent to the sandbox.";
export const WALK_PREFIX = "walk-";

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

export function walkVisit(walk: WalkRef, answers: Record<string, AnswerValue>, answeredAt: string): VisitRecord {
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

export function walkBundle(walk: WalkRef, answers: Record<string, AnswerValue>, answeredAt: string): Resource {
  const visit = walkVisit(walk, answers, answeredAt);
  return tagDemo(emitVisit(visit, null, instant(answeredAt)) as Resource);
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
 *  checks the answers against the form first (worker/src/check.ts validateAnswers). */
export function walkRecord(walk: WalkRef, answers: Record<string, AnswerValue>, answeredAt: unknown, now: string): WalkRecordRow {
  const at = walkAnsweredAt(answeredAt, now);
  const clock = parseInstant(now);
  return {
    record_id: walkVisitId(walk.id, at),
    walk_id: walk.id,
    answered_at: at,
    created_at: instant(clock),
    delete_after: instant(clock + WALK_KEEP_DAYS * DAY_MS),
    bundle: walkBundle(walk, answers, at),
  };
}
