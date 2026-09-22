import { expect, test } from "@playwright/test";
import { assertOnlyOurOrigins, mockApi, watchRequests } from "./mock-api.mjs";
import { BASE } from "./helpers";

/** Drops a pin (the denied-location path) and names the spot. */
async function placePin(page: import("@playwright/test").Page) {
  await page.getByRole("button", { name: "Start the check" }).click();
  await expect(page.getByRole("heading", { name: "Where are you?" })).toBeVisible();
  await page.getByRole("button", { name: "Drop a pin instead" }).click();
  await expect(page.getByText("No map tiles here")).toBeVisible();
  await page.getByLabel("Latitude").fill("37.8719");
  await page.getByLabel("Longitude").fill("-122.2585");
  await page.getByLabel("Name for this spot").fill("Footbridge");
  await page.getByRole("button", { name: "Next" }).click();
}

/** Answers every question in the form's order. Overall rating Good so the rating check fires. */
async function answerForm(page: import("@playwright/test").Page) {
  await expect(page.getByRole("heading", { name: "Channel form" })).toBeVisible();
  await page.getByRole("button", { name: "U shape" }).click();
  await page.getByRole("button", { name: "Artificial (concrete or stones with concrete)" }).click(); // bottom
  await page.getByRole("button", { name: "Artificial (concrete or stones with concrete)" }).click(); // bank
  await page.getByLabel("Riffles, rapids, falls").check(); // habitats
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "None of these" }).click(); // natural debris
  await page.getByRole("button", { name: "Slow", exact: true }).click(); // water flow
  await page.getByRole("button", { name: "Clear or transparent" }).click(); // water aspect
  await page.getByRole("button", { name: "No", exact: true }).click(); // withdrawal
  await page.getByRole("button", { name: "No", exact: true }).click(); // barriers
  await page.getByRole("button", { name: "Yes", exact: true }).click(); // draining pipes
  await page.getByRole("button", { name: "No", exact: true }).click(); // sewage
  await page.getByRole("button", { name: "No", exact: true }).click(); // construction
  await page.getByLabel(/Number/).fill("0.3"); // water height
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Yes", exact: true }).click(); // impervious left
  await page.getByRole("button", { name: "No", exact: true }).click(); // impervious right
  await page.getByRole("button", { name: "Yes", exact: true }).click(); // vegetation left
  await page.getByRole("button", { name: "Yes", exact: true }).click(); // vegetation right
  await page.getByRole("button", { name: "Trees" }).click(); // type left
  await page.getByRole("button", { name: "Shrubs" }).click(); // type right
  await page.getByRole("button", { name: "Yes", exact: true }).click(); // invasive species -> which ones
  await expect(page.getByRole("heading", { name: "Which ones?" })).toBeVisible();
  await expect(page.getByText("No plant list for this region yet.")).toBeVisible();
  await page.getByLabel("Not sure").check();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "No", exact: true }).click(); // cuts
  await expect(page.getByRole("heading", { name: "Which feelings best describe your experience?" })).toBeVisible();
  await page.getByLabel("Joy").fill("4");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: /^Good:/ }).click();
  await expect(page.getByRole("heading", { name: "Photos" })).toBeVisible();
}

test("guided check: one question per screen, follow-ups in place, finalize", async ({ page }) => {
  const urls = watchRequests(page);
  const calls = await mockApi(page);
  await page.goto("/check");
  await expect(page.getByRole("heading", { name: "Creek check" })).toBeVisible();
  await placePin(page);
  await expect(page.getByText("Question 1 of")).toBeVisible();
  await expect(page.getByText("Draft wording")).toBeVisible();
  await answerForm(page);
  await page.getByRole("button", { name: "Send" }).click();

  const draft = calls.find((c) => c.path === "/api/check/draft")!;
  expect(draft.body.spot).toEqual({ new: { name: "Footbridge", latitude: 37.8719, longitude: -122.2585, coarse: false } });
  expect(draft.body.first_rating).toBe("good");
  expect(draft.body.answers.bank_type).toBe("present");
  expect(draft.body.answers.draining_pipes).toBe("present");
  expect(draft.body.answers.water_height_m).toBe(0.3);
  expect(draft.body.answers.habitats).toEqual(["riffles"]);
  expect(draft.body.answers.invasive_which).toEqual(["cant_tell"]);
  // The shape the API validates (SLIDER_RE in worker/src/check.ts and apps/api/check.py). It was
  // an object once, which both servers answered with a 400.
  expect(draft.body.answers.feelings).toContain("joy:4");
  for (const entry of draft.body.answers.feelings) expect(entry).toMatch(/^(joy|serenity|anger|fear):([0-5]|not_applicable)$/);
  expect(draft.body.answers.natural_debris).toBeUndefined();
  expect(draft.body.photo_ids).toEqual([]);
  expect(draft.body.contributor_token).toBeUndefined();

  await expect(page.getByRole("heading", { name: "One or two follow-ups" })).toBeVisible();
  await expect(page.getByText("It has not rained here for 5 days.")).toBeVisible();
  await page.getByRole("region", { name: "dry_pipe" }).getByRole("button", { name: "Yes", exact: true }).click();
  await page.getByRole("button", { name: "Change my rating" }).click();
  await page.getByRole("button", { name: /^Moderate:/ }).click();
  await page.getByRole("button", { name: "Finish" }).click();

  const fin = calls.find((c) => c.path === "/api/check/finalize")!;
  expect(fin.body).toEqual({ draft_id: "d1", followup_answers: { dry_pipe: "yes", rating_check: "changed" }, final_rating: "moderate" });
  await expect(page.getByRole("heading", { name: "Saved" })).toBeVisible();
  await expect(page.getByRole("link", { name: "See this creek's record" })).toHaveAttribute("href", "/spot?id=example");
  expect(await page.evaluate(() => localStorage.getItem("sl_saved_spots"))).toContain("Footbridge");
  expect(assertOnlyOurOrigins(urls, BASE)).toEqual([]);
});

test("offline: the check is saved on the phone and sent when the network returns", async ({ page, context }) => {
  const offline = { value: false };
  const calls = await mockApi(page, { offline });
  await page.goto("/check");
  await placePin(page);
  await answerForm(page);

  offline.value = true;
  await context.setOffline(true);
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByTestId("queue-saved")).toHaveText("Saved on this phone. It will send when you are back online.");
  expect(calls.filter((c) => c.path === "/api/check/finalize")).toHaveLength(0);
  const queued = await page.evaluate(
    () =>
      new Promise<number>((resolve) => {
        const req = indexedDB.open("second-look", 1);
        req.onsuccess = () => {
          const tx = req.result.transaction("queue", "readonly");
          const all = tx.objectStore("queue").getAll();
          all.onsuccess = () => resolve(all.result.length);
        };
      }),
  );
  expect(queued).toBe(1);

  offline.value = false;
  await context.setOffline(false);
  await expect(page.getByTestId("queue-sent")).toHaveText("Sent.", { timeout: 20_000 });
  expect(calls.filter((c) => c.path === "/api/check/draft").length).toBeGreaterThanOrEqual(2);
  const fin = calls.find((c) => c.path === "/api/check/finalize")!;
  expect(fin.body).toMatchObject({ draft_id: "d1", followup_answers: {}, final_rating: "good" });
  await expect(page.getByRole("link", { name: "See this creek's record" })).toBeVisible();
});

test("a saved contributor token travels with the check", async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto("/check");
  await page.evaluate(() => localStorage.setItem("sl_contributor_token", "MOCKTOKEN1234567"));
  await page.reload();
  await placePin(page);
  await answerForm(page);
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("heading", { name: "One or two follow-ups" })).toBeVisible();
  expect(calls.find((c) => c.path === "/api/check/draft")!.body.contributor_token).toBe("MOCKTOKEN1234567");
});
