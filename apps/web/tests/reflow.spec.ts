import { expect, test } from "@playwright/test";
import { mockApi } from "./mock-api.mjs";

// WCAG 2.2 SC 1.4.10 Reflow: no screen may scroll sideways on a phone. /city once rendered 537
// CSS pixels wide on a 390 pixel phone because a bare source URL could not wrap
// (docs/internal/reviews/DESIGN_REVIEW_02.md finding 1).
for (const path of ["/", "/check", "/spot?id=example", "/two", "/quick?spot=example", "/city?creek=strawberry-creek", "/judges"]) {
  test(`${path} fits the phone width`, async ({ page }) => {
    await mockApi(page);
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const { scroll, viewport } = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      viewport: window.innerWidth,
    }));
    expect(scroll).toBeLessThanOrEqual(viewport);
  });
}
