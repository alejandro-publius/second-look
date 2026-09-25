Summary: the stage 2 order for UPDATE_31, from the merge of origin/depth to the report.

1. Wait: a report newer than 2026-09-25T18:00Z under `docs/internal/reports/` on `origin/depth`,
   and no commit on `depth` for 20 minutes. Or 2026-09-26T13:00Z, whichever comes first.
2. `git merge origin/depth` into `assisted`. Resolve by merging, never by taking one side:
   `worker/src/content.json` and `apps/web/generated` are rebuilt, not merged by hand
   (`uv run python scripts/build_worker_content.py`, `node apps/web/scripts/build-content.mjs`).
3. `git apply` 01 and 02. Apply 03 to 07 by hand as written. Delete nothing prompt 30 added.
4. Recount tests (`scripts/count_tests.py`) if the README quotes counts, `make check` green.
5. Tag, before any part 2 session exists (none can: part 2 is not deployed yet):
   - commit, then `git tag -a prereg-v2 -m "Part 2 analysis plan"` on that commit;
   - `shasum -a 256 docs/analysis_plan_v2.md` and the commit into `docs/notes/plan_hash.md`, a
     second table under the first;
   - pin `PLAN_COMMIT` and `PLAN_SHA256` in `evals/assist_analysis.py` in the next commit (the
     plan file itself does not change, so the tag stays valid);
   - an audit entry, kind `plan_tagged`, payload naming `prereg-v2`, the commit and the hash
     (`scripts/audit_log.py append`); `make audit-verify`;
   - `git cat-file tag prereg-v2 > proofs/prereg-v2.tag`, `ots stamp proofs/prereg-v2.tag`,
     and the same for the plan as `proofs/analysis_plan_v2.md.ots`; `scripts/ots_status.py`
     learns the two new proofs.
   - push the tag.
6. Merge `assisted` into `depth`, fast-forward `main` to `depth`.
7. Deploy in the order of `docs/notes/hosting.md`: D1 tables (`worker/schema.sql`, safe to run
   again), then once `worker/part2_arms.sql` (only if `SELECT COUNT(*) FROM part2_slot` is 0),
   then `bash scripts/deploy.sh worker`, the contract tests and the part 1 phone check, then
   `bash scripts/deploy.sh web`, then the phone checks again.
8. `SITE_URL=https://second-look-79t.pages.dev QA_KEY=<from .env> node apps/web/scripts/live-part2.mjs`
   writes `results/part2_live_check.json`: both arms, a Keep and a Change, real counts unchanged.
   Commit it. `uv run python scripts/deploy_record.py good` once both checks pass.
9. `make panel-status --issue` style update of the status issue, `make done-check`.
10. The report under `docs/internal/reports/`, `pbcopy`, the report block, stop.
