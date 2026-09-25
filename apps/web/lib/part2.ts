/**
 * The open second look (UPDATE_31). A reload asks the server where it was, so only the ids live
 * here, the same way lib/session.ts keeps part 1's open sitting.
 */
const OPEN_PART2_KEY = "sl_open_part2";

export interface OpenPart2 {
  part2_id: string;
  session_id: string;
}

export function setOpenPart2(open: OpenPart2): void {
  try {
    localStorage.setItem(OPEN_PART2_KEY, JSON.stringify(open));
  } catch {
    // storage blocked: a reload starts from the offer again, and the server returns the same one
  }
}

export function getOpenPart2(): OpenPart2 | null {
  try {
    const raw = localStorage.getItem(OPEN_PART2_KEY);
    if (!raw) return null;
    const v = JSON.parse(raw) as OpenPart2;
    return v && typeof v.part2_id === "string" && typeof v.session_id === "string" ? v : null;
  } catch {
    return null;
  }
}
