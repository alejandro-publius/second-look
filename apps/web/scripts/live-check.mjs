// Drives the deployed site on a phone viewport against the real API, and measures the first
// paint on a throttled 4G profile. Sessions are marked is_test by the x-qa-key header, so a
// live check never lands in the study data. Update 09 section 2, P1.
//
// The Worker marks a session as a test only when the key matches its secret, and says nothing
// when it does not. On 2026-09-22 a stale key in /tmp/qa_key.txt let a check sitting land as a
// real one. So the key now has to be passed on purpose, and the public counts are read before
// and after: if a non-test session appeared, the run fails and prints the repair.
import { chromium } from "@playwright/test";

const site = process.env.SITE_URL;
const api = (process.env.API_URL ?? "https://second-look-api.thealexschroeder.workers.dev").replace(/\/$/, "");
const qaKey = process.env.QA_KEY;
if (!site) throw new Error("set SITE_URL");
if (!qaKey) throw new Error("set QA_KEY to the Worker's QA_KEY secret; without it the sitting would be stored as real");

async function realSessions() {
  const r = await fetch(`${api}/api/test/counts`);
  const c = await r.json();
  return Object.values(c.by_arm).reduce((n, a) => n + a.randomized, 0);
}
const before = await realSessions();

const browser = await chromium.launch();

// 1. Cold first paint, throttled 4G with a 4x slower CPU, on a fresh profile with no cache.
{
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.emulateNetworkConditions", { offline: false, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8, latency: 150 });
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  await page.addInitScript(() => {
    window.__lcp = 0;
    new PerformanceObserver((l) => {
      for (const e of l.getEntries()) window.__lcp = Math.max(window.__lcp, e.startTime);
    }).observe({ type: "largest-contentful-paint", buffered: true });
  });
  const started = Date.now();
  await page.goto(`${site}/`, { waitUntil: "load" });
  const loaded = Date.now() - started;
  await page.evaluate(() => new Promise((r) => setTimeout(r, 1200)));
  const lcp = await page.evaluate(() => window.__lcp);
  console.log(`live: first screen, throttled 4G and 4x CPU: load ${loaded} ms, largest paint ${Math.round(lcp)} ms`);
  await context.close();
}

// 2. A whole sitting against the real API, on a phone, marked as a test session.
{
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
    serviceWorkers: "block",
    extraHTTPHeaders: { "x-qa-key": qaKey },
  });
  const page = await context.newPage();
  const sent = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/test/")) sent.push(new URL(r.url()).pathname);
  });
  await page.goto(`${site}/t`);
  await page.getByLabel("I understand and agree to take part.").check();
  await page.getByLabel("I am 18 or older.").check();
  await page.getByRole("button", { name: "I agree, start" }).click();
  await page.getByRole("button", { name: "This creek, on the left" }).click();

  // Wait for whichever screen the server gave us rather than guessing, or a slow arm assignment
  // reads as the untrained arm and the walk falls over.
  await Promise.race([
    page.getByText("Photo 1 of 16").waitFor({ timeout: 30_000 }),
    page.getByRole("button", { name: "Next photo", exact: true }).waitFor({ timeout: 30_000 }),
  ]);
  const lessonFirst = !(await page.getByText("Photo 1 of 16").isVisible());
  if (lessonFirst) {
    for (let f = 0; f < 4; f++) {
      await page.getByRole("button", { name: "Next photo", exact: true }).click();
      await page.getByRole("button", { name: "Next photo", exact: true }).click();
      await page.getByRole("button", { name: "Yes", exact: true }).click();
      await page.getByRole("button", { name: f === 3 ? "Finish" : "Next photo", exact: true }).click();
    }
  }
  for (let i = 1; i <= 16; i++) {
    await page.getByText(`Photo ${i} of 16`).waitFor();
    await page.getByRole("button", { name: "Yes", exact: true }).click();
    await page.locator("[data-confirm]").click();
  }
  await page.getByRole("heading", { name: "Almost done" }).waitFor();
  await page.getByRole("button", { name: "See my score" }).click();
  await page.getByRole("heading", { name: "Your score" }).waitFor();
  const score = await page.locator(".gauge-count").first().innerText();
  console.log(`live: a whole sitting on a phone, arm ${lessonFirst ? "trained" : "untrained"}, score line "${score.trim()}"`);
  console.log(`live: api calls ${[...new Set(sent)].join(", ")}, responses sent ${sent.filter((p) => p === "/api/test/response").length}`);
  await context.close();
}

await browser.close();

const after = await realSessions();
if (after !== before) {
  console.error(`live: FAILED. Non-test sessions went from ${before} to ${after}, so QA_KEY did not match the Worker's secret and this sitting was stored as real.`);
  console.error("live: repair with: cd worker && npx wrangler d1 execute second-look --remote --command \"UPDATE session SET is_test = 1 WHERE is_test = 0 AND started_at >= '<start of this run, UTC>'\"");
  process.exit(1);
}
console.log(`live: non-test sessions unchanged at ${after}, so the sitting was stored as a test`);
