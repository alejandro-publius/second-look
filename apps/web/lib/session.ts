// Browser-side helpers for the study session: the hashed random token, the device class, the
// coarse source label from ?src=, and the contributor token after "keep my score".
import type { UaClass } from "./api";

const TOKEN_KEY = "sl_client_token";
const SRC_KEY = "sl_src";
const CONTRIB_KEY = "sl_contributor_token";
const SPOTS_KEY = "sl_saved_spots";
const GUESS_KEY = "sl_landing_guess";
const OPEN_KEY = "sl_open_session";

export const SOURCE_LABELS = ["poster", "chat", "friends", "creek_group", "other"] as const;

function randomHex(bytes: number): string {
  const arr = new Uint8Array(bytes);
  crypto.getRandomValues(arr);
  return Array.from(arr, (b) => b.toString(16).padStart(2, "0")).join("");
}

export async function sha256Hex(text: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** A random token lives in localStorage; only its hash ever leaves the phone. */
export async function clientTokenHash(): Promise<string> {
  let token: string | null = null;
  try {
    token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      token = randomHex(32);
      localStorage.setItem(TOKEN_KEY, token);
    }
  } catch {
    token = randomHex(32);
  }
  return sha256Hex(token);
}

export function uaClass(): UaClass {
  if (typeof window === "undefined") return "desktop";
  const coarse = window.matchMedia?.("(pointer: coarse)").matches ?? false;
  const w = Math.min(window.innerWidth, window.innerHeight);
  if (coarse && window.innerWidth < 768) return "phone";
  if (coarse || w < 900 && /iPad|Tablet|Android(?!.*Mobile)/i.test(navigator.userAgent)) return "tablet";
  return "desktop";
}

/** Reads ?src= from a URL and keeps the coarse label for the session. Unknown values become "other". */
export function captureSource(search: string): void {
  const raw = new URLSearchParams(search).get("src");
  if (!raw) return;
  const label = (SOURCE_LABELS as readonly string[]).includes(raw) ? raw : "other";
  try {
    sessionStorage.setItem(SRC_KEY, label);
  } catch {
    // storage blocked: the session will say "other"
  }
}

export function sourceLabel(): string {
  try {
    return sessionStorage.getItem(SRC_KEY) ?? "other";
  } catch {
    return "other";
  }
}

export function buildHash(): string {
  return process.env.NEXT_PUBLIC_BUILD_HASH || "dev";
}

export function siteUrl(): string {
  return (process.env.NEXT_PUBLIC_SITE_URL || "https://second-look.example").replace(/\/$/, "");
}

export function getContributorToken(): string | null {
  try {
    return localStorage.getItem(CONTRIB_KEY);
  } catch {
    return null;
  }
}

export function setContributorToken(token: string): void {
  try {
    localStorage.setItem(CONTRIB_KEY, token);
  } catch {
    // nothing to do; the person saw it once
  }
}

export function clearContributorToken(): void {
  try {
    localStorage.removeItem(CONTRIB_KEY);
  } catch {
    // ignore
  }
}

export interface SavedSpot {
  spot_id: string;
  name: string;
}

export function savedSpots(): SavedSpot[] {
  try {
    const raw = localStorage.getItem(SPOTS_KEY);
    const list = raw ? (JSON.parse(raw) as SavedSpot[]) : [];
    return Array.isArray(list) ? list.filter((s) => s && typeof s.spot_id === "string") : [];
  } catch {
    return [];
  }
}

export function rememberSpot(spot: SavedSpot): void {
  try {
    const list = savedSpots().filter((s) => s.spot_id !== spot.spot_id);
    list.unshift(spot);
    localStorage.setItem(SPOTS_KEY, JSON.stringify(list.slice(0, 20)));
  } catch {
    // ignore
  }
}

/** Fisher-Yates with a seeded generator so the demo script is the same every time. */
export function shuffle<T>(items: T[], seed?: string): T[] {
  const out = items.slice();
  let rand: () => number;
  if (seed === undefined) {
    rand = () => {
      const a = new Uint32Array(1);
      crypto.getRandomValues(a);
      return a[0] / 2 ** 32;
    };
  } else {
    let h = 1779033703 ^ seed.length;
    for (let i = 0; i < seed.length; i++) {
      h = Math.imul(h ^ seed.charCodeAt(i), 3432918353);
      h = (h << 13) | (h >>> 19);
    }
    let state = h >>> 0;
    rand = () => {
      state = (state + 0x6d2b79f5) >>> 0;
      let z = state;
      z = Math.imul(z ^ (z >>> 15), z | 1);
      z ^= z + Math.imul(z ^ (z >>> 7), z | 61);
      return ((z ^ (z >>> 14)) >>> 0) / 2 ** 32;
    };
  }
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

/**
 * The landing page question. The choice is kept in this browser only; TestFlow sends it as the
 * warm-up answer after the person has consented, never before. docs/analysis_plan.md says so too.
 */
export function setLandingGuess(warmupId: string): void {
  try {
    sessionStorage.setItem(GUESS_KEY, warmupId);
  } catch {
    // storage blocked: the person answers the warm-up screen instead
  }
}

export function takeLandingGuess(): string | null {
  try {
    const v = sessionStorage.getItem(GUESS_KEY);
    if (v) sessionStorage.removeItem(GUESS_KEY);
    return v;
  } catch {
    return null;
  }
}

/**
 * The open sitting. A reload asks the server where it was, so only the id and the lesson card
 * live here. Cleared when the person finishes, so the end screen is not shown forever.
 */
export interface OpenSession {
  session_id: string;
  lesson_index?: number;
}

export function setOpenSession(open: OpenSession): void {
  try {
    localStorage.setItem(OPEN_KEY, JSON.stringify(open));
  } catch {
    // storage blocked: a reload starts again, which is the behaviour we had before
  }
}

export function getOpenSession(): OpenSession | null {
  try {
    const raw = localStorage.getItem(OPEN_KEY);
    if (!raw) return null;
    const v = JSON.parse(raw) as OpenSession;
    return v && typeof v.session_id === "string" ? v : null;
  } catch {
    return null;
  }
}

export function clearOpenSession(): void {
  try {
    localStorage.removeItem(OPEN_KEY);
  } catch {
    // nothing to do
  }
}
