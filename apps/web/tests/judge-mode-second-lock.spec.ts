import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mockApi } from "./mock-api.mjs";

// UPDATE_33: judge mode says if each answer is right on the photos the study uses. It opened at
// the first lock, 2026-09-28T01:00:00Z. A second wave of the study now runs until the second
// lock, 2026-10-03T04:00:00Z, so both judge mode pages are shut again until then. The pages
// decide by the browser's own clock, which these tests hold still at one moment each.
const EN: Record<string, string> = JSON.parse(readFileSync(join(__dirname, "..", "..", "..", "content", "locales", "en.json"), "utf8"));
const WHEN = "Oct 3 at 04:00 UTC, which is Friday Oct 2 at 21:00 PDT";

const PAGES = [
  { path: "/demo", open: EN["demo.title"], body: EN["demo.shut_body"], api: "/api/demo/answer" },
  { path: "/t2/demo", open: EN["part2.demo_title"], body: EN["part2.demo_shut_body"], api: "/api/t2/demo" },
];

// Shut: before the first lock, at the first lock where judge mode once opened, on the day this
// was written, when the second wave opens, and one second before the second lock.
const SHUT_AT = ["2026-09-24T12:00:00Z", "2026-09-28T01:00:00Z", "2026-09-29T21:00:00Z", "2026-09-30T04:00:00Z", "2026-10-03T03:59:59Z"];
const OPEN_AT = ["2026-10-03T04:00:00Z", "2026-10-03T04:10:00Z", "2026-10-05T04:00:00Z"];

for (const { path, open, body, api } of PAGES) {
  test(`${path} is shut until the second lock, and says when and why`, async ({ page }) => {
    const calls = await mockApi(page);
    for (const moment of SHUT_AT) {
      await page.clock.setFixedTime(new Date(moment));
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1, name: "Judge mode opens on Oct 3", exact: true }), moment).toBeVisible();
      await expect(page.getByText(body, { exact: true }), moment).toBeVisible();
      await expect(page.getByText(EN["demo.shut_meanwhile"], { exact: true }), moment).toBeVisible();
      // Shut means shut: no photo is fetched and nothing can be started.
      await expect(page.locator("img.photo, img.photo-large"), moment).toHaveCount(0);
      await expect(page.getByRole("button"), moment).toHaveCount(0);
      await expect(page.getByRole("link", { name: EN["judges.title"], exact: true }), moment).toBeVisible();
    }
    expect(body).toContain(WHEN);
    expect(body).toContain("second wave of the study");
    expect(calls.filter((c) => c.path === api)).toHaveLength(0);
    expect(calls.filter((c) => c.path.startsWith("/api/test/") || c.path.startsWith("/api/t2/"))).toHaveLength(0);
  });

  test(`${path} is open from the second lock on`, async ({ page }) => {
    await mockApi(page);
    for (const moment of OPEN_AT) {
      await page.clock.setFixedTime(new Date(moment));
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1, name: open, exact: true }), moment).toBeVisible();
      await expect(page.getByText(body, { exact: true }), moment).toHaveCount(0);
      await expect(page.getByRole("button").first(), moment).toBeVisible();
    }
  });
}

test("the shut page no longer names the first lock", async () => {
  for (const key of ["demo.shut_title", "demo.shut_body", "part2.demo_shut_body"]) {
    expect(EN[key], key).not.toMatch(/Sep 2[78]|01:00 UTC|18:00 PDT/);
  }
});
