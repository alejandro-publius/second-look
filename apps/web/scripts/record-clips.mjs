// Screen recordings for the video (Update 14 section 7 item 2), at a human pace, against a local
// production build and the mocked API, so no recording adds a session or a visit anywhere.
// Judge mode is recorded with Playwright's clock set after the lock: the lock constant is
// overridden in this test environment only, and the app is untouched.
//
// Needs: npm run build && npm run start (port 3100). Writes webm to docs/video/clips/raw, then
// scripts/video_rough.py converts them to 30 fps mp4 in docs/video/clips/ (never committed).
// Clip names follow docs/video/SHOTLIST.md; extra-* clips are cutaways no beat names.
import { mkdirSync, readFileSync, renameSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
import { mockApi } from "../tests/mock-api.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(process.env.CLIPS_RAW || join(here, "..", "..", "..", "docs", "video", "clips", "raw"));
mkdirSync(out, { recursive: true });
const base = process.env.SCREENS_URL || "http://127.0.0.1:3100";
const content = JSON.parse(readFileSync(resolve(here, "..", "generated", "content.json"), "utf8"));
const walk = (content.walks ?? [])[0];
// Playwright records at CSS pixels and pads, never scales, a page into a larger video size, so a
// video twice the viewport came out as a small page in a grey frame. The video is the viewport;
// scripts/video_rough.py scales it up.
const PHONE = { width: 390, height: 844 };
const PHONE_VIDEO = PHONE;
const DESKTOP = { width: 1280, height: 800 };
const beat = (ms = 900) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch();

async function record(name, fn, { viewport = PHONE, video = PHONE_VIDEO, after } = {}) {
  const phone = viewport === PHONE;
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: 2,
    isMobile: phone,
    hasTouch: phone,
    serviceWorkers: "block",
    recordVideo: { dir: out, size: video },
  });
  if (after) await context.clock.install({ time: new Date(after) });
  const page = await context.newPage();
  await mockApi(page, { lessonFirst: true });
  await fn(page);
  await beat(1500);
  const path = await page.video().path();
  await context.close();
  renameSync(path, join(out, `${name}.webm`));
  console.log(`record-clips: ${name}`);
}

const click = async (page, name, exact = true) => {
  await page.getByRole("button", { name, exact }).click();
  await beat();
};

async function consent(page) {
  await page.getByLabel("I understand and agree to take part.").check();
  await beat(600);
  await page.getByLabel("I am 18 or older.").check();
  await beat(600);
  await click(page, "I agree, start");
}

await record("01-landing", async (page) => {
  await page.goto(`${base}/?src=poster`);
  await beat(2500);
  await page.getByRole("button", { name: "This creek, on the left" }).click();
  await beat(2500);
});
await record("04-lesson", async (page) => {
  await page.goto(`${base}/t`);
  await consent(page);
  await page.getByRole("button", { name: "This creek, on the left" }).click();
  await page.locator(".gauge-count").first().waitFor();
  await beat(2500);
  await click(page, "Next photo");
  await beat(2500);
});
await record("05-test-items", async (page) => {
  await page.goto(`${base}/t`);
  await consent(page);
  await page.getByRole("button", { name: "This creek, on the left" }).click();
  await page.locator(".gauge-count").first().waitFor();
  for (let f = 0; f < 4; f++) {
    await page.getByRole("button", { name: "Next photo", exact: true }).click();
    await page.getByRole("button", { name: "Next photo", exact: true }).click();
    await page.getByRole("button", { name: "Yes", exact: true }).click();
    await page.getByRole("button", { name: f === 3 ? "Finish" : "Next photo", exact: true }).click();
  }
  for (const answer of ["Yes", "No", "Can't tell"]) {
    await page.getByText(/Photo \d+ of 16/).waitFor();
    await beat(1500);
    await click(page, answer);
    await page.locator("[data-confirm]").click();
    await beat();
  }
});
await record("06-end-score", async (page) => {
  await page.goto(`${base}/t`);
  await consent(page);
  await page.getByRole("button", { name: "This creek, on the left" }).click();
  await page.locator(".gauge-count").first().waitFor();
  for (let f = 0; f < 4; f++) {
    await page.getByRole("button", { name: "Next photo", exact: true }).click();
    await page.getByRole("button", { name: "Next photo", exact: true }).click();
    await page.getByRole("button", { name: "Yes", exact: true }).click();
    await page.getByRole("button", { name: f === 3 ? "Finish" : "Next photo", exact: true }).click();
  }
  for (let i = 1; i <= 16; i++) {
    await page.getByRole("button", { name: "Yes", exact: true }).click();
    await page.locator("[data-confirm]").click();
  }
  await page.getByRole("button", { name: "See my score" }).click();
  await page.getByRole("heading", { name: "Your score" }).waitFor();
  await beat(4000);
});
await record(
  "extra-judge-mode",
  async (page) => {
    await page.goto(`${base}/judges`);
    await beat(2000);
    await page.goto(`${base}/demo?script=1`);
    await beat(2000);
    await page.getByRole("button").first().click();
    await beat(2500);
  },
  { after: "2026-09-28T02:00:00Z" },
);
await record("extra-check", async (page) => {
  await page.goto(`${base}/check`);
  await beat(1500);
  await click(page, "Start the check");
  await page.getByRole("button", { name: "Drop a pin instead" }).click();
  await beat();
  await page.getByLabel("Latitude").fill("37.8719");
  await page.getByLabel("Longitude").fill("-122.2585");
  await page.getByLabel("Name for this spot").fill("Footbridge");
  await click(page, "Next");
  await click(page, "U shape");
  await beat(1500);
});
await record("10-record", async (page) => {
  await page.goto(`${base}/spot?id=example`);
  await beat(2500);
  await page.getByRole("button", { name: "View as FHIR" }).first().click();
  await beat(3500);
});
await record("11-two", async (page) => {
  await page.goto(`${base}/two`);
  await beat(3500);
});
// Beat 12 ends on "the health card gives one action for you, one for your dog, and one for your
// city", and /city has no health card, so part 12.3 of the shot list is the sample record's
// health card, from the same mock (CRITIC_03 E01).
await record("12-city", async (page) => {
  await page.goto(`${base}/city?creek=strawberry-creek`);
  await beat(2500);
  await page.mouse.wheel(0, 600);
  await beat(2500);
  await page.goto(`${base}/spot?id=example`);
  const health = page.getByRole("heading", { name: content.locale["spot.health_title"], exact: true });
  await health.waitFor();
  await health.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "start" }));
  await beat(6000);
});
if (walk) {
  await record("13-walk", async (page) => {
    await page.goto(`${base}/walk/${walk.id}`);
    await beat(1500);
    await page.locator("video").evaluate((v) => v.play()).catch(() => undefined);
    await beat(5000);
    await click(page, "Start the check");
    await click(page, "U shape");
    await beat(1500);
  });
}
await record("08-how-we-know", async (page) => {
  await page.goto(`${base}/how-we-know`);
  await beat(2500);
  for (let i = 0; i < 4; i++) {
    await page.mouse.wheel(0, 300);
    await beat(1200);
  }
});
await record("extra-score-filter", async (page) => {
  await page.goto(`${base}/spot?id=example`);
  await beat(2000);
  const filter = page.getByText("Only show answers from people who passed the test for that feature").first();
  if (await filter.isVisible()) await filter.click();
  await beat(3000);
});
// The README on a desktop, from a local render (make video-clips writes it), never GitHub.
const readme = process.env.README_HTML;
if (readme) {
  for (const [name, anchor] of [["03-rhs-manual", "the-problem"], ["07-readme-results", ""]]) {
    await record(
      name,
      async (page) => {
        await page.goto(`file://${readme}${anchor ? `#${anchor}` : ""}`);
        await beat(4000);
      },
      { viewport: DESKTOP, video: DESKTOP },
    );
  }
}
await browser.close();
