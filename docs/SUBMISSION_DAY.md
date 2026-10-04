# Submitting on Sunday Oct 4

The repository is public. The second-wave lock analysis has run, its results are in the README,
and the lock job deployed the site. The original cutoff and tagged analysis stayed fixed.
The failed job and late retry are recorded in [deviations](deviations.md).

The deadline is Sunday Oct 4 at 21:00 PDT. Alex's checklist on the
[status issue](https://github.com/alejandro-publius/second-look/issues/4) targets 17:00 PDT.

## What remains

1. Upload the final demo video and put its working link in `README.md`, `docs/devpost.md`
   and Devpost. Publication went ahead with Alex's explicit exception for this missing link;
   `make submit-check` still requires it.
2. Run `make submit-check` from an up-to-date main checkout. It must report no failed checks.
3. Review the Devpost copy from `docs/devpost.md`, the gallery, and Rachel's team membership.
   Replace the attached report with `docs/REPORT.pdf` from current main. Neither study wave
   retained eligible completed sittings, so no human benefit was measured.
4. Submit on Devpost by 17:00 PDT, check the public links, and save the confirmation.
5. Put the submitted project's Devpost link in `docs/devpost.md`, commit and push.
   `uv run python scripts/done_items.py devpost-submitted` checks that record.

## Publication command reference

Publication has completed. Keep the release tag and pre-registration tags where they are.
The command `make go-public GO=yes` is idempotent: steps already completed are skipped.

## If a step says FAIL

Fix what its line names, then run the same command again. Every step before the flip is safe
to repeat: the notes commit is made once and then skipped. After the flip, `flip`, `tag` and
`release` skip themselves when they are already done, so a second `make go-public GO=yes` only
finishes what is left.

| Step | What its FAIL means | What to do |
|---|---|---|
| start | Not on `main`, the tree is not clean, or `main` is behind GitHub | `git switch main`, commit or undo the changes, `git pull --ff-only` |
| secrets | gitleaks or the tree scan found something that looks like a key | If it is a made-up test value, add its fingerprint to `.gitleaksignore` with a reason. If it is a real key: stop, revoke the key, and ask. History is never rewritten (hard rule 15). |
| notes | A tracked file still names the working notes | Reword the file the line names |
| tests | `make lint` or a Python test failed on the tree without the notes | Fix what the line names |
| submit | `make submit-check` failed on more than the repo being private | Fix the named check: usually the video link or a Devpost field |
| readme | An image, a link or a heading in the README does not answer | Fix the README |
| changelog | A day with commits has no line in `CHANGELOG.md` | Add the line |
| push | GitHub refused the push | `git pull --ff-only`, then run again |
| flip | `gh` could not make the repo public | `gh auth status` must show the `repo` scope |
| public | A stranger could not load the page, an image, the badge or the live link | GitHub can take a few minutes after the flip: wait five and run `make go-public GO=yes` again |
| tag, release | The tag or the release was not made | Run `make go-public GO=yes` again. It never moves a v1.0 that names another commit. |
