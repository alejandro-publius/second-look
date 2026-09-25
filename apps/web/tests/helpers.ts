import { expect, type Page } from "@playwright/test";
import { WEB_ORIGIN } from "../scripts/web-port.mjs";

// The site under test: 3100 unless WEB_PORT moves it, the same origin as playwright.config.ts.
export const BASE = WEB_ORIGIN;

/** Consent: tick both boxes and start. Returns after the warm-up appears. */
export async function passConsent(page: Page) {
  await expect(page.getByRole("heading", { name: "Before you start" })).toBeVisible();
  await page.getByLabel("I understand and agree to take part.").check();
  await page.getByLabel("I am 18 or older.").check();
  await page.getByRole("button", { name: "I agree, start" }).click();
  await expect(page.getByRole("heading", { name: "Which creek is healthier?" })).toBeVisible();
}

export async function pickWarmup(page: Page) {
  await page.getByRole("button", { name: "This creek, on the left" }).click();
}

/** Walks the whole lesson: rule, second pair, practice for each of four features. */
export async function finishLesson(page: Page) {
  for (let f = 0; f < 4; f++) {
    await page.getByRole("button", { name: "Next photo", exact: true }).click();
    await page.getByRole("button", { name: "Next photo", exact: true }).click();
    await expect(page.getByText("Try one.")).toBeVisible();
    await page.getByRole("button", { name: "Yes", exact: true }).click();
    await expect(page.getByRole("status")).toBeVisible();
    await page.getByRole("button", { name: f === 3 ? "Finish" : "Next photo", exact: true }).click();
  }
}

/** Chooses an answer on the current item and confirms it with Next. */
export async function answerItem(page: Page, choice: "Yes" | "No" | "Can't tell") {
  await page.getByRole("button", { name: choice, exact: true }).click();
  await page.locator("[data-confirm]").click();
}

/** Answers all 16 items with the given pattern, select then Next each time. */
export async function answerAllItems(page: Page, pick: (i: number) => "Yes" | "No" | "Can't tell", withFeedback = false) {
  for (let i = 1; i <= 16; i++) {
    await expect(page.getByText(`Photo ${i} of 16`)).toBeVisible();
    await answerItem(page, pick(i));
    if (withFeedback) {
      await expect(page.getByRole("status")).toBeVisible();
      await page.getByRole("button", { name: i === 16 ? "Finish" : "Next photo", exact: true }).click();
    }
  }
}
