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

/** The feature the creek check has no question for, so a flag on it asks nothing. */
export const NOT_ASKED = "dug_out_channel";

/**
 * How the gate's kept flags split, from results/model_card.json#/footage_kept/by_feature: the ones
 * on a dug-out channel, which the creek check does not ask about, so they ask nothing, and the ones
 * on the feature of the kept case the page shows below (CRITIC_09 J03). Null, and the page says
 * nothing of a split, unless the model card is real, gives the same kept count as the gate, and the
 * two parts add up to all of it, so "the other" on the page is always the rest.
 *
 * The page names whose the rest are: the shown case's model, which said yes on the shown frame in
 * every one of its runs (CRITIC_11 V02). So the split is also null unless that model's own answers
 * on the frame, read from the run in results/, are all yes and are as many as the rest. A model
 * that passed the feature has every yes kept, so then the rest are exactly those answers.
 *
 * @param {any} modelCard the parsed results/model_card.json, or null
 * @param {{ kept: number } | null} gate the gate numbers howNumbers gave
 * @param {{ feature: string, model: string, own: string[] } | null | undefined} shownCase the kept case shown below
 * @returns {{ nothing: number, shown: number, model: string, runs: number } | null}
 */
export function keptSplit(modelCard, gate, shownCase) {
  const kept = modelCard?.footage_kept;
  const by = kept?.by_feature;
  const shownFeature = shownCase?.feature;
  if (!isReal(modelCard) || !gate || !by || typeof by !== "object" || !shownFeature || shownFeature === NOT_ASKED) return null;
  const nothing = by[NOT_ASKED];
  const shown = by[shownFeature];
  if (![nothing, shown, kept.kept, gate.kept].every(isCount)) return null;
  if (kept.kept !== gate.kept || nothing + shown !== gate.kept) return null;
  const own = Array.isArray(shownCase.own) ? shownCase.own : [];
  if (typeof shownCase.model !== "string" || own.length === 0 || own.length !== shown || !own.every((a) => a === "yes")) return null;
  return { nothing, shown, model: shownCase.model, runs: own.length };
}
