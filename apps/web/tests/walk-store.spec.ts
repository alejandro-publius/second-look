import { devices, expect, test, type Browser, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { walkBundle } from "../../../worker/src/core/walks";
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
const en: Record<string, string> = content.locale;
const walk: { id: string; creek_name: string; spot_name: string } = content.walks[0];
const items: { id: string; text: string; type: string; options?: { label: string }[] }[] = content.form.items;
const feature = (id: string) => content.features.find((f: { id: string }) => f.id === id).name as string;

/** The record's Bundle as the store builds it: the same port of core/walks.py the Worker runs. */
const bundleFor = (walkId: string, answers: Record<string, AnswerValue>, answeredAt: string) => {
  const w = content.walks.find((x: { id: string }) => x.id === walkId);
  return walkBundle({ id: w.id, spot_name: w.spot_name, creek_name: w.creek_name }, answers, answeredAt);
};

async function freshPage(browser: Browser, walkStore: Map<string, unknown>): Promise<Page> {
  const context = await browser.newContext({ ...devices["iPhone 13"], serviceWorkers: "block" });
  const page = await context.newPage();
  await mockApi(page, { walkStore, walkBundle: bundleFor });
  return page;
}

async function question(page: Page) {
  return (await page.locator("h1#question").innerText()).trim();
}

/** Waits until IndexedDB holds this walk with `count` answers, as lib/offline.ts keeps it. A
 * person takes longer than the write does; a test that reloads at once must wait for it. */
async function kept(page: Page, walkId: string, count: number) {
  await page.waitForFunction(
    ([id, n]) =>
      new Promise<boolean>((resolve) => {
        const open = indexedDB.open("second-look");
        open.onerror = () => resolve(false);
        open.onsuccess = () => {
          const db = open.result;
          if (!db.objectStoreNames.contains("walks")) return resolve(false);
          const get = db.transaction("walks").objectStore("walks").get(id as string);
          get.onsuccess = () => resolve(Object.keys(get.result?.answers ?? {}).length === n);
          get.onerror = () => resolve(false);
        };
      }),
    [walkId, count] as const,
  );
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
  // Its curl line fetches the stored copy.
  await expect(page.locator("pre.code").first()).toHaveText(`curl -s http://127.0.0.1:8100/api/walk/${recordId}`);

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
  await expect(page.getByText(en["city.walk_empty"])).toBeVisible();
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
  await expect(page.getByRole("button", { name: en["walk.start"] })).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: en["walk.start"] }).click();
  await expect(page.locator("h1#question")).toHaveText(items[0].text);
  await expect(page.getByRole("button", { name: items[0].options![1].label, exact: true })).toHaveAttribute("aria-pressed", "false");
  expect(await question(page)).toBe(items[0].text);
});
