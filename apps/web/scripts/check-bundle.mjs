// The answer key never ships to a browser. After a build, every file the site serves is read, and
// the build fails if one carries a gold label. On 2026-09-23 the video walks imported the Worker's
// full content file into the page code, and all 16 gold answers shipped in three chunks.
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const web = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const roots = [join(web, ".next", "static"), join(web, "out")].filter((p) => existsSync(p));
const PATTERNS = [/"gold"\s*:/, /gold_label/];
const bad = [];
let scanned = 0;

function walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walk(path);
    else if (/\.(js|json|html|txt|css)$/.test(name)) {
      scanned += 1;
      // A lesson's practice photo carries its answer on purpose: the lesson shows it right after
      // the tap, and it is never a test item. build-content.mjs makes the same exception.
      const text = readFileSync(path, "utf8").replace(/"practice":\{[^}]*\}/g, "");
      if (PATTERNS.some((p) => p.test(text))) bad.push(path.slice(web.length + 1));
    }
  }
}
for (const root of roots) walk(root);
if (roots.length === 0) {
  console.log("check-bundle: no build output to scan; run the build first");
  process.exit(1);
}
if (bad.length) {
  console.log(`check-bundle: the gold key is in ${bad.length} shipped file(s):\n  ${bad.join("\n  ")}`);
  process.exit(1);
}
console.log(`check-bundle: ${scanned} shipped files scanned, no gold key in any`);
