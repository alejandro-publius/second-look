# Load test

Made by `uv run python scripts/harden_load.py`. Arrivals are open loop at the rate below: session i starts at i times 60 / rate seconds whatever the server does, so a slow answer shows as latency, not as a lower rate. p50 and p95 are nearest rank over the requests that got a 2xx or 3xx answer; the answers column counts every answer.

- local: `wrangler dev --local` of the Worker on this Mac, a fresh local D1, rain and the sandbox pointed at a closed port so they fail closed at once. Each session is the whole two-minute test the way the browser drives it (session, the lesson for the trained arm, 16 answers with a pause of a few seconds before each, complete) plus the read endpoints. Local numbers measure the code and D1 in miniflare, not Cloudflare's edge.
- live: production, GET only: the landing page and the API's read endpoints. Every /api/test/ route is left out, and so is /api/two, because a GET there can write its cache row to D1. Nothing was written to production.

## local

50 sessions a minute for 5 minutes: 250 of 250 sessions finished, 6125 requests in 349.3 s, 0 session errors. Pause between steps 2 to 4 s. Finished 2026-09-23T04:51:39Z on Darwin 24.1.0, 8 CPUs.

| Endpoint | Requests | p50 ms | p95 ms | p99 ms | Max ms | Answers |
|---|---|---|---|---|---|---|
| GET /api/content/hash | 250 | 3.4 | 12.2 | 56.6 | 576.2 | 200: 250 |
| GET /api/creeks | 250 | 4.0 | 15.2 | 85.1 | 635.0 | 200: 250 |
| GET /api/fhir/validation | 250 | 2.8 | 10.0 | 30.8 | 262.0 | 200: 250 |
| GET /api/test/counts | 250 | 5.9 | 21.7 | 75.4 | 480.6 | 200: 250 |
| GET /api/two | 250 | 5.2 | 15.3 | 38.1 | 93.8 | 200: 250 |
| GET /health | 250 | 4.0 | 17.7 | 89.9 | 447.9 | 200: 250 |
| POST /api/test/complete | 250 | 6.8 | 25.6 | 156.8 | 285.6 | 200: 250 |
| POST /api/test/lesson-done | 125 | 5.4 | 22.6 | 117.7 | 530.7 | 200: 125 |
| POST /api/test/response | 4000 | 7.0 | 28.1 | 318.3 | 968.8 | 200: 4000 |
| POST /api/test/session | 250 | 6.8 | 19.6 | 87.0 | 143.1 | 200: 250 |

## live

50 sessions a minute for 5 minutes: 250 of 250 sessions finished, 750 requests in 301.3 s, 0 session errors. Pause between steps 0.5 to 1.5 s. Finished 2026-09-23T04:45:26Z on Darwin 24.1.0, 8 CPUs.

| Endpoint | Requests | p50 ms | p95 ms | p99 ms | Max ms | Answers |
|---|---|---|---|---|---|---|
| GET api /api/content/hash | 250 | 43.8 | 133.5 | 337.5 | 492.3 | 200: 250 |
| GET api /health | 250 | 44.8 | 136.5 | 259.5 | 4356.2 | 200: 250 |
| GET site / | 250 | 62.2 | 177.3 | 1972.0 | 4285.0 | 200: 250 |
