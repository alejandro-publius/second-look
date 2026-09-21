import { expect, test } from "@playwright/test";
import { mockApi } from "./mock-api.mjs";

test("keyboard only: consent, warm-up and one test item, never landing on the hidden field", async ({ page }) => {
  const calls = await mockApi(page, { lessonFirst: false });
  await page.goto("/t");
  await expect(page.getByRole("heading", { name: "Before you start" })).toBeVisible();

  const focusedNames: string[] = [];
  async function tabTo(predicate: (el: { tag: string; name: string; text: string; type: string }) => boolean, max = 25) {
    for (let i = 0; i < max; i++) {
      await page.keyboard.press("Tab");
      const el = await page.evaluate(() => {
        const a = document.activeElement as HTMLElement | null;
        return { tag: a?.tagName ?? "", name: (a as HTMLInputElement | null)?.name ?? "", text: (a?.textContent ?? "").trim(), type: (a as HTMLInputElement | null)?.type ?? "" };
      });
      focusedNames.push(el.name);
      if (predicate(el)) return el;
    }
    throw new Error("never reached the target with Tab");
  }

  await tabTo((el) => el.name === "agree");
  await page.keyboard.press("Space");
  await tabTo((el) => el.name === "adult");
  await page.keyboard.press("Space");
  await tabTo((el) => el.tag === "BUTTON" && el.text === "I agree, start");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Which creek is healthier?" })).toBeVisible();
  // The heading takes focus, so the next Tab lands on the first photo's button.
  await tabTo((el) => el.tag === "BUTTON" && el.text === "This creek, on the left");
  await page.keyboard.press("Enter");
  await expect(page.getByText("Photo 1 of 16")).toBeVisible();
  await tabTo((el) => el.tag === "BUTTON" && el.text === "Yes");
  await page.keyboard.press("Enter");
  await expect(page.getByText("Photo 2 of 16")).toBeVisible();

  expect(focusedNames).not.toContain("website");
  expect(calls.filter((c) => c.path === "/api/test/response")).toHaveLength(1);
  expect(calls.find((c) => c.path === "/api/test/session")!.body.hidden_field).toBe("");
});

test("focus is visible on the answer buttons", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  const outline = await page.evaluate(() => getComputedStyle(document.activeElement as Element).outlineStyle);
  expect(outline).not.toBe("none");
});
