// The landing budgets from docs/internal/updates/UPDATE_06.md section 5, as Update 07 section 1 moved them.
// Measured on a throttled 4G profile with a 4x slower CPU:
//   largest paint under 2.5s, layout shift under 0.05,
//   and no more than 25 KB compressed of OUR code on the landing route.
// The last one is measured as the landing route's JavaScript minus a near static page on the same
// app, so the App Router's own baseline is not counted against us. The 90 KB total was dropped
// because the framework floor alone is above it and we are not rebuilding the front door.
// Needs the production server on 3100. Prints the numbers and fails if one is over.
import { chromium } from "@playwright/test";

const base = process.env.BUDGET_URL || "http://127.0.0.1:3100";
// Lighthouse's mobile profile: 1.6 Mbit/s down, 750 kbit/s up, 150 ms round trip, 4x slower CPU.
const NET = { offline: false, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8, latency: 150 };
// ours: chunks the landing loads that the framework baseline page does not.
// baseline: the framework's own floor. It has a ceiling too, because a client import can land in
// a shared chunk that every page loads, which would otherwise hide inside the baseline.
const LIMITS = { lcp: 2500, cls: 0.05, ours: 25 * 1024, baseline: 140 * 1024 };
// Next's own not found page. It carries the framework and none of our code.
const BASELINE_PATH = "/_not-found";

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, serviceWorkers: "block" });
const page = await context.newPage();
const cdp = await context.newCDPSession(page);
await cdp.send("Network.enable");
await cdp.send("Network.emulateNetworkConditions", NET);
await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });

await page.addInitScript(() => {
  const w = window;
  w.__lcp = 0;
  w.__cls = 0;
  new PerformanceObserver((list) => {
    for (const e of list.getEntries()) w.__lcp = Math.max(w.__lcp, e.startTime);
  }).observe({ type: "largest-contentful-paint", buffered: true });
  new PerformanceObserver((list) => {
    for (const e of list.getEntries()) if (!e.hadRecentInput) w.__cls += e.value;
  }).observe({ type: "layout-shift", buffered: true });
});

await page.goto(`${base}/`, { waitUntil: "load" });
await page.waitForLoadState("networkidle");
await page.evaluate(() => new Promise((r) => setTimeout(r, 1500)));

const CHUNKS = `() => performance.getEntriesByType("resource")
  .filter((r) => r.name.endsWith(".js"))
  .map((r) => [r.name.split("/").pop(), r.encodedBodySize || r.transferSize || 0])`;

const got = await page.evaluate((src) => {
  const w = window;
  return { lcp: w.__lcp, cls: w.__cls };
}, CHUNKS);

// Sizes are measured without throttling. A throttled page may still be fetching when we look,
// which would quietly undercount and turn this gate into one that cannot fail.
const sizing = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, serviceWorkers: "block" });
// Read at the load event, not at network idle. After load the router prefetches the routes the
// page links to, and whether those land in time swings the number by tens of kilobytes on
// identical code. What we want is the bundle this route needs to run.
async function chunksOf(path) {
  const p = await sizing.newPage();
  await p.goto(`${base}${path}`, { waitUntil: "load" });
  const rows = await p.evaluate((src) => new Function("return " + src)()(), CHUNKS);
  await p.close();
  return rows;
}
const landingChunks = await chunksOf("/");
const baseChunks = await chunksOf(BASELINE_PATH);
await browser.close();

const baseNames = new Set(baseChunks.map(([name]) => name));
const baseline = baseChunks.reduce((n, [, size]) => n + size, 0);
// Our code is what the landing loads on top of that floor, chunk by chunk.
const ours = landingChunks.filter(([name]) => !baseNames.has(name)).reduce((n, [, size]) => n + size, 0);
const landingTotal = landingChunks.reduce((n, [, size]) => n + size, 0);

const rows = [
  ["largest contentful paint", `${Math.round(got.lcp)} ms`, `under ${LIMITS.lcp} ms`, got.lcp <= LIMITS.lcp],
  ["cumulative layout shift", got.cls.toFixed(4), `under ${LIMITS.cls}`, got.cls <= LIMITS.cls],
  ["our javascript on the landing route", `${(ours / 1024).toFixed(1)} KB`, `under ${(LIMITS.ours / 1024).toFixed(0)} KB`, ours <= LIMITS.ours],
  ["framework baseline", `${(baseline / 1024).toFixed(1)} KB`, `under ${(LIMITS.baseline / 1024).toFixed(0)} KB`, baseline <= LIMITS.baseline],
];
console.log(`budget: note landing total ${(landingTotal / 1024).toFixed(1)} KB, baseline measured at ${BASELINE_PATH}`);
for (const [name, value, limit, ok] of rows) console.log(`budget: ${ok ? "PASS" : "OVER"} ${name} ${value} (${limit}, throttled 4G, 4x CPU)`);
process.exit(rows.every((r) => r[3]) ? 0 : 1);
