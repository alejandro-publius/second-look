# 0007. Their sandbox is a mirror of our store: create by condition, delete only by ledger id

- **Status:** accepted
- **Date:** 2026-09-20, with the Library exception added 2026-09-21
- **Carried by:** commit 00ffea4 (the mirror script) and commit 9fb3de8 (the Library entry follows
  each push); `scripts/repush_sandbox.py`, `fhir/sandbox_ledger.jsonl`, `core/fhir_library.py`,
  `scripts/tests/test_repush_sandbox.py`

## Context

OneAquaHealth's FHIR sandbox is shared by every team. Anyone can write there and anyone can
delete. A careless delete by search could remove someone else's records, and our own records can
vanish at any time. Hard rule 10 in `CLAUDE.md`.

## Decision

Our own store of validated Bundles is the source of truth; the sandbox is a copy we can rebuild.
Each visit goes as a transaction of conditional creates with our `meta.tag` on every resource, one
request a second, and every created id goes into the ledger. A delete names one id that is in the
ledger: never a search, never `$expunge`. The one exception is a conditional update of our own
Library entry, matched by our own identifier, which can only ever match our resource. Only visit
Bundles are mirrored, never a test sitting, a demo walk, a referral or an example. Nothing is sent
unless `SANDBOX_MIRROR_ENABLED` is `true`.

## Consequences

- Records someone else deletes come back on the next re-push, and the conditional creates make a
  re-push a no-op for what is still there. A launchd job re-pushes on set days (`DEPLOY.md`).
- Real visits are mirrored as one tagged batch after the data lock, not as they arrive.
- The Library entry lists the Provenances the ledger says we created, so anyone can find our data
  set from the sandbox itself.
