// The three budgets from docs/updates/UPDATE_06.md section 5, measured on a throttled 4G profile:
// the landing page's largest paint under 2.5s, layout shift under 0.05, landing JavaScript under
// 90 KB compressed. Needs the production server on 3100. Prints the numbers and fails if one is over.
import { chromium } from "@playwright/test";

const base = process.env.BUDGET_URL || "http://127.0.0.1:3100";
// Lighthouse's mobile profile: 1.6 Mbit/s down, 750 kbit/s up, 150 ms round trip, 4x slower CPU.
const NET = { offline: false, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8, latency: 150 };
const LIMITS = { lcp: 2500, cls: 0.05, js: 90 * 1024 };

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

const got = await page.evaluate(() => {
  const w = window;
  const js = performance
    .getEntriesByType("resource")
    .filter((r) => r.initiatorType === "script" || r.name.endsWith(".js"))
    .reduce((n, r) => n + (r.encodedBodySize || r.transferSize || 0), 0);
  return { lcp: w.__lcp, cls: w.__cls, js };
});
await browser.close();

const rows = [
  ["largest contentful paint", `${Math.round(got.lcp)} ms`, `under ${LIMITS.lcp} ms`, got.lcp <= LIMITS.lcp],
  ["cumulative layout shift", got.cls.toFixed(4), `under ${LIMITS.cls}`, got.cls <= LIMITS.cls],
  ["landing javascript", `${(got.js / 1024).toFixed(1)} KB`, `under ${(LIMITS.js / 1024).toFixed(0)} KB`, got.js <= LIMITS.js],
];
for (const [name, value, limit, ok] of rows) console.log(`budget: ${ok ? "PASS" : "OVER"} ${name} ${value} (${limit}, throttled 4G, 4x CPU)`);
process.exit(rows.every((r) => r[3]) ? 0 : 1);
