"""Consensus with and without scores: docs/analysis_plan.md item 11, word for word.

For group sizes 3, 5 and 7 we draw 2,000 random groups of completed sessions inside each arm,
without replacement inside a group, seed 20260920. Plain vote: Yes +1, No -1, Can't tell 0, the
sign of the sum is the answer. Scored vote: each vote is multiplied by a weight from the other
three items of the same feature: with c of those correct, p = (c + 0.5) / 4 and the weight is
max(0, ln(p / (1 - p))). A sum of exactly zero is a wrong answer for both methods.

Usage: uv run python evals/consensus.py --synthetic [--scenario skill_spread]
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from evals.common import (  # noqa: E402
    ARMS,
    EXPORT_DIR,
    ITEMS_PER_FEATURE,
    PLAN_SEED,
    RESULTS_DIR,
    SYNTHETIC_DIR,
    chart_title,
    load_test_items,
    now_utc,
    parse_utc,
    result_header,
    write_json,
)
from evals.usability_analysis import apply_exclusions, load_export, refusal_reason  # noqa: E402

SCRIPT = "evals/consensus.py"
GROUP_SIZES = (3, 5, 7)
N_DRAWS = 2_000
DEFAULT_SCENARIO = "skill_spread"
VOTE_VALUE = {"yes": 1, "no": -1, "cant_tell": 0}
GOLD_SIGN = {"present": 1, "absent": -1}
ARM_COLOURS = {"untrained": "#2a78d6", "trained": "#eb6834"}
METHOD_STYLE = {"plain": ("-", "o"), "scored": ("--", "s")}


def weight_for_correct(c: int, others: int = ITEMS_PER_FEATURE - 1) -> float:
    """The plan's weight: p = (c + 0.5) / 4, weight = max(0, ln(p / (1 - p))). Never negative."""
    if c < 0 or c > others:
        raise ValueError(f"c must be between 0 and {others}, got {c}")
    p = (c + 0.5) / (others + 1)
    return max(0.0, math.log(p / (1.0 - p)))


WEIGHTS = tuple(weight_for_correct(c) for c in range(ITEMS_PER_FEATURE))


TIE_TOLERANCE = 1e-9


def plain_vote_correct(votes: np.ndarray, gold_sign: np.ndarray) -> np.ndarray:
    """votes: (..., people, items) in {-1, 0, 1}. Returns (..., items) bools. Zero sum is wrong."""
    total = votes.sum(axis=-2)
    return np.sign(total) == gold_sign


def scored_vote_correct(
    votes: np.ndarray, weights: np.ndarray, gold_sign: np.ndarray
) -> np.ndarray:
    """Weighted version of plain_vote_correct. weights must be non-negative and the same shape."""
    if np.any(weights < 0):
        raise ValueError("weights must never be negative")
    total = (votes * weights).sum(axis=-2)
    # A tie counts as a wrong answer (analysis plan item 11). Adding floats in a different order
    # leaves a speck instead of a clean zero, which would read as a decisive vote, so snap it.
    total = np.where(np.abs(total) < TIE_TOLERANCE, 0.0, total)
    return np.sign(total) == gold_sign


def weights_from_other_items(correct: np.ndarray, feature_of_item: np.ndarray) -> np.ndarray:
    """correct: (people, items) 0/1. Weight for each item from the other items of its feature."""
    n_features = int(feature_of_item.max()) + 1
    per_feature = np.stack(
        [correct[:, feature_of_item == f].sum(axis=1) for f in range(n_features)], axis=1
    )
    others = per_feature[:, feature_of_item] - correct
    table = np.asarray(WEIGHTS)
    return table[others.astype(int)]


def build_matrices(kept: pd.DataFrame, responses: pd.DataFrame) -> dict[str, dict[str, np.ndarray]]:
    """Per arm: votes (people by 16), correct (people by 16), weights (people by 16)."""
    items = load_test_items()
    item_ids = [row["id"] for row in items]
    features = sorted({row["feature"] for row in items})
    feature_of_item = np.array([features.index(row["feature"]) for row in items])
    gold_sign = np.array([GOLD_SIGN[row["gold"]] for row in items])
    sub = responses.merge(kept[["session_id", "arm"]], on="session_id", how="inner")
    sub = sub[sub["item_id"].isin(item_ids)]
    out: dict[str, dict[str, np.ndarray]] = {}
    for arm in ARMS:
        g = sub[sub["arm"] == arm]
        vote_table = (
            g.assign(vote=g["answer"].map(VOTE_VALUE).fillna(0).astype(int))
            .pivot_table(
                index="session_id", columns="item_id", values="vote", fill_value=0, aggfunc="first"
            )
            .reindex(columns=item_ids, fill_value=0)
        )
        votes = vote_table.to_numpy(dtype=int)
        correct = (votes == gold_sign[None, :]).astype(int)
        out[arm] = {
            "votes": votes,
            "correct": correct,
            "weights": weights_from_other_items(correct, feature_of_item),
            "gold_sign": gold_sign,
        }
    return out


def draw_groups(n_people: int, size: int, n_draws: int, rng: np.random.Generator) -> np.ndarray:
    """n_draws rows of `size` distinct indices each."""
    return np.stack([rng.choice(n_people, size=size, replace=False) for _ in range(n_draws)])


def consensus_for_arm(
    mats: dict[str, np.ndarray], *, sizes: tuple[int, ...], n_draws: int, rng: np.random.Generator
) -> dict[str, Any]:
    votes, weights, gold_sign = mats["votes"], mats["weights"], mats["gold_sign"]
    n_people = votes.shape[0]
    out: dict[str, Any] = {"n_people": int(n_people), "by_size": {}}
    for size in sizes:
        if n_people < size:
            out["by_size"][str(size)] = {
                "skipped": f"only {n_people} completed sessions, need {size}"
            }
            continue
        groups = draw_groups(n_people, size, n_draws, rng)
        v = votes[groups]  # (draws, size, items)
        w = weights[groups]
        plain = plain_vote_correct(v, gold_sign).mean(axis=1)
        scored = scored_vote_correct(v, w, gold_sign).mean(axis=1)
        out["by_size"][str(size)] = {
            "draws": int(n_draws),
            "plain": _summary(plain),
            "scored": _summary(scored),
            "scored_minus_plain_mean": round(float(scored.mean() - plain.mean()), 4),
        }
    return out


def _summary(shares: np.ndarray) -> dict[str, float]:
    lo, hi = np.percentile(shares, [2.5, 97.5])
    return {
        "mean_share_right": round(float(shares.mean()), 4),
        "p2_5": round(float(lo), 4),
        "p97_5": round(float(hi), 4),
        "sd_over_draws": round(float(shares.std(ddof=1)), 4),
    }


def run_consensus(
    sessions: pd.DataFrame,
    responses: pd.DataFrame,
    *,
    sizes: tuple[int, ...] = GROUP_SIZES,
    n_draws: int = N_DRAWS,
    seed: int = PLAN_SEED,
) -> dict[str, Any]:
    excl = apply_exclusions(sessions, responses)
    mats = build_matrices(excl.kept, responses)
    rng = np.random.default_rng(seed)
    arms = {
        arm: consensus_for_arm(mats[arm], sizes=sizes, n_draws=n_draws, rng=rng) for arm in ARMS
    }
    summary: dict[str, float | None] = {}
    for arm in ARMS:
        for size in sizes:
            row = arms[arm]["by_size"][str(size)]
            for method in ("plain", "scored"):
                key = f"{arm}_{method}_size{size}"
                summary[key] = (
                    None if "skipped" in row else round(row[method]["mean_share_right"] * 100, 1)
                )
            summary[f"{arm}_scored_minus_plain_size{size}"] = (
                None if "skipped" in row else round(row["scored_minus_plain_mean"] * 100, 1)
            )
    return {
        "summary": summary,
        "plan": {
            "item": "docs/analysis_plan.md item 11",
            "group_sizes": list(sizes),
            "draws_per_arm_and_size": n_draws,
            "seed": seed,
            "weights_by_correct_of_other_three": [round(w, 4) for w in WEIGHTS],
            "tie_rule": "a sum of exactly zero counts as wrong for both methods",
        },
        "arms": arms,
    }


def draw_chart(result: dict[str, Any], path: Path, *, synthetic: bool, title_extra: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 4.8), dpi=120)
    sizes = [int(s) for s in result["plan"]["group_sizes"]]
    for arm in ARMS:
        by_size = result["arms"][arm]["by_size"]
        for method, (style, marker) in METHOD_STYLE.items():
            xs = [s for s in sizes if "skipped" not in by_size[str(s)]]
            if not xs:
                continue
            means = [by_size[str(s)][method]["mean_share_right"] for s in xs]
            lows = [by_size[str(s)][method]["p2_5"] for s in xs]
            highs = [by_size[str(s)][method]["p97_5"] for s in xs]
            colour = ARM_COLOURS[arm]
            ax.fill_between(
                xs,
                lows,
                highs,
                color=colour,
                alpha=0.10 if method == "plain" else 0.07,
                linewidth=0,
            )
            ax.plot(
                xs,
                means,
                style,
                color=colour,
                marker=marker,
                markersize=6,
                linewidth=2,
                label=f"{arm}, {method} vote",
            )
    ax.set_xticks(sizes)
    ax.set_xlabel("people in the group")
    ax.set_ylabel("share of the 16 items the group gets right")
    ax.set_ylim(0, 1)
    title = chart_title(f"group answers with and without scores{title_extra}", synthetic=synthetic)
    ax.set_title(title, loc="left", fontsize=12)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e5e5e2", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(
        frameon=False,
        loc="lower right",
        fontsize=9,
        title="bands: 2.5 to 97.5 percentile over draws",
        title_fontsize=8,
    )
    if synthetic:
        fig.text(
            0.5,
            0.5,
            "SYNTHETIC",
            fontsize=64,
            color="#888888",
            alpha=0.18,
            ha="center",
            va="center",
            weight="bold",
            rotation=20,
        )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return title


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument(
        "--scenario", default=None, help=f"synthetic scenario (default {DEFAULT_SCENARIO})"
    )
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--now", default=None)
    parser.add_argument("--repo", type=Path, default=None)
    parser.add_argument("--draws", type=int, default=N_DRAWS)
    args = parser.parse_args(argv)

    now = parse_utc(args.now) if args.now else now_utc()
    repo = args.repo if args.repo is not None else RESULTS_DIR.parent
    if args.synthetic:
        if args.scenario:
            scenario = args.scenario
        elif args.input is not None:
            scenario = args.input.name
        else:
            scenario = DEFAULT_SCENARIO
        input_dir = args.input if args.input is not None else SYNTHETIC_DIR / scenario
        stamp_name = "synthetic" if args.scenario is None else f"synthetic_{scenario}"
    else:
        if args.scenario:
            print("The --scenario option only makes sense with --synthetic.")
            return 2
        reason = refusal_reason(now, repo)
        if reason:
            print(reason)
            return 3
        scenario = None
        input_dir = args.input if args.input is not None else EXPORT_DIR
        stamp_name = now.strftime("%Y%m%d")
    if not (input_dir / "sessions.csv").exists():
        print(
            f"No sessions.csv in {input_dir}. "
            "Run evals/make_synthetic_sessions.py first for synthetic data."
        )
        return 4

    sessions, responses = load_export(input_dir)
    result = result_header(SCRIPT, synthetic=args.synthetic, stamp=stamp_name, when=now)
    if args.synthetic:
        result["scenario"] = scenario
    result["input"] = str(input_dir)
    result.update(run_consensus(sessions, responses, n_draws=args.draws))
    title_extra = f" ({scenario} scenario)" if scenario else ""
    png = args.out_dir / f"consensus_{stamp_name}.png"
    result["chart_title"] = draw_chart(
        result, png, synthetic=args.synthetic, title_extra=title_extra
    )
    result["outputs"] = {"chart": png.name}
    json_path = write_json(args.out_dir / f"consensus_{stamp_name}.json", result)

    label = f"{result['stamp']} {scenario}" if scenario else result["stamp"]
    for arm in ARMS:
        parts = []
        for size in GROUP_SIZES:
            row = result["arms"][arm]["by_size"][str(size)]
            if "skipped" in row:
                parts.append(f"size {size} skipped")
            else:
                plain = row["plain"]["mean_share_right"]
                scored = row["scored"]["mean_share_right"]
                parts.append(f"size {size}: plain {plain:.3f}, scored {scored:.3f}")
        print(f"{label} {arm}: " + "; ".join(parts))
    print(f"wrote {json_path} and {png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
