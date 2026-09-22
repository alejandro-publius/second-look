import { expect, test } from "@playwright/test";
import { content } from "../lib/content";
import { assertOnlyOurOrigins, mockApi, watchRequests } from "./mock-api.mjs";
import { answerAllItems, BASE, finishLesson, passConsent, pickWarmup } from "./helpers";

test("trained arm: consent, warm-up, lesson, 16 items, score with token", async ({ page }) => {
  const urls = watchRequests(page);
  const calls = await mockApi(page, { lessonFirst: true });
  await page.goto("/t");

  // Consent appears before any session call.
  await expect(page.getByRole("heading", { name: "Before you start" })).toBeVisible();
  await expect(page.getByText("Nothing here is health advice.")).toBeVisible();
  expect(calls.filter((c) => c.path === "/api/test/session")).toHaveLength(0);
  // The bot trap exists, is not visible, and is named website.
  const trap = page.locator('input[name="website"]');
  await expect(trap).toHaveCount(1);
  await expect(trap).not.toBeInViewport();

  await passConsent(page);
  expect(calls.filter((c) => c.path === "/api/test/session")).toHaveLength(0);
  await pickWarmup(page);

  await expect.poll(() => calls.filter((c) => c.path === "/api/test/session").length).toBe(1);
  const session = calls.find((c) => c.path === "/api/test/session")!.body;
  expect(session.hidden_field).toBe("");
  expect(session.warmup_choice).toBe("w01");
  expect(session.ua_class).toBe("phone");
  expect(session.build_hash).toBe("test");
  expect(session.consent_version).toMatch(/^en-[0-9a-f]{12}$/);
  expect(session.content_hash).toMatch(/^[0-9a-f]{16}$/);
  expect(session.client_token_hash).toMatch(/^[0-9a-f]{64}$/);
  expect(session.source_label).toBe("other");

  // The rule of thumb is the heading of the lesson card; the feature name rides on the gauge.
  await expect(page.locator(".gauge-count", { hasText: "Built banks" })).toBeVisible();
  await expect(page.getByText("Draft wording, not yet approved")).toBeVisible();
  await finishLesson(page);
  await expect.poll(() => calls.filter((c) => c.path === "/api/test/lesson-done").length).toBe(1);
  const lesson = calls.find((c) => c.path === "/api/test/lesson-done")!.body;
  expect(Object.keys(lesson.lesson_seconds)).toHaveLength(12);

  // Items in the server's order (the mock reverses t01..t16). No feedback words ever appear.
  await expect(page.getByText("Photo 1 of 16")).toBeVisible();
  await expect(page.getByRole("button", { name: "Can't tell" })).toBeVisible();
  // The technical word in the question opens the bottom sheet with one plain sentence.
  await page.locator(".glossary-btn").first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Close" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await answerAllItems(page, (i) => (i % 3 === 0 ? "Can't tell" : i % 2 ? "Yes" : "No"));
  const responses = calls.filter((c) => c.path === "/api/test/response");
  expect(responses).toHaveLength(16);
  expect(responses.map((r) => r.body.position)).toEqual(Array.from({ length: 16 }, (_, i) => i + 1));
  expect(responses[0].body.item_id).toBe("t16");
  for (const r of responses) {
    expect(r.body.rt_ms).toBeGreaterThanOrEqual(0);
    expect(["yes", "no", "cant_tell"]).toContain(r.body.answer);
  }
  await expect(page.locator("body")).not.toContainText("Right.");
  await expect(page.locator("body")).not.toContainText("Not this time.");

  await expect(page.getByRole("heading", { name: "Almost done" })).toBeVisible();
  await page.getByLabel("Yes", { exact: true }).check();
  await page.getByLabel(/Keep my score for creek visits/).check();
  await page.getByRole("button", { name: "See my score" }).click();

  const complete = calls.find((c) => c.path === "/api/test/complete")!;
  expect(complete.body).toMatchObject({ prior_experience: "yes", keep_score: true });
  await expect(page.getByRole("heading", { name: "Your score" })).toBeVisible();
  const byFeature = page.getByRole("group", { name: "Score by feature" });
  await expect(byFeature.getByText("Built banks", { exact: true })).toBeVisible();
  await expect(byFeature.getByText(/^\d of 4$/).first()).toBeVisible();
  await expect(page.getByText("One visit is a snapshot. Repeated visits make a story.")).toBeVisible();

  // The warm-up reveal. The badge sits on the photograph itself, never on a position, because on
  // a phone the two stack and the order they were shown in may be shuffled (Update 11D item 1).
  const natural = content.warmup.find((w) => w.more_natural)!;
  const tidier = content.warmup.find((w) => !w.more_natural)!;
  await expect(page.getByTestId("reveal-natural").locator("img")).toHaveAttribute("src", new RegExp(`${natural.photo_id}\\.`));
  await expect(page.getByTestId("reveal-modified").locator("img")).toHaveAttribute("src", new RegExp(`${tidier.photo_id}\\.`));
  await expect(page.getByText("The messier creek is in a more natural state. Tidy is not the same as natural.")).toBeVisible();
  await expect(page.getByText("Neither photo can tell you whether the water is safe. That takes testing.")).toBeVisible();
  await expect(page.getByTestId("contributor-token")).toHaveText("MOCKTOKEN1234567");
  await expect(page.locator("img.share-card")).toHaveAttribute("src", /\/api\/share\/\d+/);
  expect(await page.evaluate(() => localStorage.getItem("sl_contributor_token"))).toBe("MOCKTOKEN1234567");
  await page.getByRole("button", { name: "Finish" }).click();
  await expect(page.getByRole("heading", { name: "Thank you" })).toBeVisible();

  expect(assertOnlyOurOrigins(urls, BASE)).toEqual([]);
  expect(calls.every((c) => c.path.startsWith("/api/") || c.path === "/health")).toBe(true);
});

test("untrained arm: test first, then the lesson offered as a thank you", async ({ page }) => {
  const urls = watchRequests(page);
  const calls = await mockApi(page, { lessonFirst: false });
  await page.goto("/t");
  await passConsent(page);
  await pickWarmup(page);
  await expect(page.getByText("Photo 1 of 16")).toBeVisible();
  expect(calls.filter((c) => c.path === "/api/test/lesson-done")).toHaveLength(0);
  await answerAllItems(page, () => "Yes");
  await page.getByRole("button", { name: "See my score" }).click();
  const complete = calls.find((c) => c.path === "/api/test/complete")!;
  expect(complete.body).toMatchObject({ prior_experience: null, keep_score: false });
  await expect(page.getByRole("heading", { name: "Your score" })).toBeVisible();
  await expect(page.getByText("8 of 16 right")).toBeVisible();
  await expect(page.getByTestId("contributor-token")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "As a thank you" })).toBeVisible();
  await page.getByRole("button", { name: "Show me" }).click();
  await finishLesson(page);
  await expect(page.getByRole("heading", { name: "Thank you" })).toBeVisible();
  expect(assertOnlyOurOrigins(urls, BASE)).toEqual([]);
});

test("a response that fails is retried and the score still arrives", async ({ page }) => {
  let failures = 0;
  // Registered after the mock so it is matched first: the first two responses fail with 503.
  const calls = await mockApi(page, { lessonFirst: false });
  await page.route("**/api/test/response", async (route) => {
    if (failures < 2) {
      failures += 1;
      await route.fulfill({ status: 503, contentType: "application/json", body: "{}" });
      return;
    }
    await route.fallback();
  });
  await page.goto("/t");
  await passConsent(page);
  await pickWarmup(page);
  await answerAllItems(page, () => "No");
  await page.getByRole("button", { name: "See my score" }).click();
  await expect(page.getByRole("heading", { name: "Your score" })).toBeVisible();
  expect(failures).toBe(2);
  expect(calls.filter((c) => c.path === "/api/test/response").length).toBeGreaterThanOrEqual(16);
});
