// The one client for the W1 API. Shapes mirror docs/CONTRACTS.md exactly. Nothing else in the app
// calls fetch against the API origin.

export const API_ORIGIN = (process.env.NEXT_PUBLIC_API_ORIGIN ?? "http://localhost:8000").replace(/\/$/, "");

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
}

export interface FhirValidationOut {
  ran_at_utc?: string;
  validator_version?: string;
  ig_commit?: string;
  fhir_version?: string;
  terminology_checks_ran?: boolean;
  errors?: number;
  warnings?: number;
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
}

export interface CityOut {
  creek_id: string;
  creek_name: string;
  visits: number;
  spots: number;
  findings: CityFinding[];
  needs: CityNeed[];
  pipes_worth_testing: CityPipe[];
  flagged_spots: { spot_id: string; spot_name: string; why: string }[];
  measures_waiting_for_approval: boolean;
}

export interface TwoOut {
  ours: FhirObservation;
  theirs: FhirObservation | null;
  theirs_status: "ok" | "cached" | "down";
  fetched_at: string;
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

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

async function request<T>(method: string, path: string, body?: unknown, retries = 0): Promise<T> {
  let attempt = 0;
  for (;;) {
    try {
      const res = await fetch(`${API_ORIGIN}${path}`, {
        method,
        headers: body === undefined ? undefined : { "content-type": "application/json" },
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
    return `${API_ORIGIN}/api/spot/${encodeURIComponent(spot_id)}/fhir`;
  },
  fhirValidation() {
    return request<FhirValidationOut>("GET", "/api/fhir/validation");
  },
  city(creek_id: string) {
    return request<CityOut>("GET", `/api/city/${encodeURIComponent(creek_id)}`);
  },
  two() {
    return request<TwoOut>("GET", "/api/two");
  },
  quick(spot_id: string, body: QuickRequest) {
    return request<{ ok?: boolean; visit_id?: string }>("POST", `/api/quick/${encodeURIComponent(spot_id)}`, body);
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
