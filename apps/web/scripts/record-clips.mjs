// Screen recordings for the video (UPDATE_14 section 7 item 2), at a human pace, against the
// production build on port 3100 and the fake API, so nothing is sent anywhere and no real
// session is stored. Judge mode is recorded with the page clock set after the lock, in this
// browser only; the site itself is untouched.
//
// Run: npm run build && npm run start (in another shell), then node scripts/record-clips.mjs
// Clips go to CLIPS_DIR (default ~/second-look-clips) as .webm, one per beat, never into the
// repo. Convert with: ffmpeg -i clip.webm -r 30 -c:v libx264 -pix_fmt yuv420p clip.mp4
import { mkdirSync, renameSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { chromium, devices } from "@playwright/test";
import { mockApi } from "../tests/mock-api.mjs";

const base = process.env.SCREENS_URL || "http://127.0.0.1:3100";
const out = process.env.CLIPS_DIR || join(homedir(), "second-look-clips");
mkdirSync(out, { recursive: true });
const AFTER_LOCK = new Date("2026-09-29T00:00:00Z");
const phone = devices["iPhone 13"];
const size = { width: phone.viewport.width * 2, height: phone.viewport.height * 2 };
const pause = (page, ms = 1200) => page.waitForTimeout(ms);

async function slowScroll(page, steps = 6) {
  for (let i = 0; i < steps; i++) {
    await page.mouse.wheel(0, 260);
    await pause(page, 700);
  }
}

const clips = {
  "01-landing": async (page) => {
    await page.goto(`${base}/`);
    await pause(page, 4000);
    await slowScroll(page, 4);
  },
  "05-demo-three-items": async (page) => {
    await page.clock.install({ time: AFTER_LOCK });
    await page.goto(`${base}/demo?script=1`);
    await pause(page, 2000);
    await page.getByRole("button", { name: "Start judge mode" }).click();
    for (let i = 0; i < 3; i++) {
      await pause(page, 2500);
      await page.getByRole("button", { name: "Yes", exact: true }).click();
      await pause(page, 800);
      await page.locator("[data-confirm]").click();
      await pause(page, 2500);
      await page.getByRole("button", { name: "Next photo", exact: true }).click();
    }
    await pause(page, 1500);
  },
  "10-spot-record": async (page) => {
    await page.goto(`${base}/spot?id=example`);
    await pause(page, 2500);
    await slowScroll(page, 8);
  },
  "11-two": async (page) => {
    await page.goto(`${base}/two`);
    await pause(page, 3000);
    await slowScroll(page, 5);
  },
  "12-city": async (page) => {
    await page.goto(`${base}/city?creek=strawberry-creek`);
    await pause(page, 3000);
    await slowScroll(page, 8);
  },
  "13-judges": async (page) => {
    await page.goto(`${base}/judges`);
    await pause(page, 3000);
    await slowScroll(page, 5);
  },
};

const only = process.argv.slice(2);
const browser = await chromium.launch();
let failed = 0;
for (const [name, run] of Object.entries(clips)) {
  if (only.length && !only.includes(name)) continue;
  const context = await browser.newContext({
    ...phone,
    serviceWorkers: "block",
    recordVideo: { dir: out, size },
  });
  const page = await context.newPage();
  await mockApi(page);
  try {
    await run(page);
  } catch (err) {
    failed++;
    console.log(`record-clips: ${name} failed: ${String(err).split("\n")[0]}`);
  }
  const video = page.video();
  await context.close();
  if (video) {
    const target = join(out, `${name}.webm`);
    renameSync(await video.path(), target);
    console.log(`record-clips: ${target}`);
  }
}
await browser.close();
process.exit(failed ? 1 : 0);
