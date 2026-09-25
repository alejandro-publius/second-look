import { expect, test } from "@playwright/test";
import { API_ORIGIN, assertOnlyOurOrigins, exampleCity, mockApi, watchRequests } from "./mock-api.mjs";
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
  await expect(page.getByText("Records built by the same code passed the HL7 validator against guide commit b907cf0 in CI: passed")).toBeVisible();
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

test("/two labels the hand-made golden visit as an example and names its place (REVIEW_03 R33)", async ({ page }) => {
  await mockApi(page, { oursExample: true });
  await page.goto("/two");
  const ours = page.getByRole("region", { name: "Volunteer (Second Look)" });
  await expect(ours.getByText("Example record, made by hand for this demo.", { exact: false })).toBeVisible();
  await expect(page.getByText("an example of a volunteer answer", { exact: false })).toBeVisible();
  await expect(page.getByText("a volunteer answer from Strawberry Creek", { exact: false })).toHaveCount(0);
  await expect(ours.getByText("Strawberry Creek, campus reach, spot 1")).toBeVisible();
  await expect(ours.getByText("Location/sl-loc-spot-1")).toHaveCount(0);
  // A stored visit is a volunteer's answer: no example label.
  await page.unrouteAll({ behavior: "ignoreErrors" });
  await mockApi(page);
  await page.goto("/two");
  await expect(page.getByRole("region", { name: "Volunteer (Second Look)" })).toBeVisible();
  await expect(page.getByText("Example record, made by hand for this demo.", { exact: false })).toHaveCount(0);
});

test("/quick/example posts the fixed enums", async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto("/quick?spot=example");
  await expect(page.getByText("Quick check", { exact: true }).first()).toBeVisible();
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

// CRITIC_09 R04: /quick with no spot showed the whole form, and Send could only end on "try
// again", since the API has no route for an empty spot. With no spot it now says where the quick
// check opens from and links the full check, and there is nothing to send.
test("/quick with no spot says to open it from a record, links the check, and has no form", async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto("/quick");
  await expect(page.getByRole("heading", { name: "Quick check", level: 1 })).toBeVisible();
  await expect(page.getByText("Open the quick check from a creek record.", { exact: false })).toBeVisible();
  await expect(page.getByRole("group", { name: "Water colour" })).toHaveCount(0);
  await expect(page.getByText("Step 1 of 4")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Send" })).toHaveCount(0);
  const link = page.getByRole("main").getByRole("link", { name: "Start a creek check", exact: true });
  await expect(link).toHaveAttribute("href", "/check");
  await link.click();
  await expect(page.getByRole("heading", { name: "Creek check" })).toBeVisible();
  expect(calls.filter((c: { path: string }) => c.path.startsWith("/api/quick"))).toEqual([]);
});

// CRITIC_10 T02: /quick's static page said "Loading the record", though it never loads one, and
// with a spot that has no record it showed a form whose Send could only fail, with "The server
// could not take that". The static line is neutral now; the page asks the API for the spot first
// and, when there is none, shows the no-spot notice; and a 404 on Send shows the API's own words.
test("/quick's static page says only Loading, never that it loads a record", async ({ request }) => {
  for (const path of ["/quick", "/quick?spot=example"]) {
    const html = await (await request.get(path)).text();
    expect(html).toContain(">Loading...<");
    expect(html).not.toContain("Loading the record");
  }
});

test("/quick for a spot with no record shows the no-spot notice and no form", async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto("/quick?spot=nosuch");
  await expect(page.getByRole("heading", { name: "Quick check", level: 1 })).toBeVisible();
  await expect(page.getByText("Open the quick check from a creek record.", { exact: false })).toBeVisible();
  await expect(page.getByRole("main").getByRole("link", { name: "Start a creek check", exact: true })).toHaveAttribute("href", "/check");
  await expect(page.getByRole("group", { name: "Water colour" })).toHaveCount(0);
  await expect(page.getByText("Step 1 of 4")).toHaveCount(0);
  expect(calls.filter((c: { path: string }) => c.path === "/api/spot/nosuch")).toHaveLength(1);
  expect(calls.filter((c: { path: string }) => c.path.startsWith("/api/quick"))).toEqual([]);
});

test("/quick shows the API's own words when Send is refused with a 404, and keeps the score token", async ({ page }) => {
  const calls = await mockApi(page);
  // The spot is gone by the time Send goes: the Worker's words for that (worker/src/check.ts).
  const sent: Record<string, unknown>[] = [];
  await page.route(`${API_ORIGIN}/api/quick/**`, (route) => {
    sent.push(route.request().postDataJSON());
    return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "We do not know that spot." }) });
  });
  await page.addInitScript(() => localStorage.setItem("sl_contributor_token", "MOCKTOKEN1234567"));
  await page.goto("/quick?spot=example");
  await page.getByRole("button", { name: "Muddy" }).click();
  await page.getByRole("button", { name: "Bad smell" }).click();
  await page.getByRole("button", { name: "Yes", exact: true }).click();
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toHaveText("We do not know that spot.");
  await expect(page.getByText("The server could not take that.", { exact: false })).toHaveCount(0);
  expect(calls.filter((c: { path: string }) => c.path === "/api/spot/example")).toHaveLength(1);
  // Sent with the token, then again without it; the token was not the trouble, so it is kept.
  expect(sent.map((b) => b.contributor_token ?? null)).toEqual(["MOCKTOKEN1234567", null]);
  expect(await page.evaluate(() => localStorage.getItem("sl_contributor_token"))).toBe("MOCKTOKEN1234567");
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

// An empty list of measures blames approval only when no measure is approved (REVIEW_03 R28).
for (const waiting of [false, true]) {
  test(`/city with no measure to show, measures ${waiting ? "not yet approved" : "approved"}`, async ({ page }) => {
    await mockApi(page);
    // Registered after mockApi, so this answers the creek first.
    await page.route(`${API_ORIGIN}/api/city/**`, (route) =>
      route.fulfill({ contentType: "application/json", body: JSON.stringify({ ...exampleCity, needs: [], measures_waiting_for_approval: waiting }) }),
    );
    await page.goto("/city?creek=example");
    await expect(page.getByRole("heading", { name: "What OneAquaHealth says to do" })).toBeVisible();
    await expect(page.getByText("Find and fix leaking or wrongly connected sewers")).toHaveCount(0);
    if (waiting) {
      await expect(page.getByText("an empty list here means nobody has approved one")).toBeVisible();
      await expect(page.getByText("No measure applies to what people have reported here so far.")).toHaveCount(0);
    } else {
      await expect(page.getByText("No measure applies to what people have reported here so far.")).toBeVisible();
      await expect(page.getByText("nobody has approved")).toHaveCount(0);
    }
  });
}

// CRITIC_06 H01: a creek with checks and no finding says nothing has been reported yet, never that
// nobody checked it, since the count at the top says otherwise. With no checks it still says that.
for (const visits of [5, 0]) {
  test(`/city with no finding after ${visits} visits says which of the two empty lines is true`, async ({ page }) => {
    await mockApi(page);
    await page.route(`${API_ORIGIN}/api/city/**`, (route) =>
      route.fulfill({ contentType: "application/json", body: JSON.stringify({ ...exampleCity, visits, findings: [] }) }),
    );
    await page.goto("/city?creek=example");
    await expect(page.getByRole("heading", { name: "What people reported" })).toBeVisible();
    const reported = page.getByText("Nobody has reported a built bank, pipe, barrier or invasive plant here yet.");
    const unchecked = page.getByText("Nobody has checked this creek yet.");
    await expect(visits > 0 ? reported : unchecked).toBeVisible();
    await expect(visits > 0 ? unchecked : reported).toHaveCount(0);
  });
}

// CRITIC_11 W02: bare /city, the route the README names, said "Nobody has checked this creek yet."
// without naming a creek or saying how to pick one. It now says the link names no creek and links
// each creek the site knows, from content/regions/.
test("/city with no creek says to pick one and links each creek", async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto("/city");
  await expect(page.getByText("This link names no creek. Pick a creek to see what it needs.")).toBeVisible();
  await expect(page.getByText("Nobody has checked this creek yet.")).toHaveCount(0);
  const link = page.getByRole("main").getByRole("link", { name: "Strawberry Creek", exact: true });
  await expect(link).toHaveAttribute("href", "/city?creek=strawberry-creek");
  // Nothing is asked of the API about a creek the link does not name.
  expect(calls.filter((c: { path: string }) => c.path.startsWith("/api/city"))).toEqual([]);
  await link.click();
  await expect(page).toHaveURL(/\/city\?creek=strawberry-creek$/);
  await expect(page.getByText("This link names no creek.", { exact: false })).toHaveCount(0);
  await expect.poll(() => calls.filter((c: { path: string }) => c.path === "/api/city/strawberry-creek").length).toBeGreaterThan(0);
});

// CRITIC_09 R05: /city?creek=<unknown> said "Something did not send", though nothing was sent and
// the API had answered in its own words. A 404 now shows that sentence; a server error says the
// server could not take it, and only a failed connection speaks of the connection.
test("/city with a creek the API does not know shows the API's own sentence", async ({ page }) => {
  await mockApi(page);
  await page.goto("/city?creek=no-such-creek");
  await expect(page.getByRole("status")).toHaveText("We have no record for that creek yet.");
  await expect(page.getByText("Something did not send")).toHaveCount(0);
  await page.route("**/api/city/**", (route) => route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "boom" }) }));
  await page.goto("/city?creek=no-such-creek");
  await expect(page.getByRole("status")).toHaveText("The server could not take that. Try again in a moment.");
  await page.route("**/api/city/**", (route) => route.abort());
  await page.goto("/city?creek=no-such-creek");
  await expect(page.getByRole("status")).toHaveText("Something did not send. Check your connection and try again.");
});

// /two shows a volunteer record beside a laboratory reading from another place, so the door must
// not promise the same creek (REVIEW_03 R34).
test("the judges' door names /two for what it shows", async ({ page }) => {
  await mockApi(page);
  await page.goto("/judges");
  await expect(page.getByRole("link", { name: "A volunteer record in the viewer built for laboratory results" })).toHaveAttribute("href", "/two");
  await expect(page.getByText("The same creek beside a laboratory result")).toHaveCount(0);
});

// The id is read in the browser, after the first paint, so the record must not ask for an empty
// id first, and a link with no id says so (REVIEW_03 R43).
test("/spot asks only for the id in the link, and says when the link names none", async ({ page }) => {
  const calls = await mockApi(page);
  const asked = () => calls.filter((c: { path: string }) => c.path.startsWith("/api/spot/")).map((c: { path: string }) => c.path);
  await page.goto("/spot?id=example");
  await expect(page.getByRole("heading", { name: "Footbridge below the library" })).toBeVisible();
  expect(asked()).toEqual(["/api/spot/example"]);
  await page.goto("/spot");
  await expect(page.getByText("This link names no spot.")).toBeVisible();
  await expect(page.getByText("No record for this spot.")).toHaveCount(0);
  expect(asked()).toEqual(["/api/spot/example"]);
});

// The live creek's own page stays empty until a real check arrives, so the city door opens the walk
// whose end has the full city view, and its line says both (CRITIC_02 D05). The creek's page still
// answers by its readable slug.
// CRITIC_09 Q04 and Q01: the door says it is the end of a walk, and how to see a measure on clips
// of natural creeks, in the words the walk itself shows.
test("the judges' city door opens the walk that ends in the city view, and names the empty creek", async ({ page }) => {
  await mockApi(page);
  await page.goto("/judges");
  const door = "What a city sees, at the end of a walk";
  const row = page.locator(".row").filter({ has: page.getByRole("link", { name: door, exact: true }) });
  await expect(row).toContainText('press "See this creek as a city would"');
  await expect(row).toContainText(
    "These clips show natural creeks, so an honest check finds little to fix. To see what a city is told, answer as if the creek were damaged: Artificial for the bank, or Yes to a pipe.",
  );
  await expect(row).toContainText("The page /city?creek=strawberry-creek stays empty until the first real creek check.");
  await row.getByRole("link", { name: door, exact: true }).click();
  await expect(page).toHaveURL(/\/walk\/v02$/);
  await page.goto("/city?creek=strawberry-creek");
  await expect(page.getByRole("heading", { name: "What this creek needs", level: 1 })).toBeVisible();
});
