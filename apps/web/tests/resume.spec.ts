import { expect, test } from "@playwright/test";
import { mockApi } from "./mock-api.mjs";
import { answerAllItems, answerItem, passConsent, pickWarmup } from "./helpers";

/**
 * Update 07 section 2.1. A reload in the middle of a sitting must resume, never restart. With
 * real people a restart loses the session twice over: the first is incomplete and the second is
 * thrown out as a repeat from the same browser.
 */

test("a reload at item 7 comes back at item 7, same order, one session row", async ({ page }) => {
  const calls = await mockApi(page, { lessonFirst: false });
  await page.goto("/t");
  await passConsent(page);
  await pickWarmup(page);

  await expect(page.getByText("Photo 1 of 16")).toBeVisible();
  for (let i = 1; i <= 6; i++) {
    await expect(page.getByText(`Photo ${i} of 16`)).toBeVisible();
    await answerItem(page, "Yes");
  }
  await expect(page.getByText("Photo 7 of 16")).toBeVisible();
  const before = calls.filter((c) => c.path === "/api/test/response").map((c) => c.body.item_id);

  await page.reload();

  await expect(page.getByText("Photo 7 of 16")).toBeVisible();
  // The same sitting: one session row, and the order did not change under the person.
  expect(calls.filter((c) => c.path === "/api/test/session")).toHaveLength(1);
  const resumed = calls.find((c) => c.path === "/api/test/resume");
  expect(resumed).toBeTruthy();
  // Finishing from here sends the nine that are left, and no id is sent twice with a new answer.
  for (let i = 7; i <= 16; i++) {
    await expect(page.getByText(`Photo ${i} of 16`)).toBeVisible();
    await answerItem(page, "Yes");
  }
  const all = calls.filter((c) => c.path === "/api/test/response").map((c) => c.body.item_id);
  expect(new Set(all).size).toBe(16);
  expect(all.slice(0, 6)).toEqual(before);
  await expect(page.getByRole("heading", { name: "Almost done" })).toBeVisible();
});

test("a reload during the lesson stays in the trained arm", async ({ page }) => {
  const calls = await mockApi(page, { lessonFirst: true });
  await page.goto("/t");
  await passConsent(page);
  await pickWarmup(page);
  await expect(page.locator(".gauge-count", { hasText: "Built banks" })).toBeVisible();
  await page.getByRole("button", { name: "Next photo", exact: true }).click();

  await page.reload();

  // Still the lesson, still one session, and the arm did not flip to untrained.
  await expect(page.locator(".gauge-count").first()).toBeVisible();
  expect(calls.filter((c) => c.path === "/api/test/session")).toHaveLength(1);
  const resumed = calls.filter((c) => c.path === "/api/test/resume").pop();
  expect(resumed).toBeTruthy();
  await expect(page.getByText("Photo 1 of 16")).toHaveCount(0);
});

test("a finished sitting shows its end screen again and creates nothing new", async ({ page }) => {
  const calls = await mockApi(page, { lessonFirst: false });
  await page.goto("/t");
  await passConsent(page);
  await pickWarmup(page);
  await answerAllItems(page, () => "Yes");
  await page.getByRole("button", { name: "See my score" }).click();
  await expect(page.getByRole("heading", { name: "Your score" })).toBeVisible();

  await page.reload();

  await expect(page.getByRole("heading", { name: "Your score" })).toBeVisible();
  await expect(page.getByText("8 of 16 right")).toBeVisible();
  expect(calls.filter((c) => c.path === "/api/test/session")).toHaveLength(1);
  expect(calls.filter((c) => c.path === "/api/test/complete").length).toBeGreaterThan(0);
});

/**
 * Update 07 sections 1.2 and 2.4. The network goes away for ten seconds in the middle of the
 * test. Every answer must still reach the server before the end screen appears.
 */
for (const lessonFirst of [false, true]) {
  const arm = lessonFirst ? "trained" : "untrained";
  test(`${arm} arm: the network drops for ten seconds and every answer still arrives`, async ({ page }) => {
    const offline = { value: false };
    const calls = await mockApi(page, { lessonFirst, offline });
    await page.goto("/t");
    await passConsent(page);
    await pickWarmup(page);
    if (lessonFirst) {
      for (let f = 0; f < 4; f++) {
        await page.getByRole("button", { name: "Next photo", exact: true }).click();
        await page.getByRole("button", { name: "Next photo", exact: true }).click();
        await page.getByRole("button", { name: "Yes", exact: true }).click();
        await page.getByRole("button", { name: f === 3 ? "Finish" : "Next photo", exact: true }).click();
      }
    }

    for (let i = 1; i <= 5; i++) {
      await expect(page.getByText(`Photo ${i} of 16`)).toBeVisible();
      await answerItem(page, "Yes");
    }

    // Ten seconds with no network, answered right through it.
    offline.value = true;
    const wentDark = Date.now();
    for (let i = 6; i <= 10; i++) {
      await expect(page.getByText(`Photo ${i} of 16`)).toBeVisible();
      await answerItem(page, "Yes");
    }
    await page.waitForTimeout(Math.max(0, 10_000 - (Date.now() - wentDark)));
    offline.value = false;

    for (let i = 11; i <= 16; i++) {
      await expect(page.getByText(`Photo ${i} of 16`)).toBeVisible();
      await answerItem(page, "Yes");
    }
    await expect(page.getByRole("heading", { name: "Almost done" })).toBeVisible();
    await page.getByRole("button", { name: "See my score" }).click();

    // The end screen only appears once the server holds all sixteen.
    await expect(page.getByRole("heading", { name: "Your score" })).toBeVisible();
    await expect(page.getByText("8 of 16 right")).toBeVisible();
    const stored = new Set(calls.filter((c) => c.path === "/api/test/response").map((c) => c.body.item_id));
    expect(stored.size).toBe(16);
    const asked = calls.filter((c) => c.path === "/api/test/complete" && c.body.need_resend);
    expect(asked.length).toBe(0);
  });
}
