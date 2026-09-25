// Build time only, like lib/verify-data.ts: /how-we-know reads its numbers from results/, and the
// footage example from examples/footage-flag/, when the static page is built, so the page shows
// exactly what is committed and nobody types a number by hand (hard rule 12). Imported by
// app/how-we-know/page.tsx, a server component; nothing here reaches the browser but the text.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { footageCases } from "./footage-example.mjs";
import { howNumbers, keptSplit } from "./how-numbers.mjs";

// next build and next dev run in apps/web, so the repository root is two folders up.
const REPO = join(process.cwd(), "..", "..");

/** The files the page reads, as the page names them. */
export const PASS_FILE = "results/model_pass_table.json";
export const GATE_FILES = ["results/footage_latest.json", "results/footage_pool.json"] as const;

function readResult(path: string): unknown {
  const full = join(REPO, path);
  return existsSync(full) ? JSON.parse(readFileSync(full, "utf8")) : null;
}

export function howWeKnowNumbers(featureOrder: string[]) {
  return howNumbers(readResult(PASS_FILE), readResult(GATE_FILES[0]), readResult(GATE_FILES[1]), featureOrder);
}

/** Where the split of the kept flags comes from (CRITIC_09 J03). */
export const MODEL_CARD_FILE = "results/model_card.json";

/**
 * How the gate's kept flags split: on a dug-out channel, and the kept model's answers on the frame
 * shown below, with that model and its runs named (CRITIC_11 V02).
 */
export function howKeptSplit(
  gate: { kept: number } | null,
  shownCase: { feature: string; model: string; own: string[] } | null | undefined,
) {
  return keptSplit(readResult(MODEL_CARD_FILE), gate, shownCase);
}

/** The footage example, written by evals/footage_example.py (CRITIC_03 D04). */
export const EXAMPLE_FILE = "examples/footage-flag/example.json";

/**
 * The example's kept and dropped cases, with the run file it names read too, so the page shows
 * the cases only while that run says it is real. The run must be a file in results/.
 */
export function footageExample() {
  const example = readResult(EXAMPLE_FILE) as { run?: { results?: unknown } } | null;
  const runPath = example?.run?.results;
  const inResults = typeof runPath === "string" && /^results\/[\w.-]+\.json$/.test(runPath);
  return footageCases(example, inResults ? readResult(runPath) : null);
}
