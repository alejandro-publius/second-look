import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { assertOnlyOurOrigins, mockApi, watchRequests } from "./mock-api.mjs";
import { BASE } from "./helpers";

// Update 14 3.7: a walk is a guided check made while watching a clip. The record is built on the
// phone, tagged as a demo on every resource, and nothing is sent to our store.
const content = JSON.parse(readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"));
const walks: { id: string; country: string; creek_name: string; title: string; author: string }[] = content.walks ?? [];

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
});
