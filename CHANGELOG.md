# Changelog

What shipped, day by day, in plain words. Days are Pacific time. The v1.0 section is the text of
the v1.0 tag and of its GitHub release, which `make go-public GO=yes` makes once the repository
is public, on the morning of Sat Oct 3. A day gets its line once it has shipped, and `make
go-public` stops before the flip if a day with commits has none. The numbers live in the README,
checked against `results/`.

## v1.0: the hackathon build, Sep 16 to Oct 3, 2026

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
- Part 2, the assisted second look: more photos after the score, where half the people who
  start it, picked at random, meet the checker's one question and keep or change their answer.
  No model is called while they answer. Its plan was tagged `prereg-v2` before any part 2 session.

### Sat Sep 26

- The creek check and the video walks ask the official OneAquaHealth Citizen Science App's own
  questions and answers, word for word, in every language the app carries them in. `make
  app-strings-check` holds our copy to the app's public translation file.
- Where a translation means something else than the English, the English shows in its place,
  marked.
- Every creek check and walk record states the language its questions were shown in.
- A creek check's FHIR record answers the rating the rating check left, and keeps the first
  rating beside it.
- Walk clips are served in parts, so moving the slider no longer starts a clip again.
- `/verify` offers each timestamp proof, and the file it stamps, as a download.
- The weekend build deployed and checked on a phone, the screens and the Devpost pictures taken
  again, and every README command run again in a fresh clone.

### Sep 27 to 28

- Nothing was committed. Judge mode opened by its lock constant at the first lock, Sep 27 at
  18:00 PDT, and stayed open until Sep 29.
- The Mac's data lock job started at 18:17 PDT and stopped at its own phone check, before any
  backup or analysis; the fix is under Sep 29.
- OneAquaHealth's sandbox answered again on Sep 28, and the re-push job put our golden visit back.

### Tue Sep 29

- The data lock job's faults fixed: its phone check expects judge mode shut before the lock and
  open from it on, its last check runs from the folder its path is written for, and it writes the
  audit log's `data_lock` line.
- A deploy asks the live database a question first, and stops when it cannot read the answer.
- The Mac jobs' records of Sep 28 and 29 committed, with every OpenTimestamps proof now confirmed
  in a Bitcoin block.
- The first data lock ran, on the job's fourth start: it had stopped at 18:17 PDT on Sep 27 and
  twice more this day, at 11:48 and 12:02, once at a check with a wrong path and once when the
  network dropped. The one pre-registered analysis ran on the locked data and the README's human
  row was written. Nobody had taken the test: the export held only our own checks and one
  automated judge walk, and the plan's rules leave them all out. Every run of the analysis read
  the same locked data, and none showed an outcome (`docs/deviations.md`).
- The hackathon's deadline moved to Sun Oct 4 at 21:00 PDT (UPDATE_33). The dates that follow
  it: the repository goes public on the morning of Sat Oct 3, the freeze is Sat Oct 3 at 09:00
  PDT, and the submission is on Sun Oct 4.
- A second wave of the study, under `docs/analysis_plan_v3.md`: the same design and analysis as
  before, for sittings from Sep 29 at 21:00 PDT up to the second lock, Fri Oct 2 at 21:00 PDT.
  The plan was tagged `prereg-v3` and anchored before any sitting of the wave. The lock job has
  a second run, ten minutes after that lock, and the README has the place for the wave's rows.
- Judge mode (`/demo`, `/t2/demo` and the two routes behind them) is shut again from 17:46 PDT,
  because it shows if each answer is right on the study's own photos. It opens at the second
  lock, Oct 3 at 04:00 UTC, which is Fri Oct 2 at 21:00 PDT. The two pages say when and why.
  The live checks and the lock's clock in `apps/web/lib/lock.ts` are tested in `make check`.
- The model card says where people meet the checker's question, which is part 2, and the data
  card counts part 2's photos as a set of their own.
- The third party list and `/credits` name the official app's words as the OneAquaHealth
  project's, under neither of our licences.
- The decisions of Sep 26 and Sep 29 written into `docs/DECISIONS.md`.
