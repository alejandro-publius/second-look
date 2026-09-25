// Runs Lighthouse against the landing page with budget.json when the lighthouse CLI is installed.
// Otherwise prints how to install it and exits 0, so CI without Chrome is not blocked.
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { WEB_ORIGIN } from "./web-port.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(here, "..");
const url = process.env.LIGHTHOUSE_URL || `${WEB_ORIGIN}/`;

const which = spawnSync(process.platform === "win32" ? "where" : "which", ["lighthouse"], { encoding: "utf8" });
if (which.status !== 0) {
  console.log("lighthouse: the CLI is not installed.");
  console.log("  Install it with: npm install -g lighthouse");
  console.log(`  Then start the app (npm run build && npm run start) and run: npm run lighthouse`);
  console.log(`  It audits ${url} against ${join(webRoot, "budget.json")} and writes out/lighthouse.html`);
  process.exit(0);
}

mkdirSync(join(webRoot, "out"), { recursive: true });
if (!existsSync(join(webRoot, "budget.json"))) {
  console.error("lighthouse: budget.json missing");
  process.exit(1);
}
const args = [
  url,
  "--budget-path",
  join(webRoot, "budget.json"),
  "--only-categories=performance,accessibility,best-practices",
  "--form-factor=mobile",
  "--chrome-flags=--headless=new",
  "--output=html",
  "--output=json",
  "--output-path",
  join(webRoot, "out", "lighthouse"),
  "--quiet",
];
const run = spawnSync("lighthouse", args, { stdio: "inherit" });
process.exit(run.status ?? 1);
