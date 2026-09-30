import { expect, test } from "@playwright/test";
import { mockApi } from "./mock-api.mjs";

// The audit of Sep 29 (docs-consistency-5, privacy-security-1): /privacy named neither the second
// look, nor the language a check or a walk was shown in, nor the language kept on the phone, nor
// the note that stays when a photo is deleted. All four are stored. The words are written out
// here, not read from the locale, so taking one out of the locale turns this red.

const stored = (page: import("@playwright/test").Page) =>
  page.getByRole("main").locator("ul").first().locator("li");

test("/privacy lists the test, the second look, the creek check, photos, the walk and the phone", async ({ page }) => {
  await mockApi(page);
  await page.goto("/privacy");
  const starts = (await stored(page).allTextContents()).map((s) => s.slice(0, s.indexOf(":")));
  expect(starts).toEqual(["Test", "Second look, if you take it", "Creek check", "Photos", "Video walk", "On your phone only"]);
});

test("/privacy says what the second look stores, and what a No thanks leaves", async ({ page }) => {
  await mockApi(page);
  await page.goto("/privacy");
  const item = stored(page).filter({ hasText: /^Second look/ });
  await expect(item).toHaveCount(1);
  for (const words of [
    "which test it follows",
    "Your first and final answer to each of its eight photos",
    "Whether the checker asked you to look again",
    "whether you chose Keep or Change",
    "How long each answer took",
    "The same hash of your browser token",
    // A row for No thanks holds more than the no (worker/src/part2.ts, offer).
    "If you say No thanks, we keep only this: that you said no, when you said it, which test it follows, your group in that test and the same hash.",
  ]) {
    await expect(item).toContainText(words);
  }
});

test("/privacy says a creek check and a walk store the language the questions were shown in", async ({ page }) => {
  await mockApi(page);
  await page.goto("/privacy");
  await expect(stored(page).filter({ hasText: /^Creek check:/ })).toContainText("The language the questions were shown in.");
  await expect(stored(page).filter({ hasText: /^Video walk:/ })).toContainText("the language the questions were shown in");
});

test("/privacy says a short note about a photo stays after the photo is deleted", async ({ page }) => {
  await mockApi(page);
  await page.goto("/privacy");
  const item = stored(page).filter({ hasText: /^Photos:/ });
  await expect(item).toContainText("deleted after 30 days");
  await expect(item).toContainText("A short note about each photo stays after that");
  await expect(item).toContainText("a hash of the key that opens it");
});

test("the language picked on /check is kept on the phone, and /privacy says so", async ({ page }) => {
  await mockApi(page);
  await page.goto("/check");
  await page.getByLabel("Language of the questions").selectOption("pt");
  expect(await page.evaluate(() => localStorage.getItem("sl.check_lang"))).toBe("pt");
  await page.goto("/privacy");
  const phone = stored(page).filter({ hasText: /^On your phone only:/ });
  await expect(phone).toContainText("The language you chose for the questions.");
  await expect(phone).toContainText("Which test and which second look you have open");
  // Seen in a browser on Sep 29: lib/offline.ts marks a queued check as sent and keeps it.
  await expect(phone).toContainText("A check that waited stays here after it is sent, without its photos.");
  await expect(phone).toContainText("Until you close the tab: the kind of link you came from and your pick on the first page.");
});

// UPDATE_33: nobody took the test before the first lock, so the same study runs a second time,
// from 2026-09-30T04:00:00Z to the second lock, 2026-10-03T04:00:00Z, under
// docs/analysis_plan_v3.md. The page says so in plain words, under the list of what is stored.
test("/privacy says the test has two windows and names the second lock", async ({ page }) => {
  await mockApi(page);
  await page.goto("/privacy");
  const main = page.getByRole("main");
  const windows = main.locator("p").filter({ hasText: /^The test runs in two windows\./ });
  await expect(windows).toHaveCount(1);
  await expect(windows).toContainText("The second closes on Oct 3 at 04:00 UTC, which is Fri Oct 2 at 21:00 PDT.");
  await expect(windows).toContainText("Both windows store the same things, listed above.");
  await expect(windows).toContainText("the anonymous answer table is published with the results, whatever they show");
  await expect(windows).toContainText("docs/analysis_plan_v3.md");
  // The paragraph follows the list of what is stored, so "listed above" is true.
  const order = await main.evaluate((el) => {
    const list = el.querySelector("ul");
    const p = [...el.querySelectorAll("p")].find((x) => x.textContent?.startsWith("The test runs in two windows."));
    return list && p ? Boolean(list.compareDocumentPosition(p) & Node.DOCUMENT_POSITION_FOLLOWING) : null;
  });
  expect(order).toBe(true);
});
