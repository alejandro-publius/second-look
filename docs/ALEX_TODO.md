# Alex: what only you can do on main

1. Mark the two machine sittings in the live study table as tests. First look, then change:

   ```
   cd ~/second-look/worker
   npx wrangler d1 execute second-look --remote --command "SELECT id, arm, is_test, started_at, completed_at FROM session WHERE is_test = 0"
   npx wrangler d1 execute second-look --remote --command "UPDATE session SET is_test = 1 WHERE is_test = 0 AND started_at < '2026-09-22T17:33:00Z'"
   ```

   Both rows were left by our own checks (Sep 21 and 2026-09-22 17:32 UTC); docs/deviations.md says how. Afterwards `curl -s https://second-look-api.thealexschroeder.workers.dev/api/test/counts` shows 0 randomized.

2. Put the Worker's QA key where the phone check can read it on purpose, for example `QA_KEY=... SITE_URL=https://second-look-79t.pages.dev node apps/web/scripts/live-check.mjs`. If you no longer have it, set a new one with `cd worker && npx wrangler secret put QA_KEY` and keep a copy in your password manager.
