# Context ledger

Facts about this project that are true outside any one session, and are not recoverable from the
code. Thirty lines at most. Add a line only when it will still matter next week.

- The planner works in a separate chat. It reads skills this terminal does not have: an anti-slop
  frontend skill, Anthropic's frontend design skill, Vercel's web interface guidelines, a
  collection of DESIGN.md reference systems, and skills for UX copy, accessibility review and
  design critique. Ask the planner to distil, do not expect them here.
- Figma is connected on the planning side, not here. A Figma file is a planner request.
- Alex is a native Spanish speaker. He checks every Spanish string himself. Draft `es` strings may
  exist but stay out of the build until he signs the file with his name and the date.
- Rachel Selbrede owns ecology copy, the four question wordings, the lesson text, the rules of
  thumb, the invasive plant list and the gold labels. Nothing she owns ships while `approved` is
  false. Alex is the second, blind labeller.
- The repo stays private until submission day, 2026-09-30. Nothing is published before then.
- Precedence when files disagree: the newest file in docs/updates/ wins, then
  docs/MASTER_BRIEF.md, then PLAN.md, unless docs/DECISIONS.md records the change. For look,
  reading and feel, docs/updates/UPDATE_06.md and docs/design/DESIGN.md win.
- Update 03 was never pasted into this terminal. P1, P2, P3, K6 and fallback F2 were built from
  Update 04's descriptions of them. If Update 03 turns up, check docs/KILL_TESTS.md against it.
- Every session ends with the report block from docs/updates/UPDATE_02.md section 1, copied to the
  clipboard, and nothing printed after it.
- The study API origin in tests is http://127.0.0.1:8100 and it is always mocked. If you start
  `npm run start` by hand, set NEXT_PUBLIC_API_ORIGIN to it, or Playwright will reuse your server
  and every mocked call will miss. That failure looks like the app being broken.
- No call ever goes to api.enora-oah.eu until Alex says permission arrived.
- ANTHROPIC_API_KEY never goes in a shell where Claude Code runs. No paid model call has run yet.
