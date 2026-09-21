// A fake W1 API for the browser tests and the screenshot script. Every /api/ route and /health on
// the API origin is answered here with the response shapes from docs/CONTRACTS.md, so nothing is
// ever sent to a real server. Plain JS so both the Playwright specs and scripts/screens.mjs can use it.

export const API_ORIGIN = "http://127.0.0.1:8100";

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
        { rule_id: "rating_check", asked: true, question_text: "You rated this stream Good, but you also reported built banks. Do you want to keep your rating?", answer: "changed", detail: {} },
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
  health_card: null,
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

  await page.route(`${API_ORIGIN}/**`, async (route) => {
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
      return json({ session_id: "s-" + calls.length, arm: lessonFirst ? "trained" : "untrained", item_order: order, lesson_first: lessonFirst });
    }
    if (path === "/api/test/response") {
      const key = `${body.session_id}:${body.item_id}`;
      const prev = responses.get(key);
      if (prev && prev !== body.answer) return json({ detail: "conflict" }, 409);
      responses.set(key, body.answer);
      return json({ ok: true });
    }
    if (path === "/api/test/lesson-done") return json({ ok: true });
    if (path === "/api/test/complete") {
      const scores = FEATURES.map((f) => ({ feature: f, correct: 0, total: 4 }));
      for (const [key, answer] of responses) {
        const [sid, item] = key.split(":");
        if (sid !== body.session_id) continue;
        if (isCorrect(answer, goldFor(item))) scores[FEATURES.indexOf(featureFor(item))].correct += 1;
      }
      const correct_total = scores.reduce((n, s) => n + s.correct, 0);
      const out = { scores, correct_total };
      if (body.keep_score) out.contributor_token = "MOCKTOKEN1234567";
      return json(out);
    }
    if (path === "/api/demo/answer") {
      // The real API answers with correct only: the gold label never leaves the server.
      return json({ correct: isCorrect(body.answer, goldFor(body.item_id)) });
    }
    if (path === "/api/upload") return json({ photo_id: "ph-upload-" + calls.length, token: "uploadtoken" });
    if (path === "/api/check/draft") return json({ draft_id: "d1", followups });
    if (path === "/api/check/finalize") return json({ visit_id: "v3", spot_id: "example", fhir_saved: true });
    if (path.startsWith("/api/spot/") && path.endsWith("/fhir")) {
      return json({ resourceType: "Bundle", type: "collection", entry: [{ resource: exampleObservation("Practitioner/sl-practitioner-1", null, "4 of 4 on Built banks, tested Sep 23") }] });
    }
    if (path.startsWith("/api/spot/")) {
      const id = decodeURIComponent(path.slice("/api/spot/".length));
      if (id !== "example") return json({ detail: "not found" }, 404);
      return json(exampleSpot);
    }
    if (path === "/api/fhir/validation") return json(exampleValidation);
    if (path === "/api/two") {
      const status = options.theirsStatus ?? "ok";
      return json({
        ours: exampleObservation("Practitioner/sl-practitioner-1", null, "4 of 4 on Built banks, tested Sep 23"),
        theirs: status === "down" ? null : exampleObservation("Organization/almyros-lab", "Laboratory analysis", null),
        theirs_status: status,
        fetched_at: "2026-09-20T20:00:00Z",
      });
    }
    if (path.startsWith("/api/quick/")) return json({ ok: true, visit_id: "q1" });
    if (path === "/api/test/counts") return json({ by_arm: { untrained: { randomized: 0, completed: 0 }, trained: { randomized: 0, completed: 0 } }, by_source: {}, post_lock: 0 });
    return json({ detail: "unknown route in mock" }, 404);
  });
  return calls;
}

/** Collects every request the page makes so a test can prove none left our origin or the mocked API. */
export function watchRequests(page) {
  const urls = [];
  page.on("request", (r) => urls.push(r.url()));
  return urls;
}

export function assertOnlyOurOrigins(urls, baseURL) {
  const bad = urls.filter((u) => !(u.startsWith(baseURL) || u.startsWith(API_ORIGIN) || u.startsWith("data:") || u.startsWith("blob:")));
  return bad;
}
