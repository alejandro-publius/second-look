// Mirrors DATA_LOCK_UTC in core/lock.py. A static export cannot ask the server what time it is,
// so the browser checks. scripts/design-check.mjs fails the build if the two drift apart.
export const DATA_LOCK_UTC = "2026-09-28T01:00:00Z";
export const DATA_LOCK_LOCAL_LABEL = "Sunday Sep 27, 2026 at 18:00 PDT";

export function isBeforeLock(when: Date = new Date()): boolean {
  return when.getTime() < Date.parse(DATA_LOCK_UTC);
}
