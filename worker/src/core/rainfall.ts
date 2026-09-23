// core/rainfall.py: rainfall for the dry pipe rule, from Open-Meteo, failing closed to unknown.
// Weather data by Open-Meteo.com, CC BY 4.0. The only network call in the ports; the caller
// passes the fetch, so the golden tests and the e2e run pass their own.

export const OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast";
export const SOURCE_OPEN_METEO = "open-meteo";
export const SOURCE_UNKNOWN = "unknown";
const PAST_DAYS = 4;
const FORECAST_DAYS = 1;
export const DEFAULT_DRY_MM = 2.5;
export const DEFAULT_WINDOW_HOURS = 72;
const DRY_HOUR_MAX_MM = 0.1;
const HOURS_PER_DAY = 24;
const HOUR_MS = 3_600_000;

export interface RainStatus {
  status: "dry" | "wet" | "unknown";
  mm_in_window: number | null;
  dry_days: number | null;
  source: string;
}

export const UNKNOWN: RainStatus = { status: "unknown", mm_in_window: null, dry_days: null, source: SOURCE_UNKNOWN };

export function buildUrl(latitude: number, longitude: number): string {
  const query = new URLSearchParams({
    latitude: latitude.toFixed(4),
    longitude: longitude.toFixed(4),
    hourly: "precipitation",
    past_days: String(PAST_DAYS),
    forecast_days: String(FORECAST_DAYS),
    timezone: "UTC",
  });
  return `${OPEN_METEO_URL}?${query.toString()}`;
}

type Hour = [number, number]; // hour end in ms, mm

function hours(payload: unknown): Hour[] {
  if (!payload || typeof payload !== "object") throw new Error("payload is not an object");
  const hourly = (payload as Record<string, unknown>).hourly;
  if (!hourly || typeof hourly !== "object") throw new Error("hourly is not an object");
  const times = (hourly as Record<string, unknown>).time;
  const values = (hourly as Record<string, unknown>).precipitation;
  if (!Array.isArray(times) || !Array.isArray(values) || times.length !== values.length) {
    throw new Error("time and precipitation lists do not line up");
  }
  const out: Hour[] = [];
  for (let i = 0; i < times.length; i++) {
    const text = times[i];
    const value = values[i];
    if (typeof text !== "string") throw new Error("time is not text");
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0) throw new Error("precipitation is not a finite non-negative number");
    const ms = Date.parse(`${text}Z`);
    if (Number.isNaN(ms)) throw new Error(`bad hour ${text}`);
    out.push([ms, value]);
  }
  return out;
}

/** Values for hour buckets ending in (start, end], or null when the span is not covered. */
function window(list: Hour[], start: number, end: number): number[] | null {
  const picked = list.filter(([hourEnd]) => start < hourEnd && hourEnd <= end).map(([, mm]) => mm);
  const needed = Math.trunc((end - start) / HOUR_MS);
  return picked.length < needed ? null : picked;
}

function dryDays(list: Hour[], now: number): number {
  let days = 0;
  for (;;) {
    const end = now - HOURS_PER_DAY * days * HOUR_MS;
    const start = end - HOURS_PER_DAY * HOUR_MS;
    const values = window(list, start, end);
    if (values === null || values.some((mm) => mm > DRY_HOUR_MAX_MM)) return days;
    days += 1;
  }
}

export function statusFromPayload(payload: unknown, nowMs: number, dryMm = DEFAULT_DRY_MM, windowHours = DEFAULT_WINDOW_HOURS): RainStatus {
  const list = hours(payload);
  const values = window(list, nowMs - windowHours * HOUR_MS, nowMs);
  if (values === null) return UNKNOWN;
  const total = Math.round(values.reduce((a, b) => a + b, 0) * 100) / 100;
  return { status: total <= dryMm ? "dry" : "wet", mm_in_window: total, dry_days: dryDays(list, nowMs), source: SOURCE_OPEN_METEO };
}

/** Open-Meteo hourly precipitation for the window. Any failure, of any kind, is unknown. */
export async function dryStatus(
  latitude: number,
  longitude: number,
  nowMs: number,
  fetchJson: (url: string) => Promise<unknown>,
  dryMm = DEFAULT_DRY_MM,
  windowHours = DEFAULT_WINDOW_HOURS,
): Promise<RainStatus> {
  try {
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180 || windowHours <= 0) {
      return UNKNOWN;
    }
    const payload = await fetchJson(buildUrl(latitude, longitude));
    return statusFromPayload(payload, nowMs, dryMm, windowHours);
  } catch {
    return UNKNOWN;
  }
}

/** The default fetch: five seconds, one retry, JSON or throw. */
export async function fetchOpenMeteo(url: string): Promise<unknown> {
  let last: unknown = null;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(5000) });
      if (!response.ok) throw new Error(`open-meteo ${response.status}`);
      return await response.json();
    } catch (err) {
      last = err;
    }
  }
  throw last;
}
