import { expect, test } from "@playwright/test";
import { API_ORIGIN, assertOnlyOurOrigins, mockApi, watchRequests } from "./mock-api.mjs";
import { BASE } from "./helpers";

test("/spot/example: timeline, observer labels, the passed-only toggle, FHIR view and curl", async ({ page }) => {
  const urls = watchRequests(page);
  const calls = await mockApi(page);
  await page.goto("/spot?id=example");
  await expect(page.getByRole("heading", { name: "Footbridge below the library" })).toBeVisible();
  await expect(page.getByText("Below the forks, west campus, Strawberry Creek")).toBeVisible();
  await expect(page.getByRole("link", { name: "The whole creek" })).toHaveAttribute("href", "/city?creek=strawberry-creek");
  // What people reported upstream, with the records one tap away.
  await expect(page.getByRole("heading", { name: "Upstream of here" })).toBeVisible();
  await expect(page.getByText("Upstream of here, 2 people reported pipes and sewage signs on Sep 23.")).toBeVisible();
  await expect(page.getByText("4 of 4 on Built banks, tested Sep 23")).toBeVisible();
  await expect(page.getByText("2 of 4 on Pipes and sewage signs, tested Sep 23")).toBeVisible();
  await expect(page.getByText("Score expired.")).toBeVisible();
  // The checks by their plain names, never the rule ids, and what the person did in words.
  await expect(page.getByText("Pipe after dry days")).toBeVisible();
  await expect(page.getByText("Rating check")).toBeVisible();
  await expect(page.getByText("You said yes.")).toBeVisible();
  await expect(page.getByText("You changed your rating from good to moderate.")).toBeVisible();
  await expect(page.getByText("dry_pipe")).toHaveCount(0);
  await expect(page.getByText("rating_check")).toHaveCount(0);
  await expect(page.getByText("First rating: good. Final rating: moderate.")).toBeVisible();
  // The health card: one approved action each for the person, the pet and the city, with sources.
  await expect(page.getByRole("heading", { name: "What you can do" })).toBeVisible();
  await expect(page.getByText("Stay out of water that smells bad, looks discoloured, or has foam, scum or mats on the surface.")).toBeVisible();
  await expect(page.getByText("If your dog seems sick after being in or near the water, call a vet right away.")).toBeVisible();
  await expect(page.getByText("Find and fix leaking or wrongly connected sewers, and improve the treatment of waste water.")).toBeVisible();
  await expect(page.getByText("Sources:")).toBeVisible();

  await page.getByLabel("Only show answers from people who passed the test for that feature").check();
  await expect(page.getByText("4 of 4 on Built banks, tested Sep 23")).toBeVisible();
  await expect(page.getByText("2 of 4 on Pipes and sewage signs, tested Sep 23")).toHaveCount(0);
  await expect(page.getByText("No answers here from people who passed the test for that feature.")).toBeVisible();

  await page.getByRole("button", { name: "View as FHIR" }).click();
  await expect(page.getByText("Validated against guide commit b907cf0: passed")).toBeVisible();
  await expect(page.getByText(`curl -s ${API_ORIGIN}/api/spot/example/fhir`)).toBeVisible();
  await expect(page.getByText('"resourceType": "Bundle"')).toBeVisible();
  expect(calls.some((c) => c.path === "/api/spot/example/fhir")).toBe(true);
  expect(calls.some((c) => c.path === "/api/fhir/validation")).toBe(true);
  await expect(page.getByRole("link", { name: "Quick check", exact: true })).toHaveAttribute("href", "/quick?spot=example");
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
  await expect(page.getByText("20 second check", { exact: true })).toBeVisible();
  // One question per screen: a tap moves on, and Send waits for the last screen.
  await expect(page.getByRole("group", { name: "Water colour" })).toBeVisible();
  await expect(page.getByText("Step 1 of 4")).toBeVisible();
  await expect(page.getByRole("button", { name: "Send" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Foam" })).toHaveCount(0);
  await page.getByRole("button", { name: "Muddy" }).click();
  await expect(page.getByRole("heading", { name: "Smell", exact: true })).toBeFocused();
  await page.getByRole("button", { name: "Bad smell" }).click();
  // Back keeps the answer, and tapping it again moves on.
  await expect(page.getByRole("group", { name: "Is the pipe running?" })).toBeVisible();
  await page.getByRole("button", { name: "Back" }).click();
  await expect(page.getByRole("button", { name: "Bad smell" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Bad smell" }).click();
  await page.getByRole("button", { name: "Yes", exact: true }).click();
  await expect(page.getByText("No photo yet")).toBeVisible();
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

test("/city shows two lists decided by code, and no number without its records", async ({ page }) => {
  await mockApi(page);
  await page.goto("/city?creek=example");
  await expect(page.getByRole("heading", { name: "What this creek needs", level: 1 })).toBeVisible();
  await expect(page.getByText("5 visits at 2 spots")).toBeVisible();

  // The approved measures, each with its source, and the one sentence that says whose they are.
  await expect(page.getByText("Find and fix leaking or wrongly connected sewers, and improve the treatment of waste water.")).toBeVisible();
  await expect(page.getByText("Replant both margins with native trees and shrubs, and stop cutting them back.")).toBeVisible();
  await expect(page.getByText("No measure is shown yet.")).toHaveCount(0);
  await expect(page.getByText("These are OneAquaHealth's own restoration measures, from the")).toBeVisible();
  await expect(page.getByRole("link", { name: "OneAquaHealth Policy Brief (2026), page 9" })).toHaveAttribute(
    "href",
    "https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf",
  );

  // A pipe two people who passed saw running in dry weather, with its records one tap away.
  await expect(page.getByText("Footbridge below the library").first()).toBeVisible();
  await expect(page.getByText("2 people, after 9 dry days")).toBeVisible();
  const evidence = page.getByRole("link", { name: "Open the records" });
  await expect(evidence.first()).toHaveAttribute("href", "/api/fhir/Bundle/v1");
  // Every list that shows a number shows a way to open it.
  expect(await evidence.count()).toBeGreaterThanOrEqual(2);

  // A pin that reads like a test is listed and kept out of the numbers.
  await expect(page.getByText("test spot")).toBeVisible();
  await expect(page.getByText("Nothing is deleted.")).toBeVisible();

  // The reaches, hills first, and the one line that landed below the finding.
  await expect(page.getByRole("heading", { name: "Reaches, from the hills to the Bay" })).toBeVisible();
  await expect(page.getByText("Flows into Below the forks, west campus. 5 visits at 1 spot.")).toBeVisible();
  await expect(page.getByText("Upstream of here, 2 people reported pipes and sewage signs on Sep 23.")).toBeVisible();
  await expect(page.getByText("Nothing reported upstream.")).toHaveCount(1);
  await expect(page.getByText("1 spot sits on this creek but on no reach")).toBeVisible();

  // The referral is one tap away, and the example result says what it is before it says anything else.
  await expect(page.getByRole("link", { name: "Referral as FHIR" })).toHaveAttribute("href", "/api/fhir/referral/example");
  await expect(page.getByText("Example", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Show how a result would come back" }).click();
  await expect(page.getByText("Example", { exact: true })).toBeVisible();
  await expect(page.getByText("This is an example, not a real result.")).toBeVisible();
  await expect(page.getByRole("cell", { name: "Enterobacteriaceae, share of 16S reads" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "1.8 percent" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Absent" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Example as FHIR" })).toHaveAttribute("href", "/api/fhir/referral/example/example-result");
  // The page's own numbers did not move: the example is counted by nothing.
  await expect(page.getByText("5 visits at 2 spots")).toBeVisible();
  await page.getByRole("button", { name: "Hide the example result" }).click();
  await expect(page.getByText("Example", { exact: true })).toHaveCount(0);
});

test("/city with no creek says so rather than showing an empty page", async ({ page }) => {
  await mockApi(page);
  await page.goto("/city");
  await expect(page.getByText("Nobody has checked this creek yet.")).toBeVisible();
});

test("the judges' door links the creek by its readable slug", async ({ page }) => {
  await mockApi(page);
  await page.goto("/judges");
  await page.getByRole("link", { name: "For a city" }).click();
  await expect(page).toHaveURL(/\/city\?creek=strawberry-creek$/);
  await expect(page.getByRole("heading", { name: "What this creek needs", level: 1 })).toBeVisible();
});
