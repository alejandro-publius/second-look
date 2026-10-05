// The demo video's screen recordings (docs/video/SHOTLIST.md, Oct 4): the app used from the first
// screen to the last, at a human pace, on a phone viewport. Frames come from Chrome's screencast
// at twice the CSS size, so a zoom-in stays sharp, and every tap and every zoom is logged for the
// cut to draw a tap ring and to zoom on what the words name.
//
// Two places, never mixed in one clip:
// - "live", the deployed site. The test sitting carries the QA key (x-qa-key), so it is stored as
//   a test and never counted; a video walk is a demo record, never counted and never sent to
//   OneAquaHealth's sandbox; judge mode, /verify and /judges store nothing.
// - "local", a local build with the mocked API (as record-clips.mjs records), for every screen the
//   live site cannot show without a real creek check: the follow-ups after nine dry days, the
//   record with each answer beside its score, the city page's pipes and lab result example, the
//   return check and the creek's timeline. The cut puts "Sample records, made up for this video."
//   on every local clip.
//
// Needs: QA_KEY (from the repository's .env, never printed), a local build started with
// NEXT_PUBLIC_API_ORIGIN and SCREENS_API_ORIGIN set to the live site, and WEB_PORT. Writes one
// folder of frames per clip, with clip.json (frames, taps, zooms, marks), under CLIPS_OUT.
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
import { mockApi } from "../tests/mock-api.mjs";
import { WEB_ORIGIN } from "./web-port.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(here, "..", "..", "..");
const OUT = resolve(process.env.CLIPS_OUT || join(ROOT, "docs", "video", "clips", "journey"));
const LIVE = "https://second-look-79t.pages.dev";
const API_AT = (process.env.SCREENS_API_ORIGIN || "").replace(/\/$/, "");
const QA = process.env.QA_KEY || "";
const ONLY = (process.env.ONLY || "").split(",").filter(Boolean);
const PHONE = { width: 390, height: 844 };
const content = JSON.parse(readFileSync(resolve(here, "..", "generated", "content.json"), "utf8"));
const beat = (ms = 900) => new Promise((r) => setTimeout(r, ms));
const now = () => Date.now() / 1000;

// The test's gold labels and the checker's flags are in the repository: the score screen can be
// made to say what the words say, and the checker's question can be met on purpose.
const rows = (file) =>
  [...readFileSync(join(ROOT, file), "utf8").matchAll(/\{ id: (\w+), feature: (\w+), photo_id: ([\w-]+), gold: (\w+) \}/g)].map(
    (m) => ({ id: m[1], feature: m[2], photo: m[3], gold: m[4] }),
  );
const TEST = Object.fromEntries(rows("content/test_items.yaml").map((r) => [r.id, r]));
const PART2 = rows("content/part2_items.yaml");
const FLAGS = Object.fromEntries(
  JSON.parse(readFileSync(join(ROOT, "results", "assist_flags.json"), "utf8")).items.map((i) => [i.item_id, i.flag?.points_to ?? null]),
);

const browser = await chromium.launch();

async function clip(name, where, fn, { mock = {} } = {}) {
  if (ONLY.length && !ONLY.includes(name)) return true;
  const ctx = await browser.newContext({
    viewport: PHONE,
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    serviceWorkers: "block",
    ...(where === "live" && QA ? { extraHTTPHeaders: { "x-qa-key": QA } } : {}),
  });
  const page = await ctx.newPage();
  page.setDefaultTimeout(20000);
  if (where === "local") {
    const ours = [WEB_ORIGIN, "data:", "blob:"];
    await ctx.route("**/*", (route) =>
      ours.some((o) => route.request().url().startsWith(o)) ? route.fallback() : route.abort("blockedbyclient"),
    );
    let routed = false;
    const onLive = {
      route: async (_url, handler) => {
        if (!routed) await page.route(`${API_AT}/**`, handler);
        routed = true;
      },
    };
    await mockApi(API_AT ? onLive : page, { lessonFirst: true, ...mock });
  }
  const dir = join(OUT, name);
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
  const cdp = await ctx.newCDPSession(page);
  const frames = [];
  let k = 0;
  cdp.on("Page.screencastFrame", ({ data, metadata, sessionId }) => {
    const f = `f${String(k++).padStart(5, "0")}.jpg`;
    writeFileSync(join(dir, f), Buffer.from(data, "base64"));
    frames.push({ f, t: metadata.timestamp });
    cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => undefined);
  });
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: 88, maxWidth: 780, maxHeight: 1688, everyNthFrame: 1 });
  const ev = { taps: [], zooms: [], marks: { start: now() } };
  const base = where === "live" ? LIVE : WEB_ORIGIN;
  const box = async (loc) => {
    const b = await loc.boundingBox();
    return b ? { x: b.x * 2, y: b.y * 2, w: b.width * 2, h: b.height * 2 } : null;
  };
  const api = {
    page,
    base,
    mark: (label) => {
      ev.marks[label] = now();
    },
    tap: async (loc, pause = 700) => {
      await loc.scrollIntoViewIfNeeded().catch(() => undefined);
      const b = await box(loc);
      if (b) ev.taps.push({ t: now(), x: b.x + b.w / 2, y: b.y + b.h / 2 });
      await loc.click();
      await beat(pause);
    },
    zoom: async (loc, ms = 2500) => {
      const b = await box(loc);
      const t0 = now();
      await beat(ms);
      if (b) ev.zooms.push({ t0, t1: now(), ...b });
    },
    show: async (loc, ms = 1200) => {
      await loc.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "center" }));
      await beat(ms);
    },
  };
  let ok = true;
  try {
    await fn(api);
  } catch (err) {
    ok = String(err).includes("ARM") ? "arm" : false;
    console.log(`record-journey: ${name} FAILED: ${String(err).split("\n")[0]}`);
    await page.screenshot({ path: join(dir, "error.png") }).catch(() => undefined);
  }
  await beat(1200);
  ev.marks.end = now();
  await cdp.send("Page.stopScreencast").catch(() => undefined);
  await beat(400);
  writeFileSync(join(dir, "clip.json"), JSON.stringify({ name, where, ok, frames, ...ev }));
  console.log(`record-journey: ${name} ${ok === true ? "ok" : "FAILED"}, ${frames.length} frames, marks ${Object.keys(ev.marks).join(" ")}`);
  await ctx.close();
  return ok;
}

const button = (page, name, exact = true) => page.getByRole("button", { name, exact });
const norm = (b) => b.replace(/\s+/g, " ").trim();

/** Answer the creek check's screens: an artificial bank, a Good rating, a pipe, the rest plain. */
async function answerCheck(api, { stopAt = null, pace = 250 } = {}) {
  const { page } = api;
  for (let i = 0; i < 60; i++) {
    const buttons = (await page.getByRole("button").allInnerTexts()).map(norm);
    if (buttons.some((b) => ["Send", "Finish"].includes(b)) && !buttons.some((b) => b.startsWith("Keep my rating"))) return "end";
    if (buttons.includes("Keep my rating")) return "followup";
    const text = await page.locator("main").innerText();
    if (stopAt && stopAt.test(text)) return "stop";
    const find = (label) => buttons.find((b) => b === label || b.startsWith(`${label} `));
    const pick = /pipes draining/i.test(text)
      ? "Yes"
      : ["Artificial (concrete or stones with concrete)", "Good quality", "U Shape"].map(find).find(Boolean) ??
        ["Natural", "Slow", "Clear/transparent", "No", "Skip", "Trees", "Next"].map(find).find(Boolean);
    if (!pick) throw new Error(`no answer for a check screen with ${buttons.join(" | ")}`);
    await api.tap(button(page, pick).first(), i < 3 ? 900 : pace);
  }
  throw new Error("the check did not end");
}

// ---- live ----------------------------------------------------------------------------------

async function liveTest(api) {
  const { page, base } = api;
  await page.goto(`${base}/`);
  api.mark("landing");
  await beat(3200);
  await api.tap(button(page, "This creek, on the left", false), 1800);
  api.mark("find_out");
  await api.tap(page.getByRole("link", { name: "Find out in two minutes" }), 1500);
  api.mark("consent");
  await beat(1500);
  await api.tap(page.getByLabel("I understand and agree to take part."), 700);
  await api.tap(page.getByLabel("I am 18 or older."), 700);
  const sessionResp = page.waitForResponse((r) => r.url().endsWith("/api/test/session"));
  await api.tap(button(page, "I agree, start"), 300);
  const session = await (await sessionResp).json();
  if (!session.lesson_first) throw new Error("ARM: this sitting's group takes the test first");
  if (await button(page, "This creek, on the left", false).isVisible().catch(() => false)) {
    await api.tap(button(page, "This creek, on the left", false), 900);
  }
  await page.locator(".gauge-count").first().waitFor();
  api.mark("lesson");
  for (let f = 0; f < 4; f++) {
    await beat(f === 0 ? 1200 : 600);
    if (f === 0) await api.zoom(page.locator("main img, main svg").first(), 2600);
    await api.tap(button(page, "Next photo"), f === 0 ? 1800 : 900);
    await api.tap(button(page, "Next photo"), 500);
    await api.tap(button(page, "Yes"), f === 0 ? 1500 : 600);
    await api.tap(button(page, f === 3 ? "Finish" : "Next photo"), 600);
  }
  await page.getByText(/Photo 1 of 16/).waitFor();
  api.mark("test");
  const wrong = { artificial_bank: 0, dug_out_channel: 1, invasive_plant: 2, pipe_running: 0 };
  for (const [n, item] of session.item_order.entries()) {
    const it = TEST[item];
    const right = it.gold === "present" ? "Yes" : "No";
    const miss = wrong[it.feature] > 0;
    if (miss) wrong[it.feature] -= 1;
    await page.getByText(/Photo \d+ of 16/).waitFor();
    await page.evaluate(() => window.scrollTo(0, 0));
    const slow = n < 4;
    await beat(slow ? 900 : 120);
    await api.tap(button(page, miss ? (right === "Yes" ? "No" : "Yes") : right), slow ? 600 : 100);
    await api.tap(page.locator("[data-confirm]"), slow ? 500 : 150);
  }
  api.mark("end_form");
  await beat(800);
  await api.tap(page.getByLabel(content.locale["end.keep_score"], { exact: false }), 900);
  await api.tap(button(page, "See my score"), 300);
  await page.getByRole("heading", { name: "Your score" }).waitFor();
  api.mark("score");
  await beat(1200);
  await api.zoom(page.locator(".card").first(), 3000);
  await api.show(page.getByText("Those two creeks again"), 1500);
  api.mark("reveal");
  await beat(3000);
  const ninety = page.getByText(/saved with every creek check you make for the next 90 days/);
  await api.show(ninety, 800);
  api.mark("ninety");
  await api.zoom(ninety, 2600);
}

async function liveWalk(api) {
  const { page, base } = api;
  await page.goto(`${base}/walk/v02`);
  await beat(1500);
  api.mark("start");
  const picker = page.getByRole("combobox").first();
  api.mark("langs");
  for (const lang of [...content.app_strings.languages.filter((l) => l !== "en"), "en"]) {
    await picker.selectOption(lang);
    await beat(550);
  }
  await page.locator("video").evaluate((v) => {
    v.play().catch(() => undefined);
  });
  api.mark("clip");
  await beat(5000);
  await api.tap(button(page, "Start the check"), 900);
  api.mark("questions");
  const at = await answerCheck(api);
  if (at !== "followup") throw new Error(`the walk ended at ${at}, not at the rating follow-up`);
  api.mark("followup");
  await api.zoom(page.getByText(/You rated this stream Good/).first(), 2600);
  await api.tap(button(page, "Keep my rating"), 1400);
  await api.tap(button(page, "Finish"), 300);
  await page.getByRole("heading", { name: "Your record from the clip" }).waitFor();
  api.mark("record");
  await beat(2500);
  await api.zoom(page.getByText(/tagged as a demo and is never counted/), 2200);
  await api.show(page.getByRole("heading", { name: "Your answers" }), 2500);
  await api.tap(button(page, "View as FHIR"), 300);
  api.mark("fhir");
  await beat(2500);
  await page.mouse.wheel(0, 420);
  await beat(2500);
  const city = page.getByRole("link", { name: "See this creek as a city would" });
  await api.show(city, 700);
  await api.tap(city, 2500);
  api.mark("city");
  await beat(1500);
  await page.mouse.wheel(0, 380);
  await beat(3500);
}

async function liveWalkItalian(api) {
  const { page, base } = api;
  await page.goto(`${base}/walk/v02`);
  await beat(1000);
  await page.getByRole("combobox").first().selectOption("it");
  api.mark("italian");
  await beat(1800);
  await api.tap(button(page, "Start the check"), 700);
  for (let i = 0; i < 40; i++) {
    const text = await page.locator("main").innerText();
    if (/pipes draining|acqua piovana/i.test(text)) break;
    const opts = page.locator("main button:not([data-confirm])");
    const names = (await opts.allInnerTexts()).map(norm);
    const idx = names.findIndex((b) => b && !/^(Back|Indietro|Enlarge|Start the check)$/i.test(b) && !/What counts/i.test(b));
    if (idx < 0) throw new Error(`no option on ${names.join(" | ")}`);
    await api.tap(opts.nth(idx), 200);
  }
  api.mark("pipe_question");
  await beat(1000);
  await api.zoom(page.locator("main h2, main legend").first(), 3500);
  await beat(1500);
}

async function liveChecker(api) {
  const { page, base } = api;
  await page.goto(`${base}/t2/demo`);
  await beat(1500);
  await api.tap(button(page, "Start judge mode"), 1200);
  api.mark("start");
  let met = false;
  for (let i = 0; i < 8 && !met; i++) {
    await page.getByText(/Photo \d+ of 8/).waitFor();
    const src = (await page.locator("main img").first().getAttribute("src")) ?? "";
    const item = PART2.find((r) => src.includes(r.photo));
    const flag = item ? FLAGS[item.id] : null;
    const right = item?.gold === "present" ? "Yes" : "No";
    // On the first photo the checker flags, answer against its flag, so its question comes up.
    const answer = flag ? (flag === "present" ? "No" : "Yes") : right;
    await beat(1000);
    await api.tap(button(page, answer), 600);
    await api.tap(page.locator("[data-confirm]"), 1200);
    const question = page.getByText(content.locale["part2.question"]);
    const asked = flag ? await question.waitFor({ timeout: 3000 }).then(() => true, () => false) : false;
    if (asked) {
      met = true;
      api.mark("look_again");
      await api.zoom(question, 3000);
      const why = page.getByRole("button", { name: /why/i }).or(page.locator("summary").filter({ hasText: /why/i }));
      if (await why.count()) {
        await api.tap(why.first(), 1500);
        api.mark("why");
        await beat(3500);
      }
      const opts = (await page.getByRole("button").allInnerTexts()).map(norm);
      const keep = opts.find((b) => /keep|looked again|stay/i.test(b)) ?? opts.find((b) => b === right);
      if (keep) await api.tap(button(page, keep), 1500);
      api.mark("after");
      await beat(2500);
    } else {
      await api.tap(button(page, "Next photo"), 600);
    }
  }
  if (!met) throw new Error("the checker's question never came up");
}

async function liveVerify(api) {
  const { page, base } = api;
  await page.goto(`${base}/verify`);
  await beat(2500);
  api.mark("log");
  await api.show(page.getByRole("heading", { name: "The audit log" }).first(), 3000);
  api.mark("stamps");
  await api.show(page.getByRole("heading", { name: "Timestamps anyone can check" }).first(), 3500);
}

async function liveJudges(api) {
  const { page, base } = api;
  await page.goto(`${base}/judges`);
  await beat(2500);
  for (let i = 0; i < 4; i++) {
    await page.mouse.wheel(0, 260);
    await beat(1200);
  }
}

// ---- local, sample records -----------------------------------------------------------------

const DRY_PIPE = { rule_id: "dry_pipe", question_text: content.locale["followup.dry_pipe"].replace("{days}", "9"), kind: "yesno" };
const RATING = {
  rule_id: "rating_check",
  question_text: content.locale["followup.rating_check"].replace("{issues}", "artificial banks"),
  kind: "keep_rating",
};

async function localCheck(api) {
  const { page, base } = api;
  await page.goto(`${base}/check`);
  await beat(800);
  await api.tap(button(page, "Start the check"), 400);
  await api.tap(button(page, "Drop a pin instead"), 300);
  await page.getByLabel("Latitude").fill("37.8719");
  await page.getByLabel("Longitude").fill("-122.2585");
  await page.getByLabel("Name for this spot").fill("Footbridge");
  await api.tap(button(page, "Next"), 400);
  api.mark("questions");
  const at = await answerCheck(api, { pace: 120 });
  if (at !== "end") throw new Error(`the check stopped at ${at}`);
  await api.tap(button(page, "Send"), 300);
  const q1 = page.getByText(DRY_PIPE.question_text.split("?")[0]);
  await q1.waitFor();
  await api.show(q1, 400);
  api.mark("followups");
  await api.zoom(q1, 2600);
  await api.tap(button(page, "Yes").first(), 1000);
  const q2 = page.getByText(RATING.question_text.split("?")[0]);
  await api.show(q2, 600);
  api.mark("rating");
  await api.zoom(q2, 2200);
  await api.tap(button(page, content.locale["check.keep_rating"]), 2500);
}

async function localRecord(api) {
  const { page, base } = api;
  await page.goto(`${base}/spot?id=example`);
  await beat(1500);
  const scored = page.getByText(/4 of 4 on Built banks/).first();
  await api.show(scored, 800);
  api.mark("answers");
  await api.zoom(scored.locator("xpath=.."), 2800);
  await api.tap(button(page, "View as FHIR").first(), 1200);
  api.mark("fhir");
  const badge = page.getByText(/passed the HL7 validator/).first();
  await api.show(badge, 600);
  await api.zoom(badge, 2600);
  await beat(1500);
}

async function localCity(api) {
  const { page, base } = api;
  await page.goto(`${base}/city?creek=strawberry-creek`);
  await beat(1500);
  api.mark("needs");
  await api.show(page.getByRole("heading", { name: "What OneAquaHealth says to do" }), 3200);
  const pipes = page.getByRole("heading", { name: "Pipes worth testing" });
  await api.show(pipes, 600);
  api.mark("pipes");
  await api.zoom(page.getByText(/after 9 dry/).first(), 2400);
  const before = page.url();
  await api.tap(page.getByRole("link", { name: "Referral as FHIR" }).first(), 600);
  api.mark("referral");
  await beat(2800);
  if (page.url() !== before) {
    await page.goBack();
    await beat(800);
    await api.show(page.getByRole("heading", { name: "Pipes worth testing" }), 600);
  }
  await api.tap(button(page, "Show how a result would come back").first(), 900);
  api.mark("result");
  const example = page.getByText(/This is an example, not a real result/).first();
  await api.show(example, 400);
  await api.zoom(example, 3000);
}

async function localReturn(api) {
  const { page, base } = api;
  await page.goto(`${base}/spot?id=example`);
  await beat(1500);
  api.mark("downstream");
  const up = page.getByText(/Upstream of here/).first();
  await api.zoom(up, 2600);
  const visits = page.getByRole("heading", { name: "Visits" });
  await api.show(visits, 700);
  api.mark("timeline");
  await beat(2200);
  const quick = page.getByRole("link", { name: "Quick check" }).or(button(page, "Quick check")).first();
  await api.show(quick, 400);
  await api.tap(quick, 1500);
  api.mark("quick");
  for (let i = 0; i < 6; i++) {
    const names = (await page.getByRole("button").allInnerTexts()).map(norm);
    const done = names.find((b) => /^(Send|Save|Finish)$/.test(b));
    if (done) {
      await api.tap(button(page, done), 2200);
      break;
    }
    const opt = names.find((b) => b && !/^(Back|Quick check|Creek check|Cancel)$/i.test(b));
    if (!opt) break;
    await api.tap(button(page, opt).first(), 700);
  }
  api.mark("after_quick");
  await beat(2000);
}

const which = process.env.WHERE || "live,local";
if (which.includes("live")) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const ok = await clip("p-test", "live", liveTest);
    if (ok !== "arm") break;
  }
  await clip("p-walk", "live", liveWalk);
  await clip("p-walk-it", "live", liveWalkItalian);
  await clip("p-checker", "live", liveChecker);
  await clip("p-verify", "live", liveVerify);
  await clip("p-judges", "live", liveJudges);
}
if (which.includes("local")) {
  await clip("l-check", "local", localCheck, { mock: { followups: [DRY_PIPE, RATING] } });
  await clip("l-record", "local", localRecord);
  await clip("l-city", "local", localCity);
  await clip("l-return", "local", localReturn);
}
await browser.close();
