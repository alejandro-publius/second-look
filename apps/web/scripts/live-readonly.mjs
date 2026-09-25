// A phone check against production that writes nothing (Update 14 sections 0 and 6).
//
// Update 14 lifts the freeze on production on one condition: after every deploy the phone end to
// end tests pass against production. A whole sitting needs the Worker's QA key, which only Alex
// holds (docs/ALEX_TODO.md); without it the sitting would be stored as real. So this check walks
// every screen a phone reaches without starting a study session: the landing page and the guess,
// the consent screen, judge mode, the judges' door, a whole video walk with its record made on the
// phone and its demo creek, and the pages that read the API. It fails if any request writes to
// the study routes, if the public counts move, or if the counts cannot be read before and after.
//
// WALK_ID picks the walk. Without it the first walk in generated/content.json is used, and the log
// says which, so the walk steps are never skipped without a word.
//
// Run: SITE_URL=https://second-look-79t.pages.dev API_URL=... node scripts/live-readonly.mjs
import { readFileSync, realpathSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";

const CONTENT = fileURLToPath(new URL("../generated/content.json", import.meta.url));

/**
 * The public counts by arm, as one string to compare before and after, or the reason the read
 * failed. A reply that is not ok, or has no by_arm, is a failed read: two failed reads must never
 * compare equal and pass.
 */
export async function readCounts(api, fetchImpl = fetch) {
  try {
    const r = await fetchImpl(`${api}/api/test/counts`);
    if (!r.ok) return { error: `HTTP ${r.status}` };
    const body = await r.json();
    if (body?.by_arm === undefined || body.by_arm === null) return { error: "the reply has no by_arm" };
    return { value: JSON.stringify(body.by_arm) };
  } catch (e) {
    return { error: String(e).split("\n")[0].slice(0, 160) };
  }
}

/** The counts check: it passes only when both reads worked and say the same thing. */
export function countsCheck(before, after) {
  if (before.error !== undefined || after.error !== undefined) {
    return { pass: false, detail: `before: ${before.error ?? before.value}; after: ${after.error ?? after.value}` };
  }
  return { pass: before.value === after.value, detail: `${before.value} then ${after.value}` };
}

/** The walk to check: WALK_ID if set, else the first walk the web build knows, else none. */
export function chooseWalk(walkId, contentPath = CONTENT) {
  if (walkId) return { id: walkId, from: "WALK_ID" };
  try {
    const first = JSON.parse(readFileSync(contentPath, "utf8")).walks?.[0]?.id;
    if (first) return { id: String(first), from: "the first walk in generated/content.json" };
  } catch {
    // No web build here, so no content.json. The caller says the walk steps are skipped.
  }
  return { id: "", from: "" };
}

/**
 * Every creek the pick list on bare /city links, from the regions in the web build, in their
 * order: [{ slug, name }]. None when there is no web build here (UPDATE_30 section 1 item 4).
 */
export function pickListCreeks(contentPath = CONTENT) {
  try {
    const regions = Object.values(JSON.parse(readFileSync(contentPath, "utf8")).regions ?? {});
    return regions.flatMap((r) => r.creeks ?? []).map((c) => ({ slug: String(c.slug), name: String(c.name) }));
  } catch {
    return [];
  }
}

async function main() {
  const site = (process.env.SITE_URL ?? "").replace(/\/$/, "");
  const api = (process.env.API_URL ?? site).replace(/\/$/, "");
  if (!site) throw new Error("set SITE_URL");
  const walk = chooseWalk(process.env.WALK_ID ?? "");
  if (walk.id) console.log(`live-readonly: walk ${walk.id}, from ${walk.from}`);
  else console.log("live-readonly: SKIP the walk steps: WALK_ID is not set and generated/content.json has no walk");
  const walkId = walk.id;

  const results = [];
  const notYet = [];
  function ok(name, pass, detail = "") {
    results.push({ name, pass, detail });
    console.log(`live-readonly: ${pass ? "PASS" : "FAIL"} ${name}${detail ? `: ${detail}` : ""}`);
  }

  const before = await readCounts(api);
  const { chromium } = await import("@playwright/test");
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await context.newPage();
  const writes = [];
  page.on("request", (r) => {
    if (r.method() !== "GET" && /\/api\/(test|check|quick|upload)/.test(r.url())) writes.push(r.url());
  });

  async function step(name, fn) {
    try {
      await fn();
      ok(name, true);
    } catch (e) {
      ok(name, false, String(e).split("\n")[0].slice(0, 160));
    }
  }

  await step("landing, the question and the guess", async () => {
    await page.goto(`${site}/?src=other`);
    await page.getByRole("heading", { name: "Which creek is healthier?" }).waitFor({ timeout: 15000 });
    await page.getByRole("button", { name: "This creek, on the left" }).click();
    await page.getByRole("link", { name: "Find out in two minutes" }).waitFor();
  });
  await step("the consent screen, not consented to", async () => {
    await page.goto(`${site}/t`);
    await page.getByRole("heading", { name: "Before you start" }).waitFor({ timeout: 15000 });
  });
  await step("judge mode says when it opens", async () => {
    await page.goto(`${site}/demo`);
    await page.getByText("Judge mode opens on Sep 28").waitFor({ timeout: 15000 });
  });
  await step("the judges' door", async () => {
    await page.goto(`${site}/judges`);
    await page.getByRole("link", { name: "Check a creek from your desk" }).waitFor({ timeout: 15000 });
  });
  if (walkId) {
    await step("a whole video walk, the record made on the phone", async () => {
      await page.goto(`${site}/walk/${walkId}`);
      await page.getByRole("button", { name: "Start the check" }).click();
      for (let i = 0; i < 40; i++) {
        if (await page.getByRole("heading", { name: "Your record from the clip" }).isVisible()) break;
        if (await page.getByRole("button", { name: "Finish" }).isVisible()) {
          await page.getByRole("button", { name: "Finish" }).click();
          continue;
        }
        // Each kind of question has its own way on: Skip, "None of these", a choice, or Next.
        const skip = page.getByRole("button", { name: "Skip" });
        const none = page.getByRole("button", { name: "None of these" });
        const choice = page.getByRole("main").getByRole("group").first().getByRole("button");
        if (await skip.first().isVisible()) await skip.first().click();
        else if (await none.isVisible()) await none.click();
        else if (await choice.first().isVisible()) await choice.first().click();
        else await page.getByRole("button", { name: "Next", exact: true }).click();
      }
      await page.getByText("Every link inside the record checks out").waitFor({ timeout: 10000 });
    });
    await step("the walk's clip is served from our own origin", async () => {
      const r = await fetch(`${site}/walks/${walkId}.mp4`, { method: "HEAD" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
    });
    await step("the demo creek on /city", async () => {
      await page.getByRole("link", { name: "See this creek as a city would" }).click();
      await page.getByText("Checks from this phone: 1").waitFor({ timeout: 10000 });
    });
  }
  await step("what the city sees, from the API", async () => {
    await page.goto(`${site}/city?creek=strawberry-creek`);
    await page.locator("h2").first().waitFor({ timeout: 15000 });
  });
  // Bare /city's pick list: each creek link must open that creek, not only change the address
  // (CRITIC_13 W02).
  const picks = pickListCreeks();
  if (picks.length === 0) console.log("live-readonly: SKIP the /city pick list: generated/content.json names no creek");
  for (const creek of picks) {
    await step(`bare /city's link to ${creek.name} opens that creek`, async () => {
      await page.goto(`${site}/city`);
      await page.getByRole("main").getByRole("link", { name: creek.name, exact: true }).click();
      await page.waitForURL(`**/city?creek=${encodeURIComponent(creek.slug)}`, { timeout: 15000 });
      await page.getByText(`reported at ${creek.name}`).waitFor({ timeout: 15000 });
    });
  }
  await step("lab and volunteer side by side, from the API", async () => {
    await page.goto(`${site}/two`);
    // Our record shows whenever our API answers.
    await page.getByRole("region", { name: "Volunteer (Second Look)" }).waitFor({ timeout: 15000 });
  });
  // Their lab record comes from their sandbox through scripts/cache_their_records.py on the Mac.
  // While the job has stored nothing (their sandbox's name stopped resolving on 2026-09-23), this
  // is reported as NOT YET, apart from the passes, so their outage cannot hide a fault of ours.
  // REQUIRE_THEIRS=1 turns it into a failure.
  const pair = await fetch(`${api}/api/two`).then((r) => r.json()).catch(() => null);
  if (pair?.theirs_status === "down" && process.env.REQUIRE_THEIRS !== "1") {
    notYet.push("their lab record on /two: nothing stored by the Mac job yet");
    console.log("live-readonly: NOT YET their lab record on /two: the Mac job has stored nothing yet");
  } else {
    await step("their lab record beside ours, fetched from their sandbox by the Mac job", async () => {
      await page.goto(`${site}/two`);
      await page.getByRole("region", { name: "Lab (OneAquaHealth sandbox)" }).waitFor({ timeout: 15000 });
      await page.getByText("Fetched from their sandbox at").waitFor({ timeout: 5000 });
    });
  }

  await browser.close();
  const after = await readCounts(api);
  ok("no request wrote to the study, check, quick or upload routes", writes.length === 0, writes.join(", "));
  const counts = countsCheck(before, after);
  ok("the public counts did not move", counts.pass, counts.detail);
  const failed = results.filter((r) => !r.pass);
  console.log(`live-readonly: ${results.length - failed.length} of ${results.length} passed${notYet.length ? `, ${notYet.length} not yet (${notYet.join("; ")})` : ""}`);
  process.exit(failed.length ? 1 : 0);
}

// Run only as a script, so a test can import the helpers above without opening a browser.
if (process.argv[1] && import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href) await main();
