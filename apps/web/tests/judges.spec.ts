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
    // Critic round 14 R12: the judge's day and the hard questions, one tap from the site.
    ["A judge's day: what you should see at each step", `${REPO}/blob/main/docs/JUDGE_DAY.md`],
    ["The hardest questions, with honest answers", `${REPO}/blob/main/docs/submission/JUDGE_QA.md`],
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
  // CRITIC_09 Q04: the clip's length on one door only, not on two doors in a row.
  const withClip = await nav.locator(".row").filter({ hasText: `${walk.clip.seconds} second` }).count();
  expect(withClip).toBe(1);
});

// CRITIC_03 E05 and E06: the /two door says what the page shows while the OneAquaHealth sandbox
// is down, and the footage door starts from the committed answer, which is the answer after
// force_answer, not the reply as the model sent it.
test("the /two door says our record shows alone while their sandbox is down, and the footage door starts from the committed answer", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/judges");
  const nav = page.getByRole("navigation", { name: "For judges" });
  const door = (name: string) => nav.locator(".row").filter({ has: page.getByRole("link", { name, exact: true }) });
  await expect(door("A volunteer record in the viewer built for laboratory results")).toContainText(
    "While the OneAquaHealth sandbox is down, our record shows alone.",
  );
  const footage = door("The checker at work on real creek footage");
  await expect(footage).toContainText("from the model's committed answer to the question a person would be asked");
  await expect(nav).not.toContainText("raw reply");
});

// CRITIC_04 F04: /judges and /about opened with the landing page's frozen line, "Two minutes
// teaching and testing you ...", two lines above the door that says about four minutes. Both now
// open with a line that names no time. The landing page keeps its frozen line.
test("/judges and /about open with a line that names no time, and the landing page keeps its frozen line", async ({ page }) => {
  await mockApi(page);
  const locale: Record<string, string> = content.locale;
  // "Second Look" is a name, not a time, so a second counts only after a number.
  const noTime = /\bminutes?\b|\bhours?\b|\d+\s*seconds?\b/i;
  for (const [path, key] of [
    ["/judges", "judges.intro"],
    ["/about", "about.lead"],
  ]) {
    await page.goto(path);
    const main = page.getByRole("main");
    await expect(main.locator("p").first()).toHaveText(locale[key]);
    expect(locale[key]).not.toMatch(noTime);
    await expect(main).not.toContainText(locale["app.one_sentence"]);
  }
  await page.goto("/");
  await expect(page.getByRole("main").getByText(locale["app.one_sentence"])).toBeVisible();
});

// CRITIC_09 R03: "Volunteers never have" was untrue: some volunteer programs certify people for a
// method before their data counts. About now says what no program we know of does: a score for
// each feature, kept with every observation.
test("About says some volunteer programs certify people, and what none we know of does", async ({ page }) => {
  await mockApi(page);
  await page.goto("/about");
  const main = page.getByRole("main");
  await expect(main).toContainText(
    "Professional stream surveyors pass a test before their data counts. Some volunteer programs certify people for a method, such as water chemistry. None we know of measures how well each volunteer sees each feature, or keeps that score with every observation.",
  );
  await expect(main).not.toContainText("never have");
});

test("About links the judges' door", async ({ page }) => {
  await mockApi(page);
  await page.goto("/about");
  await page.getByRole("navigation", { name: "More pages" }).getByRole("link", { name: "For judges" }).click();
  await expect(page).toHaveURL(/\/judges$/);
  await expect(page.getByRole("heading", { name: "For judges", level: 1 })).toBeVisible();
});

// The poster quotes the test's time from time.test (times.spec.ts); the landing page's button is a
// frozen string of the test flow and keeps its words (landing.spec.ts).
test("the poster says about four minutes with the lesson", async ({ page }) => {
  await mockApi(page);
  await page.goto("/poster");
  await expect(page.getByText("Scan to find out. It takes about four minutes with the lesson. Anonymous.")).toBeVisible();
  await expect(page.getByRole("img", { name: "QR code that opens the test" })).toBeVisible();
  await expect(page.locator("main")).not.toContainText(/two.minute|two minutes/i);
});

// Critic rounds 14 and 15 (B01, C01, E01, F01, G01): since Sep 25 a finished walk is stored as a
// demo record for 30 days, but /judges said nothing was stored but the test and a creek check, and
// /privacy's list had no walk. Both now name it, and /privacy names the walk kept on the phone.
test("/judges and /privacy say a finished walk's demo record is kept 30 days, and what stays on the phone", async ({ page }) => {
  await mockApi(page);
  const locale: Record<string, string> = content.locale;
  await page.goto("/judges");
  const intro = page.getByRole("main").locator("p").first();
  await expect(intro).toContainText("a finished walk's demo record, kept 30 days and never counted");
  await page.goto("/privacy");
  const stored = page.getByRole("main").locator("ul").first().locator("li");
  await expect(stored.filter({ hasText: /^Video walk:/ })).toHaveText(locale["privacy.stored_walk"]);
  await expect(stored.filter({ hasText: /^Video walk:/ })).toContainText("Kept 30 days as a demo record, then deleted.");
  await expect(stored.filter({ hasText: /^On your phone only:/ })).toContainText("a video walk you have not finished");
});

// Critic round 14 G03 and round 15 C03: half the people who take the test see the sixteen photos
// before the lesson. The test door says so, where a judge meets it.
test("the judges' test door says the server puts you in one of two groups at random", async ({ page }) => {
  await mockApi(page);
  await page.goto("/judges");
  const nav = page.getByRole("navigation", { name: "For judges" });
  const door = nav.locator(".row").filter({ has: page.getByRole("link", { name: "Take the test, about four minutes with its lesson" }) });
  await expect(door).toContainText("The server puts you at random in one of two groups: one sees the lesson first, the other sees the sixteen photos first and is offered the lesson after its score.");
});
