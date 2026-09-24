import { expect, test, type Page } from "@playwright/test";
import { PANEL_COMPLETION_CODE } from "../lib/panel";
import { mockApi, watchRequests } from "./mock-api.mjs";
import { answerAllItems, BASE, finishLesson, passConsent, pickWarmup } from "./helpers";

// The panel study (UPDATE_29 section 1, docs/internal/PANEL_STUDY.md). A panel appends its own
// identifiers to the link; only src may survive, nothing else may be stored or sent, the consent
// screen adds one sentence and the end screen shows the completion code, for that source only.
const PANEL_SENTENCE =
  "You are taking part through a research panel and will be paid by the panel; nothing that identifies you is stored here.";

async function toScore(page: Page) {
  await passConsent(page);
  await pickWarmup(page);
  await finishLesson(page);
  await answerAllItems(page, (i) => (i % 2 ? "Yes" : "No"));
  await expect(page.getByRole("heading", { name: "Almost done" })).toBeVisible();
  await page.getByLabel("No", { exact: true }).check();
  await page.getByRole("button", { name: "See my score" }).click();
  await expect(page.getByRole("heading", { name: "Your score" })).toBeVisible();
}

test("panel: identifiers stripped, the sentence on consent, the code after the score", async ({ page }) => {
  const urls = watchRequests(page);
  const calls = await mockApi(page, { lessonFirst: true });
  await page.goto("/t?src=panel&PROLIFIC_PID=pid5f3a9&STUDY_ID=study77&SESSION_ID=sess42");
  await expect(page.getByRole("heading", { name: "Before you start" })).toBeVisible();
  // Only src is left in the address bar, before anything is stored.
  await expect.poll(() => page.url()).toBe(`${BASE}/t?src=panel`);
  await expect(page.getByTestId("consent-panel")).toHaveText(PANEL_SENTENCE);

  await toScore(page);
  const session = calls.find((c) => c.path === "/api/test/session")!.body;
  expect(session.source_label).toBe("panel");
  await expect(page.getByTestId("panel-code")).toContainText(PANEL_COMPLETION_CODE);

  // No panel identifier reached an API call, a request body, any request after the page itself, or
  // storage. The first request is the browser loading the page from the panel's link, before any of
  // our code runs; docs/internal/PANEL_STUDY.md says so.
  expect(urls[0]).toContain("PROLIFIC_PID");
  const everything = JSON.stringify(calls) + urls.slice(1).join(" ") + (await page.evaluate(() => JSON.stringify({ ...sessionStorage }) + JSON.stringify({ ...localStorage })));
  for (const id of ["pid5f3a9", "study77", "sess42", "PROLIFIC_PID", "STUDY_ID", "SESSION_ID"]) {
    expect(everything).not.toContain(id);
  }
});

// The service worker caches every page it fetches (public/sw.js). Opened a second time, the panel's
// link goes through it, and its cache key must not keep the panel's identifiers (REVIEW_03 R03).
test.describe("with the service worker running", () => {
  test.use({ serviceWorkers: "allow" });

  test("a panel link opened twice leaves no panel identifier in any cache", async ({ page }) => {
    await mockApi(page, { lessonFirst: true });
    const link = "/t?src=panel&PROLIFIC_PID=pid5f3a9&STUDY_ID=study77&SESSION_ID=sess42";
    await page.goto(link);
    await expect(page.getByRole("heading", { name: "Before you start" })).toBeVisible();
    await expect.poll(() => page.evaluate(() => navigator.serviceWorker.controller !== null), { timeout: 30_000 }).toBe(true);
    await page.goto(link);
    await expect(page.getByRole("heading", { name: "Before you start" })).toBeVisible();
    const cached = () =>
      page.evaluate(async () => {
        const urls: string[] = [];
        for (const name of await caches.keys()) {
          const cache = await caches.open(name);
          for (const req of await cache.keys()) urls.push(`${name} ${req.url}`);
        }
        return urls;
      });
    // The second visit's page lands in the runtime cache, under some key for /t.
    await expect.poll(async () => (await cached()).filter((u) => /-runtime \S+\/t(\?|$)/.test(u)).length, { timeout: 15_000 }).toBeGreaterThan(0);
    const all = (await cached()).join(" ");
    for (const id of ["pid5f3a9", "study77", "sess42", "PROLIFIC_PID", "STUDY_ID", "SESSION_ID"]) {
      expect(all).not.toContain(id);
    }
  });
});

test("not panel: no sentence and no code, and other query parameters are stripped too", async ({ page }) => {
  const calls = await mockApi(page, { lessonFirst: true });
  await page.goto("/t?src=poster&utm_source=x");
  await expect(page.getByRole("heading", { name: "Before you start" })).toBeVisible();
  await expect.poll(() => page.url()).toBe(`${BASE}/t?src=poster`);
  await expect(page.getByText(PANEL_SENTENCE)).toHaveCount(0);
  await toScore(page);
  expect(calls.find((c) => c.path === "/api/test/session")!.body.source_label).toBe("poster");
  await expect(page.getByTestId("panel-code")).toHaveCount(0);
  await expect(page.getByText(PANEL_COMPLETION_CODE)).toHaveCount(0);
});
