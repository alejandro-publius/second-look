import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { assertOnlyOurOrigins, mockApi, PART2_FLAGS, watchRequests } from "./mock-api.mjs";
import { answerItem, BASE } from "./helpers";

// Audit finding first-two-minutes-1: /t2/demo is the one place a judge meets the AI's question,
// and the door to it must say honestly what happens there. These tests hold the door's words to
// what the screens do, and to the committed flags the live Worker reads.
const AFTER_LOCK = new Date("2026-09-29T00:00:00Z");
const QUESTION = "The checker noticed something here. Look again?";
const ROOT = join(__dirname, "..", "..", "..");
const GENERATED = JSON.parse(readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"));
const EN: Record<string, string> = GENERATED.locale;
const ITEM_FOR_PHOTO_URL: Record<string, string> = Object.fromEntries(
  (GENERATED.part2_items as { id: string; photo_id: string }[]).map((i) => [GENERATED.photos[i.photo_id].url, i.id]),
);
const flags: Record<string, string | undefined> = PART2_FLAGS;
const sideAnswer = (side: string) => (side === "present" ? "Yes" : "No");

async function openFromJudges(page: Page) {
  await page.clock.install({ time: AFTER_LOCK });
  await page.goto("/judges");
  await page.getByRole("link", { name: EN["judges.assist"], exact: true }).click();
  await expect(page.getByRole("heading", { name: "Assisted second look, judge mode" })).toBeVisible();
  await page.getByRole("button", { name: "Start judge mode" }).click();
}

/** The part 2 item on screen, found through its photo, because judge mode shuffles the order. */
async function itemOnScreen(page: Page, n: number): Promise<string> {
  await expect(page.getByText(`Photo ${n} of 8`)).toBeVisible();
  const src = await page.locator("img.photo-large").getAttribute("src");
  const itemId = ITEM_FOR_PHOTO_URL[src!];
  expect(itemId, `no part 2 item shows ${src}`).toBeTruthy();
  return itemId;
}

const next = (page: Page, n: number) => page.getByRole("button", { name: n === 8 ? "Finish" : "Next photo", exact: true }).click();

test("the door's line is what judge mode does: Can't tell brings the question on every flagged photo, and nothing is stored", async ({ page }) => {
  const urls = watchRequests(page);
  const calls = await mockApi(page);
  await openFromJudges(page);
  const asked: string[] = [];
  for (let n = 1; n <= 8; n++) {
    const itemId = await itemOnScreen(page, n);
    await answerItem(page, "Can't tell");
    if (flags[itemId]) {
      // Can't tell is never the checker's answer, so a flagged photo always asks.
      await expect(page.getByText(QUESTION)).toBeVisible();
      asked.push(itemId);
      // The person decides: Keep keeps the answer given.
      await page.getByRole("button", { name: "Keep", exact: true }).click();
    }
    await expect(page.getByRole("status")).toHaveText(EN["demo.feedback_wrong"]);
    await expect(page.getByText(QUESTION)).toHaveCount(0);
    await next(page, n);
  }
  expect(asked.sort()).toEqual(Object.keys(flags).sort());
  await expect(page.getByText("Nothing from judge mode is stored.")).toBeVisible();
  // Nothing stored: judge mode speaks to its own route only, never to the study's.
  const api = calls.filter((c) => c.path.startsWith("/api/"));
  expect(api.length).toBeGreaterThanOrEqual(16);
  expect(api.filter((c) => c.path !== "/api/t2/demo").map((c) => c.path)).toEqual([]);
  expect(assertOnlyOurOrigins(urls, BASE)).toEqual([]);
});

test("a judge who answers as the checker did is never asked, as the door's line says", async ({ page }) => {
  await mockApi(page);
  await openFromJudges(page);
  for (let n = 1; n <= 8; n++) {
    const itemId = await itemOnScreen(page, n);
    const side = flags[itemId];
    await answerItem(page, side ? sideAnswer(side) : "No");
    // Straight to right or wrong, with no question on the way.
    await expect(page.getByRole("status")).toHaveText(new RegExp(`^(${EN["demo.feedback_correct"]}|${EN["demo.feedback_wrong"]})$`));
    await expect(page.getByTestId("part2-question")).toHaveCount(0);
    await next(page, n);
  }
  await expect(page.getByText("Nothing from judge mode is stored.")).toBeVisible();
});

// The door names the photos that bring the question on the live site. The live Worker reads the
// committed flags, results/assist_flags.json, so the door's words are held to that file: a flag on
// every photo about banks, a channel or a pipe, and none on a photo about plants.
test("the door names the features the committed flags cover, and says it never asks about plants", () => {
  const committed = JSON.parse(readFileSync(join(ROOT, "results", "assist_flags.json"), "utf8")) as {
    items: { item_id: string; feature: string; flag: { points_to: string } | null }[];
  };
  const flagged = (feature: string) => committed.items.filter((i) => i.feature === feature).map((i) => i.flag !== null);
  expect(committed.items).toHaveLength(8);
  expect(flagged("artificial_bank")).toEqual([true, true]);
  expect(flagged("dug_out_channel")).toEqual([true, true]);
  expect(flagged("pipe_running")).toEqual([true, true]);
  expect(flagged("invasive_plant")).toEqual([false, false]);
  for (const item of committed.items) if (item.flag) expect(["present", "absent"]).toContain(item.flag.points_to);

  const note = EN["judges.assist_note"];
  expect(note).toContain("It asks you to look again only when its answer differs from yours, and you decide.");
  expect(note).toContain("To see its question, answer Can't tell when asked about banks, a channel or a pipe.");
  expect(note).toContain("It never asks about plants, because the model did not pass that feature.");
  expect(note).toContain("stores nothing");
  expect(note).toContain("No model is called while you answer.");
});
