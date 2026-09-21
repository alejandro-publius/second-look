import { expect, test } from "@playwright/test";
import { API_ORIGIN, assertOnlyOurOrigins, mockApi, watchRequests } from "./mock-api.mjs";
import { BASE } from "./helpers";

test("/spot/example: timeline, observer labels, the passed-only toggle, FHIR view and curl", async ({ page }) => {
  const urls = watchRequests(page);
  const calls = await mockApi(page);
  await page.goto("/spot?id=example");
  await expect(page.getByRole("heading", { name: "Footbridge below the library" })).toBeVisible();
  await expect(page.getByText("Campus reach, Strawberry Creek")).toBeVisible();
  await expect(page.getByText("4 of 4 on Built banks, tested Sep 23")).toBeVisible();
  await expect(page.getByText("2 of 4 on Pipes and sewage signs, tested Sep 23")).toBeVisible();
  await expect(page.getByText("Score expired.")).toBeVisible();
  await expect(page.getByText("dry_pipe")).toBeVisible();
  await expect(page.getByText("First rating: good. Final rating: moderate.")).toBeVisible();

  await page.getByLabel("Only people who passed this feature").check();
  await expect(page.getByText("4 of 4 on Built banks, tested Sep 23")).toBeVisible();
  await expect(page.getByText("2 of 4 on Pipes and sewage signs, tested Sep 23")).toHaveCount(0);
  await expect(page.getByText("No answers from people who passed this feature.")).toBeVisible();

  await page.getByRole("button", { name: "View as FHIR" }).click();
  await expect(page.getByText("Validated against guide commit b907cf0: passed")).toBeVisible();
  await expect(page.getByText(`curl -s ${API_ORIGIN}/api/spot/example/fhir`)).toBeVisible();
  await expect(page.getByText('"resourceType": "Bundle"')).toBeVisible();
  expect(calls.some((c) => c.path === "/api/spot/example/fhir")).toBe(true);
  expect(calls.some((c) => c.path === "/api/fhir/validation")).toBe(true);
  await expect(page.getByRole("link", { name: "20 second return check" })).toHaveAttribute("href", "/quick?spot=example");
  expect(assertOnlyOurOrigins(urls, BASE)).toEqual([]);
});

test("/spot/unknown says there is no record", async ({ page }) => {
  await mockApi(page);
  await page.goto("/spot?id=unknown");
  await expect(page.getByText("No record for this spot.")).toBeVisible();
});

test("/two renders both observers with one card and says plainly when theirs is down", async ({ page }) => {
  await mockApi(page);
  await page.goto("/two");
  await expect(page.getByRole("heading", { name: "Two kinds of observer" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Lab (OneAquaHealth sandbox)" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Volunteer (Second Look)" })).toBeVisible();
  await expect(page.getByText("Laboratory analysis")).toBeVisible();
  await expect(page.getByText("4 of 4 on Built banks, tested Sep 23")).toBeVisible();
  await page.unrouteAll({ behavior: "ignoreErrors" });
  await mockApi(page, { theirsStatus: "down" });
  await page.goto("/two");
  await expect(page.getByText("Their sandbox did not answer, so only our record is shown.")).toBeVisible();
  await expect(page.getByRole("region", { name: "Lab (OneAquaHealth sandbox)" })).toHaveCount(0);
});

test("/quick/example posts the fixed enums", async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto("/quick?spot=example");
  await expect(page.getByRole("heading", { name: "20 second check" })).toBeVisible();
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Pick a colour" })).toBeVisible();
  await page.getByRole("button", { name: "Muddy" }).click();
  await page.getByRole("button", { name: "Bad smell" }).click();
  await page.getByRole("button", { name: "Yes", exact: true }).click();
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Saved. Thank you.")).toBeVisible();
  const q = calls.find((c) => c.path === "/api/quick/example")!;
  expect(q.body).toEqual({ colour: "muddy", smell: "bad", pipe_running: "present" });
  await expect(page.getByRole("link", { name: "See the record" })).toHaveAttribute("href", "/spot?id=example");
});

test("share card route returns an SVG built from the score and rejects bad scores", async ({ request }) => {
  const ok = await request.get("/api/share/13");
  expect(ok.status()).toBe(200);
  expect(ok.headers()["content-type"]).toContain("image/svg+xml");
  const svg = await ok.text();
  expect(svg).toContain("I spotted 13 of 16.");
  expect(svg).not.toContain("<script");
  expect((await request.get("/api/share/99")).status()).toBe(404);
  expect((await request.get("/api/share/abc")).status()).toBe(404);
  const share = await request.get("/share/13");
  const html = await share.text();
  expect(html).toContain('property="og:image"');
  expect(html).toContain("/api/share/13");
});
