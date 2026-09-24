import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mockApi } from "./mock-api.mjs";

// CRITIC_02 D03, D05 and D11: a judge on the live site must reach the evidence, each door must
// say what it shows and about how long it takes, and no door may say two minutes when the consent
// says the test takes about four.
const content = JSON.parse(readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"));
const REPO = "https://github.com/alejandro-publius/second-look";
const SEP_30 = "Opens on Sep 30, when the repository goes public.";

test("every door on /judges has one line under it with about how long it takes", async ({ page }) => {
  await mockApi(page);
  await page.goto("/judges");
  const rows = page.getByRole("navigation", { name: "For judges" }).locator(".row");
  const doors = await rows.evaluateAll((els) =>
    els.map((el) => ({
      links: el.querySelectorAll("a").length,
      label: (el.querySelector("a")?.textContent ?? "").trim(),
      line: (el.querySelector(".row-value")?.textContent ?? "").trim(),
    })),
  );
  expect(doors.length).toBeGreaterThanOrEqual(14);
  const without = doors.filter((d) => d.links !== 1 || !d.line).map((d) => d.label);
  expect(without, "doors with no line, or not exactly one link").toEqual([]);
  const untimed = doors.filter((d) => !/\b(minutes?|seconds?)\b/i.test(`${d.label} ${d.line}`)).map((d) => d.label);
  expect(untimed, "doors that do not say how long they take").toEqual([]);
});

test("the repository doors link the README, the report, the model card, the footage example and the code, and say they open on Sep 30", async ({ page }) => {
  await mockApi(page);
  await page.goto("/judges");
  for (const [name, href] of [
    ["The guide for judges in our README", `${REPO}#for-judges`],
    ["The technical report, as a PDF", `${REPO}/blob/main/docs/REPORT.pdf`],
    ["The model card", `${REPO}/blob/main/docs/MODEL_CARD.md`],
    ["The checker at work on real creek footage", `${REPO}/blob/main/examples/footage-flag/README.md`],
    ["The code", REPO],
  ]) {
    const link = page.getByRole("link", { name, exact: true });
    await expect(link).toHaveAttribute("href", href);
    await expect(page.locator(".row").filter({ has: link })).toContainText(SEP_30);
  }
});

test("the judges' doors give the test about four minutes and the walk its clip, never two minutes", async ({ page }) => {
  await mockApi(page);
  await page.goto("/judges");
  const nav = page.getByRole("navigation", { name: "For judges" });
  await expect(nav.getByRole("link", { name: "Take the test, about four minutes with its lesson" })).toHaveAttribute(
    "href",
    "/t?src=other",
  );
  const walk = content.walks[0];
  await expect(nav.getByRole("link", { name: `A sample record: a ${walk.clip.seconds} second clip, then the full check` })).toHaveAttribute(
    "href",
    `/walk/${walk.id}`,
  );
  await expect(nav).not.toContainText(/two.minute|one.minute/i);
  await expect(page.getByText(/two minute test/i)).toHaveCount(0);
});

test("About links the judges' door", async ({ page }) => {
  await mockApi(page);
  await page.goto("/about");
  await page.getByRole("navigation", { name: "More pages" }).getByRole("link", { name: "For judges" }).click();
  await expect(page).toHaveURL(/\/judges$/);
  await expect(page.getByRole("heading", { name: "For judges", level: 1 })).toBeVisible();
});

// The poster's duration is its own string; the landing page's button is a frozen string of the
// test flow and keeps its words (landing.spec.ts).
test("the poster says about four minutes with the lesson", async ({ page }) => {
  await mockApi(page);
  await page.goto("/poster");
  await expect(page.getByText("Scan to find out. About four minutes with the lesson. Anonymous.")).toBeVisible();
  await expect(page.getByRole("img", { name: "QR code that opens the test" })).toBeVisible();
  await expect(page.locator("main")).not.toContainText(/two.minute|two minutes/i);
});
