# The tagged plan, and how to check it yourself

`docs/analysis_plan.md` became binding when it was tagged `prereg-v1` on 2026-09-21, before any
real participant. Nothing in it changes after that. Anything that does change is written in
`docs/deviations.md` with its date.

| Thing | Value |
|---|---|
| Tag | `prereg-v1` |
| Commit | `ca0a83251ef38d85f1e8d5d268df858e8819faff` |
| SHA-256 of `docs/analysis_plan.md` | `86da527e30c0a8e8492b6fb22c3056be1a2ad3087b5ca8c6f4a0a1bd58aed9cf` |
| Audit entry | kind `plan_tagged`, hash `3d3cbb4da01ac26e9e9579dac9681d67e5b034006cfc1ddd4215ea28d0fb3cc3` |

Check it on any machine with the repo:

```
shasum -a 256 docs/analysis_plan.md
git show prereg-v1:docs/analysis_plan.md | shasum -a 256
make audit-verify
```

The two sums must match each other and the table. `evals/usability_analysis.py` refuses to run
if the tag is missing or if the working copy of the plan differs from the tagged one, so the
analysis cannot quietly follow a plan written after the data.

Alex posts the SHA-256 publicly when he posts the link. The point is that anyone can see the
plan was fixed before the answers arrived.

## Part 2, the assisted second look: `prereg-v2`

`docs/analysis_plan_v2.md` became binding when it was tagged `prereg-v2` on 2026-09-26, before
any part 2 session existed (part 2 was not deployed yet). It changes nothing in the first plan.
Anything that changes after the tag is written in `docs/deviations.md` with its date.

| Thing | Value |
|---|---|
| Tag | `prereg-v2` |
| Commit | `d2ada333ea3c710589504e1bac7b9c6bb55b91a8` |
| SHA-256 of `docs/analysis_plan_v2.md` | `723f7980a2e05eba3b74f43826e0afbf2211a7c35da6dcc18581dba3df73a8c3` |
| Audit entry | kind `plan_tagged`, hash `bf68d0a8214227254cfdd23d5c90a7bf063cf02322388b5aaedc47ff635aec13` |
| OpenTimestamps | `proofs/prereg-v2.tag.ots` and `proofs/analysis_plan_v2.md.ots` |

```
shasum -a 256 docs/analysis_plan_v2.md
git show prereg-v2:docs/analysis_plan_v2.md | shasum -a 256
make audit-verify
```

`evals/assist_analysis.py` refuses to run if the tag is missing, if the working copy of the plan
differs from the tagged one, or if the tag does not point at the commit above.
