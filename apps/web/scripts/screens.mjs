// Walks every screen on a phone viewport against the fake API and writes screenshots to screens/.
// Needs the production server on port 3100, or WEB_PORT (npm run build && npm run start). Playwright only.
import { mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, devices } from "@playwright/test";
import { mockApi } from "../tests/mock-api.mjs";
import { WEB_ORIGIN } from "./web-port.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "..", "screens");
mkdirSync(out, { recursive: true });
const base = process.env.SCREENS_URL || WEB_ORIGIN;

const browser = await chromium.launch();
const context = await browser.newContext({ ...devices["iPhone 13"], serviceWorkers: "block" });
const page = await context.newPage();
let n = 0;
async function shot(name) {
  n += 1;
  const path = join(out, `${String(n).padStart(2, "0")}-${name}.png`);
  await page.waitForFunction(() => Array.from(document.images).every((i) => i.complete)).catch(() => undefined);
  await page.screenshot({ path, fullPage: true });
  console.log(`screens: ${path}`);
}
const click = (name, exact = true) => page.getByRole("button", { name, exact }).click();

await mockApi(page, { lessonFirst: true });
await page.goto(`${base}/?src=poster`);
await shot("landing");
await page.goto(`${base}/t`);
await shot("consent");
await page.getByLabel("I understand and agree to take part.").check();
await page.getByLabel("I am 18 or older.").check();
await click("I agree, start");
await shot("warmup");
await click("This creek, on the left");
await page.locator(".gauge-count").first().waitFor();
await shot("lesson-rule");
await click("Next photo");
await shot("lesson-pair2");
await click("Next photo");
await shot("lesson-practice");
await click("Yes");
await shot("lesson-practice-feedback");
await click("Next photo");
for (let f = 1; f < 4; f++) {
  await click("Next photo");
  await click("Next photo");
  await click("Yes");
  await click(f === 3 ? "Finish" : "Next photo");
}
await page.getByText("Photo 1 of 16").waitFor();
await shot("test-item");
await page.locator(".glossary-btn").first().click();
await shot("test-item-glossary");
// Select then Next on every item (Update 07 section 1.3).
for (let i = 0; i < 16; i++) {
  await click(i % 2 ? "No" : "Yes");
  await page.locator("[data-confirm]").click();
}
await page.getByRole("heading", { name: "Almost done" }).waitFor();
await shot("before-score");
await page.getByLabel(/Keep my score/).check();
await click("See my score");
await page.getByRole("heading", { name: "Your score" }).waitFor();
await shot("score");

await page.goto(`${base}/demo?script=1`);
await shot("demo-intro");
await click("Start");
await click("Yes");
await page.getByRole("status").waitFor();
await shot("demo-feedback");

await page.goto(`${base}/check`);
await shot("check-intro");
await click("Start the check");
await shot("check-location");
await click("Drop a pin instead");
await shot("check-pin");
await page.getByLabel("Latitude").fill("37.8719");
await page.getByLabel("Longitude").fill("-122.2585");
await page.getByLabel("Name for this spot").fill("Footbridge");
await click("Next photo");
await shot("check-question-choice");
await click("U shape");
await click("Natural");
await click("Artificial (concrete or stones with concrete)");
await shot("check-question-multi");
await click("None of these");
await click("None of these");
await click("Slow");
await click("Clear or transparent");
for (let i = 0; i < 3; i++) await click("No");
await click("No");
await click("No");
await shot("check-question-number");
await click("Skip");
for (let i = 0; i < 4; i++) await click("No");
await click("Trees");
await click("Shrubs");
await click("No");
await click("No");
await shot("check-sliders");
await click("Next photo");
await shot("check-rating");
await page.getByRole("button", { name: /^Good:/ }).click();
await shot("check-photos");
await click("Send");
await page.getByRole("heading", { name: "One or two follow-ups" }).waitFor();
await shot("check-followups");
await page.getByRole("region", { name: "dry_pipe" }).getByRole("button", { name: "Yes", exact: true }).click();
await click("Keep my rating");
await click("Finish");
await page.getByRole("heading", { name: "Saved" }).waitFor();
await shot("check-done");

await page.goto(`${base}/spot/example`);
await page.getByText("4 of 4 on Built banks, tested Sep 23").waitFor();
await shot("spot-record");
await click("View as FHIR");
await page.getByText("passed the HL7 validator against guide commit").waitFor();
await shot("spot-fhir");
await page.goto(`${base}/two`);
await page.getByRole("region", { name: "Volunteer (Second Look)" }).waitFor();
await shot("two");
await page.goto(`${base}/quick/example`);
await shot("quick");
await page.goto(`${base}/poster`);
await shot("poster");
await page.goto(`${base}/about`);
await shot("about");
await page.goto(`${base}/privacy`);
await shot("privacy");
await page.goto(`${base}/how-we-know`);
await shot("how-we-know");
await page.goto(`${base}/share/13`);
await shot("share");
await page.goto(`${base}/offline`);
await shot("offline");
await browser.close();
console.log(`screens: ${n} screenshots in ${out}`);
