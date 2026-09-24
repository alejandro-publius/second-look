// UPDATE_27, a dated item in docs/internal/DONE.md: does /demo on the live site open on Sep 28?
//
// Judge mode is shut until the data lock and the page decides by the browser's own clock, so
// this loads the live page in Chromium and reads its first heading. Every request that is not
// GET, HEAD or OPTIONS is aborted before it leaves the browser, so this can never write to
// production or start a study session. Exit 0 when the page shows judge mode open, 1 when it
// shows it shut or anything else.
//
//   node scripts/demo-open-check.mjs
//   DEMO_URL=http://localhost:3100/demo node scripts/demo-open-check.mjs
//   node scripts/demo-open-check.mjs --clock 2026-09-29T00:00:00Z   pretend it is that time,
//     to test this script before the date; make done-check never passes it.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const here = dirname(fileURLToPath(import.meta.url));
const words = JSON.parse(readFileSync(join(here, "..", "..", "..", "content", "locales", "en.json"), "utf8"));
const OPEN = words["demo.title"];
const SHUT = words["demo.shut_title"];
const url = process.env.DEMO_URL ?? "https://second-look-79t.pages.dev/demo";
const at = process.argv.indexOf("--clock");
const clock = at > 0 ? process.argv[at + 1] : null;

const browser = await chromium.launch();
const blocked = [];
let heading = "";
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.route("**/*", (route) => {
    const method = route.request().method();
    if (["GET", "HEAD", "OPTIONS"].includes(method)) return route.continue();
    blocked.push(`${method} ${route.request().url()}`);
    return route.abort();
  });
  if (clock) await page.clock.install({ time: new Date(clock) });
  const response = await page.goto(url, { waitUntil: "networkidle", timeout: 45000 });
  if (!response || response.status() !== 200) {
    console.log(`demo-open-check: ${url} answered ${response ? response.status() : "nothing"}`);
    process.exitCode = 1;
  } else {
    await page.waitForFunction(() => document.querySelector("h1")?.textContent?.trim(), null, { timeout: 15000 });
    heading = (await page.locator("h1").first().textContent())?.trim() ?? "";
  }
} finally {
  await browser.close();
}
if (blocked.length) console.log(`demo-open-check: aborted before sending: ${blocked.join(", ")}`);
if (heading === OPEN) {
  console.log(`demo-open-check: ${url} shows "${heading}", judge mode is open`);
} else if (!process.exitCode) {
  const why = heading === SHUT ? "judge mode is still shut" : "not the judge mode page";
  console.log(`demo-open-check: ${url} shows "${heading}", ${why}`);
  process.exitCode = 1;
}
