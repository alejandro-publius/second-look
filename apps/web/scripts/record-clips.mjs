// Screen recordings for the video (Update 14 section 7 item 2), at a human pace, against a local
// production build and the mocked API, so no recording adds a session or a visit anywhere.
// Judge mode is recorded with Playwright's clock set after the lock: the lock constant is
// overridden in this test environment only, and the app is untouched.
//
// Needs: npm run build && npm run start (port 3100, or WEB_PORT). Writes webm to docs/video/clips/raw, then
// scripts/video_rough.py converts them to 30 fps mp4 in docs/video/clips/ (never committed).
// Clip names follow docs/video/SHOTLIST.md; extra-* clips are cutaways no beat names.
import { mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { featureFor, goldFor } from "../tests/mock-api.mjs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
import { mockApi } from "../tests/mock-api.mjs";
import { WEB_ORIGIN } from "./web-port.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(process.env.CLIPS_RAW || join(here, "..", "..", "..", "docs", "video", "clips", "raw"));
mkdirSync(out, { recursive: true });
const base = process.env.SCREENS_URL || WEB_ORIGIN;
const content = JSON.parse(readFileSync(resolve(here, "..", "generated", "content.json"), "utf8"));
const walk = (content.walks ?? [])[0];
// Playwright records at CSS pixels and pads, never scales, a page into a larger video size, so a
// video twice the viewport came out as a small page in a grey frame. The video is the viewport;
// scripts/video_rough.py scales it up.
const PHONE = { width: 390, height: 844 };
const PHONE_VIDEO = PHONE;
const DESKTOP = { width: 1280, height: 800 };
const beat = (ms = 900) => new Promise((r) => setTimeout(r, ms));

// UPDATE_30 section 4, the judge's review of the first final cut. Record against a build of the
// deployed commit made with NEXT_PUBLIC_API_ORIGIN set to the live site, as the deployed site calls
// its API on its own address: then a curl line on screen shows the live address, not this Mac.
// SCREENS_API_ORIGIN names that address, and the mock answers it as well, so nothing reaches it.
// Every other request that would leave this machine is refused, except the README's public badges.
const API_AT = (process.env.SCREENS_API_ORIGIN || "").replace(/\/$/, "");
const README_BADGES = ["https://img.shields.io/"];

const browser = await chromium.launch();

// Each clip also writes <name>.marks.json: the second of the recording where each named moment
// starts. "start" is where the video's use of the clip begins, past the consent and warm-up
// screens; scripts/video_final.py cuts the clip there, and a screen part of the shot list whose
// From names a mark starts at that mark. The seconds count from the page's first frame.
async function record(name, fn, { viewport = PHONE, video = PHONE_VIDEO, after, mock = {}, leave = [] } = {}) {
  const phone = viewport === PHONE;
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: 2,
    isMobile: phone,
    hasTouch: phone,
    serviceWorkers: "block",
    recordVideo: { dir: out, size: video },
  });
  const ours = [base, "file:", "data:", "blob:", ...leave];
  await context.route("**/*", (route) =>
    ours.some((o) => route.request().url().startsWith(o)) ? route.fallback() : route.abort("blockedbyclient"),
  );
  if (after) await context.clock.install({ time: new Date(after) });
  const page = await context.newPage();
  const t0 = Date.now();
  const marks = { start: 0 };
  const mark = (label) => {
    marks[label] = Math.round((Date.now() - t0) / 100) / 10;
  };
  // With SCREENS_API_ORIGIN, the mock's handler is handed to that address instead of its own two.
  let routed = false;
  const onLive = {
    route: async (_url, handler) => {
      if (!routed) await page.route(`${API_AT}/**`, handler);
      routed = true;
    },
  };
  await mockApi(API_AT ? onLive : page, { lessonFirst: true, ...mock });
  await fn(page, mark);
  await beat(1500);
  const path = await page.video().path();
  await context.close();
  renameSync(path, join(out, `${name}.webm`));
  writeFileSync(join(out, `${name}.marks.json`), JSON.stringify(marks) + "\n");
  console.log(`record-clips: ${name} ${JSON.stringify(marks)}`);
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

// Consent, the warm-up pair and the whole lesson at speed, for the clips that begin after them.
async function toTheTest(page) {
  await page.goto(`${base}/t`);
  await page.getByLabel("I understand and agree to take part.").check();
  await page.getByLabel("I am 18 or older.").check();
  await page.getByRole("button", { name: "I agree, start" }).click();
  await page.getByRole("button", { name: "This creek, on the left" }).click();
  await page.locator(".gauge-count").first().waitFor();
  for (let f = 0; f < 4; f++) {
    await page.getByRole("button", { name: "Next photo", exact: true }).click();
    await page.getByRole("button", { name: "Next photo", exact: true }).click();
    await page.getByRole("button", { name: "Yes", exact: true }).click();
    await page.getByRole("button", { name: f === 3 ? "Finish" : "Next photo", exact: true }).click();
  }
  await page.getByText(/Photo 1 of 16/).waitFor();
  await page.evaluate(() => window.scrollTo(0, 0));
}

// One test photo answered: the photo in view from the top of the page, the answer, then on.
async function answer(page, choice, pause) {
  await page.getByText(/Photo \d+ of 16/).waitFor();
  await page.evaluate(() => window.scrollTo(0, 0));
  await beat(pause);
  await page.getByRole("button", { name: choice, exact: true }).click();
  await beat(pause ? 500 : 0);
  await page.locator("[data-confirm]").click();
}

await record("01-landing", async (page) => {
  await page.goto(`${base}/?src=poster`);
  await beat(2500);
  await page.getByRole("button", { name: "This creek, on the left" }).click();
  await beat(4500);
});
// Beat 4: the video starts on the first lesson card, past consent and the warm-up. The practice
// photo with its marks is on screen for "marks the part that matters", then the dug-out channel's
// card for "a dug-out channel".
await record("04-lesson", async (page, mark) => {
  await page.goto(`${base}/t`);
  await consent(page);
  await page.getByRole("button", { name: "This creek, on the left" }).click();
  await page.locator(".gauge-count").first().waitFor();
  await beat(300);
  mark("start");
  await beat(5000);
  await page.getByRole("button", { name: "Next photo", exact: true }).click();
  await beat(4000);
  await page.getByRole("button", { name: "Next photo", exact: true }).click();
  await page.getByRole("button", { name: "Yes", exact: true }).click();
  await beat(4800);
  await page.getByRole("button", { name: "Next photo", exact: true }).click();
  await beat(6000);
});
// Beat 5: from the first test photo, seven photos answered Yes, No and Can't tell at a human pace,
// long enough for the beat, so the clip never starts over.
await record("05-test-items", async (page, mark) => {
  await toTheTest(page);
  mark("start");
  for (const choice of ["Yes", "No", "Can't tell", "Yes", "No", "Yes", "Can't tell"]) await answer(page, choice, 1700);
  await page.getByText(/Photo 8 of 16/).waitFor();
  await page.evaluate(() => window.scrollTo(0, 0));
  await beat(2000);
});
// Beat 6: the score screen with a different score on each feature, four of four on built banks as
// the words say. The answers are picked from the mock's key, one photo at a time.
const WRONG = { artificial_bank: 0, dug_out_channel: 1, invasive_plant: 2, pipe_running: 1 };
await record("06-end-score", async (page, mark) => {
  const session = page.waitForResponse((r) => r.url().endsWith("/api/test/session"));
  await toTheTest(page);
  const order = (await (await session).json()).item_order;
  const wrong = { ...WRONG };
  for (const item of order) {
    const feature = featureFor(item);
    const right = goldFor(item) === "present" ? "Yes" : "No";
    const miss = wrong[feature] > 0;
    if (miss) wrong[feature] -= 1;
    await answer(page, miss ? (right === "Yes" ? "No" : "Yes") : right, 0);
  }
  await page.getByRole("button", { name: "See my score" }).click();
  await page.getByRole("heading", { name: "Your score" }).waitFor();
  mark("start");
  await beat(14000);
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
  { after: "2026-10-03T05:00:00Z" },
);
// Beat 9: the start screen (the app's order, every question marked draft wording), a pin and the
// first questions at a human pace; then the rest of the form at speed, with a pipe reported, up to
// the dry weather question about that pipe, the mark "followups", which is answered Yes.
const DRY_PIPE = {
  rule_id: "dry_pipe",
  question_text: content.locale["followup.dry_pipe"].replace("{days}", "5"),
  kind: "yesno",
};
await record(
  "extra-check",
  async (page, mark) => {
    await page.goto(`${base}/check`);
    await beat(3000);
    await page.getByRole("button", { name: "Start the check", exact: true }).click();
    await beat(500);
    await page.getByRole("button", { name: "Drop a pin instead" }).click();
    await page.getByLabel("Latitude").fill("37.8719");
    await page.getByLabel("Longitude").fill("-122.2585");
    await page.getByLabel("Name for this spot").fill("Footbridge");
    await beat(400);
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await beat(3200);
    await click(page, "U shape");
    await beat(1500);
    for (let i = 0; i < 40; i++) {
      const buttons = await page.getByRole("button").allInnerTexts();
      if (buttons.includes("Send")) break;
      const text = await page.locator("main").innerText();
      const pick = /pipes draining/i.test(text)
        ? "Yes"
        : buttons.find((b) => b.startsWith("Moderate")) ??
          ["Natural", "Slow", "Clear or transparent", "No", "Skip", "Trees", "Next"].find((b) => buttons.includes(b));
      if (!pick) throw new Error(`record-clips: no answer for a check screen with ${buttons.join(", ")}`);
      await page.getByRole("button", { name: pick, exact: true }).first().click();
      await beat(150);
    }
    await page.getByRole("button", { name: "Send", exact: true }).click();
    const question = page.getByText(DRY_PIPE.question_text.split("?")[0]);
    await question.waitFor();
    await question.evaluate((el) => el.scrollIntoView({ block: "center" }));
    mark("followups");
    await beat(3500);
    await page.getByRole("button", { name: "Yes", exact: true }).click();
    await beat(6000);
  },
  { mock: { followups: [DRY_PIPE] } },
);
// Beat 10: the answer beside its score, then View as FHIR, which opens on the validation badge and
// the curl line, held for the rest of the beat.
await record("10-record", async (page) => {
  await page.goto(`${base}/spot?id=example`);
  await beat(4000);
  await page.getByRole("button", { name: "View as FHIR" }).first().click();
  await beat(11000);
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
  await beat(9000);
});
if (walk) {
  await record("13-walk", async (page) => {
    await page.goto(`${base}/walk/${walk.id}`);
    await page.locator("video").evaluate((v) => v.play()).catch(() => undefined);
    await beat(6500);
    await click(page, "Start the check");
    await click(page, "U shape");
    await beat(1500);
  });
}
// Beat 8: the top of the page, then down through "AI on the same test", the pass table and the gate
// on real footage, slowly enough to last the whole beat.
await record("08-how-we-know", async (page) => {
  await page.goto(`${base}/how-we-know`);
  await beat(2500);
  const ai = page.getByRole("heading", { name: "AI on the same test" });
  await ai.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "start" }));
  await beat(3500);
  for (let i = 0; i < 11; i++) {
    await page.mouse.wheel(0, 240);
    await beat(1500);
  }
});
await record("extra-score-filter", async (page) => {
  await page.goto(`${base}/spot?id=example`);
  await beat(2000);
  const filter = page.getByText("Only show answers from people who passed the test for that feature").first();
  if (await filter.isVisible()) await filter.click();
  await beat(3000);
});
// The README on a desktop, from a local render (make video-clips writes it), never GitHub. A badge
// that cannot load (the CI badge of a private repository) is taken out, not shown broken.
// 03: the paragraph with the River Habitat Survey and "None we know of". 07: the AI results, then
// the table of which features each model passed, which the words of beat 7 are about.
const readme = process.env.README_HTML;
if (readme) {
  const readmeClip = async (page, mark, to, then) => {
    await page.goto(`file://${readme}`);
    await page.evaluate(() => {
      for (const img of document.images) if (img.complete && img.naturalWidth === 0) (img.closest("a") ?? img).remove();
    });
    await page.getByText(to).first().evaluate((el) => {
      el.scrollIntoView({ block: "start" });
      window.scrollBy(0, -24);
    });
    await beat(200);
    mark("start");
    await beat(then ? 5500 : 16500);
    if (then) {
      await page.getByText(then).first().evaluate((el) => {
        const y = el.getBoundingClientRect().top + window.scrollY - 24;
        window.scrollTo({ top: y, behavior: "smooth" });
      });
      await beat(17000);
    }
  };
  await record("03-rhs-manual", (page, mark) => readmeClip(page, mark, "People judge a creek the way they judge a park"), {
    viewport: DESKTOP,
    video: DESKTOP,
    leave: README_BADGES,
  });
  await record(
    "07-readme-results",
    (page, mark) => readmeClip(page, mark, "The AI, on the same 16 photos", "Which features each model passed on the 16-photo test"),
    { viewport: DESKTOP, video: DESKTOP, leave: README_BADGES },
  );
}
await browser.close();
