# 0001. The site is a static export on Cloudflare Pages, with the API on the same origin

- **Status:** accepted
- **Date:** 2026-09-21
- **Carried by:** commit 2f61b23 ("One person can launch, on Cloudflare") and commit 2c441e9
  ("the API behind /api/* on the Pages origin"); `apps/web/next.config.ts`,
  `apps/web/security-headers.mjs`, `apps/web/scripts/build-headers.mjs`, `apps/web/wrangler.jsonc`,
  `apps/web/functions/`, `apps/web/public/_routes.json`

## Context

The first plan was Vercel for the web app and Fly.io for the API. Both wanted a card, and one
person had to be able to launch alone. The study needs strict security headers, no third party
anything, and a fast first screen on a phone. Some networks block `workers.dev` addresses.

## Decision

Build the Next.js app as a static export (`npm run export`, which sets `NEXT_EXPORT=1`) and serve
it from Cloudflare Pages. Pages hands every `/api/*` and `/health` request to the API Worker
through a service binding, so the browser talks to one origin only. The security headers have one
definition, `apps/web/security-headers.mjs`, which the server build reads and
`apps/web/scripts/build-headers.mjs` writes into `public/_headers` for Pages.

## Consequences

- Nothing needs a card. The policy can say `connect-src 'self'`.
- A static export cannot read a path it did not know at build time, so `/spot/[id]` became
  `/spot?id=` and `/quick/[spot]` became `/quick?spot=`.
- A static export gets no headers from Next at all. Without the one definition, the strict policy
  would have vanished on deploy with nothing failing.
- Once the project gained the `/api` Functions, Pages stopped turning preload tags into Early
  Hints, so the site writes its own Link headers (see `WRITEUP.md`, part 9).
- A Pages wrangler file becomes the project's source of truth for the environment it is deployed
  to, so the production deploy of that file was done knowingly, in the order of
  `docs/notes/hosting.md`.
