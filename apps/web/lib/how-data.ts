// Build time only, like lib/verify-data.ts: /how-we-know reads its numbers from results/ when the
// static page is built, so the page shows exactly what is committed and nobody types a number by
// hand (hard rule 12). Imported by app/how-we-know/page.tsx, a server component; nothing here
// reaches the browser but the numbers, as text.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { howNumbers } from "./how-numbers.mjs";

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
