# Adopt Second Look in your city

One page for a follower city. Every command here exists in this repository today, and every
line number was checked on 2026-09-30. Two region packs exist: the Bay Area pack, filled and
approved, and the Heraklion stub, empty on purpose. Nothing here is a claim about any city. The
long form is `DEPLOY.md`.

## The steps, in order

1. Install: `uv sync`, then `(cd apps/web && npm ci)`, `(cd worker && npm ci)` and
   `(cd tools/diagrams && npm ci)`. Java 17 and gitleaks, as `DEPLOY.md`, "What you need", says.
2. Your Cloudflare account, once: the three steps in `DEPLOY.md`, "A new Cloudflare account,
   once". Make the D1 database and the KV namespace and put their ids in `worker/wrangler.jsonc`;
   apply `worker/schema.sql`, then `worker/arms.sql` and `worker/part2_arms.sql` once each; set
   the two Worker secrets with `npx wrangler secret put`. No card is needed.
3. Your city: `make new-city NAME=<city> COUNTRY=<country> LAT=<lat> LON=<lon> SITE=<your site>`.
   It writes a region pack stub, the nested Locations in FSH, a poster whose QR opens SITE, and
   a five step checklist in `docs/cities/<slug>/CHECKLIST.md`.
4. Fill the pack, `content/regions/<slug>.yaml`, by hand: `bbox`, the box the plant list is
   offered inside; `creeks` with their reaches; `invasive_plants` from your regional inventory,
   each with its source.
5. `bash scripts/fhir_build.sh`, then `make check`. The build puts your Locations inside their
   guide; the check runs the HL7 validator over every record the code makes.
6. `bash scripts/deploy.sh worker`, then `bash scripts/deploy.sh web`, from your `main`. Do not
   edit `scripts/deploy.sh` before Oct 3 2026: the lock job runs it on the night of Oct 2. The
   web deploy first cuts our walk clips from a video cache that is not in git and stops
   without it (`scripts/build_walks.py --clips-only`), so a city changes that line after Oct 3.

## The lines that name our site, and would name yours

| File | Lines today | What is ours there |
|---|---|---|
| `scripts/deploy.sh` | 26, 32, 41 | the D1 database's name, `second-look`; keep that name and these lines stay |
| `scripts/deploy.sh` | 57, 59, 62 | `https://second-look-79t.pages.dev` and the Pages project `second-look` |
| `worker/wrangler.jsonc` | 7, 10 | our D1 database id and our KV namespace id; the Worker's name is line 2 |
| `apps/web/wrangler.jsonc` | 8, 11 | the Pages project's name, and the Worker it binds as `API` |
| `scripts/new_city.py` | 38 | `DEFAULT_SITE`, the site a poster's QR opens when `SITE=` is not passed |

## The jobs a city would run

Of the nine Mac jobs in `DEPLOY.md`, "Jobs on the Mac", three: `backup`, `inaturalist` and
`repush`. The other six are this study's own and stop with it. The Worker has one cron today and
it runs only the two purges, so a job moved into the Worker is new code.

## What a city gets with no code change

- The creek check in the official app's six languages (en, pt, nl, no, fr, it), the browser's
  language first.
- Every visit as records under the OneAquaHealth profiles, from `core/fhir_emit.py`.
- The HL7 validator over every record in CI: `.github/workflows/check.yml` runs `make check`.
