// Drives the deployed site on a phone viewport against the real API, and measures the first
// paint on a throttled 4G profile. Sessions are marked is_test by the x-qa-key header, so a
// live check never lands in the study data. Update 09 section 2, P1.
import { readFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const site = process.env.SITE_URL;
const qaKey = process.env.QA_KEY ?? readFileSync("/tmp/qa_key.txt", "utf8").trim();
if (!site) throw new Error("set SITE_URL");

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
