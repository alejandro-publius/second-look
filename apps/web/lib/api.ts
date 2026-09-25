// The one client for the W1 API. Shapes mirror docs/CONTRACTS.md exactly. Nothing else in the app
// calls fetch against the API origin.

// Empty means the API is served under /api/* on this same origin (Update 10 A1): every fetch is
// then a relative path and the policy says connect-src 'self'.
export const API_ORIGIN = (process.env.NEXT_PUBLIC_API_ORIGIN ?? "http://localhost:8000").replace(/\/$/, "");

/** An absolute URL for a path a person may copy, such as a curl line. */
export function absoluteApiUrl(path: string): string {
  if (API_ORIGIN) return `${API_ORIGIN}${path}`;
  return typeof window === "undefined" ? path : `${window.location.origin}${path}`;
}
/**
 * Set only on the dry-run build. It makes the server stamp every session this build starts as
 * is_test, so three friends trying the thing out never land in the study (Update 11D item 5).
 * The launch build leaves it empty, and then no session is ever marked from the browser.
 *
 * It is in the client bundle on purpose: the only thing this key can do is take a session out of
 * the analysis. It cannot read anyone's answers, which needs EXPORT_TOKEN and never leaves the
 * server.
 */
export const QA_KEY = process.env.NEXT_PUBLIC_QA_KEY ?? "";

export type TestAnswer = "yes" | "no" | "cant_tell";
export type Arm = "untrained" | "trained";
export type UaClass = "phone" | "tablet" | "desktop";

export interface SessionRequest {
  consent_version: string;
  content_hash: string;
  build_hash: string;
  source_label: string;
  hidden_field: string;
  client_token_hash: string;
  ua_class: UaClass;
  warmup_choice: string;
}

export interface SessionResponse {
  session_id: string;
  arm: Arm;
  item_order: string[];
  lesson_first: boolean;
}

export interface ResponseRequest {
  session_id: string;
  item_id: string;
  /** The confirmed choice, the one that is scored. Called final_choice in the analysis plan. */
  answer: TestAnswer;
  /** Time from the photo appearing to pressing Next. Called t_confirm_ms in the analysis plan. */
  rt_ms: number;
  position: number;
  first_choice?: TestAnswer;
  t_first_ms?: number;
  n_changes?: number;
}

export interface CompleteRequest {
  session_id: string;
  prior_experience: "yes" | "no" | null;
  keep_score: boolean;
  /** How many items this browser answered. The server replies with any it does not hold. */
  answered_count: number;
  /** True once the browser has resent what it could and still cannot close the gap. */
  final?: boolean;
}

export interface FeatureScoreOut {
  feature: string;
  correct: number;
  total: number;
}

export interface CompleteResponse {
  scores?: FeatureScoreOut[];
  correct_total?: number;
  contributor_token?: string;
  /** Item ids the server does not hold. The browser sends them again from its own copy. */
  need_resend?: string[];
  stored_count?: number;
}

/** Where a reloading browser was. Read only on the server: it creates nothing. */
export interface ResumeResponse {
  session_id: string;
  arm: Arm;
  item_order: string[];
  lesson_first: boolean;
  lesson_done: boolean;
  answered: string[];
  completed: boolean;
  scores?: FeatureScoreOut[];
  correct_total?: number;
}

export interface DemoAnswerResponse {
  // Whether the judge was right, and nothing else. The gold label stays on the server:
  // sixteen of these replies would be the whole answer key for the live test.
  correct: boolean;
}

export type SpotRef = { spot_id: string } | { new: { name: string; latitude: number; longitude: number; coarse: boolean } };

export type AnswerValue = string | number | string[] | Record<string, number | string>;

export interface DraftRequest {
  contributor_token?: string;
  spot: SpotRef;
  answers: Record<string, AnswerValue>;
  first_rating: string | null;
  photo_ids: string[];
}

export type FollowupKind = "yesno" | "photo" | "keep_rating" | "look_again";

export interface Followup {
  rule_id: string;
  question_text: string;
  kind: FollowupKind;
}

export interface DraftResponse {
  draft_id: string;
  followups: Followup[];
}

export interface FinalizeRequest {
  draft_id: string;
  followup_answers: Record<string, string>;
  final_rating: string | null;
}

export interface FinalizeResponse {
  visit_id: string;
  spot_id: string;
  fhir_saved?: boolean;
}

export interface SpotAnswer {
  item_id: string;
  text: string;
  value: string | number | string[] | Record<string, unknown>;
  label: string;
  feature: string | null;
  observer_label: string | null;
  observer_passed: boolean | null;
}

export interface CheckResultOut {
  rule_id: string;
  asked: boolean;
  question_text?: string | null;
  answer?: string | null;
  detail?: Record<string, unknown>;
}

export interface VisitOut {
  visit_id: string;
  answered_at: string;
  answers: SpotAnswer[];
  checks: CheckResultOut[];
  first_rating: string | null;
  final_rating: string | null;
}

export interface HealthCardOut {
  person: string;
  pet: string;
  city: string;
  sources: [string, string, string] | string[];
}

export interface SpotOut {
  spot_id: string;
  spot_name: string;
  reach_id?: string;
  reach_name?: string;
  creek_id?: string;
  creek_name?: string;
  latitude?: number | null;
  longitude?: number | null;
  coarse?: boolean;
}

export interface SpotRecordOut {
  spot: SpotOut;
  visits: VisitOut[];
  health_card: HealthCardOut | null;
  place?: SpotPlace | null;
  downstream_notes?: DownstreamNote[];
}

export interface FhirValidationOut {
  ran_at_utc?: string;
  validator_version?: string;
  ig_commit?: string;
  fhir_version?: string;
  terminology_checks_ran?: boolean;
  errors?: number;
  warnings?: number;
  /** How many of the files the validator checked are walk records (scripts/fhir_validate.py). */
  walk_records_validated?: number;
  [k: string]: unknown;
}

export type FhirObservation = Record<string, unknown>;

/** The analyst's view. Every number carries the visit ids and Bundle links behind it. */
export interface CityFinding {
  spot_id: string;
  spot_name: string;
  feature: string;
  feature_name: string;
  observers: number;
  first_seen: string;
  last_seen: string;
  visit_ids: string[];
  fhir: string[];
}

export interface CityNeed {
  sentence_id: string;
  text: string;
  source: string;
  because: string[];
  visit_ids: string[];
  fhir: string[];
}

export interface CityPipe {
  spot_id: string;
  spot_name: string;
  observers: number;
  dry_days: number[];
  last_seen: string;
  visit_ids: string[];
  fhir: string[];
  /** The ServiceRequest for this pipe, real and computed from the visits above. */
  referral: string;
  /** How a laboratory result would come back to the same record. An example, tagged as one. */
  example_result: string;
}

/** The little of FHIR the example panel needs to draw a table. */
export interface FhirBundle {
  resourceType: "Bundle";
  meta?: { tag?: { system?: string; code?: string; display?: string }[] };
  entry?: { resource: FhirResource }[];
}

export interface FhirResource {
  resourceType: string;
  id?: string;
  meta?: { tag?: { system?: string; code?: string; display?: string }[] };
  code?: { coding?: { code?: string; display?: string }[]; text?: string };
  valueQuantity?: { value?: number; unit?: string; code?: string };
  valueCodeableConcept?: { coding?: { code?: string; display?: string }[] };
  specimen?: { reference?: string };
  [k: string]: unknown;
}

/** One plain line on a reach below a finding, with the visits it was counted from. */
export interface DownstreamNote {
  reach_slug: string;
  reach_name: string;
  from_reach_slug: string;
  from_reach_name: string;
  feature: string;
  feature_name: string;
  line: string;
  observers: number;
  visit_ids: string[];
  fhir: string[];
}

/** A reach from the region pack, hills first, with the notes that land on it. */
export interface CityReach {
  slug: string;
  name: string;
  flows_into: string | null;
  flows_into_name: string | null;
  spots: number;
  visits: number;
  notes: DownstreamNote[];
}

export interface CityOut {
  creek_id: string;
  /** The readable slug from the region pack, or null for a creek the pack does not know. */
  creek_slug: string | null;
  creek_name: string;
  visits: number;
  spots: number;
  findings: CityFinding[];
  needs: CityNeed[];
  pipes_worth_testing: CityPipe[];
  flagged_spots: { spot_id: string; spot_name: string; why: string }[];
  measures_waiting_for_approval: boolean;
  reaches: CityReach[];
  downstream_notes: DownstreamNote[];
  unplaced_spots: number;
}

/** Where a spot sits in the region pack. reach_* are null for a coarse pin. */
export interface SpotPlace {
  creek_slug: string;
  creek_name: string;
  reach_slug: string | null;
  reach_name: string | null;
}

export interface TwoOut {
  ours: FhirObservation;
  /** True when no creek check is stored and `ours` is the golden visit, made by hand for the demo. */
  ours_example?: boolean;
  /** The name of the place `ours` is about, read from its record. */
  ours_place?: string | null;
  theirs: FhirObservation | null;
  theirs_status: "ok" | "cached" | "down";
  fetched_at: string;
}

/** One listed plant in the iNaturalist context line. */
export interface InatSpecies {
  taxon_id: number | null;
  name: string;
  latin_name: string;
  count: number;
  last_observed: string;
  url: string;
}

/**
 * GET /api/inaturalist/{creek}: the copy the Mac stored. `shown` is false until the creek's record
 * answers the invasive plant question, and then `species` is always empty.
 */
export interface InatOut {
  creek: string;
  shown: boolean;
  status: "cached" | "none";
  fetched_at: string | null;
  since: string | null;
  radius_m: number | null;
  species: InatSpecies[];
  source: string;
  terms: string;
}

/** POST /api/walk: a finished video walk, sent once so its record opens on any device. */
export interface WalkStoreRequest {
  walk_id: string;
  answers: Record<string, AnswerValue>;
  answered_at: string;
}

/** What the store answers: the record's id, which is the walk visit's own id, and its delete date. */
export interface WalkStoredOut {
  record_id: string;
  walk_id: string;
  answered_at: string;
  delete_after: string;
}

/** GET /api/walk/{record_id}: one stored walk record, with its answers and its demo Bundle. */
export interface WalkRecordOut extends WalkStoredOut {
  answers: Record<string, AnswerValue>;
  bundle: Record<string, unknown>;
}

export type QuickColour = "clear" | "muddy" | "foam" | "coloured" | "cant_tell";
export type QuickSmell = "none" | "bad" | "cant_tell";

export interface QuickRequest {
  contributor_token?: string;
  colour: QuickColour;
  smell: QuickSmell;
  pipe_running: "present" | "absent" | "cant_tell";
  photo_id?: string;
}

export interface Part2State {
  part2_id: string;
  arm: "assisted" | "unassisted";
  item_order: string[];
  answered: string[];
  pending: string | null;
  completed: boolean;
  total: number;
  correct_total?: number;
}

export interface Part2AnswerRequest {
  part2_id: string;
  item_id: string;
  answer: TestAnswer;
  t_first_ms: number;
  position: number;
}

export interface Part2ChoiceRequest {
  part2_id: string;
  item_id: string;
  choice: "keep" | "change";
  changed_to?: TestAnswer;
  t_final_ms: number;
}

export interface Part2Complete {
  correct_total?: number;
  total?: number;
  need_resend?: string[];
  stored_count?: number;
}

export class ApiError extends Error {
  status: number;
  /** The API's own sentence for the person, from a 4xx answer's { detail }, when it gave one. */
  detail?: string;
  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

function qaHeaders(body: unknown): Record<string, string> | undefined {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["content-type"] = "application/json";
  if (QA_KEY) headers["x-qa-key"] = QA_KEY;
  return Object.keys(headers).length ? headers : undefined;
}

async function request<T>(method: string, path: string, body?: unknown, retries = 0): Promise<T> {
  let attempt = 0;
  for (;;) {
    try {
      const res = await fetch(`${API_ORIGIN}${path}`, {
        method,
        headers: qaHeaders(body),
        body: body === undefined ? undefined : JSON.stringify(body),
        credentials: "omit",
        cache: "no-store",
      });
      if (!res.ok) {
        // 4xx answers are final. Retry only server-side and network failures.
        if (res.status >= 500 && attempt < retries) throw new Error(`status ${res.status}`);
        throw new ApiError(res.status, `${method} ${path} failed with ${res.status}`);
      }
      return (await res.json()) as T;
    } catch (err) {
      if (err instanceof ApiError) throw err;
      if (attempt >= retries) throw err;
      attempt += 1;
      await sleep(300 * 2 ** attempt);
    }
  }
}

/**
 * A call whose 4xx answer carries a sentence for the person in { detail }, kept on the error so the
 * page can show it: /city?creek=<unknown> said "Something did not send" when the API had answered
 * "We have no record for that creek yet." (CRITIC_09 R05), and the quick check said "The server
 * could not take that" when the API had answered "We do not know that spot." (CRITIC_10 T02). Only
 * the city view and the quick check use it; request() above, which the test flow runs on, is left
 * as it is.
 */
async function withDetail<T>(method: "GET" | "POST", path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_ORIGIN}${path}`, {
    method,
    headers: qaHeaders(body),
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "omit",
    cache: "no-store",
  });
  if (!res.ok) {
    const answer = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    throw new ApiError(res.status, `${method} ${path} failed with ${res.status}`, typeof answer?.detail === "string" ? answer.detail : undefined);
  }
  return (await res.json()) as T;
}

export const api = {
  /** Wakes the API. Never awaited by anything that paints. */
  health(): Promise<void> {
    return fetch(`${API_ORIGIN}/health`, { credentials: "omit", cache: "no-store", keepalive: true })
      .then(() => undefined)
      .catch(() => undefined);
  },
  contentHash() {
    return request<{ content_hash: string; build_hash: string }>("GET", "/api/content/hash");
  },
  createSession(body: SessionRequest) {
    return request<SessionResponse>("POST", "/api/test/session", body, 2);
  },
  /** A repeat with the same answer is 200. A 409 means the first answer stands; treat it as done. */
  async sendResponse(body: ResponseRequest): Promise<void> {
    try {
      await request<{ ok: boolean }>("POST", "/api/test/response", body, 3);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) return;
      throw err;
    }
  },
  lessonDone(session_id: string, lesson_seconds: Record<string, number>) {
    return request<{ ok: boolean }>("POST", "/api/test/lesson-done", { session_id, lesson_seconds }, 2);
  },
  complete(body: CompleteRequest) {
    return request<CompleteResponse>("POST", "/api/test/complete", body, 2);
  },
  resume(session_id: string) {
    return request<ResumeResponse>("GET", `/api/test/resume?session_id=${encodeURIComponent(session_id)}`, undefined, 2);
  },
  demoAnswer(item_id: string, answer: TestAnswer) {
    return request<DemoAnswerResponse>("POST", "/api/demo/answer", { item_id, answer }, 1);
  },
  // Part 2, the assisted second look (UPDATE_31). The server keeps the flags and answers each
  // first answer with whether to ask; nothing here learns which way a flag points.
  part2Offer(session_id: string, decision: "start" | "decline") {
    return request<Part2State | { declined: true }>("POST", "/api/t2/offer", { session_id, decision }, 2);
  },
  part2Answer(body: Part2AnswerRequest) {
    return request<{ ask: boolean }>("POST", "/api/t2/answer", body, 3);
  },
  /** A repeat of the same choice is 200. A 409 means the first choice stands; treat it as done. */
  async part2Choice(body: Part2ChoiceRequest): Promise<void> {
    try {
      await request<{ ok: boolean }>("POST", "/api/t2/choice", body, 3);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) return;
      throw err;
    }
  },
  part2Complete(part2_id: string, answered_count: number, final = false) {
    return request<Part2Complete>("POST", "/api/t2/complete", { part2_id, answered_count, final }, 2);
  },
  part2Resume(part2_id: string) {
    return request<Part2State>("GET", `/api/t2/resume?part2_id=${encodeURIComponent(part2_id)}`, undefined, 2);
  },
  part2Demo(item_id: string, answer: TestAnswer) {
    return request<{ ask: boolean; correct: boolean }>("POST", "/api/t2/demo", { item_id, answer }, 1);
  },
  checkDraft(body: DraftRequest) {
    return request<DraftResponse>("POST", "/api/check/draft", body);
  },
  checkFinalize(body: FinalizeRequest) {
    return request<FinalizeResponse>("POST", "/api/check/finalize", body);
  },
  spot(spot_id: string) {
    return request<SpotRecordOut>("GET", `/api/spot/${encodeURIComponent(spot_id)}`);
  },
  spotFhir(spot_id: string) {
    return request<Record<string, unknown>>("GET", `/api/spot/${encodeURIComponent(spot_id)}/fhir`);
  },
  spotFhirUrl(spot_id: string) {
    return absoluteApiUrl(`/api/spot/${encodeURIComponent(spot_id)}/fhir`);
  },
  fhirValidation() {
    return request<FhirValidationOut>("GET", "/api/fhir/validation");
  },
  city(creek_id: string) {
    return withDetail<CityOut>("GET", `/api/city/${encodeURIComponent(creek_id)}`);
  },
  /** A path the city view handed us, such as a pipe's referral or its example result. */
  fhirAt(path: string) {
    return request<FhirBundle>("GET", path);
  },
  fhirUrl(path: string) {
    return absoluteApiUrl(path);
  },
  two() {
    return request<TwoOut>("GET", "/api/two");
  },
  inaturalist(creek: string) {
    return request<InatOut>("GET", `/api/inaturalist/${encodeURIComponent(creek)}`);
  },
  quick(spot_id: string, body: QuickRequest) {
    return withDetail<{ ok?: boolean; visit_id?: string }>("POST", `/api/quick/${encodeURIComponent(spot_id)}`, body);
  },
  /** Stores a finished walk's demo record (UPDATE_30 section 1 item 3). Sent through the offline
   *  queue, so a walk finished without a network is stored when it returns. */
  storeWalk(body: WalkStoreRequest) {
    return withDetail<WalkStoredOut>("POST", "/api/walk", body);
  },
  walkRecord(record_id: string) {
    return withDetail<WalkRecordOut>("GET", `/api/walk/${encodeURIComponent(record_id)}`);
  },
  walkRecordUrl(record_id: string) {
    return absoluteApiUrl(`/api/walk/${encodeURIComponent(record_id)}`);
  },
  /** Multipart upload. The API strips EXIF and checks the real type; we only downsize. The token
   *  serves the photo back to the uploader only; we never store it. */
  async upload(blob: Blob, filename = "photo.jpg"): Promise<{ photo_id: string; token?: string }> {
    const form = new FormData();
    form.append("file", blob, filename);
    const res = await fetch(`${API_ORIGIN}/api/upload`, { method: "POST", body: form, credentials: "omit" });
    if (!res.ok) throw new ApiError(res.status, `upload failed with ${res.status}`);
    return (await res.json()) as { photo_id: string; token?: string };
  },
};

export function isNetworkError(err: unknown): boolean {
  return !(err instanceof ApiError);
}
