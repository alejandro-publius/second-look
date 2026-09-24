// GET /api/two on the Worker: one volunteer Observation of ours beside one laboratory Observation
// from their sandbox. A port of apps/api/fhir_routes.py, with one difference: the Worker never
// fetches their record itself. On 2026-09-23 the Worker's fetch got HTTP 530, "error code: 1016"
// (Cloudflare's origin DNS error): the sandbox's name had dropped out of their DNS (NXDOMAIN at
// their own nameserver), and the Mac reached it only from a cached answer. So
// scripts/cache_their_records.py fetches it on the Mac once a day and stores it in D1, and the
// Worker shows what that script stored, with the time it was fetched. If nothing is stored yet,
// the screen says so and shows ours alone. Their record is never written to git.

import GOLDEN from "../../fhir/golden/visit-strawberry-creek-1.json";
import { latestBundle } from "./check";
import { OAH_SYSTEM, SL_SYSTEM } from "./core/fhir_emit";
import { sha256Hex } from "./core/sha256";

const THEIRS_LOCATION = "Location/Loc-Almyros";
const THEIRS_CODE = "dissolved-oxygen";

interface TwoEnv {
  DB: D1Database;
  SANDBOX_THEIRS_CODE?: string;
}

type Resource = Record<string, unknown>;

function theirsQuery(env: TwoEnv): Record<string, string> {
  return { subject: THEIRS_LOCATION, code: `${OAH_SYSTEM}|${env.SANDBOX_THEIRS_CODE ?? THEIRS_CODE}`, _sort: "-date", _count: "1" };
}

function observations(bundle: Resource): Resource[] {
  return ((bundle.entry ?? []) as Resource[]).map((e) => e.resource as Resource).filter((r) => r && r.resourceType === "Observation");
}

/** The name of the Location an Observation is about, read from the same Bundle, so the page can
 *  say where in words and not show a raw id such as Location/sl-loc-spot-1. */
function placeOf(bundle: Resource, obs: Resource | null): string | null {
  const reference = String(((obs?.subject ?? {}) as Resource).reference ?? "");
  if (!reference.startsWith("Location/")) return null;
  const id = reference.slice("Location/".length);
  for (const e of (bundle.entry ?? []) as Resource[]) {
    const r = e.resource as Resource | undefined;
    if (r && r.resourceType === "Location" && r.id === id && typeof r.name === "string") return r.name;
  }
  return null;
}

/** One of our Observations: a feature answer from the latest stored visit. With no visit stored,
 *  the golden visit, which was made by hand for this demo: `example` says so, so the page can
 *  label it and never pass it off as a volunteer's answer (review REVIEW_03 R33). */
export async function ours(env: TwoEnv): Promise<{ observation: Resource | null; example: boolean; place: string | null }> {
  const stored = await latestBundle(env.DB);
  const bundle = stored ?? (GOLDEN as unknown as Resource);
  const list = observations(bundle);
  let pick: Resource | null = list[0] ?? null;
  for (const obs of list) {
    const coding = (((obs.code as Resource | undefined)?.coding ?? []) as Resource[])[0];
    if (coding && coding.system === SL_SYSTEM) {
      pick = obs;
      break;
    }
  }
  return { observation: pick, example: stored === null, place: placeOf(bundle, pick) };
}

/** The D1 key scripts/cache_their_records.py writes under. Both compute it the same way. */
export function theirsCacheKey(env: TwoEnv): string {
  return `theirs-${sha256Hex(JSON.stringify(theirsQuery(env))).slice(0, 16)}`;
}

export async function theirs(env: TwoEnv): Promise<{ observation: Resource | null; status: "cached" | "down"; fetched_at: string }> {
  const cached = await env.DB.prepare("SELECT body, fetched_at FROM sandbox_cache WHERE cache_key = ?").bind(theirsCacheKey(env)).first<{ body: string; fetched_at: string }>();
  if (cached === null) return { observation: null, status: "down", fetched_at: "" };
  return { observation: JSON.parse(cached.body) as Resource, status: "cached", fetched_at: cached.fetched_at };
}

export async function two(env: TwoEnv) {
  const t = await theirs(env);
  const o = await ours(env);
  return { ours: o.observation, ours_example: o.example, ours_place: o.place, theirs: t.observation, theirs_status: t.status, fetched_at: t.fetched_at };
}
