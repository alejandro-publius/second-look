// The stage 1 screens, at the phone size the study will actually run on, into docs/screens/.
// Viewport shots, not full page, because what is above the fold is the thing being judged.
// Needs the production server on 3100 (npm run build && npm run start).
import { mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
import { mockApi } from "../tests/mock-api.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "..", "..", "..", "docs", "screens");
mkdirSync(out, { recursive: true });
const base = process.env.SCREENS_URL || "http://127.0.0.1:3100";
const PHONE = { width: 390, height: 844 };

const browser = await chromium.launch();

async function open(colorScheme = "light", viewport = PHONE) {
  const context = await browser.newContext({ viewport, deviceScaleFactor: 2, isMobile: viewport === PHONE, hasTouch: viewport === PHONE, colorScheme, serviceWorkers: "block" });
  const page = await context.newPage();
  await mockApi(page, { lessonFirst: true });
  return page;
}

async function shot(page, name) {
  await page.waitForFunction(() => Array.from(document.images).every((i) => i.complete)).catch(() => undefined);
  // Move the pointer off the last thing clicked, or one choice ships looking different from the
  // other two, in a study whose point is that the three answers carry equal weight.
  await page.mouse.move(0, 0);
  const path = join(out, `${name}.png`);
  await page.screenshot({ path, animations: "disabled" });
  console.log(`design-screens: ${path}`);
}

const click = (page, name, exact = true) => page.getByRole("button", { name, exact }).click();
// The pick button contains the photograph, so its accessible name starts with the image alt text.
const pick = (page) => page.getByRole("button", { name: "This creek, on the left" }).click();

// Walks consent to the screen asked for. lessonFirst is on, so the lesson comes before the test.
async function walk(page, to) {
  await page.goto(`${base}/t`);
  await page.getByRole("heading", { name: "Before you start" }).waitFor();
  if (to === "consent") return;
  await page.getByLabel("I understand and agree to take part.").check();
  await page.getByLabel("I am 18 or older.").check();
  await click(page, "I agree, start");
  await pick(page);
  await page.locator(".gauge-count").first().waitFor();
  if (to === "lesson") return;
  for (let f = 0; f < 4; f++) {
    await click(page, "Next photo");
    await click(page, "Next photo");
    await click(page, "Yes");
    await click(page, f === 3 ? "Finish" : "Next photo");
  }
  await page.getByText("Photo 1 of 16").waitFor();
  if (to === "item") return;
  for (let i = 1; i <= 16; i++) {
    await click(page, "Yes");
    await page.locator("[data-confirm]").click();
  }
  await page.getByRole("heading", { name: "Almost done" }).waitFor();
  await click(page, "See my score");
  await page.getByRole("heading", { name: "Your score" }).waitFor();
}

// 1 to 6: the launch path on a phone, in light mode.
{
  const page = await open();
  await page.goto(`${base}/?src=poster`);
  await shot(page, "01-landing");
  await pick(page);
  await shot(page, "02-landing-guess");
  await page.close();
}
for (const [name, to] of [["03-consent", "consent"], ["04-lesson-card", "lesson"], ["05-test-item", "item"], ["06-end-score", "score"]]) {
  const page = await open();
  await walk(page, to);
  await shot(page, name);
  await page.close();
}
{
  const page = await open();
  await page.goto(`${base}/demo`);
  await page.getByRole("heading", { name: "Judge mode" }).waitFor();
  await shot(page, "07-demo");
  await page.close();
}
// 8: the test item in dark mode.
{
  const page = await open("dark");
  await walk(page, "item");
  await shot(page, "08-test-item-dark");
  await page.close();
}
// 9: the landing page on a desktop, the one wide screen judges will open.
{
  const page = await open("light", { width: 1280, height: 800 });
  await page.goto(`${base}/`);
  await shot(page, "09-landing-desktop");
  await page.close();
}

await browser.close();
