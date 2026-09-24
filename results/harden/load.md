# Load test

Made by `uv run python scripts/harden_load.py`. Arrivals are open loop at the rate below: session i starts at i times 60 / rate seconds whatever the server does, so a slow answer shows as latency, not as a lower rate. p50 and p95 are nearest rank over the requests that got a 2xx or 3xx answer; the answers column counts every answer.

- local: `wrangler dev --local` of the Worker on this Mac, a fresh local D1, rain and the sandbox pointed at a closed port so they fail closed at once. Each session is the whole two-minute test the way the browser drives it (session, the lesson for the trained arm, 16 answers with a pause of a few seconds before each, complete) plus the read endpoints. Local numbers measure the code and D1 in miniflare, not Cloudflare's edge.
- live: production, GET only: the landing page and the API's read endpoints. Every /api/test/ route is left out, and so is /api/two, because a GET there can write its cache row to D1. Nothing was written to production.

## local

50 sessions a minute for 5 minutes: 250 of 250 sessions finished, 6125 requests in 349.4 s, 0 session errors. Pause between steps 2 to 4 s. Finished 2026-09-24T06:00:22Z on Darwin 24.1.0, 8 CPUs.

| Endpoint | Requests | p50 ms | p95 ms | p99 ms | Max ms | Answers |
|---|---|---|---|---|---|---|
| GET /api/content/hash | 250 | 2.7 | 8.5 | 17.0 | 39.1 | 200: 250 |
| GET /api/creeks | 250 | 3.4 | 7.9 | 19.8 | 31.6 | 200: 250 |
| GET /api/fhir/validation | 250 | 2.7 | 7.7 | 15.2 | 24.7 | 200: 250 |
| GET /api/test/counts | 250 | 5.1 | 11.0 | 30.4 | 35.6 | 200: 250 |
| GET /api/two | 250 | 3.9 | 11.1 | 17.9 | 32.5 | 200: 250 |
| GET /health | 250 | 3.0 | 12.6 | 56.0 | 146.5 | 200: 250 |
| POST /api/test/complete | 250 | 5.2 | 12.6 | 18.6 | 34.4 | 200: 250 |
| POST /api/test/lesson-done | 125 | 4.3 | 18.9 | 27.1 | 27.5 | 200: 125 |
| POST /api/test/response | 4000 | 5.3 | 16.7 | 33.4 | 156.2 | 200: 4000 |
| POST /api/test/session | 250 | 5.4 | 21.0 | 35.0 | 56.9 | 200: 250 |

## live

50 sessions a minute for 5 minutes: 250 of 250 sessions finished, 750 requests in 301.3 s, 0 session errors. Pause between steps 0.5 to 1.5 s. Finished 2026-09-24T06:05:24Z on Darwin 24.1.0, 8 CPUs.

| Endpoint | Requests | p50 ms | p95 ms | p99 ms | Max ms | Answers |
|---|---|---|---|---|---|---|
| GET api /api/content/hash | 250 | 46.2 | 123.3 | 174.4 | 387.3 | 200: 250 |
| GET api /health | 250 | 44.6 | 121.3 | 220.5 | 341.0 | 200: 250 |
| GET site / | 250 | 58.1 | 115.1 | 170.8 | 210.6 | 200: 250 |
