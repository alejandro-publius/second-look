# 0011. Creek pages show iNaturalist sightings as context, from a daily copy, and nothing decides from them

- **Status:** accepted
- **Date:** 2026-09-24
- **Carried by:** commit f5cff68 (the read only route and the `inaturalist_cache` table), commit
  549c088 (the daily Mac job), commit 368bed1 (the line on the record page and `/city`, and the
  credits) and commit 43e2001 (the check of the plant photos); `scripts/cache_inaturalist.py`,
  `scripts/install_inaturalist_job.sh`, `worker/src/inaturalist.ts`, `apps/api/inaturalist.py`,
  `apps/web/components/InatContext.tsx`, `scripts/verify_inat_photos.py`,
  `scripts/tests/test_inaturalist.py`

## Context

A person who reports invasive plants on a creek bank, or a city analyst reading the creek, gains
from knowing what other people have seen there. iNaturalist holds that: research grade
observations, checked by more than one person, with a date, a place and a link. UPDATE_29 section 8
asks for one line of it per creek. Three risks come with it. A line shown before the invasive plant
question could lead the answer. A count from somewhere else could slip into our numbers or our
rules. And a live call from the Worker would make the page depend on a service we do not run, the
way their sandbox's DNS failure broke `/two` (ADR 0010).

## Decision

- The Mac asks, the Worker reads. `scripts/cache_inaturalist.py` runs once a day through launchd
  (`com.secondlook.inaturalist`, 07:45). It reads each creek's Locations from our own public API,
  asks https://api.inaturalist.org/v1/observations once per Location for research grade
  observations of the plants on the region pack's invasive list (by `inaturalist_taxon_id`),
  within `RADIUS_KM` of the Location and on or after the day `YEARS` years back. At most one request a
  second, with a user agent that names this repo, as iNaturalist asks of API users. It stores one
  summary per creek (per plant: the count, the latest date, a link to those observations) in the
  D1 table `inaturalist_cache` with the fetch time, by `wrangler d1 execute --remote` as
  `scripts/cache_their_records.py` does. A failed creek stores nothing, so the last copy stays.
- `GET /api/inaturalist/{creek}` on the Worker and on the Python API reads that copy and nothing
  else. It withholds the sightings until a finished visit on the creek has answered the invasive
  plant question. The gate opens once for the creek, not for each person: the route does not know
  who is asking, so after that first finished answer anyone who opens the record page or `/city`
  sees the line, a later volunteer who has not answered on that creek yet included. It keeps the
  line from leading the first answer on a creek, not every later one (review REVIEW_03 R07;
  `docs/DECISIONS.md` says why this stays).
- `InatContext` shows the line on the record page and on `/city` only, below what people reported,
  with the fetch time and iNaturalist's terms. With no copy, or an empty one, it says "There are no
  recent sightings on record." If the route fails or withholds the sightings, it shows nothing.
- The line is context. It is counted in no number, and neither server's route, nor the job, imports
  anything that reaches `core/gate.py`, `core/followups.py` or the check code. The guided check,
  the quick check, the test and judge mode never import the component.
- The plant photos in the lesson, the practice and the test that come from iNaturalist are credited
  by author and licence on `/credits`, beside what iNaturalist itself said about each when
  `scripts/verify_inat_photos.py` asked (`results/inat_photos.json`): research grade or not, inside
  California or not. Only those facts reach the browser, never the species, which for a test photo
  is its answer. The lesson screen itself carries no credit line: it is inside the two-minute test,
  which this change may not touch.

## Consequences

- The page works whether or not iNaturalist answers, and says how old its copy is.
- A later volunteer can read the line on a creek's record page before starting their own check
  there, because the gate is per creek. The guided check itself never shows it.
- Only plants on the approved region pack are asked about. The Bay Area list was approved for the
  team on 2026-09-25 with a taxon id for each of its 11 plants (UPDATE_30 section 3), and the job
  stored Strawberry Creek's copy that day; it shows once a finished check there has answered the
  invasive plant question.
- Each observation keeps the licence its observer chose. We store and show a plant name, a count,
  a date and a link, and never a photo, a note, a person's name or a position.
- A link names at most `MAX_LINK_IDS` observations, the newest, so a very busy creek links to part
  of what it counts.
