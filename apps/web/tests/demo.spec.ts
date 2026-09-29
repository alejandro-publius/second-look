import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

// Update 09 section 4.5: /demo gives feedback on the same sixteen photos the study uses, so it
// stays shut until the data lock. These tests move the browser clock past it.
const AFTER_LOCK = new Date("2026-09-29T00:00:00Z");
import { assertOnlyOurOrigins, goldFor, mockApi, watchRequests } from "./mock-api.mjs";
import { answerAllItems, BASE } from "./helpers";


// The real photographs have their own ids, so the item on screen is found through the generated
// content: photo url to photo id to test item.
const GENERATED = JSON.parse(readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"));
const ITEM_FOR_PHOTO_URL: Record<string, string> = Object.fromEntries(
  (GENERATED.test_items as { id: string; photo_id: string }[]).map((t) => [GENERATED.photos[t.photo_id].url, t.id]),
);

test("judge mode gives feedback, stores nothing, and teaches only what was missed", async ({ page }) => {
  const urls = watchRequests(page);
  const calls = await mockApi(page);
  await page.clock.install({ time: AFTER_LOCK });
  await page.goto("/demo");
  await expect(page.getByRole("heading", { name: "Judge mode" })).toBeVisible();
  await expect(page.getByText("Nothing here is stored.")).toBeVisible();
  await page.getByRole("button", { name: "Start judge mode" }).click();
  // Yes on everything: the mock's key has two present per feature, so every feature scores 2 of 4 and is missed.
  await answerAllItems(page, () => "Yes", true);
  await expect(page.getByRole("heading", { name: "What you missed" })).toBeVisible();
  const byFeature = page.getByRole("group", { name: "Score by feature" });
  await expect(byFeature.getByText("Built banks", { exact: true })).toBeVisible();
  await expect(byFeature.getByText("2 of 4").first()).toBeVisible();
  await page.getByRole("button", { name: "Show the lessons" }).click();
  await expect(page.locator(".gauge-count", { hasText: "Built banks" })).toBeVisible();
  expect(calls.filter((c) => c.path === "/api/demo/answer")).toHaveLength(16);
  expect(calls.filter((c) => c.path.startsWith("/api/test/"))).toHaveLength(0);
  expect(calls.filter((c) => c.path.startsWith("/api/check/"))).toHaveLength(0);
  expect(assertOnlyOurOrigins(urls, BASE)).toEqual([]);
});

test("a judge who passes every feature gets no lesson", async ({ page }) => {
  await mockApi(page);
  await page.clock.install({ time: AFTER_LOCK });
  await page.goto("/demo");
  await page.getByRole("button", { name: "Start judge mode" }).click();
  // The order is random, so read which photo is on screen and answer by the mock's own key.
  for (let i = 1; i <= 16; i++) {
    await expect(page.getByText(`Photo ${i} of 16`)).toBeVisible();
    const src = await page.locator("img.photo-large").getAttribute("src");
    const itemId = ITEM_FOR_PHOTO_URL[src!];
    expect(itemId, `no test item shows ${src}`).toBeTruthy();
    await page.getByRole("button", { name: goldFor(itemId) === "present" ? "Yes" : "No", exact: true }).click();
    await page.locator("[data-confirm]").click();
    await expect(page.getByRole("status")).toContainText("Right.");
    await page.getByRole("button", { name: i === 16 ? "Finish" : "Next photo", exact: true }).click();
  }
  await expect(page.getByText("You passed every feature. No lesson needed.")).toBeVisible();
});

test("?script=1 fixes the item order for the screen recording", async ({ page }) => {
  const order = async () => {
    const calls = await mockApi(page);
    await page.clock.install({ time: AFTER_LOCK });
    await page.goto("/demo?script=1");
    await expect(page.getByText("Scripted order for the screen recording.")).toBeVisible();
    await page.getByRole("button", { name: "Start judge mode" }).click();
    for (let i = 1; i <= 3; i++) {
      await page.getByRole("button", { name: "Yes", exact: true }).click();
      await page.locator("[data-confirm]").click();
      await page.getByRole("button", { name: "Next photo", exact: true }).click();
    }
    await page.unrouteAll({ behavior: "ignoreErrors" });
    return calls.filter((c) => c.path === "/api/demo/answer").map((c) => c.body.item_id);
  };
  const a = await order();
  const b = await order();
  expect(a).toHaveLength(3);
  expect(a).toEqual(b);
});

test("judge mode is shut before the lock and open after it", async ({ page }) => {
  await mockApi(page);
  await page.clock.install({ time: new Date("2026-09-24T12:00:00Z") });
  await page.goto("/demo");
  await expect(page.getByRole("heading", { name: "Judge mode opens on Sep 28" })).toBeVisible();
  // One moment, said once in both zones, so the heading's Sep 28 and the Sep 27 below it agree
  // (REVIEW_03 R44).
  await expect(page.getByText("It opens when the data locks: Sep 28 at 01:00 UTC, which is Sunday Sep 27 at 18:00 PDT.")).toBeVisible();
  // Shut means shut: no photo is fetched and no start button exists.
  await expect(page.locator("img.photo, img.photo-large")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Start judge mode" })).toHaveCount(0);

  await page.clock.install({ time: new Date("2026-09-29T00:00:00Z") });
  await page.goto("/demo");
  await expect(page.getByRole("heading", { name: "Judge mode" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start judge mode" })).toBeVisible();
});

// Audit finding time-bombs-5: both judge mode pages were built shut, so after the lock every reader
// saw "Judge mode opens on Sep 28" until the script had run, and for good with scripts off. The
// page as built now holds the heading alone, and none of the shut page's words.
for (const [path, title] of [
  ["/demo", "demo.title"],
  ["/t2/demo", "part2.demo_title"],
] as const) {
  test(`${path} as built holds its heading and no word of the shut page`, async ({ request }) => {
    const en: Record<string, string> = GENERATED.locale;
    const reply = await request.get(path);
    expect(reply.status()).toBe(200);
    const html = await reply.text();
    // Apostrophes and the like are escaped in HTML, so the words are looked for both ways.
    const escaped = (s: string) => s.replace(/&/g, "&amp;").replace(/'/g, "&#x27;").replace(/"/g, "&quot;");
    const holds = (s: string) => html.includes(s) || html.includes(escaped(s));
    expect(html).toMatch(new RegExp(`<h1[^>]*>${en[title]}</h1>`));
    for (const key of ["demo.shut_title", "demo.shut_body", "part2.demo_shut_body", "demo.shut_meanwhile"]) {
      expect(holds(en[key]), `${path} is built with ${key}`).toBe(false);
    }
    expect(html).not.toMatch(/opens on Sep 28|It opens when the data locks|Until then/);
    // Unknown is not open: no photo and no start button are built into the page either.
    expect(holds(en["demo.start"])).toBe(false);
    expect(html).not.toMatch(/<img[^>]+photo/);
  });

  test(`${path} with scripts off shows its heading, not that it opens on Sep 28`, async ({ browser }) => {
    const en: Record<string, string> = GENERATED.locale;
    const context = await browser.newContext({ javaScriptEnabled: false, serviceWorkers: "block" });
    const page = await context.newPage();
    await page.goto(`${BASE}${path}`);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(en[title]);
    await expect(page.getByRole("main")).not.toContainText("opens on Sep 28");
    await context.close();
  });

  test(`${path} never shows the shut heading on its way to open, after the lock`, async ({ page }) => {
    const en: Record<string, string> = GENERATED.locale;
    await mockApi(page);
    await page.clock.install({ time: AFTER_LOCK });
    // Every heading the page shows, from the first paint on.
    await page.addInitScript(() => {
      const seen: string[] = [];
      (window as unknown as { seenHeadings: string[] }).seenHeadings = seen;
      const note = () => {
        const text = document.querySelector("h1")?.textContent ?? "";
        if (text && seen[seen.length - 1] !== text) seen.push(text);
      };
      new MutationObserver(note).observe(document, { childList: true, subtree: true, characterData: true });
      document.addEventListener("DOMContentLoaded", note);
    });
    await page.goto(path);
    await expect(page.getByRole("button", { name: "Start judge mode" })).toBeVisible();
    const seen = await page.evaluate(() => (window as unknown as { seenHeadings: string[] }).seenHeadings);
    expect(seen).toEqual([en[title]]);
  });
}

test("the second look's judge mode is shut before the lock and open after it", async ({ page }) => {
  await mockApi(page);
  await page.clock.install({ time: new Date("2026-09-24T12:00:00Z") });
  await page.goto("/t2/demo");
  await expect(page.getByRole("heading", { name: "Judge mode opens on Sep 28" })).toBeVisible();
  await expect(page.getByText(GENERATED.locale["part2.demo_shut_body"])).toBeVisible();
  // Shut means shut: no photo is fetched and no start button exists.
  await expect(page.locator("img.photo, img.photo-large")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Start judge mode" })).toHaveCount(0);

  await page.clock.install({ time: AFTER_LOCK });
  await page.goto("/t2/demo");
  await expect(page.getByRole("heading", { name: "Assisted second look, judge mode" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start judge mode" })).toBeVisible();
});

// CRITIC_09 R02: the judges' door said judge mode "shows the right answer" after each photo. It
// says only right or not: the Worker sends back { correct } and never the answer. The door now says
// what judge mode does, and this holds the door to what the screens show.
test("the judges' door says what judge mode shows: right or not, never the answer", async ({ page }) => {
  const en: Record<string, string> = GENERATED.locale;
  const note = en["judges.demo_note"];
  expect(note).toContain("whether you were right");
  expect(note).not.toMatch(/right answer|the answer/i);
  await mockApi(page);
  await page.clock.install({ time: AFTER_LOCK });
  await page.goto("/judges");
  const door = page.locator(".row").filter({ has: page.getByRole("link", { name: en["judges.demo"], exact: true }) });
  await expect(door.locator(".row-value")).toHaveText(note);
  await door.getByRole("link", { name: en["judges.demo"], exact: true }).click();
  await page.getByRole("button", { name: "Start judge mode" }).click();
  // Can't tell is never right, and the line after it names no answer.
  await page.getByRole("button", { name: "Can't tell", exact: true }).click();
  await page.locator("[data-confirm]").click();
  await expect(page.getByRole("status")).toHaveText(en["demo.feedback_wrong"]);
});
