import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { answerWalkPlainly } from "../scripts/gallery-walk.mjs";
import { mockApi } from "./mock-api.mjs";
import { BASE } from "./helpers";

// CRITIC_10 S01: the browser's Back from a walk's city view reopened the walk on its watch screen,
// and the record, its answers and View as FHIR were gone, though the answers were still saved. A
// walk this browser has finished now opens on its record, rebuilt from the saved answers (kept in
// IndexedDB since UPDATE_30), with Start again; and the city view links back to the record.
const content = JSON.parse(readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"));
const en: Record<string, string> = content.locale;
const walk: { id: string } = content.walks[0];

/** Finishes the walk the way the gallery does, answering Artificial for the bank, and returns the
 * record's answer lines and its FHIR as View as FHIR shows them. */
async function finishWalk(page: Page) {
  await page.goto(`${BASE}/walk/${walk.id}`);
  await page.getByRole("button", { name: en["walk.start"] }).click();
  await answerWalkPlainly(page, content, { bank: "present" });
  return readRecord(page);
}

async function readRecord(page: Page) {
  await expect(page.getByRole("heading", { name: en["walk.done_title"], level: 1 })).toBeVisible();
  const rows = await page.getByTestId("walk-answers").locator(".answer-line").allInnerTexts();
  await page.getByRole("button", { name: en["spot.view_fhir"] }).click();
  const json = await page.locator("pre.code").last().innerText();
  return { rows, bundle: JSON.parse(json) };
}

test("Back from a walk's city view opens the walk on its record, with View as FHIR, and Start again clears it", async ({ page }) => {
  await mockApi(page, {});
  const made = await finishWalk(page);
  expect(made.rows.length).toBeGreaterThan(0);
  await page.getByRole("link", { name: en["walk.city_link"] }).click();
  await expect(page.getByText(en["city.walk_visits"].replace("{n}", "1"))).toBeVisible();

  await page.goBack();
  await expect(page).toHaveURL(`${BASE}/walk/${walk.id}`);
  const back = await readRecord(page);
  expect(back.rows).toEqual(made.rows);
  // The same record, rebuilt from the saved answers: same answers, same time, same ids.
  expect(back.bundle).toEqual(made.bundle);
  expect(back.bundle.meta.tag.some((t: { code: string }) => t.code === "demo-walk")).toBe(true);
  await expect(page.getByTestId("walk-structure")).toHaveText(en["walk.structure_ok"]);

  // Start again clears the record from this tab and goes back to the watch screen.
  await page.getByRole("button", { name: en["walk.start_again"], exact: true }).click();
  await expect(page.getByRole("button", { name: en["walk.start"] })).toBeVisible();
  await expect(page.getByRole("heading", { name: en["walk.done_title"] })).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("button", { name: en["walk.start"] })).toBeVisible();
  await expect(page.getByRole("heading", { name: en["walk.done_title"] })).toHaveCount(0);
  await page.goto(`${BASE}/city?walk=${walk.id}`);
  await expect(page.getByText(en["city.walk_empty"])).toBeVisible();
});

test("the walk's city view links back to the record, and has no such link before a walk", async ({ page }) => {
  await mockApi(page, {});
  await page.goto(`${BASE}/city?walk=${walk.id}`);
  await expect(page.getByText(en["city.walk_empty"])).toBeVisible();
  await expect(page.getByRole("link", { name: en["city.walk_back"] })).toHaveCount(0);

  const made = await finishWalk(page);
  await page.getByRole("link", { name: en["walk.city_link"] }).click();
  const link = page.getByRole("main").getByRole("link", { name: en["city.walk_back"], exact: true });
  await expect(link).toHaveAttribute("href", `/walk/${walk.id}`);
  // The way to the judges' page stays, after the link back to the record.
  const judges = page.getByRole("main").getByRole("link", { name: en["city.walk_more"], exact: true });
  await expect(judges).toHaveAttribute("href", "/judges");
  await link.click();
  await expect(page).toHaveURL(`${BASE}/walk/${walk.id}`);
  const back = await readRecord(page);
  expect(back.rows).toEqual(made.rows);
  expect(back.bundle).toEqual(made.bundle);
});
