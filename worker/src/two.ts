// GET /api/two on the Worker: one volunteer Observation of ours beside one laboratory Observation
// from their sandbox. A port of apps/api/fhir_routes.py. Their record is fetched with a user agent
// that names the repository, kept in D1 for an hour so the screen still works when the sandbox is
// down, and never written to git. If the sandbox does not answer, the screen says so and shows
// ours alone.

import GOLDEN from "../../fhir/golden/visit-strawberry-creek-1.json";
import { latestBundle } from "./check";
import { OAH_SYSTEM, REPO_URL, SL_SYSTEM } from "./core/fhir_emit";
import { sha256Hex } from "./core/sha256";

export const SANDBOX_DEFAULT_BASE = "https://sandbox.hl7europe.eu/oneaquahealth/fhir";
const USER_AGENT = `second-look (+${REPO_URL})`;
const TIMEOUT_MS = 10_000;
const CACHE_LIFETIME_MS = 3_600_000;
const THEIRS_LOCATION = "Location/Loc-Almyros";
const THEIRS_CODE = "dissolved-oxygen";

interface TwoEnv {
  DB: D1Database;
  SANDBOX_BASE_URL?: string;
  SANDBOX_THEIRS_CODE?: string;
}

type Resource = Record<string, unknown>;

function theirsQuery(env: TwoEnv): Record<string, string> {
  return { subject: THEIRS_LOCATION, code: `${OAH_SYSTEM}|${env.SANDBOX_THEIRS_CODE ?? THEIRS_CODE}`, _sort: "-date", _count: "1" };
}

function observations(bundle: Resource): Resource[] {
  return ((bundle.entry ?? []) as Resource[]).map((e) => e.resource as Resource).filter((r) => r && r.resourceType === "Observation");
}

/** One of our Observations: a feature answer from the latest stored visit, else the golden. */
export async function ours(env: TwoEnv): Promise<Resource | null> {
  const bundle = (await latestBundle(env.DB)) ?? (GOLDEN as unknown as Resource);
  const list = observations(bundle);
  for (const obs of list) {
    const coding = (((obs.code as Resource | undefined)?.coding ?? []) as Resource[])[0];
    if (coding && coding.system === SL_SYSTEM) return obs;
  }
  return list[0] ?? null;
}

async function fetchTheirsLive(env: TwoEnv): Promise<Resource | null> {
  const base = (env.SANDBOX_BASE_URL ?? SANDBOX_DEFAULT_BASE).replace(/\/$/, "");
  if (base.includes("api.enora-oah.eu")) return null; // hard rule 9: never that host
  const url = `${base}/Observation?${new URLSearchParams(theirsQuery(env)).toString()}`;
  try {
    const response = await fetch(url, { headers: { "User-Agent": USER_AGENT, Accept: "application/fhir+json" }, signal: AbortSignal.timeout(TIMEOUT_MS) });
    if (response.status !== 200) return null;
    const body = (await response.json()) as Resource;
    if (!body || typeof body !== "object") return null;
    if (body.resourceType === "Observation") return body;
    if (body.resourceType === "Bundle") {
      for (const entry of (body.entry ?? []) as Resource[]) {
        const resource = entry.resource as Resource | undefined;
        if (resource && resource.resourceType === "Observation") return resource;
      }
    }
    return null;
  } catch {
    return null;
  }
}

export async function theirs(env: TwoEnv, nowMs: number): Promise<{ observation: Resource | null; status: "ok" | "cached" | "down"; fetched_at: string }> {
  const key = `theirs-${sha256Hex(JSON.stringify(theirsQuery(env))).slice(0, 16)}`;
  const cached = await env.DB.prepare("SELECT body, fetched_at FROM sandbox_cache WHERE cache_key = ?").bind(key).first<{ body: string; fetched_at: string }>();
  if (cached !== null && nowMs - Date.parse(cached.fetched_at) < CACHE_LIFETIME_MS) {
    return { observation: JSON.parse(cached.body) as Resource, status: "cached", fetched_at: cached.fetched_at };
  }
  const nowIso = new Date(nowMs).toISOString().replace(/\.\d{3}Z$/, "Z");
  const live = await fetchTheirsLive(env);
  if (live === null) return { observation: null, status: "down", fetched_at: nowIso };
  await env.DB.prepare("INSERT OR REPLACE INTO sandbox_cache (cache_key, body, status, fetched_at) VALUES (?, ?, 'ok', ?)").bind(key, JSON.stringify(live), nowIso).run();
  return { observation: live, status: "ok", fetched_at: nowIso };
}

export async function two(env: TwoEnv, nowMs: number) {
  const t = await theirs(env, nowMs);
  return { ours: await ours(env), theirs: t.observation, theirs_status: t.status, fetched_at: t.fetched_at };
}
