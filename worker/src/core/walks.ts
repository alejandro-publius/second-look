// Port of core/walks.py. A walk visit is built on the person's device and never stored, so it is
// never counted and never mirrored. Proved equal to Python by worker/golden/walks.json.

import { REPO_URL, emitVisit } from "./fhir_emit";
import { sha256Hex } from "./sha256";
import { instant, type AnswerValue, type Json, type Spot, type VisitRecord } from "./types";

export const DEMO_TAG_SYSTEM = `${REPO_URL}/tags`;
export const DEMO_TAG_CODE = "demo-walk";
export const DEMO_TAG_DISPLAY = "Demo visit from a video walk. Made on the device, never stored or counted.";
export const WALK_PREFIX = "walk-";

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
