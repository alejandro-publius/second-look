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
const QA_KEY = "e2e-qa-key-0123456789abcdef";
const BASE = `http://127.0.0.1:${PORT}`;
const PERSIST = join(worker, ".wrangler", "e2e-state");
const CONTENT = JSON.parse(readFileSync(join(worker, "src", "content.json"), "utf8"));

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

let dev = null;
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
  dev = spawn(
    process.execPath,
    wranglerArgs([
      "dev", "--local", "--port", String(PORT), "--persist-to", PERSIST,
      // The local runtime binary lags the edge; the date only has to be one this binary knows.
      "--compatibility-date", process.env.E2E_COMPAT_DATE ?? "2026-08-18",
      "--var", `QA_KEY:${QA_KEY}`, "--var", `RAIN_URL:http://127.0.0.1:${RAIN_PORT}/v1/forecast`,
      "--show-interactive-dev-session=false",
    ]),
    { cwd: worker, stdio: ["ignore", "pipe", "pipe"], env: WRANGLER_ENV },
  );
  let devLog = "";
  dev.stdout.on("data", (d) => (devLog += d));
  dev.stderr.on("data", (d) => (devLog += d));
  dev.on("exit", (code) => {
    if (code !== null && code !== 0) console.error(`wrangler dev exited with ${code}\n${devLog}`);
  });
  try {
    await waitFor(`${BASE}/health`, 120_000);
  } catch (err) {
    console.error(devLog);
    throw err;
  }

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
  // Read only: the route answers GET and nothing else.
  assert.equal((await api("POST", "/api/inaturalist/strawberry-creek", {})).status, 404);

  // 8b. Judge mode's answer route is shut until the data lock (review finding F86): before it,
  // sixteen answers would be the live test's key.
  at("judge mode shut before the lock");
  const demo = await api("POST", "/api/demo/answer", { item_id: "t01", answer: "yes" });
  if (Date.now() < Date.parse("2026-09-28T01:00:00Z")) {
    assert.equal(demo.status, 403);
    assert.equal(demo.data.detail, "Judge mode opens on Sep 28.");
  } else {
    assert.equal(demo.status, 200);
  }

  // 9. Bad input is a plain 422 or 404, never a 500.
  at("bad input");
  assert.equal((await api("POST", "/api/check/draft", { spot: GLADE, answers: { nothing: "x" }, first_rating: "good", photo_ids: [] })).status, 422);
  assert.equal((await api("POST", "/api/check/draft", { spot: { new: { name: "a@b", latitude: 1, longitude: 1, coarse: true } }, answers: {}, first_rating: null, photo_ids: [] })).status, 422);
  assert.equal((await api("POST", "/api/check/finalize", { draft_id: "visit-nowhere", followup_answers: {}, final_rating: "good" })).status, 404);
  assert.equal((await api("POST", "/api/check/draft", { contributor_token: "unknowntoken123", spot: GLADE, answers: {}, first_rating: null, photo_ids: [] })).status, 404);

  console.log(`worker e2e: ${sections} sections passed against wrangler dev on port`, PORT);
} finally {
  if (rain) rain.close();
  if (dev) {
    dev.kill("SIGTERM");
    await new Promise((resolve) => {
      const hard = setTimeout(() => {
        dev.kill("SIGKILL");
        resolve();
      }, 5000);
      dev.on("exit", () => {
        clearTimeout(hard);
        resolve();
      });
    });
  }
  clearTimeout(watchdog);
}
