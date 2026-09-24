// The numbers /how-we-know shows, from three files in results/: which features each vision model
// passed (model_pass_table.json, written by evals/model_sweep.py) and what the gate did on real
// creek footage (footage_latest.json and footage_pool.json). lib/how-data.ts reads the files when
// the page is built and hands them here, so no number on the page is typed by hand (hard rule 12).
// Pure, so tests/how-we-know.spec.ts can hand it a changed copy of the files.
//
// A file that is missing, or that does not say "real": true, gives null, and the page leaves that
// part out. A pass table from the fake client licenses nothing (core/checker.py), so it is never
// shown as a result.

/** @param {any} doc */
function isReal(doc) {
  return doc?.real === true && doc?.synthetic !== true;
}

/** @param {any} n */
function isCount(n) {
  return Number.isInteger(n) && n >= 0;
}

/**
 * @param {any} passTable the parsed results/model_pass_table.json, or null
 * @param {any} footage the parsed results/footage_latest.json, or null
 * @param {any} pool the parsed results/footage_pool.json, or null
 * @param {string[]} featureOrder feature ids, in the order the site lists them
 * Each part's date is the run's generated_at_utc, as the file gives it.
 * @returns {{
 *   pass: { date: string, models: { model: string, passed: string[], failed: string[] }[] } | null,
 *   gate: { date: string, frames: number, videos: number, candidates: number, dropped: number, kept: number } | null,
 * }}
 */
export function howNumbers(passTable, footage, pool, featureOrder) {
  let pass = null;
  if (isReal(passTable) && passTable.models && typeof passTable.models === "object") {
    const models = Object.entries(passTable.models).map(([model, byFeature]) => {
      const tested = featureOrder.filter((f) => byFeature && typeof byFeature[f] === "object");
      return {
        model,
        passed: tested.filter((f) => byFeature[f].passed === true),
        failed: tested.filter((f) => byFeature[f].passed !== true),
      };
    });
    if (models.length) pass = { date: String(passTable.generated_at_utc ?? ""), models };
  }

  let gate = null;
  const g = footage?.gate;
  if (
    isReal(footage) &&
    isReal(pool) &&
    g &&
    [g.candidates, g.dropped, g.kept, pool.frames_kept, pool.videos_kept].every(isCount)
  ) {
    gate = {
      date: String(footage.generated_at_utc ?? ""),
      frames: pool.frames_kept,
      videos: pool.videos_kept,
      candidates: g.candidates,
      dropped: g.dropped,
      kept: g.kept,
    };
  }
  return { pass, gate };
}
