# How long a follower city took

Berkeley was built by hand as the first city. Every later city runs `make new-city`,
which writes its own row here.

| City | What | How measured | Time |
|---|---|---|---|
| Heraklion | `scripts/new_city.py` | wall clock of the script, measured by the script | 0.1 seconds, 4 files |
| Berkeley | the same four things by hand: the region pack, the nested Locations in FSH, the poster page, the five step section in the README | `git log --diff-filter=A` on each file; from the first commit (2026-09-20 14:00) to the last of the four (the poster page, 17:21), alongside everything else built that afternoon | 3 hours 21 minutes, 4 files |
