import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mockApi } from "./mock-api.mjs";
import { answerAllItems, passConsent, pickWarmup } from "./helpers";

// Judge walk W09: the time quoted for one thing changed from one screen to the next. How long the
// test and the creek check take is written once, in time.test and time.check, and every screen
// but the landing page's frozen lines (docs/deviations.md, critic round 02 D11) quotes it from
// there, as {time.test} or {time.check}, which the content build fills in.
const ROOT = join(__dirname, "..", "..", "..");
const written: Record<string, string> = JSON.parse(readFileSync(join(ROOT, "content", "locales", "en.json"), "utf8"));
const built = JSON.parse(readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"));
const shown: Record<string, string> = built.locale;
const TEST = written["time.test"];
const CHECK = written["time.check"];

// The strings that say how long the test or the creek check takes.
const QUOTES_TEST = ["consent.what", "end.share", "share.card_line2", "share.cta", "poster.scan", "judges.take_test"];
const QUOTES_CHECK = ["check.intro", "judges.check_note", "judges.walks_note"];
// The landing page's two frozen lines, and the lesson's own time, which is another thing.
// Part 2's offer quotes its own time, word for word from UPDATE_31.
const TWO_MINUTES = ["landing.cta", "app.one_sentence", "end.lesson_offer", "part2.offer"];
// Other things with a time of their own: judge mode, reading one example, and reading the judge's
// day (critic round 14 R12).
const THREE_OF_ANOTHER_THING = ["judges.demo_note", "judges.ai_example_note", "judges.day_note"];

test("the test's time and the check's time are each written once, and the strings that quote them read them from there", () => {
  expect(TEST).toBe("about four minutes");
  expect(CHECK).toBe("about three minutes");
  for (const key of QUOTES_TEST) expect(written[key], key).toContain("{time.test}");
  for (const key of QUOTES_CHECK) expect(written[key], key).toContain("{time.check}");
  const saying = (re: RegExp) =>
    Object.entries(written)
      .filter(([key, value]) => !key.startsWith("time.") && re.test(value))
      .map(([key]) => key)
      .sort();
  expect(saying(/\bfour[ -]minutes?\b/i), "strings that write the test's time themselves").toEqual([]);
  expect(saying(/\bthree[ -]minutes?\b/i), "strings that write the check's time themselves").toEqual([...THREE_OF_ANOTHER_THING].sort());
  expect(saying(/\btwo[ -]minutes?\b/i), "strings that still say two minutes").toEqual([...TWO_MINUTES].sort());
  // The build filled every reference in, and the consent version is over the words as shown, so
  // a reference that reads the same leaves the version where it was.
  for (const key of [...QUOTES_TEST, ...QUOTES_CHECK]) expect(shown[key], key).not.toContain("{time.");
  const consent = Object.keys(shown).filter((k) => k.startsWith("consent.")).sort();
  const version = "en-" + createHash("sha256").update(consent.map((k) => `${k}=${shown[k]}`).join("\n")).digest("hex").slice(0, 12);
  expect(built.consent_version).toBe(version);
});

test("the consent, the poster, the judges' doors, the check and the share page quote the same times", async ({ page, request }) => {
  await mockApi(page);
  const noRaw = async () => expect(page.locator("body")).not.toContainText("{time.");
  const noTwo = async () => expect(page.getByRole("main")).not.toContainText(/two.minute/i);

  await page.goto("/t?src=other");
  await expect(page.getByText(`It takes ${TEST}.`)).toBeVisible();
  await noRaw();
  await noTwo();

  await page.goto("/poster");
  await expect(page.getByText(`Scan to find out. It takes ${TEST} with the lesson. Anonymous.`)).toBeVisible();
  await noRaw();
  await noTwo();

  await page.goto("/judges");
  const nav = page.getByRole("navigation", { name: "For judges" });
  await expect(nav.getByRole("link", { name: `Take the test, ${TEST} with its lesson` })).toHaveAttribute("href", "/t?src=other");
  await expect(nav).toContainText(`never by a model. It takes ${CHECK}.`);
  await expect(nav).toContainText(`It takes ${CHECK}, like the check itself.`);
  await noRaw();

  await page.goto("/check");
  await expect(page.getByText(`It takes ${CHECK}.`)).toBeVisible();
  await noRaw();

  await page.goto("/share/13");
  await expect(page.getByRole("link", { name: `Find out in ${TEST}` })).toHaveAttribute("href", "/t?src=friends");
  await noRaw();
  await noTwo();

  const card = await (await request.get("/api/share/13")).text();
  expect(card).toContain(`It takes ${TEST}. Can you beat me?`);
  expect(card).not.toMatch(/two.minute|\{time\./i);
});

test("the score screen's share text quotes the test's time", async ({ page }) => {
  await page.addInitScript(() => {
    const nav = navigator as Navigator & { share?: (d: ShareData) => Promise<void> };
    nav.share = async (d: ShareData) => {
      (window as unknown as { __shared: ShareData }).__shared = d;
    };
  });
  await mockApi(page, { lessonFirst: false });
  await page.goto("/t");
  await passConsent(page);
  await pickWarmup(page);
  await answerAllItems(page, () => "Yes");
  await page.getByRole("button", { name: "See my score" }).click();
  await expect(page.getByText("8 of 16 right")).toBeVisible();
  await page.getByRole("button", { name: "Share my score" }).click();
  const shared = await page.waitForFunction(() => (window as unknown as { __shared?: ShareData }).__shared?.text);
  expect(await shared.jsonValue()).toBe(`I spotted 8 of 16. It takes ${TEST}. Can you beat me?`);
});
