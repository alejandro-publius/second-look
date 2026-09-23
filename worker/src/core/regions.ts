// core/regions.py: which creek and reach a stored spot sits on, from the region pack's creeks in
// content.json. The pack is validated when Python builds that file, so this only reads it.

import CONTENT from "./core_content.json";
import type { Spot } from "./types";

export interface Reach {
  slug: string;
  name: string;
  flows_into: string | null;
  bbox: [number, number, number, number] | null;
}

export interface Creek {
  slug: string;
  name: string;
  source: string;
  reaches: Reach[];
}

export interface Placement {
  creek: Creek;
  reach: Reach | null;
}

export const CREEKS: Creek[] = CONTENT.creeks as Creek[];

export function creekBySlug(slug: string, creeks: Creek[] = CREEKS): Creek | null {
  for (const c of creeks) if (c.slug === slug) return c;
  return null;
}

export function reachOf(creek: Creek, slug: string): Reach | null {
  for (const r of creek.reaches) if (r.slug === slug) return r;
  return null;
}

function inBox(box: [number, number, number, number] | null, lat: number, lon: number): boolean {
  if (box === null) return false;
  const [south, west, north, east] = box;
  return south <= lat && lat <= north && west <= lon && lon <= east;
}

export function creekBbox(creek: Creek): [number, number, number, number] | null {
  const boxes = creek.reaches.map((r) => r.bbox).filter((b): b is [number, number, number, number] => b !== null);
  if (boxes.length === 0) return null;
  return [
    Math.min(...boxes.map((b) => b[0])),
    Math.min(...boxes.map((b) => b[1])),
    Math.max(...boxes.map((b) => b[2])),
    Math.max(...boxes.map((b) => b[3])),
  ];
}

/** Every reach downstream of this one, nearest first, following flows_into to the end. */
export function reachesBelow(reach: Reach, creek: Creek): Reach[] {
  const out: Reach[] = [];
  const seen = new Set([reach.slug]);
  let current = reach;
  while (current.flows_into !== null) {
    const next = reachOf(creek, current.flows_into);
    if (next === null) throw new Error(`creek ${creek.slug}: reach ${current.flows_into} does not exist`);
    if (seen.has(next.slug)) throw new Error(`creek ${creek.slug}: reaches flow in a circle at ${next.slug}`);
    seen.add(next.slug);
    out.push(next);
    current = next;
  }
  return out;
}

const named = (text: string, name: string) => text.toLowerCase().includes(name.toLowerCase());

function reachByName(spot: Spot, creek: Creek): Reach | null {
  for (const reach of creek.reaches) {
    if (named(spot.reach_name, reach.name) || named(spot.spot_name, reach.name)) return reach;
  }
  return null;
}

/** A precise pin inside a reach box; then any pin inside a creek box; then the creek's name in
 *  the spot's names. A coarse pin is placed on the creek only, unless the person named the reach. */
export function placeSpot(spot: Spot, creeks: Creek[] = CREEKS): Placement | null {
  const lat = spot.latitude;
  const lon = spot.longitude;
  if (lat !== null && lon !== null) {
    if (!spot.coarse) {
      for (const creek of creeks) for (const reach of creek.reaches) if (inBox(reach.bbox, lat, lon)) return { creek, reach };
    }
    for (const creek of creeks) if (inBox(creekBbox(creek), lat, lon)) return { creek, reach: reachByName(spot, creek) };
  }
  for (const creek of creeks) {
    if (named(spot.creek_name, creek.name) || named(spot.spot_name, creek.name)) return { creek, reach: reachByName(spot, creek) };
  }
  return null;
}
