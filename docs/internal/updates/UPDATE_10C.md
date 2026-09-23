# Second Look: Update 10C (answers, and the downstream note pinned)

Pasted into Claude Code on 2026-09-21. Everything below is addressed to Claude Code.

Answers to your three questions. Save this as docs/updates/UPDATE_10C.md in ~/second-look-depth.

1. Open a draft pull request from depth to main now, so CI runs on every push. Title it "Depth: do not merge before data lock". It stays a draft. Nothing merges yet.
2. The merge waits until after data lock on Sep 27. Production stays exactly as it is while strangers take the test: nothing about the study's network path changes mid-study. At the merge, do both in one session in this order: apply the new D1 tables (additive only) and deploy the Worker, run the study contract tests and the phone end-to-end tests against production, and only then ship the Pages file that puts the API behind the same origin, and run the phone tests again. Write that order into docs/notes/hosting.md.
3. Mirror real creek visits to their sandbox once, as one tagged batch after data lock, not as they arrive. Fewer writes on a server everyone shares, and one clean ledger. Two-minute test sessions are never mirrored, because they are not creek observations. Re-run the repush just before the video is recorded, again on Sep 30, and again on Oct 1, because anyone can delete records there. Update the Library entry's count at each push.

Then one piece of work: add the golden vectors for notes_below and the downstream line, so the TypeScript port is pinned like the others. make check, commit, push, refresh docs/HANDOFF_NEXT.md. Then write the report, copy it to the clipboard with pbcopy, print the report block, and stop. Tier 3 and tier 4 stay parked.
