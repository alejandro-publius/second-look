# Second Look: prompt 32 (the weekend run, time-boxed)

Alex: run this in a plain terminal tab, then paste this whole file:

```
cd ~/second-look && git fetch origin && git worktree add -b weekend ../second-look-weekend origin/depth && cd ../second-look-weekend && cp ~/second-look-depth/.env .env && uv sync && (cd apps/web && npm ci) && (cd worker && npm ci) && claude
```

Everything below is addressed to Claude Code.

You are a fresh session with no memory of earlier work; the files below tell you everything. The `.env` in this folder was copied from `~/second-look-depth` and holds the QA key and the API key: never print it or commit it.

## 0. The box

- Hard stop: 4 hours after you start, or Sunday 2026-09-27 at 12:00 PDT (19:00Z), whichever comes first. At the stop, finish the item you are on or revert it, and close out as in section 8. No deploy after Sunday 16:00 PDT.
- Work in `~/second-look-weekend` on branch `weekend`. `~/second-look-depth` is the checkout the lock job deploys from on Sunday at 18:10 PDT: never edit it. After every merge into `depth` and `main`, fast-forward `~/second-look-depth` to the new head, check `git status` there is clean, and run `make lock-analysis-ready` there. It must read ready every time.
- Frozen until the lock: the two-minute test (`/t`), part 2 (`/t2`), their study endpoints, both analysis plans and the 16 frozen Worker functions. `fncmp.py` must report `changed: []` after every merge.
- No critic rounds and no judge simulations: they never converge. One adversarial check by a fresh subagent on the new code only, in section 7.
- Read `CLAUDE.md`, `PLAN.md`, `docs/HANDOFF_NEXT.md` and the two newest reports. Save this text as `docs/internal/updates/UPDATE_32.md`. Decide instead of asking. Work the sections in order; each ends with `make check`, a merge to `depth` and `main`, the lock checkout step above, a deploy in the order in `docs/notes/hosting.md`, and the phone tests against production. No em dashes, en dashes or emoji. Paid calls are not capped.

## 1. The creek check, verified against the official app (highest value)

Every creek check item is still draft wording, which a judge who built the official app will notice. The app's own strings are public: the Citizen Science App at `https://apps.oneaquahealth.eu/` ships its translations in a public JavaScript bundle (a Nuxt i18n config chunk under `/_nuxt/`). No login is needed to read it, and never log in.

1. Fetch the bundle, record its URL, date and SHA-256 in `docs/notes/app_strings.md`, and extract every assessment question and answer option in every language it contains.
2. Map each item in `content/form.yaml` to the app's string by meaning. Where our English differs from theirs, use theirs. Mark each item `verified_against_app: true` with `source: app public bundle, <sha256 prefix>, <date>`. The dug-out channel lesson item stays our own wording, marked as ours.
3. Never commit the bundle. Commit only the strings we use, each attributed to the OneAquaHealth Citizen Science App.
4. `make app-strings-check` re-fetches the bundle and fails if a string we quote has changed. Add it to the done list as its own line, not to `make check` (it needs the network).

## 2. The creek check in the app's own languages

1. Offer the creek check and the walks in every language the app's bundle contains, using the app's own translations for every mirrored item. A language picker on `/check` and `/walk`, remembered on the phone. The two-minute test and part 2 stay English: they are frozen.
2. Our own strings around the questions (buttons, follow-ups, the health card, the dug-out channel item) are not machine translated into the UI. For each language: if a checked translation exists, use it; otherwise show English for that string with a small "English" tag. Spanish stays behind Alex's signature as before.
3. Meaning check: a subagent reads each translated item beside the English and flags any whose meaning differs (the planner saw on Sep 20 that the Italian pipes item seemed to ask about rainwater while English and Dutch ask about polluted water). A flagged item falls back to English in that language, with a note. Write every finding in `docs/notes/app_translations.md` and draft a short, friendly message to the organizers listing them, in `docs/internal/MESSAGE_TRANSLATIONS.md`, for Alex to post.
4. Every record states the language the check was taken in (the QuestionnaireResponse's `language`), and the FHIR still validates with 0 errors.
5. Tests: every mirrored item has each language or an explicit fallback; a Playwright check of `/check` in two languages on the phone profile.
6. The README's OneAquaHealth surfaces table gains one row: the creek check speaks the official app's own languages, so a volunteer in any pilot city sees the questions they already know.

## 3. The kept rating in the creek check's record

Known weaknesses says the creek check's FHIR record keeps the first rating after a rating check. Fix it in both emitters: the overall rating Observation carries the kept rating as its value, and the first rating is kept in the same record as a component with its own local code, so the change stays visible. Update the golden vectors, validate with 0 errors, and remove that line from Known weaknesses.

## 4. Walk clip seeking

Known weaknesses says seeking a walk clip fails in Chrome because the host answers range requests with the whole file. Serve the clips through a small Worker or Pages Function route that answers `Range` with `206 Partial Content`, reading from wherever the clips live today. If it cannot be done without a paid storage product in 45 minutes, stop, leave the Known weaknesses line, and say so.

## 5. Devpost gallery and thumbnail

1. Five gallery images, 1500 by 1000 (3:2), each under 5 MB, built from real screenshots of the live site: the two creek photos and the question; a lesson card with marks; the score screen with the four gauges; a creek record beside the observer's score with View as FHIR; `/city` with what the creek needs. Save them to `docs/submission/gallery/` with a one-line caption each in `docs/devpost.md`.
2. A video thumbnail at 1280 by 720 under 2 MB: the two creek photos and "Which creek is healthier?". Save it to `docs/video/thumbnail.png` and name it in `docs/video/UPLOAD.md`.

## 6. The judges' top thin items

Read `docs/internal/reviews/JUDGE_SIM_02_final.md`. Fix the three most valuable items it calls thin that each take under an hour and touch nothing frozen. List what you fixed and what you left.

## 7. One adversarial check

A fresh subagent that wrote none of sections 1 to 6 reviews only the new code and strings: licensing and attribution of the app's strings, anything that could put a wrong translation in front of a volunteer, the FHIR changes, the range route, and whether the lock checkout is clean and ready. Fix what it confirms above cosmetic.

## 8. Close out

`make done-check` with its full output; CI green on `main` and `depth`; `~/second-look-depth` at the deployed commit, clean, and `make lock-analysis-ready` reading ready; the top of the status issue rewritten with only Alex's items and dates. Write the report under `docs/internal/reports/`, copy it to the clipboard with `pbcopy`, print the report block, and stop.
