# Changelog

What shipped, day by day, in plain words. Days are Pacific time. The v1.0 section is the text of
the v1.0 tag and of its GitHub release, which `make go-public GO=yes` makes once the repository
is public. A day gets its line once it has shipped, and `make go-public` stops before the flip if
a day with commits has none. The numbers live in the README, checked against `results/`.

## v1.0: the hackathon build, Sep 16 to 30, 2026

### Sep 16 to 19

- The hackathon opened. Nothing was committed yet: the first commit is on Sep 20.

### Sun Sep 20

- The plan, the hard rules and the checks, with CI from the first hour.
- The FHIR proof: records built from OneAquaHealth's own guide validate with zero errors.
- The core as pure functions: the gate that turns model output into a flag or drops it, the
  follow-up questions, the rain rule, the score labels and the health card.
- The study and creek check API, the FHIR emitter, the pre-registered analysis and the web app,
  from the two-minute test to the creek record.
- The design pass: one set of colours and sizes, and a gate that fails the build on a raw value.
- Real, openly licensed photos, labelled and credited, and a write back to their sandbox.

### Mon Sep 21

- Hosting moved to Cloudflare: the site on Pages, the study on a Worker with its own database,
  no card needed.
- The Worker runs the same core as the Python, and golden vectors prove the two agree.
- A read-only MCP server over our records, and `make new-city` for a follower city.
- Health sentences only from an approved list, each with its source.
- The analysis plan tagged `prereg-v1` before anyone took the test.
- Three gates a judge can run: reading age, the diagrams, and `make judge-check`.

### Tue Sep 22

- Open creek footage from Wikimedia Commons: found by rule, every frame screened by Apple Vision
  for people and text, then checked by eye.
- Video walks: check a creek from your desk, on your phone.
- The Devpost text, the video's shot list and rough cut, and `make go-public` prepared.
- The sandbox re-push on a schedule, and a phone check of production that writes nothing.
- The answer key no longer reaches the browser.

### Wed Sep 23

- The first real AI run: vision models took the same photo test as people, and the gate ran on
  the creek footage. The README's AI table comes from it.
- The work merged to `main` and deployed; `/two` shows our record while their sandbox is down.
- The definition of done and its runner, the decision records, and three diagrams drawn from
  the code.
- The README in judge-first order, with a gallery of the real screens.

### Thu Sep 24

- Four models in the AI run: Claude Opus 5.5 and Fable 5.1 joined.
- The model card, the data card and the threat model.
- `/verify` and a daily OpenTimestamps anchor for the audit log.
- The iNaturalist context line on a creek's record, behind its own gate.
- `make reproduce` grades every AI number again from the raw replies; mutation testing on the
  modules that decide.
- The technical report, `docs/REPORT.pdf`, built from the README and `results/`.
- Contributed back to OneAquaHealth's guide: hl7-eu/oah pull request 5 and issues 6, 7 and 8.
- axe and Lighthouse on every page of production; a full review and the first critic rounds,
  each finding fixed with its proof.

### Fri Sep 25

- Critic rounds 09 to 13 and their fixes: the location works from every door, a walk says how to
  see a measure, and the words in the docs match what the product does.
- The Bay Area invasive plant list approved for the team, and every one-person gate made a team
  gate.
- `docs/JUDGE_DAY.md`: a judge's path in 45 seconds and in 10 minutes.
- `make go-public` does the whole day in order, with a dry run that touches nothing; submit-check
  holds the Devpost text to the form; this changelog.
- A video walk is kept as a demo record for 30 days, so its link opens on any device; it survives
  Back and a reload, and runs the creek check's follow-up questions.
- A first visit downloads 2.3 MB in the background instead of 24 MB, and a started test and the
  creek check keep working offline.
- On the Mac: the data lock and analysis job for Sep 27, uptime every 10 minutes, the daily
  sandbox retry, and `make rollback`.
- The captions-only video, built by `make video-final`, and critic rounds 14 to 17.
