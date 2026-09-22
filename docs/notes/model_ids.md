# Model ids and prices, checked before any paid run

Update 09 section 4.7. No paid model call has run yet. Check this file again if more than a few
days pass: prices and ids move.

**Checked 2026-09-21** against https://platform.claude.com/docs/en/about-claude/pricing (the
older docs.claude.com path now redirects there).

The three models docs/internal/MASTER_BRIEF.md names for the test run, cheapest first:

| Model | Id used in our config | Input per MTok | Output per MTok | Batch input | Batch output |
|---|---|---|---|---|---|
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | $1 | $5 | $0.50 | $2.50 |
| Claude Sonnet 5 | `claude-sonnet-5` | $2 | $10 | $1 | $5 |
| Claude Opus 5 | `claude-opus-5` | $5 | $25 | $2.50 | $12.50 |

The pricing page lists model names, not API ids. The ids above are the ones in our config. Confirm
them against the models page on the console before the first paid call, which is the one thing
this file cannot do for you.

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
