import { expect, test, type Page } from "@playwright/test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { API_ORIGIN, exampleCity, mockApi } from "./mock-api.mjs";

// UPDATE_30 section 1 item 4 (CRITIC_13 W02). On the live site, the creek link on bare /city
// changed the address and not the page. The page reads its query once, and a client side move to
// /city with a new query kept the pick list whenever the router had not fetched the creek's page
// ahead of the tap. These tests stop that fetch ahead, as a slow phone does, so they take the path
// the live site took. The pick list's links load their page whole, so each tap shows its creek.

const content = JSON.parse(readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"));
const en: Record<string, string> = content.locale;
type Creek = { slug: string; name: string };
type Region = { region: string; name: string; creeks?: Creek[] };
const regions: Region[] = Object.values(content.regions);
const creeks: Creek[] = regions.flatMap((r) => r.creeks ?? []);
const regionFiles = readdirSync(join(__dirname, "..", "..", "..", "content", "regions")).filter((f) => f.endsWith(".yaml"));

/**
 * Every creek answers with its own name, and each answer with its own number of visits (101, 102,
 * and so on), so a page that kept an earlier answer is caught even with one creek. No page is
 * fetched ahead of a tap. Returns the creeks asked for, in order.
 */
async function everyCreekAnswers(page: Page): Promise<string[]> {
  await mockApi(page);
  const asked: string[] = [];
  await page.route(`${API_ORIGIN}/api/city/**`, (route) => {
    const slug = decodeURIComponent(new URL(route.request().url()).pathname.slice("/api/city/".length));
    asked.push(slug);
    const creek = creeks.find((c) => c.slug === slug);
    if (!creek) return route.fulfill({ status: 404, json: { detail: "We have no record for that creek yet." } });
    return route.fulfill({ json: { ...exampleCity, creek_id: slug, creek_slug: slug, creek_name: creek.name, visits: 100 + asked.length } });
  });
  await page.route("**/*", (route) => (route.request().headers()["next-router-prefetch"] ? route.abort() : route.fallback()));
  return asked;
}

async function seesPicker(page: Page) {
  await expect(page).toHaveURL(/\/city$/);
  await expect(page.getByRole("heading", { level: 1, name: en["city.pick_title"] })).toBeVisible();
  await expect(page.getByText(en["city.pick"])).toBeVisible();
}

/** The creek's own page, filled from answer number `answer` of the API. */
async function seesCreek(page: Page, creek: Creek, asked: string[], answer: number) {
  await expect(page).toHaveURL(new RegExp(`/city\\?creek=${encodeURIComponent(creek.slug)}$`));
  await expect(page.getByText(en["city.intro"].replace("{creek}", creek.name))).toBeVisible();
  await expect(page.getByText(`${100 + answer} visits at ${exampleCity.spots} spots`)).toBeVisible();
  await expect(page.getByText(en["city.pick"])).toHaveCount(0);
  expect(asked[answer - 1]).toBe(creek.slug);
}

test("bare /city lists every region pack with its creeks, and each creek link shows that creek", async ({ page }) => {
  expect(regions.length).toBe(regionFiles.length);
  expect(creeks.length).toBeGreaterThan(0);
  const asked = await everyCreekAnswers(page);
  await page.goto("/city");
  await seesPicker(page);
  const main = page.getByRole("main");
  for (const region of regions) {
    const section = main.locator("section").filter({ has: page.getByRole("heading", { level: 2, name: region.name, exact: true }) });
    await expect(section).toHaveCount(1);
    if ((region.creeks ?? []).length === 0) await expect(section.getByText(en["city.pick_none"])).toBeVisible();
    for (const c of region.creeks ?? []) {
      await expect(section.getByRole("link", { name: c.name, exact: true })).toHaveAttribute("href", `/city?creek=${encodeURIComponent(c.slug)}`);
    }
  }
  // Nothing is asked of the API about a creek the link does not name.
  expect(asked).toEqual([]);
  for (const [i, creek] of creeks.entries()) {
    await page.goto("/city");
    await seesPicker(page);
    await main.getByRole("link", { name: creek.name, exact: true }).click();
    await seesCreek(page, creek, asked, i + 1);
  }
});

test("pick a creek, go Back to the pick list, and pick another: each shows its own creek", async ({ page }) => {
  const asked = await everyCreekAnswers(page);
  // Another creek when the regions name two or more; with one, the same creek again, which must
  // show the second answer and not the first.
  const first = creeks[0];
  const second = creeks[1 % creeks.length];
  await page.goto("/city");
  await seesPicker(page);
  await page.getByRole("main").getByRole("link", { name: first.name, exact: true }).click();
  await seesCreek(page, first, asked, 1);
  await page.goBack();
  await seesPicker(page);
  await page.getByRole("main").getByRole("link", { name: second.name, exact: true }).click();
  await seesCreek(page, second, asked, 2);
});
