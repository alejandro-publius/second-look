import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mockApi } from "./mock-api.mjs";

// The creek check and the video walks quote the OneAquaHealth Citizen Science App word for word.
// Those words are not ours and neither of our licences covers them, so /credits says whose they
// are. Every fact the page shows is read from content/app_strings.json, and so is every fact here.
const root = join(__dirname, "..", "..", "..");
const en: Record<string, string> = JSON.parse(readFileSync(join(root, "content", "locales", "en.json"), "utf8"));
const appStrings = JSON.parse(readFileSync(join(root, "content", "app_strings.json"), "utf8"));
const source: { app: string; app_url: string } = appStrings.source;
const languages: string[] = appStrings.languages.filter((l: string) => l in appStrings.strings);

const fill = (s: string, params: Record<string, string | number>) =>
  s.replace(/\{(\w+)\}/g, (whole, name: string) => (name in params ? String(params[name]) : whole));

test("the credits page says the creek check's questions are the official app's words, not ours", async ({ page }) => {
  await mockApi(page);
  await page.goto("/credits");
  const section = page.getByRole("region", { name: en["credits.app_title"] });
  await expect(section.getByRole("heading", { name: en["credits.app_title"], level: 2 })).toBeVisible();

  expect(languages.length).toBeGreaterThan(1);
  const body = fill(en["credits.app_body"], { app: source.app, n: languages.length });
  expect(body).toContain(`the ${source.app}, in ${languages.length} of its languages`);
  await expect(section.getByText(body, { exact: true })).toBeVisible();
  await expect(section.getByText("The words belong to the OneAquaHealth project. Our licences do not cover them.", { exact: true })).toBeVisible();
  await expect(section.getByRole("link", { name: fill(en["credits.app_link"], { app: source.app }), exact: true })).toHaveAttribute(
    "href",
    source.app_url,
  );
  // No string is missing and no token is left unfilled.
  await expect(section).not.toContainText("[missing");
  await expect(section).not.toContainText("{");
});

test("the app's credit sits with the other credits and the page still fits a phone", async ({ page }) => {
  await mockApi(page);
  await page.goto("/credits");
  const headings = await page.getByRole("heading", { level: 2 }).allTextContents();
  expect(headings).toContain(en["credits.app_title"]);
  expect(headings.indexOf(en["credits.inat_title"])).toBeLessThan(headings.indexOf(en["credits.app_title"]));
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
