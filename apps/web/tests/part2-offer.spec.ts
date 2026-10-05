import { expect, test, type Page } from "@playwright/test";
import { mockApi } from "./mock-api.mjs";
import { answerAllItems, finishLesson, passConsent, pickWarmup } from "./helpers";

// The one change to part 1 (UPDATE_31, docs/deviations.md): the offer line on the score screen.
const OFFER = "Eight more photos, two minutes, and this time a checker may ask you to look again.";

async function toScore(page: Page) {
  await page.goto("/t");
  await passConsent(page);
  await pickWarmup(page);
  await finishLesson(page);
  await answerAllItems(page, () => "No");
  await page.getByLabel("No", { exact: true }).check();
  await page.getByRole("button", { name: "See my score" }).click();
  await expect(page.getByRole("heading", { name: "Your score" })).toBeVisible();
}

test("the score screen explains stored part 2 data, and Start opens it", async ({ page }) => {
  await mockApi(page, { part2Arm: "assisted" });
  await toScore(page);
  await expect(page.getByTestId("part2-offer")).toContainText(OFFER);
  const offer = page.getByTestId("part2-offer");
  await expect(offer).toContainText("We store your answers");
  await expect(offer).toContainText("whether the checker asked you to look again");
  await expect(offer).toContainText("what you chose");
  await expect(offer).toContainText("the time each step took");
  await expect(offer).toContainText("the same random session id");
  await expect(offer).toContainText("We store no name, email");
  await page.getByRole("button", { name: "Start the second look" }).click();
  await expect(page).toHaveURL(/\/t2$/);
  await expect(page.getByRole("heading", { name: "A second look" })).toBeVisible();
});

test("No thanks records the decline and ends", async ({ page }) => {
  const calls = await mockApi(page);
  await toScore(page);
  await page.getByRole("button", { name: "No thanks" }).last().click();
  await expect(page.getByRole("heading", { name: "Thank you" })).toBeVisible();
  expect(calls.find((c) => c.path === "/api/t2/offer")?.body).toMatchObject({ decision: "decline" });
});
