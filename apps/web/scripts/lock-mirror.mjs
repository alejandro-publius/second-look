// The study's instants are written in three places: core/lock.py, which is the reference, and
// its mirrors apps/web/lib/lock.ts and worker/src/index.ts. This reads the first two as text and
// says where they differ. scripts/design-check.mjs runs it on every build, and
// scripts/tests/test_lock_mirror.py proves it on files made to differ. The Worker's copy is held
// to core/lock.py by scripts/tests/test_worker_lock.py and scripts/tests/test_lock_mirror.py.

/** Every instant and label the two files must both hold, with the same value. */
export const LOCK_NAMES = [
  "DATA_LOCK_UTC",
  "DATA_LOCK_LOCAL_LABEL",
  "WAVE2_OPEN_UTC",
  "WAVE2_OPEN_LOCAL_LABEL",
  "SECOND_LOCK_UTC",
  "SECOND_LOCK_LOCAL_LABEL",
  "JUDGE_MODE_OPENS_UTC",
];

const two = (n) => String(n).padStart(2, "0");
const INSTANT_OR_LABEL = /_(UTC|LOCAL_LABEL)$/;

/** Follows NAME = OTHER_NAME until a value, so JUDGE_MODE_OPENS_UTC reads as the second lock. */
function resolved(values, aliases) {
  const out = { ...values };
  for (const name of Object.keys(aliases)) {
    let at = name;
    const seen = new Set();
    while (aliases[at] !== undefined && !seen.has(at)) {
      seen.add(at);
      at = aliases[at];
    }
    if (values[at] !== undefined) out[name] = values[at];
  }
  return out;
}

/** The constants of core/lock.py: each datetime as an ISO instant, each label as written. */
export function pythonLockConstants(text) {
  const values = {};
  const aliases = {};
  for (const line of text.split("\n")) {
    const when = /^([A-Z][A-Z0-9_]*) = datetime\((\d+), (\d+), (\d+), (\d+), (\d+), (\d+), tzinfo=UTC\)$/.exec(line);
    const label = /^([A-Z][A-Z0-9_]*) = "([^"]*)"$/.exec(line);
    const alias = /^([A-Z][A-Z0-9_]*) = ([A-Z][A-Z0-9_]*)$/.exec(line);
    if (when) {
      const [, name, y, mo, d, h, mi, s] = when;
      values[name] = `${y}-${two(mo)}-${two(d)}T${two(h)}:${two(mi)}:${two(s)}Z`;
    } else if (label) values[label[1]] = label[2];
    else if (alias) aliases[alias[1]] = alias[2];
  }
  return resolved(values, aliases);
}

/** The exported constants of apps/web/lib/lock.ts, as written. */
export function webLockConstants(text) {
  const values = {};
  const aliases = {};
  for (const line of text.split("\n")) {
    const value = /^export const ([A-Z][A-Z0-9_]*) = "([^"]*)";$/.exec(line);
    const alias = /^export const ([A-Z][A-Z0-9_]*) = ([A-Z][A-Z0-9_]*);$/.exec(line);
    if (value) values[value[1]] = value[2];
    else if (alias) aliases[alias[1]] = alias[2];
  }
  return resolved(values, aliases);
}

/**
 * What is wrong between the two files, one plain line each; none when they agree. Every name in
 * LOCK_NAMES must be in both with one value, every instant must be a real time, and an instant
 * or label that only one file holds is a fault too, so a new one cannot be added to one side.
 */
export function lockMirrorFails(pythonText, webText) {
  const py = pythonLockConstants(pythonText);
  const ts = webLockConstants(webText);
  const out = [];
  const extra = [...Object.keys(py), ...Object.keys(ts)].filter((n) => INSTANT_OR_LABEL.test(n));
  for (const name of [...new Set([...LOCK_NAMES, ...extra])]) {
    if (py[name] === undefined) out.push(`core/lock.py:1 has no ${name}, or not in the form this check reads`);
    if (ts[name] === undefined) out.push(`apps/web/lib/lock.ts:1 has no ${name}, or not in the form this check reads`);
    if (py[name] === undefined || ts[name] === undefined) continue;
    if (py[name] !== ts[name]) out.push(`apps/web/lib/lock.ts:1 ${name} is ${ts[name]} but core/lock.py says ${py[name]}`);
    if (name.endsWith("_UTC") && Number.isNaN(Date.parse(ts[name]))) out.push(`apps/web/lib/lock.ts:1 ${name} is ${ts[name]}, which is not a time`);
  }
  return out;
}

/**
 * Callers of isBeforeLock other than the two judge mode pages. The name now answers whether judge
 * mode is shut (apps/web/lib/lock.ts says why), so a new caller that wants the first lock would
 * get the wrong answer. files is [{ path, text }], with path from the repo's root.
 */
export const BEFORE_LOCK_CALLERS = ["apps/web/app/demo/page.tsx", "apps/web/app/t2/demo/page.tsx", "apps/web/lib/lock.ts"];

export function strayBeforeLockCallers(files) {
  const out = [];
  for (const { path, text } of files) {
    if (BEFORE_LOCK_CALLERS.includes(path)) continue;
    text.split("\n").forEach((line, i) => {
      // A line of comment may name it; only code that imports or calls it counts.
      if (/^\s*(\/\/|\/?\*)/.test(line)) return;
      if (/\bisBeforeLock\b/.test(line)) out.push(`${path}:${i + 1} calls isBeforeLock, which now means judge mode is shut: use isJudgeModeShut, or DATA_LOCK_UTC for the first lock`);
    });
  }
  return out;
}
