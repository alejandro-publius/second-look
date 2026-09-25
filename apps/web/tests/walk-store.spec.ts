import { devices, expect, test, type Browser, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fill } from "../../../worker/src/core/labels";
import { walkBundle, walkChecks, walkFollowups } from "../../../worker/src/core/walks";
import type { AnswerValue } from "../../../worker/src/core/types";
import { answerWalkPlainly } from "../scripts/gallery-walk.mjs";
import { mockApi } from "./mock-api.mjs";
import { BASE } from "./helpers";

// UPDATE_30 section 1 items 2 and 3. A walk's answers wait in IndexedDB beside the creek check's
// offline queue, keyed by the walk's id, so the browser's Back, a reload or a closed tab opens the
// walk on its next unanswered question with the earlier answers in place. A finished walk goes
// through that queue to the store, which keeps it as a demo record, so its link opens in another
// browser, on /spot?id=<id> and on /city under the walk's demo creek.
const content = JSON.parse(readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"));
// The follow-up table and the form as the ports read them, as worker/src/core/core_content.json holds them.
const CORE = JSON.parse(readFileSync(join(__dirname, "..", "..", "..", "worker", "src", "core", "core_content.json"), "utf8"));
const en: Record<string, string> = content.locale;
const walk: { id: string; creek_name: string; spot_name: string } = content.walks[0];
const items: { id: string; text: string; type: string; options?: { label: string }[] }[] = content.form.items;
const feature = (id: string) => content.features.find((f: { id: string }) => f.id === id).name as string;

/** The record's Bundle as the store builds it: the same port of core/walks.py the Worker runs. */
const bundleFor = (walkId: string, answers: Record<string, AnswerValue>, answeredAt: string, finalRating: string | null = null) => {
  const w = content.walks.find((x: { id: string }) => x.id === walkId);
  return walkBundle({ id: w.id, spot_name: w.spot_name, creek_name: w.creek_name }, answers, answeredAt, finalRating);
};

/** The overall rating a record's QuestionnaireResponse answers, and that response's text. */
const ratingIn = (bundle: { entry: { resource: Record<string, unknown> }[] }) => {
  const qr = bundle.entry.map((e) => e.resource).find((r) => r.resourceType === "QuestionnaireResponse") as {
    item: { linkId: string; answer: { valueCoding: { code: string } }[] }[];
    text: { div: string };
  };
  return { code: qr.item.find((i) => i.linkId === "overall_rating")!.answer[0].valueCoding.code, text: qr.text.div };
};

/** The checks the store keeps with a walk (judge walk W01), as worker/src/walk_store.ts makes them:
 *  the rules through the same port, each question filled from the locale as questionText fills it. */
const storeChecks = (answers: Record<string, AnswerValue>, given: Record<string, unknown>, finalRating: string | null) => {
  const chosen = walkFollowups(answers, CORE.followups as Record<string, unknown>, CORE.form_items as never);
  const out = walkChecks(answers, chosen, chosen.map((f) => fill(en[f.question_key], f.params)), given, finalRating);
  return { checks: out.checks, first_rating: typeof answers.overall_rating === "string" ? answers.overall_rating : null, final_rating: out.final_rating };
};

async function freshPage(browser: Browser, walkStore: Map<string, unknown>): Promise<Page> {
  const context = await browser.newContext({ ...devices["iPhone 13"], serviceWorkers: "block" });
  const page = await context.newPage();
  await mockApi(page, { walkStore, walkBundle: bundleFor, walkChecks: storeChecks });
  return page;
}

async function question(page: Page) {
  return (await page.locator("h1#question").innerText()).trim();
}

/** Waits until IndexedDB holds this walk with `count` answers, as lib/offline.ts keeps it. A
 * person takes longer than the write does; a test that reloads at once must wait for it. */
async function kept(page: Page, walkId: string, count: number) {
  // page.evaluate waits for the promise; waitForFunction would take the promise itself as a yes.
  const answers = () =>
    page.evaluate(
      (id) =>
        new Promise<number>((resolve) => {
          const open = indexedDB.open("second-look");
          open.onerror = () => resolve(-1);
          open.onsuccess = () => {
            const db = open.result;
            if (!db.objectStoreNames.contains("walks")) {
              db.close();
              return resolve(-1);
            }
            const get = db.transaction("walks").objectStore("walks").get(id);
            get.onsuccess = () => {
              db.close();
              resolve(Object.keys(get.result?.answers ?? {}).length);
            };
            get.onerror = () => resolve(-1);
          };
        }),
      walkId,
    );
  await expect.poll(answers, { timeout: 10_000 }).toBe(count);
}

test("four answers survive Back and a reload, and the walk opens on the next question", async ({ page }) => {
  await mockApi(page, {});
  await page.goto(`${BASE}/walk`);
  await page.getByRole("link", { name: walk.creek_name, exact: true }).click();
  await expect(page).toHaveURL(`${BASE}/walk/${walk.id}`);
  await page.getByRole("button", { name: en["walk.start"] }).click();

  // Four answers, each a different one from the first choice, so a default cannot pass for one.
  const [q1, q2, q3, q4, q5] = items;
  expect([q1.type, q2.type, q3.type, q4.type]).toEqual(["choice", "choice", "choice", "multi"]);
  const picks = [q1.options![1].label, q2.options![1].label, q3.options![2].label];
  for (const [i, label] of picks.entries()) {
    await expect(page.locator("h1#question")).toHaveText(items[i].text);
    await page.getByRole("button", { name: label, exact: true }).click();
  }
  await expect(page.locator("h1#question")).toHaveText(q4.text);
  const ticked = [q4.options![0].label, q4.options![3].label];
  for (const label of ticked) await page.getByLabel(label, { exact: true }).check();
  await page.getByRole("button", { name: en["check.next"], exact: true }).click();
  await expect(page.locator("h1#question")).toHaveText(q5.text);
  await kept(page, walk.id, 4);

  // The browser's Back leaves the walk page, and the reload starts that page from nothing.
  await page.goBack();
  await expect(page).toHaveURL(`${BASE}/walk`);
  await page.reload();
  await page.goForward();
  await expect(page).toHaveURL(`${BASE}/walk/${walk.id}`);

  // Back on the fifth question, with a line that says so, and the four answers behind it.
  await expect(page.locator("h1#question")).toHaveText(q5.text);
  await expect(page.getByTestId("walk-resumed")).toHaveText(en["walk.resumed"]);
  await page.getByRole("button", { name: en["check.back"], exact: true }).click();
  await expect(page.locator("h1#question")).toHaveText(q4.text);
  for (const label of ticked) await expect(page.getByLabel(label, { exact: true })).toBeChecked();
  await expect(page.getByLabel(q4.options![1].label, { exact: true })).not.toBeChecked();
  for (let i = 2; i >= 0; i--) {
    await page.getByRole("button", { name: en["check.back"], exact: true }).click();
    await expect(page.locator("h1#question")).toHaveText(items[i].text);
    await expect(page.getByRole("button", { name: picks[i], exact: true })).toHaveAttribute("aria-pressed", "true");
  }

  // A closed tab too: a new tab in the same browser opens the walk on the fifth question.
  const context = page.context();
  await page.close();
  const tab = await context.newPage();
  await mockApi(tab, {});
  await tab.goto(`${BASE}/walk/${walk.id}`);
  await expect(tab.locator("h1#question")).toHaveText(q5.text);
});

test("a phone with the old offline queue keeps its queued check when the walks store is added", async ({ page }) => {
  await mockApi(page, {});
  // The database as the app left it before UPDATE_30: version 1, the queue store only, one check
  // the server refused, so no page tries to send it again.
  await page.goto(`${BASE}/about`);
  await page.evaluate(
    () =>
      new Promise<void>((resolve, reject) => {
        const open = indexedDB.open("second-look", 1);
        open.onupgradeneeded = () => open.result.createObjectStore("queue", { keyPath: "id", autoIncrement: true });
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
          const t = open.result.transaction("queue", "readwrite");
          t.objectStore("queue").add({ kind: "quick", created_at: "2026-09-24T10:00:00Z", photos: [], status: "failed", error: "kept for the test" });
          t.oncomplete = () => {
            open.result.close();
            resolve();
          };
        };
      }),
  );
  await page.goto(`${BASE}/walk/${walk.id}`);
  await page.getByRole("button", { name: en["walk.start"] }).click();
  await page.getByRole("button", { name: items[0].options![1].label, exact: true }).click();
  await kept(page, walk.id, 1);
  const db = await page.evaluate(
    () =>
      new Promise<{ version: number; queued: string[] }>((resolve) => {
        const open = indexedDB.open("second-look");
        open.onsuccess = () => {
          const all = open.result.transaction("queue").objectStore("queue").getAll();
          all.onsuccess = () => resolve({ version: open.result.version, queued: all.result.map((q: { error?: string }) => q.error ?? "") });
        };
      }),
  );
  expect(db).toEqual({ version: 2, queued: ["kept for the test"] });
});

test("a finished walk's record link opens in a fresh browser, on /spot and on /city under the demo creek", async ({ page, browser }) => {
  const walkStore = new Map<string, unknown>();
  const calls = await mockApi(page, { walkStore, walkBundle: bundleFor });
  await page.goto(`${BASE}/walk/${walk.id}`);
  await page.getByRole("button", { name: en["walk.start"] }).click();
  await answerWalkPlainly(page, content, { bank: "present" });
  const link = page.getByTestId("walk-record-link");
  await expect(link).toHaveText(en["walk.stored_link"]);
  const href = (await link.getAttribute("href"))!;
  expect(href).toMatch(/^\/spot\?id=walk-[0-9a-f]{16}$/);
  const recordId = href.split("=")[1];
  const rows = await page.getByTestId("walk-answers").locator(".answer-line").allInnerTexts();
  await page.getByRole("button", { name: en["spot.view_fhir"] }).click();
  const made = JSON.parse(await page.locator("pre.code").last().innerText());
  // The phone sent the walk once, to the walk store, and nothing to the creek check's routes.
  const sent = calls.filter((c: { method: string }) => c.method === "POST").map((c: { path: string }) => c.path);
  expect(sent).toEqual(["/api/walk"]);
  // Its curl line fetches the stored copy's Bundle, the FHIR itself (critic round 14 B04).
  await expect(page.locator("pre.code").first()).toHaveText(`curl -s http://127.0.0.1:8100/api/walk/${recordId}/fhir`);

  // Another browser, with nothing of the first one's: the record, the same answers, the same FHIR.
  const other = await freshPage(browser, walkStore);
  await other.goto(`${BASE}${href}`);
  await expect(other.getByRole("heading", { name: en["walk.stored_title"], level: 1 })).toBeVisible();
  await expect(other.getByTestId("walk-stored-notice")).toContainText("never counted");
  await expect(other.getByTestId("walk-structure")).toHaveText(en["walk.structure_ok"]);
  expect(await other.getByTestId("walk-answers").locator(".answer-line").allInnerTexts()).toEqual(rows);
  await other.getByRole("button", { name: en["spot.view_fhir"] }).click();
  await expect(other.getByTestId("fhir-badge")).toContainText("This one was not checked.");
  const stored = JSON.parse(await other.locator("pre.code").last().innerText());
  expect(stored).toEqual(made);
  expect(stored.meta.tag.some((t: { code: string }) => t.code === "demo-walk")).toBe(true);

  // Its demo creek on /city, from the record the link names: the built bank it reported.
  await other.getByRole("link", { name: en["walk.city_link"] }).click();
  await expect(other).toHaveURL(`${BASE}/city?walk=${walk.id}&record=${recordId}`);
  await expect(other.getByRole("heading", { name: en["city.walk_title"].replace("{name}", walk.creek_name), level: 1 })).toBeVisible();
  await expect(other.getByText(en["city.walk_visits"].replace("{n}", "1"))).toBeVisible();
  const found = other.getByRole("region", { name: en["city.walk_findings"] });
  await expect(found.locator(".row")).toHaveText([`${feature("artificial_bank")}${en["city.walk_seen"].replace("{n}", "1")}`]);
  await expect(other.getByRole("main").getByRole("link", { name: en["city.walk_back_stored"], exact: true })).toHaveAttribute("href", `/spot?id=${recordId}`);
  await other.context().close();
});

// Judge walk W01: the walk is the same creek check, so it runs the creek check's follow-up rules
// on its answers. Overall Good with an artificial bank is the rating check's trigger; a clip has no
// weather, so the dry pipe question is never asked. The question shows as the creek check shows
// it, the answer goes to the store with the walk, and "Checks that ran" shows on the phone's
// record and on the stored one, as /spot shows it for a creek check.
test("a walk asks the rating check, keeps the answer, and shows the checks that ran on both records", async ({ page, browser }) => {
  const walkStore = new Map<string, unknown>();
  const calls = await mockApi(page, { walkStore, walkBundle: bundleFor, walkChecks: storeChecks });
  await page.goto(`${BASE}/walk/${walk.id}`);
  await page.getByRole("button", { name: en["walk.start"] }).click();
  await answerWalkPlainly(page, content, { bank: "present", until: "followups" });
  const asked = page.getByTestId("walk-followups");
  // One question, so one follow-up, not "One or two" (critic round 14 B04, round 15 F06).
  await expect(asked.getByRole("heading", { name: en["check.followups_title_one"] })).toBeVisible();
  await expect(asked).toContainText(en["check.followups_intro"]);
  const question = fill(en["followup.rating_check"], { issues: "artificial banks" });
  // The card is named by its check's plain name, never by the rule's code name.
  await expect(asked.getByRole("region", { name: en["spot.rule_rating_check"] })).toContainText(question);
  await expect(asked.getByRole("region", { name: "rating_check" })).toHaveCount(0);
  await expect(asked.locator('[data-rule="dry_pipe"]')).toHaveCount(0);
  expect(calls.filter((c: { method: string }) => c.method === "POST")).toEqual([]);
  await asked.getByRole("button", { name: en["check.change_rating"] }).click();
  await asked.getByRole("button", { name: /^Poor:/ }).click();
  await expect(asked.getByTestId("rating-chosen")).toHaveText(fill(en["check.rating_new"], { rating: en["spot.rating_word_poor"] }));
  await asked.getByRole("button", { name: en["check.finish"], exact: true }).click();

  // The phone's record: the checks that ran, worded as /spot words them.
  await expect(page.getByRole("heading", { name: en["walk.done_title"], level: 1 })).toBeVisible();
  const ran = page.getByTestId("checks-ran");
  await expect(ran.getByRole("heading", { name: en["spot.checks"], level: 2 })).toBeVisible();
  const outcome = fill(en["spot.outcome_changed"], { from: en["spot.rating_word_good"], to: en["spot.rating_word_poor"] });
  await expect(ran.locator("li")).toHaveText([`${en["spot.rule_rating_check"]}${question}${outcome}`]);
  // Sent with the walk, and only what the store takes.
  await expect(page.getByTestId("walk-record-link")).toBeVisible();
  const post = calls.find((c: { method: string; path: string }) => c.method === "POST" && c.path === "/api/walk")!;
  expect(post.body.followup_answers).toEqual({ rating_check: "change" });
  expect(post.body.final_rating).toBe("poor");

  // Critic round 15 F02: View as FHIR on the phone answers the rating question with Poor, the
  // rating kept, and names the first rating; it no longer answers Good.
  await page.getByRole("button", { name: en["spot.view_fhir"] }).click();
  const made = JSON.parse(await page.locator("pre.code").last().innerText());
  expect(ratingIn(made).code).toBe("poor");
  expect(ratingIn(made).text).toContain("The first overall rating was good.");

  // The stored record, in another browser: the same checks, and the same FHIR record.
  const href = (await page.getByTestId("walk-record-link").getAttribute("href"))!;
  const other = await freshPage(browser, walkStore);
  await other.goto(`${BASE}${href}`);
  await expect(other.getByRole("heading", { name: en["walk.stored_title"], level: 1 })).toBeVisible();
  await expect(other.getByTestId("checks-ran").locator("li")).toHaveText([`${en["spot.rule_rating_check"]}${question}${outcome}`]);
  await other.getByRole("button", { name: en["spot.view_fhir"] }).click();
  const stored = JSON.parse(await other.locator("pre.code").last().innerText());
  expect(ratingIn(stored).code).toBe("poor");
  expect(stored).toEqual(made);
  await other.context().close();
});

test("a walk whose answers call for no follow-up goes straight to its record, with no checks", async ({ page }) => {
  const walkStore = new Map<string, unknown>();
  const calls = await mockApi(page, { walkStore, walkBundle: bundleFor, walkChecks: storeChecks });
  await page.goto(`${BASE}/walk/${walk.id}`);
  await page.getByRole("button", { name: en["walk.start"] }).click();
  await answerWalkPlainly(page, content, { bank: "absent", until: "followups" });
  await expect(page.getByRole("heading", { name: en["walk.done_title"], level: 1 })).toBeVisible();
  await expect(page.getByTestId("walk-followups")).toHaveCount(0);
  await expect(page.getByTestId("checks-ran")).toHaveCount(0);
  await expect(page.getByTestId("walk-record-link")).toBeVisible();
  const post = calls.find((c: { method: string; path: string }) => c.method === "POST" && c.path === "/api/walk")!;
  expect(post.body.followup_answers).toEqual({});
  expect(post.body.final_rating).toBeNull();
});

test("the walk's demo creek in a new tab of the same browser shows the walk, counted once", async ({ page }) => {
  const walkStore = new Map<string, unknown>();
  await mockApi(page, { walkStore, walkBundle: bundleFor });
  await page.goto(`${BASE}/walk/${walk.id}`);
  await page.getByRole("button", { name: en["walk.start"] }).click();
  await answerWalkPlainly(page, content, { bank: "present" });
  await expect(page.getByTestId("walk-record-link")).toBeVisible();
  const city = await page.getByRole("link", { name: en["walk.city_link"] }).getAttribute("href");
  expect(city).toMatch(new RegExp(`^/city\\?walk=${walk.id}&record=walk-[0-9a-f]{16}$`));
  const tab = await page.context().newPage();
  await mockApi(tab, { walkStore, walkBundle: bundleFor });
  // Both the bare link and the one that names the stored record: the same one walk, once.
  for (const url of [`/city?walk=${walk.id}`, city!]) {
    await tab.goto(`${BASE}${url}`);
    await expect(tab.getByText(en["city.walk_visits"].replace("{n}", "1"))).toBeVisible();
    await expect(tab.getByRole("main").getByRole("link", { name: en["city.walk_back"], exact: true })).toHaveAttribute("href", `/walk/${walk.id}`);
    await expect(tab.getByTestId("walk-record-missing")).toHaveCount(0);
  }
});

test("a link to a walk record that is gone says so, on /spot and on /city", async ({ page }) => {
  await mockApi(page, {});
  await page.goto(`${BASE}/spot?id=walk-0000000000000000`);
  await expect(page.getByRole("heading", { name: en["walk.stored_title"], level: 1 })).toBeVisible();
  await expect(page.getByText(/deleted 30 days after it is stored/)).toBeVisible();
  await page.goto(`${BASE}/city?walk=${walk.id}&record=walk-0000000000000000`);
  await expect(page.getByTestId("walk-record-missing")).toContainText("deleted 30 days after it is stored");
  await expect(page.getByTestId("walk-city-empty")).toHaveText(en["city.walk_empty"].replace("{link}", en["city.walk_empty_link"]));
});

test("a walk the store refuses keeps its record on the page and says why", async ({ page }) => {
  await mockApi(page, { walkRefuse: { status: 429, detail: "The demo store has taken all the walks it can for today." } });
  await page.goto(`${BASE}/walk/${walk.id}`);
  await page.getByRole("button", { name: en["walk.start"] }).click();
  await answerWalkPlainly(page, content, { bank: "absent" });
  await expect(page.getByTestId("walk-stored")).toContainText("The demo store has taken all the walks it can for today.");
  await expect(page.getByTestId("walk-record-link")).toHaveCount(0);
  await expect(page.getByTestId("walk-structure")).toHaveText(en["walk.structure_ok"]);
  // Not stored, so no web address to copy: the FHIR view says so.
  await page.getByRole("button", { name: en["spot.view_fhir"] }).click();
  await expect(page.getByText(en["walk.no_curl"])).toBeVisible();
  await expect(page.getByRole("button", { name: en["spot.curl"] })).toHaveCount(0);
});

test("a walk finished with no network is stored when the network comes back", async ({ page }) => {
  const offline = { value: false };
  await mockApi(page, { offline });
  await page.goto(`${BASE}/walk/${walk.id}`);
  await page.getByRole("button", { name: en["walk.start"] }).click();
  offline.value = true;
  await answerWalkPlainly(page, content, { bank: "absent" });
  await expect(page.getByTestId("walk-stored")).toContainText(en["walk.stored_waiting"]);
  await expect(page.getByTestId("walk-record-link")).toHaveCount(0);
  // Closed and opened again while still offline: the walk opens on its record, still waiting.
  await page.reload();
  await expect(page.getByTestId("walk-stored")).toContainText(en["walk.stored_waiting"]);
  offline.value = false;
  await page.getByRole("button", { name: en["walk.stored_retry"] }).click();
  await expect(page.getByTestId("walk-record-link")).toHaveAttribute("href", /^\/spot\?id=walk-[0-9a-f]{16}$/);
});

test("Start again forgets the walk on this device, and a new walk starts from the first question", async ({ page }) => {
  await mockApi(page, {});
  await page.goto(`${BASE}/walk/${walk.id}`);
  await page.getByRole("button", { name: en["walk.start"] }).click();
  await page.getByRole("button", { name: items[0].options![1].label, exact: true }).click();
  await expect(page.locator("h1#question")).toHaveText(items[1].text);
  await kept(page, walk.id, 1);
  await page.reload();
  await expect(page.locator("h1#question")).toHaveText(items[1].text);
  // The first question's Back returns to the clip; a finished walk's Start again clears it all.
  await answerWalkPlainly(page, content, { bank: "absent" });
  await page.getByRole("button", { name: en["walk.start_again"], exact: true }).click();
  await page.getByRole("button", { name: en["walk.start_again_yes"], exact: true }).click();
  await expect(page.getByRole("button", { name: en["walk.start"] })).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: en["walk.start"] }).click();
  await expect(page.locator("h1#question")).toHaveText(items[0].text);
  await expect(page.getByRole("button", { name: items[0].options![1].label, exact: true })).toHaveAttribute("aria-pressed", "false");
  expect(await question(page)).toBe(items[0].text);
});

// Critic round 14 B02 and round 15 F03: the rating card looked the same before and after a tap. Keep
// was filled orange from the start, so it looked chosen, and after Change and a new rating the
// picker closed with nothing to show for it. Now Keep and Change look the same until one is
// pressed, the pressed one is marked as a pick, and the card says which rating the record keeps.
test("the rating card shows which answer was picked and the rating the record keeps", async ({ page }) => {
  // No colour fades, so each look is read when it has settled.
  await page.emulateMedia({ reducedMotion: "reduce" });
  await mockApi(page, { walkBundle: bundleFor, walkChecks: storeChecks });
  await page.goto(`${BASE}/walk/${walk.id}`);
  await page.getByRole("button", { name: en["walk.start"] }).click();
  await answerWalkPlainly(page, content, { bank: "present", until: "followups" });
  const card = page.getByRole("region", { name: en["spot.rule_rating_check"] });
  const keep = card.getByRole("button", { name: en["check.keep_rating"] });
  const change = card.getByRole("button", { name: en["check.change_rating"] });
  const look = (b: typeof keep) => b.evaluate((el) => { const s = getComputedStyle(el); return [s.backgroundColor, s.borderTopColor, s.boxShadow, s.color].join(" | "); });
  await page.mouse.move(0, 0);
  const before = [await look(keep), await look(change)];
  expect(before[0], "Keep and Change look the same before a tap").toBe(before[1]);
  await expect(card.getByTestId("rating-chosen")).toHaveText("");

  await change.click();
  await card.getByRole("button", { name: /^Moderate:/ }).click();
  await page.mouse.move(0, 0);
  await expect(change).toHaveAttribute("aria-pressed", "true");
  await expect(card.getByTestId("rating-chosen")).toHaveText(fill(en["check.rating_new"], { rating: en["spot.rating_word_moderate"] }));
  expect(await look(change), "the pressed answer is marked").not.toBe(before[1]);
  expect(await look(keep), "the other one is not").toBe(before[0]);

  await keep.click();
  await page.mouse.move(0, 0);
  await expect(keep).toHaveAttribute("aria-pressed", "true");
  await expect(card.getByTestId("rating-chosen")).toHaveText(fill(en["check.rating_kept"], { rating: en["spot.rating_word_good"] }));
  expect(await look(keep)).not.toBe(before[0]);
  expect(await look(change)).toBe(before[1]);
});

// Critic round 15 Y02: one tap on Start again dropped a finished walk's record, and the only place
// its link was shown, with no warning. It now asks first, says what goes and what stays, and Keep
// this walk leaves everything as it was.
test("Start again on a finished walk asks first, and says the stored record stays at its link", async ({ page }) => {
  const walkStore = new Map<string, unknown>();
  await mockApi(page, { walkStore, walkBundle: bundleFor });
  await page.goto(`${BASE}/walk/${walk.id}`);
  await page.getByRole("button", { name: en["walk.start"] }).click();
  await answerWalkPlainly(page, content, { bank: "absent" });
  await expect(page.getByTestId("walk-record-link")).toBeVisible();
  await page.getByRole("button", { name: en["walk.start_again"], exact: true }).click();
  const warn = page.getByTestId("walk-start-again-warn");
  await expect(warn).toContainText(en["walk.start_again_warn"]);
  await expect(warn).toContainText(/The stored record still opens at its link until \w{3} \d{1,2}, \d{4}\./);
  await expect(page.getByRole("button", { name: en["walk.start_again_no"], exact: true })).toBeFocused();
  await page.getByRole("button", { name: en["walk.start_again_no"], exact: true }).click();
  await expect(warn).toHaveCount(0);
  await expect(page.getByTestId("walk-record-link")).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("walk-record-link")).toBeVisible();
});

// Critic rounds 14 and 15 O02: in a fresh tab the demo creek said "Do the walk first" with no way
// to the walk, and an unknown walk showed one line with no heading and no link.
test("the walk's demo creek links to the walk in a fresh tab, and an unknown walk says so with a way on", async ({ page }) => {
  await mockApi(page, {});
  await page.goto(`${BASE}/city?walk=${walk.id}`);
  const empty = page.getByTestId("walk-city-empty");
  await expect(empty).toHaveText(en["city.walk_empty"].replace("{link}", en["city.walk_empty_link"]));
  await expect(empty.getByRole("link", { name: en["city.walk_empty_link"] })).toHaveAttribute("href", `/walk/${walk.id}`);
  await page.goto(`${BASE}/city?walk=v99`);
  await expect(page.getByRole("heading", { level: 1, name: en["city.walk_unknown_title"] })).toBeVisible();
  await expect(page.getByText(en["city.walk_unknown"])).toBeVisible();
  await expect(page.getByRole("main").getByRole("link", { name: en["walk.list_title"] })).toHaveAttribute("href", "/walk");
});

// Critic round 15 O02 item 4: a reloaded finished walk painted an empty clip frame under the
// heading while it opened. Nothing but the heading and the opening line shows until it knows.
test("a finished walk opens on its record with no clip painted first", async ({ page }) => {
  await mockApi(page, {});
  await page.goto(`${BASE}/walk/${walk.id}`);
  await page.getByRole("button", { name: en["walk.start"] }).click();
  await answerWalkPlainly(page, content, { bank: "absent" });
  await expect(page.getByTestId("walk-record-link")).toBeVisible();
  await page.addInitScript(() => {
    const seen: boolean[] = [];
    (window as unknown as { __clipSeen: boolean[] }).__clipSeen = seen;
    new MutationObserver(() => {
      if (document.querySelector("video.walk-clip")) seen.push(true);
    }).observe(document, { childList: true, subtree: true });
  });
  await page.reload();
  await expect(page.getByTestId("walk-record-link")).toBeVisible();
  expect(await page.evaluate(() => (window as unknown as { __clipSeen: boolean[] }).__clipSeen.length)).toBe(0);
});
