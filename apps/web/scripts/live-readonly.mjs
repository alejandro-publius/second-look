// A phone check against production that writes nothing (Update 14 sections 0 and 6).
//
// Update 14 lifts the freeze on production on one condition: after every deploy the phone end to
// end tests pass against production. A whole sitting needs the Worker's QA key, which only Alex
// holds (docs/ALEX_TODO.md); without it the sitting would be stored as real. So this check walks
// every screen a phone reaches without starting a study session: the landing page and the guess,
// the consent screen, judge mode, the judges' door, a whole video walk with its record made on the
// phone and its demo creek, and the pages that read the API. It fails if any request writes to
// the study routes or if the public counts move.
//
// Run: SITE_URL=https://second-look-79t.pages.dev API_URL=... node scripts/live-readonly.mjs
import { chromium } from "@playwright/test";

const site = (process.env.SITE_URL ?? "").replace(/\/$/, "");
const api = (process.env.API_URL ?? site).replace(/\/$/, "");
const walkId = process.env.WALK_ID ?? "";
if (!site) throw new Error("set SITE_URL");

const results = [];
function ok(name, pass, detail = "") {
  results.push({ name, pass, detail });
  console.log(`live-readonly: ${pass ? "PASS" : "FAIL"} ${name}${detail ? `: ${detail}` : ""}`);
}

async function counts() {
  const r = await fetch(`${api}/api/test/counts`);
  return JSON.stringify((await r.json()).by_arm);
}

const before = await counts();
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
await step("lab and volunteer side by side, from the API", async () => {
  await page.goto(`${site}/two`);
  await page.locator(".row").first().waitFor({ timeout: 15000 });
});

await browser.close();
const after = await counts();
ok("no request wrote to the study, check, quick or upload routes", writes.length === 0, writes.join(", "));
ok("the public counts did not move", before === after, `${before} then ${after}`);
const failed = results.filter((r) => !r.pass);
console.log(`live-readonly: ${results.length - failed.length} of ${results.length} passed`);
process.exit(failed.length ? 1 : 0);
