// The landing page's first screen on a throttled phone, from a static build (Update 22 section 1
// answer 2). Serves the build the way Cloudflare Pages does, with the headers of its _headers file
// and gzip for text, but without Early Hints. Then loads / on a phone with the budget.mjs profile,
// a few times at each pixel density, and writes bytes and largest paint to results/.
//
//   node scripts/first-screen.mjs --dir <static build> --label before|after --commit <sha>
//
// Without Early Hints on purpose: Chrome does not throttle what an Early Hint fetches, so a
// throttled run with them hides the photo bytes. Each label is kept, so run it once per build.
//
// First screen bytes are what the page itself and its stylesheet ask for: the HTML, the CSS, the
// font, the scripts in the HTML and the photos. What the page's scripts fetch once they run (the
// router's prefetch of the pages the landing links to, the call that wakes the API) is counted
// apart. It is the same on both builds, but it lands before or after the load event depending on
// how long the photos take, so counting up to the load event would put about 40 KB into one build
// and not the other. Both are read at network idle, once every request has finished.
import { createServer } from "node:http";
import { existsSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";
import { chromium } from "@playwright/test";

const web = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repo = resolve(web, "..", "..");
const RESULT = join(repo, "results", "warmup_photos.json");
const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > 0 ? process.argv[i + 1] : fallback;
};
const dir = resolve(arg("dir", join(web, "out")));
const label = arg("label", "after");
const commit = arg("commit", "");
const tries = Number(arg("tries", 3));
const densities = arg("dpr", "3,2,1").split(",").map(Number);
// Lighthouse's mobile profile, as in budget.mjs and live-check.mjs.
const NET = { offline: false, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8, latency: 150 };
const VIEWPORT = { width: 390, height: 844 };
const CPU_SLOWDOWN = 4;
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "application/javascript", ".css": "text/css", ".json": "application/json", ".txt": "text/plain; charset=utf-8", ".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".avif": "image/avif", ".woff2": "font/woff2", ".svg": "image/svg+xml", ".ico": "image/x-icon", ".webmanifest": "application/manifest+json" };
const TEXT = new Set([".html", ".js", ".css", ".json", ".txt", ".svg", ".webmanifest"]);

if (!existsSync(join(dir, "index.html"))) throw new Error(`no static build in ${dir}: run npm run export`);

// The rules of _headers: a path line, then indented header lines. Exact paths and /* only.
const rules = [];
for (const line of existsSync(join(dir, "_headers")) ? readFileSync(join(dir, "_headers"), "utf8").split("\n") : []) {
  if (!line.trim() || line.startsWith("#")) continue;
  if (!line.startsWith(" ")) rules.push({ path: line.trim(), headers: [] });
  else rules.at(-1)?.headers.push([line.slice(0, line.indexOf(":")).trim(), line.slice(line.indexOf(":") + 1).trim()]);
}

function fileFor(pathname) {
  const clean = normalize(decodeURIComponent(pathname)).replace(/^(\.\.[/\\])+/, "");
  const tries_ = clean.endsWith("/") ? [join(dir, clean, "index.html")] : [join(dir, clean), join(dir, `${clean}.html`), join(dir, clean, "index.html")];
  return tries_.find((p) => existsSync(p) && statSync(p).isFile());
}

const server = createServer((req, res) => {
  const { pathname } = new URL(req.url, "http://x");
  const file = fileFor(pathname);
  if (!file) {
    res.writeHead(404).end();
    return;
  }
  const headers = { "content-type": TYPES[extname(file)] ?? "application/octet-stream", "cache-control": "public, max-age=0, must-revalidate" };
  for (const r of rules) {
    const hit = r.path === pathname || (r.path.endsWith("/*") && pathname.startsWith(r.path.slice(0, -1)));
    if (hit) for (const [k, v] of r.headers) headers[k] = headers[k] ? `${headers[k]}, ${v}` : v;
  }
  let body = readFileSync(file);
  if (TEXT.has(extname(file)) && /gzip/.test(req.headers["accept-encoding"] ?? "")) {
    body = gzipSync(body);
    headers["content-encoding"] = "gzip";
  }
  res.writeHead(200, { ...headers, "content-length": body.length }).end(body);
});
await new Promise((ok) => server.listen(0, "127.0.0.1", ok));
const base = `http://127.0.0.1:${server.address().port}`;

const browser = await chromium.launch();
async function once(dpr) {
  const ctx = await browser.newContext({ viewport: VIEWPORT, deviceScaleFactor: dpr, isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
  await cdp.send("Network.emulateNetworkConditions", NET);
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: CPU_SLOWDOWN });
  const reqs = new Map();
  // byScript: fetched by the page's own scripts once they run, not asked for by the HTML or CSS.
  cdp.on("Network.requestWillBeSent", (e) => reqs.set(e.requestId, { url: e.request.url, bytes: 0, done: false, byScript: e.initiator?.type === "script" }));
  cdp.on("Network.loadingFinished", (e) => {
    if (reqs.has(e.requestId)) Object.assign(reqs.get(e.requestId), { bytes: e.encodedDataLength, done: true });
  });
  await page.addInitScript(() => {
    window.__lcp = { t: 0, what: "" };
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) if (e.startTime >= window.__lcp.t) window.__lcp = { t: e.startTime, what: e.url ? e.url.split("/").pop() : e.element?.tagName.toLowerCase() ?? "" };
    }).observe({ type: "largest-contentful-paint", buffered: true });
  });
  const started = Date.now();
  await page.goto(`${base}/`, { waitUntil: "load" });
  const load_ms = Date.now() - started;
  await page.waitForLoadState("networkidle");
  await page.evaluate(() => new Promise((r) => setTimeout(r, 1500)));
  const lcp = await page.evaluate(() => window.__lcp);
  const shown = await page.$$eval("img.photo", (imgs) => imgs.map((i) => i.currentSrc.split("/").pop()));
  await ctx.close();
  const all = [...reqs.values()];
  // A photo counts wherever its request came from, so a second copy fetched by a script shows up.
  const isPhoto = (r) => new URL(r.url).pathname.startsWith("/photos/");
  const first = all.filter((r) => !r.byScript || isPhoto(r));
  // A request of the first screen that never finished would be counted as 0 bytes. Stop instead.
  const unfinished = first.filter((r) => !r.done).map((r) => new URL(r.url).pathname);
  if (unfinished.length) throw new Error(`first screen requests that never finished: ${unfinished.join(" ")}`);
  const photos = first.filter(isPhoto);
  const sum = (rs) => rs.reduce((n, r) => n + r.bytes, 0);
  return {
    load_ms,
    lcp_ms: Math.round(lcp.t),
    lcp_element: lcp.what,
    first_screen_bytes: sum(first),
    first_screen_requests: first.length,
    photo_bytes: sum(photos),
    later_script_bytes: sum(all.filter((r) => r.byScript && !isPhoto(r))),
    photos_fetched: photos.map((r) => new URL(r.url).pathname.split("/").pop()).sort(),
    photos_shown: shown,
  };
}

const median = (xs) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];
const run = { commit, dpr: {} };
for (const dpr of densities) {
  const got = [];
  for (let i = 0; i < tries; i++) got.push(await once(dpr));
  run.dpr[dpr] = {
    tries: got,
    median_lcp_ms: median(got.map((g) => g.lcp_ms)),
    median_load_ms: median(got.map((g) => g.load_ms)),
    median_first_screen_bytes: median(got.map((g) => g.first_screen_bytes)),
    median_photo_bytes: median(got.map((g) => g.photo_bytes)),
    median_later_script_bytes: median(got.map((g) => g.later_script_bytes)),
  };
  console.log(`first-screen: ${label} at ${dpr}x: largest paint ${run.dpr[dpr].median_lcp_ms} ms, ${run.dpr[dpr].median_first_screen_bytes} bytes, photos ${got[0].photos_fetched.join(" ")}`);
}
const version = browser.version();
await browser.close();
server.close();

// The photo bytes on disk: the two JPEGs and every smaller copy, from the manifests.
const csv = (path) => {
  const [head, ...lines] = readFileSync(path, "utf8").trim().split("\n");
  const cols = head.split(",");
  return lines.map((l) => Object.fromEntries(l.split(",").map((v, i) => [cols[i], v])));
};
const photos = {};
for (const row of csv(join(repo, "photos", "derived", "manifest.csv"))) {
  photos[row.source_id] ??= { jpeg_bytes: statSync(join(repo, "photos", "warmup", `${row.source_id}.jpg`)).size, copies: {} };
  photos[row.source_id].copies[`${row.format}-${row.width}`] = Number(row.bytes);
}

// Each run carries the profile it was measured with, and a run is only written next to runs with
// the same profile and browser, so a before and an after in this file always compare like with like.
const profile = {
  browser: `chromium ${version}`,
  viewport: `${VIEWPORT.width}x${VIEWPORT.height}`,
  densities,
  tries,
  download_bytes_per_s: NET.downloadThroughput,
  upload_bytes_per_s: NET.uploadThroughput,
  latency_ms: NET.latency,
  cpu_slowdown: CPU_SLOWDOWN,
  http_cache: "off",
  service_worker: "blocked",
  early_hints: "none",
};
run.measured_at_utc = new Date().toISOString().replace(/\.\d+Z$/, "Z");
run.profile = profile;
const doc = existsSync(RESULT) ? JSON.parse(readFileSync(RESULT, "utf8")) : { runs: {} };
const others = Object.entries(doc.runs ?? {}).filter(([name, r]) => name !== label && JSON.stringify(r.profile) !== JSON.stringify(profile));
if (others.length) {
  console.log(`first-screen: not written. ${others.map(([name]) => name).join(", ")} ran with another profile or browser; delete ${RESULT.slice(repo.length + 1)} and run every label again`);
  process.exit(1);
}
doc.generated_at_utc = run.measured_at_utc;
doc.script = "apps/web/scripts/first-screen.mjs";
doc.what =
  "The landing page's first screen on a phone, loaded from a static build served with its _headers file and without Early Hints. first_screen_bytes counts what the page's HTML and stylesheet ask for, and every photo, read once all of it has arrived. later_script_bytes is what the page's scripts fetch afterwards: the router's prefetch of linked pages and the call that wakes the API.";
doc.profile = profile;
doc.photos = photos;
doc.runs = { ...doc.runs, [label]: run };
writeFileSync(RESULT, JSON.stringify(doc, null, 2) + "\n");
console.log(`first-screen: wrote ${RESULT.slice(repo.length + 1)} (${label})`);
