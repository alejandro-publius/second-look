// Part 2 end to end on the Worker, locally (UPDATE_31): wrangler dev with a local D1, the schema
// and both slot files applied, every /api/t2 route driven over HTTP the way /t2 drives it.
//
//   cd worker && npm run e2e:part2
//
// What it proves: part 2 cannot start before part 1's score screen; the offer randomizes once per
// part 1 session, in blocks of 4 per part 1 arm; the question appears exactly when the committed
// flag disagrees, and only in the assisted arm; Keep and Change store the person's pick; resend,
// resume and the export work; judge mode is shut before the lock and stores nothing after it.
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const worker = join(here, "..");
const PORT = 8795; // beside e2e.mjs's 8791 to 8793, so the two can run at once
const AFTER_PORT = PORT + 1;
const QA_KEY = "e2e-qa-key-0123456789abcdef";
const EXPORT_TOKEN = "e2e-export-token-0123456789abcdef";
const BASE = `http://127.0.0.1:${PORT}`;
const PERSIST = join(worker, ".wrangler", "e2e-part2");
const PERSIST_AFTER = join(worker, ".wrangler", "e2e-part2-after");
const CONTENT = JSON.parse(readFileSync(join(worker, "src", "content.json"), "utf8"));
const FLAGS = CONTENT.part2_flags;
const GOLD = Object.fromEntries(CONTENT.part2_items.map((i) => [i.id, i.gold]));
const WRANGLER_ENV = { ...process.env, CI: "true", WRANGLER_SEND_METRICS: "false", NO_UPDATE_NOTIFIER: "1", FORCE_COLOR: "0" };
const WRANGLER_CLI = join(worker, "node_modules", "wrangler", "wrangler-dist", "cli.js");
const wranglerArgs = (args) => ["--no-warnings", WRANGLER_CLI, ...args];
const running = [];

function wrangler(args) {
  const r = spawnSync(process.execPath, wranglerArgs(args), { cwd: worker, encoding: "utf8", env: WRANGLER_ENV, stdio: ["ignore", "pipe", "pipe"], timeout: 180_000 });
  if (r.status !== 0 || r.error) {
    console.error(r.stdout, r.stderr);
    throw new Error(`wrangler ${args.join(" ")} failed`);
  }
  return r.stdout;
}
const d1 = (sql) => JSON.parse(wrangler(["d1", "execute", "second-look", "--local", "--persist-to", PERSIST, "--json", "--command", sql]))[0].results;

async function startDev(port, persist, vars) {
  const args = ["dev", "--local", "--port", String(port), "--persist-to", persist, "--compatibility-date", process.env.E2E_COMPAT_DATE ?? "2026-08-18", "--show-interactive-dev-session=false"];
  for (const [k, v] of Object.entries(vars)) args.push("--var", `${k}:${v}`);
  const proc = spawn(process.execPath, wranglerArgs(args), { cwd: worker, stdio: ["ignore", "pipe", "pipe"], env: WRANGLER_ENV });
  let log = "";
  proc.stdout.on("data", (d) => (log += d));
  proc.stderr.on("data", (d) => (log += d));
  running.push(proc);
  const end = Date.now() + 120_000;
  while (Date.now() < end) {
    try {
      if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) return proc;
    } catch {
      // not up yet
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  console.error(log);
  throw new Error("wrangler dev did not start");
}

async function api(method, path, body, headers = {}, base = BASE) {
  const res = await fetch(`${base}${path}`, {
    method,
    headers: body === undefined ? headers : { "content-type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  return { status: res.status, data, res };
}

const right = (id) => (GOLD[id] === "present" ? "yes" : "no");
const agreeing = (side) => (side === "present" ? "yes" : "no");
const disagreeing = (side) => (side === "present" ? "no" : "yes");

/** A part 1 sitting, finished or not. qa marks it a test the way the QA key does. */
async function part1({ finish = true, qa = false } = {}) {
  const s = await api("POST", "/api/test/session", {
    consent_version: "v1", content_hash: CONTENT.content_hash, build_hash: "e2e", source_label: "other", hidden_field: "",
    client_token_hash: `e2e-${Math.random().toString(16).slice(2)}-0123456789abcdef`, ua_class: "phone",
  }, qa ? { "x-qa-key": QA_KEY } : {});
  assert.equal(s.status, 200, JSON.stringify(s.data));
  if (!finish) return s.data;
  let position = 0;
  for (const id of s.data.item_order) {
    assert.equal((await api("POST", "/api/test/response", { session_id: s.data.session_id, item_id: id, answer: "cant_tell", rt_ms: 900, position: position++ })).status, 200);
  }
  assert.equal((await api("POST", "/api/test/complete", { session_id: s.data.session_id, prior_experience: "no", answered_count: 16 })).status, 200);
  return s.data;
}

let step = "start";
const at = (name) => {
  step = name;
  console.log(`part2 e2e: ${name}`);
};
const watchdog = setTimeout(() => {
  console.error(`part2 e2e: watchdog fired at "${step}"`);
  process.exit(3);
}, 10 * 60_000);
watchdog.unref();

try {
  at("apply schema and slots");
  spawnSync("rm", ["-rf", PERSIST, PERSIST_AFTER]);
  for (const f of ["schema.sql", "arms.sql", "part2_arms.sql"]) wrangler(["d1", "execute", "second-look", "--local", "--persist-to", PERSIST, "--file", f]);
  wrangler(["d1", "execute", "second-look", "--local", "--persist-to", PERSIST, "--command", "INSERT OR IGNORE INTO counter (id, next_position) VALUES (1, 0)"]);
  await startDev(PORT, PERSIST, { QA_KEY, EXPORT_TOKEN, E2E_NOW: "2026-09-28T00:59:59Z" });

  at("part 2 cannot start before part 1's score screen");
  const open = await part1({ finish: false });
  const early = await api("POST", "/api/t2/offer", { session_id: open.session_id, decision: "start" });
  assert.equal(early.status, 409, JSON.stringify(early.data));
  assert.match(early.data.detail, /after the score screen/);
  assert.equal((await api("POST", "/api/t2/offer", { session_id: "nope", decision: "start" })).status, 404);
  assert.equal((await api("POST", "/api/t2/offer", { session_id: open.session_id, decision: "maybe" })).status, 422);
  assert.deepEqual(d1("SELECT COUNT(*) AS n FROM part2_session"), [{ n: 0 }]);

  at("a decline is recorded and counted");
  const decliner = await part1();
  assert.deepEqual((await api("POST", "/api/t2/offer", { session_id: decliner.session_id, decision: "decline" })).data, { declined: true });
  assert.equal((await api("GET", "/api/t2/counts")).data.declined, 1);

  at("randomized once per part 1 session, blocks of 4 per part 1 arm");
  const started = [];
  for (let i = 0; i < 8; i++) {
    const p1 = await part1();
    const s = await api("POST", "/api/t2/offer", { session_id: p1.session_id, decision: "start" });
    assert.equal(s.status, 200, JSON.stringify(s.data));
    assert.equal(s.data.item_order.length, 8);
    const again = await api("POST", "/api/t2/offer", { session_id: p1.session_id, decision: "start" });
    assert.equal(again.data.part2_id, s.data.part2_id, "the same part 2 on a second offer");
    started.push({ ...s.data, part1_arm: p1.arm });
  }
  for (const stratum of ["untrained", "trained"]) {
    const rows = d1(`SELECT arm FROM part2_session WHERE part1_arm = '${stratum}' AND declined = 0 ORDER BY started_at, rowid LIMIT 4`);
    if (rows.length === 4) assert.equal(rows.filter((r) => r.arm === "assisted").length, 2, `block 0 of ${stratum} is 2 and 2`);
  }
  const assisted = started.find((s) => s.arm === "assisted");
  const unassisted = started.find((s) => s.arm === "unassisted");
  assert.ok(assisted && unassisted, "both arms appear in 8 starts");

  at("the question appears only for a disagreeing flag, only when assisted");
  const flagged = Object.keys(FLAGS).filter((id) => FLAGS[id] !== null);
  for (const [who, arm] of [[assisted, "assisted"], [unassisted, "unassisted"]]) {
    let position = 0;
    for (const id of who.item_order) {
      const side = FLAGS[id];
      const first = side ? disagreeing(side) : right(id);
      const r = await api("POST", "/api/t2/answer", { part2_id: who.part2_id, item_id: id, answer: first, t_first_ms: 4000, position: position++ });
      assert.equal(r.status, 200, JSON.stringify(r.data));
      assert.equal(r.data.ask, arm === "assisted" && side !== null, `${arm} ${id}`);
      if (r.data.ask) {
        // A different first answer never replaces the stored one, and a choice needs a question.
        assert.equal((await api("POST", "/api/t2/answer", { part2_id: who.part2_id, item_id: id, answer: agreeing(side), position: 0 })).status, 409);
      }
    }
  }
  if (flagged.length > 0) {
    const [keepId, changeId, cantTellId] = flagged;
    assert.equal((await api("POST", "/api/t2/choice", { part2_id: assisted.part2_id, item_id: keepId, choice: "keep", t_final_ms: 6000 })).status, 200);
    if (changeId) {
      assert.equal((await api("POST", "/api/t2/choice", { part2_id: assisted.part2_id, item_id: changeId, choice: "change", changed_to: "maybe" })).status, 422);
      assert.equal((await api("POST", "/api/t2/choice", { part2_id: assisted.part2_id, item_id: changeId, choice: "change", changed_to: "cant_tell", t_final_ms: 7000 })).status, 200);
      assert.equal((await api("POST", "/api/t2/choice", { part2_id: assisted.part2_id, item_id: changeId, choice: "keep" })).status, 409, "the first choice stays");
    }
    if (cantTellId) {
      assert.equal((await api("POST", "/api/t2/choice", { part2_id: assisted.part2_id, item_id: cantTellId, choice: "change", changed_to: agreeing(FLAGS[cantTellId]), t_final_ms: 7000 })).status, 200);
    }
    const stored = Object.fromEntries(d1(`SELECT item_id, first_answer, final_answer, question_shown, choice FROM part2_response WHERE part2_id = '${assisted.part2_id}'`).map((r) => [r.item_id, r]));
    assert.equal(stored[keepId].final_answer, stored[keepId].first_answer, "Keep stores the first answer");
    assert.equal(stored[keepId].choice, "keep");
    if (changeId) assert.equal(stored[changeId].final_answer, "cant_tell", "Change stores the person's pick, not the flag's side");
    for (const id of Object.keys(FLAGS).filter((i) => FLAGS[i] === null)) assert.equal(stored[id].question_shown, 0);
  }
  const unflaggedChoice = Object.keys(FLAGS).find((id) => FLAGS[id] === null);
  if (unflaggedChoice) {
    assert.equal((await api("POST", "/api/t2/choice", { part2_id: unassisted.part2_id, item_id: unflaggedChoice, choice: "change", changed_to: "yes" })).status, 409);
  }

  at("resend, resume and the score");
  const resumed = await api("GET", `/api/t2/resume?part2_id=${assisted.part2_id}`);
  assert.equal(resumed.data.completed, false);
  const fresh = started.find((s) => s !== assisted && s !== unassisted);
  const first = fresh.item_order[0];
  await api("POST", "/api/t2/answer", { part2_id: fresh.part2_id, item_id: first, answer: right(first), t_first_ms: 3000, position: 0 });
  const need = await api("POST", "/api/t2/complete", { part2_id: fresh.part2_id, answered_count: 8 });
  assert.equal(need.data.need_resend.length, fresh.arm === "assisted" && FLAGS[first] && FLAGS[first] !== GOLD[first] ? 8 : 7);
  let position = 1;
  for (const id of fresh.item_order.slice(1)) {
    const r = await api("POST", "/api/t2/answer", { part2_id: fresh.part2_id, item_id: id, answer: right(id), t_first_ms: 3000, position: position++ });
    if (r.data.ask) await api("POST", "/api/t2/choice", { part2_id: fresh.part2_id, item_id: id, choice: "keep", t_final_ms: 5000 });
  }
  const pendingFirst = (await api("GET", `/api/t2/resume?part2_id=${fresh.part2_id}`)).data.pending;
  if (pendingFirst) await api("POST", "/api/t2/choice", { part2_id: fresh.part2_id, item_id: pendingFirst, choice: "keep", t_final_ms: 5000 });
  const done = await api("POST", "/api/t2/complete", { part2_id: fresh.part2_id, answered_count: 8 });
  assert.deepEqual(done.data, { correct_total: 8, total: 8 }, "every right first answer kept is 8 of 8");
  assert.equal((await api("GET", `/api/t2/resume?part2_id=${fresh.part2_id}`)).data.correct_total, 8);
  assert.equal((await api("GET", "/api/t2/counts")).data.by_arm[fresh.arm].completed, 1);

  at("a QA part 1 makes a QA part 2, and a QA check names its arm without taking a slot");
  const qa = await part1({ qa: true });
  await api("POST", "/api/t2/offer", { session_id: qa.session_id, decision: "start" });
  assert.deepEqual(d1(`SELECT is_test FROM part2_session WHERE session_id = '${qa.session_id}'`), [{ is_test: 1 }]);
  const counters = () => d1("SELECT stratum, next_position FROM part2_counter ORDER BY stratum");
  const before = counters();
  for (const arm of ["assisted", "unassisted"]) {
    const s = await part1({ qa: true });
    const r = await api("POST", "/api/t2/offer", { session_id: s.session_id, decision: "start", qa_arm: arm }, { "x-qa-key": QA_KEY });
    assert.equal(r.data.arm, arm);
  }
  assert.deepEqual(counters(), before, "a QA check with its own arm takes no slot");
  const plain = await part1();
  const ignored = await api("POST", "/api/t2/offer", { session_id: plain.session_id, decision: "start", qa_arm: "assisted" });
  assert.equal(ignored.status, 200);
  assert.notDeepEqual(counters(), before, "without the key, qa_arm is ignored and a slot is taken");

  at("the export carries the columns the analysis reads");
  const res = await fetch(`${BASE}/api/test/export?token=${EXPORT_TOKEN}`);
  const bytes = new Uint8Array(await res.arrayBuffer());
  const text = new TextDecoder().decode(bytes);
  const analysis = readFileSync(join(worker, "..", "evals", "assist_analysis.py"), "utf8");
  for (const [file, constant] of [["part2_sessions.csv", "SESSION_COLUMNS"], ["part2_responses.csv", "RESPONSE_COLUMNS"]]) {
    const cols = [...new RegExp(`^${constant} = \\[([^\\]]*)\\]`, "m").exec(analysis)[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
    const head = text.slice(text.indexOf(file) + file.length).split("\r\n")[0];
    assert.equal(head, cols.join(","), `${file} header`);
  }

  at("judge mode: shut before the lock, feedback and nothing stored after it");
  assert.equal((await api("POST", "/api/t2/demo", { item_id: "a01", answer: "yes" })).status, 403);
  await startDev(AFTER_PORT, PERSIST_AFTER, { E2E_NOW: "2026-09-28T01:00:00Z" });
  const judge = await api("POST", "/api/t2/demo", { item_id: "a01", answer: right("a01") }, {}, `http://127.0.0.1:${AFTER_PORT}`);
  assert.equal(judge.status, 200);
  assert.equal(judge.data.correct, true);
  assert.equal(judge.data.ask, FLAGS.a01 !== null && FLAGS.a01 !== GOLD.a01);
  console.log(`part2 e2e: passed, ${flagged.length} flagged item(s) in the committed flags`);
} finally {
  for (const p of running) p.kill("SIGTERM");
}
