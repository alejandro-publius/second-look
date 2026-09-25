// Port of core/assist.py: when part 2's question appears, and what is stored. Pure. Proved equal
// to the Python by worker/golden/assist.json (worker/test/golden.test.ts). The flag is not a
// parameter of settle, so a flag can make the question appear and nothing else.

export const ANSWERS = ["yes", "no", "cant_tell"];
export const SIDES = ["present", "absent"];
export const QUESTION = "The checker noticed something here. Look again?";
export const ALLOCATOR_TO_PART2: Record<string, string> = { untrained: "unassisted", trained: "assisted" };

export class AssistError extends Error {}

export const sideAnswer = (side: string) => (side === "present" ? "yes" : "no");

const isMapping = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);

export function flagSide(flags: unknown, itemId: unknown): string | null {
  if (!isMapping(flags) || typeof itemId !== "string") return null;
  const items = flags.items;
  if (!Array.isArray(items)) return null;
  for (const entry of items) {
    if (!isMapping(entry) || entry.item_id !== itemId) continue;
    const flag = entry.flag;
    if (isMapping(flag) && typeof flag.points_to === "string" && SIDES.includes(flag.points_to)) return flag.points_to;
    return null;
  }
  return null;
}

export function questionNeeded(arm: unknown, side: unknown, first: unknown): boolean {
  if (arm !== "assisted" || typeof side !== "string" || !SIDES.includes(side)) return false;
  if (typeof first !== "string" || !ANSWERS.includes(first)) return false;
  return first !== sideAnswer(side);
}

export interface Settled {
  first_answer: string;
  final_answer: string;
  question_shown: boolean;
  choice: string;
}

const blank = (v: unknown) => v === null || v === undefined || v === "";

export function settle(first: unknown, asked: boolean, choice: unknown = null, changedTo: unknown = null): Settled {
  if (typeof first !== "string" || !ANSWERS.includes(first)) throw new AssistError("We do not know that answer.");
  if (!asked) {
    if (!blank(choice) || !blank(changedTo)) throw new AssistError("No question was asked for this photo, so there is nothing to choose.");
    return { first_answer: first, final_answer: first, question_shown: false, choice: "" };
  }
  if (choice === "keep") {
    if (!blank(changedTo) && changedTo !== first) throw new AssistError("Keep keeps the first answer.");
    return { first_answer: first, final_answer: first, question_shown: true, choice: "keep" };
  }
  if (choice === "change") {
    if (typeof changedTo !== "string" || !ANSWERS.includes(changedTo)) throw new AssistError("We do not know that answer.");
    return { first_answer: first, final_answer: changedTo, question_shown: true, choice: "change" };
  }
  throw new AssistError("Choose Keep or Change.");
}
