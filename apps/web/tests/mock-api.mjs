// A fake W1 API for the browser tests and the screenshot script. Every /api/ route and /health on
// the API origin is answered here with the response shapes from docs/CONTRACTS.md, so nothing is
// ever sent to a real server. Plain JS so both the Playwright specs and scripts/screens.mjs can use it.

export const API_ORIGIN = "http://127.0.0.1:8100";

// NEXT_PUBLIC_API_ORIGIN is inlined at build time, so a build made without it bakes the default
// from lib/api.ts instead. Mock both, or a test run against such a build silently talks to
// nothing and every screen after consent shows the network error.
export const BUILT_IN_DEFAULT = "http://localhost:8000";

const ITEM_IDS = Array.from({ length: 16 }, (_, i) => `t${String(i + 1).padStart(2, "0")}`);
const FEATURES = ["artificial_bank", "dug_out_channel", "invasive_plant", "pipe_running"];

/** The mock's private gold key: two present then two absent per feature, matching the placeholder items. */
export function goldFor(itemId) {
  const n = Number(itemId.slice(1));
  return (n - 1) % 4 < 2 ? "present" : "absent";
}

export function featureFor(itemId) {
  const n = Number(itemId.slice(1));
  return FEATURES[Math.floor((n - 1) / 4)];
}

function isCorrect(answer, gold) {
  return (answer === "yes" && gold === "present") || (answer === "no" && gold === "absent");
}

// The analyst's view. Every number carries the visit ids and Bundle links behind it.
export const exampleCity = {
  creek_id: "example",
  creek_name: "Strawberry Creek",
  visits: 5,
  spots: 2,
  findings: [
    {
      spot_id: "example",
      spot_name: "Footbridge below the library",
      feature: "pipe_running",
      feature_name: "Pipes and sewage signs",
      observers: 2,
      first_seen: "2026-09-22",
      last_seen: "2026-09-23",
      visit_ids: ["v1", "v2"],
      fhir: ["/api/fhir/Bundle/v1", "/api/fhir/Bundle/v2"],
    },
  ],
  // Update 13: the approved city measures, OneAquaHealth's own, from the Policy Brief page 9.
  needs: [
    {
      sentence_id: "city_fix_sewers",
      text: "Find and fix leaking or wrongly connected sewers, and improve the treatment of waste water.",
      source: "OneAquaHealth Policy Brief (2026), page 9: improvement of sewage systems and water treatments. https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf",
      because: ["Pipes and sewage signs"],
      visit_ids: ["v1", "v2"],
      fhir: ["/api/fhir/Bundle/v1", "/api/fhir/Bundle/v2"],
    },
    {
      sentence_id: "city_replant_margins",
      text: "Replant both margins with native trees and shrubs, and stop cutting them back.",
      source: "OneAquaHealth Policy Brief (2026), page 9: rehabilitation of the riparian vegetation should prioritize a diverse corridor with native species, along both stream margins, free from unnecessary clearing. https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf",
      because: ["Built banks"],
      visit_ids: ["v2"],
      fhir: ["/api/fhir/Bundle/v2"],
    },
  ],
  pipes_worth_testing: [
    {
      spot_id: "example",
      spot_name: "Footbridge below the library",
      observers: 2,
      dry_days: [5, 9],
      last_seen: "2026-09-23",
      visit_ids: ["v1", "v2"],
      fhir: ["/api/fhir/Bundle/v1", "/api/fhir/Bundle/v2"],
      referral: "/api/fhir/referral/example",
      example_result: "/api/fhir/referral/example/example-result",
    },
  ],
  flagged_spots: [{ spot_id: "t1", spot_name: "test spot", why: "the name reads like a test" }],
  measures_waiting_for_approval: false,
  creek_slug: "strawberry-creek",
  unplaced_spots: 1,
  downstream_notes: [],
  reaches: [],
};

// The iNaturalist context line's sightings, as scripts/cache_inaturalist.py stores them.
export const exampleInat = [
  { taxon_id: 61317, name: "Himalayan blackberry", latin_name: "Rubus armeniacus", count: 5, last_observed: "2025-12-11", url: "https://www.inaturalist.org/observations?id=283650055,294575631,299064622,351067371,351067372" },
  { taxon_id: 64113, name: "Algerian ivy", latin_name: "Hedera canariensis", count: 1, last_observed: "2025-12-16", url: "https://www.inaturalist.org/observations?id=330995130" },
];

const exampleNote = {
  reach_slug: "campus-west",
  reach_name: "Below the forks, west campus",
  from_reach_slug: "south-fork-campus",
  from_reach_name: "South Fork, central campus",
  feature: "pipe_running",
  feature_name: "Pipes and sewage signs",
  line: "Upstream of here, 2 people reported pipes and sewage signs on Sep 23.",
  observers: 2,
  visit_ids: ["v1", "v2"],
  fhir: ["/api/fhir/Bundle/v1", "/api/fhir/Bundle/v2"],
};
exampleCity.downstream_notes = [exampleNote];
exampleCity.reaches = [
  { slug: "south-fork-campus", name: "South Fork, central campus", flows_into: "campus-west", flows_into_name: "Below the forks, west campus", spots: 1, visits: 5, notes: [] },
  { slug: "campus-west", name: "Below the forks, west campus", flows_into: null, flows_into_name: null, spots: 0, visits: 0, notes: [exampleNote] },
];

const SL = "https://github.com/alejandro-publius/second-look/fhir/CodeSystem/second-look";
const exampleTag = { system: SL, code: "example", display: "Example, not a real result" };

// The referral is real: a ServiceRequest whose reasons are the two pipe Observations.
export const exampleReferral = {
  resourceType: "Bundle",
  id: "sl-referral-bundle-example",
  type: "collection",
  entry: [
    { resource: { resourceType: "Location", id: "sl-loc-example", name: "Footbridge below the library" } },
    {
      resource: {
        resourceType: "ServiceRequest",
        id: "sl-referral-example",
        status: "active",
        intent: "proposal",
        code: { coding: [{ system: SL, code: "test-pipe-outflow", display: "Test the water coming out of this pipe" }] },
        subject: { reference: "Location/sl-loc-example" },
        reasonReference: [{ reference: "Observation/o1" }, { reference: "Observation/o2" }],
      },
    },
  ],
};

// How a result would come back: a Specimen and a small panel, every one tagged as an example.
export const exampleLabResult = {
  resourceType: "Bundle",
  id: "sl-example-result-example",
  meta: { tag: [exampleTag] },
  type: "collection",
  entry: [
    ...exampleReferral.entry,
    { resource: { resourceType: "Specimen", id: "sl-example-specimen-example", meta: { tag: [exampleTag] }, subject: { reference: "Location/sl-loc-example" } } },
    {
      resource: {
        resourceType: "Observation",
        id: "sl-example-obs-1",
        meta: { tag: [exampleTag] },
        status: "final",
        code: { coding: [{ system: SL, code: "lab-enterobacteriaceae-share", display: "Enterobacteriaceae, share of 16S reads" }] },
        specimen: { reference: "Specimen/sl-example-specimen-example" },
        valueQuantity: { value: 1.8, unit: "percent", code: "%" },
      },
    },
    {
      resource: {
        resourceType: "Observation",
        id: "sl-example-obs-2",
        meta: { tag: [exampleTag] },
        status: "final",
        code: { coding: [{ system: SL, code: "lab-hf183", display: "Human faecal marker HF183" }] },
        specimen: { reference: "Specimen/sl-example-specimen-example" },
        valueCodeableConcept: { coding: [{ code: "absent", display: "Absent" }] },
      },
    },
  ],
};

export const exampleSpot = {
  spot: { spot_id: "example", spot_name: "Footbridge below the library", reach_id: "campus", reach_name: "Campus reach", creek_id: "strawberry", creek_name: "Strawberry Creek", latitude: 37.87, longitude: -122.26, coarse: true },
  visits: [
    {
      visit_id: "v2",
      answered_at: "2026-09-23T17:10:00Z",
      first_rating: "good",
      final_rating: "moderate",
      answers: [
        { item_id: "bank_type", text: "Bank type", value: "present", label: "Artificial (concrete or stones with concrete)", feature: "artificial_bank", observer_label: "4 of 4 on Built banks, tested Sep 23", observer_passed: true },
        { item_id: "draining_pipes", text: "Are there pipes draining polluted water into the stream?", value: "present", label: "Yes", feature: "pipe_running", observer_label: "2 of 4 on Pipes and sewage signs, tested Sep 23", observer_passed: false },
        { item_id: "invasive_species", text: "Do you see any non-native or invasive plant species?", value: "cant_tell", label: "Not sure", feature: "invasive_plant", observer_label: null, observer_passed: null },
        { item_id: "water_flow", text: "Water flow", value: "slow", label: "Slow", feature: null, observer_label: null, observer_passed: null },
      ],
      checks: [
        { rule_id: "dry_pipe", asked: true, question_text: "It has not rained here for 5 days. Is anything coming out of that pipe?", answer: "yes", detail: { days: 5 } },
        { rule_id: "rating_check", asked: true, question_text: "You rated this stream Good, but you also reported built banks. Do you want to keep your rating?", answer: "change", detail: {} },
      ],
    },
    {
      visit_id: "v1",
      answered_at: "2026-09-18T15:00:00Z",
      first_rating: "moderate",
      final_rating: "moderate",
      answers: [{ item_id: "bank_type", text: "Bank type", value: "absent", label: "Natural", feature: "artificial_bank", observer_label: "Score expired. Tested Jun 1, more than 90 days ago. Retake the test.", observer_passed: null }],
      checks: [],
    },
  ],
  health_card: {
    person: "Stay out of water that smells bad, looks discoloured, or has foam, scum or mats on the surface.",
    pet: "If your dog seems sick after being in or near the water, call a vet right away.",
    city: "Find and fix leaking or wrongly connected sewers, and improve the treatment of waste water.",
    sources: [
      "CDC, Preventing Illness from Harmful Algal Blooms: if water looks or smells bad, stay out. https://www.cdc.gov/harmful-algal-blooms/prevention/index.html",
      "CDC, Preventing Illness from Harmful Algal Blooms: if your pets seem sick after going in or near water, call a veterinarian right away. https://www.cdc.gov/harmful-algal-blooms/prevention/index.html",
      "OneAquaHealth Policy Brief (2026), page 9: improvement of sewage systems and water treatments. https://www.oneaquahealth.eu/app/uploads/2026/05/OneAquaHealth-Policy-Brief.pdf",
    ],
  },
  place: { creek_slug: "strawberry-creek", creek_name: "Strawberry Creek", reach_slug: "campus-west", reach_name: "Below the forks, west campus" },
  downstream_notes: [exampleNote],
};

export const exampleObservation = (performer, method, note) => ({
  resourceType: "Observation",
  id: "sl-obs-bank-1",
  status: "final",
  code: { coding: [{ system: "https://second-look.example/cs", code: "artificial-bank", display: "Artificial bank" }] },
  subject: { reference: "Location/sl-loc-spot-1", display: "Footbridge below the library" },
  effectiveDateTime: "2026-09-23T17:10:00Z",
  performer: [{ reference: performer, display: performer }],
  method: method ? { text: method } : undefined,
  valueCodeableConcept: { coding: [{ code: "present", display: "Present" }] },
  note: note ? [{ text: note }] : undefined,
});

export const exampleValidation = { ran_at_utc: "2026-09-20T22:58:03+00:00", validator_version: "6.10.4", ig_commit: "b907cf0", fhir_version: "4.0.1", terminology_checks_ran: false, errors: 0, warnings: 15 };

/**
 * Registers the fake API on a page. Options: lessonFirst (bool), followups (array), theirsStatus,
 * offline (object with a mutable `value` flag; when true every API request fails like a dead network).
 * Returns the list of calls: { method, path, body }.
 */
export async function mockApi(page, options = {}) {
  const calls = [];
  const offline = options.offline ?? { value: false };
  const followups =
    options.followups ?? [
      { rule_id: "dry_pipe", question_text: "It has not rained here for 5 days. Is anything coming out of that pipe?", kind: "yesno" },
      { rule_id: "rating_check", question_text: "You rated this stream Good, but you also reported built banks. Do you want to keep your rating?", kind: "keep_rating" },
    ];
  const responses = new Map();
  // Enough session state for a reload to resume, the way the real API does.
  const sessions = new Map();
  let sessionCount = 0;

  const scoresFor = (sid) => {
    const scores = FEATURES.map((f) => ({ feature: f, correct: 0, total: 4 }));
    for (const [key, answer] of responses) {
      const [owner, item] = key.split(":");
      if (owner !== sid) continue;
      if (isCorrect(answer, goldFor(item))) scores[FEATURES.indexOf(featureFor(item))].correct += 1;
    }
    return scores;
  };

  const handle = async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname;
    let body = null;
    const raw = req.postData();
    if (raw && req.headers()["content-type"]?.includes("application/json")) {
      try {
        body = JSON.parse(raw);
      } catch {
        body = raw;
      }
    }
    calls.push({ method: req.method(), path, body });
    if (offline.value) {
      await route.abort("internetdisconnected");
      return;
    }
    const json = (data, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(data) });

    if (path === "/health") return json({ status: "ok" });
    if (path === "/api/content/hash") return json({ content_hash: "mock", build_hash: "mock" });
    if (path === "/api/test/session") {
      const lessonFirst = options.lessonFirst ?? true;
      const order = ITEM_IDS.slice().reverse();
      sessionCount += 1;
      const made = { session_id: "s-" + sessionCount, arm: lessonFirst ? "trained" : "untrained", item_order: order, lesson_first: lessonFirst };
      sessions.set(made.session_id, { ...made, lesson_done: false, completed: false });
      return json(made);
    }
    if (path === "/api/test/resume") {
      const sid = url.searchParams.get("session_id");
      const s = sessions.get(sid);
      if (!s) return json({ detail: "not found" }, 404);
      const answered = s.item_order.filter((i) => responses.has(`${sid}:${i}`));
      const out = { session_id: sid, arm: s.arm, item_order: s.item_order, lesson_first: s.lesson_first, lesson_done: s.lesson_done, answered, completed: s.completed };
      if (s.completed) {
        out.scores = scoresFor(sid);
        out.correct_total = out.scores.reduce((n, x) => n + x.correct, 0);
      }
      return json(out);
    }
    if (path === "/api/test/response") {
      const key = `${body.session_id}:${body.item_id}`;
      const prev = responses.get(key);
      if (prev && prev !== body.answer) return json({ detail: "conflict" }, 409);
      responses.set(key, body.answer);
      return json({ ok: true });
    }
    if (path === "/api/test/lesson-done") {
      const s = sessions.get(body.session_id);
      if (s) s.lesson_done = true;
      return json({ ok: true });
    }
    if (path === "/api/test/complete") {
      const s = sessions.get(body.session_id);
      const order = s ? s.item_order : ITEM_IDS;
      const held = order.filter((i) => responses.has(`${body.session_id}:${i}`));
      const gap = order.filter((i) => !responses.has(`${body.session_id}:${i}`));
      // The end screen waits until we hold every answer. Same shape as the real API.
      if (gap.length > 0 && !body.final && !(s && s.completed) && (body.answered_count ?? 0) > held.length) {
        return json({ need_resend: gap, stored_count: held.length });
      }
      if (s) s.completed = true;
      const scores = scoresFor(body.session_id);
      const out = { scores, correct_total: scores.reduce((n, x) => n + x.correct, 0) };
      if (body.keep_score) out.contributor_token = "MOCKTOKEN1234567";
      return json(out);
    }
    if (path === "/api/demo/answer") {
      // The real API answers with correct only: the gold label never leaves the server.
      return json({ correct: isCorrect(body.answer, goldFor(body.item_id)) });
    }
    if (path === "/api/upload") return json({ photo_id: "ph-upload-" + calls.length, token: "uploadtoken" });
    if (path === "/api/check/draft") return json({ draft_id: "d1", followups });
    if (path === "/api/check/finalize") {
      // The same answers apps/api/check.py and worker/src/check.ts accept (FOLLOWUP_ANSWERS), or a
      // photo id from an upload. A mock that took anything once hid a follow-up the servers refused.
      const allowed = new Set(["yes", "no", "cant_tell", "keep", "change", "skipped"]);
      for (const [rule, v] of Object.entries(body.followup_answers ?? {})) {
        if (!allowed.has(String(v)) && !String(v).startsWith("ph-upload-")) {
          return json({ detail: `${rule}: answer yes, no, cant_tell, keep, change or skipped.` }, 422);
        }
      }
      return json({ visit_id: "v3", spot_id: "example", fhir_saved: true });
    }
    if (path.startsWith("/api/spot/") && path.endsWith("/fhir")) {
      return json({ resourceType: "Bundle", type: "collection", entry: [{ resource: exampleObservation("Practitioner/sl-practitioner-1", null, "4 of 4 on Built banks, tested Sep 23") }] });
    }
    if (path.startsWith("/api/spot/")) {
      const id = decodeURIComponent(path.slice("/api/spot/".length));
      if (id !== "example") return json({ detail: "not found" }, 404);
      return json(exampleSpot);
    }
    if (path === "/api/fhir/referral/example/example-result") return json(exampleLabResult);
    if (path === "/api/fhir/referral/example") return json(exampleReferral);
    if (path.startsWith("/api/fhir/referral/")) return json({ detail: "No referral: this pipe is not on the list." }, 404);
    if (path.startsWith("/api/city/")) {
      const creek = decodeURIComponent(path.slice("/api/city/".length));
      if (creek !== "example" && creek !== "strawberry-creek") return json({ detail: "not found" }, 404);
      return json(exampleCity);
    }
    if (path === "/api/fhir/validation") return json(exampleValidation);
    if (path === "/api/two") {
      const status = options.theirsStatus ?? "ok";
      // options.oursExample: no creek check is stored, so the API sends the hand-made golden visit,
      // whose subject is a bare Location id, and says so, with the place by name.
      const ours = exampleObservation("Practitioner/sl-practitioner-1", null, "4 of 4 on Built banks, tested Sep 23");
      if (options.oursExample) ours.subject = { reference: "Location/sl-loc-spot-1" };
      return json({
        ours,
        ours_example: Boolean(options.oursExample),
        ours_place: options.oursExample ? "Strawberry Creek, campus reach, spot 1" : "Footbridge below the library",
        theirs: status === "down" ? null : exampleObservation("Organization/almyros-lab", "Laboratory analysis", null),
        theirs_status: status,
        fetched_at: "2026-09-20T20:00:00Z",
      });
    }
    if (path.startsWith("/api/inaturalist/")) {
      // The same shape worker/src/inaturalist.ts answers. options.inat picks the case: "cached"
      // (the default), "empty" (a copy with no sightings), "none" (nothing stored), "hidden" (the
      // creek's record has not answered the invasive plant question) or "down" (the route fails).
      const kind = options.inat ?? "cached";
      if (kind === "down") return json({ detail: "The server could not take that." }, 500);
      const creek = decodeURIComponent(path.slice("/api/inaturalist/".length));
      const stored = kind === "cached" || kind === "empty" || kind === "hidden";
      return json({
        creek: creek === "example" ? "strawberry-creek" : creek,
        shown: kind !== "hidden",
        status: stored ? "cached" : "none",
        fetched_at: stored ? "2026-09-24T07:45:00Z" : null,
        since: stored ? "2023-09-24" : null,
        radius_m: stored ? 300 : null,
        species: kind === "cached" ? exampleInat : [],
        source: "https://www.inaturalist.org",
        terms: "https://www.inaturalist.org/pages/terms",
      });
    }
    if (path.startsWith("/api/quick/")) return json({ ok: true, visit_id: "q1" });
    if (path === "/api/test/counts") return json({ by_arm: { untrained: { randomized: 0, completed: 0 }, trained: { randomized: 0, completed: 0 } }, by_source: {}, post_lock: 0 });
    return json({ detail: "unknown route in mock" }, 404);
  };

  await page.route(`${API_ORIGIN}/**`, handle);
  await page.route(`${BUILT_IN_DEFAULT}/**`, handle);
  return calls;
}

/** Collects every request the page makes so a test can prove none left our origin or the mocked API. */
export function watchRequests(page) {
  const urls = [];
  page.on("request", (r) => urls.push(r.url()));
  return urls;
}

export function assertOnlyOurOrigins(urls, baseURL) {
  const ours = [baseURL, API_ORIGIN, BUILT_IN_DEFAULT, "data:", "blob:"];
  const bad = urls.filter((u) => !ours.some((o) => u.startsWith(o)));
  return bad;
}
