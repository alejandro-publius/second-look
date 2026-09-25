// The two cases /how-we-know shows from examples/footage-flag/example.json (CRITIC_03 D04): one
// frame where core/gate.py kept a model's flag, with the question it makes eligible, and one where
// the gate dropped it, with its reason. evals/footage_example.py writes the file from the paid
// footage run and make check holds it. lib/how-data.ts reads it when the page is built, with the
// run it names, and hands both here. Pure, so tests/how-we-know.spec.ts can hand it a changed copy.
//
// A case is null, and the page leaves it out, when the file does not say what the page would
// claim: a kept case the gate did not keep, a model that had not passed the feature, a question
// without its note, or a run file that does not say "real": true. The live site has the checker
// off today, so this record is the only place a checker question shows; it must be the real one.

/** @param {any} doc */
function isReal(doc) {
  return doc?.real === true && doc?.synthetic !== true;
}

/** @param {any} v */
function isText(v) {
  return typeof v === "string" && v.trim() !== "";
}

/** @param {any} n */
function isCount(n) {
  return Number.isInteger(n) && n >= 0;
}

/**
 * The parts both cases share: the frame, the model, the feature, the frame's credit and what the
 * pass table says about this model and feature. Null when one is missing.
 * @param {any} c
 */
function common(c) {
  const row = c?.manifest_row;
  const cell = c?.pass_table_cell;
  if (![c?.frame, c?.model, c?.feature, row?.author, row?.license, row?.source_url].every(isText)) return null;
  if (typeof cell?.passed !== "boolean" || ![cell.photos_per_run, cell.runs_with_every_photo_right, cell.runs].every(isCount)) {
    return null;
  }
  return {
    frame: c.frame,
    model: c.model,
    feature: c.feature,
    credit: { author: row.author, license: row.license, source_url: row.source_url },
    photos: cell.photos_per_run,
    right: cell.runs_with_every_photo_right,
    runs: cell.runs,
    // True only when the manifest row the file copies says, in so many words, that the frame has
    // no label: the field is there and empty (CRITIC_04 F02). The label itself never leaves here.
    unlabelled: row.gold_label === "",
  };
}

const ANSWERS = new Set(["yes", "no", "cant_tell"]);

/**
 * The other models that passed this feature on the test, each with its answers on this frame run
 * by run, from the file's same_frame_and_feature (CRITIC_04 F02). A model the file does not say
 * passed is left out, and so is a row that is not a list of answers.
 * @param {any} c
 */
function othersThatPassed(c) {
  const rows = Array.isArray(c?.same_frame_and_feature) ? c.same_frame_and_feature : [];
  return rows
    .filter(
      (r) =>
        isText(r?.model) &&
        r.model !== c.model &&
        r.passed_this_feature === true &&
        Array.isArray(r.answers_by_run) &&
        r.answers_by_run.length > 0 &&
        r.answers_by_run.every((a) => ANSWERS.has(a)),
    )
    .map((r) => ({ model: r.model, answers: [...r.answers_by_run] }));
}

/**
 * The kept model's own answers on the kept frame and feature, one per run in run order, read from
 * the run's answers in results/ rather than from the example file (CRITIC_11 V02). Empty when the
 * run does not list them, or lists one that is not an answer.
 * @param {any} c
 * @param {any} run
 * @returns {string[]}
 */
function ownAnswers(c, run) {
  const rows = Array.isArray(run?.answers) ? run.answers : [];
  const mine = rows
    .filter((a) => a?.frame === c.frame && a?.feature === c.feature && a?.model === c.model)
    .sort((a, b) => Number(a?.run) - Number(b?.run));
  if (!mine.every((a) => ANSWERS.has(a?.answer) && isCount(a?.run))) return [];
  return mine.map((a) => a.answer);
}

/**
 * @param {any} example the parsed examples/footage-flag/example.json, or null
 * @param {any} run the parsed results file the example names in run.results, or null
 * @returns {{
 *   date: string,
 *   files: string[],
 *   kept: null | { frame: string, model: string, feature: string, credit: { author: string, license: string, source_url: string },
 *     photos: number, right: number, runs: number, unlabelled: boolean, question: string, note: string,
 *     others: { model: string, answers: string[] }[], own: string[] },
 *   dropped: null | { frame: string, model: string, feature: string, credit: { author: string, license: string, source_url: string },
 *     photos: number, right: number, runs: number, unlabelled: boolean, not_passed: boolean, reasons: string[] },
 * } | null}
 */
export function footageCases(example, run) {
  if (!example || !isReal(run) || !isText(example.run?.results)) return null;

  let kept = null;
  const k = example.kept;
  const base = common(k);
  const screen = k?.followup?.on_screen;
  if (
    base &&
    k.gate?.kept === true &&
    k.pass_table_cell.passed === true &&
    Array.isArray(k.followup?.eligible) &&
    k.followup.eligible.length > 0 &&
    isText(screen?.question) &&
    isText(screen?.note)
  ) {
    kept = { ...base, question: screen.question, note: screen.note, others: othersThatPassed(k), own: ownAnswers(k, run) };
  }

  let dropped = null;
  const d = example.dropped;
  const dBase = common(d);
  const reasons = d?.gate?.drop_reasons;
  if (
    dBase &&
    d.gate?.kept === false &&
    Array.isArray(reasons) &&
    reasons.length > 0 &&
    reasons.every(isText) &&
    Array.isArray(d.followup?.eligible) &&
    d.followup.eligible.length === 0
  ) {
    // The plain words the page gives are "it did not pass this feature". They are said only when
    // the pass table cell says so and every reason the gate gave is that one; any other reason is
    // shown in the gate's own words alone.
    const notPassed =
      d.pass_table_cell.passed === false && reasons.every((r) => r.includes(`feature ${d.feature} not passed by model ${d.model}`));
    dropped = { ...dBase, not_passed: notPassed, reasons: [...reasons] };
  }

  if (!kept && !dropped) return null;
  return {
    date: String(example.run.generated_at_utc ?? ""),
    files: ["examples/footage-flag/example.json", example.run.results],
    kept,
    dropped,
  };
}
