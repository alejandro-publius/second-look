import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { mockApi, watchRequests, assertOnlyOurOrigins } from "./mock-api.mjs";
import { answerAllItems, answerItem, BASE, finishLesson, passConsent, pickWarmup } from "./helpers";

// Part 2, the assisted second look (UPDATE_31). The mock keeps the flags, as the Worker does:
// a01 and a07 point at present, a02 at present (wrongly), a03 at absent (wrongly).
const QUESTION = "The checker noticed something here. Look again?";

async function part1ToScore(page: Page) {
  await page.goto("/t");
  await passConsent(page);
  await pickWarmup(page);
  await finishLesson(page);
  await answerAllItems(page, () => "No");
  await page.getByLabel("No", { exact: true }).check();
  await page.getByRole("button", { name: "See my score" }).click();
  await expect(page.getByRole("heading", { name: "Your score" })).toBeVisible();
}

async function startPart2(page: Page) {
  await page.goto("/t2");
  await expect(page.getByRole("heading", { name: "A second look" })).toBeVisible();
  await page.getByRole("button", { name: "Start", exact: true }).click();
}

const photo = (page: Page, n: number) => expect(page.getByText(`Photo ${n} of 8`)).toBeVisible();

test("part 2 cannot be reached before part 1's score screen", async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto("/t2");
  await expect(page.getByRole("heading", { name: "First, the test" })).toBeVisible();
  await expect(page.getByText("The second look opens after the score screen of the first test.")).toBeVisible();
  // A part 1 sitting that has started but not reached its score: the server refuses, the page says so.
  await page.goto("/t");
  await passConsent(page);
  await pickWarmup(page);
  await expect.poll(() => page.evaluate(() => localStorage.getItem("sl_open_session"))).not.toBeNull();
  await page.goto("/t2");
  await expect(page.getByRole("heading", { name: "First, the test" })).toBeVisible();
  const offer = calls.find((c) => c.path === "/api/t2/offer");
  expect(offer?.body).toMatchObject({ decision: "start" });
  expect(calls.some((c) => c.path === "/api/t2/answer")).toBe(false);
});

test("assisted: the question appears only for a disagreeing flag, Keep and Change store the person's pick", async ({ page }) => {
  const urls = watchRequests(page);
  const calls = await mockApi(page, { part2Arm: "assisted" });
  await part1ToScore(page);
  await startPart2(page);
  // Everything answered No. a01 (flag present) asks: Keep.
  await photo(page, 1);
  await answerItem(page, "No");
  await expect(page.getByText(QUESTION)).toBeVisible();
  await page.getByRole("button", { name: "Keep", exact: true }).click();
  // a02 (flag present, gold absent) asks: Change to Yes.
  await photo(page, 2);
  await answerItem(page, "No");
  await expect(page.getByText(QUESTION)).toBeVisible();
  await page.getByRole("button", { name: "Change", exact: true }).click();
  await answerItem(page, "Yes");
  // a03 (flag absent) agrees with No: no question.
  await photo(page, 3);
  await answerItem(page, "No");
  for (const n of [4, 5, 6]) {
    await photo(page, n);
    await expect(page.getByText(QUESTION)).toHaveCount(0);
    await answerItem(page, "No");
  }
  // a07 (flag present) asks: Change to Yes. a08 has no flag.
  await photo(page, 7);
  await answerItem(page, "No");
  await page.getByRole("button", { name: "Change", exact: true }).click();
  await answerItem(page, "Yes");
  await photo(page, 8);
  await answerItem(page, "No");
  // a04, a06, a07 and a08 right: 4 of 8.
  await expect(page.getByTestId("part2-score")).toHaveText("4 of 8 right");
  const choices = calls.filter((c) => c.path === "/api/t2/choice").map((c) => c.body);
  expect(choices.map((c) => [c.item_id, c.choice, c.changed_to ?? null])).toEqual([
    ["a01", "keep", null],
    ["a02", "change", "yes"],
    ["a07", "change", "yes"],
  ]);
  // The page never learns which way a flag points: no answer from the API carries one.
  expect(calls.filter((c) => c.path === "/api/t2/answer")).toHaveLength(8);
  assertOnlyOurOrigins(urls, BASE);
});

test("unassisted: the same eight photos and no question, whatever the flags", async ({ page }) => {
  const calls = await mockApi(page, { part2Arm: "unassisted" });
  await part1ToScore(page);
  await startPart2(page);
  for (let n = 1; n <= 8; n++) {
    await photo(page, n);
    await answerItem(page, "No");
  }
  await expect(page.getByTestId("part2-score")).toHaveText("4 of 8 right");
  await expect(page.getByText(QUESTION)).toHaveCount(0);
  expect(calls.some((c) => c.path === "/api/t2/choice")).toBe(false);
});

test("resume: a reload while the question shows brings the question back", async ({ page }) => {
  const calls = await mockApi(page, { part2Arm: "assisted" });
  await part1ToScore(page);
  await startPart2(page);
  await photo(page, 1);
  await answerItem(page, "No");
  await expect(page.getByText(QUESTION)).toBeVisible();
  await page.reload();
  await expect(page.getByText(QUESTION)).toBeVisible();
  await page.getByRole("button", { name: "Keep", exact: true }).click();
  await photo(page, 2);
  expect(calls.filter((c) => c.path === "/api/t2/resume").length).toBeGreaterThan(0);
});

test("panel: the same completion code at the end of part 2", async ({ page }) => {
  await mockApi(page, { part2Arm: "unassisted" });
  await page.goto("/t?src=panel");
  await passConsent(page);
  await pickWarmup(page);
  await finishLesson(page);
  await answerAllItems(page, () => "No");
  await page.getByLabel("No", { exact: true }).check();
  await page.getByRole("button", { name: "See my score" }).click();
  await expect(page.getByTestId("panel-code")).toBeVisible();
  await startPart2(page);
  for (let n = 1; n <= 8; n++) {
    await photo(page, n);
    await answerItem(page, "No");
  }
  await expect(page.getByTestId("panel-code")).toContainText("SLCREEK26");
});

test("no flag and no gold reaches the browser's content", () => {
  const text = readFileSync(join(process.cwd(), "generated", "content.json"), "utf8");
  const content = JSON.parse(text);
  expect(content.part2_items).toHaveLength(8);
  expect(text).not.toMatch(/points_to|part2_flags/);
  for (const item of content.part2_items) expect(Object.keys(item).sort()).toEqual(["feature", "id", "photo_id"]);
});
