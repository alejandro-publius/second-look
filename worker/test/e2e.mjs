// The Worker end to end, locally: wrangler dev with a local D1 and KV, the schema applied, the
// arm sequence seeded, rain answered by a stub on this machine, and every judge facing route
// driven over HTTP the way the browser and the MCP server drive it. No network beyond localhost,
// except the two observer screen, which is allowed to say the sandbox is down.
//
//   cd worker && npm run e2e
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const worker = join(here, "..");
const PORT = Number(process.env.E2E_PORT ?? 8791);
const RAIN_PORT = PORT + 1;
// A second, short lived Worker whose clock reads the data lock itself (review REVIEW_03 R52).
const AFTER_PORT = PORT + 2;
const QA_KEY = "e2e-qa-key-0123456789abcdef";
const EXPORT_TOKEN = "e2e-export-token-0123456789abcdef";
const BASE = `http://127.0.0.1:${PORT}`;
const PERSIST = join(worker, ".wrangler", "e2e-state");
const PERSIST_AFTER = join(worker, ".wrangler", "e2e-state-after-lock");
const CONTENT = JSON.parse(readFileSync(join(worker, "src", "content.json"), "utf8"));
// Judge mode's lock (core/lock.py). The main Worker's clock is fixed one second before it, the
// second Worker's at it, so both sides of the lock run on every run, whatever today is.
const LOCK = "2026-09-28T01:00:00Z";
const JUST_BEFORE_LOCK = "2026-09-28T00:59:59Z";

// Wrangler never gets a terminal here: no metrics prompt, no update check, no stdin to wait on,
// and a hard time limit so a hang in CI fails with its output instead of eating the job. The
// real CLI script is run directly with this Node, not through npx and the bin launcher, which
// each spawn another process that a kill would leave behind holding the job's output pipes.
const WRANGLER_ENV = { ...process.env, CI: "true", WRANGLER_SEND_METRICS: "false", NO_UPDATE_NOTIFIER: "1", FORCE_COLOR: "0" };
const WRANGLER_CLI = join(worker, "node_modules", "wrangler", "wrangler-dist", "cli.js");
const wranglerArgs = (args) => ["--no-warnings", WRANGLER_CLI, ...args];

function wrangler(args, opts = {}) {
  const result = spawnSync(process.execPath, wranglerArgs(args), {
    cwd: worker,
    encoding: "utf8",
    env: WRANGLER_ENV,
    stdio: ["ignore", "pipe", "pipe"],
    timeout: 180_000,
    ...opts,
  });
  if (result.status !== 0 || result.error) {
    console.error(result.stdout, result.stderr, result.error?.message ?? "");
    throw new Error(`wrangler ${args.join(" ")} failed${result.error ? ` (${result.error.code})` : ""}`);
  }
  return result.stdout;
}

/** Rows from the local D1 the running Worker uses. */
function d1(sql) {
  const out = wrangler(["d1", "execute", "second-look", "--local", "--persist-to", PERSIST, "--json", "--command", sql]);
  return JSON.parse(out)[0].results;
}

/** wrangler dev on a port, with its own state folder and vars. The caller kills it. */
async function startDev(port, persist, vars, extra = []) {
  const args = [
    "dev", "--local", "--port", String(port), "--persist-to", persist,
    // The local runtime binary lags the edge; the date only has to be one this binary knows.
    "--compatibility-date", process.env.E2E_COMPAT_DATE ?? "2026-08-18",
    "--show-interactive-dev-session=false",
    ...extra,
  ];
  for (const [name, value] of Object.entries(vars)) args.push("--var", `${name}:${value}`);
  const proc = spawn(process.execPath, wranglerArgs(args), { cwd: worker, stdio: ["ignore", "pipe", "pipe"], env: WRANGLER_ENV });
  let log = "";
  proc.stdout.on("data", (d) => (log += d));
  proc.stderr.on("data", (d) => (log += d));
  proc.on("exit", (code) => {
    if (code !== null && code !== 0) console.error(`wrangler dev on ${port} exited with ${code}\n${log}`);
  });
  running.push(proc);
  try {
    await waitFor(`http://127.0.0.1:${port}/health`, 120_000);
  } catch (err) {
    console.error(log);
    throw err;
  }
  return proc;
}

async function stopDev(proc) {
  if (proc.exitCode !== null || proc.signalCode !== null) return;
  proc.kill("SIGTERM");
  await new Promise((resolve) => {
    const hard = setTimeout(() => {
      proc.kill("SIGKILL");
      resolve();
    }, 5000);
    proc.on("exit", () => {
      clearTimeout(hard);
      resolve();
    });
  });
}

/** The files of a zip written without compression, as the Worker's export writes it. */
function readStoredZip(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const files = {};
  let at = 0;
  while (at + 30 <= bytes.length && view.getUint32(at, true) === 0x04034b50) {
    assert.equal(view.getUint16(at + 8, true), 0, "stored, not compressed");
    const size = view.getUint32(at + 18, true);
    const nameLength = view.getUint16(at + 26, true);
    const extraLength = view.getUint16(at + 28, true);
    const start = at + 30 + nameLength + extraLength;
    const name = new TextDecoder().decode(bytes.slice(at + 30, at + 30 + nameLength));
    files[name] = new TextDecoder().decode(bytes.slice(start, start + size));
    at = start + size;
  }
  return files;
}

/** A column list from the Python API's export (apps/api/study.py), the schema the Worker must match. */
function pythonColumns(name) {
  const source = readFileSync(join(worker, "..", "apps", "api", "study.py"), "utf8");
  const found = new RegExp(`^${name} = \\[([^\\]]*)\\]`, "m").exec(source);
  assert.ok(found, `${name} in apps/api/study.py`);
  return [...found[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
}

// Whatever happens, this process ends: a stuck request cannot hold the CI job open.
const watchdog = setTimeout(() => {
  console.error(`worker e2e: watchdog fired at step "${step}"`);
  process.exit(3);
}, 10 * 60_000);
watchdog.unref();
let step = "start";
// The steps that only set up the database and start wrangler dev are not sections: the count
// printed at the end is the route sections, the same number scripts/count_tests.py writes.
const SETUP_STEPS = new Set(["apply schema and arms", "start wrangler dev"]);
let sections = 0;
const at = (name) => {
  step = name;
  if (!SETUP_STEPS.has(name)) sections += 1;
  console.log(`worker e2e: ${name}`);
};

// A dry week, every hour zero, so the dry pipe question is asked and asks about 5 or more days.
function rainPayload() {
  const hours = [];
  const start = Date.now() - 4 * 24 * 3600 * 1000;
  const startHour = Math.floor(start / 3600000) * 3600000;
  for (let i = 0; i < 24 * 6; i++) hours.push(new Date(startHour + i * 3600000).toISOString().slice(0, 16));
  return { hourly: { time: hours, precipitation: hours.map(() => 0) }, hourly_units: { time: "iso8601", precipitation: "mm" } };
}

async function waitFor(url, ms) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch {
      // not up yet
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error(`${url} did not answer in ${ms} ms`);
}

async function api(method, path, body, headers = {}) {
  const res = await fetch(`${BASE}${path}`, {
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

async function passingSession() {
  const created = await api("POST", "/api/test/session", {
    consent_version: "v1",
    content_hash: CONTENT.content_hash,
    build_hash: "e2e",
    source_label: "other",
    hidden_field: "",
    client_token_hash: `e2e-${Math.random().toString(16).slice(2)}-0123456789abcdef`,
    ua_class: "phone",
    warmup_choice: CONTENT.warmup_ids[0],
  }, { "x-qa-key": QA_KEY });
  assert.equal(created.status, 200, JSON.stringify(created.data));
  const gold = Object.fromEntries(CONTENT.test_items.map((i) => [i.id, i.gold]));
  let position = 0;
  for (const itemId of created.data.item_order) {
    const r = await api("POST", "/api/test/response", { session_id: created.data.session_id, item_id: itemId, answer: gold[itemId] === "present" ? "yes" : "no", rt_ms: 900, position: position++ });
    assert.equal(r.status, 200);
  }
  const done = await api("POST", "/api/test/complete", { session_id: created.data.session_id, prior_experience: "no", keep_score: true, answered_count: 16 });
  assert.equal(done.status, 200, JSON.stringify(done.data));
  assert.ok(done.data.scores.every((s) => s.correct === 4), "every feature 4 of 4");
  return done.data.contributor_token;
}

const GOOD_ANSWERS = {
  channel_form: "u_shape",
  bank_type: "present",
  draining_pipes: "present",
  water_flow: "slow",
  habitats: ["riffles", "sand_banks"],
  water_height_m: 0.3,
  invasive_species: "absent",
  feelings: ["joy:4", "fear:not_applicable"],
  overall_rating: "good",
};
const QUIET_ANSWERS = { ...GOOD_ANSWERS, bank_type: "absent", draining_pipes: "absent" };
const GLADE = { new: { name: "Faculty Glade bridge", latitude: 37.8716, longitude: -122.256, coarse: false } };
const PARK = { new: { name: "Daylighted reach in the park", latitude: 37.8666, longitude: -122.2885, coarse: false } };

async function visit(token, spot, answers) {
  const body = { spot, answers, first_rating: "good", photo_ids: [] };
  if (token) body.contributor_token = token;
  const draft = await api("POST", "/api/check/draft", body);
  assert.equal(draft.status, 200, JSON.stringify(draft.data));
  const asked = draft.data.followups.map((f) => f.rule_id);
  const answersBack = asked.includes("dry_pipe") ? { dry_pipe: "yes" } : {};
  const done = await api("POST", "/api/check/finalize", { draft_id: draft.data.draft_id, followup_answers: answersBack, final_rating: "good" });
  assert.equal(done.status, 200, JSON.stringify(done.data));
  return { ...done.data, asked, nearby: draft.data.nearby_spot };
}

// A tiny JPEG shaped file: SOI, an APP1 EXIF segment with a fake GPS tag, a DQT, a scan, EOI.
function jpegWithExif() {
  const exif = new TextEncoder().encode("Exif\0\0GPSLatitude=37.87");
  const app1 = [0xff, 0xe1, (exif.length + 2) >> 8, (exif.length + 2) & 0xff, ...exif];
  const dqt = [0xff, 0xdb, 0x00, 0x05, 0x00, 0x01, 0x02];
  const sos = [0xff, 0xda, 0x00, 0x04, 0x01, 0x00, 0x12, 0x34, 0x56, 0xff, 0xd9];
  return new Uint8Array([0xff, 0xd8, ...app1, ...dqt, ...sos]);
}

const running = [];
let rain = null;
try {
  // 1. Fresh local state: schema, arms, the counter row.
  at("apply schema and arms");
  spawnSync("rm", ["-rf", PERSIST]);
  wrangler(["d1", "execute", "second-look", "--local", "--persist-to", PERSIST, "--file", "schema.sql"]);
  wrangler(["d1", "execute", "second-look", "--local", "--persist-to", PERSIST, "--file", "arms.sql"]);
  wrangler(["d1", "execute", "second-look", "--local", "--persist-to", PERSIST, "--command", "INSERT OR IGNORE INTO counter (id, next_position) VALUES (1, 0)"]);

  // 2. The rain stub and the Worker.
  rain = createServer((req, res) => {
    res.setHeader("content-type", "application/json");
    res.end(JSON.stringify(rainPayload()));
  });
  await new Promise((r) => rain.listen(RAIN_PORT, "127.0.0.1", r));
  at("start wrangler dev");
  // --test-scheduled lets the walk section run the daily cron by hand, at /__scheduled.
  await startDev(PORT, PERSIST, {
    QA_KEY,
    RAIN_URL: `http://127.0.0.1:${RAIN_PORT}/v1/forecast`,
    EXPORT_TOKEN,
    E2E_NOW: JUST_BEFORE_LOCK,
  }, ["--test-scheduled"]);

  // 2a. Before anyone checks a creek. /two has no visit of ours to show, so it shows the golden
  // visit, which was made by hand, and says so (review REVIEW_03 R33). The first deploy's
  // /api/skeleton is gone: it wrote a row on any request, a GET included (REVIEW_03 R02).
  at("an empty store");
  const empty = await api("GET", "/api/two");
  assert.equal(empty.status, 200, JSON.stringify(empty.data));
  assert.equal(empty.data.ours_example, true, "the golden visit is labelled an example");
  assert.equal(empty.data.ours.id, "sl-obs-visit-0001-bank-type");
  assert.equal(empty.data.ours_place, "Strawberry Creek, campus reach, spot 1", "the place by name, not Location/sl-loc-spot-1");
  assert.equal((await api("GET", "/api/skeleton")).status, 404);
  assert.equal((await api("POST", "/api/skeleton", {})).status, 404);
  assert.deepEqual(d1("SELECT COUNT(*) AS n FROM skeleton_ping"), [{ n: 0 }], "no request wrote a skeleton row");

  // 3. Two people who passed, one pipe, one quiet visit downstream.
  at("sessions and visits");
  const alice = await passingSession();
  const bob = await passingSession();
  const first = await visit(alice, GLADE, GOOD_ANSWERS);
  assert.deepEqual(first.asked, ["dry_pipe", "rating_check"], "dry week: the dry pipe question, then the rating check");
  assert.equal(first.fhir_saved, true);
  const second = await visit(bob, { spot_id: first.spot_id }, GOOD_ANSWERS);
  const quiet = await visit(null, PARK, QUIET_ANSWERS);
  assert.deepEqual(quiet.asked, [], "nothing reported, nothing asked");
  // A third pin a few metres from the glade is offered the existing spot, not merged into it.
  const near = await api("POST", "/api/check/draft", { spot: { new: { name: "Glade again", latitude: 37.87162, longitude: -122.25602, coarse: false } }, answers: QUIET_ANSWERS, first_rating: "good", photo_ids: [] });
  assert.equal(near.data.nearby_spot?.spot_id, first.spot_id);
  assert.ok(near.data.nearby_spot.metres <= 30);

  // 4. The record: labels beside answers, the place, the FHIR with the sitting inside.
  at("the record");
  const record = await api("GET", `/api/spot/${first.spot_id}`);
  assert.equal(record.status, 200);
  assert.equal(record.data.visits.length, 2);
  const bank = record.data.visits[0].answers.find((a) => a.item_id === "bank_type");
  assert.match(bank.observer_label, /^4 of 4 on Built banks, tested /);
  assert.equal(bank.observer_passed, true);
  assert.equal(record.data.place.reach_slug, "south-fork-campus");
  assert.deepEqual(record.data.downstream_notes, []);
  const park = await api("GET", `/api/spot/${quiet.spot_id}`);
  assert.equal(park.data.place.reach_slug, "strawberry-creek-park");
  assert.deepEqual(park.data.downstream_notes.map((n) => n.feature).sort(), ["artificial_bank", "pipe_running"]);
  assert.match(park.data.downstream_notes[0].line, /^Upstream of here, 2 people reported /);

  const fhir = await api("GET", `/api/fhir/Bundle/${first.visit_id}`);
  assert.equal(fhir.status, 200);
  const types = fhir.data.entry.map((e) => e.resource.resourceType);
  assert.equal(types.filter((t) => t === "QuestionnaireResponse").length, 2, "the visit and the test sitting");
  assert.equal(types.at(-1), "Provenance");
  const sitting = fhir.data.entry.find((e) => e.resource.id.startsWith("sl-qr-test-")).resource;
  assert.equal(sitting.item.length, 4);
  const bySpot = await api("GET", `/api/spot/${first.spot_id}/fhir`);
  assert.equal(bySpot.data.id, `sl-visit-${second.visit_id}`, "the latest visit at the spot");
  const validation = await api("GET", "/api/fhir/validation");
  assert.equal(validation.data.errors, 0);
  assert.equal(validation.data.ig_commit, "b907cf0");

  // 5. The city: every number with its ids, the pipe with its referral, the notes below.
  at("the city");
  const city = await api("GET", "/api/city/strawberry-creek");
  assert.equal(city.status, 200, JSON.stringify(city.data));
  assert.equal(city.data.visits, 3);
  assert.equal(city.data.visit_ids.length, 3);
  assert.equal(city.data.pipes_worth_testing.length, 1);
  const pipe = city.data.pipes_worth_testing[0];
  assert.equal(pipe.observers, 2);
  assert.equal(pipe.referral, `/api/fhir/referral/${first.spot_id}`);
  assert.ok(city.data.downstream_notes.length >= 8, "two findings, four reaches below");
  assert.ok(city.data.findings.every((f) => f.visit_ids.length > 0 && f.fhir.length > 0));
  const finding = city.data.findings.find((f) => f.feature === "pipe_running");
  assert.equal(finding.passed_observers, 2);
  // The glade, and the "Glade again" pin that was offered the glade and never finalized: two
  // spots on the reach, two visits, because a spot is a spot even before anyone finishes a check.
  const glade = city.data.reaches.find((r) => r.slug === "south-fork-campus");
  assert.equal(glade.spots, 2);
  assert.equal(glade.visits, 2);
  assert.equal(city.data.reaches.find((r) => r.slug === "strawberry-creek-park").notes.length, 2);
  const byId = await api("GET", `/api/city/${record.data.spot.creek_id}`);
  assert.equal(byId.data.creek_slug, "strawberry-creek");
  const creeks = await api("GET", "/api/creeks");
  assert.equal(creeks.data.creeks[0].creek, "strawberry-creek");
  assert.equal(creeks.data.creeks[0].visits, 3);
  assert.equal((await api("GET", "/api/city/nowhere")).status, 404);
  assert.equal((await api("GET", "/api/city/example")).status, 404);

  // 6. The referral and the way back.
  at("the referral");
  const referral = await api("GET", pipe.referral);
  assert.equal(referral.status, 200, JSON.stringify(referral.data));
  const request = referral.data.entry.map((e) => e.resource).find((r) => r.resourceType === "ServiceRequest");
  assert.equal(request.reasonReference.length, 2);
  assert.equal(request.requester.reference, "Organization/sl-org");
  const example = await api("GET", pipe.example_result);
  assert.equal(example.status, 200);
  assert.ok(example.data.meta.tag.some((t) => t.code === "example"));
  assert.ok(JSON.stringify(example.data).includes("EXAMPLE"));
  assert.equal((await api("GET", `/api/fhir/referral/${quiet.spot_id}`)).status, 404, "a quiet spot has no referral");

  // 7. The quick check, and a photo with its metadata cut out.
  at("quick check and upload");
  const q = await api("POST", `/api/quick/${first.spot_id}`, { colour: "muddy", smell: "bad", pipe_running: "present" });
  assert.equal(q.status, 200);
  const form = new FormData();
  form.append("file", new Blob([jpegWithExif()], { type: "image/jpeg" }), "photo.jpg");
  const up = await fetch(`${BASE}/api/upload`, { method: "POST", body: form });
  assert.equal(up.status, 200);
  const upload = await up.json();
  assert.match(upload.photo_id, /^up-/);
  const back = await fetch(`${BASE}/api/photo/${upload.photo_id}?t=${upload.token}`);
  assert.equal(back.status, 200);
  const bytes = new Uint8Array(await back.arrayBuffer());
  assert.equal(new TextDecoder().decode(bytes).includes("GPSLatitude"), false, "the EXIF segment is gone");
  assert.equal(bytes[0], 0xff, "still a JPEG");
  assert.equal((await fetch(`${BASE}/api/photo/${upload.photo_id}?t=wrong`)).status, 404);
  assert.equal((await fetch(`${BASE}/api/photo/${upload.photo_id}`)).status, 404);
  const bad = new FormData();
  bad.append("file", new Blob([new TextEncoder().encode("not an image")], { type: "text/plain" }), "x.txt");
  assert.equal((await fetch(`${BASE}/api/upload`, { method: "POST", body: bad })).status, 422);

  // 8. Two observers. The Worker never fetches their sandbox; it shows what
  // scripts/cache_their_records.py stored. Nothing stored: ours stands alone and the screen is
  // told. A stored record: it comes back with the time it was fetched. The key is the one the
  // Mac script writes: the first 16 hex of sha256 over JSON.stringify of the query.
  at("two observers");
  const pair = await api("GET", "/api/two");
  assert.equal(pair.status, 200);
  assert.equal(pair.data.theirs_status, "down");
  assert.equal(pair.data.ours.resourceType, "Observation");
  // A stored visit now: a volunteer's answer, not the example, and its place by name.
  assert.equal(pair.data.ours_example, false);
  assert.ok(pair.data.ours.id.startsWith("sl-obs-visit-") && pair.data.ours.id !== "sl-obs-visit-0001-bank-type");
  assert.ok(["Faculty Glade bridge", "Daylighted reach in the park"].includes(pair.data.ours_place), pair.data.ours_place);
  const query = { subject: "Location/Loc-Almyros", code: "http://hl7.eu/fhir/ig/oah/CodeSystem/temporarySystem-oah-eu|dissolved-oxygen", _sort: "-date", _count: "1" };
  const key = `theirs-${createHash("sha256").update(JSON.stringify(query)).digest("hex").slice(0, 16)}`;
  const lab = JSON.stringify({ resourceType: "Observation", id: "lab-e2e", status: "final" }).replaceAll("'", "''");
  wrangler(["d1", "execute", "second-look", "--local", "--persist-to", PERSIST, "--command", `INSERT OR REPLACE INTO sandbox_cache (cache_key, body, status, fetched_at) VALUES ('${key}', '${lab}', 'ok', '2026-09-23T07:30:00Z')`]);
  const stored = await api("GET", "/api/two");
  assert.equal(stored.data.theirs_status, "cached");
  assert.equal(stored.data.theirs.id, "lab-e2e");
  assert.equal(stored.data.fetched_at, "2026-09-23T07:30:00Z");

  // 8a. The iNaturalist context line. The Worker never asks iNaturalist; it reads the copy
  // scripts/cache_inaturalist.py stored. Nothing stored: status none, and the page says "no recent
  // sightings on record". Stored: the sightings come back with their fetch time, but only on a
  // creek whose record answers the invasive plant question, only with links to iNaturalist, and
  // not one number on the city view moves.
  at("iNaturalist context");
  const inatBefore = await api("GET", "/api/inaturalist/strawberry-creek");
  assert.equal(inatBefore.status, 200, JSON.stringify(inatBefore.data));
  assert.equal(inatBefore.data.creek, "strawberry-creek");
  assert.equal(inatBefore.data.shown, true, "every visit above answered the invasive plant question");
  assert.equal(inatBefore.data.status, "none");
  assert.equal(inatBefore.data.fetched_at, null);
  assert.deepEqual(inatBefore.data.species, []);
  assert.equal(inatBefore.data.terms, "https://www.inaturalist.org/pages/terms");
  const cityBefore = await api("GET", "/api/city/strawberry-creek");
  const summary = JSON.stringify({
    since: "2023-09-24",
    radius_m: 300,
    species: [
      { taxon_id: 61317, name: "Himalayan blackberry", latin_name: "Rubus armeniacus", count: 3, last_observed: "2025-12-11", url: "https://www.inaturalist.org/observations?id=1,2,3" },
      { taxon_id: 1, name: "Not a link to iNaturalist", latin_name: "x", count: 1, last_observed: "2025-01-01", url: "https://example.org/" },
      { taxon_id: 3, name: "A yes, not a count", latin_name: "z", count: true, last_observed: "2025-02-02", url: "https://www.inaturalist.org/observations?id=4" },
    ],
  }).replaceAll("'", "''");
  wrangler(["d1", "execute", "second-look", "--local", "--persist-to", PERSIST, "--command", `INSERT OR REPLACE INTO inaturalist_cache (creek, body, fetched_at) VALUES ('strawberry-creek', '${summary}', '2026-09-24T07:45:00Z')`]);
  const inat = await api("GET", "/api/inaturalist/strawberry-creek");
  assert.equal(inat.data.status, "cached");
  assert.equal(inat.data.fetched_at, "2026-09-24T07:45:00Z");
  assert.equal(inat.data.radius_m, 300);
  assert.deepEqual(inat.data.species.map((s) => [s.name, s.count, s.last_observed]), [["Himalayan blackberry", 3, "2025-12-11"]], "the link that leaves iNaturalist and the count that is not a number are dropped");
  const byCreekId = await api("GET", `/api/inaturalist/${record.data.spot.creek_id}`);
  assert.equal(byCreekId.data.creek, "strawberry-creek", "a stored creek id reads the same row as its slug");
  const cityAfter = await api("GET", "/api/city/strawberry-creek");
  assert.deepEqual(cityAfter.data, cityBefore.data, "the city view is the same with or without the sightings");
  assert.equal(JSON.stringify(cityAfter.data).includes("Himalayan"), false);
  // A creek nobody has asked about invasive plants: the sightings are withheld, even when stored.
  const bridge = await visit(null, { new: { name: "Stone bridge", latitude: 35.3301, longitude: 25.1401, coarse: false } }, { channel_form: "u_shape" });
  const bridgeCreek = (await api("GET", `/api/spot/${bridge.spot_id}`)).data.spot.creek_id;
  wrangler(["d1", "execute", "second-look", "--local", "--persist-to", PERSIST, "--command", `INSERT OR REPLACE INTO inaturalist_cache (creek, body, fetched_at) VALUES ('${bridgeCreek}', '${summary}', '2026-09-24T07:45:00Z')`]);
  const withheld = await api("GET", `/api/inaturalist/${bridgeCreek}`);
  assert.equal(withheld.data.shown, false);
  assert.equal(withheld.data.status, "cached");
  assert.deepEqual(withheld.data.species, []);
  // A check left unfinished there does not open it, even when it answers the question.
  const unfinished = await api("POST", "/api/check/draft", { spot: { spot_id: bridge.spot_id }, answers: GOOD_ANSWERS, first_rating: "good", photo_ids: [] });
  assert.equal(unfinished.status, 200, JSON.stringify(unfinished.data));
  assert.equal((await api("GET", `/api/inaturalist/${bridgeCreek}`)).data.shown, false, "an unfinished check does not open the line");
  // Nor does a finished check at a pin whose name reads like a test, which /city leaves out too.
  const testPin = await visit(null, { new: { name: "test", latitude: 12.5, longitude: 12.5, coarse: false } }, GOOD_ANSWERS);
  const testCreek = (await api("GET", `/api/spot/${testPin.spot_id}`)).data.spot.creek_id;
  wrangler(["d1", "execute", "second-look", "--local", "--persist-to", PERSIST, "--command", `INSERT OR REPLACE INTO inaturalist_cache (creek, body, fetched_at) VALUES ('${testCreek}', '${summary}', '2026-09-24T07:45:00Z')`]);
  const onTestPin = await api("GET", `/api/inaturalist/${testCreek}`);
  assert.equal(onTestPin.data.status, "cached");
  assert.equal(onTestPin.data.shown, false, "a test pin does not open the line");
  assert.deepEqual(onTestPin.data.species, []);
  // One finished check at the bridge that answers the question opens the line for that whole
  // creek. The gate is per creek, not per person: this request carries no token and no check of
  // its own, and it gets the sightings, as a later volunteer on the record page would (REVIEW_03
  // R07). The words in inaturalist.ts, its Python twin and ADR 0011 say so.
  await visit(null, { spot_id: bridge.spot_id }, GOOD_ANSWERS);
  const freshViewer = await api("GET", `/api/inaturalist/${bridgeCreek}`);
  assert.equal(freshViewer.data.shown, true, "one finished answer on the creek opens it for every viewer");
  assert.deepEqual(freshViewer.data.species.map((s) => s.name), ["Himalayan blackberry"]);
  // Read only: the route answers GET and nothing else.
  assert.equal((await api("POST", "/api/inaturalist/strawberry-creek", {})).status, 404);

  // 8a2. A plant on the city view (CRITIC_06 H01). A check that reports only a plant that does not
  // belong is a finding the city sees, and it asks for no OneAquaHealth measure. The list of which
  // plants is no second answer. Made after /api/two, which shows the latest stored visit.
  at("a plant on the city view");
  const plantOnly = await visit(null, { new: { name: "Codornices Creek at the path", latitude: 37.89, longitude: -122.28, coarse: false } }, { ...QUIET_ANSWERS, invasive_species: "present", invasive_which: ["cant_tell"] });
  const plantCreek = (await api("GET", `/api/spot/${plantOnly.spot_id}`)).data.spot.creek_id;
  const plantCity = await api("GET", `/api/city/${plantCreek}`);
  assert.equal(plantCity.status, 200, JSON.stringify(plantCity.data));
  assert.equal(plantCity.data.visits, 1);
  assert.deepEqual(plantCity.data.findings.map((f) => [f.feature, f.feature_name, f.observers, f.visit_ids]), [["invasive_plant", "Plants that do not belong", 1, [plantOnly.visit_id]]]);
  assert.deepEqual(plantCity.data.needs, []);

  // 8a3. A finished video walk's demo record (UPDATE_30 section 1 item 3). Stored by its id in
  // walk_record and read back on any device; the same walk sent again is one record. Never
  // counted: the study counts, the creeks, the city view and /two do not move, and no spot, visit
  // or FHIR row is made, so the sandbox mirror cannot see it. The guards: the body's size, only
  // what a walk collects, the time window, the same headers as the other routes, a daily cap,
  // and the delete date, kept by the daily cron and by every new store.
  at("a video walk's demo record");
  const walkRule = (name) => Number(new RegExp(`export const ${name} = (\\d+);`).exec(readFileSync(join(worker, "src", "core", "walks.ts"), "utf8"))[1]);
  const WALK_DAILY_CAP = walkRule("WALK_DAILY_CAP");
  const WALK_MAX_BYTES = walkRule("WALK_MAX_BYTES");
  const walkId = CONTENT.walks[0].id;
  const secondsAgo = (s) => new Date(Date.now() - s * 1000).toISOString();
  const walkAnswers = { bank_type: "present", draining_pipes: "present", water_height_m: 0.5, habitats: ["riffles"], feelings: ["joy:3", "fear:not_applicable"] };
  const unmoved = async () => ({
    counts: (await api("GET", "/api/test/counts")).data,
    creeks: (await api("GET", "/api/creeks")).data,
    city: (await api("GET", "/api/city/strawberry-creek")).data,
    two: (await api("GET", "/api/two")).data,
    rows: d1("SELECT (SELECT COUNT(*) FROM spot) AS spots, (SELECT COUNT(*) FROM visit) AS visits, (SELECT COUNT(*) FROM fhir_bundle) AS bundles, (SELECT COUNT(*) FROM check_result) AS checks"),
  });
  const beforeWalk = await unmoved();
  const firstAt = secondsAgo(90);
  const storedWalk = await api("POST", "/api/walk", { walk_id: walkId, answers: walkAnswers, answered_at: firstAt });
  assert.equal(storedWalk.status, 200, JSON.stringify(storedWalk.data));
  const recordId = storedWalk.data.record_id;
  assert.match(recordId, /^walk-[0-9a-f]{16}$/);
  assert.equal(storedWalk.data.walk_id, walkId);
  const keptDays = (Date.parse(storedWalk.data.delete_after) - Date.now()) / 86_400_000;
  assert.ok(keptDays > 29.99 && keptDays <= 30, `deleted 30 days on, not ${keptDays}`);
  const creeksHeaders = (await api("GET", "/api/creeks")).res.headers;
  for (const name of ["content-type", "cache-control", "access-control-allow-origin", "access-control-allow-methods", "access-control-allow-headers"]) {
    assert.equal(storedWalk.res.headers.get(name), creeksHeaders.get(name), `${name} as on the other routes`);
  }
  const readWalk = await api("GET", `/api/walk/${recordId}`);
  assert.equal(readWalk.status, 200, JSON.stringify(readWalk.data));
  assert.deepEqual(readWalk.data.answers, walkAnswers);
  assert.equal(readWalk.data.answered_at, firstAt.replace(/\.\d{3}Z$/, "Z"));
  assert.equal(readWalk.res.headers.get("cache-control"), creeksHeaders.get("cache-control"));
  const walkTags = [readWalk.data.bundle, ...readWalk.data.bundle.entry.map((e) => e.resource)].map((r) => (r.meta?.tag ?? []).map((t) => t.code));
  assert.ok(walkTags.every((codes) => codes.includes("demo-walk")), "the demo tag on every resource");
  const resent = await api("POST", "/api/walk", { walk_id: walkId, answers: walkAnswers, answered_at: firstAt });
  assert.equal(resent.status, 200);
  assert.equal(resent.data.record_id, recordId, "the same walk sent again is the same record");
  const clash = await api("POST", "/api/walk", { walk_id: walkId, answers: { bank_type: "absent" }, answered_at: firstAt });
  assert.equal(clash.status, 409, JSON.stringify(clash.data));
  assert.deepEqual(d1("SELECT COUNT(*) AS n FROM walk_record"), [{ n: 1 }]);
  assert.deepEqual(await unmoved(), beforeWalk, "a walk is never counted, never a creek, never a visit");
  assert.equal((await api("GET", `/api/city/walk-${walkId}`)).status, 404, "the walk's demo creek is not a creek on the server");
  // Only what a walk collects, in a small body, dated when a phone could have made it.
  const refused = [
    [{ walk_id: "v99", answers: walkAnswers, answered_at: firstAt }, 404],
    [{ walk_id: walkId, answers: walkAnswers, answered_at: firstAt, note: "a note" }, 422],
    [{ walk_id: walkId, answers: { bank_type: "my own words" }, answered_at: firstAt }, 422],
    [{ walk_id: walkId, answers: { notes: "free text" }, answered_at: firstAt }, 422],
    [{ walk_id: walkId, answers: { habitats: [{ x: 1 }] }, answered_at: firstAt }, 422],
    [{ walk_id: walkId, answers: walkAnswers, answered_at: secondsAgo(8 * 86_400) }, 422],
    [{ walk_id: walkId, answers: walkAnswers, answered_at: secondsAgo(-3600) }, 422],
    [{ walk_id: walkId, answers: walkAnswers, answered_at: "soon" }, 422],
  ];
  for (const [body, status] of refused) {
    const r = await api("POST", "/api/walk", body);
    assert.equal(r.status, status, `${JSON.stringify(body)}: ${JSON.stringify(r.data)}`);
    assert.equal(typeof r.data.detail, "string");
  }
  const notJson = await fetch(`${BASE}/api/walk`, { method: "POST", headers: { "content-type": "application/json" }, body: "walk_id=v02" });
  assert.equal(notJson.status, 422);
  const large = await fetch(`${BASE}/api/walk`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ walk_id: walkId, answers: walkAnswers, answered_at: firstAt }) + " ".repeat(WALK_MAX_BYTES) });
  assert.equal(large.status, 413);
  // The same body sent in chunks, with no length declared: refused by the count of what came in.
  const chunked = new Blob([JSON.stringify({ walk_id: walkId, answers: walkAnswers, answered_at: firstAt }), " ".repeat(WALK_MAX_BYTES)]).stream();
  const streamed = await fetch(`${BASE}/api/walk`, { method: "POST", headers: { "content-type": "application/json" }, body: chunked, duplex: "half" });
  assert.equal(streamed.status, 413, "a body with no declared length is still measured");
  assert.equal((await api("GET", "/api/walk/walk-0000000000000000")).status, 404);
  assert.equal((await api("GET", "/api/walk/not-a-walk")).status, 404);
  assert.deepEqual(d1("SELECT COUNT(*) AS n FROM walk_record"), [{ n: 1 }], "nothing refused was stored");
  // The daily cap, over the whole server: the day is filled to one short of it by hand.
  const today = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
  const later = new Date(Date.now() + 29 * 86_400_000).toISOString().replace(/\.\d{3}Z$/, "Z");
  d1(`WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < ${WALK_DAILY_CAP - 2}) INSERT INTO walk_record (record_id, walk_id, answered_at, answers_json, bundle_json, created_at, delete_after) SELECT printf('walk-fill%012d', i), '${walkId}', '${today}', '{}', '{}', '${today}', '${later}' FROM n`);
  const last = await api("POST", "/api/walk", { walk_id: walkId, answers: walkAnswers, answered_at: secondsAgo(60) });
  assert.equal(last.status, 200, `the day's last place: ${JSON.stringify(last.data)}`);
  const overCap = await api("POST", "/api/walk", { walk_id: walkId, answers: walkAnswers, answered_at: secondsAgo(30) });
  assert.equal(overCap.status, 429, JSON.stringify(overCap.data));
  assert.equal((await api("POST", "/api/walk", { walk_id: walkId, answers: walkAnswers, answered_at: firstAt })).status, 200, "a stored walk sent again still gets its id");
  assert.deepEqual(d1("SELECT COUNT(*) AS n FROM walk_record"), [{ n: WALK_DAILY_CAP }]);
  // The delete date: past it, the record is not served, and the daily cron deletes the row.
  d1(`UPDATE walk_record SET delete_after = '2026-01-01T00:00:00Z' WHERE record_id = '${recordId}'`);
  assert.equal((await api("GET", `/api/walk/${recordId}`)).status, 404, "not served after its date");
  assert.equal((await api("GET", `/api/walk/${last.data.record_id}`)).status, 200);
  const cron = await fetch(`${BASE}/__scheduled?cron=${encodeURIComponent("17 4 * * *")}`);
  assert.equal(cron.status, 200, await cron.text());
  assert.deepEqual(d1(`SELECT COUNT(*) AS n FROM walk_record WHERE record_id = '${recordId}'`), [{ n: 0 }], "the daily cron deleted it");
  assert.deepEqual(d1("SELECT COUNT(*) AS n FROM walk_record"), [{ n: WALK_DAILY_CAP - 1 }], "and nothing else");
  assert.deepEqual(await unmoved(), beforeWalk, "still nothing counted");

  // 8a4. A walk runs the creek check's follow-up rules on its answers (judge walk W01). Overall
  // Good with an artificial bank, a sewage discharge and a pipe: the rating check is asked, and
  // the dry pipe question never is, because a clip has no weather. The store decides which
  // questions were asked, checks each answer, and keeps the checks with the record.
  at("a video walk's follow-up checks");
  const rated = { ...walkAnswers, overall_rating: "good", sewage_discharge: "present" };
  const ratedAt = secondsAgo(45);
  for (const [body, detail] of [
    [{ followup_answers: { dry_pipe: "yes" } }, "No follow-up called 'dry_pipe' was asked in this walk."],
    [{ followup_answers: { rating_check: "yes" } }, "rating_check: answer keep, change, skipped."],
    [{ followup_answers: { rating_check: "change" } }, "A changed rating needs the new rating."],
    [{ followup_answers: { rating_check: "keep" }, final_rating: "poor" }, "The final rating can differ from the first only when the rating check says change."],
  ]) {
    const r = await api("POST", "/api/walk", { walk_id: walkId, answers: rated, answered_at: ratedAt, ...body });
    assert.equal(r.status, 422, JSON.stringify(r.data));
    assert.equal(r.data.detail, detail);
  }
  assert.deepEqual(d1("SELECT COUNT(*) AS n FROM walk_checks"), [{ n: 0 }], "nothing refused was kept");
  const ratedBody = { walk_id: walkId, answers: rated, answered_at: ratedAt, followup_answers: { rating_check: "change" }, final_rating: "poor" };
  const ratedWalk = await api("POST", "/api/walk", ratedBody);
  assert.equal(ratedWalk.status, 200, JSON.stringify(ratedWalk.data));
  const ratedRead = (await api("GET", `/api/walk/${ratedWalk.data.record_id}`)).data;
  assert.equal(ratedRead.first_rating, "good");
  assert.equal(ratedRead.final_rating, "poor");
  assert.deepEqual(ratedRead.checks, [
    {
      rule_id: "rating_check",
      asked: true,
      question_text: "You rated this stream Good, but you also reported artificial banks, a sewage discharge. Do you want to keep your rating?",
      answer: "change",
      detail: { issues: "artificial banks, a sewage discharge", first_rating: "good", kind: "keep_rating" },
    },
  ]);
  assert.deepEqual((await api("POST", "/api/walk", ratedBody)).data, ratedWalk.data, "sent again, the same record");
  assert.equal((await api("POST", "/api/walk", { ...ratedBody, followup_answers: { rating_check: "keep" }, final_rating: null })).status, 409);
  // A walk stored without follow-ups, as before, reads back with none and its own rating.
  const plain = (await api("GET", `/api/walk/${last.data.record_id}`)).data;
  assert.deepEqual([plain.checks, plain.first_rating, plain.final_rating], [[], null, null]);
  // The checks go with their record: past its date the daily cron deletes both.
  d1(`UPDATE walk_record SET delete_after = '2026-01-01T00:00:00Z' WHERE record_id = '${ratedWalk.data.record_id}'`);
  const cronAgain = await fetch(`${BASE}/__scheduled?cron=${encodeURIComponent("17 4 * * *")}`);
  assert.equal(cronAgain.status, 200, await cronAgain.text());
  assert.deepEqual(d1("SELECT COUNT(*) AS n FROM walk_checks"), [{ n: 0 }], "the cron deleted the checks with their record");
  assert.deepEqual(await unmoved(), beforeWalk, "a walk's checks are never a creek check's");

  // 8b. Judge mode's answer route is shut until the data lock (review finding F86): before it,
  // sixteen answers would be the live test's key. This Worker's clock reads one second before
  // the lock; a second Worker's reads the lock itself, where the route opens (REVIEW_03 R52).
  at("judge mode shut before the lock");
  const demo = await api("POST", "/api/demo/answer", { item_id: "t01", answer: "yes" });
  assert.equal(demo.status, 403);
  assert.equal(demo.data.detail, "Judge mode opens on Sep 28.");

  at("judge mode open at the lock");
  spawnSync("rm", ["-rf", PERSIST_AFTER]);
  const afterLock = await startDev(AFTER_PORT, PERSIST_AFTER, { E2E_NOW: LOCK });
  const judge = async (itemId, answer) => {
    const res = await fetch(`http://127.0.0.1:${AFTER_PORT}/api/demo/answer`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ item_id: itemId, answer }) });
    return { status: res.status, data: await res.json() };
  };
  const t01 = CONTENT.test_items.find((i) => i.id === "t01");
  const right = t01.gold === "present" ? "yes" : "no";
  assert.deepEqual(await judge("t01", right), { status: 200, data: { correct: true } });
  assert.deepEqual(await judge("t01", right === "yes" ? "no" : "yes"), { status: 200, data: { correct: false } });
  assert.equal((await judge("t99", "yes")).status, 404);
  await stopDev(afterLock);

  // 8c. The public counts by source (review REVIEW_03 R48). Two real sittings, not marked as
  // tests: one from the panel's link and one whose source is a panel id pasted into the link,
  // which is not a label we keep and is stored as "other". Only finished real sittings count.
  at("counts by source");
  const finish = async (sourceLabel) => {
    const s = await api("POST", "/api/test/session", {
      consent_version: "v1",
      content_hash: CONTENT.content_hash,
      build_hash: "e2e",
      source_label: sourceLabel,
      hidden_field: "",
      client_token_hash: `e2e-${Math.random().toString(16).slice(2)}-0123456789abcdef`,
      ua_class: "phone",
    });
    assert.equal(s.status, 200, JSON.stringify(s.data));
    let position = 0;
    for (const itemId of s.data.item_order) {
      assert.equal((await api("POST", "/api/test/response", { session_id: s.data.session_id, item_id: itemId, answer: "cant_tell", rt_ms: 900, position: position++ })).status, 200);
    }
    assert.equal((await api("POST", "/api/test/complete", { session_id: s.data.session_id, prior_experience: "no", answered_count: 16 })).status, 200);
    return s.data.session_id;
  };
  const before = (await api("GET", "/api/test/counts")).data;
  assert.deepEqual(before.by_source, { poster: 0, chat: 0, friends: 0, creek_group: 0, other: 0, panel: 0 }, "the e2e's own sittings are tests");
  const panelSession = await finish("panel");
  const pastedSession = await finish("PROLIFIC_PID=abc");
  const counted = (await api("GET", "/api/test/counts")).data;
  assert.equal(counted.by_source.panel, 1, "the panel label is kept");
  assert.equal(counted.by_source.other, 1, "a label we do not keep is stored as other");
  assert.equal(counted.by_arm.untrained.completed + counted.by_arm.trained.completed, 2);

  // 8d. The anonymous export (review REVIEW_03 R20): without the token, or with a wrong one, the
  // route answers 404 as if it did not exist; with it, the two files in the Python API's schema.
  at("the export");
  assert.equal((await api("GET", "/api/test/export")).status, 404);
  assert.equal((await api("GET", "/api/test/export?token=wrong")).status, 404);
  assert.equal((await api("GET", `/api/test/export?token=${EXPORT_TOKEN.replace(/.$/, "x")}`)).status, 404, "one character off");
  const exported = await fetch(`${BASE}/api/test/export?token=${EXPORT_TOKEN}`);
  assert.equal(exported.status, 200);
  assert.equal(exported.headers.get("content-type"), "application/zip");
  const files = readStoredZip(new Uint8Array(await exported.arrayBuffer()));
  assert.deepEqual(Object.keys(files).sort(), ["responses.csv", "sessions.csv"]);
  const sessionLines = files["sessions.csv"].trimEnd().split("\r\n");
  const responseLines = files["responses.csv"].trimEnd().split("\r\n");
  assert.deepEqual(sessionLines[0].split(","), pythonColumns("SESSIONS_COLUMNS"));
  assert.deepEqual(responseLines[0].split(","), pythonColumns("RESPONSES_COLUMNS"));
  const sourceOf = (id) => sessionLines.find((l) => l.startsWith(`${id},`)).split(",")[3];
  assert.equal(sourceOf(panelSession), "panel");
  assert.equal(sourceOf(pastedSession), "other");
  assert.equal(responseLines.filter((l) => l.startsWith(`${panelSession},`)).length, 16);

  // 9. Bad input is a plain 422 or 404, never a 500.
  at("bad input");
  assert.equal((await api("POST", "/api/check/draft", { spot: GLADE, answers: { nothing: "x" }, first_rating: "good", photo_ids: [] })).status, 422);
  assert.equal((await api("POST", "/api/check/draft", { spot: { new: { name: "a@b", latitude: 1, longitude: 1, coarse: true } }, answers: {}, first_rating: null, photo_ids: [] })).status, 422);
  assert.equal((await api("POST", "/api/check/finalize", { draft_id: "visit-nowhere", followup_answers: {}, final_rating: "good" })).status, 404);
  assert.equal((await api("POST", "/api/check/draft", { contributor_token: "unknowntoken123", spot: GLADE, answers: {}, first_rating: null, photo_ids: [] })).status, 404);

  console.log(`worker e2e: ${sections} sections passed against wrangler dev on port`, PORT);
} finally {
  if (rain) rain.close();
  for (const proc of running) await stopDev(proc);
  clearTimeout(watchdog);
}
