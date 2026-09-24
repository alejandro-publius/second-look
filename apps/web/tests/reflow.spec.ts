import { expect, test } from "@playwright/test";
import { mockApi } from "./mock-api.mjs";

// WCAG 2.2 SC 1.4.10 Reflow: no screen may scroll sideways on a phone. /city once rendered 537
// CSS pixels wide on a 390 pixel phone because a bare source URL could not wrap
// (docs/internal/reviews/DESIGN_REVIEW_02.md finding 1). /credits once rendered 713 wide because a
// footage title sat in a row's end slot, which never shrinks (REVIEW_03 R26).
for (const path of ["/", "/check", "/spot?id=example", "/two", "/quick?spot=example", "/city?creek=strawberry-creek", "/judges", "/credits", "/walk", "/verify", "/accessibility"]) {
  test(`${path} fits the phone width`, async ({ page }) => {
    await mockApi(page);
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    // The phone's own width, not window.innerWidth: on a phone the layout viewport grows to fit a
    // page that is too wide, so innerWidth would always equal the page's width.
    const viewport = page.viewportSize()!.width;
    const scroll = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scroll).toBeLessThanOrEqual(viewport);
  });
}
