import { expect, test } from "@playwright/test";
import { assertOnlyOurOrigins, goldFor, mockApi, watchRequests } from "./mock-api.mjs";
import { answerAllItems, BASE } from "./helpers";

test("judge mode gives feedback, stores nothing, and teaches only what was missed", async ({ page }) => {
  const urls = watchRequests(page);
  const calls = await mockApi(page);
  await page.goto("/demo");
  await expect(page.getByRole("heading", { name: "Judge mode" })).toBeVisible();
  await expect(page.getByText("Nothing here is stored.")).toBeVisible();
  await page.getByRole("button", { name: "Start" }).click();
  // Yes on everything: the mock's key has two present per feature, so every feature scores 2 of 4 and is missed.
  await answerAllItems(page, () => "Yes", true);
  await expect(page.getByRole("heading", { name: "What you missed" })).toBeVisible();
  await expect(page.getByText("2 of 4 on Built banks")).toBeVisible();
  await page.getByRole("button", { name: "Show the lessons" }).click();
  await expect(page.getByRole("heading", { name: /Lesson: / })).toBeVisible();
  expect(calls.filter((c) => c.path === "/api/demo/answer")).toHaveLength(16);
  expect(calls.filter((c) => c.path.startsWith("/api/test/"))).toHaveLength(0);
  expect(calls.filter((c) => c.path.startsWith("/api/check/"))).toHaveLength(0);
  expect(assertOnlyOurOrigins(urls, BASE)).toEqual([]);
});

test("a judge who passes every feature gets no lesson", async ({ page }) => {
  await mockApi(page);
  await page.goto("/demo");
  await page.getByRole("button", { name: "Start" }).click();
  // The order is random, so read which photo is on screen and answer by the mock's own key.
  for (let i = 1; i <= 16; i++) {
    await expect(page.getByText(`Photo ${i} of 16`)).toBeVisible();
    const src = await page.locator("img.photo-large").getAttribute("src");
    const itemId = "t" + src!.match(/ph-test-(\d\d)/)![1];
    await page.getByRole("button", { name: goldFor(itemId) === "present" ? "Yes" : "No", exact: true }).click();
    await expect(page.getByRole("status")).toContainText("Right.");
    await page.getByRole("button", { name: i === 16 ? "Finish" : "Next", exact: true }).click();
  }
  await expect(page.getByText("You passed every feature. No lesson needed.")).toBeVisible();
});

test("?script=1 fixes the item order for the screen recording", async ({ page }) => {
  const order = async () => {
    const calls = await mockApi(page);
    await page.goto("/demo?script=1");
    await expect(page.getByText("Scripted order for the screen recording.")).toBeVisible();
    await page.getByRole("button", { name: "Start" }).click();
    for (let i = 1; i <= 3; i++) {
      await page.getByRole("button", { name: "Yes", exact: true }).click();
      await page.getByRole("button", { name: "Next", exact: true }).click();
    }
    await page.unrouteAll({ behavior: "ignoreErrors" });
    return calls.filter((c) => c.path === "/api/demo/answer").map((c) => c.body.item_id);
  };
  const a = await order();
  const b = await order();
  expect(a).toHaveLength(3);
  expect(a).toEqual(b);
});
