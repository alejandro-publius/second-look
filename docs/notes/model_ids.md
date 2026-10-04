# Model ids and prices, checked before any paid run

Update 09 section 4.7. No paid model call has run yet. Check this file again if more than a few
days pass: prices and ids move.

**Checked 2026-09-21** against https://platform.claude.com/docs/en/about-claude/pricing (the
older docs.claude.com path now redirects there).

**In use from 2026-09-24** (UPDATE_27 section 4): `claude-haiku-4-5-20251001`, `claude-sonnet-5`,
`claude-opus-5-5` in place of the legacy `claude-opus-5`, and `claude-fable-5-1`, the strongest
model on the models page, as a fourth observer. Opus 5.5 costs $4 and $20 per MTok and Fable 5.1
$10 and $50, both checked on the pages below on 2026-09-23; one direct call to each with our
prompt and tool answered through the tool in about 120 output tokens.

**Re-confirmed 2026-09-23** (UPDATE_22 section 3) on the models overview page
(https://platform.claude.com/docs/en/about-claude/models/overview) and the pricing page. The three
ids in `evals/models.yaml` still answer exactly as below, at the same prices and batch prices.
What changed since Sep 21: `claude-opus-5` is now listed as a legacy model, still available, and
the current Opus is Claude Opus 5.5, `claude-opus-5-5`, at $4 input and $20 output per MTok ($2
and $10 in a batch), retiring no sooner than 2027-09-22. Claude Haiku 4.5 still retires no sooner
than 2026-10-15, and Sonnet 5's $2 and $10 is now its standard price. The config is left as it is:
the paid run needs Alex's key and Alex's word on the flags, and swapping Opus 5 for Opus 5.5 is one
line in `evals/models.yaml` plus its row in `evals/pricing.yaml` when that word comes.

**Re-confirmed 2026-09-21, this time on the models overview page**
(https://platform.claude.com/docs/en/about-claude/models/overview), which is where the API ids
live. All three ids below are exactly what that page's "Claude API ID" row gives, and the prices
match its pricing row. Two things worth writing down from that page:

- Every current id is a pinned snapshot, dateless ones included. `claude-haiku-4-5-20251001` is
  the pinned id and `claude-haiku-4-5` is its alias; we keep the pinned one so a rerun in October
  answers the same question as a run today.
- Claude Haiku 4.5 retires no sooner than 2026-10-15. That is after the deadline, but anyone
  rerunning our evals later should expect to swap it.

The three models the team's working notes (MASTER BRIEF) names for the test run, cheapest first:

| Model | Id used in our config | Input per MTok | Output per MTok | Batch input | Batch output |
|---|---|---|---|---|---|
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | $1 | $5 | $0.50 | $2.50 |
| Claude Sonnet 5 | `claude-sonnet-5` | $2 | $10 | $1 | $5 |
| Claude Opus 5 | `claude-opus-5` | $5 | $25 | $2.50 | $12.50 |

All three are confirmed against the models overview page as of 2026-09-21. Every current model
takes image input, which is what this run needs. Haiku 4.5 does not support the effort parameter
and still uses the older thinking shape; we send neither, so the same request body works on all
three.

## What this means for our budget

We use the Batch API for evals, which is half price on both input and output. The pre-registered
model run is 16 photos, one question each, three repeat runs, three models: 144 image requests.
A photo resized to 1092 px on the long side is roughly 1,600 input tokens, and our answers are
short, so a run is on the order of tens of cents at batch rates, not dollars. The P3 probe is
boxed at 1 dollar and 8 photos.

Rules that still hold:

- Every call is logged to `results/cost_log.jsonl` with model, tokens, cost and purpose. Fake
  client runs write `results/cost_log_fake.jsonl` instead, so the real log stays about money.
- The spend checks in PLAN.md: above 150 dollars by Sep 23 or 350 by Sep 26, routine sessions
  drop to the cheaper model and nothing tagged COULD is built.
- `ANTHROPIC_API_KEY` lives in `.env` in this repo on this Mac and is never exported in the shell
  that starts `claude`.

## Things on the page worth knowing

- Prompt caching: a 5 minute cache write is 1.25x base input and a cache hit is 0.1x. Not useful
  for a batch of independent photo questions.
- The Batch API discount and caching multipliers stack.
- Claude 4.6 and later carry the full 1M token context at standard pricing. Irrelevant to us; our
  requests are one photo and one question.

**Re-confirmed 2026-09-22** (Update 14 section 3 item 1) against the Claude API reference bundled
with Claude Code (its model table, cached 2026-06-24). The three ids above are still current and
their prices are unchanged; the Batch API still halves both input and output. Claude Opus 5.5
(`claude-opus-5-5`, $4 and $20 per MTok) is launching. The brief names Opus 5, and the
configuration was frozen with it, so it stays; a later run may add Opus 5.5 as a fourth row.
No paid call has run: `.env` holds no `ANTHROPIC_API_KEY`, so this run used the fake client.
