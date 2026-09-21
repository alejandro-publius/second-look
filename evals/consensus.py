"""Does leaving out low scorers change what a group gets right? docs/analysis_plan.md item 11.

Exploratory, run after lock, reported as description only. The 16 items are split at random into
two halves with two items of each feature in each half (seed 20260920, 200 splits). A person
passes a half with 6 or more of its 8 items correct. For random groups of 5 within an arm (2,000
draws) the group answers each item of the other half by plain majority, once using everyone and
once using only the people who passed the first half. When nobody passed, or the passers tie, the
group falls back to everyone. We report the share of items each version gets right.

Usage: uv run python evals/consensus.py --synthetic [--scenario skill_spread]
"""

from __future__ import annotations

import argparse
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
    N_ITEMS,
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
GROUP_SIZE = 5
N_DRAWS = 2_000
N_SPLITS = 200
HALF_ITEMS = N_ITEMS // 2
PASS_MARK = 6
DEFAULT_SCENARIO = "skill_spread"
VOTE_VALUE = {"yes": 1, "no": -1, "cant_tell": 0}
GOLD_SIGN = {"present": 1, "absent": -1}
ARM_COLOURS = {"untrained": "#2a78d6", "trained": "#eb6834"}
VERSIONS = ("everyone", "passers_only")
VERSION_LABEL = {"everyone": "everyone votes", "passers_only": "only the people who passed"}


def split_items(
    feature_of_item: np.ndarray, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """One random split: half the items of each feature score a person, the other half are voted on.

    Returns the score half and the vote half as sorted item indexes.
    """
    score: list[int] = []
    vote: list[int] = []
    for feature in range(int(feature_of_item.max()) + 1):
        idx = np.flatnonzero(feature_of_item == feature)
        if len(idx) % 2 != 0:
            raise ValueError(f"feature {feature} has {len(idx)} items, which does not halve evenly")
        shuffled = rng.permutation(idx)
        cut = len(idx) // 2
        score.extend(int(i) for i in shuffled[:cut])
        vote.extend(int(i) for i in shuffled[cut:])
    return np.sort(np.array(score, dtype=int)), np.sort(np.array(vote, dtype=int))


def draw_groups(n_people: int, size: int, n_draws: int, rng: np.random.Generator) -> np.ndarray:
    """n_draws rows of `size` people, distinct inside a row."""
    if n_people < size:
        raise ValueError(f"need {size} people for a group, got {n_people}")
    return np.argsort(rng.random((n_draws, n_people)), axis=1)[:, :size]


def decide_items(
    votes: np.ndarray, passed: np.ndarray, gold_sign: np.ndarray
) -> dict[str, np.ndarray]:
    """Plain majority twice over: everyone, then only the passers with a fallback to everyone.

    votes: (draws, people, items) in {-1, 0, 1}. passed: (draws, people) bool.
    A sum of exactly zero is a tie. For the passers it sends that item back to everyone. For
    everyone it stays a wrong answer, because the group did not decide.
    """
    if votes.ndim != 3:
        raise ValueError(f"votes must be (draws, people, items), got shape {votes.shape}")
    everyone_total = votes.sum(axis=1)
    passer_total = (votes * passed[:, :, None]).sum(axis=1)
    has_passer = passed.any(axis=1)
    use_passers = has_passer[:, None] & (passer_total != 0)
    passer_answer = np.where(use_passers, passer_total, everyone_total)
    return {
        "everyone_right": np.sign(everyone_total) == gold_sign,
        "passers_right": np.sign(passer_answer) == gold_sign,
        "fell_back": ~use_passers,
        "has_passer": has_passer,
    }


def build_matrices(kept: pd.DataFrame, responses: pd.DataFrame) -> dict[str, dict[str, np.ndarray]]:
    """Per arm: votes (people by 16) and correct (people by 16), plus the gold and feature maps."""
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
        out[arm] = {
            "votes": votes,
            "correct": (votes == gold_sign[None, :]).astype(int),
            "gold_sign": gold_sign,
            "feature_of_item": feature_of_item,
        }
    return out


def consensus_for_arm(
    mats: dict[str, np.ndarray],
    *,
    n_splits: int = N_SPLITS,
    n_draws: int = N_DRAWS,
    group_size: int = GROUP_SIZE,
    pass_mark: int = PASS_MARK,
    rng: np.random.Generator,
) -> dict[str, Any]:
    """Run every split for one arm and pool the per-draw shares."""
    votes, correct = mats["votes"], mats["correct"]
    gold_sign, feature_of_item = mats["gold_sign"], mats["feature_of_item"]
    n_people = int(votes.shape[0])
    out: dict[str, Any] = {"n_people": n_people, "group_size": group_size, "pass_mark": pass_mark}
    if n_people < group_size:
        out["skipped"] = f"only {n_people} completed sessions, need {group_size}"
        return out
    everyone_shares: list[np.ndarray] = []
    passer_shares: list[np.ndarray] = []
    fell_back = 0
    no_passer = 0
    total_items = 0
    total_groups = 0
    people_passing = 0
    people_seen = 0
    for _ in range(n_splits):
        score_half, vote_half = split_items(feature_of_item, rng)
        passed_person = correct[:, score_half].sum(axis=1) >= pass_mark
        people_passing += int(passed_person.sum())
        people_seen += n_people
        groups = draw_groups(n_people, group_size, n_draws, rng)
        v = votes[:, vote_half][groups]
        p = passed_person[groups]
        decided = decide_items(v, p, gold_sign[vote_half])
        everyone_shares.append(decided["everyone_right"].mean(axis=1))
        passer_shares.append(decided["passers_right"].mean(axis=1))
        fell_back += int(decided["fell_back"].sum())
        total_items += int(decided["fell_back"].size)
        no_passer += int((~decided["has_passer"]).sum())
        total_groups += int(decided["has_passer"].size)
    everyone = np.concatenate(everyone_shares)
    passers = np.concatenate(passer_shares)
    out.update(
        {
            "splits": n_splits,
            "draws_per_split": n_draws,
            "everyone": _summary(everyone),
            "passers_only": _summary(passers),
            "passers_minus_everyone_mean": round(float(passers.mean() - everyone.mean()), 4),
            "share_of_people_passing_a_half": round(people_passing / people_seen, 4),
            "share_of_groups_with_no_passer": round(no_passer / total_groups, 4),
            "share_of_items_sent_back_to_everyone": round(fell_back / total_items, 4),
        }
    )
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
    n_splits: int = N_SPLITS,
    n_draws: int = N_DRAWS,
    group_size: int = GROUP_SIZE,
    seed: int = PLAN_SEED,
) -> dict[str, Any]:
    excl = apply_exclusions(sessions, responses)
    mats = build_matrices(excl.kept, responses)
    rng = np.random.default_rng(seed)
    arms = {
        arm: consensus_for_arm(
            mats[arm], n_splits=n_splits, n_draws=n_draws, group_size=group_size, rng=rng
        )
        for arm in ARMS
    }
    summary: dict[str, float | None] = {}
    for arm in ARMS:
        row = arms[arm]
        skipped = "skipped" in row
        for version in VERSIONS:
            summary[f"{arm}_{version}"] = (
                None if skipped else round(row[version]["mean_share_right"] * 100, 1)
            )
        summary[f"{arm}_passers_minus_everyone"] = (
            None if skipped else round(row["passers_minus_everyone_mean"] * 100, 1)
        )
    return {
        "summary": summary,
        "plan": {
            "item": "docs/analysis_plan.md item 11",
            "splits": n_splits,
            "items_per_half": HALF_ITEMS,
            "items_per_feature_per_half": ITEMS_PER_FEATURE // 2,
            "pass_mark_of_8": PASS_MARK,
            "group_size": group_size,
            "draws_per_split": n_draws,
            "seed": seed,
            "fallback_rule": (
                "when nobody in the group passed, or the passers tie, the group falls back "
                "to everyone; a tie among everyone stays a wrong answer"
            ),
        },
        "arms": arms,
    }


def draw_chart(result: dict[str, Any], path: Path, *, synthetic: bool, title_extra: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 4.8), dpi=120)
    width = 0.32
    for offset, version in zip((-width / 2, width / 2), VERSIONS, strict=True):
        xs: list[float] = []
        means: list[float] = []
        lows: list[float] = []
        highs: list[float] = []
        colours: list[str] = []
        for i, arm in enumerate(ARMS):
            row = result["arms"][arm]
            if "skipped" in row:
                continue
            xs.append(i + offset)
            means.append(row[version]["mean_share_right"])
            lows.append(row[version]["mean_share_right"] - row[version]["p2_5"])
            highs.append(row[version]["p97_5"] - row[version]["mean_share_right"])
            colours.append("#9aa0a6" if version == "everyone" else ARM_COLOURS[arm])
        if not xs:
            continue
        ax.bar(
            xs,
            means,
            width=width,
            color=colours,
            yerr=[lows, highs],
            capsize=4,
            ecolor="#4a4a48",
            label=VERSION_LABEL[version],
        )
    ax.set_xticks(range(len(ARMS)))
    ax.set_xticklabels(list(ARMS))
    ax.set_ylabel("share of the 8 voted items the group gets right")
    ax.set_ylim(0, 1)
    title = chart_title(
        f"groups of {result['plan']['group_size']}, with and without the low scorers{title_extra}",
        synthetic=synthetic,
    )
    ax.set_title(title, loc="left", fontsize=12)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e5e5e2", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(
        frameon=False,
        loc="lower right",
        fontsize=9,
        title="bars: 2.5 to 97.5 percentile over draws",
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
    parser.add_argument("--splits", type=int, default=N_SPLITS)
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
    result.update(run_consensus(sessions, responses, n_splits=args.splits, n_draws=args.draws))
    title_extra = f" ({scenario} scenario)" if scenario else ""
    png = args.out_dir / f"consensus_{stamp_name}.png"
    result["chart_title"] = draw_chart(
        result, png, synthetic=args.synthetic, title_extra=title_extra
    )
    result["outputs"] = {"chart": png.name}
    json_path = write_json(args.out_dir / f"consensus_{stamp_name}.json", result)

    label = f"{result['stamp']} {scenario}" if scenario else result["stamp"]
    for arm in ARMS:
        row = result["arms"][arm]
        if "skipped" in row:
            print(f"{label} {arm}: {row['skipped']}")
            continue
        print(
            f"{label} {arm}: everyone {row['everyone']['mean_share_right']:.3f}, "
            f"passers only {row['passers_only']['mean_share_right']:.3f}, "
            f"difference {row['passers_minus_everyone_mean']:+.3f}"
        )
    print(f"wrote {json_path} and {png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
