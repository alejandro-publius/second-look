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
  await expect(imgs.first()).toHaveAttribute("alt", "gray placeholder block, not a photo");
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
  expect(headers["permissions-policy"]).toContain("geolocation=()");
  expect(headers["permissions-policy"]).toContain("camera=()");
  const check = await page.request.get("/check");
  expect(check.headers()["permissions-policy"]).toContain("geolocation=(self)");
  expect(check.headers()["permissions-policy"]).toContain("camera=(self)");
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

  // Today every photo is a placeholder, so the page says so rather than showing an empty card.
  await expect(page.getByText("No photographs are loaded yet.")).toBeVisible();
  await expect(page.getByText("Placeholder blocks are not photographs.")).toBeVisible();

  // The judges' door and About both reach it. The participant's door deliberately does not.
  await page.goto("/judges");
  await expect(page.getByRole("link", { name: "Photo credits" })).toBeVisible();
  await page.goto("/about");
  await expect(page.getByRole("link", { name: "Photo credits" })).toBeVisible();
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Photo credits" })).toHaveCount(0);
});
