import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { howNumbers } from "../lib/how-numbers.mjs";

// CRITIC_02 D03: /how-we-know shows the pass table and what the gate did on real footage, read
// from results/ when the page is built, never typed by hand (hard rule 12). The first test reads
// the files itself and compares; the second hands the page's reader a changed copy.
const ROOT = join(__dirname, "..", "..", "..");
const result = (name: string) => JSON.parse(readFileSync(join(ROOT, "results", name), "utf8"));
const en: Record<string, string> = JSON.parse(readFileSync(join(ROOT, "content", "locales", "en.json"), "utf8"));
const content = JSON.parse(readFileSync(join(__dirname, "..", "generated", "content.json"), "utf8"));
const order: string[] = content.features.map((f: { id: string }) => f.id);
const featureName: Record<string, string> = Object.fromEntries(
  content.features.map((f: { id: string; name: string }) => [f.id, f.name]),
);
const fill = (key: string, params: Record<string, string | number>) =>
  en[key].replace(/\{(\w+)\}/g, (whole, name: string) => (name in params ? String(params[name]) : whole));
const exactly = (s: string) => new RegExp(`^${s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`);
const day = (iso: string) => new Date(iso).toLocaleDateString("en-US", { dateStyle: "medium", timeZone: "UTC" });

test("/how-we-know shows the pass table and the gate on real footage as the files in results/ say", async ({ page }) => {
  const table = result("model_pass_table.json");
  const footage = result("footage_latest.json");
  const pool = result("footage_pool.json");
  // The page shows only a real run, and all three files are real, so all of it must be there.
  expect([table.real, footage.real, pool.real]).toEqual([true, true, true]);
  await page.goto("/how-we-know");

  const models = Object.keys(table.models);
  await expect(page.getByText(fill("how.pass_intro", { models: models.length }))).toBeVisible();
  const rows = page.getByTestId("pass-table").locator(".row");
  await expect(rows).toHaveCount(models.length);
  for (const [i, model] of models.entries()) {
    const byFeature = table.models[model];
    const names = (passed: boolean) =>
      order.filter((f) => byFeature[f] && byFeature[f].passed === passed).map((f) => featureName[f]).join(", ") || en["how.none"];
    await expect(rows.nth(i).locator(".hash")).toHaveText(model);
    // The two lines sit either side of a <br>, which textContent joins with nothing.
    await expect(rows.nth(i).locator(".row-value")).toHaveText(
      exactly(fill("how.passed", { list: names(true) }) + fill("how.not_passed", { list: names(false) })),
    );
  }
  await expect(
    page.getByText(fill("how.from", { files: "results/model_pass_table.json", date: day(table.generated_at_utc) })),
  ).toBeVisible();

  await expect(page.getByTestId("gate-numbers")).toHaveText(
    exactly(
      fill("how.gate", {
        frames: pool.frames_kept,
        videos: pool.videos_kept,
        candidates: footage.gate.candidates,
        dropped: footage.gate.dropped,
        kept: footage.gate.kept,
      }),
    ),
  );

  // Nobody typed a number into the page's own words: every number comes in through a placeholder.
  const typed = Object.entries(en).filter(([k, v]) => k.startsWith("how.") && /\d/.test(v.replace(/\{\w+\}/g, "")));
  expect(typed.map(([k]) => k)).toEqual([]);
});

test("the page's reader follows the files: a changed copy changes the numbers, and a run that is not real shows none", () => {
  const table = result("model_pass_table.json");
  const footage = result("footage_latest.json");
  const pool = result("footage_pool.json");

  const table2 = structuredClone(table);
  const footage2 = structuredClone(footage);
  const pool2 = structuredClone(pool);
  const [first] = Object.keys(table2.models);
  const feature = order[0];
  const wasPassed = table2.models[first][feature].passed === true;
  table2.models[first][feature].passed = !wasPassed;
  footage2.gate.dropped += 1;
  footage2.gate.candidates += 7;
  footage2.gate.kept += 6;
  pool2.frames_kept += 3;
  pool2.videos_kept += 2;

  const out = howNumbers(table2, footage2, pool2, order);
  expect(out.gate).toEqual({
    date: footage.generated_at_utc,
    frames: pool.frames_kept + 3,
    videos: pool.videos_kept + 2,
    candidates: footage.gate.candidates + 7,
    dropped: footage.gate.dropped + 1,
    kept: footage.gate.kept + 6,
  });
  const row = out.pass!.models.find((m: { model: string }) => m.model === first)!;
  expect(row.passed.includes(feature)).toBe(!wasPassed);
  expect(row.failed.includes(feature)).toBe(wasPassed);
  expect(out.pass!.models.map((m: { model: string }) => m.model)).toEqual(Object.keys(table.models));

  // A table from the fake client licenses nothing, so the page shows no pass table from it.
  expect(howNumbers({ ...table, real: false }, footage, pool, order).pass).toBeNull();
  expect(howNumbers({ ...table, synthetic: true }, footage, pool, order).pass).toBeNull();
  expect(howNumbers(table, { ...footage, real: false }, pool, order).gate).toBeNull();
  expect(howNumbers(table, footage, { ...pool, real: false }, order).gate).toBeNull();
  expect(howNumbers(null, null, null, order)).toEqual({ pass: null, gate: null });
});
