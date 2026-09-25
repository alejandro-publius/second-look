// The README gallery (UPDATE_27 block 23): a phone screenshot of every screen a person or a judge
// reaches, the frames of the two-minute test GIF, and two lesson photos with their marks.
//
// Two sources, never mixed up:
// - live: the read only pages, from the live site. Every request that could write is refused
//   before it leaves the browser (scripts/gallery-guard.mjs), and a refused request fails the run.
// - local mock: the test flow and the sample record, from a local production build with the fake
//   API in tests/mock-api.mjs, so no screenshot adds a session or a visit anywhere.
//
// Needs the local build on GALLERY_LOCAL_URL (make screens builds and starts it). Writes raw PNGs
// and captures.json to apps/web/screens/gallery/, which git ignores; scripts/make_gallery.py then
// frames and encodes them into docs/screens/ and writes results/screens.json.
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
import { API_ORIGIN, BUILT_IN_DEFAULT, goldFor, mockApi } from "../tests/mock-api.mjs";
import { liveRequestAllowed, localRequestAllowed } from "./gallery-guard.mjs";
import { toPageTop, toRegionTop, wholeOnFirstScreen } from "./gallery-view.mjs";
import { answerWalkPlainly } from "./gallery-walk.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const RAW = resolve(process.env.GALLERY_RAW || join(here, "..", "screens", "gallery"));
const LIVE = process.env.GALLERY_LIVE_URL || "https://second-look-79t.pages.dev";
const LOCAL = process.env.GALLERY_LOCAL_URL || "http://127.0.0.1:3217";
const content = JSON.parse(readFileSync(resolve(here, "..", "generated", "content.json"), "utf8"));
const firstWalk = (content.walks ?? [])[0];
// The two lesson photos the README shows with their marks: the first marked photo of each lesson.
const LESSON_PHOTOS = { artificial_bank: "built-bank", pipe_running: "pipe" };

// 390 by 844 CSS pixels at 2x: the phone the study runs on.
const PHONE = {
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 2,
  isMobile: true,
  hasTouch: true,
  serviceWorkers: "block",
  reducedMotion: "reduce",
  colorScheme: "light",
  locale: "en-US",
  timezoneId: "America/Los_Angeles",
};

rmSync(RAW, { recursive: true, force: true });
mkdirSync(RAW, { recursive: true });

const captures = { live_url: LIVE, screens: [], lesson_photos: [], gif_frames: [] };
const refused = [];
let shots = 0;

async function settle(page) {
  await page.waitForLoadState("load");
  await page.evaluate(() => document.fonts.ready);
  await page
    .waitForFunction(() => Array.from(document.images).every((i) => i.complete && i.naturalWidth > 0), null, { timeout: 15_000 })
    .catch(() => undefined);
  await page.waitForTimeout(400);
}

/** One viewport screenshot. Returns the raw file name. */
async function shoot(page) {
  // The pointer rests in the corner, so the button tapped last does not show its hover colour and
  // look chosen.
  await page.mouse.move(0, 0);
  await settle(page);
  shots += 1;
  const file = `raw-${String(shots).padStart(3, "0")}.png`;
  await page.screenshot({ path: join(RAW, file), animations: "disabled" });
  return file;
}

function gallery(name, route, source, file, alt) {
  captures.screens.push({ name, route, source, file, alt });
  console.log(`gallery: ${name} (${source}) ${route}`);
}

const button = (page, name) => page.getByRole("button", { name, exact: true });

// ---------------------------------------------------------------------------------------------
// Local mock: the two-minute test from consent to the score screen. Every state is a GIF frame
// with how long it stays up; the gallery takes its test flow screens from the same run.
// ---------------------------------------------------------------------------------------------
async function localRun(browser) {
  const context = await browser.newContext(PHONE);
  const allowed = [LOCAL, API_ORIGIN, BUILT_IN_DEFAULT];
  await context.route("**/*", (route) => {
    const url = route.request().url();
    if (localRequestAllowed(url, allowed)) return route.fallback();
    refused.push(`local: ${route.request().method()} ${url}`);
    return route.abort();
  });
  const page = await context.newPage();
  await mockApi(page, { lessonFirst: true });
  // Each frame shows the top of the screen, as a person first sees it, unless it is scrolled on
  // purpose to a marked photo.
  const frame = async (ms, { keepScroll = false } = {}) => {
    if (!keepScroll) await page.evaluate(() => window.scrollTo(0, 0));
    const file = await shoot(page);
    captures.gif_frames.push({ file, ms });
    return file;
  };

  await page.goto(`${LOCAL}/t`);
  gallery("consent", "/t", "local mock", await frame(1600), "The consent screen: what the test is, what is stored, and two boxes to tick.");
  await page.getByLabel("I understand and agree to take part.").check();
  await page.getByLabel("I am 18 or older.").check();
  await frame(900, { keepScroll: true });
  await button(page, "I agree, start").click();
  await page.getByRole("heading", { name: "Which creek is healthier?" }).waitFor();
  const warmup = await frame(1400);
  gallery("warmup", "/t", "local mock", warmup, "The warm-up: which creek is healthier, asked once before the test and answered at the end.");
  await button(page, "This creek, on the left").click();

  const lessons = Object.keys(content.lessons).length;
  for (let f = 0; f < lessons; f++) {
    // The first lesson shows every screen. The other three show the marks and the practice
    // feedback only: every frame with new photos costs bytes, and the GIF must stay under 3 MB.
    const full = f === 0;
    await page.locator(".gauge-count").first().waitFor();
    if (full) await frame(1000);
    await button(page, "Show what to look at").click();
    const marked = page.locator("figure.photoframe").nth(1);
    await marked.scrollIntoViewIfNeeded();
    const withMarks = await frame(1600, { keepScroll: true });
    // Which photo is on screen, read from the page, not assumed from the order of the lessons.
    const src = await marked.locator("img").getAttribute("src");
    const photoId = Object.entries(content.photos).find(([, p]) => p.url === src)?.[0];
    const feature = Object.keys(content.lessons).find((k) => content.lessons[k]?.contrast_pairs?.[0]?.actual_photo_id === photoId);
    if (feature === "artificial_bank") gallery("lesson-card", "/t", "local mock", withMarks, "A lesson card on built banks: a concrete channel with two numbered marks, and what each mark points at.");
    if (photoId && LESSON_PHOTOS[feature]) {
      const file = `lesson-${LESSON_PHOTOS[feature]}.png`;
      await settle(page);
      await marked.screenshot({ path: join(RAW, file), animations: "disabled" });
      const featureName = content.features.find((x) => x.id === feature)?.name ?? feature;
      captures.lesson_photos.push({ name: `lesson-${LESSON_PHOTOS[feature]}-marks`, feature, feature_name: featureName, photo_id: photoId, file });
      console.log(`gallery: lesson photo ${photoId}`);
    }
    await button(page, "Next photo").click();
    await page.locator(".gauge-count").first().waitFor();
    if (full) await frame(900);
    await button(page, "Next photo").click();
    await page.getByText("Try one. You get feedback on this photo only.").waitFor();
    if (full) await frame(900);
    await button(page, "Yes").click();
    await page.getByRole("status").first().waitFor();
    await frame(1300, { keepScroll: true });
    await button(page, f === lessons - 1 ? "Finish" : "Next photo").click();
  }

  // Sixteen items. Every frame is taken before the answer is chosen, so no frame pairs a test
  // photo with an answer: the GIF must not hand out the key while the study runs. The answers
  // themselves are right on twelve and wrong on the last item of each feature, so the score
  // screen shows a score a person could get.
  for (let i = 1; i <= 16; i++) {
    await page.getByText(`Photo ${i} of 16`).waitFor();
    const shot = await frame(i === 1 ? 1600 : 500);
    if (i === 1) gallery("test-item", "/t", "local mock", shot, "A test item: one creek photo, the question, and the buttons Yes, No and Can't tell.");
    // The mock hands out the sixteen items in reverse order, t16 first.
    const gold = goldFor(`t${String(17 - i).padStart(2, "0")}`);
    const right = i % 4 !== 0;
    await button(page, (gold === "present") === right ? "Yes" : "No").click();
    await page.locator("[data-confirm]").click();
  }
  await page.getByRole("heading", { name: "Almost done" }).waitFor();
  await frame(1400);
  await button(page, "See my score").click();
  await page.getByRole("heading", { name: "Your score" }).waitFor();
  gallery("score", "/t", "local mock", await frame(4000), "The score screen: the total and a score for each of the four features.");

  // The sample record. The live site has no record under this id, so it comes from the mock.
  await page.goto(`${LOCAL}/spot?id=example`);
  await page.getByText("4 of 4 on Built banks, tested Sep 23").first().waitFor();
  gallery("spot-record", "/spot?id=example", "local mock", await shoot(page), "A sample creek record: what the volunteer saw, and the observer score that goes with it.");
  await button(page, "View as FHIR").first().click();
  await page.getByText("passed the HL7 validator against guide commit").first().waitFor();
  gallery("spot-fhir", "/spot?id=example", "local mock", await shoot(page), "The same record opened with View as FHIR: the Observation the record is stored as.");
  // The health card, the record's last card: one thing to do for the person, one for the pet and
  // one for the city, each an approved sentence with its source. It renders only on a stored
  // record, and the live site has none under this id, so it comes from the mock (CRITIC_03 E01).
  // Opened again so View as FHIR is closed, then scrolled until the card's heading is at the top.
  await page.goto(`${LOCAL}/spot?id=example`);
  const health = page.getByRole("heading", { name: content.locale["spot.health_title"], exact: true });
  await health.waitFor();
  await health.evaluate((el) => {
    el.scrollIntoView({ block: "start" });
    window.scrollBy(0, -16);
  });
  gallery(
    "spot-health",
    "/spot?id=example",
    "local mock",
    await shoot(page),
    "The end of the sample record: the What you can do card, with one thing to do for you, one for your pet and one for the city, and the source of each.",
  );
  // The quick check opens from a record, with the record's spot in the link. With no spot it says
  // so and shows no form (CRITIC_09 R04), and the live site has no stored spot, so the picture of
  // the form comes from the mock, from the link the sample record gives.
  await page.goto(`${LOCAL}/quick?spot=example`);
  await page.getByRole("group", { name: content.locale["quick.colour"] }).waitFor();
  gallery("quick", "/quick?spot=example", "local mock", await shoot(page), "The quick check: water colour, smell and the pipe, in three taps.");
  await context.close();
}

// ---------------------------------------------------------------------------------------------
// Live, reading only.
// ---------------------------------------------------------------------------------------------
async function liveRun(browser) {
  const context = await browser.newContext(PHONE);
  await context.route("**/*", (route) => {
    const req = route.request();
    if (liveRequestAllowed(req.method(), req.url(), LIVE)) return route.fallback();
    refused.push(`live: ${req.method()} ${req.url()}`);
    return route.abort();
  });
  const page = await context.newPage();
  const visit = async (route) => {
    await page.goto(`${LIVE}${route}`);
    return shoot(page);
  };

  gallery("landing", "/", "live", await visit("/"), "The first screen: the question Which creek is healthier? above two creek photos.");
  await page.getByRole("button", { name: /This creek, on the left/ }).click();
  await page.getByText("Kept on this phone.", { exact: false }).waitFor();
  gallery("landing-guess", "/", "live", await shoot(page), "The same screen after a tap on the left photo: the guess is kept on the phone until the person agrees to take part.");
  gallery("demo", "/demo", "live", await visit("/demo"), "Judge mode today: it opens on Sep 28, when the data locks.");
  gallery("judges", "/judges", "live", await visit("/judges"), "The page for judges: every part of Second Look, in order.");
  gallery("walks", "/walk", "live", await visit("/walk"), "Check a creek from your desk: one short clip of a creek for each country.");
  if (firstWalk) {
    const route = `/walk/${firstWalk.id}`;
    // The alt text names the button, so the run fails unless the button is whole on the first
    // screen (CRITIC_11 V01). tests/walk.spec.ts takes the same step on every walk.
    await page.goto(`${LIVE}${route}`);
    await wholeOnFirstScreen(page, button(page, "Start the check"));
    gallery("walk", route, "live", await shoot(page), "A walk: the clip of a creek, with its credit, and a button to start the check.");
    await button(page, "Start the check").click();
    for (let step = 0; step < 2; step++) {
      const choice = page.getByRole("main").getByRole("group").first().getByRole("button");
      const skip = page.getByRole("button", { name: "Skip" });
      if (await choice.first().isVisible()) await choice.first().click();
      else await skip.first().click();
    }
    gallery("walk-in-progress", route, "live", await shoot(page), "A walk in progress: a question about the creek in the clip, with a progress count.");
    // The clip shows a natural creek, so an honest walk asks nothing of a city. The picture of the
    // city view comes from a walk that answers Artificial for the bank and reports no other damage,
    // and its alt text says so (CRITIC_09 Q01).
    await answerWalkPlainly(page, content, { bank: "present" });
    await page.getByRole("heading", { name: "Your record from the clip" }).waitFor();
    // From the top of the page, with the title in view, never from where the form left off.
    await toPageTop(page);
    gallery("walk-record", route, "live", await shoot(page), "The record from the walk, made on the phone and never sent, with a line saying every link inside it checks out.");
    await page.getByRole("link", { name: "See this creek as a city would" }).click();
    await page.waitForURL(/\/city/);
    await toRegionTop(page, content.locale["city.walk_needs"]);
    gallery("walk-city", "/city?walk=" + firstWalk.id, "live", await shoot(page), "The walk seen as a city would see it, after answering Artificial for the bank: what this demo creek needs, in OneAquaHealth's own measures, each with its source.");
  }
  gallery("check-start", "/check", "live", await visit("/check"), "The creek check: what it asks and a button to start.");
  await button(page, "Start the check").click();
  await button(page, "Drop a pin instead").waitFor();
  gallery("check-location", "/check", "live", await shoot(page), "The creek check asks where you are: use the phone's location or drop a pin.");
  await button(page, "Drop a pin instead").click();
  await page.getByLabel("Latitude").fill("37.8719");
  await page.getByLabel("Longitude").fill("-122.2585");
  await page.getByLabel("Name for this spot").fill("Footbridge");
  await page.getByRole("button", { name: /^Next/ }).first().click();
  gallery("check-question", "/check", "live", await shoot(page), "The first question of the creek check, with the answers as big buttons.");
  // The alt text says what the screen shows. Until somebody checks Strawberry Creek, the live
  // page has no visits and no measure on it, so the alt text says that instead.
  const cityShot = await visit("/city?creek=strawberry-creek");
  const cityEmpty = await page.getByText(/^0 visits at /).first().isVisible().catch(() => false);
  const cityAlt = cityEmpty
    ? "The city view of Strawberry Creek before anyone has checked it: no visits yet, and no OneAquaHealth measure shown yet."
    : "The city view of Strawberry Creek: what volunteers found there and what OneAquaHealth says to do.";
  gallery("city", "/city?creek=strawberry-creek", "live", cityShot, cityAlt);
  gallery("two", "/two", "live", await visit("/two"), "Two kinds of observer: a volunteer record in the same viewer built for a laboratory result.");
  gallery("how-we-know", "/how-we-know", "live", await visit("/how-we-know"), "How we know: where each rule and each number comes from.");
  gallery("credits", "/credits", "live", await visit("/credits"), "Credits: every photo and clip with its author and licence.");
  gallery("privacy", "/privacy", "live", await visit("/privacy"), "Privacy: what is stored and what is not.");
  gallery("about", "/about", "live", await visit("/about"), "About: what Second Look is and why it was built.");
  gallery("poster", "/poster", "live", await visit("/poster"), "The poster to print and put up by a creek, with its QR code.");
  gallery("accessibility", "/accessibility", "live", await visit("/accessibility"), "Accessibility: what we aim for and how each part is checked.");
  gallery("verify", "/verify", "live", await visit("/verify"), "Check a record: its receipt, its place in the audit log and the OpenTimestamps proof.");
  gallery("offline", "/offline", "live", await visit("/offline"), "The page a phone shows when it has no signal: what still works.");
  gallery("share", "/share/12", "live", await visit("/share/12"), "The page a shared score opens: the score card and a link to take the test.");
  await context.close();
}

const browser = await chromium.launch();
try {
  await localRun(browser);
  await liveRun(browser);
} finally {
  await browser.close();
}
writeFileSync(join(RAW, "captures.json"), JSON.stringify(captures, null, 2) + "\n");
if (refused.length) {
  console.log(`gallery: ${refused.length} request(s) refused, so the run fails:\n${refused.join("\n")}`);
  process.exit(1);
}
console.log(`gallery: ${captures.screens.length} screens, ${captures.lesson_photos.length} lesson photos, ${captures.gif_frames.length} GIF frames in ${RAW}`);
