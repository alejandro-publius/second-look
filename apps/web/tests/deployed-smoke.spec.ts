import { expect, test } from "@playwright/test";

// One real session against the deployed pair, on a phone viewport. It is skipped unless
// DEPLOYED_URL is set, so CI never reaches the network and never writes a row.
//
// Safe to run against the dry-run deployment: that build carries the QA key, so every session it
// starts is stamped is_test and the counts endpoint, which only counts real ones, does not move
// (Update 11D item 5).

const DEPLOYED = process.env.DEPLOYED_URL ?? "";
const API = process.env.DEPLOYED_API ?? "";

test.skip(!DEPLOYED || !API, "set DEPLOYED_URL and DEPLOYED_API to run this against a deployment");
test.describe.configure({ mode: "serial" });

async function counts(request: { get: (url: string) => Promise<{ json: () => Promise<unknown> }> }) {
  const res = await request.get(`${API}/api/test/counts`);
  return (await res.json()) as {
    by_arm: Record<string, { randomized: number; completed: number }>;
  };
}

test("a stranger can finish the whole thing on a phone, and it never lands in the study", async ({
  page,
  request,
}) => {
  const before = await counts(request);

  await page.goto(`${DEPLOYED}/?src=friends`);
  await expect(page.getByRole("heading", { name: "Which creek is healthier?" })).toBeVisible();
  await page.getByRole("button", { name: "This creek, on the left" }).click();
  await page.getByRole("link", { name: "Find out in two minutes" }).click();

  await expect(page.getByRole("heading", { name: "Before you start" })).toBeVisible();
  await expect(page.getByText("alejandro-publius@berkeley.edu")).toBeVisible();
  await page.getByLabel("I understand and agree to take part.").check();
  await page.getByLabel("I am 18 or older.").check();
  await page.getByRole("button", { name: "I agree, start" }).click();

  // Either arm, and whatever order the screens come in: press on the way a stranger would,
  // answering when there is something to answer and advancing when there is not, until the last
  // question before the score. The point of this test is that a person can get to the end on a
  // phone against the real deployment, not that the flow has a particular shape.
  for (let step = 0; step < 120; step++) {
    if (await page.getByRole("heading", { name: "Almost done" }).isVisible().catch(() => false)) break;
    const yes = page.getByRole("button", { name: "Yes", exact: true });
    if (await yes.isVisible().catch(() => false)) {
      const pressed = await yes.getAttribute("aria-pressed");
      if (pressed === "false") await yes.click();
    }
    const advance = page.locator("[data-confirm]:not([disabled])").first();
    if (await advance.isVisible().catch(() => false)) {
      await advance.click();
      continue;
    }
    const named = page
      .getByRole("button", { name: /^(Next photo|Next|Finish|See my score)$/ })
      .and(page.locator(":not([disabled])"))
      .first();
    if (await named.isVisible().catch(() => false)) {
      await named.click();
      continue;
    }
    await page.waitForTimeout(250);
  }

  await expect(page.getByRole("heading", { name: "Almost done" })).toBeVisible();
  await page.getByLabel("No", { exact: true }).check();
  await page.getByRole("button", { name: "See my score" }).click();
  await expect(page.getByRole("heading", { name: "Your score" })).toBeVisible();

  // The warm-up reveal is here, and the badge is on the photograph, not on a side.
  await expect(page.getByTestId("reveal-natural")).toBeVisible();
  await expect(
    page.getByText("The messier creek is in a more natural state. Tidy is not the same as natural."),
  ).toBeVisible();

  // Nothing reached the study: this build stamps its sessions is_test.
  const after = await counts(request);
  for (const arm of Object.keys(before.by_arm)) {
    expect(after.by_arm[arm], `arm ${arm} moved`).toEqual(before.by_arm[arm]);
  }
});

test("the deployed pages carry the strict headers and no third party origin", async ({ page }) => {
  const outside: string[] = [];
  page.on("request", (r) => {
    const host = new URL(r.url()).origin;
    if (host !== DEPLOYED && host !== API) outside.push(r.url());
  });
  const res = await page.goto(`${DEPLOYED}/`);
  expect(res?.status()).toBe(200);
  const csp = res?.headers()["content-security-policy"] ?? "";
  expect(csp, "the deployed site serves a CSP").toContain("default-src");
  // networkidle never settles here: the page keeps a connection open. Wait for the thing a
  // person waits for instead, then give the rest of the page a moment to ask for anything else.
  await expect(page.getByRole("heading", { name: "Which creek is healthier?" })).toBeVisible();
  await page.waitForTimeout(2000);
  expect(outside, "nothing is fetched from anywhere else").toEqual([]);
});
