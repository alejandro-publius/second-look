import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { mockApi } from "./mock-api.mjs";
import { passConsent, pickWarmup } from "./helpers";

async function noSeriousViolations(page: Page, label: string) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  const summary = serious.map((v) => `${v.id}: ${v.help} (${v.nodes.length} nodes)`).join("\n");
  console.log(`axe ${label}: ${results.violations.length} violations, ${serious.length} serious or critical, ${results.passes.length} checks passed`);
  expect(serious, summary).toEqual([]);
}

test("axe: landing", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await noSeriousViolations(page, "/");
});

test("axe: consent and one test item", async ({ page }) => {
  await mockApi(page, { lessonFirst: false });
  await page.goto("/t");
  await expect(page.getByRole("heading", { name: "Before you start" })).toBeVisible();
  await noSeriousViolations(page, "/t consent");
  await passConsent(page);
  await noSeriousViolations(page, "/t warm-up");
  await pickWarmup(page);
  await expect(page.getByText("Photo 1 of 16")).toBeVisible();
  await noSeriousViolations(page, "/t item");
});

test("axe: the accessibility page", async ({ page }) => {
  await mockApi(page);
  await page.goto("/accessibility");
  await expect(page.getByRole("heading", { level: 1, name: "Accessibility" })).toBeVisible();
  await noSeriousViolations(page, "/accessibility");
});

test("axe: /city has its level-one heading before the record loads", async ({ page }) => {
  await mockApi(page);
  await page.goto("/city");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await noSeriousViolations(page, "/city");
});

test("axe: demo", async ({ page }) => {
  await mockApi(page);
  await page.goto("/demo");
  await noSeriousViolations(page, "/demo");
});

test("axe: check first screen and the location screen", async ({ page }) => {
  await mockApi(page);
  await page.goto("/check");
  await noSeriousViolations(page, "/check");
  await page.getByRole("button", { name: "Start the check" }).click();
  await page.getByRole("button", { name: "Drop a pin instead" }).click();
  await noSeriousViolations(page, "/check location");
});

test("axe: spot record", async ({ page }) => {
  await mockApi(page);
  await page.goto("/spot?id=example");
  await expect(page.getByText("4 of 4 on Built banks, tested Sep 23")).toBeVisible();
  await noSeriousViolations(page, "/spot?id=example");
});

test("axe: two observers", async ({ page }) => {
  await mockApi(page);
  await page.goto("/two");
  await expect(page.getByRole("region", { name: "Volunteer (Second Look)" })).toBeVisible();
  await noSeriousViolations(page, "/two");
});
