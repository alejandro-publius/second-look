import { expect, test, type Page } from "@playwright/test";
import { mockApi } from "./mock-api.mjs";

const MIN = 44;

/**
 * Tap targets on the phone viewport, over the stage 1 screens only. Inline targets inside a
 * sentence are exempt, which is what WCAG 2.2 target size says and what the dotted glossary word
 * in a question relies on.
 */
async function tapTargets(page: Page, label: string) {
  const small = await page.evaluate((min) => {
    const bad: string[] = [];
    const nodes = document.querySelectorAll<HTMLElement>("button, a[href], input, [role='button'], summary");
    for (const el of nodes) {
      const cs = getComputedStyle(el);
      if (cs.display === "none" || cs.visibility === "hidden") continue;
      if (cs.display === "inline") continue; // a target inside a sentence
      // A control wrapped in a label shares one hit target with it, so measure the label.
      const target = el.closest("label") ?? el;
      const r = target.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;
      if (r.left < -1000) continue; // the off screen bot trap
      if (r.height < min || r.width < min) {
        bad.push(`${el.tagName.toLowerCase()}.${el.className || "(none)"} ${Math.round(r.width)}x${Math.round(r.height)}`);
      }
    }
    return bad;
  }, MIN);
  expect(small, `${label}: tap targets under ${MIN}px`).toEqual([]);
}

test("tap targets: landing and judge mode", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Which creek is healthier?" })).toBeVisible();
  await tapTargets(page, "/");
  await page.getByRole("button", { name: "This creek, on the left" }).click();
  await tapTargets(page, "/ after the guess");
  await page.goto("/demo");
  await expect(page.getByRole("heading", { name: "Judge mode" })).toBeVisible();
  await tapTargets(page, "/demo");
});

test("tap targets: consent, test item, lesson card and the end screen", async ({ page }) => {
  await mockApi(page, { lessonFirst: true });
  await page.goto("/t");
  await expect(page.getByRole("heading", { name: "Before you start" })).toBeVisible();
  await tapTargets(page, "consent");

  await page.getByLabel("I understand and agree to take part.").check();
  await page.getByLabel("I am 18 or older.").check();
  await page.getByRole("button", { name: "I agree, start" }).click();
  await page.getByRole("button", { name: "This creek, on the left" }).click();

  await expect(page.getByText("Built banks")).toBeVisible();
  await tapTargets(page, "lesson card");

  for (let f = 0; f < 4; f++) {
    await page.getByRole("button", { name: "Next photo", exact: true }).click();
    await page.getByRole("button", { name: "Next photo", exact: true }).click();
    await page.getByRole("button", { name: "Yes", exact: true }).click();
    await page.getByRole("button", { name: f === 3 ? "Finish" : "Next photo", exact: true }).click();
  }

  await expect(page.getByText("Photo 1 of 16")).toBeVisible();
  await tapTargets(page, "test item");

  for (let i = 1; i <= 16; i++) {
    await page.getByRole("button", { name: "Yes", exact: true }).click();
    await page.locator("[data-confirm]").click();
  }
  await expect(page.getByRole("heading", { name: "Almost done" })).toBeVisible();
  await page.getByRole("button", { name: "See my score" }).click();
  await expect(page.getByRole("heading", { name: "Your score" })).toBeVisible();
  await tapTargets(page, "end screen");
});

// /accessibility says buttons and links are at least 48 pixels tall. The judges' door is a list of
// links a judge taps first, so each is held to that (REVIEW_03 R40).
test("tap targets: every link on the judges' door is at least 48 pixels tall", async ({ page }) => {
  await mockApi(page);
  await page.goto("/judges");
  await expect(page.getByRole("heading", { name: "For judges" })).toBeVisible();
  const links = await page
    .getByRole("navigation", { name: "For judges" })
    .getByRole("link")
    .evaluateAll((as) => as.map((a) => ({ name: (a.textContent ?? "").trim(), height: a.getBoundingClientRect().height })));
  expect(links.length).toBeGreaterThanOrEqual(10);
  const short = links.filter((l) => l.height < 48).map((l) => `${l.name}: ${Math.round(l.height)}`);
  expect(short, "links under 48 pixels tall").toEqual([]);
});
