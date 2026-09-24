# Plan to done: from here to RED: 0

UPDATE_27 sections 0 to 3. Written 2026-09-24 (Thursday) against `docs/internal/DONE.md`. Run
`make done-check` to see where things stand; it ends with `RED: <n> BLOCKED: <n> HUMAN: <n>`. The
run is over when RED is 0 and only BLOCKED and HUMAN lines are left. Times are UTC first, with
Pacific time where Alex acts.

Who is who:

- **The session** is the Claude Code run in `~/second-look-depth` that owns `depth` and `main`:
  it merges, runs `make check`, pushes, deploys in the order in `docs/notes/hosting.md`, and runs
  the loop in UPDATE_27 section 2.
- **A subagent** works in its own worktree on its own branch cut from `depth`, never pushes and
  never merges. Four at a time at most (UPDATE_27 section 4).
- **Alex** does only the HUMAN items. Each one is in `docs/ALEX_TODO.md` with its date.

Where it stands on Sep 24: D01, D07, D22, D29, D33 to D36 and the API key (D42) pass. D38 to D40
wait for the lock and D41 waits for their sandbox's name as well. Every other CHECK item is RED
because its work is being built in parallel right now.

## Thursday Sep 24: build the missing parts

1. **Subagents, in parallel, each on its own branch from `depth`** (running now):
   - `p27/visuals`: the screenshots in one device frame (D02), the GIF of the test (D03), the two
     lesson photos with marks (D04), the 1280 by 640 social preview image (D08).
   - `p27/diagrams`: the three Mermaid diagrams and their rendering in CI (D05).
   - `p27/tideline`: the Tideline layer (D09 to D21): the gate steps, the three properties,
     `WRITEUP.md`, security and privacy, the API and MCP tables, the tech stack, running locally,
     the tests paragraph, `DEPLOY.md`, the ADRs, Dependabot and pre-commit.
   - `p27/done`: this checklist, `make done-check` and this plan.
2. **The session** merges these branches into `depth` one at a time, with `make check` green
   after each merge, and fixes any clash.
3. **A README subagent** folds all of it into `README.md` in the judge-first order (D06), keeps
   the five organizer headers that `make submit-check` reads, and renders every number from
   `results/` through claim tokens. The Tideline sections land in the README here, so D09 to D17
   turn green only after this step.
4. **The session** rewrites `docs/ALEX_TODO.md` to the HUMAN items only, each with its date
   (D37); the dry run on Sep 27 belongs inside the Devpost step. Then `make done-check`.

## Friday Sep 25: harden the finished repo

5. **The session** merges `depth` into `main` and deploys the Worker, then Pages, in the order in
   `docs/notes/hosting.md`, with the phone tests after each. The `/accessibility` page and the new
   screens are then live, so the hardening below measures what judges will see.
6. **Subagents, one per measurement**, each at a commit that contains 8cecc38, writing to
   `results/harden/`: axe on every screen with the `/accessibility` page (D26), Lighthouse (D27),
   the load test on the live site with GET requests only (D28), the test suites three times
   (D30), every README command run in a fresh clone (D31), the link check (D32).
7. **Reviewer subagents that wrote none of the code**: the adversarial review of the finished repo
   as `REVIEW_03.md` (D23), then critic rounds `CRITIC_01.md` onward, each fixed by the session
   before the next, until two rounds in a row report nothing above cosmetic (D24), and the
   six-judge simulation rerun as `JUDGE_SIM_01_after.md` on the same inputs as the baseline
   (D25).
8. **Alex, Fri Sep 25**: record the voice against the rough cut, saved in
   `~/second-look-media/voice/` (D43).

## Saturday Sep 26: the submission pack

9. **The session** keeps `make submit-check` failing only on `video_link` and `repo_public`
   (D35) and `make go-public` ready (D36) after every merge.
10. **Alex, Sat Sep 26**: paste `docs/devpost.md` into the Devpost draft and put the project page
    link in that file (D45); upload the social preview image in the repo's settings (D44).
11. **The session**: the loop in UPDATE_27 section 2 until `make done-check` reads `RED: 0`, then
    merges forward to `main`, waits for CI, and rewrites the status issue with only the HUMAN
    items in order with their dates.

## Monday Sep 28, 01:00 UTC (Sunday Sep 27, 18:00 PDT): the data lock

12. **The session**, after the lock: the `data_lock` entry in the audit log (D38), the analysis
    run once on real data as a description (D39), and a check that `/demo` shows judge mode open
    on the live site (D40, `make demo-open-check`).
13. **The session**: the sandbox re-push as one tagged batch if `sandbox.hl7europe.eu` resolves
    again (D41). While it does not, D41 stays BLOCKED with its cause, tested again on every pass,
    and never counts as RED.
14. **Alex, Sun Sep 27 (PDT)**: the dry-run submission on Devpost, read back as a judge would, as
    part of D45.

## Tuesday Sep 29: the video

15. **The session** lays Alex's voice over the rough cut in place of the scratch voice, keeping
    every credit line and the CC BY-SA 4.0 end card.
16. **Alex, Tue Sep 29**: upload the video from his account and put the link in the README and in
    `docs/devpost.md` (D46). After this, `make submit-check` fails only on `repo_public`.

## Wednesday Sep 30: public and submitted

17. **Alex, Wed Sep 30 morning**: on `main`, `make go-public`, then `make go-public GO=yes` (D47).
    It removes these working notes, this file included, runs `make submit-check`, and only then
    makes the repository public.
18. **Alex, Wed Sep 30 by 18:00 PDT**: submit on Devpost (D48).

## Last block: UPDATE_29, undeniable

Taken only after every item above is PASS, HUMAN or BLOCKED, except the panel study's software
side (D49, D50), which is done at once because Alex needs it by Sep 26 evening.

19. **The session, Sep 24**: the panel study's software side and `docs/internal/PANEL_STUDY.md`
    (D49, D50), as a logged deviation.
20. **Alex, by Sat Sep 26 evening, 15 minutes**: create and fund the panel study from
    `docs/internal/PANEL_STUDY.md` and launch it (D51).
21. **The session**: contribute back to hl7-eu/oah (D53); OpenTimestamps and `/verify` (D54, D55);
    `make reproduce`, mutation testing, Lighthouse on the landing page (D56 to D58); the model card,
    threat model, report and data card (D59 to D62); iNaturalist context (D64); then the loop over
    everything new (D65).
22. **Rachel, optional, 15 minutes**: a second set of labels (D63).
23. **The session, after the lock on Sep 28**: the analysis once, into the README's human row (D52).
