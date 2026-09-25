import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
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

/** Answers every question in the form's order. Overall rating Good so the rating check fires.
 * On the feelings screen it moves Joy to 4, unless moveJoy is false. */
async function answerForm(page: import("@playwright/test").Page, { moveJoy = true } = {}) {
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
  // The Bay Area list was approved on 2026-09-25 (UPDATE_30 section 3), so its plants are offered.
  await expect(page.getByLabel("Himalayan blackberry (Rubus armeniacus)")).toBeVisible();
  await expect(page.getByText("No plant list for this region yet.")).toHaveCount(0);
  // Critic round 14 B03: the list says whose it is, here the spot's own region.
  await expect(page.getByTestId("region-list-note")).toHaveText("This list is for California, San Francisco Bay Area.");
  await page.getByLabel("Can't tell").check();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "No", exact: true }).click(); // cuts
  await expect(page.getByRole("heading", { name: "Which feelings best describe your experience?" })).toBeVisible();
  if (moveJoy) await page.getByLabel("Joy").fill("4");
  else {
    // Ticked and then unticked again: still not an answer.
    await page.locator(".card", { hasText: "Serenity" }).getByLabel("Not applicable").check();
    await page.locator(".card", { hasText: "Serenity" }).getByLabel("Not applicable").uncheck();
  }
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: /^Good:/ }).click();
  await expect(page.getByRole("heading", { name: "Photos" })).toBeVisible();
}

// CRITIC_10 T03: /check said "We have not yet checked the questions marked draft against that
// app", which suggests some are not draft, when content/form.yaml marks every one unchecked. The
// note says so. If a question is ever checked against the app, the first line fails, and the note
// must change with it.
test("/check says none of its questions has been checked against the app, as the form says", async ({ page }) => {
  const content = JSON.parse(readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"));
  const items: { verified_against_app: boolean }[] = content.form.items;
  expect(items.length).toBeGreaterThan(0);
  expect(items.filter((i) => i.verified_against_app !== false)).toEqual([]);
  await mockApi(page);
  await page.goto("/check");
  await expect(page.getByText("None of these questions has been checked against that app yet, so each is marked draft wording.")).toBeVisible();
  await expect(page.getByText("questions marked draft")).toHaveCount(0);
});

test("guided check: one question per screen, follow-ups in place, finalize", async ({ page }) => {
  const urls = watchRequests(page);
  const calls = await mockApi(page);
  await page.goto("/check");
  await expect(page.getByRole("heading", { name: "Creek check" })).toBeVisible();
  await placePin(page);
  await expect(page.getByText("Question 1 of")).toBeVisible();
  await expect(page.getByText("Draft wording")).toBeVisible();
  await answerForm(page);
  // Judge walk W01: Send is what writes, and the follow-ups come after it. The Photos screen says
  // so before the button, and nothing has been sent yet.
  await expect(page.getByTestId("send-note")).toHaveText(
    "Send stores this spot and your check on the live site. Any follow-up questions come after that.",
  );
  expect(calls.filter((c) => c.path.startsWith("/api/check"))).toEqual([]);
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
  // an object once, which both servers answered with a 400. Only the slider that was moved is sent:
  // the three left where they start are not a 0 (CRITIC_06 H03).
  expect(draft.body.answers.feelings).toEqual(["joy:4"]);
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
  expect(fin.body).toEqual({ draft_id: "d1", followup_answers: { dry_pipe: "yes", rating_check: "change" }, final_rating: "moderate" });
  await expect(page.getByRole("heading", { name: "Saved" })).toBeVisible();
  await expect(page.getByRole("link", { name: "See this creek's record" })).toHaveAttribute("href", "/spot?id=example");
  expect(await page.evaluate(() => localStorage.getItem("sl_saved_spots"))).toContain("Footbridge");
  expect(assertOnlyOurOrigins(urls, BASE)).toEqual([]);
});

// CRITIC_06 H03: every feelings slider starts at 0, and a person who went on past the screen
// without moving one was sent as feeling none of the four. The screen has no Skip, so Next with
// no slider moved now leaves the question out, as Skip does elsewhere.
test("feelings sliders nobody moved are not sent with the check", async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto("/check");
  await placePin(page);
  await answerForm(page, { moveJoy: false });
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("heading", { name: "One or two follow-ups" })).toBeVisible();
  const draft = calls.find((c) => c.path === "/api/check/draft")!;
  expect(draft.body.answers.feelings).toBeUndefined();
  // The answers on either side of it are still there.
  expect(draft.body.answers.vegetation_cuts).toBe("absent");
  expect(draft.body.first_rating).toBe("good");
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
        // No version: whichever the app is at. Version 2 added the walks store (UPDATE_30).
        const req = indexedDB.open("second-look");
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

// CRITIC_09 R01: a permissions policy belongs to the page that was loaded, and a tap on a Next link
// loads no new page. Every page but /check and /quick sent geolocation=(), so Use my location
// failed on the check a judge opens from /judges, and then said the person had refused it. Each
// way into the check from inside the app is a tap like that, so each is tried here, with location
// allowed and a fake position set, as on a phone where the person said yes.
test.describe("Use my location works on a check opened by a tap inside the app", () => {
  test.use({ permissions: ["geolocation"], geolocation: { latitude: 37.8719, longitude: -122.2585 } });
  for (const from of ["/judges", "/offline", "/spot?id=example"]) {
    test(`from ${from}`, async ({ page }) => {
      await mockApi(page);
      await page.goto(from);
      await page.getByRole("main").getByRole("link", { name: "Creek check", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Creek check" })).toBeVisible();
      await page.getByRole("button", { name: "Start the check" }).click();
      await page.getByRole("button", { name: "Use my location" }).click();
      await expect(page.getByRole("status")).toHaveText("Position found and rounded.");
      await expect(page.getByText("Rounded position: 37.87, -122.26")).toBeVisible();
    });
  }
});

// Critic round 14 B03: in /check the plant list follows the spot's region. A pin outside every
// region pack's box, here Heraklion, gets no list, only Can't tell and None of these, with a line
// that says the list is for the Bay Area.
test("a spot outside the Bay Area is offered no plant list", async ({ page }) => {
  await mockApi(page);
  await page.goto("/check");
  await page.getByRole("button", { name: "Start the check" }).click();
  await page.getByRole("button", { name: "Drop a pin instead" }).click();
  await page.getByLabel("Latitude").fill("35.3387");
  await page.getByLabel("Longitude").fill("25.1442");
  await page.getByLabel("Name for this spot").fill("Bridge");
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByText("Question 1 of")).toBeVisible();
  for (let i = 0; i < 40; i++) {
    const question = (await page.locator("h1#question").innerText()).trim();
    if (question === "Which ones?") break;
    if (question === "Do you see any non-native or invasive plant species?") await page.getByRole("button", { name: "Yes", exact: true }).click();
    else if (await page.getByRole("button", { name: "Skip", exact: true }).isVisible()) await page.getByRole("button", { name: "Skip", exact: true }).click();
    else if (await page.getByRole("button", { name: "None of these", exact: true }).isVisible()) await page.getByRole("button", { name: "None of these", exact: true }).click();
    else if (await page.getByRole("main").getByRole("group").first().getByRole("button").first().isVisible()) await page.getByRole("main").getByRole("group").first().getByRole("button").first().click();
    else await page.getByRole("button", { name: "Next", exact: true }).click();
    await page.waitForFunction((q) => document.querySelector("h1#question")?.textContent?.trim() !== q, question);
  }
  await expect(page.locator("h1#question")).toHaveText("Which ones?");
  await expect(page.getByText(/Hedera helix/)).toHaveCount(0);
  await expect(page.getByRole("main").getByRole("group").getByRole("checkbox")).toHaveCount(1);
  await expect(page.getByTestId("region-list-note")).toHaveText(
    "We have a plant list only for California, San Francisco Bay Area, so there is none for this creek. Pick Can't tell, or None of these.",
  );
});
