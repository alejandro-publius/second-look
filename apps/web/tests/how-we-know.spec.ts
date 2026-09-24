import { expect, test, type Locator } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { footageCases } from "../lib/footage-example.mjs";
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

// CRITIC_03 D04: no volunteer has seen a checker question, because the checker is off on the live
// site today. /how-we-know shows the paid footage run's record instead: the kept flag with the
// question it makes eligible, and the dropped flag with the gate's reason, read from
// examples/footage-flag/example.json when the page is built.
const EXAMPLE = "examples/footage-flag/example.json";
const example = () => JSON.parse(readFileSync(join(ROOT, EXAMPLE), "utf8"));
const runOf = (doc: { run: { results: string } }) => JSON.parse(readFileSync(join(ROOT, doc.run.results), "utf8"));

test("/how-we-know shows the footage example's kept and dropped flags as examples/footage-flag/example.json says", async ({ page }) => {
  const doc = example();
  expect(runOf(doc).real).toBe(true);
  await page.goto("/how-we-know");
  await expect(page.getByText(en["how.example_intro"])).toBeVisible();
  expect(en["how.example_intro"]).toContain("On the live site the checker is off today");

  const rowValue = (card: Locator, key: string) => card.locator(".row").filter({ hasText: en[key] }).locator(".row-value");
  const credit = async (card: Locator, c: { manifest_row: { author: string; license: string; source_url: string } }) => {
    const line = card.getByTestId("frame-credit");
    await expect(line).toContainText(fill("how.example_credit", { author: c.manifest_row.author }));
    await expect(line.getByRole("link", { name: c.manifest_row.license, exact: true })).toHaveAttribute(
      "href",
      "https://creativecommons.org/licenses/by/3.0/",
    );
    await expect(line.getByRole("link", { name: en["credits.source"], exact: true })).toHaveAttribute("href", c.manifest_row.source_url);
  };

  // Kept: the frame, the model, the feature, that it passed, and the question with the note after
  // "the checker noticed", and nowhere else.
  const k = doc.kept;
  expect(k.gate.kept).toBe(true);
  const kept = page.getByTestId("example-kept");
  await expect(rowValue(kept, "how.example_frame")).toHaveText(k.frame);
  await expect(rowValue(kept, "how.example_model")).toHaveText(k.model);
  await expect(rowValue(kept, "how.example_feature")).toHaveText(featureName[k.feature]);
  const cell = k.pass_table_cell;
  expect(cell.passed).toBe(true);
  await expect(
    kept.getByText(fill("how.example_kept", { photos: cell.photos_per_run, right: cell.runs_with_every_photo_right, runs: cell.runs })),
  ).toBeVisible();
  await expect(kept.getByTestId("example-question").locator("strong")).toHaveText(k.followup.on_screen.question);
  await expect(kept.getByTestId("example-note")).toHaveText(`${en["label.checker_noticed"]}: ${k.followup.on_screen.note}`);
  await expect(page.getByText(k.followup.on_screen.note, { exact: false })).toHaveCount(1);
  await credit(kept, k);

  // Dropped: the model, the feature and the gate's reason in plain words, and in its own words.
  const d = doc.dropped;
  expect(d.gate.kept).toBe(false);
  const dropped = page.getByTestId("example-dropped");
  await expect(rowValue(dropped, "how.example_frame")).toHaveText(d.frame);
  await expect(rowValue(dropped, "how.example_model")).toHaveText(d.model);
  await expect(rowValue(dropped, "how.example_feature")).toHaveText(featureName[d.feature]);
  const dcell = d.pass_table_cell;
  expect(dcell.passed).toBe(false);
  await expect(
    dropped.getByText(fill("how.example_dropped", { photos: dcell.photos_per_run, right: dcell.runs_with_every_photo_right, runs: dcell.runs })),
  ).toBeVisible();
  await expect(dropped.getByTestId("example-reason")).toHaveText(d.gate.drop_reasons.join("; "));
  // The dropped flag's note is the model's text, and model text reaches a page only as a kept
  // flag's note (hard rule 5).
  await expect(page.locator("main")).not.toContainText(d.candidate_flag.note);
  await credit(dropped, d);

  await expect(
    page.getByText(fill("how.from", { files: `${EXAMPLE}, ${doc.run.results}`, date: day(doc.run.generated_at_utc) })),
  ).toBeVisible();
});

test("the footage example's reader follows the file: a changed copy changes what the page would show, and a run that is not real shows none", () => {
  const doc = example();
  const run = runOf(doc);
  const out = footageCases(doc, run)!;
  expect(out.kept).toMatchObject({
    frame: doc.kept.frame,
    model: doc.kept.model,
    feature: doc.kept.feature,
    question: doc.kept.followup.on_screen.question,
    note: doc.kept.followup.on_screen.note,
    right: doc.kept.pass_table_cell.runs_with_every_photo_right,
  });
  expect(out.dropped).toMatchObject({ frame: doc.dropped.frame, not_passed: true, reasons: doc.dropped.gate.drop_reasons });

  const copy = structuredClone(doc);
  copy.kept.frame = "v99-00001";
  copy.kept.model = "another-model";
  copy.kept.feature = "artificial_bank";
  copy.kept.followup.on_screen.question = "A changed question?";
  copy.kept.followup.on_screen.note = "A changed note.";
  copy.kept.pass_table_cell.runs_with_every_photo_right = 3;
  copy.kept.manifest_row.author = "Someone else";
  copy.dropped.model = "third-model";
  copy.dropped.feature = "invasive_plant";
  copy.dropped.gate.drop_reasons = ["flag 1: feature invasive_plant not passed by model third-model"];
  copy.dropped.pass_table_cell.runs_with_every_photo_right = 1;
  copy.run.generated_at_utc = "2026-10-01T00:00:00+00:00";
  const changed = footageCases(copy, run)!;
  expect(changed.kept).toMatchObject({
    frame: "v99-00001",
    model: "another-model",
    feature: "artificial_bank",
    question: "A changed question?",
    note: "A changed note.",
    right: 3,
    credit: { author: "Someone else" },
  });
  expect(changed.dropped).toMatchObject({ model: "third-model", feature: "invasive_plant", right: 1, not_passed: true });
  expect(changed.date).toBe("2026-10-01T00:00:00+00:00");

  // The page says "it had not passed" only when the file says so; any other reason is left to the
  // gate's own words.
  const other = structuredClone(doc);
  other.dropped.gate.drop_reasons = ["flag 1: note is empty"];
  expect(footageCases(other, run)!.dropped!.not_passed).toBe(false);

  // A kept case the gate did not keep, or by a model that had not passed the feature, is left out.
  const notKept = structuredClone(doc);
  notKept.kept.gate.kept = false;
  expect(footageCases(notKept, run)!.kept).toBeNull();
  const notPassed = structuredClone(doc);
  notPassed.kept.pass_table_cell.passed = false;
  expect(footageCases(notPassed, run)!.kept).toBeNull();
  const noNote = structuredClone(doc);
  delete noNote.kept.followup.on_screen.note;
  expect(footageCases(noNote, run)!.kept).toBeNull();

  // A run that is not real, or no file, shows nothing.
  expect(footageCases(doc, { ...run, real: false })).toBeNull();
  expect(footageCases(doc, { ...run, synthetic: true })).toBeNull();
  expect(footageCases(null, run)).toBeNull();
});
