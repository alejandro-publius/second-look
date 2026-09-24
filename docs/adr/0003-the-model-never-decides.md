# 0003. The model never decides

- **Status:** accepted
- **Date:** 2026-09-20
- **Carried by:** commit c73ab6a (the gate and the follow-ups as pure functions) and commit
  e0b2fdc (the checker that can only ask); `core/gate.py`, `core/checker.py`, `core/followups.py`,
  `core/tests/test_gate.py`

## Context

A vision model can help a volunteer look again, but its output is text we do not control. If it
could set an answer, a label or a score, a stored observation would no longer be the person's, and
nobody could say how far to trust it. Hard rule 2 in `CLAUDE.md`.

## Decision

Model output becomes `Flag` objects through `core/gate.py` or is dropped with a reason. A flag can
only make one follow-up question eligible. Follow-up selection in `core/followups.py` is a pure
function of the answers, the site, the person's scores and the flags: two questions at most, the
model's at most one, asked after the person has answered, with no model call inside it.
`build_record` is the only way a record is made and has no parameter that can carry model output.
The model's note reaches a person only labelled "the checker noticed", cut to a short length.

## Consequences

- The model has no path to the store. Fuzz tests throw arbitrary output at the gate and check that
  nothing reaches an answer or a label.
- Any change to the gate ships with a test in the same commit.
- Neither server calls the checker on a creek check today: both pass the follow-up selector no
  flags, whatever `CHECKER_ENABLED` says. The model's flags reach people only in the video walks,
  where `scripts/build_walks.py` sends them through the same gate at build time, and only on
  features in the pass table (`docs/adr/0004-pass-table-per-feature.md`).
- A model that is right more often than a person still cannot overrule them. That is the point:
  the record says what the person saw, next to how well they see it.
