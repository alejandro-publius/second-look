# 0002. A TypeScript Worker on D1 serves the API; Python stays the reference

- **Status:** accepted
- **Date:** 2026-09-21
- **Carried by:** commit 2f61b23 (the study Worker), commit 1a271a6 (golden vectors and the
  TypeScript ports) and commit e219c5f (the judge facing endpoints on the Worker);
  `worker/src/index.ts`, `evals/golden_vectors.py`, `worker/golden/`, `worker/test/golden.test.ts`,
  `scripts/seed_arms.py`

## Context

All the tested code was Python: FastAPI in `apps/api/` over SQLModel, and pure functions in
`core/`. A Python Worker can run FastAPI, but a D1 binding is a prepared statement interface, not
a database connection, and SQLModel cannot reach it without a shim nobody has written. That shim
would sit under the study, the one part that must not be wrong. The Python Worker's bundler also
needed a newer uv than this machine had. The probe is recorded in `docs/notes/hosting.md`.

## Decision

The API on Cloudflare is a small TypeScript Worker on D1 and KV. Python stays the reference and the
toolchain: `evals/golden_vectors.py` writes the Python outputs for chosen inputs into
`worker/golden/`, and the TypeScript ports in `worker/src/core/` must reproduce every one exactly in
`make worker-check`. Python also writes `worker/src/content.json`, the tables the ports read.
Randomization is not ported: `scripts/seed_arms.py` writes `core/allocator.py`'s own sequence into
the `arm_slot` table, and the Worker takes the next slot.

## Consequences

- The site and the tests cannot quietly disagree: a port that differs fails `make check`, and a
  golden file older than the Python that writes it fails too.
- Language details had to be matched on purpose: `worker/src/core/pyround.ts` rounds an exact half
  the way Python's `round()` does.
- `core.allocator.replay` still checks every stored assignment, because the sequence is Python's.
- The Worker has no shared memory, so it has no rate limit (`docs/DATA_HANDLING.md`).
- `make worker-e2e` drives every route under `wrangler dev` with a local D1 and KV, in CI.
