import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { assertOnlyOurOrigins, mockApi, watchRequests } from "./mock-api.mjs";
import { BASE } from "./helpers";

const en: Record<string, string> = JSON.parse(
  readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"),
).locale;

/** The app's own word for one of our buttons or labels in a language, else our English. */
function appWord(lang: string, key: string, english: string): string {
  const doc = JSON.parse(
    readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"),
  ).app_strings;
  if (lang === "en" || doc.fallback[lang]?.[`ui:${key}`]) return english;
  return doc.strings[lang].ui[key];
}

/** Drops a pin (the denied-location path) and names the spot. In another language the three
 * labels and Next are the official app's own words; the rest of the screen is ours, in English. */
async function placePin(
  page: import("@playwright/test").Page,
  { latitude = "37.8719", longitude = "-122.2585", lang = "en" } = {},
) {
  await page.getByRole("button", { name: "Start the check" }).click();
  await expect(
    page.getByRole("heading", { name: "Where are you?" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Drop a pin instead" }).click();
  await expect(page.getByText("No map tiles here")).toBeVisible();
  await page
    .getByLabel(appWord(lang, "latitude", "Latitude"), { exact: true })
    .fill(latitude);
  await page
    .getByLabel(appWord(lang, "longitude", "Longitude"), { exact: true })
    .fill(longitude);
  await page
    .getByLabel(appWord(lang, "spot_name", "Name for this spot"), {
      exact: true,
    })
    .fill("Footbridge");
  await page
    .getByRole("button", { name: appWord(lang, "next", "Next"), exact: true })
    .click();
}

/** Answers every question in the form's order. Overall rating Good so the rating check fires.
 * On the feelings screen it moves Joy to 4, unless moveJoy is false. */
async function answerForm(
  page: import("@playwright/test").Page,
  { moveJoy = true } = {},
) {
  await expect(
    page.getByRole("heading", { name: "Channel form" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "U shape" }).click();
  await page
    .getByRole("button", {
      name: "Artificial (concrete or stones with concrete)",
    })
    .click(); // bottom
  await page
    .getByRole("button", {
      name: "Artificial (concrete or stones with concrete)",
    })
    .click(); // bank
  await page.getByLabel("Riffles, rapids, falls").check(); // habitats
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "None of these" }).click(); // natural debris
  await page.getByRole("button", { name: "Slow", exact: true }).click(); // water flow
  await page.getByRole("button", { name: "Clear/transparent" }).click(); // water aspect
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
  await expect(
    page.getByRole("heading", { name: "Which ones?" }),
  ).toBeVisible();
  // The Bay Area list was approved on 2026-09-25 (UPDATE_30 section 3), so its plants are offered.
  await expect(
    page.getByLabel("Himalayan blackberry (Rubus armeniacus)"),
  ).toBeVisible();
  await expect(
    page.getByText("No plant list for this region yet."),
  ).toHaveCount(0);
  // Critic round 14 B03: the list says whose it is, here the spot's own region.
  await expect(page.getByTestId("region-list-note")).toHaveText(
    "This list is for California, San Francisco Bay Area.",
  );
  await page.getByLabel("Can't tell").check();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "No", exact: true }).click(); // cuts
  await expect(
    page.getByRole("heading", {
      name: "Which feeling(s) best describe your experience?",
    }),
  ).toBeVisible();
  if (moveJoy) await page.getByLabel("Joy").fill("4");
  else {
    // Ticked and then unticked again: still not an answer.
    await page
      .locator(".card", { hasText: "Serenity" })
      .getByLabel("Not applicable")
      .check();
    await page
      .locator(".card", { hasText: "Serenity" })
      .getByLabel("Not applicable")
      .uncheck();
  }
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: /^Good quality/ }).click();
  await expect(page.getByRole("heading", { name: "Photos" })).toBeVisible();
}

// UPDATE_32 section 1: every question quotes the official app's public bundle and says where it
// came from, so /check says the words are the app's and no question is marked draft wording.
test("/check says its questions are the official app's own words, as the form says", async ({
  page,
}) => {
  const content = JSON.parse(
    readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"),
  );
  const items: { verified_against_app: boolean; source?: string }[] =
    content.form.items;
  expect(items.length).toBeGreaterThan(0);
  expect(
    items.filter(
      (i) =>
        i.verified_against_app !== true ||
        !i.source?.startsWith("app public bundle, "),
    ),
  ).toEqual([]);
  await mockApi(page);
  await page.goto("/check");
  await expect(
    page.getByText(
      "The questions and answers are the OneAquaHealth Citizen Science App's own, word for word.",
    ),
  ).toBeVisible();
  await expect(page.getByText("draft wording")).toHaveCount(0);
});

// UPDATE_32 section 2: the creek check in the app's own languages, on the phone profile. The
// picked language is remembered, the question and its answers are the app's translation, our own
// buttons stay English with lang="en" and a tag, and a translation found to mean something else
// falls back to English with the tag (Italian draining pipes asks about rainwater).
test("/check in Italian and in Dutch: the app's own translations, our words marked English", async ({
  page,
}) => {
  const content = JSON.parse(
    readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"),
  );
  const it = content.app_strings.strings.it.items;
  const nl = content.app_strings.strings.nl.items;
  await mockApi(page);
  await page.goto("/check");
  await page.getByLabel("Language of the questions").selectOption("it");
  await placePin(page, { lang: "it" });
  await expect(
    page.getByRole("heading", { name: it.channel_form.text }),
  ).toBeVisible();
  await expect(page.locator("#question > span[lang=it]")).toHaveText(
    it.channel_form.text,
  );
  await expect(
    page.getByRole("button", { name: it.channel_form.options.u_shape }),
  ).toBeVisible();
  // Back is the app's own word, in Italian. No row of buttons is marked English as a whole.
  const ui = content.app_strings.strings.it.ui;
  expect(ui.back).toBe("Indietro");
  await expect(
    page.getByRole("button", { name: ui.back, exact: true }),
  ).toHaveAttribute("lang", "it");
  await expect(page.getByRole("button", { name: "Back" })).toHaveCount(0);
  await expect(page.locator(".btn-row[lang]")).toHaveCount(0);
  // Remembered on the phone: a reload keeps Italian.
  await page.reload();
  await expect(page.getByLabel("Language of the questions")).toHaveValue("it");
  // Dutch now, and on to the pipes question, whose Italian falls back to English.
  await page.getByLabel("Language of the questions").selectOption("nl");
  await placePin(page, { lang: "nl" });
  await expect(
    page.getByRole("heading", { name: nl.channel_form.text }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: nl.channel_form.options.u_shape })
    .click();
  await expect(
    page.getByRole("heading", { name: nl.bottom_type.text }),
  ).toBeVisible();
  await expect(page.getByTestId("english-tag")).toHaveCount(0);
  await page.goto("/check");
  await page.getByLabel("Language of the questions").selectOption("it");
  expect(content.app_strings.fallback.it["draining_pipes.text"]).toBeTruthy();
  await placePin(page, { lang: "it" });
  for (let i = 0; i < 20; i++) {
    const h = (await page.locator("#question").textContent()) ?? "";
    if (h.includes("Are there pipes draining polluted water into the stream?"))
      break;
    const skip = page.getByRole("button", { name: "None of these" });
    if (await skip.isVisible()) {
      // On a list: Back and Next in the app's Italian, None of these in our English, marked.
      await expect(skip).toHaveAttribute("lang", "en");
      await expect(
        page.getByRole("button", { name: ui.next, exact: true }),
      ).toHaveAttribute("lang", "it");
      await expect(
        page.getByRole("button", { name: "Next", exact: true }),
      ).toHaveCount(0);
      await skip.click();
    } else await page.locator(".option").first().click();
  }
  await expect(page.locator("#question > span").first()).toHaveAttribute(
    "lang",
    "en",
  );
  await expect(page.locator("#question > span").first()).toHaveText(
    "Are there pipes draining polluted water into the stream?",
  );
  await expect(
    page.locator("#question").getByTestId("english-tag"),
  ).toBeVisible();
  // WCAG 1.3.1: a screen reader hears "shown in English", not the word English tacked onto the
  // question. The visible word is hidden from it; the hidden words are read.
  const tag = page.locator("#question").getByTestId("english-tag");
  await expect(tag.locator("[aria-hidden=true]")).toHaveText(en["check.english_tag"]);
  await expect(tag.locator(".visually-hidden")).toHaveText(en["check.english_tag_sr"]);
  expect(en["check.english_tag_sr"]).toBe("shown in English");
  await expect(
    page.getByRole("button", { name: it.draining_pipes.options.present }),
  ).toBeVisible();
});

test("guided check: one question per screen, follow-ups in place, finalize", async ({
  page,
}) => {
  const urls = watchRequests(page);
  const calls = await mockApi(page);
  await page.goto("/check");
  await expect(
    page.getByRole("heading", { name: "Creek check" }),
  ).toBeVisible();
  await placePin(page);
  await expect(page.getByText("Question 1 of")).toBeVisible();
  await expect(page.getByText("Draft wording")).toHaveCount(0);
  // WCAG 2.4.3: an answer moves to the next question, and its heading takes focus, so a keyboard
  // or screen reader user lands on the new question and not at the top of the page. The quick
  // check does this already (tests/record.spec.ts); the creek check and the walks dropped focus.
  await expect(page.getByRole("heading", { name: "Channel form" })).toBeVisible();
  await page.getByRole("button", { name: "U shape" }).click();
  await expect(page.locator("h1#question")).toBeFocused();
  await expect(page.locator("h1#question")).not.toContainText(/channel form/i);
  await page.getByRole("button", { name: "Back" }).click();
  await expect(page.locator("h1#question")).toContainText(/channel form/i);
  await expect(page.locator("h1#question")).toBeFocused();
  await answerForm(page);
  // Judge walk W01: Send is what writes, and the follow-ups come after it. The Photos screen says
  // so before the button, and nothing has been sent yet.
  await expect(page.getByTestId("send-note")).toHaveText(
    "Send stores this spot and your check on the live site. Any follow-up questions come after that.",
  );
  expect(calls.filter((c) => c.path.startsWith("/api/check"))).toEqual([]);
  await page.getByRole("button", { name: "Send" }).click();

  const draft = calls.find((c) => c.path === "/api/check/draft")!;
  expect(draft.body.spot).toEqual({
    new: {
      name: "Footbridge",
      latitude: 37.8719,
      longitude: -122.2585,
      coarse: false,
    },
  });
  expect(draft.body.first_rating).toBe("good");
  expect(draft.body.language).toBe("en");
  expect(draft.body.answers.bank_type).toBe("present");
  expect(draft.body.answers.draining_pipes).toBe("present");
  expect(draft.body.answers.water_height_m).toBe(0.3);
  expect(draft.body.answers.habitats).toEqual(["riffles"]);
  expect(draft.body.answers.invasive_which).toEqual(["cant_tell"]);
  // The shape the API validates (SLIDER_RE in worker/src/check.ts and apps/api/check.py). It was
  // an object once, which both servers answered with a 400. Only the slider that was moved is sent:
  // the three left where they start are not a 0 (CRITIC_06 H03).
  expect(draft.body.answers.feelings).toEqual(["joy:4"]);
  for (const entry of draft.body.answers.feelings)
    expect(entry).toMatch(/^(joy|serenity|anger|fear):([0-5]|not_applicable)$/);
  expect(draft.body.answers.natural_debris).toBeUndefined();
  expect(draft.body.photo_ids).toEqual([]);
  expect(draft.body.contributor_token).toBeUndefined();

  await expect(
    page.getByRole("heading", { name: "One or two follow-ups" }),
  ).toBeVisible();
  await expect(
    page.getByText("It has not rained here for 5 days."),
  ).toBeVisible();
  // Each card is named by its check, never by its rule's code name (critic round 14 B04).
  await expect(page.getByRole("region", { name: "dry_pipe" })).toHaveCount(0);
  await page
    .getByRole("region", { name: "Pipe after dry days" })
    .getByRole("button", { name: "Yes", exact: true })
    .click();
  await page.getByRole("button", { name: "Change my rating" }).click();
  await page.getByRole("button", { name: /^Moderate quality/ }).click();
  await page.getByRole("button", { name: "Finish" }).click();

  const fin = calls.find((c) => c.path === "/api/check/finalize")!;
  expect(fin.body).toEqual({
    draft_id: "d1",
    followup_answers: { dry_pipe: "yes", rating_check: "change" },
    final_rating: "moderate",
  });
  await expect(page.getByRole("heading", { name: "Saved" })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "See this creek's record" }),
  ).toHaveAttribute("href", "/spot?id=example");
  expect(
    await page.evaluate(() => localStorage.getItem("sl_saved_spots")),
  ).toContain("Footbridge");
  expect(assertOnlyOurOrigins(urls, BASE)).toEqual([]);
});

// CRITIC_06 H03: every feelings slider starts at 0, and a person who went on past the screen
// without moving one was sent as feeling none of the four. The screen has no Skip, so Next with
// no slider moved now leaves the question out, as Skip does elsewhere.
test("feelings sliders nobody moved are not sent with the check", async ({
  page,
}) => {
  const calls = await mockApi(page);
  await page.goto("/check");
  await placePin(page);
  await answerForm(page, { moveJoy: false });
  await page.getByRole("button", { name: "Send" }).click();
  await expect(
    page.getByRole("heading", { name: "One or two follow-ups" }),
  ).toBeVisible();
  const draft = calls.find((c) => c.path === "/api/check/draft")!;
  expect(draft.body.answers.feelings).toBeUndefined();
  // The answers on either side of it are still there.
  expect(draft.body.answers.vegetation_cuts).toBe("absent");
  expect(draft.body.first_rating).toBe("good");
  expect(draft.body.language).toBe("en");
});

test("offline: the check is saved on the phone and sent when the network returns", async ({
  page,
  context,
}) => {
  const offline = { value: false };
  const calls = await mockApi(page, { offline });
  await page.goto("/check");
  await placePin(page);
  await answerForm(page);

  offline.value = true;
  await context.setOffline(true);
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByTestId("queue-saved")).toHaveText(
    "Saved on this phone. It will send when you are back online.",
  );
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
  await expect(page.getByTestId("queue-sent")).toHaveText("Sent.", {
    timeout: 20_000,
  });
  expect(
    calls.filter((c) => c.path === "/api/check/draft").length,
  ).toBeGreaterThanOrEqual(2);
  const fin = calls.find((c) => c.path === "/api/check/finalize")!;
  expect(fin.body).toMatchObject({
    draft_id: "d1",
    followup_answers: {},
    final_rating: "good",
  });
  await expect(
    page.getByRole("link", { name: "See this creek's record" }),
  ).toBeVisible();
});

test("a saved contributor token travels with the check", async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto("/check");
  await page.evaluate(() =>
    localStorage.setItem("sl_contributor_token", "MOCKTOKEN1234567"),
  );
  await page.reload();
  await placePin(page);
  await answerForm(page);
  await page.getByRole("button", { name: "Send" }).click();
  await expect(
    page.getByRole("heading", { name: "One or two follow-ups" }),
  ).toBeVisible();
  expect(
    calls.find((c) => c.path === "/api/check/draft")!.body.contributor_token,
  ).toBe("MOCKTOKEN1234567");
});

// CRITIC_09 R01: a permissions policy belongs to the page that was loaded, and a tap on a Next link
// loads no new page. Every page but /check and /quick sent geolocation=(), so Use my location
// failed on the check a judge opens from /judges, and then said the person had refused it. Each
// way into the check from inside the app is a tap like that, so each is tried here, with location
// allowed and a fake position set, as on a phone where the person said yes.
test.describe("Use my location works on a check opened by a tap inside the app", () => {
  test.use({
    permissions: ["geolocation"],
    geolocation: { latitude: 37.8719, longitude: -122.2585 },
  });
  for (const from of ["/judges", "/offline", "/spot?id=example"]) {
    test(`from ${from}`, async ({ page }) => {
      await mockApi(page);
      await page.goto(from);
      await page
        .getByRole("main")
        .getByRole("link", { name: "Creek check", exact: true })
        .click();
      await expect(
        page.getByRole("heading", { name: "Creek check" }),
      ).toBeVisible();
      await page.getByRole("button", { name: "Start the check" }).click();
      await page.getByRole("button", { name: "Use my location" }).click();
      await expect(page.getByRole("status")).toHaveText(
        "Position found and rounded.",
      );
      await expect(
        page.getByText("Rounded position: 37.87, -122.26"),
      ).toBeVisible();
    });
  }
});

// Critic round 14 B03: in /check the plant list follows the spot's region. A pin outside every
// region pack's box, here Heraklion, gets no list, only Can't tell and None of these, with a line
// that says the list is for the Bay Area. Critic round 14 B04: the Photos screen counts in words
// that fit the number.
test("a spot outside the Bay Area is offered no plant list, and the Photos screen counts photos in plain words", async ({
  page,
}) => {
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
    if (question === "Do you see any non-native or invasive plant species?")
      await page.getByRole("button", { name: "Yes", exact: true }).click();
    else if (
      await page.getByRole("button", { name: "Skip", exact: true }).isVisible()
    )
      await page.getByRole("button", { name: "Skip", exact: true }).click();
    else if (
      await page
        .getByRole("button", { name: "None of these", exact: true })
        .isVisible()
    )
      await page
        .getByRole("button", { name: "None of these", exact: true })
        .click();
    else if (
      await page
        .getByRole("main")
        .getByRole("group")
        .first()
        .getByRole("button")
        .first()
        .isVisible()
    )
      await page
        .getByRole("main")
        .getByRole("group")
        .first()
        .getByRole("button")
        .first()
        .click();
    else await page.getByRole("button", { name: "Next", exact: true }).click();
    await page.waitForFunction(
      (q) => document.querySelector("h1#question")?.textContent?.trim() !== q,
      question,
    );
  }
  await expect(page.locator("h1#question")).toHaveText("Which ones?");
  await expect(page.getByText(/Hedera helix/)).toHaveCount(0);
  await expect(
    page.getByRole("main").getByRole("group").getByRole("checkbox"),
  ).toHaveCount(1);
  await expect(page.getByTestId("region-list-note")).toHaveText(
    "We have a plant list only for California, San Francisco Bay Area, so there is none for this creek. Pick Can't tell, or None of these.",
  );
  await page
    .getByRole("button", { name: "None of these", exact: true })
    .click();
  for (
    let i = 0;
    i < 10 &&
    !(await page.getByRole("heading", { name: "Photos" }).isVisible());
    i++
  ) {
    const question = (await page.locator("h1#question").innerText()).trim();
    if (
      await page.getByRole("button", { name: "Skip", exact: true }).isVisible()
    )
      await page.getByRole("button", { name: "Skip", exact: true }).click();
    else if (
      await page
        .getByRole("main")
        .getByRole("group")
        .first()
        .getByRole("button")
        .first()
        .isVisible()
    )
      await page
        .getByRole("main")
        .getByRole("group")
        .first()
        .getByRole("button")
        .first()
        .click();
    else await page.getByRole("button", { name: "Next", exact: true }).click();
    await page.waitForFunction(
      (q) => document.querySelector("h1#question")?.textContent?.trim() !== q,
      question,
    );
  }
  await expect(page.getByRole("heading", { name: "Photos" })).toBeVisible();
  await expect(page.getByText("0 photos ready")).toBeVisible();
  await expect(page.getByText(/photo\(s\)/)).toHaveCount(0);
});

// Critic round 16 K01: the spot's name is public, and the screen said nothing about it; and after
// Use my location, Drop a pin instead kept "Position found and rounded." over empty pin fields.
test.describe("the location step says the spot's name is public, and a pin clears the found line", () => {
  test.use({
    permissions: ["geolocation"],
    geolocation: { latitude: 37.8719, longitude: -122.2585 },
  });
  test("found, then a pin", async ({ page }) => {
    await mockApi(page);
    await page.goto("/check");
    await page.getByRole("button", { name: "Start the check" }).click();
    await page.getByRole("button", { name: "Use my location" }).click();
    await expect(page.getByRole("status")).toHaveText(
      "Position found and rounded.",
    );
    await expect(page.getByText(en["check.pin_name_public"])).toBeVisible();
    await expect(page.getByLabel("Name for this spot")).toHaveAttribute(
      "aria-describedby",
      "spot-name-public",
    );
    await page.getByRole("button", { name: "Drop a pin instead" }).click();
    await expect(page.getByText("Position found and rounded.")).toHaveCount(0);
    await expect(page.getByText(en["check.pin_name_public"])).toBeVisible();
  });
});

// UPDATE_32 section 7, review finding 3: in another language the follow-ups are our own English
// words and say so, and the rating check offers the ratings in the app's own translation.
test("/check in Portuguese: the follow-ups say they are English, the rating check is the app's", async ({
  page,
}) => {
  const content = JSON.parse(
    readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"),
  );
  const pt = content.app_strings.strings.pt.items.overall_rating;
  await mockApi(page);
  await page.goto("/check");
  await page.getByLabel("Language of the questions").selectOption("pt");
  const words = content.app_strings.strings.pt.ui;
  expect([words.back, words.next, words.send]).toEqual([
    "Anterior",
    "Seguinte",
    "Submeter",
  ]);
  await placePin(page, { lang: "pt" });
  for (let i = 0; i < 40; i++) {
    if (await page.getByRole("heading", { name: "Photos" }).isVisible()) break;
    const good = page.getByRole("button", { name: new RegExp(`^${pt.options.good}`) });
    const none = page.getByRole("button", { name: "None of these" });
    const skip = page.getByRole("button", { name: "Skip" });
    if (await good.isVisible()) await good.click();
    else if (await none.isVisible()) await none.click();
    else if (await skip.first().isVisible()) await skip.first().click();
    else if (await page.locator(".option").first().isVisible()) await page.locator(".option").first().click();
    // The feelings sliders: none moved, so Next leaves the question out.
    else
      await page.getByRole("button", { name: words.next, exact: true }).click();
    await page.waitForTimeout(50);
  }
  // The photo step: Back and Send in the app's Portuguese, and no English Send beside them.
  await expect(
    page.getByRole("button", { name: words.back, exact: true }),
  ).toHaveAttribute("lang", "pt");
  await expect(
    page.getByRole("button", { name: "Send", exact: true }),
  ).toHaveCount(0);
  const send = page.getByRole("button", { name: words.send, exact: true });
  await expect(send).toHaveAttribute("lang", "pt");
  await send.click();
  await expect(page.getByRole("heading", { name: "One or two follow-ups" })).toBeVisible();
  const card = page.locator("section.card[data-rule]").first();
  await expect(card).toHaveAttribute("lang", "en");
  await expect(card.getByTestId("english-tag")).toBeVisible();
  await page.getByRole("button", { name: "Change my rating" }).click();
  const moderate = page.getByRole("button", { name: new RegExp(`^${pt.options.moderate}`) });
  await expect(moderate).toBeVisible();
  await expect(moderate).toHaveAttribute("lang", "pt");
});

// Audit finding phone-ux-languages-1: a phone set to Portuguese opened the check in English,
// because only a stored choice was read. With nothing stored, the first of the browser's own
// languages that the check offers is the default. A stored choice still wins, and a browser
// whose languages the check does not offer stays English.
const PICKER = "Language of the questions";
for (const [locale, want] of [
  ["pt-PT", "pt"],
  ["nb-NO", "no"],
  ["nn-NO", "no"],
  ["fr-CA", "fr"],
  ["en-US", "en"],
  ["de-DE", "en"],
] as const) {
  test.describe(`a browser set to ${locale}`, () => {
    test.use({ locale });
    test(`opens the check in ${want} when nothing is stored`, async ({
      page,
    }) => {
      await mockApi(page);
      await page.goto("/check");
      await expect(page.getByLabel(PICKER)).toHaveValue(want);
      expect(
        await page.evaluate(() => localStorage.getItem("sl.check_lang")),
      ).toBeNull();
      // The page itself stays English: only the questions follow the language.
      await expect(page.locator("html")).toHaveAttribute("lang", "en");
    });
  });
}

test.describe("a browser set to pt-PT with a stored choice", () => {
  test.use({ locale: "pt-PT" });
  test("the stored choice wins over the browser's language", async ({
    page,
  }) => {
    await mockApi(page);
    await page.addInitScript(() =>
      localStorage.setItem("sl.check_lang", "fr"),
    );
    await page.goto("/check");
    await expect(page.getByLabel(PICKER)).toHaveValue("fr");
  });

  test("the first question is in the browser's language, and a pick is kept", async ({
    page,
  }) => {
    const content = JSON.parse(
      readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"),
    );
    await mockApi(page);
    await page.goto("/check");
    await expect(page.getByLabel(PICKER)).toHaveValue("pt");
    await placePin(page, { lang: "pt" });
    await expect(page.locator("#question > span[lang=pt]")).toHaveText(
      content.app_strings.strings.pt.items.channel_form.text,
    );
    await page.goto("/check");
    await page.getByLabel(PICKER).selectOption("en");
    await page.reload();
    await expect(page.getByLabel(PICKER)).toHaveValue("en");
  });
});

// Some Android WebViews write the language with an underscore, pt_BR, and the check opened in
// English on them, because only a hyphen was split on.
test("a browser that writes its language as pt_BR opens the check in Portuguese", async ({
  page,
}) => {
  await mockApi(page);
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "languages", { get: () => ["pt_BR", "en-US"] });
    Object.defineProperty(navigator, "language", { get: () => "pt_BR" });
  });
  await page.goto("/check");
  await expect(page.getByLabel(PICKER)).toHaveValue("pt");
});

// Audit finding phone-ux-languages-2, second case: the plant list's last answer was "Can't tell"
// in English with no tag, while every other question said it in the app's own words. It now uses
// the words of the app's invasive species question, which "Which ones?" belongs to. The plants'
// names are from our own list, so they stay English and say so to a screen reader.
test("/check in Portuguese: the plant list ends on the app's own not sure answer", async ({
  page,
}) => {
  const content = JSON.parse(
    readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"),
  );
  const pt = content.app_strings.strings.pt.items;
  await mockApi(page);
  await page.goto("/check");
  await page.getByLabel(PICKER).selectOption("pt");
  await placePin(page, { lang: "pt" });
  for (let i = 0; i < 30; i++) {
    const h = (
      (await page.locator("#question > span").first().textContent()) ?? ""
    ).trim();
    if (h === pt.invasive_which.text) break;
    const none = page.getByRole("button", { name: "None of these" });
    const skip = page.getByRole("button", { name: "Skip" });
    if (await none.isVisible()) await none.click();
    else if (await skip.isVisible()) await skip.click();
    else await page.locator("button.option").first().click();
    await page.waitForFunction(
      (was) =>
        document.querySelector("#question > span")?.textContent?.trim() !==
        was,
      h,
    );
  }
  await expect(page.locator("#question > span[lang=pt]")).toHaveText(
    pt.invasive_which.text,
  );
  const options = page.locator("label.option");
  const last = options.last();
  await expect(last.locator("span[lang=pt]")).toHaveText(
    pt.invasive_species.options.cant_tell,
  );
  await expect(last.getByTestId("english-tag")).toHaveCount(0);
  await expect(page.getByText("Can't tell", { exact: true })).toHaveCount(0);
  // A plant of the Bay Area list, where the pin is: our own English words.
  expect(await options.count()).toBeGreaterThan(1);
  await expect(options.first().locator("span[lang=en]")).toBeVisible();
});

// Audit findings phone-ux-languages-4 and 6, on the phone profile (390 by 664). The app's long
// questions ran six or seven lines and pushed the last answer off the first screen in four
// languages, and on 9 of 24 screens an English section line sat right above the translated
// question. Now a long question is set one size down, a section line shows only in the language
// of the questions, and the English tag is a small outlined label on one line.
const formSections: { id: string; title: string }[] = JSON.parse(
  readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"),
).form.sections;
for (const lang of ["en", "pt", "nl", "no", "fr", "it"]) {
  test(`every question screen in ${lang}: the answers fit the first screen and no stray English line`, async ({
    page,
  }) => {
    const content = JSON.parse(
      readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"),
    );
    const app = content.app_strings.strings[lang];
    await mockApi(page);
    await page.goto("/check");
    await page.getByLabel(PICKER).selectOption(lang);
    // A pin in Lisbon, outside every plant list, so the plant question is a short one too.
    await placePin(page, {
      latitude: "38.7223",
      longitude: "-9.1393",
      lang,
    });
    const seen: string[] = [];
    const lines: Record<string, number> = {};
    for (const item of content.form.items as {
      id: string;
      type: string;
      section: string;
      text: string;
    }[]) {
      const heading = page.locator("h1#question");
      const shown =
        lang !== "en" && content.app_strings.fallback[lang]?.[`${item.id}.text`]
          ? item.text
          : app.items[item.id].text;
      await expect(heading.locator("span").first()).toHaveText(shown);
      seen.push(item.id);
      await page.evaluate(() => window.scrollTo(0, 0));

      // The section line: the app's own title in this language, or none.
      const line = page.getByTestId("section-line");
      const title = app.sections[item.section];
      if (title) {
        await expect(line.locator(`span[lang=${lang}]`)).toHaveText(title);
        lines[item.section] = (lines[item.section] ?? 0) + 1;
      } else if (lang === "en") {
        await expect(line).toHaveText(
          formSections.find((x) => x.id === item.section)!.title,
        );
      } else await expect(line).toHaveCount(0);
      if (lang !== "en")
        await expect(line.getByTestId("english-tag")).toHaveCount(0);

      // Every answer of a pick-one question ends on the first screen.
      if (item.type === "choice" || item.type === "yesno") {
        const height = page.viewportSize()!.height;
        const boxes = await page
          .locator("button.option")
          .evaluateAll((els) =>
            els.map((e) => Math.round(e.getBoundingClientRect().bottom)),
          );
        expect(boxes.length).toBeGreaterThan(1);
        for (const bottom of boxes)
          expect(bottom, `${item.id} in ${lang}`).toBeLessThanOrEqual(height);
      }

      // A long question is one size down; the rest keep the heading's size.
      const size = await heading.evaluate((h) => getComputedStyle(h).fontSize);
      expect(size, item.id).toBe(shown.length > 90 ? "24px" : "30px");

      // Each English tag on the screen is a label on one line, with an outline.
      for (const tag of await page.getByTestId("english-tag").all()) {
        const look = await tag.evaluate((e) => {
          const c = getComputedStyle(e);
          const line = parseFloat(c.lineHeight) || parseFloat(c.fontSize) * 1.5;
          return {
            oneLine: e.getBoundingClientRect().height < 2 * line,
            weight: c.fontWeight,
            outline: c.borderTopColor !== c.backgroundColor,
            clear: c.borderTopColor.includes(", 0)"),
          };
        });
        expect(look, item.id).toEqual({
          oneLine: true,
          weight: "400",
          outline: true,
          clear: false,
        });
      }
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBeLessThanOrEqual(page.viewportSize()!.width);

      // The note above the plant list runs several lines, and its tag follows its last word:
      // it is not a column of its own beside the note.
      if (item.type === "pick_region_list" && lang !== "en") {
        const note = page.getByTestId("region-list-note");
        const noteBox = (await note.boundingBox())!;
        const tagBox = (await note.getByTestId("english-tag").boundingBox())!;
        expect(noteBox.height).toBeGreaterThan(3 * tagBox.height);
        expect(tagBox.y).toBeGreaterThan(noteBox.y + noteBox.height / 2);
      }

      const none = page.getByRole("button", { name: "None of these" });
      const skip = page.getByRole("button", { name: "Skip" });
      if (item.type === "multi" || item.type === "pick_region_list")
        await none.click();
      else if (item.type === "number") await skip.click();
      else if (item.type === "sliders")
        await page.locator(".btn-row .btn:not(.btn-secondary)").last().click();
      else await page.locator("button.option").first().click();
    }
    await expect(page.getByRole("heading", { name: "Photos" })).toBeVisible();
    // Yes everywhere asks every question, the plant list too.
    expect(seen.length).toBe(content.form.items.length);
    if (lang !== "en")
      expect(Object.keys(lines).sort()).toEqual(["margins", "what_you_see"]);
  });
}

// Audit finding phone-ux-languages-3: the official app has its own words for Next, Previous and
// Submit and for the three labels of a pin, in all six languages, and the check showed ours in
// English on every screen. They are the app's now, each read beside the English for meaning
// (docs/notes/app_translations.md). English keeps our own words, as the app's English has a typo.
for (const lang of ["en", "pt", "nl", "no", "fr", "it"]) {
  test(`the pin's labels, Back and Next in ${lang} are the app's own words, or ours in English`, async ({
    page,
  }) => {
    const content = JSON.parse(
      readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"),
    );
    const ui = content.app_strings.strings[lang].ui;
    const want =
      lang === "en"
        ? {
            latitude: "Latitude",
            longitude: "Longitude",
            spot_name: "Name for this spot",
            back: "Back",
            next: "Next",
          }
        : {
            latitude: ui.latitude,
            longitude: ui.longitude,
            spot_name: ui.spot_name,
            back: ui.back,
            next: ui.next,
          };
    expect(Object.values(want).every((w) => typeof w === "string" && w)).toBe(
      true,
    );
    await mockApi(page);
    await page.goto("/check");
    await page.getByLabel(PICKER).selectOption(lang);
    await page.getByRole("button", { name: "Start the check" }).click();
    await page.getByRole("button", { name: "Drop a pin instead" }).click();
    const labels = page.locator("form .field-label");
    await expect(labels).toHaveText([
      want.latitude,
      want.longitude,
      want.spot_name,
    ]);
    for (const label of await labels.all())
      await expect(label).toHaveAttribute("lang", lang);
    const buttons = page.locator("form .btn-row button");
    await expect(buttons).toHaveText([want.back, want.next]);
    for (const b of await buttons.all())
      await expect(b).toHaveAttribute("lang", lang);
    // The app's English typo never shows.
    await expect(page.getByText("Logitude")).toHaveCount(0);
    // Back goes back, whatever it is called.
    await buttons.first().click();
    await expect(
      page.getByRole("heading", { name: "Creek check", level: 1 }),
    ).toBeVisible();
  });
}
