# UPDATE_19: answers from the planner, and the merge

If your context was just compacted, read docs/HANDOFF_NEXT.md and the "Status: Second Look" issue first.

1. Merge into main as soon as the QA key is set. Nobody is being recruited, so waiting for data lock on Sep 28 protects nothing. Update the status issue to say so.
2. PR #5: depth is the only source. Copy into depth only what #5 has and depth lacks (for example the teleprompter page, the judge Q&A, the upstream package, the when-Alex-is-back list), each checked by verify_claims, then close #5 with a comment saying where each file went.
3. Set the QA key yourself: generate one with openssl rand -hex 32, set it on the Worker with wrangler secret put QA_KEY, and keep a copy in the gitignored .env files in ~/second-look and ~/second-look-depth. Never print it or commit it.

Then merge, in the order in docs/notes/hosting.md:

a. CI must be green on depth first. If it is not, fix it from the failure logs.
b. Prove the two-minute test flow and the study endpoints are untouched since prereg-v1 with git diff --stat on their paths. If they are touched, stop and report.
c. Apply the additive D1 tables, deploy the Worker, and run the study contract tests and the phone end-to-end tests against production with the QA key.
d. Merge depth into main, ship the Pages build that puts the API behind the same origin, run the phone tests against production again, and confirm /demo still shows the shut page until Sep 28.
e. Close PR #1 as merged. Get CI green on main. Re-push to their sandbox if the golden visit or the Library entry is missing.
f. Update the status issue with what is live, the public link, and the first thing Alex does tonight.

Then write the report, copy it to the clipboard with pbcopy, print the report block, and stop.
