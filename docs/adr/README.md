# Architecture decision records

One short record per decision that shapes the code: the context, the decision, what follows from
it, the date, and the commit or file that carries it. They are written from `docs/DECISIONS.md`,
the dated one-line log, and from the working notes in the team's working notes. A new decision gets the
next number and a line here; a decision that is replaced keeps its record, marked with what
replaced it. `scripts/tests/test_adr.py` checks that every record is listed here and has its parts.

| Number | Decision | Date | Status |
|---|---|---|---|
| [0001](0001-static-export-on-pages.md) | The site is a static export on Cloudflare Pages, with the API on the same origin | 2026-09-21 | accepted |
| [0002](0002-typescript-worker-python-reference.md) | A TypeScript Worker on D1 serves the API; Python stays the reference | 2026-09-21 | accepted |
| [0003](0003-the-model-never-decides.md) | The model never decides | 2026-09-20 | accepted |
| [0004](0004-pass-table-per-feature.md) | A model may flag a feature only if it passed the people's test for it | 2026-09-20 | accepted |
| [0005](0005-fhir-under-oneaquahealth-profiles.md) | Records are FHIR under OneAquaHealth's profiles, with a pseudonymous Practitioner | 2026-09-20 | accepted |
| [0006](0006-preregistration-with-a-lock.md) | The analysis plan is pre-registered, and the code enforces the lock | 2026-09-21 | accepted |
| [0007](0007-sandbox-is-a-mirror.md) | Their sandbox is a mirror of our store: create by condition, delete only by ledger id | 2026-09-20 | accepted |
| [0008](0008-open-footage-no-creek-visit.md) | No creek visit: the video and the AI use openly licensed footage | 2026-09-23 | accepted |
| [0009](0009-direct-calls-over-batches.md) | The paid model run may make direct calls instead of batches | 2026-09-23 | accepted |
| [0010](0010-cached-sandbox-record.md) | `/two` shows their laboratory record from a daily copy, not a live fetch | 2026-09-23 | accepted |
| [0011](0011-inaturalist-context.md) | Creek pages show iNaturalist sightings as context, from a daily copy, and nothing decides from them | 2026-09-24 | accepted |
