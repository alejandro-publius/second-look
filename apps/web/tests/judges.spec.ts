import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mockApi } from "./mock-api.mjs";

// CRITIC_02 D03, D05 and D11: a judge on the live site must reach the evidence, each door must
// say what it shows and about how long it takes, and no door may say two minutes when the consent
// says the test takes about four.
const content = JSON.parse(readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"));
const REPO = "https://github.com/alejandro-publius/second-look";
const EN: Record<string, string> = content.locale;
// Audit findings time-bombs-1 and first-two-minutes-4: the doors said "Opens on Sep 30" and "It
// opens on Sep 28", fixed strings that turn false on those days. Then the deadline moved
// (UPDATE_33): the repository is public from Oct 3, and judge mode, which was open from Sep 28,
// is shut again while a second wave of the study runs, until the second lock,
// 2026-10-03T04:00:00Z. The page has no clock and is read on both sides of that instant, so
// these words are true before it and after it.
const PUBLIC_FROM = "The repository is public from Oct 3.";
const JUDGE_MODE_SHUT_WHILE = "It is shut while the second wave of the study runs, because the study uses the same photos.";
const JUDGE_MODE_OPEN_FROM = "Open from Oct 3 at 04:00 UTC, which is Friday Oct 2 at 21:00 PDT.";
// Words that are true on one side of a day only: a day to come, or a state as of today.
const ONE_SIDED = /\bopens on\b|\bwill open\b|\bgoes public\b|\bnot yet open\b|\bopen since\b|\bopen (now|today)\b|\bis open\b|\bshut (now|today)\b/i;
// The days the doors named before the deadline moved.
const OLD_DAYS = /\bSep 28\b|\bSep 30\b/;
const BEFORE_SECOND_LOCK = new Date("2026-10-03T03:59:59Z");
const AT_SECOND_LOCK = new Date("2026-10-03T04:00:00Z");

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

test("the repository doors link the README, the report, the model card, the footage example and the code, and say the repository is public from Oct 3", async ({ page }) => {
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
    await expect(page.locator(".row").filter({ has: link })).toContainText(PUBLIC_FROM);
  }
});

// The page is read from Sep 29 to Oct 15 and has no clock. So no door may speak of a day to come
// or of how things are today, and the page must read the same whatever the clock says: before the
// second lock, at it, and to the end of judging.
test("no door on /judges says that something opens or will open, on any day from now to the end of judging", async ({ page }) => {
  await mockApi(page);
  const seen: string[] = [];
  for (const day of [new Date("2026-09-29T19:00:00Z"), BEFORE_SECOND_LOCK, AT_SECOND_LOCK, new Date("2026-10-15T23:00:00Z")]) {
    await page.clock.install({ time: day });
    await page.goto("/judges");
    const main = page.getByRole("main");
    await expect(page.getByRole("heading", { name: "For judges", level: 1 })).toBeVisible();
    await expect(main).not.toContainText(ONE_SIDED);
    const nav = page.getByRole("navigation", { name: "For judges" });
    const row = (href: string) => nav.locator(".row").filter({ has: page.locator(`a[href="${href}"]`) });
    for (const href of ["/demo", "/t2/demo"]) {
      await expect(row(href)).toContainText(JUDGE_MODE_SHUT_WHILE);
      await expect(row(href)).toContainText(JUDGE_MODE_OPEN_FROM);
    }
    seen.push(await main.innerText());
  }
  for (const text of seen) expect(text).toBe(seen[0]);
});

// The two judge mode doors name an instant. It is the one the pages and the server open at, read
// here from apps/web/lib/lock.ts, which the design gate holds to core/lock.py. The shut pages say
// the same moment in the same words, so a judge never reads two times for one thing.
test("the judge mode doors name the instant judge mode opens, as lock.ts and the shut pages give it", () => {
  const lock = readFileSync(join(__dirname, "..", "lib", "lock.ts"), "utf8");
  const constant = (name: string): string => {
    const value = new RegExp(`^export const ${name} = "([^"]*)";$`, "m").exec(lock);
    if (value) return value[1];
    const alias = new RegExp(`^export const ${name} = ([A-Z][A-Z0-9_]*);$`, "m").exec(lock);
    expect(alias, `lock.ts holds no ${name}`).not.toBeNull();
    return constant(alias![1]);
  };
  const opens = new Date(constant("JUDGE_MODE_OPENS_UTC"));
  expect(Number.isNaN(opens.getTime())).toBe(false);
  const month = opens.toLocaleString("en-US", { month: "short", timeZone: "UTC" });
  const utc = `${month} ${opens.getUTCDate()} at ${String(opens.getUTCHours()).padStart(2, "0")}:${String(opens.getUTCMinutes()).padStart(2, "0")} UTC`;
  // "Friday Oct 2, 2026 at 21:00 PDT" in lock.ts is "Friday Oct 2 at 21:00 PDT" on the page.
  const local = constant("SECOND_LOCK_LOCAL_LABEL").replace(", 2026", "");
  expect(constant("JUDGE_MODE_OPENS_UTC")).toBe(constant("SECOND_LOCK_UTC"));
  expect(JUDGE_MODE_OPEN_FROM).toBe(`Open from ${utc}, which is ${local}.`);
  for (const key of ["judges.demo_note", "judges.assist_note"]) {
    expect(EN[key], key).toContain(JUDGE_MODE_SHUT_WHILE);
    expect(EN[key], key).toContain(JUDGE_MODE_OPEN_FROM);
    expect(EN[key], key).not.toMatch(ONE_SIDED);
    expect(EN[key], key).not.toMatch(OLD_DAYS);
  }
  const repoNotes = ["repo", "readme", "day", "qa", "report", "ai_example", "model_card"].map((k) => `judges.${k}_note`);
  for (const key of repoNotes) {
    expect(EN[key], key).toContain(PUBLIC_FROM);
    expect(EN[key], key).not.toMatch(OLD_DAYS);
  }
  for (const key of ["demo.shut_body", "part2.demo_shut_body"]) {
    expect(EN[key], key).toContain(`${utc}, which is ${local}.`);
  }
  expect(EN["demo.shut_title"]).toBe(`Judge mode opens on ${month} ${opens.getUTCDate()}`);
  // The repository goes public on the same day, some hours later.
  expect(PUBLIC_FROM).toBe(`The repository is public from ${month} ${opens.getUTCDate()}.`);
});

// Every door that was on the page before the AI's door moved up is still there, once each.
test("/judges keeps every door: eighteen, each to its own place", async ({ page }) => {
  await mockApi(page);
  await page.goto("/judges");
  const walk = content.walks[0];
  const hrefs = await page
    .getByRole("navigation", { name: "For judges" })
    .locator(".row a")
    .evaluateAll((links) => links.map((a) => a.getAttribute("href")));
  expect(hrefs).toEqual([
    "/demo",
    "/t2/demo",
    "/t?src=other",
    "/check",
    "/walk",
    `/walk/${walk.id}`,
    `/walk/${walk.id}`,
    "/two",
    "/how-we-know",
    `${REPO}#for-judges`,
    `${REPO}/blob/main/docs/JUDGE_DAY.md`,
    `${REPO}/blob/main/docs/submission/JUDGE_QA.md`,
    `${REPO}/blob/main/docs/REPORT.pdf`,
    `${REPO}/blob/main/docs/MODEL_CARD.md`,
    `${REPO}/blob/main/examples/footage-flag/README.md`,
    REPO,
    "/verify",
    "/credits",
  ]);
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

// CRITIC_03 E05 and E06: the /two door says what the page shows, and the footage door starts from
// the committed answer, which is the answer after force_answer, not the reply as the model sent it.
// Audit findings api-fhir-1 and docs-consistency-2: the door said "While the OneAquaHealth sandbox
// is down", and their sandbox answers again, at times. The Worker shows a stored copy of their
// record with the time it was fetched, or ours alone when no copy is stored (worker/src/two.ts),
// so the door says that, and it is true whether their sandbox answers or not.
test("the /two door is true whether their sandbox answers or not, and the footage door starts from the committed answer", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/judges");
  const nav = page.getByRole("navigation", { name: "For judges" });
  const door = (name: string) => nav.locator(".row").filter({ has: page.getByRole("link", { name, exact: true }) });
  const two = door("A volunteer record in the viewer built for laboratory results");
  await expect(two).toContainText(
    "The lab result is a copy from the OneAquaHealth sandbox, shown with the time it was fetched. If no copy is stored, our record shows alone and the page says so.",
  );
  await expect(two).not.toContainText(/is down|is up|answers again/i);
  // The door's two cases are the page's two cases.
  await page.unrouteAll({ behavior: "ignoreErrors" });
  await mockApi(page, { theirsStatus: "cached" });
  await page.goto("/two");
  await expect(page.getByText("Fetched from their sandbox at", { exact: false })).toBeVisible();
  await expect(page.getByRole("region", { name: "Lab (OneAquaHealth sandbox)" })).toBeVisible();
  await page.unrouteAll({ behavior: "ignoreErrors" });
  await mockApi(page, { theirsStatus: "down" });
  await page.goto("/two");
  await expect(page.getByText("Their sandbox did not answer, so only our record is shown.")).toBeVisible();
  await expect(page.getByRole("region", { name: "Volunteer (Second Look)" })).toBeVisible();
  await page.unrouteAll({ behavior: "ignoreErrors" });
  await mockApi(page);
  await page.goto("/judges");
  const footage = door("The checker at work on real creek footage");
  await expect(footage).toContainText("from the model's committed answer to the question a person would be asked");
  await expect(nav).not.toContainText("raw reply");
});

// Audit finding first-two-minutes-4: /judges opened with "Every part of Second Look, in the order
// that makes the point", which never said what Second Look is. Its first lines now say it.
test("/judges says in its first lines what Second Look is, and what the AI may do", async ({ page }) => {
  await mockApi(page);
  await page.goto("/judges");
  const intro = page.getByRole("main").locator("p").first();
  await expect(intro).toContainText(/^Second Look tests how well each volunteer sees four kinds of creek damage, and keeps that score with every observation they make\./);
  await expect(intro).toContainText("AI vision models take the same test. On a feature a model passed, it may ask a person to look again, and the person decides.");
  // The study's second wave has paid participants who take the test, so the line says where
  // nobody has used it: at a creek.
  await expect(intro).toContainText("No volunteer has used it at a creek yet.");
  // The first paragraph comes before the first door.
  const order = await page.getByRole("main").evaluate((main) => {
    const p = main.querySelector("p");
    const nav = main.querySelector("nav");
    return p && nav ? Boolean(p.compareDocumentPosition(nav) & Node.DOCUMENT_POSITION_FOLLOWING) : false;
  });
  expect(order).toBe(true);
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

// Audit finding first-two-minutes-1: this door was the last of eighteen, five screens down on a
// phone. It is the one place a judge meets the AI's question, so it is the second door.
test("the assisted second look door, to the AI's one question, is the second door and leads to part 2's judge mode", async ({ page }) => {
  await mockApi(page);
  await page.clock.install({ time: AT_SECOND_LOCK });
  await page.goto("/judges");
  const rows = page.getByRole("navigation", { name: "For judges" }).locator(".row");
  await expect(rows.nth(0).getByRole("link")).toHaveAttribute("href", "/demo");
  await expect(rows.nth(1).getByRole("link")).toHaveAttribute("href", "/t2/demo");
  await expect(rows.nth(1).getByRole("link")).toHaveText("The AI's one question, try it");
  await expect(rows.nth(2).getByRole("link")).toHaveAttribute("href", "/t?src=other");
  // On a phone the door was five and a half screens down. Now it starts the second screen, under
  // the first paragraph and the first door.
  const box = await rows.nth(1).getByRole("link").boundingBox();
  const screen = page.viewportSize();
  expect(box!.y + box!.height).toBeLessThan(2 * screen!.height);
  const door = page.getByRole("link", { name: "The AI's one question, try it" });
  await expect(door).toHaveCount(1);
  await door.click();
  // From the second lock on, judge mode starts.
  await expect(page.getByRole("heading", { level: 1, name: "Assisted second look, judge mode", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start judge mode" })).toBeVisible();
});

// UPDATE_33: judge mode is shut again while the second wave of the study runs. The door's line is
// honest about it: it says what the door is, that it is shut while the wave runs, when it opens,
// and when the checker's question appears. One second before the second lock the door leads to
// the shut page, which names the same moment as the door.
test("the door to the AI's one question says it is judge mode for part 2, shut while the second wave runs, and leads to the shut page before the second lock", async ({ page }) => {
  await mockApi(page);
  await page.clock.install({ time: BEFORE_SECOND_LOCK });
  await page.goto("/judges");
  const row = page.getByRole("navigation", { name: "For judges" }).locator(".row").nth(1);
  const line = row.locator(".row-value");
  await expect(line).toHaveText(EN["judges.assist_note"]);
  await expect(line).toContainText(/^Judge mode for part 2 of the test: eight photos as the assisted group of the study sees them\./);
  await expect(line).toContainText(JUDGE_MODE_SHUT_WHILE);
  await expect(line).toContainText(JUDGE_MODE_OPEN_FROM);
  await expect(line).toContainText("It asks you to look again only when its answer differs from yours, and you decide.");
  await row.getByRole("link").click();
  await expect(page.getByRole("heading", { level: 1, name: "Judge mode opens on Oct 3", exact: true })).toBeVisible();
  await expect(page.getByText(EN["part2.demo_shut_body"], { exact: true })).toBeVisible();
  await expect(page.getByRole("button")).toHaveCount(0);
  // The first door says the same of judge mode for the test itself, and leads to its shut page.
  await page.goto("/judges");
  const first = page.getByRole("navigation", { name: "For judges" }).locator(".row").nth(0);
  await expect(first.locator(".row-value")).toContainText(`It stores nothing. ${JUDGE_MODE_SHUT_WHILE} ${JUDGE_MODE_OPEN_FROM} About three minutes.`);
  await first.getByRole("link").click();
  await expect(page.getByRole("heading", { level: 1, name: "Judge mode opens on Oct 3", exact: true })).toBeVisible();
  await expect(page.getByText(EN["demo.shut_body"], { exact: true })).toBeVisible();
});
