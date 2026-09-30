// Mirrors the instants in core/lock.py. A static export cannot ask the server what time it is,
// so the browser checks. scripts/design-check.mjs fails the build if the two drift apart.
//
// DATA_LOCK_UTC is the first wave's data lock and never moves. The second wave of the study
// (plan v3, UPDATE_33) is the sittings that started at or after WAVE2_OPEN_UTC and before
// SECOND_LOCK_UTC. Judge mode shows the answers to the photos the study uses, so it is shut
// until JUDGE_MODE_OPENS_UTC, which is the second lock.
export const DATA_LOCK_UTC = "2026-09-28T01:00:00Z";
export const DATA_LOCK_LOCAL_LABEL = "Sunday Sep 27, 2026 at 18:00 PDT";
export const WAVE2_OPEN_UTC = "2026-09-30T04:00:00Z";
export const WAVE2_OPEN_LOCAL_LABEL = "Tuesday Sep 29, 2026 at 21:00 PDT";
export const SECOND_LOCK_UTC = "2026-10-03T04:00:00Z";
export const SECOND_LOCK_LOCAL_LABEL = "Friday Oct 2, 2026 at 21:00 PDT";
export const JUDGE_MODE_OPENS_UTC = SECOND_LOCK_UTC;

/** True while judge mode is shut: at any time before the second lock, the days it was open after
 *  the first lock included. */
export function isJudgeModeShut(when: Date = new Date()): boolean {
  return when.getTime() < Date.parse(JUDGE_MODE_OPENS_UTC);
}
