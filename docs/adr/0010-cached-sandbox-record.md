# 0010. `/two` shows their laboratory record from a daily copy, not a live fetch

- **Status:** accepted
- **Date:** 2026-09-23
- **Carried by:** commit 9f067a6 ("/two: the Worker shows their lab record from a daily Mac fetch,
  never fetches it live"); `worker/src/two.ts`, `scripts/cache_their_records.py`,
  `scripts/install_cache_job.sh`, `scripts/tests/test_cache_their_records.py`

## Context

`/two` puts one of our volunteer Observations beside one laboratory Observation from their sandbox,
under the same profile. On 2026-09-23 the Worker's fetch failed with HTTP 530 and code 1016,
Cloudflare's error for a name it cannot resolve. `sandbox.hl7europe.eu` no longer existed at their
own name server; the Mac had reached it only from an old cached answer. The cause is on their side
and out of our hands.

## Decision

The Worker never fetches their record. `scripts/cache_their_records.py` fetches it on the Mac once
a day through launchd, with one read only request, the same query and the same user agent as the
Python API, and stores it in the D1 table `sandbox_cache` with the time it was fetched. The Worker
shows that copy with "fetched from their sandbox at" its time. With no copy, the page says so and
shows our record alone. A failed fetch stores nothing, so the last good copy stays.

## Consequences

- `/two` works whether or not their sandbox is up, and says honestly how old their record is.
- Until their name resolves again, the page shows our record alone. The job fills the cache the
  first day it does, with no change to the code.
- The script and the Worker must compute the same cache key; a test checks that they do.
- Their record lives in D1 only, never in git.
