import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import {
  toPageTop,
  toRegionTop,
  wholeOnFirstScreen,
} from "../scripts/gallery-view.mjs";
import { answerWalkPlainly } from "../scripts/gallery-walk.mjs";
import { assertOnlyOurOrigins, mockApi, watchRequests } from "./mock-api.mjs";
import { BASE } from "./helpers";

// Update 14 3.7: a walk is a guided check made while watching a clip. The record is built on the
// phone and tagged as a demo on every resource. Since UPDATE_30 the finished walk is also sent to
// the walk store, and to nothing else (tests/walk-store.spec.ts).
const content = JSON.parse(
  readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"),
);
const walks: {
  id: string;
  country: string;
  creek_name: string;
  title: string;
  author: string;
  question: unknown;
  checker_run: string;
  checker_dropped: number;
}[] = content.walks ?? [];

// Update 14 asks for four walks from four countries. The rule found three (docs/DECISIONS.md,
// 2026-09-22), so the test holds the rule itself: at least one, each from a different country.
test("every walk comes from a different country and is linked from /judges", async ({
  page,
}) => {
  expect(walks.length).toBeGreaterThan(0);
  expect(new Set(walks.map((w) => w.country)).size).toBe(walks.length);
  await page.goto(`${BASE}/judges`);
  await page
    .getByRole("link", { name: "Check a creek from your desk" })
    .click();
  // CRITIC_09 Q04: each link is named by its creek alone. The poster is decoration, so its alt
  // text is empty, and the name no longer starts with "photo of a creek".
  for (const w of walks) {
    const link = page.getByRole("link", { name: w.creek_name, exact: true });
    await expect(link).toBeVisible();
    await expect(link.locator("img")).toHaveAttribute("alt", "");
  }
  // "A creek in the United Kingdom", never "A creek in United Kingdom" (REVIEW_03 R41).
  const names = await page.getByRole("main").getByRole("link").allInnerTexts();
  expect(names.filter((n) => /\bin United\b/.test(n))).toEqual([]);
  if (walks.some((w) => w.country === "United Kingdom"))
    expect(names).toContain("A creek in the United Kingdom");
});

// CRITIC_11 V02: /walk and /judges said the clips show "a creek from another country", though one
// walk is in the United States, where the Berkeley setup that /about describes is.
test("the walks are said to be somewhere else, not from another country", async ({
  page,
}) => {
  for (const path of ["/walk", "/judges"]) {
    await page.goto(`${BASE}${path}`);
    await expect(page.getByRole("main"), path).not.toContainText(
      /another country/i,
    );
    await expect(page.getByRole("main"), path).toContainText(
      "a short clip of a creek somewhere else",
    );
  }
});

// Judge walk W05: the host answers a range request with the whole clip, so even preload
// "metadata" pulled megabytes on page open, before anyone pressed play. Now the clip asks for no
// byte until play, and its poster shows in its place.
test("a walk's clip loads nothing before play and shows its poster", async ({
  page,
}) => {
  await mockApi(page, {});
  const clips: string[] = [];
  page.on("request", (r) => {
    if (/\/walks\/[^/?]+\.mp4/.test(r.url())) clips.push(r.url());
  });
  for (const w of content.walks as { id: string; poster_photo_id: string }[]) {
    await page.goto(`${BASE}/walk/${w.id}`);
    const video = page.locator("video.walk-clip");
    await expect(video).toHaveAttribute("preload", "none");
    await expect(video).toHaveAttribute(
      "poster",
      content.photos[w.poster_photo_id].url,
    );
    await page.waitForLoadState("networkidle");
    expect(
      await video.evaluate((v: HTMLVideoElement) => v.readyState),
      w.id,
    ).toBe(0);
  }
  expect(clips, "clip bytes asked for before play").toEqual([]);
});

// UPDATE_30 section 1 item 3: the finished walk now goes to the walk store, once, as a demo
// record, and to nothing else: no creek check, no upload, no quick check.
test("a walk shows its credit, builds a demo record on the phone, and sends it to the walk store only", async ({
  page,
}) => {
  const calls = await mockApi(page, {});
  const urls = watchRequests(page);
  const w = walks[0];
  await page.goto(`${BASE}/walk/${w.id}`);
  await expect(page.locator("video.walk-clip")).toHaveCount(1);
  await expect(
    page.getByText(w.author, { exact: false }).first(),
  ).toBeVisible();
  await expect(page.getByText(en["walk.demo_notice"])).toBeVisible();
  await expect(page.getByText(en["walk.demo_notice"])).toContainText(
    "never counted",
  );
  await page.getByRole("button", { name: "Start the check" }).click();
  await page.getByRole("button", { name: "U shape" }).click(); // channel form
  // The count's total stays the same when a follow-up such as "Which ones?" appears (REVIEW_03 R42).
  const counts: string[] = [];
  let sawFollowUp = false;
  for (let i = 0; i < 40; i++) {
    if (
      await page
        .getByRole("heading", { name: "Your record from the clip" })
        .isVisible()
    )
      break;
  // WCAG 2.4.3: the next question's heading takes focus (tests/check.spec.ts says why).
  await expect(page.locator("h1#question")).toBeFocused();
    const count = page.getByText(/^Question \d+ of \d+$/);
    if (await count.isVisible()) counts.push(await count.innerText());
    if (await page.getByRole("heading", { name: "Which ones?" }).isVisible())
      sawFollowUp = true;
    if (await page.getByRole("button", { name: "Finish" }).isVisible()) {
      await page.getByRole("button", { name: "Finish" }).click();
      continue;
    }
    // Each kind of question has its own way on: Skip, "None of these", a choice, or Next.
    const skip = page.getByRole("button", { name: "Skip" });
    const none = page.getByRole("button", { name: "None of these" });
    const choice = page
      .getByRole("main")
      .getByRole("group")
      .first()
      // The follow-ups' heading takes focus when they appear, as each question's does.
      await expect(
        page.getByTestId("walk-followups").getByRole("heading", { level: 2 }),
      ).toBeFocused();
      .getByRole("button");
    if (await skip.first().isVisible()) await skip.first().click();
    else if (await none.isVisible()) await none.click();
    else if (await choice.first().isVisible()) await choice.first().click();
    else await page.getByRole("button", { name: "Next", exact: true }).click();
  }
  expect(sawFollowUp).toBe(true);
  expect(new Set(counts.map((c) => c.replace(/^Question \d+ /, ""))).size).toBe(
    1,
  );
  await expect(page.getByTestId("walk-structure")).toHaveText(
    "Every link inside the record checks out",
  );
  // CRITIC_03 E04: a walk whose build record stopped nothing says no model saw a feature, and
  // never blames the pass rule for "0 of its guesses".
  if (!w.question && w.checker_run === "real" && w.checker_dropped === 0) {
    await expect(
      page.getByText(content.locale["walk.checker_nothing_seen"]),
    ).toBeVisible();
    await expect(page.getByText(/of its guesses on this clip/)).toHaveCount(0);
  }
  // Stored as a demo: the page links to it (UPDATE_30 section 1 item 3).
  await expect(page.getByTestId("walk-record-link")).toHaveText(
    en["walk.stored_link"],
  );
  await page.getByRole("button", { name: "View as FHIR" }).click();
  // The record was made on this phone: the badge speaks of walk records made the same way, which
  // the validator checked in CI, never of this one (REVIEW_03 R31). The curl line fetches the
  // stored copy.
  await expect(page.getByTestId("fhir-badge")).toHaveText(
    "Walk records made the same way passed the HL7 validator on Sep 20, 2026. This one was made on your phone and was not checked.",
  );
  await expect(
    page.getByText("passed the HL7 validator against guide commit"),
  ).toHaveCount(0);
  await expect(page.locator("pre.code").first()).toHaveText(
    /^curl -s http:\/\/127\.0\.0\.1:8100\/api\/walk\/walk-[0-9a-f]{16}\/fhir$/,
  );
  const json = await page.locator("pre.code").last().innerText();
  const bundle = JSON.parse(json);
  expect(
    bundle.meta.tag.some((t: { code: string }) => t.code === "demo-walk"),
  ).toBe(true);
  for (const e of bundle.entry)
    expect(
      e.resource.meta.tag.some((t: { code: string }) => t.code === "demo-walk"),
    ).toBe(true);
  // One send, to the walk store: no check, upload or quick call.
  expect(
    calls
      .filter((c: { method: string }) => c.method === "POST")
      .map((c: { path: string }) => c.path),
  ).toEqual(["/api/walk"]);
  expect(
    calls.filter((c: { path: string }) =>
      /\/api\/(check|upload|quick)/.test(c.path),
    ),
  ).toEqual([]);
  expect(assertOnlyOurOrigins(urls, BASE)).toEqual([]);

  await page
    .getByRole("link", { name: "See this creek as a city would" })
    .click();
  await expect(page.getByRole("heading", { name: /Demo creek/ })).toBeVisible();
  await expect(
    page.getByText(en["city.walk_visits"].replace("{n}", "1")),
  ).toBeVisible();
  // CRITIC_04 F04: the walk said yes to barriers, and the finding and the reason carry the short
  // label, never the form's whole question.
  const barriers = formItems.find((it) => it.id === "barriers")!.text;
  // The finding's row: its label, then the count, which textContent joins across the <br>.
  await expect(page.getByRole("main")).toContainText(
    `${en["city.finding_barriers"]}${en["city.walk_seen"].replace("{n}", "1")}`,
  );
  await expect(page.getByRole("main")).toContainText(
    `${en["city.finding_barriers"]}. OneAquaHealth Policy Brief`,
  );
  await expect(page.getByRole("main")).not.toContainText(barriers);
  // CRITIC_06 H01: the walk said yes to plants as well. The plant is listed with what the checks
  // found, beside a plain line that no OneAquaHealth measure answers it; barriers, which has a
  // measure, carries no such line, and no measure names the plant.
  const found = page.getByRole("region", { name: en["city.walk_findings"] });
  const plant = found
    .locator(".row")
    .filter({ hasText: featureNames["invasive_plant"] });
  await expect(plant).toHaveText(
    `${featureNames["invasive_plant"]}${en["city.walk_seen"].replace("{n}", "1")}${en["city.walk_no_measure"]}`,
  );
  await expect(
    found.locator(".row").filter({ hasText: en["city.finding_barriers"] }),
  ).not.toContainText(en["city.walk_no_measure"]);
  await expect(
    page.getByRole("region", { name: en["city.walk_needs"] }),
  ).not.toContainText(featureNames["invasive_plant"]);
});

const featureNames: Record<string, string> = Object.fromEntries(
  content.features.map((f: { id: string; name: string }) => [f.id, f.name]),
);

// CRITIC_07 J04: a walk that found only a plant has a finding and no measure. Its needs box says
// that no measure applies, never "Nothing was found", which the findings box above contradicts.
test("a walk that found only a plant says no measure applies to it", async ({
  page,
}) => {
  await mockApi(page, {});
  const w = walks[0];
  await page.goto(`${BASE}/walk/${w.id}`);
  await page.getByRole("button", { name: "Start the check" }).click();
  const plantItem = content.form.items.find(
    (it: { feature?: string | null; kind?: string }) =>
      it.feature === "invasive_plant",
  )!;
  for (let i = 0; i < 60; i++) {
    if (
      await page
        .getByRole("heading", { name: "Your record from the clip" })
        .isVisible()
    )
      break;
    if (await page.getByRole("button", { name: "Finish" }).isVisible()) {
      await page.getByRole("button", { name: "Finish" }).click();
      continue;
    }
    const onPlant = await page
      .getByRole("heading", { name: plantItem.text, exact: true })
      .isVisible();
    const yes = page.getByRole("button", { name: en["test.yes"], exact: true });
    const no = page.getByRole("button", { name: en["test.no"], exact: true });
    const skip = page.getByRole("button", { name: "Skip" });
    const none = page.getByRole("button", { name: "None of these" });
    const choice = page
      .getByRole("main")
      .getByRole("group")
      .first()
      .getByRole("button");
    if (onPlant && (await yes.isVisible())) await yes.click();
    else if (await no.isVisible()) await no.click();
    else if (await none.isVisible()) await none.click();
    else if (await skip.first().isVisible()) await skip.first().click();
    else if (await choice.first().isVisible()) await choice.first().click();
    else await page.getByRole("button", { name: "Next", exact: true }).click();
  }
  await page
    .getByRole("link", { name: "See this creek as a city would" })
    .click();
  const found = page.getByRole("region", { name: en["city.walk_findings"] });
  await expect(found.locator(".row")).toHaveCount(1);
  await expect(found).toContainText(featureNames["invasive_plant"]);
  const needs = page.getByRole("region", { name: en["city.walk_needs"] });
  await expect(needs).toContainText(en["city.walk_needs_none"]);
  await expect(needs).not.toContainText(en["city.walk_nothing"]);
});

// CRITIC_04 F01: the one record a judge can make listed no answer and no score. The record screen
// now lists every answer the walk made, the way /spot lists a stored visit's, and where /spot shows
// the observer's score it says "No score in a demo record" (walk.not_tested), then points to the
// example on /two, where a volunteer's score travels with the answer.
const en: Record<string, string> = content.locale;
const formItems: { id: string; text: string; feature: string | null }[] =
  content.form.items;

test("the walk's record lists every answer the walk made, with No score in a demo record where /spot shows the score", async ({
  page,
}) => {
  await mockApi(page, {});
  const w = walks[0];
  await page.goto(`${BASE}/walk/${w.id}`);
  await page.getByRole("button", { name: "Start the check" }).click();
  // Each question answered, as the screen showed it: the question and the words of the answer.
  const made: { question: string; answer: string }[] = [];
  for (let i = 0; i < 40; i++) {
    if (
      await page
        .getByRole("heading", { name: "Your record from the clip" })
        .isVisible()
    )
      break;
    if (await page.getByRole("button", { name: "Finish" }).isVisible()) {
      await page.getByRole("button", { name: "Finish" }).click();
      continue;
    }
    const heading = page.locator("h1#question");
    const question = (await heading.innerText()).trim();
    const group = page.getByRole("main").getByRole("group").first();
    const skip = page.getByRole("button", { name: "Skip" });
    const none = page.getByRole("button", { name: "None of these" });
    const choice = group.getByRole("button").first();
    if (await skip.first().isVisible()) await skip.first().click();
    else if (await none.isVisible()) await none.click();
    else if (await choice.isVisible()) {
      // The answer's own words, without the app's line under it (the three overall ratings).
      made.push({
        question,
        answer: (await choice.locator("span").first().innerText()).trim(),
      });
      await choice.click();
    } else {
      // The feelings sliders, left where they start: a slider nobody moved is not an answer, so
      // the question makes no line (CRITIC_06 H03).
      await page.getByRole("button", { name: "Next", exact: true }).click();
    }
    // On to the next screen before the next look: the question on screen has changed or gone.
    await page.waitForFunction(
      (q) => document.querySelector("h1#question")?.textContent?.trim() !== q,
      question,
    );
  }
  await expect(
    page.getByRole("heading", { name: "Your record from the clip" }),
  ).toBeVisible();

  // Both kinds of question were answered, so both kinds of line are held.
  const byText = (q: string) => formItems.find((it) => it.text === q);
  expect(made.every((m) => byText(m.question))).toBe(true);
  expect(made.some((m) => byText(m.question)!.feature)).toBe(true);
  expect(made.some((m) => !byText(m.question)!.feature)).toBe(true);

  const answers = page.getByTestId("walk-answers");
  await expect(
    page.getByRole("heading", { name: en["walk.answers_title"], level: 2 }),
  ).toBeVisible();
  const rows = answers.locator(".answer-line");
  await expect(rows).toHaveCount(made.length);
  for (const [i, m] of made.entries()) {
    const row = rows.nth(i);
    await expect(row.locator(".muted").first()).toHaveText(m.question);
    await expect(row.locator("strong")).toHaveText(m.answer);
    await expect(row.locator(".observer")).toHaveText(
      byText(m.question)!.feature
        ? en["walk.not_tested"]
        : en["spot.no_feature"],
    );
  }
  // No score is made up: nothing reads like a score line or a missing score.
  await expect(answers).not.toContainText(/ of \d+ on |No test score/);

  const note = page.getByTestId("walk-score-note");
  await expect(note).toHaveText(
    en["walk.score_note"].replace("{link}", en["walk.score_link"]),
  );
  await expect(
    note.getByRole("link", { name: en["walk.score_link"], exact: true }),
  ).toHaveAttribute("href", "/two");

  // WCAG 2.2 SC 1.4.10: the record with its answers still fits the phone width.
  const viewport = page.viewportSize()!.width;
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(viewport);
});

/** Goes through a walk's questions the quick way, as the gallery does, until its record shows:
 * Skip, None of these, the first choice, or Next. The feelings screen is left to onFeelings. */
async function answerWalk(page: Page, onFeelings: () => Promise<void>) {
  const feelings = formItems.find((it) => it.id === "feelings")!.text;
  for (let i = 0; i < 40; i++) {
    if (
      await page
        .getByRole("heading", { name: en["walk.done_title"] })
        .isVisible()
    )
      return;
    if (await page.getByRole("button", { name: "Finish" }).isVisible()) {
      await page.getByRole("button", { name: "Finish" }).click();
      continue;
    }
    const question = (await page.locator("h1#question").innerText()).trim();
    const skip = page.getByRole("button", { name: "Skip" });
    const none = page.getByRole("button", { name: "None of these" });
    const choice = page
      .getByRole("main")
      .getByRole("group")
      .first()
      .getByRole("button");
    if (question === feelings) await onFeelings();
    else if (await skip.first().isVisible()) await skip.first().click();
    else if (await none.isVisible()) await none.click();
    else if (await choice.first().isVisible()) await choice.first().click();
    else await page.getByRole("button", { name: "Next", exact: true }).click();
    await page.waitForFunction(
      (q) => document.querySelector("h1#question")?.textContent?.trim() !== q,
      question,
    );
  }
  await expect(
    page.getByRole("heading", { name: en["walk.done_title"] }),
  ).toBeVisible();
}

// CRITIC_06 H03: every feelings slider starts at 0, and one nobody moved was kept as 0, so a person
// who went on past the screen was recorded as feeling none of the four. A slider is an answer only
// once it is moved or marked Not applicable; the rest stay out of the answers and the record.
test("a feelings slider nobody moved stays out of the walk's record", async ({
  page,
}) => {
  await mockApi(page, {});
  const feelings = formItems.find((it) => it.id === "feelings")!.text;
  for (const moved of [false, true]) {
    await page.goto(`${BASE}/walk/${walks[0].id}`);
    // The second time, this tab holds the first walk, so the page opens on its record (CRITIC_10 S01).
    if (moved) {
      await page
        .getByRole("button", { name: en["walk.start_again"], exact: true })
        .click();
      await page
        .getByRole("button", { name: en["walk.start_again_yes"], exact: true })
        .click();
    }
    await page.getByRole("button", { name: "Start the check" }).click();
    await answerWalk(page, async () => {
      const shown = page.locator("output[for^='slider-']");
      // No slider shows a number before it is moved.
      await expect(shown).toHaveText(["", "", "", ""]);
      if (moved) {
        await page.getByLabel("Joy").fill("3");
        await page
          .locator(".card", { hasText: "Fear" })
          .getByLabel("Not applicable")
          .check();
        // Ticked and then unticked again is not an answer either.
        await page
          .locator(".card", { hasText: "Serenity" })
          .getByLabel("Not applicable")
          .check();
        await page
          .locator(".card", { hasText: "Serenity" })
          .getByLabel("Not applicable")
          .uncheck();
        await expect(shown).toHaveText(["3", "", "", ""]);
      }
      await page.getByRole("button", { name: "Next", exact: true }).click();
    });
    const row = page
      .getByTestId("walk-answers")
      .locator(".answer-line")
      .filter({ hasText: feelings });
    if (moved)
      await expect(row.locator("strong")).toHaveText(
        "Joy: 3, Fear: Not applicable",
      );
    else await expect(row).toHaveCount(0);
  }
});

// CRITIC_11 V01: the note on how to see a measure pushed Start the check below the first screen
// of every walk at 390 by 844, and the gallery's picture of a walk, whose alt text names the
// button, showed none. The button now comes before the demo notice. The gallery takes the same
// step (scripts/gallery-view.mjs) before its shot, so a walk whose button is not whole on the
// first screen fails both here and there.
test("Start the check is whole on the first screen of every walk at 390 by 844", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  expect(walks.length).toBeGreaterThan(0);
  for (const w of walks) {
    await page.goto(`${BASE}/walk/${w.id}`);
    const box = await wholeOnFirstScreen(
      page,
      page.getByRole("button", { name: en["walk.start"] }),
    );
    expect(box.y).toBeGreaterThanOrEqual(0);
    expect(box.y + box.height, w.id).toBeLessThanOrEqual(844);
  }
});

// CRITIC_06 H03: the gallery's shot of a walk's record opened on a line cut in half, with the page
// title out of the frame, because the record showed wherever the form had left the page. The
// gallery now goes to the top of the page first (scripts/gallery-view.mjs). This makes a record on
// the gallery's phone size, takes the same step, and checks the title is whole on screen.
test("the gallery's shot of a walk's record has the page title whole in view", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page, {});
  await page.goto(`${BASE}/walk/${walks[0].id}`);
  await page.getByRole("button", { name: "Start the check" }).click();
  await answerWalk(page, () =>
    page.getByRole("button", { name: "Next", exact: true }).click(),
  );
  await toPageTop(page);
  const box = (await page
    .getByRole("heading", { name: en["walk.done_title"], level: 1 })
    .boundingBox())!;
  expect(box.y).toBeGreaterThanOrEqual(0);
  expect(box.y + box.height).toBeLessThanOrEqual(844);
});

// The built-bank measures as the act rules and the approved sentences give them: the words of
// each and its source up to the web address, as the city view shows a source.
const core = JSON.parse(
  readFileSync(
    join(
      __dirname,
      "..",
      "..",
      "..",
      "worker",
      "src",
      "core",
      "core_content.json",
    ),
    "utf8",
  ),
);
const bankMeasures: { text: string; source: string }[] = (
  core.rules.measure_for_feature.artificial_bank as string[]
)
  .map((id) => core.sentences.find((s: { id: string }) => s.id === id))
  .sort((a: { id: string }, b: { id: string }) => (a.id < b.id ? -1 : 1))
  .map((s: { text: string; source: string }) => ({
    text: s.text,
    source: s.source.replace(/\s*https?:\/\/\S+/g, "").trim(),
  }));

// CRITIC_07 J04: the gallery's shot of the walk's city view cut the first measure off before its
// source. The gallery now puts the needs region at the top (scripts/gallery-view.mjs); this makes
// the same city view at the gallery's phone size, takes the same step, and checks the first
// measure is whole on screen, source and all.
// CRITIC_09 Q01: the gallery tapped the first button everywhere, which answers Yes to every yes or
// no question, so its picture showed dams, pipes and plants the clip does not show. It now answers
// Artificial for the bank and reports no other damage (scripts/gallery-walk.mjs), which this runs
// too: the one finding is the built bank, and the needs are the built-bank measures and no others.
test("the gallery's shot of a walk's city view shows the first measure whole, with its source", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page, {});
  await page.goto(`${BASE}/walk/${walks[0].id}`);
  await page.getByRole("button", { name: "Start the check" }).click();
  await answerWalkPlainly(page, content, { bank: "present" });
  await page
    .getByRole("link", { name: "See this creek as a city would" })
    .click();
  const found = page.getByRole("region", { name: en["city.walk_findings"] });
  await expect(found.locator(".row")).toHaveCount(1);
  await expect(found.locator(".row")).toHaveText(
    `${featureNames["artificial_bank"]}${en["city.walk_seen"].replace("{n}", "1")}`,
  );
  const needs = page.getByRole("region", { name: en["city.walk_needs"] });
  await expect(needs.locator(".row")).toHaveText(
    bankMeasures.map(
      (m) => `${m.text}${featureNames["artificial_bank"]}. ${m.source}`,
    ),
  );
  // A walk that found something to fix shows no example.
  await expect(page.getByTestId("walk-example")).toHaveCount(0);
  await toRegionTop(page, en["city.walk_needs"]);
  const first = needs.locator(".row").first();
  await expect(first).toContainText("OneAquaHealth Policy Brief");
  const box = (await first.boundingBox())!;
  expect(box.y).toBeGreaterThanOrEqual(0);
  expect(box.y + box.height).toBeLessThanOrEqual(844);
  // CRITIC_11 U02: the page is too short to bring the region to the top, and the shot stopped
  // where the page ends, cutting the line that counts the checks through the middle at the top edge.
  // It now stops at the top of a whole line instead, so no text is cut there.
  expect(await textCutAtTop(page)).toEqual([]);
});

// CRITIC_11 U02: the same step on a page made too short to bring its region to the top, with lines
// of text of a fractional height above it, so the step must find a line's top for itself.
test("the gallery's step to a region stops at a whole line when the page is too short", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const lines = Array.from(
    { length: 40 },
    (_, i) => `<p style="margin:0">Line ${i + 1} of the text above</p>`,
  ).join("");
  await page.setContent(
    `<head><meta name="viewport" content="width=device-width, initial-scale=1"></head>` +
      `<body style="margin:0;font:17px/25.5px sans-serif">${lines}<section aria-label="Needs" style="height:120px"><h2 style="margin:0">Needs</h2></section></body>`,
  );
  expect(await page.evaluate(() => window.innerHeight)).toBe(844);
  const most = await page.evaluate(
    () => document.documentElement.scrollHeight - window.innerHeight,
  );
  const regionTop = await page
    .getByRole("region", { name: "Needs" })
    .evaluate((el) => el.getBoundingClientRect().top);
  // Too short: the region cannot come to the top, and where the page ends the edge cuts a line.
  expect(most).toBeLessThan(regionTop - 12);
  expect(most % 25.5).not.toBe(0);
  await toRegionTop(page, "Needs");
  expect(await textCutAtTop(page)).toEqual([]);
  // As far down as it can go without cutting one: less than a line short of the end of the page.
  const y = await page.evaluate(() => window.scrollY);
  expect(y).toBeLessThanOrEqual(most);
  expect(most - y).toBeLessThan(25.5 + 12);
  // The region's heading is on screen, whole.
  const box = (await page
    .getByRole("heading", { name: "Needs" })
    .boundingBox())!;
  expect(box.y).toBeGreaterThanOrEqual(0);
  expect(box.y + box.height).toBeLessThanOrEqual(844);
});

/** The text lines on screen that the top edge cuts through: part above it, part below. */
async function textCutAtTop(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const cut: string[] = [];
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
    );
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const text = n.textContent?.trim();
      if (!text) continue;
      const range = document.createRange();
      range.selectNodeContents(n);
      for (const r of Array.from(range.getClientRects()))
        if (r.top < -1 && r.bottom > 1) cut.push(text);
    }
    return cut;
  });
}

// CRITIC_09 Q01: the clips show natural creeks, so a walk answered as the clip shows it found
// nothing, and the city view said so twice and stopped. The walk now says, before the check starts,
// how to see what a city is told, and the city view shows, marked as an example, what one reported
// built bank would ask for, from the same rules and approved sentences. It ends with a way back to
// the judges' doors (CRITIC_09 Q04).
test("a walk says how to see a measure, and an honest walk ends on a marked example of one", async ({
  page,
}) => {
  await mockApi(page, {});
  await page.goto(`${BASE}/walk/${walks[0].id}`);
  const note = page.getByTestId("walk-honest-note");
  await expect(note).toHaveText(en["walk.honest_note"]);
  // It comes before the button that starts the check.
  const start = page.getByRole("button", { name: en["walk.start"] });
  expect(
    await note.evaluate(
      (el, button) =>
        !!(
          el.compareDocumentPosition(button!) & Node.DOCUMENT_POSITION_FOLLOWING
        ),
      await start.elementHandle(),
    ),
  ).toBe(true);
  await start.click();
  await answerWalkPlainly(page, content, { bank: "absent" });
  await page
    .getByRole("link", { name: "See this creek as a city would" })
    .click();
  await expect(
    page.getByRole("region", { name: en["city.walk_findings"] }),
  ).toContainText(en["city.walk_nothing"]);
  await expect(
    page.getByRole("region", { name: en["city.walk_needs"] }),
  ).toContainText(en["city.walk_nothing"]);
  const example = page.getByRole("region", {
    name: en["city.walk_example_title"],
  });
  await expect(
    example.getByRole("heading", {
      name: en["city.walk_example_title"],
      level: 2,
    }),
  ).toBeVisible();
  await expect(example).toContainText(en["city.walk_example_intro"]);
  await expect(example.locator(".row")).toHaveText(
    bankMeasures.map(
      (m) => `${m.text}${featureNames["artificial_bank"]}. ${m.source}`,
    ),
  );
  // CRITIC_11 V02: the link says where it goes. It said "Try another door", and no page calls the
  // judges' entries doors.
  const back = page
    .getByRole("main")
    .getByRole("link", { name: "Back to the judges' page", exact: true });
  await expect(back).toHaveAttribute("href", "/judges");
  await expect(page.getByRole("main")).not.toContainText(/\bdoor\b/i);
  await back.click();
  await expect(
    page.getByRole("heading", { name: "For judges", level: 1 }),
  ).toBeVisible();
});

// Critic round 14 B03 and round 15 F04: Which ones? offered the San Francisco Bay Area's plant list
// on creeks in Russia, the UK and Oregon, English ivy among them, which is native to Britain, and
// named no region. A walk's creek is in no region with a list, so it offers only Can't tell and
// None of these, and says whose list it would be. The line that said the clip could not seek is
// gone, since functions/walks/[[path]].js serves the clip in parts (round 15 W05).
test("a walk's Which ones? offers no region's plants and says the list is for the Bay Area", async ({
  page,
}) => {
  await mockApi(page, {});
  const uk = walks.find((w: { id: string }) => w.id === "v03")!;
  await page.goto(`${BASE}/walk/${uk.id}`);
  await expect(
    page.getByRole("button", { name: en["walk.start"] }),
  ).toBeVisible();
  await expect(page.getByTestId("walk-seek-note")).toHaveCount(0);
  await page.getByRole("button", { name: en["walk.start"] }).click();
  const invasive = content.form.items.find(
    (i: { id: string }) => i.id === "invasive_species",
  );
  for (let i = 0; i < 40; i++) {
    const question = (await page.locator("h1#question").innerText()).trim();
    if (question === "Which ones?") break;
    if (question === invasive.text)
      await page
        .getByRole("button", { name: en["check.yes"], exact: true })
        .click();
    else if (
      await page
        .getByRole("button", { name: en["check.skip"], exact: true })
        .isVisible()
    )
      await page
        .getByRole("button", { name: en["check.skip"], exact: true })
        .click();
    else if (
      await page
        .getByRole("button", { name: en["check.none_of_these"], exact: true })
        .isVisible()
    )
      await page
        .getByRole("button", { name: en["check.none_of_these"], exact: true })
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
    else
      await page
        .getByRole("button", { name: en["check.next"], exact: true })
        .click();
    await page.waitForFunction(
      (q) => document.querySelector("h1#question")?.textContent?.trim() !== q,
      question,
    );
  }
  await expect(page.locator("h1#question")).toHaveText("Which ones?");
  const group = page.getByRole("main").getByRole("group");
  await expect(group.getByText(/Hedera helix/)).toHaveCount(0);
  await expect(group.getByRole("checkbox")).toHaveCount(1);
  await expect(group.getByLabel(en["check.not_sure"])).toBeVisible();
  await expect(
    page.getByRole("button", { name: en["check.none_of_these"], exact: true }),
  ).toBeVisible();
  const bayArea = content.regions["california-bay-area"].name;
  await expect(page.getByTestId("region-list-note")).toHaveText(
    en["check.region_list_elsewhere"].replace("{regions}", bayArea),
  );
});

// Audit finding phone-ux-languages-2: a walk answered in Portuguese read every answer back in
// English, with no English tag. The record now words each question and answer in the language
// the walk was taken in, in the official app's own words, and marks as English only what fell
// back to English. The expected words are worked out here from content.json, not from the screen.
type ShownWords = { text: string; lang: string; english: boolean };
type FormItemFull = {
  id: string;
  text: string;
  type: string;
  unit?: string;
  sliders?: string[];
  depends_on?: { item: string; value: string };
  options?: { id: string; value: string; label: string }[];
};
const fullItems: FormItemFull[] = content.form.items;

/** What the screen should show for one of the app's strings: the translation, or English marked. */
function wordsFor(
  lang: string,
  key: string,
  translated: string | undefined,
  english: string,
): ShownWords {
  if (lang === "en") return { text: english, lang: "en", english: false };
  const fellBack = Boolean(content.app_strings.fallback[lang]?.[key]);
  if (translated && !fellBack)
    return { text: translated, lang, english: false };
  return { text: english, lang: "en", english: true };
}

/** An answer's words on the question screen and in the record, in another language. */
function optionWords(lang: string, item: FormItemFull, id: string): ShownWords {
  const app = (l: string) => content.app_strings.strings[l].items[item.id];
  const own = (item.options ?? []).find((o) => o.id === id)?.label;
  return wordsFor(
    lang,
    `${item.id}.option:${id}`,
    app(lang)?.options?.[id],
    own ?? app("en")?.options?.[id],
  );
}

/**
 * Takes the walk on screen in `lang`, saying something on every screen: the first choice (or
 * `pick[item]`), Yes on a yes or no question, two habitats, the plant list's not sure answer, a
 * water height, and two feelings moved with a third marked not applicable. Returns each row the
 * record should hold: the question and the pieces of the answer.
 */
async function walkIn(
  page: Page,
  lang: string,
  pick: Record<string, string[]>,
): Promise<{ question: ShownWords; answer: ShownWords[]; text: string }[]> {
  const rows: { question: ShownWords; answer: ShownWords[]; text: string }[] =
    [];
  const answers: Record<string, string> = {};
  const button = (name: string) =>
    page.getByRole("button", { name, exact: true });
  const next = () => button(uiWords(lang, "next", en["check.next"]).text);
  for (const item of fullItems) {
    if (item.depends_on && answers[item.depends_on.item] !== item.depends_on.value)
      continue;
    const app = content.app_strings.strings[lang].items[item.id];
    const question = wordsFor(lang, `${item.id}.text`, app?.text, item.text);
    await expect(page.locator("h1#question > span").first()).toHaveText(
      question.text,
    );
    await expect(page.locator("h1#question > span").first()).toHaveAttribute(
      "lang",
      question.lang,
    );
    let answer: ShownWords[] = [];
    let text = "";
    if (item.type === "choice") {
      const id = pick[item.id]?.[0] ?? item.options![0].id;
      const w = optionWords(lang, item, id);
      answers[item.id] = item.options!.find((o) => o.id === id)!.value;
      answer = [w];
      text = w.text;
      await page
        .getByRole("group")
        .getByRole("button")
        .filter({ has: page.getByText(w.text, { exact: true }) })
        .first()
        .click();
    } else if (item.type === "yesno") {
      const w = optionWords(lang, item, "present");
      answers[item.id] = "present";
      answer = [w];
      text = w.text;
      await page
        .getByRole("group")
        .getByRole("button")
        .filter({ has: page.getByText(w.text, { exact: true }) })
        .first()
        .click();
    } else if (item.type === "multi") {
      const ids = pick[item.id] ?? [item.options![0].id];
      answer = ids.map((id) => optionWords(lang, item, id));
      text = answer.map((w) => w.text).join(", ");
      for (const w of answer)
        await page
          .locator("label.option")
          .filter({ has: page.getByText(w.text, { exact: true }) })
          .getByRole("checkbox")
          .check();
      await next().click();
    } else if (item.type === "pick_region_list") {
      const w = wordsFor(
        lang,
        `${item.id}.option:cant_tell`,
        app?.options?.cant_tell,
        en["check.not_sure"],
      );
      answer = [w];
      text = w.text;
      await page
        .locator("label.option")
        .filter({ has: page.getByText(w.text, { exact: true }) })
        .getByRole("checkbox")
        .check();
      await next().click();
    } else if (item.type === "number") {
      await page.locator(`input[name=${item.id}]`).fill("0.3");
      answer = [{ text: `0.3 ${item.unit}`, lang, english: false }];
      text = answer[0].text;
      await next().click();
    } else if (item.type === "sliders") {
      const moved = ["joy", "anger"];
      const parts: string[] = [];
      for (const s of item.sliders!) {
        const name = optionWords(lang, item, s);
        if (moved.includes(s)) {
          await page.locator(`#slider-${s}`).fill("3");
          answer.push(name, { text: "3", lang: name.lang, english: false });
          parts.push(`${name.text}: 3`);
        } else if (s === "fear") {
          const na = optionWords(lang, item, "not_applicable");
          await page
            .locator(".card")
            .filter({ has: page.locator(`#slider-${s}`) })
            .getByRole("checkbox")
            .check();
          answer.push(name, na);
          parts.push(`${name.text}: ${na.text}`);
        }
      }
      text = parts.join(", ");
      await next().click();
    }
    rows.push({ question, answer, text });
  }
  // The follow-ups the rules ask, and the checker's question, are left as they are.
  const done = page.getByRole("heading", {
    name: en["walk.done_title"],
    level: 1,
  });
  for (let i = 0; i < 4 && !(await done.isVisible()); i++) {
    const finish = button(en["check.finish"]);
    if (await finish.isVisible()) await finish.click();
    else await page.waitForTimeout(100);
  }
  await expect(done).toBeVisible();
  return rows;
}

/** A button of ours that the app has its own word for (scripts/app_strings.py UI). */
function uiWords(lang: string, key: string, english: string): ShownWords {
  return wordsFor(
    lang,
    `ui:${key}`,
    content.app_strings.strings[lang]?.ui?.[key],
    english,
  );
}

/** Checks the record's rows on screen against the rows the walk should have made. */
async function expectRows(
  page: Page,
  rows: { question: ShownWords; answer: ShownWords[]; text: string }[],
) {
  const lines = page.getByTestId("walk-answers").locator(".answer-line");
  await expect(lines).toHaveCount(rows.length);
  let tags = 0;
  for (const [i, row] of rows.entries()) {
    const line = lines.nth(i);
    const q = line.locator(".muted").first();
    await expect(q.locator("span[lang]").first()).toHaveText(row.question.text);
    await expect(q.locator("span[lang]").first()).toHaveAttribute(
      "lang",
      row.question.lang,
    );
    await expect(q.getByTestId("english-tag")).toHaveCount(
      row.question.english ? 1 : 0,
    );
    const pieces = line.locator("strong span[lang]:not([data-testid])");
    await expect(pieces).toHaveText(row.answer.map((w) => w.text));
    for (const [j, w] of row.answer.entries())
      await expect(pieces.nth(j)).toHaveAttribute("lang", w.lang);
    const marked = row.answer.filter((w) => w.english).length;
    await expect(line.locator("strong").getByTestId("english-tag")).toHaveCount(
      marked,
    );
    tags += marked + (row.question.english ? 1 : 0);
  }
  await expect(
    page.getByTestId("walk-answers").getByTestId("english-tag"),
  ).toHaveCount(tags);
  return tags;
}

for (const [lang, pick, fellBack] of [
  ["pt", {}, 3],
  ["nl", { habitats: ["sand_banks", "riffles"] }, 2],
  ["no", { habitats: ["sand_banks", "riffles"] }, 4],
] as const) {
  test(`a walk taken in ${lang} reads its answers back in ${lang}, with the English tag only where a string fell back`, async ({
    page,
  }) => {
    await mockApi(page, {});
    const w = walks[0];
    await page.goto(`${BASE}/walk/${w.id}`);
    await page.getByLabel(en["check.lang_label_short"]).selectOption(lang);
    await page.getByRole("button", { name: en["walk.start"] }).click();
    const rows = await walkIn(page, lang, pick as Record<string, string[]>);
    // The words are the app's own: the first row is its translation of the channel form.
    expect(rows[0].question.text).toBe(
      content.app_strings.strings[lang].items.channel_form.text,
    );
    expect(rows[0].answer[0].text).toBe(
      content.app_strings.strings[lang].items.channel_form.options.flat,
    );
    expect(rows[0].question.text).not.toBe(fullItems[0].text);
    const tags = await expectRows(page, rows);
    // Every string this walk showed that the meaning check sent back to English, and no other.
    expect(tags).toBe(fellBack);
    const feelings = rows.find((r) => r.text.includes(": 3"))!;
    await expect(
      page
        .getByTestId("walk-answers")
        .locator(".answer-line")
        .filter({ hasText: feelings.question.text })
        .locator("strong"),
    ).toContainText(feelings.text.split(",")[0]);
    // The record keeps the language the walk was taken in: another pick made later, and a
    // reload, leave its answers as they were given.
    await page.evaluate(() => localStorage.setItem("sl.check_lang", "fr"));
    await page.reload();
    await expect(
      page.getByRole("heading", { name: en["walk.done_title"], level: 1 }),
    ).toBeVisible();
    expect(await expectRows(page, rows)).toBe(fellBack);
  });
}

test("a walk taken in English reads back as before, with no English tag", async ({
  page,
}) => {
  await mockApi(page, {});
  await page.goto(`${BASE}/walk/${walks[0].id}`);
  await page.getByRole("button", { name: en["walk.start"] }).click();
  await answerWalkPlainly(page, content, { bank: "present" });
  const lines = page.getByTestId("walk-answers").locator(".answer-line");
  await expect(lines.first().locator("strong")).toHaveText("Flat");
  await expect(lines.first().locator("span[lang]").first()).toHaveAttribute(
    "lang",
    "en",
  );
  await expect(page.getByTestId("english-tag")).toHaveCount(0);
});

// Audit finding phone-ux-languages-5: on a walk the list of languages sat below Start and the
// demo notice, off the first screen, so a person could start a walk without ever seeing that it
// speaks their language. The list is now right under the walk's title, whole on the first
// screen of the phone profile, at the full tap height, and its note stays below Start. The test
// above still holds Start whole on the first screen at 390 by 844.
test("the list of languages is whole on the first screen of every walk, and its note comes after Start", async ({
  page,
}) => {
  const height = page.viewportSize()!.height;
  expect(height).toBeLessThanOrEqual(664);
  for (const w of walks) {
    await page.goto(`${BASE}/walk/${w.id}`);
    const list = page.getByLabel(en["check.lang_label_short"]);
    await expect(list).toBeVisible();
    await expect(list).toHaveValue("en");
    await page.evaluate(() => window.scrollTo(0, 0));
    const box = (await list.boundingBox())!;
    expect(box.y, w.id).toBeGreaterThanOrEqual(0);
    expect(box.y + box.height, w.id).toBeLessThanOrEqual(height);
    // A thumb's height, drawn by the page and not left to the browser's own small list.
    expect(box.height, w.id).toBeGreaterThanOrEqual(48);
    expect(await list.evaluate((e) => getComputedStyle(e).appearance)).toBe(
      "none",
    );
    // Under the title and above the clip.
    const title = (await page
      .getByRole("heading", { name: w.creek_name, level: 1 })
      .boundingBox())!;
    const clip = (await page.locator("video.walk-clip").boundingBox())!;
    expect(box.y).toBeGreaterThanOrEqual(title.y + title.height);
    expect(clip.y).toBeGreaterThanOrEqual(box.y + box.height + 8);
    // The note about whose words these are is kept, below Start.
    const note = (await page.getByTestId("language-note").boundingBox())!;
    const start = (await page
      .getByRole("button", { name: en["walk.start"] })
      .boundingBox())!;
    await expect(page.getByTestId("language-note")).toHaveText(
      en["check.lang_note"],
    );
    expect(note.y).toBeGreaterThan(start.y + start.height);
    await expect(page.locator("select")).toHaveCount(1);
  }
  // The list is for choosing before the walk starts: a question screen has none.
  await page.getByLabel(en["check.lang_label_short"]).selectOption("it");
  await page.getByRole("button", { name: en["walk.start"] }).click();
  await expect(page.locator("h1#question > span[lang=it]")).toHaveText(
    content.app_strings.strings.it.items.channel_form.text,
  );
  await expect(page.locator("select")).toHaveCount(0);
});
    // WCAG 3.3.2: the list has a label a sighted person can read, right above it, and Start the
    // check is still whole on this first screen with the label there.
    const label = page.getByText(en["check.lang_label_short"], { exact: true });
    await expect(label).toBeVisible();
    expect(en["check.lang_label_short"]).toBe("Questions in");
    const labelBox = (await label.boundingBox())!;
    expect(labelBox.y + labelBox.height, w.id).toBeLessThanOrEqual(box.y);
    expect(start.y + start.height, w.id).toBeLessThanOrEqual(height);
