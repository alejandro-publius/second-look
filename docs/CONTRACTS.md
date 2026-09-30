# Contracts between workstreams

Read this before touching anything. It is the one place where folder ownership, shared shapes and the rules for parallel work are written down. The integrator owns this file. If you need a contract changed, say so in your report; do not change it yourself.

## Rules for every workstream

1. You own the folders listed under your name and nothing else. Tests live inside your folders (`<folder>/tests/`). If you must touch another folder, stop and report instead.
2. Never commit. Never run `git add`, `git commit`, `git push`, `git tag`, `git stash` or `git checkout`. The integrator commits after review.
3. Never edit `pyproject.toml`, `uv.lock`, `Makefile`, `CLAUDE.md`, `PLAN.md`, `docs/CONTRACTS.md` or `.github/`. If you need a Python dependency, name it in your report and write the code so it fails clearly without it. W4 alone edits `apps/web/package.json`.
4. Read CLAUDE.md first. Its twenty rules apply to you. In particular: no em or en dashes anywhere, not in code comments, strings, docs or test names (run `uv run python scripts/check_dashes.py` before you finish); no secrets; no calls to `api.enora-oah.eu`; no paid model calls (the fake client only); no image shown to a person that is not a labelled gray placeholder or a real photo with a manifest row.
5. Python: `uv run pytest <your folder> -q`, `uv run ruff check <your folder>`, `uv run ruff format <your folder>`, `uv run mypy <your folder>`. All four must be clean before you report. Line length is 100. Use `Annotated[Session, Depends(get_session)]`, never `= Depends()` defaults (ruff B008).
6. Web: `cd apps/web && npm run lint && npm run build`. Playwright tests under `apps/web/tests/`.
7. Every proving command you claim must have been run by you. Paste its key line in your report.
8. Report format: the block from `docs/internal/updates/UPDATE_02.md` section 1. Nothing after it.
9. Plain words everywhere a person will read them, reading age about 12. Never the words "seamless", "robust", "leverage", "cutting-edge", "empower", "unlock", "first-of-its-kind", "real number".

## Folder ownership

| Workstream | Owns | Reads |
|---|---|---|
| W1 API | `apps/api/` (all of it except `apps/api/fhir_routes.py`, which W3 owns), `core/allocator.py`, `core/scoring.py`, `core/tests/test_allocator.py`, `core/tests/test_scoring.py` | `core/`, `content/`, `photos/manifest.csv` |
| W2 Analysis | `evals/` except `evals/model_sweep.py`, `evals/benchmark.py`, `evals/agreement.py`, `evals/ablation.py`, `evals/fixtures/` | `core/lock.py`, `core/records.py`, `docs/analysis_plan.md` |
| W3 FHIR | `fhir/` (except `fhir/ig-src`, `fhir/tools`, `fhir/build`), `core/fhir_emit.py`, `core/tests/test_fhir_emit*.py`, `apps/api/fhir_routes.py`, `scripts/repush_sandbox.py`, `docs/ig_proposal.md` | `core/records.py`, `docs/fhir_mapping.md`, `results/fhir_validation.json` |
| W4 Web | `apps/web/` | `content/`, `photos/`, this file |
| W5 Core | `core/gate.py`, `core/followups.py`, `core/rainfall.py`, `core/labels.py`, `core/healthcard.py`, `core/tests/` (except W1, W3 and W6 test files) | `content/`, `core/records.py`, `core/content_loader.py` |
| W6 AI | `evals/model_sweep.py`, `evals/benchmark.py`, `evals/agreement.py`, `evals/ablation.py`, `evals/fixtures/`, `evals/tests/test_model_*.py`, `evals/tests/test_benchmark*.py`, `core/checker.py`, `core/tests/test_checker*.py`, `results/model_pass_table.json`, `results/cost_log.jsonl` | `core/gate.py` (W5), `content/test_items.yaml` |
| W7 Tools and docs | `scripts/` (except `scripts/repush_sandbox.py`, `scripts/fhir_build.sh`, `scripts/fhir_validate.py`, `scripts/check_*.py`, `scripts/verify_claims.py`, `scripts/make_placeholders.py`, `scripts/smoke.py`, `scripts/deploy.sh`, `scripts/sandbox_write_test.sh`), `audit/`, `docs/` (except `docs/internal/MASTER_BRIEF.md`, `docs/internal/updates/`, `docs/CONTRACTS.md`, `docs/fhir_mapping.md`, `docs/ig_proposal.md`, `docs/internal/BUILD_LOG.md`, `docs/DECISIONS.md`), `content/drafts/`, `README.md` | everything |

The integrator owns: `core/records.py`, `core/lock.py`, `core/content_loader.py`, `content/*.yaml` (not drafts), `content/locales/en.json` (W4 may add keys; say which in the report), `photos/`, `pyproject.toml`, `Makefile`, `.github/`, `docker-compose.yml`, `apps/api/Dockerfile`, `apps/web/Dockerfile`, `docs/CONTRACTS.md`, `docs/internal/BUILD_LOG.md`, `docs/DECISIONS.md`.

## Shared shapes (already written, import them)

- `core/records.py`: `FeatureId`, `FEATURES`, `AnswerValue` (present, absent, cant_tell), `TestAnswer` (yes, no, cant_tell), `Arm`, `FeatureScore`, `Observer`, `Spot`, `CheckResult`, `VisitRecord`, `TestSitting`. `SCORE_VALID_DAYS = 90`, `ITEMS_PER_FEATURE = 4`.
- `core/lock.py`: `DATA_LOCK_UTC` (2026-09-28T01:00:00Z), `is_before_lock(ts)`.
- `core/content_loader.py`: `load_content(root) -> Content` with `.features`, `.form["items"]`, `.test_items`, `.followups`, `.sentences`, `.locale`, `.glossary`, `.regions`, `.lessons`, `.photos` (id to `Photo`), `.content_hash()`, plus `placeholder_report(content) -> list[str]` (human inputs missing). Raises `ContentError` with every problem.

## Content files (integrator owns, everyone reads)

- `content/features.yaml`: four features with `id`, `name`, `plain`, `question`, `wording_source`, `wording_status` (draft or frozen), `app_item`, `verified_against_app`, `oah_category`, `fhir_code`, `glossary_term`.
- `content/form.yaml`: `sections[]` and `items[]`. Item: `id`, `section`, `type` (choice, multi, yesno, number, pick_region_list, sliders), `text`, `options[] {id, label, value}`, `wording_source`, `verified_against_app`, `feature` (or null), `fhir {code_system: sl or oah, code, category?, unit?}` or null, optional `depends_on`, `region_list`, `rating_check`. `yesno` answers are `present`, `absent`, `cant_tell`.
- `content/test_items.yaml`: `items[] {id, feature, photo_id, gold}` (16, 2 present and 2 absent per feature) and `warmup[] {id, photo_id, description}`.
- `content/followups.yaml`: `max_questions: 2`, `rules[] {id, priority, needs_items, trigger, question_key, ...}`.
- `content/approved_sentences.yaml`: `sentences[] {id, audience: person|pet|city, text, source, approved}`. Only `approved: true` may reach a screen.
- `content/lessons/<feature>.yaml`: `feature`, `approved`, `rule_of_thumb`, `source`, `contrast_pairs[] {assume_photo_id, actual_photo_id, assume_caption, actual_caption}`, `practice {photo_id, gold, feedback_correct, feedback_wrong}`.
- `content/regions/<region>.yaml`: `region`, `name`, `approved`, `invasive_plants[] {common_name, latin_name, source}`.
- `content/locales/en.json`: flat `key: string` with `{placeholders}`. All UI strings come from here.
- `photos/manifest.csv`: columns `id, file, sha256, source_url, author, license, capture_date, coarse_location, scene_id, role, feature, gold_label, labeller_2, synthetic, faces, notes, label_evidence`. License `placeholder` marks a gray block. `label_evidence` says where the source itself supports the label: a research grade identification, a caption, a category name. A photo with a `source_url` needs one, and an invasive plant row needs the Cal-IPC profile link in it (Update 09 section 1).
- `photos/derived/manifest.csv`: smaller AVIF and WebP copies of a manifest photo, written by `scripts/derive_photos.py`. Columns `file, source_id, source_sha256, sha256, format, width, height, quality, bytes`. A copy is named `<source id>-<width>.<format>` and is the whole source picture scaled down, with no EXIF, XMP or colour profile. Only warm-up photos get copies; the JPEG stays in `photos/warmup/` as the fallback. `scripts/check_manifest.py` fails a copy with no row, a row whose source row or source sha256 does not match, a copy of a photo in another role, a copy over the byte cap `DERIVED_MAX_BYTES` in `core/content_loader.py`, and a copy that is cropped, stretched or carries metadata (Update 22 section 1).

## W1 API contract (W4 builds against this)

All JSON. Times are UTC ISO strings. CORS allows `PUBLIC_WEB_ORIGIN` only. Responses carry `Content-Security-Policy: default-src 'none'` on the API (it serves data, not pages). Every study endpoint refuses requests after `DATA_LOCK_UTC` by storing `post_lock = true` and still answering, so a late visitor is not shown an error.

- `POST /api/test/session` body `{consent_version, content_hash, build_hash, source_label, hidden_field, client_token_hash, ua_class, warmup_choice}`. `source_label` is coerced to one of `poster, chat, friends, creek_group, panel, other`. `hidden_field` non-empty sets `hidden_field_filled = true` and the session is still created (bots must not learn they were caught). Returns `{session_id, arm, item_order: [item_id...], lesson_first: bool}`. Assignment is permuted blocks of 4 from a stored seed, server side, safe under concurrent requests.
- `POST /api/test/response` body `{session_id, item_id, answer: yes|no|cant_tell, rt_ms, position, first_choice?, t_first_ms?, n_changes?}`. Idempotent on `(session_id, item_id)`: a repeat with the same answer returns 200, a repeat with a different answer returns 409 and keeps the first. Returns `{ok: true}`. No correctness in the response. `answer` is the confirmed choice, the one that is scored, and `rt_ms` is the time to confirm; the analysis plan calls them `final_choice` and `t_confirm_ms`. `first_choice`, `t_first_ms` and `n_changes` describe how the person got there and are never scored (Update 07 section 1.3).
- `POST /api/test/lesson-done` body `{session_id, lesson_seconds: {screen_id: seconds}}` returns `{ok: true}`.
- `POST /api/test/complete` body `{session_id, prior_experience: yes|no|null, keep_score: bool, answered_count, final?}`. Marks completion, scores from the server-side gold key. Returns `{scores: [{feature, correct, total}], correct_total, contributor_token?}`. `contributor_token` is issued only when `keep_score` is true and is a random 16 character string, stored with the scores in an `observer` table and never linked to the session id.
  - Update 07 section 1.2. `answered_count` is how many items the browser says the person answered. If the server holds fewer and `final` is not set, it completes nothing and returns `{need_resend: [item_id...], stored_count}` instead. The browser sends those ids again from its own copy, which is safe because responses are idempotent, then calls complete again. Only a browser that has tried and still cannot close the gap sends `final: true`, and then the session row carries `unsent_count` above zero. The end screen never appears while the server is missing an answer.
- `GET /api/test/resume?session_id=...` returns `{session_id, arm, item_order, lesson_first, lesson_done, answered: [item_id...], completed}` and, for a finished sitting, `scores` and `correct_total`. Read only: it creates no session row and mints no contributor token. A reload uses it to come back to the next unanswered item with the same arm and the same order (Update 07 section 2.1). 404 if the session id is unknown.
- `GET /api/test/counts` returns `{by_arm: {untrained: {randomized, completed}, trained: {...}}, by_source: {poster: n, ...}, post_lock: n}` and nothing else.
- `GET /api/test/export?token=...` returns a zip with `sessions.csv` and `responses.csv` (schema below). On the Worker the zip holds four files: part 2's `part2_sessions.csv` and `part2_responses.csv` too (UPDATE_31, `worker/src/part2.ts`). Wrong token returns 404. Token compared in constant time.
- `POST /api/demo/answer` body `{item_id, answer}` returns `{correct: bool}` and never the gold label. Stores nothing. Rate limited on the Python API. Both servers answer 403 before 2026-10-03T04:00:00Z, the second lock, when judge mode opens (`core/lock.py`, UPDATE_33).
- `GET /api/content/hash` returns `{content_hash, build_hash}`.
- `GET /health` returns `{status: ok}`.
- Creek check (rung 2): `POST /api/check/draft` body `{contributor_token?, spot: {spot_id} | {new: {name, latitude, longitude, coarse}}, answers: {item_id: value}, first_rating, photo_ids: [], language?}` returns `{draft_id, followups: [{rule_id, question_text, kind: yesno|photo|keep_rating}]}` chosen by `core.followups.select_followups`. `POST /api/check/finalize` body `{draft_id, followup_answers: {rule_id: value}, final_rating}` returns `{visit_id, spot_id}`. `GET /api/spot/{spot_id}` returns the record view model: `{spot, visits: [{visit_id, answered_at, answers: [{item_id, text, value, label, feature, observer_label: "4 of 4 on built banks, tested Sep 23" | null, observer_passed: bool | null}], checks: [CheckResult], first_rating, final_rating}], health_card}`. `GET /api/spot/{spot_id}/fhir` returns the FHIR Bundle for the latest visit (W3 route). `POST /api/quick/{spot_id}` body `{contributor_token?, colour, smell, pipe_running, photo_id?}`. `POST /api/upload` multipart image only, real type checked, 8 MB cap, EXIF stripped, returns `{photo_id, token}`; `GET /api/photo/{photo_id}?t=<per-upload token>` serves it back only with the token returned to the uploader. Uploads are deleted after 30 days: on the Python API by `scripts/cleanup_uploads.py`, on the Worker by KV's own expiry for the photo and the daily run for the `upload` row (`purgeUploads` in `worker/src/uploads.ts`). `language` on the draft is the code of the language the questions were shown in, one of `en, pt, nl, no, fr, it` (`content/app_strings.json`, UPDATE_32 section 2); `en` when not sent, 422 for any other value; stored on the visit and stated on its QuestionnaireResponse.
- Video walk: `POST /api/walk` body `{walk_id, answers, answered_at, followup_answers?, final_rating?, language?}` returns `{record_id, walk_id, answered_at, delete_after}`. `language` is validated and stored as on the draft. `GET /api/walk/{record_id}` returns the stored record and `GET /api/walk/{record_id}/fhir` its demo Bundle alone, both until `delete_after`. The full rules are in `docs/API.md`.
- FHIR answers: `/api/spot/{spot_id}/fhir`, `/api/fhir/Bundle/{visit_id}`, `/api/fhir/referral/{spot_id}`, its `/example-result` and `/api/walk/{record_id}/fhir` answer under `application/fhir+json; charset=utf-8` (plain `application/json` when the client asks for `text/html`, with `Vary: Accept`), and an error on them is an OperationOutcome with one issue and the plain sentence in `details.text`, not `{detail}` (`worker/src/fhir_http.ts`, `apps/api/fhir_http.py`). A broken percent code in a path id is a plain 404. A 500 carries one fixed sentence and never the error's own text.
- `GET /api/two` returns `{ours: Observation, ours_example: bool, ours_place: str | null, theirs: Observation | null, theirs_status: ok|cached|down, fetched_at}`. `ours` comes from the latest stored visit; with none stored it is the golden visit in `fhir/golden/`, made by hand, and `ours_example` is true. `ours_place` is the name of the Location `ours` is about, read from the same Bundle. Their Observation comes from the sandbox at one request per second with `User-Agent: second-look (+https://github.com/alejandro-publius/second-look)`, cached in the database, never in git.
- `GET /api/inaturalist/{creek}` returns `{creek, shown, status: cached|none, fetched_at, since, radius_m, species: [{taxon_id, name, latin_name, count, last_observed, url}], source, terms}`, read from the `inaturalist_cache` table that `scripts/cache_inaturalist.py` fills on the Mac. `species` is empty until the creek's record answers the invasive plant question. Context only: nothing counts it and nothing decides from it.
- Rate limit: in memory, per client address, short window, never written to disk or logs. Server access logs must not contain client addresses (uvicorn `--no-access-log` in production and a log filter in tests).
- Tables: `session (id, arm, block_id, item_order, consent_version, content_hash, build_hash, consent_at, started_at, lesson_seconds, completed_at, client_token_hash, ua_class, is_test, source_label, hidden_field_filled, post_lock, prior_experience, warmup_choice)`, `response (session_id, item_id, answer, rt_ms, position, received_at)`, `observer (contributor_token, scores_json, tested_on)`, `spot`, `visit`, `check_result`, `upload`, `sandbox_cache`, `inaturalist_cache`. Migrations run on SQLite and Postgres (`DATABASE_URL`).

## Export schema (W1 writes, W2 reads; synthetic data uses the same columns)

`sessions.csv`: `session_id, arm, block_id, source_label, ua_class, consent_version, content_hash, build_hash, started_at_utc, lesson_seconds_total, completed_at_utc, test_seconds, is_test, post_lock, hidden_field_filled, client_token_hash, prior_experience, warmup_choice, unsent_count`.
`responses.csv`: `session_id, item_id, feature, gold, answer, correct, rt_ms, position, first_choice, final_choice, t_first_ms, t_confirm_ms, n_changes`. `answer` is yes, no or cant_tell; `correct` is 1 when yes matches present or no matches absent, else 0. `final_choice` repeats `answer` and `t_confirm_ms` repeats `rt_ms`, under the names the analysis plan uses (Update 07 section 1.3).

The Worker's zip also holds part 2 (`worker/src/part2.ts`, read by `evals/assist_analysis.py`):
`part2_sessions.csv`: `part2_id, session_id, part1_arm, arm, block_id, offered_at_utc, declined, started_at_utc, completed_at_utc, test_seconds, client_token_hash, is_test, post_lock`.
`part2_responses.csv`: `part2_id, item_id, feature, gold, position, first_answer, final_answer, question_shown, choice, t_first_ms, t_final_ms, correct`.

## Results conventions (W2, W6, W7)

Every file in `results/` is JSON or CSV or PNG, written by a script in `evals/` or `scripts/`. JSON files carry `"generated_at_utc"`, `"script"`, and `"synthetic": true|false`. Synthetic outputs also carry `"stamp": "SYNTHETIC"` and every chart title starts with SYNTHETIC. `scripts/verify_claims.py` accepts synthetic results only with `--synthetic`. The README cites a number as `<!-- claim: results/<file>.json#<json-pointer> = <value> -->` on the line before the number.

- `results/model_pass_table.json` (W6): `{"real": bool, "generated_at_utc", "synthetic": bool, "models": {"<model_id>": {"<feature>": {"passed": bool, "runs": [[bool, bool, bool, bool], ...]}}}}`. `core.gate` reads `models[model][feature].passed`.
- `results/cost_log.jsonl` (W6): one line per call `{ts_utc, model, purpose, input_tokens, output_tokens, cost_usd, real}`.
- `results/power.json` (W2), `results/usability_<stamp>.json`, `results/consensus_<stamp>.json`, `results/examples.json`, results/key_agreement.json (W7 merge_labels, written only once a second labeller's file exists), `results/fhir_validation.json` (exists).

## Audit log (W7 writes the module, everyone appends through it)

`audit/log.jsonl`, one JSON object per line: `{seq, ts_utc, kind, payload_sha256, prev_hash, hash}` where `hash = sha256(f"{seq}|{ts_utc}|{kind}|{payload_sha256}|{prev_hash}")`. Kinds: `plan_tagged, key_frozen, launch_wipe, model_pass_table, data_lock, record_written, sandbox_push`. Module `scripts/audit_log.py` exposes `append(kind: str, payload: dict) -> str` and `verify() -> int` (chain length). `scripts/verify_audit.py` calls verify. Call it an audit log, never a blockchain.

## Environment variables

See `.env.example`. Settings are read once in `apps/api/settings.py`. Web reads only `NEXT_PUBLIC_API_ORIGIN`.

## Gold key handling

The gold labels live in `content/test_items.yaml` and `photos/manifest.csv` on the server. They never reach the browser during the test. `/demo` learns correctness only through `POST /api/demo/answer`. `scripts/freeze_key.py` (W7) writes `results/key_hash.json` with the sha256 of the sorted `(item_id, gold)` pairs.

## Core function signatures (W5 writes them, W1 and W4 call them; build against these exactly)

```python
# core/gate.py (W5)
class Flag(Frozen):
    feature: FeatureId
    confidence: float            # 0 to 1
    note: str                    # 160 characters at most, shown only as "the checker noticed ..."
    region: tuple[float, float, float, float] | None = None   # x, y, w, h as fractions of the image
def parse_flags(raw: object, *, model_id: str, pass_table: Mapping[str, Any]) -> tuple[list[Flag], list[str]]:
    """Parse any model output into Flags or drop it. Returns (flags for passed features only, drop reasons)."""
def build_record(*, visit_id: str, spot: Spot, observer: Observer, answered_at: datetime,
                 answers: Mapping[str, str | float | list[str]], first_rating: str | None,
                 final_rating: str | None, checks: Sequence[CheckResult], photo_ids: Sequence[str]) -> VisitRecord:
    """The only way a VisitRecord is made. No parameter carries model output."""

# core/followups.py (W5)
class SiteContext(Frozen):
    rain: Literal["dry", "wet", "unknown"]
    dry_days: int | None = None
    mm_in_window: float | None = None
class Followup(Frozen):
    rule_id: str                 # dry_pipe, rating_check, checker_flag, low_score
    kind: Literal["yesno", "keep_rating", "look_again", "photo"]
    question_key: str            # locale key
    params: dict[str, str | int | float]   # fills the locale string, e.g. days, issues, note, feature, correct
def select_followups(answers: Mapping[str, str | float | list[str]], site: SiteContext,
                     observer: Observer | None, flags: Sequence[Flag], table: Mapping[str, Any],
                     *, form_items: Sequence[Mapping[str, Any]], checker_enabled: bool = False) -> list[Followup]:
    """Pure. At most table["max_questions"] (2). Priority order from the table. No model call."""

# core/rainfall.py (W5)
class RainStatus(Frozen):
    status: Literal["dry", "wet", "unknown"]
    mm_in_window: float | None
    dry_days: int | None
    source: str                  # "open-meteo" or "unknown"
def dry_status(latitude: float, longitude: float, now: datetime, *, dry_mm: float = 2.5,
               window_hours: int = 72, fetch: Callable[[str], dict] | None = None,
               cache: MutableMapping[str, tuple[datetime, dict]] | None = None) -> RainStatus:
    """Open-Meteo hourly precipitation for the window. Timeout and one retry inside fetch. Any failure -> unknown."""

# core/labels.py (W5)
HUMAN_PASS_MIN = 3               # a person "passed" a feature with 3 of 4 or better
class Label(Frozen):
    text: str                    # "4 of 4 on built banks, tested Sep 23" or the expired sentence
    expired: bool
    passed: bool | None          # None when there is no score
def observer_label(score: FeatureScore | None, feature_name: str, today: date, locale: Mapping[str, str]) -> Label: ...

# core/healthcard.py (W5)
class HealthCard(Frozen):
    person: str
    pet: str
    city: str
    sources: tuple[str, str, str]
def pick_actions(sentences: Sequence[Mapping[str, Any]], seed: str) -> HealthCard | None:
    """Only sentences with approved == True. One per audience, chosen by a seeded pick. None if any audience has none."""

# core/scoring.py (W1)
def is_correct(answer: TestAnswer, gold: GoldLabel) -> bool: ...
def score_sitting(responses: Mapping[str, TestAnswer], items: Sequence[Mapping[str, Any]], tested_on: date) -> list[FeatureScore]:
    """Missing or cant_tell answers count as incorrect."""

# core/allocator.py (W1)
def arm_for_position(seed: str, position: int, *, k: int = 2, block: int = 4) -> tuple[Arm, int]:
    """Deterministic: the arm and block id for the nth randomized session. Permuted blocks of `block` over `k` arms."""
```
