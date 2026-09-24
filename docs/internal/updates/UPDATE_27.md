# Second Look: prompt 27 (keep working while Alex is away)

Alex: quit Claude Code so the waiting update applies, run `cd ~/second-look-depth && claude`, paste this whole file, then type the `/goal` line at the bottom of this file, then go. If `/goal` comes back as unknown, ignore it: this prompt keeps the run going on its own.

Everything below is addressed to Claude Code.

## Start of this session

You have no memory of earlier work. Read `CLAUDE.md`, `PLAN.md`, `docs/HANDOFF_NEXT.md` and the newest file in `docs/internal/reports/`, which is UPDATE_22's report: it shipped at b876a2b with `main` equal to `depth`, CI green, the AI run done for real, the footage in the rough cut, and their sandbox name still not resolving. Then answer its three open points before anything else:

1. Finding F86, the demo answer route revealing the gold key before Sep 28: fix it now with a lock check, as a logged deviation. The README says judge mode is shut until Sep 28, so an API that hands out the key contradicts a claim judges will read.
2. Patch 04, which closes F06 to F08 (the analysis running on real data before the lock through test flags): apply it as a logged deviation. It strengthens the pre-registration claim, which is also in the README.
3. The health sentence person_no_swallow: approve it if its `source_quote` supports it word for word; otherwise drop it. Do not wait for Alex.

Then continue with section 1 below, starting at UPDATE_23, because UPDATE_22 is finished.

## 0. The one instruction

Alex is away. Carry straight on through everything below, and do not end the turn while any item in the definition of done is RED. If you think you are finished, run `make done-check` and continue with the top RED item. The turn ends only when the count reads `RED: 0` with only HUMAN and BLOCKED items left. Save this text as `docs/internal/updates/UPDATE_27.md`.

## 1. Where the instructions are

Prompts 23 to 26 may already be queued as messages after this one, or already saved in the repo, or neither. Handle all three cases the same way: before each one, check whether `docs/internal/updates/UPDATE_23.md`, `UPDATE_24.md`, `UPDATE_25.md` and `UPDATE_26.md` exist. For any that does not, look for the file in `~/Downloads/` (`SECOND_LOOK_PROMPT_23_REPO_POLISH.md`, `SECOND_LOOK_PROMPT_24_TIDELINE_LAYER.md`, `SECOND_LOOK_PROMPT_25_UNTIL_DONE.md`, `SECOND_LOOK_PROMPT_26_GOAL_MODE.md`), copy it into `docs/internal/updates/` under the UPDATE name, and follow it. If a file is in neither place, follow section 3 of this prompt for that block. If the same prompt later arrives as a queued message, treat it as already done and skip it.

Order: finish and ship UPDATE_22; then UPDATE_23 (screenshots, the GIF, the three Mermaid diagrams, the judge-first README); then UPDATE_24 (the Tideline layer); then UPDATE_25 and UPDATE_26 together (the checklist, `make done-check`, `docs/internal/PLAN_TO_DONE.md`); then the loop in section 2.

## 2. The loop

1. Run `make done-check`. Take the top RED item in file order. Fix it, prove it with its own command, `make check`, commit, push.
2. Refresh `docs/HANDOFF_NEXT.md` with the DONE table and the item you are on. If context is tight, write the handoff and continue in a fresh subagent with the reading order from UPDATE_26 section 1.
3. Print the full `make done-check` output, the line `RED: <n> BLOCKED: <n> HUMAN: <n>`, and the newest CI result on `main` and `depth` from `gh run list`, after every item, so the evaluator in goal mode can see it.
4. Go to 1. Never skip an item because it looks hard: split it and keep going. An item that cannot pass because of something outside the repo (their DNS, a service down, the missing API key) is marked BLOCKED with the reason and the date, re-tested on every pass, and never counted as RED. Never weaken an item's command to make it pass.
5. When `RED: 0`: merge forward to `main`, wait for CI, rewrite the top of the "Status: Second Look" issue for Alex (what is live, the public link, what is green, and only the human items in order with dates), write the report under `docs/internal/reports/`, copy it to the clipboard with `pbcopy`, print the report block, and stop.

## 3. If a prompt file is missing, this is the block

- **23, the repo lift:** real screenshots of every screen from the live site in one device frame under 400 KB each, a GIF of the two-minute test under 3 MB, two lesson photos with marks, three Mermaid diagrams (the system map by the five verbs with labelled edges, the FHIR resource graph, the AI gate as a sequence diagram) rendered by `make diagrams` in CI, and the README in judge-first order: track statement, the one sentence, badges, the two warm-up photos with "Which creek is healthier?" and the answer in a details block, three links, the GIF, numbers at a glance, the gallery, why trust a volunteer and the AI, what the AI cannot do, architecture, how OneAquaHealth is used, evals, real versus synthetic, quickstart with `make judge-check`, for judges, known weaknesses, how this was built, credits, repo map, licence. Repo description, homepage and topics set. A 1280 by 640 social preview image made.
- **24, the Tideline layer:** the gate as the heart of it in numbered steps naming files; three properties that follow, each tied to a test; engineering challenges with `WRITEUP.md`; security and privacy; the API table; the MCP tools table; the tech stack; running locally with offline demo data and a tests paragraph with counts; `DEPLOY.md` and a configuration table; 8 to 10 ADRs in `docs/adr/`; Dependabot; pre-commit; up to 12 topics.
- **25 and 26, the checklist:** `docs/internal/DONE.md`, one line per item in the order above plus hardening (a second adversarial review, the six-judge simulation with a rerun, axe clean with an `/accessibility` page, Lighthouse and a load test, 90 percent coverage on `core/`, no flaky tests over three runs, every README command executed, a link check, `make readability`), the submission pack (Devpost text verified, `make submit-check` red only on the video and the repo being public, `make go-public` prepared, `docs/ALEX_TODO.md` with only human steps), the dated items (data lock 2026-09-28T01:00:00Z, the analysis run once as a description, `/demo` opening on Sep 28, the sandbox re-push when the name resolves), and the human items (the API key, the voice recording, the social preview upload, Devpost and the video upload, go-public and submission on Sep 30). Each line has a command that fails when the thing is missing; `scripts/done_check.py` and `make done-check` print PASS, RED, BLOCKED or HUMAN per line and the counts at the end. Break three commands on purpose and watch them go red before trusting the list.

## 4. Rules that never change

Work on `depth` and merge forward to `main`. Nothing in the two-minute test flow, the study endpoints or the Worker's logic changes. Decide instead of asking and log each decision in `docs/DECISIONS.md`. Never make the repo public. Never delete by search or `$expunge` on their sandbox. No em dashes, en dashes or emoji. Up to four subagents at a time, each in its own worktree. Paid model calls are not capped: run the AI on the 16-photo test and on the footage in full, with the current Opus model in place of Opus 5, and add a fourth run with the strongest model available if it helps the README. The eval scripts call the API themselves, so they need `ANTHROPIC_API_KEY` in `~/second-look-depth/.env`; if it is not there, that one item is HUMAN and everything else proceeds.

## 5. The line for Alex to type after pasting this

```
/goal make done-check has been run in this turn and its full output is in the transcript, ending with "RED: 0"; every BLOCKED line names a cause outside the repo with a date; gh run list output in this turn shows the newest run on main and on depth as completed success; the newest two critic rounds under docs/internal/reviews/ both report nothing above cosmetic; and the top paragraph of the "Status: Second Look" issue lists only HUMAN items. Stop after 400 turns at most.
```
