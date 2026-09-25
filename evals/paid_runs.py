"""The paid model runs, and the facts about each one that are not in its own results file.

evals/extract_raw.py reads this list to write the fixtures in evals/fixtures/raw/, and
evals/reproduce.py reads it to regrade them. A results file stamped real that is not listed here
makes make reproduce fail, so a new paid run cannot be committed without its raw responses.

What each run needs that its results file does not say:

- billing: the first sweep went through the Batch API at half price. Every later run made direct
  calls at the full price (EVALS_SYNC=1, commit 88d4a29), because a batch waited hours in the queue.
- prices: Opus 5 was dropped for Opus 5.5 on Sep 24 (commit 8cecc38), and its price went with it
  from evals/pricing.yaml. The runs before that are billed at the prices the file held then.
"""

from __future__ import annotations

from dataclasses import dataclass

from evals.model_sweep import ModelPrice, Pricing

# Dollars per million tokens, input then output. From evals/pricing.yaml at commit 88d4a29, the
# file the Sep 24 runs before 05:00 UTC read, and at 8cecc38, the file every later run read.
PRICES_BEFORE_OPUS_5_5: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-opus-5": (5.00, 25.00),
}
PRICES_WITH_OPUS_5_5: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-fable-5-1": (10.00, 50.00),
}
BATCH_MULTIPLIER = 0.5


@dataclass(frozen=True)
class PaidRun:
    kind: str  # model_sweep, benchmark or footage: the script and the cost log's purpose
    stamp: str
    billing: str  # "batch" or "direct"
    prices: dict[str, tuple[float, float]]
    prices_from: str

    @property
    def results_name(self) -> str:
        return f"{self.kind}_{self.stamp}.json"

    @property
    def fixture_name(self) -> str:
        return f"{self.kind}_{self.stamp}.jsonl"

    @property
    def batch(self) -> bool:
        return self.billing == "batch"

    def pricing(self) -> Pricing:
        """The price table this run was billed at, as the object the run itself used."""
        return pricing_from(self.prices)


def pricing_from(prices: dict[str, tuple[float, float]]) -> Pricing:
    return Pricing(
        models={
            model: ModelPrice(input_per_million=i, output_per_million=o, source_checked=True)
            for model, (i, o) in prices.items()
        },
        batch_multiplier=BATCH_MULTIPLIER,
        batch_checked=True,
    )


_BEFORE = "evals/pricing.yaml at commit 88d4a29"
_AFTER = "evals/pricing.yaml at commit 8cecc38, the same as today"

PAID_RUNS: tuple[PaidRun, ...] = (
    PaidRun("model_sweep", "20260924T030451Z", "batch", PRICES_BEFORE_OPUS_5_5, _BEFORE),
    PaidRun("model_sweep", "20260924T031128Z", "direct", PRICES_BEFORE_OPUS_5_5, _BEFORE),
    PaidRun("benchmark", "20260924T031225Z", "direct", PRICES_BEFORE_OPUS_5_5, _BEFORE),
    PaidRun("footage", "20260924T032230Z", "direct", PRICES_BEFORE_OPUS_5_5, _BEFORE),
    PaidRun("model_sweep", "20260924T054756Z", "direct", PRICES_WITH_OPUS_5_5, _AFTER),
    PaidRun("benchmark", "20260924T054939Z", "direct", PRICES_WITH_OPUS_5_5, _AFTER),
    PaidRun("footage", "20260924T060539Z", "direct", PRICES_WITH_OPUS_5_5, _AFTER),
    # Part 2's eight items (UPDATE_31, evals/assist_flags.py --collect), through the Batch API.
    PaidRun("assist_answers", "20260925T230654Z", "batch", PRICES_WITH_OPUS_5_5, _AFTER),
)

# The one real call in the cost log that belongs to no results file: a single smoke call on
# Sep 24 before the second sweep, to see the answer tool come back. Direct, at the full price.
SMOKE_PURPOSE = "smoke"
