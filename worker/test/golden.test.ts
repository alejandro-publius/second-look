// The golden vectors: Python wrote worker/golden/*.json (evals/golden_vectors.py); the TypeScript
// ports must reproduce every expected output exactly. Run with npm test. The emitter's Bundles are
// also written to fhir/build/instances/ so the HL7 validator checks them in make check. The ts-
// Bundles an earlier run left there are deleted first, so the validator counts this code's only.

import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import CONTENT from "../src/content.json";
import { downstreamNote, findingsFromVisits, looksLikeATestName, metresBetween, nearestSpot, needsFromFindings, notesBelow, pipesWorthTesting } from "../src/core/act";
import { AssistError, QUESTION, flagSide, questionNeeded, settle } from "../src/core/assist";
import { checkBundle, emitVisit, fhirId } from "../src/core/fhir_emit";
import { exampleLabResult, isExample, referralBundle } from "../src/core/fhir_referral";
import { selectFollowups } from "../src/core/followups";
import { pickActions } from "../src/core/healthcard";
import { observerLabel } from "../src/core/labels";
import { pyRound } from "../src/core/pyround";
import { creekBySlug, placeSpot, reachOf, reachesBelow } from "../src/core/regions";
import { sha256Hex } from "../src/core/sha256";
import { WalkRecordError, isDemo, walkBundle, walkChecks, walkFollowups, walkRecord } from "../src/core/walks";
import { FHIR_JSON, PLAIN_JSON, fhirMediaType, operationOutcome } from "../src/fhir_http";
import worker from "../src/index";
import { storeUpload, stripJpeg } from "../src/uploads";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const golden = (name: string) => JSON.parse(readFileSync(join(root, "worker", "golden", `${name}.json`), "utf8"));
const instancesDir = join(root, "fhir", "build", "instances");

/** The Worker's Bundles in a folder: every ts-*.json. */
function tsBundles(dir: string): string[] {
  return readdirSync(dir).filter((f) => f.startsWith("ts-") && f.endsWith(".json")).sort();
}

/** Delete the ts- Bundles an earlier run wrote. The validator reads every file in the folder, so
 * one left from older code would be counted as if today's code had written it. */
function clearOldBundles(dir: string): string[] {
  mkdirSync(dir, { recursive: true });
  const old = tsBundles(dir);
  for (const f of old) rmSync(join(dir, f));
  return old;
}

// Once, before any test writes a Bundle.
clearOldBundles(instancesDir);
const written = new Set<string>();

function writeBundle(bundle: { id?: unknown }): void {
  const file = `ts-${String(bundle.id)}.json`;
  writeFileSync(join(instancesDir, file), JSON.stringify(bundle, null, 2) + "\n");
  written.add(file);
}

/** JSON with sorted keys, so two documents compare as data and not as key order. */
function canonical(value: unknown): string {
  return JSON.stringify(value, (_k, v) => {
    if (v && typeof v === "object" && !Array.isArray(v)) {
      return Object.fromEntries(Object.keys(v).sort().map((k) => [k, (v as Record<string, unknown>)[k]]));
    }
    return v;
  });
}

function same(actual: unknown, expected: unknown, name: string) {
  assert.equal(canonical(actual), canonical(expected), name);
}

test("helpers: sha256, Python rounding, fhir_id", () => {
  const doc = golden("helpers");
  for (const c of doc.sha256) same(sha256Hex(c.input.text), c.expected, `sha256 ${c.name}`);
  for (const c of doc.round) same(pyRound(c.input.value, c.input.digits), c.expected, `round ${c.name}`);
  for (const c of doc.fhir_id) same(fhirId(...c.input.parts), c.expected, `fhir_id ${c.name}`);
});

test("assist: part 2's question and the stored row, the flag never an answer", () => {
  const doc = golden("assist");
  same(QUESTION, doc.question, "the question's words");
  for (const c of doc.flag_side) same(flagSide(c.input.flags, c.input.item_id), c.expected, `flag_side ${c.name}`);
  for (const c of doc.question_needed) same(questionNeeded(c.input.arm, c.input.side, c.input.first), c.expected, `ask ${c.name}`);
  for (const c of doc.settle) {
    let got: unknown;
    try {
      got = settle(c.input.first, c.input.asked, c.input.choice, c.input.changed_to);
    } catch (e) {
      if (!(e instanceof AssistError)) throw e;
      got = { error: e.message };
    }
    same(got, c.expected, `settle ${c.name}`);
  }
});

test("followups: the selector, over the repository's own table and form", () => {
  const doc = golden("followups");
  // CRITIC_06 H02: the vectors hold checker flags, among them one on a feature with no form item.
  assert.ok(doc.cases.some((c: { input: { flags: unknown[] } }) => c.input.flags.length > 0), "no vector carries a flag");
  for (const c of doc.cases) {
    const chosen = selectFollowups(c.input.answers, c.input.site, c.input.observer, c.input.flags, CONTENT.followups, CONTENT.form_items, c.input.checker_enabled);
    same(chosen, c.expected, c.name);
  }
});

test("labels: k of 4, the date, the expired sentence", () => {
  const doc = golden("labels");
  for (const c of doc.cases) {
    same(observerLabel(c.input.score, c.input.feature_name, c.input.today, c.input.locale), c.expected, c.name);
  }
});

test("healthcard: approved sentences only, the same pick for the same seed", () => {
  const doc = golden("healthcard");
  for (const c of doc.cases) same(pickActions(c.input.sentences, c.input.seed), c.expected, c.name);
});

test("act: findings, needs, pipes worth testing, and both pin guards", () => {
  const doc = golden("act");
  for (const c of doc.findings_from_visits) same(findingsFromVisits(c.input.visits, c.input.finding_key_for), c.expected, c.name);
  for (const c of doc.needs_from_findings) same(needsFromFindings(c.input.findings, c.input.sentences), c.expected, c.name);
  for (const c of doc.pipes_worth_testing) same(pipesWorthTesting(c.input.visits, c.input.today), c.expected, c.name);
  for (const c of doc.looks_like_a_test_name) same(looksLikeATestName(c.input.name), c.expected, c.name);
  for (const c of doc.metres_between) {
    const d = metresBetween(c.input.lat1, c.input.lon1, c.input.lat2, c.input.lon2);
    assert.ok(Math.abs(d - c.expected) < 0.002, `${c.name}: ${d} vs ${c.expected}`);
  }
  for (const c of doc.nearest_spot) {
    const found = nearestSpot(c.input.latitude, c.input.longitude, c.input.spots, c.input.within);
    if (c.expected === null) assert.equal(found, null, c.name);
    else {
      assert.ok(found, c.name);
      assert.equal(found!.spot.spot_id, c.expected.spot_id, c.name);
      assert.ok(Math.abs(found!.metres - c.expected.metres) < 0.002, `${c.name}: ${found!.metres} vs ${c.expected.metres}`);
    }
  }
});

test("act: the downstream note, only where flows_into is set", () => {
  const doc = golden("act");
  for (const c of doc.downstream_note) same(downstreamNote(c.input.finding, c.input.feature_name, c.input.reaches_below), c.expected, c.name);
  for (const c of doc.notes_below) {
    const creek = c.input.creek;
    // A reach of another creek, when the case names one, or the creek's own reach by slug.
    const foreign = c.input.foreign_reach ?? null;
    const reachOfSpot = Object.fromEntries(
      Object.entries(c.input.reach_of as Record<string, string | null>).map(([spotId, slug]) => [
        spotId,
        slug === null ? null : foreign && foreign.slug === slug ? foreign : reachOf(creek, slug),
      ]),
    );
    same(notesBelow(c.input.findings, reachOfSpot, creek, c.input.labels), c.expected, c.name);
  }
});

test("regions: placement on a creek and a reach, and the reaches below", () => {
  const doc = golden("regions");
  for (const c of doc.place_spot) {
    const p = placeSpot(c.input.spot);
    const got = p === null ? null : { creek_slug: p.creek.slug, reach_slug: p.reach ? p.reach.slug : null };
    same(got, c.expected, c.name);
  }
  for (const c of doc.reaches_below) {
    const creek = creekBySlug(c.input.creek_slug)!;
    const reach = reachOf(creek, c.input.reach_slug)!;
    same(reachesBelow(reach, creek).map((r) => r.slug), c.expected, c.name);
  }
});

test("fhir_emit: the same Bundle as Python, and it passes the structural check", () => {
  const doc = golden("fhir_emit");
  for (const c of doc.cases) {
    const bundle = emitVisit(c.input.visit, c.input.test_sitting, c.input.emitted_at);
    same(bundle, c.expected, c.name);
    assert.deepEqual(checkBundle(bundle), [], `${c.name}: structural check`);
    writeBundle(bundle);
  }
  // A fullUrl used twice is caught (bdl-7), as the HL7 validator would.
  const doubled = emitVisit(doc.cases[0].input.visit, doc.cases[0].input.test_sitting, doc.cases[0].input.emitted_at) as { entry: unknown[] };
  doubled.entry.push(JSON.parse(JSON.stringify(doubled.entry[2])));
  assert.ok(checkBundle(doubled as never).some((p) => p.includes("appears twice")));
  // And a broken Bundle is caught, so the check is not a rubber stamp.
  const broken = emitVisit(doc.cases[0].input.visit, doc.cases[0].input.test_sitting, doc.cases[0].input.emitted_at) as { entry: { resource: Record<string, unknown> }[] };
  const prov = broken.entry.find((e) => e.resource.resourceType === "Provenance")!;
  (prov.resource.target as { reference: string }[]).push({ reference: "Observation/nowhere" });
  assert.ok(checkBundle(broken as never).some((p) => p.includes("does not resolve")));
});

test("fhir_emit: a rating changed at the rating check is the value, and the first is a component", () => {
  type Obs = { id: string; valueCodeableConcept: { coding: { code: string }[] }; component: { code: { coding: { code: string }[] }; valueCodeableConcept: { coding: { code: string }[] } }[] };
  type Entry = { resource: { resourceType: string; id: string; item?: { linkId: string; answer: { valueCoding: { code: string } }[] }[]; target?: { reference: string }[] } };
  const base = golden("fhir_emit").cases.find((c: { name: string }) => c.name.startsWith("a coarse pin")).input.visit;
  assert.equal(base.answers.overall_rating, "good", "the app stores the first rating as the answer");
  const rated = (first: string | null, final: string | null) => {
    const bundle = emitVisit({ ...base, first_rating: first, final_rating: final }, null, "2026-09-26T09:16:00Z") as { entry: Entry[] };
    const byType = (t: string) => bundle.entry.map((e) => e.resource).filter((r) => r.resourceType === t);
    const qr = byType("QuestionnaireResponse").at(-1)!;
    const answered = qr.item!.find((i) => i.linkId === "overall_rating")!.answer[0].valueCoding.code;
    const ratings = byType("Observation").filter((o) => o.id.endsWith("-overall-rating")) as unknown as Obs[];
    return { bundle, answered, ratings, provenance: byType("Provenance")[0] };
  };
  const changed = rated("good", "poor");
  assert.deepEqual(checkBundle(changed.bundle as never), []);
  assert.equal(changed.answered, "poor", "the response answers the kept rating");
  assert.equal(changed.ratings.length, 1);
  const [obs] = changed.ratings;
  assert.equal(obs.valueCodeableConcept.coding[0].code, "poor", "the value is the kept rating");
  assert.equal(obs.component.length, 1);
  assert.equal(obs.component[0].code.coding[0].code, "first-rating");
  assert.equal(obs.component[0].valueCodeableConcept.coding[0].code, "good", "the component is the first rating");
  assert.ok(changed.provenance.target!.some((t) => t.reference === `Observation/${obs.id}`));
  assert.equal(base.answers.overall_rating, "good", "the stored answers stay as given");
  // A rating the check did not change adds no rating Observation and answers the rating given.
  for (const [first, final] of [["good", "good"], ["good", null], [null, null], [null, "good"]] as const) {
    const same = rated(first, final);
    assert.equal(same.ratings.length, 0, `${first} then ${final}`);
    assert.equal(same.answered, "good");
  }
});

test("fhir_referral: the ServiceRequest and the example result, the same as Python", () => {
  const doc = golden("fhir_emit");
  const [referral, example] = doc.referral;
  const made = referralBundle(referral.input.pipe, referral.input.bundles, referral.input.emitted_at);
  same(made, referral.expected, referral.name);
  assert.equal(isExample(made), false, "a referral is real");
  const result = exampleLabResult(example.input.referral, example.input.collected_at, example.input.reported_at);
  same(result, example.expected, example.name);
  assert.equal(isExample(result), true, "the way back is an example, and says so");
  writeBundle(made);
  writeBundle(result);
});

test("walks: the same demo Bundle as Python, tagged on every resource, and structurally sound", () => {
  const doc = golden("walks");
  for (const c of doc.cases) {
    const bundle = walkBundle(c.input.walk, c.input.answers, c.input.answered_at, c.input.final_rating ?? null);
    same(bundle, c.expected, c.name);
    assert.deepEqual(checkBundle(bundle as never), [], `${c.name}: structural check`);
    assert.ok(isDemo(bundle), `${c.name}: the Bundle carries the demo tag`);
    for (const e of bundle.entry as { resource: Record<string, never> }[]) {
      assert.ok(isDemo(e.resource), `${c.name}: ${String(e.resource.resourceType)} carries the demo tag`);
    }
    writeBundle(bundle);
  }
});

test("walks: the stored row of a finished walk, or the same reason to refuse it, as Python", () => {
  const doc = golden("walks");
  assert.ok(doc.record_cases.length >= 5, "cases that store and cases that refuse");
  let stored = 0;
  for (const c of doc.record_cases) {
    let got: unknown;
    try {
      got = walkRecord(c.input.walk, c.input.answers, c.input.answered_at, c.input.now, c.input.final_rating ?? null);
    } catch (err) {
      assert.ok(err instanceof WalkRecordError, `${c.name}: ${String(err)}`);
      got = { error: err.message };
    }
    same(got, c.expected, c.name);
    if (!("error" in c.expected)) stored += 1;
  }
  assert.ok(stored > 0 && stored < doc.record_cases.length, "both kinds of case ran");
});

// Judge walk W01: a walk runs the creek check's follow-up rules on its answers, and the store
// keeps the checks that ran. The phone, the Worker and Python run the same two functions.
test("walks: the follow-ups a walk asks and the checks kept with it, or the same reason to refuse them, as Python", () => {
  const doc = golden("walks");
  const kinds = new Set<string>();
  for (const c of doc.followups_cases) {
    const chosen = walkFollowups(c.input.answers, CONTENT.followups, CONTENT.form_items as never);
    let got: unknown;
    try {
      const out = walkChecks(c.input.answers, chosen, c.input.question_texts, c.input.given, c.input.final_rating);
      got = { followups: chosen, checks: out.checks, final_rating: out.final_rating };
      kinds.add(out.checks.length > 0 ? "checks" : "none");
    } catch (err) {
      assert.ok(err instanceof WalkRecordError, `${c.name}: ${String(err)}`);
      got = { followups: chosen, error: err.message };
      kinds.add("error");
    }
    same(got, c.expected, c.name);
  }
  assert.deepEqual([...kinds].sort(), ["checks", "error", "none"], "cases that keep checks, keep none, and refuse");
});

test("old Bundles: only ts- JSON files are deleted, and only the ones in that folder", () => {
  const dir = mkdtempSync(join(tmpdir(), "sl-instances-"));
  for (const f of ["ts-old-visit.json", "ts-old-walk.json", "visit-from-python.json", "ts-notes.txt"]) {
    writeFileSync(join(dir, f), "{}\n");
  }
  assert.deepEqual(clearOldBundles(dir), ["ts-old-visit.json", "ts-old-walk.json"]);
  assert.deepEqual(readdirSync(dir).sort(), ["ts-notes.txt", "visit-from-python.json"]);
  rmSync(dir, { recursive: true });
});

// Last, after every test above has written its Bundles.
test("old Bundles: every ts- Bundle the validator will read was written by this run", () => {
  assert.ok(written.size > 0, "the tests above wrote Bundles");
  assert.deepEqual(tsBundles(instancesDir), [...written].sort());
});

// Review finding F01: camera metadata must go wherever it sits in a JPEG. Each probe carries the
// words PROBE-GPS in an APP1 segment; the picture's own bytes must come out unchanged.
const jpegParts = (() => {
  const seg = (marker: number, payload: number[]) => [0xff, marker, (payload.length + 2) >> 8, (payload.length + 2) & 0xff, ...payload];
  const text = (s: string) => [...s].map((c) => c.charCodeAt(0));
  return {
    soi: [0xff, 0xd8],
    app0: seg(0xe0, [...text("JFIF"), 0, 1, 1, 0, 0, 1, 0, 1, 0, 0]),
    exif: seg(0xe1, [...text("Exif"), 0, 0, ...text("PROBE-GPS 37.87 -122.26")]),
    dqt: seg(0xdb, [0, 1, 2]),
    sos: seg(0xda, [1, 1, 0, 0, 63, 0]),
    scan: [0x12, 0xff, 0x00, 0x34, 0xff, 0xd0, 0x56],
    eoi: [0xff, 0xd9],
  };
})();
const has = (bytes: Uint8Array, words: string) => new TextDecoder("latin1").decode(bytes).includes(words);

test("uploads: a JPEG keeps its picture and loses its metadata, wherever the metadata sits", () => {
  const p = jpegParts;
  const picture = [...p.soi, ...p.app0, ...p.dqt, ...p.sos, ...p.scan, ...p.eoi];
  const plain = Uint8Array.from([...p.soi, ...p.app0, ...p.exif, ...p.dqt, ...p.sos, ...p.scan, ...p.eoi]);
  assert.deepEqual([...stripJpeg(plain)], picture);
  const trailing = Uint8Array.from([...picture, ...p.soi, ...p.exif, ...p.sos, ...p.scan, ...p.eoi]);
  assert.deepEqual([...stripJpeg(trailing)], picture);
  const betweenScans = Uint8Array.from([...p.soi, ...p.app0, ...p.dqt, ...p.sos, ...p.scan, ...p.exif, ...p.sos, ...p.scan, ...p.eoi]);
  const out = stripJpeg(betweenScans);
  assert.equal(has(out, "PROBE-GPS"), false);
  assert.deepEqual([...out], [...p.soi, ...p.app0, ...p.dqt, ...p.sos, ...p.scan, ...p.sos, ...p.scan, ...p.eoi]);
  const fill = Uint8Array.from([...p.soi, 0xff, ...p.exif, ...p.app0, ...p.dqt, ...p.sos, ...p.scan, ...p.eoi]);
  assert.equal(has(stripJpeg(fill), "PROBE-GPS"), false);
});

test("uploads: a JPEG that breaks the shape is refused, not copied with its metadata", () => {
  const p = jpegParts;
  const stray = Uint8Array.from([...p.soi, 0x00, ...p.exif, ...p.dqt, ...p.sos, ...p.scan, ...p.eoi]);
  assert.throws(() => stripJpeg(stray), /could not be read/);
  const noEnd = Uint8Array.from([...p.soi, ...p.exif, ...p.dqt, ...p.sos, ...p.scan]);
  assert.throws(() => stripJpeg(noEnd), /could not be read/);
  const cut = Uint8Array.from([...p.soi, 0xff, 0xe1, 0x40, 0x00, ...[..."Exif"].map((c) => c.charCodeAt(0))]);
  assert.throws(() => stripJpeg(cut), /could not be read/);
});

// Hard rule 8 on the Worker (review REVIEW_03 R20): an upload is deleted after 30 days by KV's own
// expiry, set when the photo is stored, so nothing has to run to keep the promise.
test("uploads: a stored photo is put in KV to expire after 30 days", async () => {
  const p = jpegParts;
  const puts: { key: string; options: { expirationTtl?: number } }[] = [];
  const env = {
    PHOTOS: {
      put: async (key: string, _value: unknown, options: { expirationTtl?: number }) => {
        puts.push({ key, options });
      },
    },
    DB: { prepare: () => ({ bind: () => ({ run: async () => ({}) }) }) },
  } as unknown as Parameters<typeof storeUpload>[0];
  const form = new FormData();
  form.append("file", new Blob([Uint8Array.from([...p.soi, ...p.app0, ...p.exif, ...p.dqt, ...p.sos, ...p.scan, ...p.eoi])], { type: "image/jpeg" }), "photo.jpg");
  const stored = await storeUpload(env, new Request("http://127.0.0.1/api/upload", { method: "POST", body: form }), "2026-09-24T10:00:00Z");
  assert.equal(puts.length, 1);
  assert.equal(puts[0].key, `photo:${stored.photo_id}`);
  assert.equal(puts[0].options.expirationTtl, 30 * 24 * 60 * 60, "30 days, in seconds");
});

/** A store that only writes down what it was asked, for the routes below. */
function recordingStore(changes = 0) {
  const ran: { sql: string; args: unknown[] }[] = [];
  const DB = {
    prepare: (sql: string) => ({
      bind: (...args: unknown[]) => ({
        sql,
        args,
        run: async () => {
          ran.push({ sql, args });
          return { meta: { changes } };
        },
      }),
    }),
    batch: async (statements: { sql: string; args: unknown[] }[]) =>
      statements.map((s) => {
        ran.push({ sql: s.sql, args: s.args });
        return { meta: { changes } };
      }),
  };
  return { ran, env: { DB, PHOTOS: {} } as unknown as Parameters<typeof worker.fetch>[1] };
}

// Audit finding api-fhir-5: an error on a route that answers with a FHIR resource is FHIR's own
// OperationOutcome. apps/api/tests/test_fhir_routes.py holds the same one, letter for letter.
test("fhir_http: an error as an OperationOutcome, the same as Python", () => {
  assert.deepEqual(operationOutcome(404, "no FHIR record for this visit"), {
    resourceType: "OperationOutcome",
    text: { status: "generated", div: '<div xmlns="http://www.w3.org/1999/xhtml"><p>no FHIR record for this visit</p></div>' },
    issue: [{ severity: "error", code: "not-found", details: { text: "no FHIR record for this visit" } }],
  });
  assert.deepEqual(
    [404, 409, 413, 422, 429, 500, 503].map((status) => operationOutcome(status, "x").issue[0].code),
    ["not-found", "conflict", "too-long", "invalid", "throttled", "exception", "exception"],
  );
  assert.equal(operationOutcome(404, "a <b> & c").text.div, '<div xmlns="http://www.w3.org/1999/xhtml"><p>a &lt;b&gt; &amp; c</p></div>');
});

test("fhir_http: FHIR's media type, and plain JSON for a browser that opens the link", () => {
  assert.equal(FHIR_JSON, "application/fhir+json; charset=utf-8");
  for (const accept of [null, "", "*/*", "application/fhir+json", "application/json", "application/fhir+json, text/plain"]) {
    assert.equal(fhirMediaType(accept), FHIR_JSON, String(accept));
  }
  for (const accept of ["text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "TEXT/HTML"]) {
    assert.equal(fhirMediaType(accept), PLAIN_JSON, accept);
  }
});

const ask = async (env: Parameters<typeof worker.fetch>[1], address: string, headers: Record<string, string> = {}) => {
  const res = await worker.fetch(new Request(`http://127.0.0.1${address}`, { headers }), env);
  return { status: res.status, type: res.headers.get("content-type"), vary: res.headers.get("vary"), cache: res.headers.get("cache-control"), body: await res.json() };
};

// Audit finding privacy-security-4: GET /api/spot/%E0%A4%A was a 500 that carried "URIError: URI
// malformed". A broken percent code is an id nobody has: a plain 404, and the store is not asked.
test("routes: a broken percent code in the address is a plain 404", async () => {
  const { ran, env } = recordingStore();
  for (const address of ["/api/spot/%E0%A4%A", "/api/walk/%ff", "/api/city/%", "/api/photo/%E0%A4%A?t=x", "/api/inaturalist/%"]) {
    const answer = await ask(env, address);
    assert.deepEqual([answer.status, answer.body, answer.type], [404, { detail: "Not found." }, PLAIN_JSON], address);
  }
  const quick = await worker.fetch(new Request("http://127.0.0.1/api/quick/%E0%A4%A", { method: "POST", headers: { "content-type": "application/json" }, body: "{}" }), env);
  assert.deepEqual([quick.status, await quick.json()], [404, { detail: "Not found." }]);
  for (const address of ["/api/spot/%E0%A4%A/fhir", "/api/walk/%ff/fhir", "/api/fhir/Bundle/%", "/api/fhir/referral/%", "/api/fhir/referral/%/example-result"]) {
    const answer = await ask(env, address);
    assert.deepEqual([answer.status, answer.body, answer.type], [404, operationOutcome(404, "Not found."), FHIR_JSON], address);
  }
  assert.deepEqual(ran, [], "nothing was asked of the store");
});

test("routes: a 500 says one fixed sentence and never the error's own text", async () => {
  const env = {
    DB: {
      prepare: () => {
        throw new Error("D1_ERROR: no such table: spot, asked with the-secret-word");
      },
    },
    PHOTOS: {},
  } as unknown as Parameters<typeof worker.fetch>[1];
  const sentence = "The server could not take that. Try again in a moment.";
  const plain = await ask(env, "/api/creeks");
  assert.deepEqual([plain.status, plain.body], [500, { detail: sentence }], "no error field");
  const fhir = await ask(env, "/api/fhir/Bundle/visit-0001");
  assert.deepEqual([fhir.status, fhir.body, fhir.type], [500, operationOutcome(500, sentence), FHIR_JSON]);
  const study = await worker.fetch(new Request("http://127.0.0.1/api/test/counts"), env);
  assert.deepEqual([study.status, await study.json()], [500, { detail: sentence }], "the study routes too");
  for (const answer of [plain.body, fhir.body]) assert.ok(!JSON.stringify(answer).includes("secret") && !JSON.stringify(answer).includes("D1_ERROR"));
});

test("routes: a FHIR route answers under FHIR's media type, found or not", async () => {
  const rows: Record<string, unknown> = {};
  const env = {
    DB: { prepare: () => ({ bind: () => ({ first: async () => rows.next ?? null, all: async () => ({ results: [] }) }) }) },
    PHOTOS: {},
  } as unknown as Parameters<typeof worker.fetch>[1];
  const missing = await ask(env, "/api/fhir/Bundle/visit-nowhere");
  assert.deepEqual([missing.status, missing.body], [404, operationOutcome(404, "no FHIR record for this visit")]);
  assert.deepEqual([missing.type, missing.vary, missing.cache], [FHIR_JSON, "Accept", "no-store"]);
  const spot = await ask(env, "/api/spot/spot-nowhere/fhir");
  assert.deepEqual([spot.status, spot.body, spot.type], [404, operationOutcome(404, "no FHIR record for this spot yet"), FHIR_JSON]);
  const inBrowser = await ask(env, "/api/fhir/Bundle/visit-nowhere", { accept: "text/html,application/xhtml+xml,*/*;q=0.8" });
  assert.deepEqual([inBrowser.status, inBrowser.type, inBrowser.body], [404, PLAIN_JSON, missing.body], "the same bytes, shown in the tab");
  // The routes that are not FHIR resources keep plain JSON.
  assert.equal((await ask(env, "/api/fhir/validation")).type, PLAIN_JSON);
  assert.equal((await ask(env, "/api/nothing-here")).type, PLAIN_JSON);
});
