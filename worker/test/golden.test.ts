// The golden vectors: Python wrote worker/golden/*.json (evals/golden_vectors.py); the TypeScript
// ports must reproduce every expected output exactly. Run with npm test. The emitter's Bundles are
// also written to fhir/build/instances/ so the HL7 validator checks them in make check.

import assert from "node:assert/strict";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import CONTENT from "../src/content.json";
import { findingsFromVisits, looksLikeATestName, metresBetween, nearestSpot, needsFromFindings, pipesWorthTesting } from "../src/core/act";
import { checkBundle, emitVisit, fhirId } from "../src/core/fhir_emit";
import { selectFollowups } from "../src/core/followups";
import { pickActions } from "../src/core/healthcard";
import { observerLabel } from "../src/core/labels";
import { pyRound } from "../src/core/pyround";
import { creekBySlug, placeSpot, reachOf, reachesBelow } from "../src/core/regions";
import { sha256Hex } from "../src/core/sha256";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const golden = (name: string) => JSON.parse(readFileSync(join(root, "worker", "golden", `${name}.json`), "utf8"));

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

test("followups: the selector, over the repository's own table and form", () => {
  const doc = golden("followups");
  for (const c of doc.cases) {
    const chosen = selectFollowups(c.input.answers, c.input.site, c.input.observer, [], CONTENT.followups, CONTENT.form_items, c.input.checker_enabled);
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
  const outDir = join(root, "fhir", "build", "instances");
  mkdirSync(outDir, { recursive: true });
  for (const c of doc.cases) {
    const bundle = emitVisit(c.input.visit, c.input.test_sitting, c.input.emitted_at);
    same(bundle, c.expected, c.name);
    assert.deepEqual(checkBundle(bundle), [], `${c.name}: structural check`);
    const file = `ts-${String(bundle.id)}.json`;
    writeFileSync(join(outDir, file), JSON.stringify(bundle, null, 2) + "\n");
  }
  // And a broken Bundle is caught, so the check is not a rubber stamp.
  const broken = emitVisit(doc.cases[0].input.visit, doc.cases[0].input.test_sitting, doc.cases[0].input.emitted_at) as { entry: { resource: Record<string, unknown> }[] };
  const prov = broken.entry.find((e) => e.resource.resourceType === "Provenance")!;
  (prov.resource.target as { reference: string }[]).push({ reference: "Observation/nowhere" });
  assert.ok(checkBundle(broken as never).some((p) => p.includes("does not resolve")));
});
