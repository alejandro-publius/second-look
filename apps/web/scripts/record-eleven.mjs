// Screen recordings for the ElevenLabs-voiced video (docs/video/VOICE_SCRIPT.md, Oct 4), at a human
// pace, against a local production build and the mocked API, as record-clips.mjs does, so no
// recording adds a session or a visit anywhere. Each clip matches its narration: the score screen
// has every pipe caught and half the invasive plants missed, and the check reaches both follow-ups
// the words name, the dry pipe after nine dry days and the kept rating beside an artificial bank.
//
// Needs: npm run build && npm run start (WEB_PORT). Writes webm and marks to CLIPS_RAW.
import { mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
import { featureFor, goldFor, mockApi } from "../tests/mock-api.mjs";
import { WEB_ORIGIN } from "./web-port.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(process.env.CLIPS_RAW || join(here, "..", "..", "..", "docs", "video", "clips", "raw-eleven"));
mkdirSync(out, { recursive: true });
const base = WEB_ORIGIN;
const content = JSON.parse(readFileSync(resolve(here, "..", "generated", "content.json"), "utf8"));
const walk = (content.walks ?? [])[0];
const only = (process.env.ONLY || "").split(",").filter(Boolean);
const PHONE = { width: 390, height: 844 };
const DESKTOP = { width: 1280, height: 800 };
const beat = (ms = 900) => new Promise((r) => setTimeout(r, ms));
// As record-clips.mjs does: build with NEXT_PUBLIC_API_ORIGIN set to the live site, so a curl line
// on screen shows the live address, and name it in SCREENS_API_ORIGIN, so the mock answers it and
// nothing reaches it.
const API_AT = (process.env.SCREENS_API_ORIGIN || "").replace(/\/$/, "");
const CITY = { width: 1152, height: 648 };
const browser = await chromium.launch();

async function record(name, fn, { viewport = PHONE, mock = {} } = {}) {
  if (only.length && !only.includes(name)) return;
  const phone = viewport === PHONE;
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: 2,
    isMobile: phone,
    hasTouch: phone,
    serviceWorkers: "block",
    recordVideo: { dir: out, size: viewport },
  });
  const ours = [base, "file:", "data:", "blob:"];
  await context.route("**/*", (route) =>
    ours.some((o) => route.request().url().startsWith(o)) ? route.fallback() : route.abort("blockedbyclient"),
  );
  const page = await context.newPage();
  const t0 = Date.now();
  const marks = { start: 0 };
  const mark = (label) => {
    marks[label] = Math.round((Date.now() - t0) / 100) / 10;
  };
  page.setDefaultTimeout(15000);
  let routed = false;
  const onLive = {
    route: async (_url, handler) => {
      if (!routed) await page.route(`${API_AT}/**`, handler);
      routed = true;
    },
  };
  await mockApi(API_AT ? onLive : page, { lessonFirst: true, ...mock });
  try {
    await fn(page, mark);
  } catch (err) {
    await page.screenshot({ path: join(out, `${name}.error.png`) }).catch(() => undefined);
    console.log(`record-eleven: ${name} FAILED: ${String(err).split("\n")[0]}`);
    await context.close();
    return;
  }
  await beat(1500);
  marks.end = Math.round((Date.now() - t0) / 100) / 10;
  const path = await page.video().path();
  await context.close();
  renameSync(path, join(out, `${name}.webm`));
  writeFileSync(join(out, `${name}.marks.json`), JSON.stringify(marks) + "\n");
  console.log(`record-eleven: ${name} ${JSON.stringify(marks)}`);
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

async function answer(page, choice, pause) {
  await page.getByText(/Photo \d+ of 16/).waitFor();
  await page.evaluate(() => window.scrollTo(0, 0));
  await beat(pause);
  await page.getByRole("button", { name: choice, exact: true }).click();
  await beat(pause ? 500 : 0);
  await page.locator("[data-confirm]").click();
}

// Slide 4 (spare): the landing question and a tap.
await record("landing", async (page) => {
  await page.goto(`${base}/?src=other`);
  await beat(3000);
  await page.getByRole("button", { name: "This creek, on the left" }).click();
  await beat(5000);
});

// Slide 5 (spare): the first lesson cards.
await record("lesson", async (page, mark) => {
  await page.goto(`${base}/t`);
  await consent(page);
  await page.getByRole("button", { name: "This creek, on the left" }).click();
  await page.locator(".gauge-count").first().waitFor();
  await beat(300);
  mark("start");
  await beat(4500);
  await page.getByRole("button", { name: "Next photo", exact: true }).click();
  await beat(4000);
  await page.getByRole("button", { name: "Next photo", exact: true }).click();
  await page.getByRole("button", { name: "Yes", exact: true }).click();
  await beat(4000);
});

// Slide 6 (spare): test photos answered Yes, No and Can't tell.
await record("test", async (page, mark) => {
  await toTheTest(page);
  mark("start");
  for (const choice of ["Yes", "No", "Can't tell", "Yes", "No"]) await answer(page, choice, 1600);
  await beat(1500);
});

// Slide 7: "Maya caught every pipe, and missed half the invasive plants."
const WRONG = { artificial_bank: 0, dug_out_channel: 1, invasive_plant: 2, pipe_running: 0 };
await record("score", async (page, mark) => {
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
  // "It travels with everything she sends for ninety days": she keeps her score.
  await page.getByLabel(content.locale["end.keep_score"], { exact: false }).check();
  await page.getByRole("button", { name: "See my score" }).click();
  await page.getByRole("heading", { name: "Your score" }).waitFor();
  mark("start");
  await beat(5000);
  await page.mouse.wheel(0, 260);
  await beat(9000);
});

// Slide 8: a walk on real open footage; its first screen lists the six languages.
if (walk) {
  await record("walk", async (page, mark) => {
    await page.goto(`${base}/walk/${walk.id}`);
    await page.locator("video").evaluate((v) => {
      v.play().catch(() => undefined);
    }).catch(() => undefined);
    mark("start");
    await beat(8000);
    await click(page, "Start the check");
    await beat(1500);
    await click(page, "U Shape");
    await beat(3000);
  });
}

// Slide 9: an artificial bank, a Good rating and a pipe, sent; then the two follow-ups the words
// name: nine dry days and the pipe, then Keep my rating.
const DRY_PIPE = {
  rule_id: "dry_pipe",
  question_text: content.locale["followup.dry_pipe"].replace("{days}", "9"),
  kind: "yesno",
};
const RATING = {
  rule_id: "rating_check",
  question_text: content.locale["followup.rating_check"].replace("{issues}", "artificial banks"),
  kind: "keep_rating",
};
await record(
  "followup",
  async (page, mark) => {
    await page.goto(`${base}/check`);
    await beat(800);
    await page.getByRole("button", { name: "Start the check", exact: true }).click();
    await page.getByRole("button", { name: "Drop a pin instead" }).click();
    await page.getByLabel("Latitude").fill("37.8719");
    await page.getByLabel("Longitude").fill("-122.2585");
    await page.getByLabel("Name for this spot").fill("Footbridge");
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await beat(600);
    for (let i = 0; i < 60; i++) {
      const buttons = await page.getByRole("button").allInnerTexts();
      if (buttons.includes("Send")) break;
      const text = await page.locator("main").innerText();
      const norm = (b) => b.replace(/\s+/g, " ").trim();
      const find = (label) => buttons.map(norm).find((b) => b === label || b.startsWith(`${label} `));
      const pick = /pipes draining/i.test(text)
        ? "Yes"
        : ["Artificial (concrete or stones with concrete)", "Good quality", "U Shape"].map(find).find(Boolean) ??
          ["Natural", "Slow", "Clear/transparent", "No", "Skip", "Trees", "Next"].map(find).find(Boolean);
      if (!pick) throw new Error(`record-eleven: no answer for a check screen with ${buttons.map(norm).join(" | ")}`);
      await page.getByRole("button", { name: pick, exact: true }).first().click();
      await beat(60);
    }
    mark("send");
    await page.getByRole("button", { name: "Send", exact: true }).click();
    const q1 = page.getByText(DRY_PIPE.question_text.split("?")[0]);
    await q1.waitFor();
    await q1.evaluate((el) => el.scrollIntoView({ block: "center" }));
    mark("start");
    await beat(4000);
    await page.getByRole("button", { name: "Yes", exact: true }).first().click();
    await beat(1200);
    const q2 = page.getByText(RATING.question_text.split("?")[0]);
    await q2.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "center" }));
    mark("rating");
    await beat(3500);
    await page.getByRole("button", { name: content.locale["check.keep_rating"], exact: true }).click();
    await beat(4000);
  },
  { mock: { followups: [DRY_PIPE, RATING] } },
);

// Slide 10 (spare): /how-we-know through "AI on the same test" and the gate on real footage.
await record("how-we-know", async (page) => {
  await page.goto(`${base}/how-we-know`);
  await beat(2000);
  const ai = page.getByRole("heading", { name: "AI on the same test" });
  await ai.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "start" }));
  await beat(3000);
  for (let i = 0; i < 10; i++) {
    await page.mouse.wheel(0, 220);
    await beat(1400);
  }
});

// Slide 11: an answer beside its score, then View as FHIR with the validation badge.
await record("record", async (page, mark) => {
  await page.goto(`${base}/spot?id=example`);
  await beat(4500);
  mark("fhir");
  await page.getByRole("button", { name: "View as FHIR" }).first().click();
  await beat(11000);
});

// Slide 12: the creek's page for the city: what it needs, which pipes are worth testing, and how a
// lab result would come back.
await record(
  "city",
  async (page, mark) => {
    await page.goto(`${base}/city?creek=strawberry-creek`);
    await beat(3500);
    const needs = page.getByRole("heading", { name: "What OneAquaHealth says to do" });
    await needs.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "start" }));
    mark("needs");
    await beat(4500);
    const pipes = page.getByRole("heading", { name: "Pipes worth testing" });
    await pipes.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "start" }));
    mark("pipes");
    await beat(4500);
    await page.getByRole("button", { name: "Show how a result would come back" }).first().click();
    mark("result");
    await beat(6000);
  },
  { viewport: CITY },
);

await browser.close();
