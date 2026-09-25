import { expect, test, type Locator } from "@playwright/test";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { basename, join } from "node:path";
import { footageCases } from "../lib/footage-example.mjs";
import { howNumbers, keptSplit } from "../lib/how-numbers.mjs";

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
    // The two lines sit either side of a <br>, which textContent joins with nothing.
    const lines = fill("how.passed", { list: names(true) }) + fill("how.not_passed", { list: names(false) });
    await expect(rows.nth(i).locator(".row-value")).toHaveText(exactly(lines));
    // CRITIC_04 F02 and F04: the model by the name the README and the model card give it, never its API id.
    expect(en[`model.${model}`], `content/locales/en.json has no model.${model}`).toBeTruthy();
    await expect(rows.nth(i).locator(".row-label")).toHaveText(exactly(en[`model.${model}`] + lines));
  }
  await expect(page.getByTestId("pass-table")).not.toContainText(/claude-[a-z0-9-]+/);
  await expect(
    page.getByText(fill("how.from", { files: "results/model_pass_table.json", date: day(table.generated_at_utc) })),
  ).toBeVisible();

  // CRITIC_09 J03: after "kept 35", how many of those are on a dug-out channel and ask nothing, and
  // how many are the kept case below, from results/model_card.json.
  const card = result("model_card.json");
  const kept = example().kept.feature;
  await expect(page.getByTestId("gate-numbers")).toHaveText(
    exactly(
      fill("how.gate", {
        frames: pool.frames_kept,
        videos: pool.videos_kept,
        candidates: footage.gate.candidates,
        dropped: footage.gate.dropped,
        kept: footage.gate.kept,
      }) +
        " " +
        fill("how.gate_split", {
          nothing: card.footage_kept.by_feature.dug_out_channel,
          kept: footage.gate.kept,
          shown: card.footage_kept.by_feature[kept],
        }),
    ),
  );
  await expect(
    page.getByText(
      fill("how.from", {
        files: "results/footage_latest.json, results/footage_pool.json, results/model_card.json",
        date: day(footage.generated_at_utc),
      }),
    ),
  ).toBeVisible();

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

// CRITIC_09 J03: the split of the kept flags follows results/model_card.json. A changed copy
// changes the words, and a copy whose parts do not add up to the gate's kept count shows none.
test("the page's reader follows the model card's split of the kept flags", () => {
  const card = result("model_card.json");
  const gate = howNumbers(result("model_pass_table.json"), result("footage_latest.json"), result("footage_pool.json"), order).gate!;
  const feature = example().kept.feature;
  const by = card.footage_kept.by_feature;
  expect(keptSplit(card, gate, feature)).toEqual({ nothing: by.dug_out_channel, shown: by[feature] });

  // Two flags move from the kept case to the dug-out channel.
  const moved = structuredClone(card);
  moved.footage_kept.by_feature.dug_out_channel += 2;
  moved.footage_kept.by_feature[feature] -= 2;
  const out = keptSplit(moved, gate, feature)!;
  expect(out).toEqual({ nothing: by.dug_out_channel + 2, shown: by[feature] - 2 });
  const words = fill("how.gate_split", { nothing: out.nothing, kept: gate.kept, shown: out.shown });
  expect(words).toContain(`${by.dug_out_channel + 2} of the ${gate.kept} kept flags`);
  expect(words).toContain(`The other ${by[feature] - 2} are`);

  // Parts that are not the whole, a kept count the gate does not give, or a card that is not real.
  const short = structuredClone(card);
  short.footage_kept.by_feature.dug_out_channel -= 1;
  expect(keptSplit(short, gate, feature)).toBeNull();
  const other = structuredClone(card);
  other.footage_kept.kept += 1;
  expect(keptSplit(other, gate, feature)).toBeNull();
  expect(keptSplit({ ...card, real: false }, gate, feature)).toBeNull();
  expect(keptSplit(card, null, feature)).toBeNull();
  expect(keptSplit(card, gate, null)).toBeNull();
  expect(keptSplit(card, gate, "dug_out_channel")).toBeNull();
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
  // CRITIC_06 H02: a feature the creek check asks about, so a flag on it can make a question
  // eligible at all. The check has no item for a dug-out channel.
  const asked = new Set(content.form.items.map((i: { feature?: string | null }) => i.feature).filter(Boolean));
  expect(asked.has(k.feature)).toBe(true);
  expect(asked.has("dug_out_channel")).toBe(false);
  const kept = page.getByTestId("example-kept");
  await expect(rowValue(kept, "how.example_frame")).toHaveText(k.frame);
  await expect(rowValue(kept, "how.example_model")).toHaveText(en[`model.${k.model}`]);
  await expect(rowValue(kept, "how.example_feature")).toHaveText(featureName[k.feature]);
  const cell = k.pass_table_cell;
  expect(cell.passed).toBe(true);
  await expect(
    kept.getByText(fill("how.example_kept", { photos: cell.photos_per_run, right: cell.runs_with_every_photo_right, runs: cell.runs })),
  ).toBeVisible();
  await expect(kept.getByTestId("example-question").locator("strong")).toHaveText(k.followup.on_screen.question);
  // A note the checker cut at 160 characters is shown to its last whole word, then "...", never
  // stopping mid-word (CRITIC_07 J04).
  const note: string = k.followup.on_screen.note;
  const shown = note.length < 160 ? note : `${note.slice(0, note.lastIndexOf(" ")).replace(/[\s,;:.]+$/, "")}...`;
  await expect(kept.getByTestId("example-note")).toHaveText(`${en["label.checker_noticed"]}: ${shown}`);
  await expect(page.getByText(shown, { exact: false })).toHaveCount(1);
  if (note.length >= 160) expect(shown.endsWith("...") && note.startsWith(shown.slice(0, -3))).toBe(true);
  await credit(kept, k);

  // Dropped: the model, the feature and the gate's reason in plain words, and in its own words.
  const d = doc.dropped;
  expect(d.gate.kept).toBe(false);
  const dropped = page.getByTestId("example-dropped");
  await expect(rowValue(dropped, "how.example_frame")).toHaveText(d.frame);
  await expect(rowValue(dropped, "how.example_model")).toHaveText(en[`model.${d.model}`]);
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

// CRITIC_04 F02: the page credited two frames it did not show. Each frame now sits right above its
// card, served by the site byte for byte from the file its manifest row names, with an alt text of
// its own that says what is in the frame and gives no answer away. The kept card says what the
// other models that passed the feature answered on that frame, and both cards say nobody has
// labelled the frame, all as the example file says.
type SameFrame = { model: string; passed_this_feature: boolean; answers_by_run: string[] };
const ANSWER_KEY: Record<string, string> = { yes: "test.yes", no: "test.no", cant_tell: "test.cant_tell" };

test("/how-we-know shows each footage frame above its card, from its manifest row, with the other models' answers and no label", async ({ page, request }) => {
  const doc = example();
  const manifest = readFileSync(join(ROOT, "photos", "manifest.csv"), "utf8").split("\n");
  // id, file and sha256 lead every row and never hold a comma.
  const row = (id: string) => manifest.find((l) => l.startsWith(`${id},`))?.split(",");
  await page.goto("/how-we-know");

  for (const [which, c] of [
    ["kept", doc.kept],
    ["dropped", doc.dropped],
  ] as const) {
    const frame = page.getByTestId(`example-${which}-frame`);
    await expect(frame.locator("xpath=following-sibling::*[1]")).toHaveAttribute("data-testid", `example-${which}`);
    const img = frame.locator("img");
    await expect(img).toHaveAttribute("src", `/photos/${basename(c.manifest_row.file)}`);
    const alt = en[`photo.alt.${c.frame}`];
    expect(alt, `content/locales/en.json has no photo.alt.${c.frame}`).toBeTruthy();
    await expect(img).toHaveAttribute("alt", alt);
    // What is in the frame, never what the model, the gate or a label made of it (hard rule 17).
    expect(alt).not.toMatch(/straight|dug|deepen|channel|pipe|drain|outlet|sewage|built|concrete|invasive|flag|model|checker|label/i);
    await img.scrollIntoViewIfNeeded();
    await expect.poll(() => img.evaluate((el: HTMLImageElement) => (el.complete ? el.naturalWidth : 0))).toBeGreaterThan(0);
    // Served by the site, and the very file whose hash the manifest row holds (hard rule 6).
    const r = row(c.frame);
    expect(r, `photos/manifest.csv has no row ${c.frame}`).toBeTruthy();
    expect(r![1]).toBe(c.manifest_row.file);
    const served = await request.get(`/photos/${basename(r![1])}`);
    expect(served.status()).toBe(200);
    expect(createHash("sha256").update(await served.body()).digest("hex")).toBe(r![2]);
    // Both frames have no label in the file, and the card says so.
    expect(c.manifest_row.gold_label).toBe("");
    await expect(page.getByTestId(`example-${which}`).getByTestId("example-no-label")).toHaveText(en["how.example_no_label"]);
  }

  // Only these two benchmark frames reach the site, besides the walks' posters.
  const posters: string[] = content.walks.map((w: { poster_photo_id: string }) => w.poster_photo_id);
  const shownBenchmark = Object.values(content.photos as Record<string, { id: string; role: string }>)
    .filter((p) => p.role === "benchmark")
    .map((p) => p.id)
    .sort();
  expect(shownBenchmark).toEqual([...new Set([...posters, doc.kept.frame, doc.dropped.frame])].sort());
  const another = manifest.map((l) => l.split(",")).find((r) => /^v\d+-\d+$/.test(r[0]) && !shownBenchmark.includes(r[0]));
  expect(another, "a benchmark frame the site does not show").toBeTruthy();
  expect((await request.get(`/photos/${basename(another![1])}`)).status()).toBe(404);

  // The kept card: every other model that passed the feature, by name, with its answers.
  const others = (doc.kept.same_frame_and_feature as SameFrame[]).filter((m) => m.model !== doc.kept.model && m.passed_this_feature);
  expect(others.length).toBeGreaterThan(0);
  const lines = page.getByTestId("example-kept").getByTestId("example-other");
  await expect(lines).toHaveCount(others.length);
  for (const [i, o] of others.entries()) {
    // No in every run is said in those words; any other answers are listed run by run, as the file
    // gives them (on the built bank frame the others each said can't tell three times).
    const model = en[`model.${o.model}`];
    const words = o.answers_by_run.every((a) => a === "no")
      ? fill("how.example_other_no", { model, runs: o.answers_by_run.length })
      : fill("how.example_other_said", { model, answers: o.answers_by_run.map((a) => en[ANSWER_KEY[a]].toLowerCase()).join(", ") });
    await expect(lines.nth(i)).toHaveText(words);
  }
  await expect(page.getByTestId("example-dropped").getByTestId("example-other")).toHaveCount(0);
  // CRITIC_07 J03: when no other model that passed the feature said yes on the frame, the card says
  // so, and says that is why a flag can only ask.
  const noOtherYes = others.every((o) => !o.answers_by_run.includes("yes"));
  await expect(page.getByTestId("example-why-ask")).toHaveCount(noOtherYes ? 1 : 0);
  if (noOtherYes) await expect(page.getByTestId("example-why-ask")).toHaveText(en["how.example_why_ask"]);
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
  // CRITIC_04 F02: the other models that passed, with their answers, and whether the frame has a label.
  expect(out.kept!.others).toEqual(
    (doc.kept.same_frame_and_feature as SameFrame[])
      .filter((m) => m.model !== doc.kept.model && m.passed_this_feature)
      .map((m) => ({ model: m.model, answers: m.answers_by_run })),
  );
  expect([out.kept!.unlabelled, out.dropped!.unlabelled]).toEqual([true, true]);
  const labelled = structuredClone(doc);
  labelled.kept.manifest_row.gold_label = "present";
  delete labelled.dropped.manifest_row.gold_label;
  const lab = footageCases(labelled, run)!;
  // A label, or no word on it, is never read as no label, and the label itself goes nowhere.
  expect([lab.kept!.unlabelled, lab.dropped!.unlabelled]).toEqual([false, false]);
  expect(JSON.stringify(lab)).not.toContain("gold");
  const mixed = structuredClone(doc);
  const fable = (mixed.kept.same_frame_and_feature as SameFrame[]).find((m) => m.model === "claude-fable-5-1")!;
  fable.passed_this_feature = true;
  fable.answers_by_run = ["yes", "cant_tell", "no"];
  const sonnet = (mixed.kept.same_frame_and_feature as SameFrame[]).find((m) => m.model === "claude-sonnet-5")!;
  sonnet.passed_this_feature = false;
  const opus = (doc.kept.same_frame_and_feature as SameFrame[]).find((m) => m.model === "claude-opus-5-5")!;
  expect(opus.passed_this_feature).toBe(true);
  expect(footageCases(mixed, run)!.kept!.others).toEqual([
    { model: "claude-opus-5-5", answers: opus.answers_by_run },
    { model: "claude-fable-5-1", answers: ["yes", "cant_tell", "no"] },
  ]);

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
