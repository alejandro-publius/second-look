// GET /api/inaturalist/{creek} on the Worker: the iNaturalist context line for one creek, read
// from the copy scripts/cache_inaturalist.py stored in D1. A port of apps/api/inaturalist.py; the
// two answer in the same shape. The Worker never asks iNaturalist itself: the Mac does, once a
// day, at most one request a second, with a user agent that names this project.
//
// Context only, by construction. The sightings are withheld until the creek's record holds an
// answer to the invasive plant question, so they cannot lead anyone's answer. Nothing counts them,
// and this file imports nothing that decides: not ./check, which reaches the follow-up rules, and
// not ./core/followups. scripts/tests/test_inaturalist.py walks the imports to prove it.

import { looksLikeATestName } from "./core/act";
import { CREEKS, creekBySlug, placeSpot, type Creek } from "./core/regions";
import type { Spot } from "./core/types";

// The form item that asks about invasive plants (content/form.yaml).
export const INVASIVE_ITEM = "invasive_species";
export const SOURCE = "https://www.inaturalist.org";
export const TERMS = "https://www.inaturalist.org/pages/terms";
const LINK_PREFIX = "https://www.inaturalist.org/observations";

interface InatEnv {
  DB: D1Database;
}

interface SpotRowLite {
  spot_id: string;
  spot_name: string;
  reach_id: string;
  reach_name: string;
  creek_id: string;
  creek_name: string;
  latitude: number | null;
  longitude: number | null;
  coarse: number;
}

export interface InatSpecies {
  taxon_id: unknown;
  name: string;
  latin_name: string;
  count: number;
  last_observed: string;
  url: string;
}

function asSpot(row: SpotRowLite): Spot {
  return {
    spot_id: row.spot_id,
    spot_name: row.spot_name,
    reach_id: row.reach_id,
    reach_name: row.reach_name,
    creek_id: row.creek_id,
    creek_name: row.creek_name,
    latitude: row.latitude,
    longitude: row.longitude,
    coarse: Boolean(row.coarse),
  };
}

/** The cache key for a creek reference and the real spots on that creek, read as /api/city reads it. */
export async function creekSpots(env: InatEnv, creekRef: string): Promise<{ key: string; spots: SpotRowLite[] }> {
  const rows = (await env.DB.prepare("SELECT spot_id, spot_name, reach_id, reach_name, creek_id, creek_name, latitude, longitude, coarse FROM spot ORDER BY created_at").all<SpotRowLite>()).results ?? [];
  const placed = new Map(rows.map((r) => [r.spot_id, placeSpot(asSpot(r), CREEKS)]));
  let creek: Creek | null = creekBySlug(creekRef);
  let spots: SpotRowLite[];
  if (creek !== null) {
    const slug = creek.slug;
    spots = rows.filter((r) => placed.get(r.spot_id)?.creek.slug === slug);
  } else {
    spots = rows.filter((r) => r.creek_id === creekRef);
    const on = new Set(spots.map((r) => placed.get(r.spot_id)?.creek.slug).filter((x): x is string => Boolean(x)));
    creek = on.size === 1 ? creekBySlug([...on][0]) : null;
  }
  return { key: creek?.slug ?? creekRef, spots: spots.filter((r) => !looksLikeATestName(r.spot_name)) };
}

/** True when a finished visit at one of these spots answered the invasive plant question. */
export async function invasiveAnswered(env: InatEnv, spotIds: string[]): Promise<boolean> {
  if (spotIds.length === 0) return false;
  const marks = spotIds.map(() => "?").join(",");
  const rows = (await env.DB.prepare(`SELECT answers_json FROM visit WHERE spot_id IN (${marks}) AND finalized_at IS NOT NULL`).bind(...spotIds).all<{ answers_json: string }>()).results ?? [];
  for (const r of rows) {
    const answers = JSON.parse(r.answers_json) as Record<string, unknown> | null;
    const value = answers && typeof answers === "object" ? answers[INVASIVE_ITEM] : undefined;
    if (value !== undefined && value !== null && value !== "") return true;
  }
  return false;
}

/** Only the fields the page shows, and only links that go to iNaturalist's observations. */
export function cleanSpecies(raw: unknown): InatSpecies[] {
  const out: InatSpecies[] = [];
  for (const s of Array.isArray(raw) ? raw : []) {
    if (!s || typeof s !== "object") continue;
    const item = s as Record<string, unknown>;
    const url = String(item.url ?? "");
    const count = item.count;
    if (!url.startsWith(LINK_PREFIX) || typeof count !== "number" || !Number.isInteger(count) || count < 1) continue;
    out.push({
      taxon_id: item.taxon_id ?? null,
      name: String(item.name ?? ""),
      latin_name: String(item.latin_name ?? ""),
      count,
      last_observed: String(item.last_observed ?? ""),
      url,
    });
  }
  return out;
}

export async function inaturalistView(env: InatEnv, creekRef: string) {
  const { key, spots } = await creekSpots(env, creekRef);
  const shown = await invasiveAnswered(env, spots.map((s) => s.spot_id));
  const row = await env.DB.prepare("SELECT body, fetched_at FROM inaturalist_cache WHERE creek = ?").bind(key).first<{ body: string; fetched_at: string }>();
  let body: Record<string, unknown> = {};
  if (row !== null) {
    try {
      const parsed = JSON.parse(row.body) as unknown;
      body = parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : {};
    } catch {
      body = {};
    }
  }
  return {
    creek: key,
    shown,
    status: row !== null ? "cached" : "none",
    fetched_at: row !== null ? row.fetched_at : null,
    since: body.since ?? null,
    radius_m: body.radius_m ?? null,
    // Withheld until the invasive plant question is answered on this creek's record.
    species: shown ? cleanSpecies(body.species) : [],
    source: SOURCE,
    terms: TERMS,
  };
}
