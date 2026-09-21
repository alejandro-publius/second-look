// Fails when any file we own contains an em dash or an en dash (hard rule 18).
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(here, "..");
const skip = new Set(["node_modules", ".next", "out", "public", "generated", "screens", "playwright-report", "test-results"]);
const bad = [String.fromCharCode(0x2014), String.fromCharCode(0x2013)];
const hits = [];

function walk(dir) {
  for (const name of readdirSync(dir)) {
    if (skip.has(name)) continue;
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if (/\.(ts|tsx|mjs|js|json|css|md)$/.test(name)) {
      const lines = readFileSync(p, "utf8").split("\n");
      lines.forEach((line, i) => {
        if (bad.some((ch) => line.includes(ch))) hits.push(`${p}:${i + 1}`);
      });
    }
  }
}
walk(webRoot);
if (hits.length) {
  console.log(hits.join("\n"));
  console.log(`dash-check: ${hits.length} hit(s)`);
  process.exit(1);
}
console.log("dash-check: no em or en dashes in apps/web");
