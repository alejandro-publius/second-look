// core/healthcard.py: one approved action each for the person, the pet and the city (hard rule 5).
// Only sentences with approved exactly true and a source. Code picks by a seeded hash so the same
// seed gives the same card. With any audience empty there is no card at all.

import { sha256Bytes } from "./sha256";
import { compareStrings } from "./types";

export const AUDIENCES = ["person", "pet", "city"] as const;
type Audience = (typeof AUDIENCES)[number];

export interface HealthCard {
  person: string;
  pet: string;
  city: string;
  sources: [string, string, string];
}

type Sentence = Record<string, unknown>;

function eligible(s: Sentence): boolean {
  const text = s.text;
  const source = s.source;
  return (
    s.approved === true &&
    typeof text === "string" &&
    text.trim().length > 0 &&
    typeof source === "string" &&
    source.trim().length > 0 &&
    (AUDIENCES as readonly string[]).includes(String(s.audience))
  );
}

function pickIndex(seed: string, audience: string, count: number): number {
  const digest = sha256Bytes(`${seed}:${audience}`);
  let value = 0n;
  for (let i = 0; i < 8; i++) value = (value << 8n) | BigInt(digest[i]);
  return Number(value % BigInt(count));
}

export function pickActions(sentences: Sentence[], seed: string): HealthCard | null {
  const chosen: Partial<Record<Audience, [string, string]>> = {};
  for (const audience of AUDIENCES) {
    const pool = sentences
      .filter((s) => eligible(s) && s.audience === audience)
      .sort((a, b) => compareStrings(String(a.id ?? ""), String(b.id ?? "")) || compareStrings(String(a.text), String(b.text)));
    if (pool.length === 0) return null;
    const pick = pool[pickIndex(seed, audience, pool.length)];
    chosen[audience] = [String(pick.text).trim(), String(pick.source).trim()];
  }
  return {
    person: chosen.person![0],
    pet: chosen.pet![0],
    city: chosen.city![0],
    sources: [chosen.person![1], chosen.pet![1], chosen.city![1]],
  };
}
