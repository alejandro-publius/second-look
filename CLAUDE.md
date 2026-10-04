# CLAUDE.md: Second Look

Start every session by reading PLAN.md, then only the brief section the session names. Precedence: newest file in the team's working notes wins over the team's working notes (MASTER BRIEF), which wins over PLAN.md unless docs/DECISIONS.md records the change. End every session and every decision point with the report block from the team's working notes (UPDATE 02) section 1 and nothing after it.

## Hard rules, one line each (full text: the team's working notes (MASTER BRIEF) section 4 and the team's working notes)

1. New code only, written in this repo inside Sep 16 to 30. Never copy from Alex's earlier projects. Dependencies and licenses in docs/THIRD_PARTY.md.
2. The model never decides. Model output becomes Flag objects through core/gate.py or is rejected. A flag can only make one follow-up question eligible. Gate changes ship with a test in the same commit.
3. Follow-up selection is a pure function of answers, site context, scores and flags. Two questions at most. No model call inside it.
4. A model may flag a feature only if it passed the same test as the volunteers. The pass table is a committed file the gate reads.
5. Every health or ecology sentence a user sees comes from content/approved_sentences.yaml with a source. Model text reaches users only as a flag note labelled "the checker noticed".
6. Real photos only, own or openly licensed, no AI images anywhere, no faces or plates. Every image has a manifest row. CI enforces it.
7. The usability test is anonymous: no names, emails, IPs, free text, third-party scripts or fingerprinting. docs/DATA_HANDLING.md says what the host logs.
8. Field use is pseudonymous: random contributor token, EXIF stripped, uploads private and deleted after 30 days, coarse location unless the user places the pin.
9. No calls to api.enora-oah.eu or the Resilience Map API until a team member says permission arrived. Never commit their raw data.
10. The sandbox is a mirror of our store: conditional creates, meta.tag on everything, delete only ledger ids, never delete by search, never $expunge. One exception: a conditional update is allowed on our own Library entry only, matched by our own identifier, because that match can only ever hit our resource. Read-only GETs allowed from Session E at one per second, 50 per session.
11. FHIR R4 4.0.1. IG pinned to hl7-eu/oah b907cf0 in fhir/ig.lock. Package built by SUSHI 3.20.1. Every emitted resource validated in CI.
12. Every number in README or docs comes from evals/ through results/. scripts/verify_claims.py runs in CI. Never hand-edit a number.
13. docs/analysis_plan.md is tagged prereg-v1 before the first participant. Analysis refuses real data before the lock, 2026-09-28T01:00:00Z. The second wave (UPDATE_33) runs under docs/analysis_plan_v3.md, tagged prereg-v3, and locks at 2026-10-03T04:00:00Z. The tagged plans and the tagged analysis scripts are never edited. Changes go in docs/deviations.md.
14. No secret is ever committed: `.env.example` is tracked, `.env` is not. ANTHROPIC_API_KEY lives in `.env` in this repo on this Mac, and is never exported in the shell that starts `claude` (Update 07 section 4).
15. Repo private until Oct 3 (the deadline moved to Oct 4, UPDATE_33). Small honest commits. Never rewrite history, squash or backdate.
16. Code MIT. Our photos and copy CC BY 4.0. The README states both.
17. WCAG 2.2 AA. Alt text never gives away a test answer.
18. Plain words, reading age about 12, no hype words, no em or en dashes anywhere in the repo, including commit messages.
19. One recommended path with a one-line reason. One question at a time. Every milestone ends with a proving command. Stuck 15 minutes means stop and report.
20. audit/log.jsonl is a hash-chained audit log. Call it an audit log, never a blockchain.

## Layout

```
apps/web/   Next.js PWA          apps/api/  FastAPI          core/     pure functions: gate, followups, labels, lock, fhir_emit
content/    lessons, items, form, followups, glossary, approved sentences, regions/, locales/
photos/     manifest.csv + images    evals/    every reported number    results/  eval outputs, failures included
scripts/    verify_claims, preflight, freeze_key, wipe_for_launch, repush_sandbox, ingest/label/merge photos, verify_audit
fhir/       ig.lock, FSH, sandbox_ledger.jsonl, postman/    audit/    log.jsonl    docs/    product docs, notes/; the team's working notes holds the brief, updates/, reports/
```

## Commands

- `make dev` runs everything locally. `make check` runs lint, types, pytest, web build, manifest check, FHIR validation, verify_claims. Green before every commit to main.
- `make preflight` is the launch gate. `make submit-check` is the submission gate.
- Targeted: `uv run pytest -q <path>`, `npx playwright test`, `uv run python scripts/verify_audit.py`.

## Working style

Short replies. Never print whole files; show the path and the lines that matter. Targeted tests while working, one full `make check` per milestone. Subagents only for wide reading. Recommend one path, ask one plain question at a time.
