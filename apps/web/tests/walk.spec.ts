import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { assertOnlyOurOrigins, mockApi, watchRequests } from "./mock-api.mjs";
import { BASE } from "./helpers";

// Update 14 3.7: a walk is a guided check made while watching a clip. The record is built on the
// phone, tagged as a demo on every resource, and nothing is sent to our store.
const content = JSON.parse(readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"));
const walks: {
  id: string;
  country: string;
  creek_name: string;
  title: string;
  author: string;
  question: unknown;
  checker_run: string;
  checker_dropped: number;
}[] = content.walks ?? [];

// Update 14 asks for four walks from four countries. The rule found three (docs/DECISIONS.md,
// 2026-09-22), so the test holds the rule itself: at least one, each from a different country.
test("every walk comes from a different country and is linked from /judges", async ({ page }) => {
  expect(walks.length).toBeGreaterThan(0);
  expect(new Set(walks.map((w) => w.country)).size).toBe(walks.length);
  await page.goto(`${BASE}/judges`);
  await page.getByRole("link", { name: "Check a creek from your desk" }).click();
  for (const w of walks) await expect(page.getByRole("link", { name: w.creek_name })).toBeVisible();
  // "A creek in the United Kingdom", never "A creek in United Kingdom" (REVIEW_03 R41).
  const names = await page.getByRole("main").getByRole("link").allInnerTexts();
  expect(names.filter((n) => /\bin United\b/.test(n))).toEqual([]);
  if (walks.some((w) => w.country === "United Kingdom")) expect(names).toContain("A creek in the United Kingdom");
});

test("a walk shows its credit, builds a demo record on the phone, and sends nothing", async ({ page }) => {
  const calls = await mockApi(page, {});
  const urls = watchRequests(page);
  const w = walks[0];
  await page.goto(`${BASE}/walk/${w.id}`);
  await expect(page.locator("video.walk-clip")).toHaveCount(1);
  await expect(page.getByText(w.author, { exact: false }).first()).toBeVisible();
  await expect(page.getByText("never stored, never counted")).toBeVisible();
  await page.getByRole("button", { name: "Start the check" }).click();
  await page.getByRole("button", { name: "U shape" }).click(); // channel form
  // The count's total stays the same when a follow-up such as "Which ones?" appears (REVIEW_03 R42).
  const counts: string[] = [];
  let sawFollowUp = false;
  for (let i = 0; i < 40; i++) {
    if (await page.getByRole("heading", { name: "Your record from the clip" }).isVisible()) break;
    const count = page.getByText(/^Question \d+ of \d+$/);
    if (await count.isVisible()) counts.push(await count.innerText());
    if (await page.getByRole("heading", { name: "Which ones?" }).isVisible()) sawFollowUp = true;
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
  expect(sawFollowUp).toBe(true);
  expect(new Set(counts.map((c) => c.replace(/^Question \d+ /, ""))).size).toBe(1);
  await expect(page.getByTestId("walk-structure")).toHaveText("Every link inside the record checks out");
  // CRITIC_03 E04: a walk whose build record stopped nothing says no model saw a feature, and
  // never blames the pass rule for "0 of its guesses".
  if (!w.question && w.checker_run === "real" && w.checker_dropped === 0) {
    await expect(page.getByText(content.locale["walk.checker_nothing_seen"])).toBeVisible();
    await expect(page.getByText(/of its guesses on this clip/)).toHaveCount(0);
  }
  await page.getByRole("button", { name: "View as FHIR" }).click();
  // The record was made on this phone: the badge speaks of walk records made the same way, which
  // the validator checked in CI, never of this one, and there is no address to copy (REVIEW_03 R31).
  await expect(page.getByTestId("fhir-badge")).toHaveText(
    "Walk records made the same way passed the HL7 validator on Sep 20, 2026. This one was made on your phone and was not checked.",
  );
  await expect(page.getByText("passed the HL7 validator against guide commit")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Copy the curl line" })).toHaveCount(0);
  await expect(page.getByText("This record was made on your phone and has no web address.")).toBeVisible();
  const json = await page.locator("pre.code").last().innerText();
  const bundle = JSON.parse(json);
  expect(bundle.meta.tag.some((t: { code: string }) => t.code === "demo-walk")).toBe(true);
  for (const e of bundle.entry) expect(e.resource.meta.tag.some((t: { code: string }) => t.code === "demo-walk")).toBe(true);
  // No check, upload or quick call: the record never leaves the phone.
  expect(calls.filter((c: { path: string }) => /\/api\/(check|upload|quick)/.test(c.path))).toEqual([]);
  expect(assertOnlyOurOrigins(urls, BASE)).toEqual([]);

  await page.getByRole("link", { name: "See this creek as a city would" }).click();
  await expect(page.getByRole("heading", { name: /Demo creek/ })).toBeVisible();
  await expect(page.getByText("Checks from this phone: 1")).toBeVisible();
  // CRITIC_04 F04: the walk said yes to barriers, and the finding and the reason carry the short
  // label, never the form's whole question.
  const barriers = formItems.find((it) => it.id === "barriers")!.text;
  // The finding's row: its label, then the count, which textContent joins across the <br>.
  await expect(page.getByRole("main")).toContainText(`${en["city.finding_barriers"]}${en["city.walk_seen"].replace("{n}", "1")}`);
  await expect(page.getByRole("main")).toContainText(`${en["city.finding_barriers"]}. OneAquaHealth Policy Brief`);
  await expect(page.getByRole("main")).not.toContainText(barriers);
});

// CRITIC_04 F01: the one record a judge can make listed no answer and no score. The record screen
// now lists every answer the walk made, the way /spot lists a stored visit's, and where /spot shows
// the observer's score it says "No score in a demo record" (walk.not_tested), then points to the
// example on /two, where a volunteer's score travels with the answer.
const en: Record<string, string> = content.locale;
const formItems: { id: string; text: string; feature: string | null }[] = content.form.items;

test("the walk's record lists every answer the walk made, with No score in a demo record where /spot shows the score", async ({ page }) => {
  await mockApi(page, {});
  const w = walks[0];
  await page.goto(`${BASE}/walk/${w.id}`);
  await page.getByRole("button", { name: "Start the check" }).click();
  // Each question answered, as the screen showed it: the question and the words of the answer.
  const made: { question: string; answer: string }[] = [];
  for (let i = 0; i < 40; i++) {
    if (await page.getByRole("heading", { name: "Your record from the clip" }).isVisible()) break;
    if (await page.getByRole("button", { name: "Finish" }).isVisible()) {
      await page.getByRole("button", { name: "Finish" }).click();
      continue;
    }
    const heading = page.locator("h1#question");
    const question = (await heading.innerText()).trim();
    const group = page.getByRole("main").getByRole("group").first();
    const skip = page.getByRole("button", { name: "Skip" });
    const none = page.getByRole("button", { name: "None of these" });
    const choice = group.getByRole("button").first();
    if (await skip.first().isVisible()) await skip.first().click();
    else if (await none.isVisible()) await none.click();
    else if (await choice.isVisible()) {
      made.push({ question, answer: (await choice.innerText()).trim() });
      await choice.click();
    } else {
      // The feelings sliders, left where they start: a slider nobody moved is not an answer, so
      // the question makes no line (CRITIC_06 H03).
      await page.getByRole("button", { name: "Next", exact: true }).click();
    }
    // On to the next screen before the next look: the question on screen has changed or gone.
    await page.waitForFunction((q) => document.querySelector("h1#question")?.textContent?.trim() !== q, question);
  }
  await expect(page.getByRole("heading", { name: "Your record from the clip" })).toBeVisible();

  // Both kinds of question were answered, so both kinds of line are held.
  const byText = (q: string) => formItems.find((it) => it.text === q);
  expect(made.every((m) => byText(m.question))).toBe(true);
  expect(made.some((m) => byText(m.question)!.feature)).toBe(true);
  expect(made.some((m) => !byText(m.question)!.feature)).toBe(true);

  const answers = page.getByTestId("walk-answers");
  await expect(page.getByRole("heading", { name: en["walk.answers_title"], level: 2 })).toBeVisible();
  const rows = answers.locator(".answer-line");
  await expect(rows).toHaveCount(made.length);
  for (const [i, m] of made.entries()) {
    const row = rows.nth(i);
    await expect(row.locator(".muted").first()).toHaveText(m.question);
    await expect(row.locator("strong")).toHaveText(m.answer);
    await expect(row.locator(".observer")).toHaveText(byText(m.question)!.feature ? en["walk.not_tested"] : en["spot.no_feature"]);
  }
  // No score is made up: nothing reads like a score line or a missing score.
  await expect(answers).not.toContainText(/ of \d+ on |No test score/);

  const note = page.getByTestId("walk-score-note");
  await expect(note).toHaveText(en["walk.score_note"].replace("{link}", en["walk.score_link"]));
  await expect(note.getByRole("link", { name: en["walk.score_link"], exact: true })).toHaveAttribute("href", "/two");

  // WCAG 2.2 SC 1.4.10: the record with its answers still fits the phone width.
  const viewport = page.viewportSize()!.width;
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport);
});

/** Goes through a walk's questions the quick way, as the gallery does, until its record shows:
 * Skip, None of these, the first choice, or Next. The feelings screen is left to onFeelings. */
async function answerWalk(page: Page, onFeelings: () => Promise<void>) {
  const feelings = formItems.find((it) => it.id === "feelings")!.text;
  for (let i = 0; i < 40; i++) {
    if (await page.getByRole("heading", { name: en["walk.done_title"] }).isVisible()) return;
    if (await page.getByRole("button", { name: "Finish" }).isVisible()) {
      await page.getByRole("button", { name: "Finish" }).click();
      continue;
    }
    const question = (await page.locator("h1#question").innerText()).trim();
    const skip = page.getByRole("button", { name: "Skip" });
    const none = page.getByRole("button", { name: "None of these" });
    const choice = page.getByRole("main").getByRole("group").first().getByRole("button");
    if (question === feelings) await onFeelings();
    else if (await skip.first().isVisible()) await skip.first().click();
    else if (await none.isVisible()) await none.click();
    else if (await choice.first().isVisible()) await choice.first().click();
    else await page.getByRole("button", { name: "Next", exact: true }).click();
    await page.waitForFunction((q) => document.querySelector("h1#question")?.textContent?.trim() !== q, question);
  }
  await expect(page.getByRole("heading", { name: en["walk.done_title"] })).toBeVisible();
}

// CRITIC_06 H03: every feelings slider starts at 0, and one nobody moved was kept as 0, so a person
// who went on past the screen was recorded as feeling none of the four. A slider is an answer only
// once it is moved or marked Not applicable; the rest stay out of the answers and the record.
test("a feelings slider nobody moved stays out of the walk's record", async ({ page }) => {
  await mockApi(page, {});
  const feelings = formItems.find((it) => it.id === "feelings")!.text;
  for (const moved of [false, true]) {
    await page.goto(`${BASE}/walk/${walks[0].id}`);
    await page.getByRole("button", { name: "Start the check" }).click();
    await answerWalk(page, async () => {
      const shown = page.locator("output[for^='slider-']");
      // No slider shows a number before it is moved.
      await expect(shown).toHaveText(["", "", "", ""]);
      if (moved) {
        await page.getByLabel("Joy").fill("3");
        await page.locator(".card", { hasText: "Fear" }).getByLabel("Not applicable").check();
        // Ticked and then unticked again is not an answer either.
        await page.locator(".card", { hasText: "Serenity" }).getByLabel("Not applicable").check();
        await page.locator(".card", { hasText: "Serenity" }).getByLabel("Not applicable").uncheck();
        await expect(shown).toHaveText(["3", "", "", ""]);
      }
      await page.getByRole("button", { name: "Next", exact: true }).click();
    });
    const row = page.getByTestId("walk-answers").locator(".answer-line").filter({ hasText: feelings });
    if (moved) await expect(row.locator("strong")).toHaveText("Joy: 3, Fear: Not applicable");
    else await expect(row).toHaveCount(0);
  }
});
