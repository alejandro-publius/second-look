# Timestamp proofs

OpenTimestamps is a public timestamp service. It is not ours, and it is not our own chain. You give
it the SHA-256 hash of a file; its calendars gather many hashes and write one summary of them into
a Bitcoin transaction. Once that transaction is in a block, the proof shows the file existed no
later than that block. Only the hash leaves this machine, never the file.

| Proof | What it stamps | Check it |
|---|---|---|
| `prereg-v1.tag.ots` | `prereg-v1.tag`, the raw bytes of the `prereg-v1` tag object | `uv run ots verify proofs/prereg-v1.tag.ots` |
| `analysis_plan.md.ots` | `docs/analysis_plan.md`, unchanged since the tag | `uv run ots verify -f docs/analysis_plan.md proofs/analysis_plan.md.ots` |
| `prereg-v2.tag.ots` | `prereg-v2.tag`, the raw bytes of the `prereg-v2` tag object, part 2's plan | `uv run ots verify proofs/prereg-v2.tag.ots` |
| `analysis_plan_v2.md.ots` | `docs/analysis_plan_v2.md`, unchanged since the tag | `uv run ots verify -f docs/analysis_plan_v2.md proofs/analysis_plan_v2.md.ots` |
| `audit-head-<date>.ots` | `audit-head-<date>`, the text `audit/log.jsonl` hashes for its last entry on that date, so the file's SHA-256 is that entry's hash | `uv run ots verify proofs/audit-head-<date>.ots` |

`prereg-v1.tag` is exactly what `git cat-file tag prereg-v1` prints. Git names a tag object by the
hash of those bytes, and the tag names the commit, which names every file in it. So one stamp
covers the whole repository at the tag. Check the bytes are the tag's own:

    git cat-file tag prereg-v1 | cmp - proofs/prereg-v1.tag
    git hash-object -t tag proofs/prereg-v1.tag   # prints the same id as: git rev-parse prereg-v1

A proof starts out pending: the calendars have promised to include the hash. A few hours later it
can be upgraded to a complete proof that names a Bitcoin block. `uv run python scripts/ots_status.py`
asks the calendars for that, saves any upgrade here, and writes each proof's status and block
height to `results/ots.json`, which `/verify` shows. `ots verify` needs a Bitcoin node to check a
complete proof on its own; without one, `ots_status.py` checks the block header against a public
block explorer instead.

The first two proofs were stamped on 2026-09-24, after the tag was made on 2026-09-22. Once
confirmed, they show the plan and the tag existed no later than the confirming block, whose time
`results/ots.json` records; data lock is 2026-09-28T01:00:00Z. They do not prove the tag's own
date; the tag, the audit log and GitHub's copy of the repository speak to that.

`ots verify` checks an audit head proof against its copy of the line here, in
`audit-head-<date>`, and a rewrite of the log with fresh hashes still passes
`scripts/verify_audit.py`. So `scripts/ots_status.py` and `/verify` also compare each stamped line
with the same line of `audit/log.jsonl`, and call the proof broken when the log no longer has it.

`scripts/anchor_audit_head.py` stamps the audit log's last hash, and
`scripts/install_anchor_job.sh` runs it once a day on this Mac with launchd. It stamps nothing when
the last hash has not changed since the newest proof. The audit log is a hash-chained audit log,
not a blockchain.
