import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { assertOnlyOurOrigins, mockApi, watchRequests } from "./mock-api.mjs";

// The iNaturalist context line (UPDATE_29 section 8): on the record page and /city only, below
// what people reported, with its fetch time, and "no recent sightings on record" when the stored
// copy is missing or empty. Nothing shows when the API withholds it (no finished check on the
// creek has answered the invasive plant question yet) or when the route fails. The page never calls iNaturalist itself.

const region = (page: Page) => page.getByRole("region", { name: "iNaturalist, for context" });

test("/spot shows the sightings below the visits, with links, the fetch time and the terms", async ({ page, baseURL }) => {
  const urls = watchRequests(page);
  const calls = await mockApi(page);
  await page.goto("/spot?id=example");
  const line = region(page);
  await expect(line).toBeVisible();
  await expect(line).toContainText("iNaturalist, for context only.");
  await expect(line).toContainText("Research grade only. Not counted in anything on this page.");
  await expect(line).toContainText("within 300 metres of this creek's spots since Sep 24, 2023");
  await expect(line).toContainText("Himalayan blackberry: seen 5 times, last on Dec 11, 2025");
  await expect(line).toContainText("Algerian ivy: seen once, last on Dec 16, 2025");
  await expect(line).toContainText("Fetched from iNaturalist on Sep 24, 2026");
  await expect(line.getByRole("link", { name: "see them Himalayan blackberry on iNaturalist" })).toHaveAttribute(
    "href",
    "https://www.inaturalist.org/observations?id=283650055,294575631,299064622,351067371,351067372",
  );
  await expect(line.getByRole("link", { name: "iNaturalist terms of use" })).toHaveAttribute("href", "https://www.inaturalist.org/pages/terms");
  await expect(line).not.toContainText("no recent sightings on record");
  // Below the answers, never above them.
  const visitsTop = (await page.getByRole("heading", { name: "Visits" }).boundingBox())!.y;
  expect((await line.boundingBox())!.y).toBeGreaterThan(visitsTop);
  // The spot sits on Strawberry Creek, so the line is asked for by the creek's slug.
  expect(calls.some((c) => c.path === "/api/inaturalist/strawberry-creek")).toBe(true);
  expect(assertOnlyOurOrigins(urls, baseURL!)).toEqual([]);
});

for (const kind of ["none", "empty"] as const) {
  test(`/spot says "no recent sightings on record" when the stored copy is ${kind === "none" ? "missing" : "empty"}`, async ({ page }) => {
    await mockApi(page, { inat: kind });
    await page.goto("/spot?id=example");
    const line = region(page);
    await expect(line).toBeVisible();
    await expect(line).toHaveText(/no recent sightings on record/);
    await expect(line.getByRole("link")).toHaveCount(0);
    if (kind === "empty") await expect(line).toContainText("Fetched from iNaturalist on Sep 24, 2026");
    else await expect(line).not.toContainText("Fetched");
  });
}

for (const kind of ["hidden", "down"] as const) {
  test(`/spot shows nothing from iNaturalist when the line is ${kind === "hidden" ? "withheld" : "unreachable"}`, async ({ page }) => {
    await mockApi(page, { inat: kind });
    await page.goto("/spot?id=example");
    await expect(page.getByRole("heading", { name: "Visits" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "What you can do" })).toBeVisible();
    await expect(region(page)).toHaveCount(0);
    await expect(page.getByText("iNaturalist")).toHaveCount(0);
  });
}

test("/city shows the line after what people reported, and no number moves", async ({ page, baseURL }) => {
  const urls = watchRequests(page);
  const calls = await mockApi(page);
  await page.goto("/city?creek=example");
  const line = region(page);
  await expect(line).toBeVisible();
  await expect(line).toContainText("Himalayan blackberry: seen 5 times, last on Dec 11, 2025");
  await expect(page.getByText("5 visits at 2 spots")).toBeVisible();
  const reportedTop = (await page.getByRole("heading", { name: "What people reported" }).boundingBox())!.y;
  expect((await line.boundingBox())!.y).toBeGreaterThan(reportedTop);
  expect(calls.some((c) => c.path === "/api/inaturalist/strawberry-creek")).toBe(true);
  expect(assertOnlyOurOrigins(urls, baseURL!)).toEqual([]);
});

test("/city degrades to the same words, and shows nothing when the line is withheld", async ({ page }) => {
  await mockApi(page, { inat: "none" });
  await page.goto("/city?creek=example");
  await expect(region(page)).toHaveText(/no recent sightings on record/);
  await page.unrouteAll({ behavior: "ignoreErrors" });
  await mockApi(page, { inat: "hidden" });
  await page.goto("/city?creek=example");
  await expect(page.getByText("5 visits at 2 spots")).toBeVisible();
  await expect(region(page)).toHaveCount(0);
});

test("the guided check never asks for the line or shows it", async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto("/check");
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
  await expect(region(page)).toHaveCount(0);
  await expect(page.getByText("iNaturalist")).toHaveCount(0);
  expect(calls.some((c) => c.path.startsWith("/api/inaturalist"))).toBe(false);
});

test("the credits page names iNaturalist, its terms and what it said about each plant photo", async ({ page }) => {
  await mockApi(page);
  await page.goto("/credits");
  await expect(page.getByRole("heading", { name: "iNaturalist" })).toBeVisible();
  await expect(page.getByText("9 of the plant photos above come from iNaturalist")).toBeVisible();
  await expect(page.getByText("We asked iNaturalist about each of them on Sep 24, 2026.")).toBeVisible();
  await expect(page.getByText("Research grade, seen in California.")).toHaveCount(9);
  await expect(page.getByRole("link", { name: "iNaturalist terms of use" })).toHaveAttribute("href", "https://www.inaturalist.org/pages/terms");
  await expect(page.getByText("by Pinnacles National Park")).toBeVisible();
});

// UPDATE_30 section 3: the Bay Area list was approved on 2026-09-25 and the job ran that day. The
// copy it fetched for Strawberry Creek's spot is in tests/fixtures, word for word, and the record
// page and /city show it. On the live site the API withholds it until a finished check there has
// answered the invasive plant question, as the lines above test.
const realCopy = JSON.parse(readFileSync(join(__dirname, "fixtures", "inaturalist-strawberry-creek.json"), "utf8"));
const firstPlant = realCopy.species[0];
const firstLine = `${firstPlant.name}: seen ${firstPlant.count} times`;

test("the copy the job fetched on Sep 25 renders on the Strawberry Creek record and on /city", async ({ page }) => {
  expect(realCopy.species.length).toBeGreaterThan(0);
  await mockApi(page, { inatBody: realCopy });
  await page.goto("/spot?id=example");
  await expect(region(page)).toContainText(firstLine);
  await page.goto("/city?creek=example");
  await expect(region(page)).toContainText(firstLine);
});
