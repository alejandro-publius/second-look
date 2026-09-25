// After the build: adds to precache.json every /_next/static file the precached pages load, so the
// service worker's install caches the JavaScript, the CSS and the fonts with the pages. Without
// them a page came back from the cache offline as bare HTML, and the creek check's Start button
// did nothing until a second visit online (CRITIC_11 W01).
//
// build-content.mjs writes the pages and photos before the build, when the file names of the
// build are not known yet. This runs after it and lists exactly what the build wrote: the files
// each precached page's HTML names, the fonts its CSS names, and the chunks a listed script names.
// A named file that the build did not write fails the build.
//
//   node scripts/precache-static.mjs            after next build: reads .next, writes public/precache.json
//   node scripts/precache-static.mjs --export   after the static export: reads out/, writes out/precache.json
import { existsSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(here, "..");
const isExport = process.argv.includes("--export");

// Where this build keeps each page's HTML and the files served under /_next/static/.
const htmlRoot = isExport ? join(webRoot, "out") : join(webRoot, ".next", "server", "app");
const staticRoot = isExport ? join(webRoot, "out", "_next", "static") : join(webRoot, ".next", "static");
const listPath = isExport ? join(webRoot, "out", "precache.json") : join(webRoot, "public", "precache.json");

function fail(msg) {
  console.error(`precache-static: ${msg}`);
  process.exit(1);
}

/** The HTML file of a precached page, or null for a route that is not a page (the manifest). */
function htmlFile(page) {
  const last = page.split("/").pop();
  if (last.includes(".")) return null;
  return join(htmlRoot, page === "/" ? "index.html" : `${page.slice(1)}.html`);
}

/** The file on disk behind a /_next/static/ address. */
function fileOf(url) {
  return join(staticRoot, url.slice("/_next/static/".length).split(/[?#]/)[0]);
}

// Addresses as HTML writes them, in attributes and in the escaped flight data (\"/_next/...\").
const HTML_REF = /\/_next\/static\/[^"'\s)\\<>]+/g;
// Chunks and media a script loads by itself, named relative to /_next/.
const JS_REF = /(?:\/_next\/)?static\/(?:chunks|media)\/[\w.~-]+/g;
const CSS_URL = /url\(\s*(["']?)([^"')]+)\1\s*\)/g;

function refsIn(url) {
  const text = readFileSync(fileOf(url), "utf8");
  if (url.endsWith(".css")) {
    return [...text.matchAll(CSS_URL)]
      .map((m) => m[2])
      .filter((u) => !u.startsWith("data:") && !u.startsWith("#"))
      .map((u) => new URL(u, `http://x${url}`).pathname)
      .filter((u) => u.startsWith("/_next/static/"));
  }
  if (url.endsWith(".js")) return [...text.matchAll(JS_REF)].map((m) => (m[0].startsWith("/") ? m[0] : `/_next/${m[0]}`));
  return [];
}

function main() {
  if (!existsSync(listPath)) fail(`${listPath} is missing; build-content.mjs writes it before the build`);
  if (!existsSync(staticRoot)) fail(`${staticRoot} is missing; run this after the build`);
  const list = JSON.parse(readFileSync(listPath, "utf8"));
  const pages = list.pages ?? [];

  const found = new Set();
  for (const page of pages) {
    const file = htmlFile(page);
    if (!file) continue;
    if (!existsSync(file)) fail(`no HTML for the precached page ${page} at ${file}`);
    for (const m of readFileSync(file, "utf8").matchAll(HTML_REF)) found.add(m[0]);
  }
  // A stylesheet names its fonts, and a script may name the chunks it loads later.
  const queue = [...found];
  while (queue.length) {
    const url = queue.pop();
    if (!existsSync(fileOf(url))) fail(`${url} is named by a precached page but the build has no such file`);
    for (const ref of refsIn(url)) {
      if (!found.has(ref)) {
        found.add(ref);
        queue.push(ref);
      }
    }
  }

  const files = [...found].sort();
  const bytes = files.reduce((sum, url) => sum + statSync(fileOf(url)).size, 0);
  writeFileSync(listPath, JSON.stringify({ ...list, static: files }, null, 2) + "\n");
  const kinds = ["js", "css", "woff2"].map((ext) => `${files.filter((f) => f.split("?")[0].endsWith(`.${ext}`)).length} ${ext}`).join(", ");
  console.log(`precache-static: ${files.length} files under /_next/static (${kinds}), ${bytes} bytes, for ${pages.length} precached pages`);
}

main();
