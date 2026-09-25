import { expect, test } from "@playwright/test";
import { API_ORIGIN, assertOnlyOurOrigins, mockApi, watchRequests } from "./mock-api.mjs";
import { BASE } from "./helpers";

test("landing paints without the API and wakes it afterwards", async ({ page }) => {
  const urls = watchRequests(page);
  const offline = { value: true };
  const calls = await mockApi(page, { offline });
  await page.goto("/?src=poster");
  await expect(page.getByRole("heading", { name: "Which creek is healthier?" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Find out in two minutes" })).toBeVisible();
  await expect(page.getByText("No camera needed.")).toBeVisible();
  await expect(page.getByText("This trains your eyes for the visit.")).toBeVisible();
  const imgs = page.getByRole("group", { name: "Two creek photos" }).locator("img");
  await expect(imgs).toHaveCount(2);
  // Real photographs now. The alt text describes a creek and never gives the answer away.
  await expect(imgs.first()).toHaveAttribute("alt", "photo of a creek");
  await expect(imgs.last()).toHaveAttribute("alt", "photo of a creek");
  await expect.poll(() => calls.filter((c) => c.path === "/health").length).toBeGreaterThan(0);
  expect(await page.evaluate(() => sessionStorage.getItem("sl_src"))).toBe("poster");
  await expect(page.getByRole("link", { name: "Find out in two minutes" })).toHaveAttribute("href", "/t?src=poster");
  expect(assertOnlyOurOrigins(urls, BASE)).toEqual([]);
});

test("security headers are set and the CSP allows only our origin and the API", async ({ page }) => {
  const res = await page.goto("/");
  const headers = res!.headers();
  const csp = headers["content-security-policy"];
  expect(csp).toContain("default-src 'self'");
  expect(csp).toContain(`connect-src 'self' ${API_ORIGIN}`);
  expect(csp).toContain("img-src 'self' data: blob:");
  expect(csp).toContain("script-src 'self' 'unsafe-inline'");
  expect(csp).not.toContain("unsafe-eval");
  expect(csp).toContain("frame-ancestors 'none'");
  expect(headers["referrer-policy"]).toBe("no-referrer");
  // A permissions policy belongs to the page that was loaded, and a tap on a link inside the app
  // loads none, so every page allows location and the camera for our own origin, and nothing
  // else (CRITIC_09 R01). The check itself is tested from /judges in check.spec.ts.
  const policy = "geolocation=(self), camera=(self), microphone=(), payment=(), usb=()";
  for (const path of ["/", "/judges", "/check", "/quick"]) {
    const res = await page.request.get(path);
    expect(res.headers()["permissions-policy"], path).toBe(policy);
  }
});

test("no CSP violations are reported on the main screens", async ({ page }) => {
  const violations: string[] = [];
  page.on("console", (m) => {
    if (m.text().includes("Content Security Policy")) violations.push(m.text());
  });
  await mockApi(page);
  for (const path of ["/", "/t", "/demo", "/check", "/about", "/privacy", "/how-we-know", "/two", "/spot?id=example", "/poster", "/share/13", "/judges", "/credits"]) {
    await page.goto(path);
    await expect(page.locator("main")).toBeVisible();
  }
  expect(violations).toEqual([]);
});

test("every screen shows real strings, none missing from the locale", async ({ page }) => {
  await mockApi(page);
  for (const path of ["/", "/t", "/demo", "/check", "/about", "/privacy", "/how-we-know", "/two", "/spot?id=example", "/quick?spot=example", "/poster", "/offline", "/share/13", "/judges", "/credits"]) {
    await page.goto(path);
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("body")).not.toContainText("[missing:");
  }
});

test("every photograph a visitor can see is named on the credits page", async ({ page }) => {
  await mockApi(page);
  await page.goto("/credits");
  await expect(page.getByRole("heading", { name: "Photo credits" })).toBeVisible();

  // Every photograph is real and credited by name; no placeholder is left to explain.
  await expect(page.getByText("by Gregwadley").first()).toBeVisible();
  await expect(page.getByText("by Roger Kidd").first()).toBeVisible();
  await expect(page.getByText("No photographs are loaded yet.")).toHaveCount(0);
  await expect(page.getByText("Placeholder blocks are not photographs.")).toHaveCount(0);
  // The video walks' footage is credited too, one line per video.
  await expect(page.getByRole("heading", { name: "Creek footage" })).toBeVisible();
  // The open footage in the video, each item with its author and licence, and the video's own
  // licence, CC BY-SA 4.0 (UPDATE_22 6.6).
  await expect(page.getByRole("heading", { name: "Footage in our video" })).toBeVisible();
  await expect(page.getByText("by Coro").first()).toBeVisible();
  await expect(page.getByText("by Awinch1001")).toBeVisible();
  await expect(page.getByRole("link", { name: "Our video's licence: CC BY-SA 4.0" })).toHaveAttribute(
    "href",
    "https://creativecommons.org/licenses/by-sa/4.0/",
  );
  await expect(page.getByRole("link", { name: "StrawberryCreek9.JPG" })).toHaveAttribute(
    "href",
    "https://commons.wikimedia.org/wiki/File:StrawberryCreek9.JPG",
  );

  // The judges' door and About both reach it. The participant's door deliberately does not.
  await page.goto("/judges");
  await expect(page.getByRole("link", { name: "Photo credits" })).toBeVisible();
  await page.goto("/about");
  await expect(page.getByRole("link", { name: "Photo credits" })).toBeVisible();
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Photo credits" })).toHaveCount(0);
});

// The plan was tagged prereg-v1 on 2026-09-21, before any participant, and the tag is never moved
// (hard rules 13 and 15), so the page names it without a caveat (REVIEW_03 R30).
test("the how we know page names the plan's tag as made", async ({ page }) => {
  await page.goto("/how-we-know");
  await expect(page.getByText("Analysis plan tag: prereg-v1. The plan names")).toBeVisible();
  await expect(page.locator("main")).not.toContainText("not yet tagged");
});

// WCAG 2.2 SC 2.4.2: each page says what it is in its title, not only the site's name (REVIEW_03 R39).
for (const [path, title] of [
  ["/city?creek=strawberry-creek", "What this creek needs: Second Look"],
  ["/spot?id=example", "Creek record: Second Look"],
  ["/demo", "Judge mode: Second Look"],
  ["/quick?spot=example", "Quick check: Second Look"],
]) {
  test(`${path} has a title of its own`, async ({ page }) => {
    await mockApi(page);
    await page.goto(path);
    await expect(page).toHaveTitle(title);
  });
}
