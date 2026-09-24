"""The pre-registered analysis of the usability test: docs/analysis_plan.md items 4 to 7 and 9.

Without --synthetic this script refuses to run before the data lock, without the git tag
prereg-v1 on the pinned commit, when docs/analysis_plan.md differs from the tagged and pinned
version, or on a folder marked SYNTHETIC.txt. It always reads the real clock and this repository.
With --synthetic it runs only on a folder that evals/make_synthetic_sessions.py wrote, never on
the real export, and stamps every output SYNTHETIC.

Usage:
  uv run python evals/usability_analysis.py --synthetic [--scenario real_gain]
  uv run python evals/usability_analysis.py [--input data/export]
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from core.lock import DATA_LOCK_UTC  # noqa: E402
from evals.common import (  # noqa: E402
    ARMS,
    EXPORT_DIR,
    N_ITEMS,
    PLAN_SEED,
    RESPONSE_COLUMNS,
    RESULTS_DIR,
    SESSION_COLUMNS,
    SYNTHETIC_DIR,
    chart_title,
    iso_utc,
    load_test_items,
    now_utc,
    parse_utc,
    result_header,
    round_or_none,
    write_json,
)

SCRIPT = "evals/usability_analysis.py"
REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_RELATIVE = "docs/analysis_plan.md"
PLAN_TAG = "prereg-v1"
# The commit the tag points at and the SHA-256 of the tagged plan, as docs/notes/plan_hash.md
# records them. Another repository, a look-alike ref or a moved tag cannot match both.
PLAN_COMMIT = "ca0a83251ef38d85f1e8d5d268df858e8819faff"
PLAN_SHA256 = "86da527e30c0a8e8492b6fb22c3056be1a2ad3087b5ca8c6f4a0a1bd58aed9cf"
SYNTHETIC_MARKER = "SYNTHETIC.txt"
N_BOOT = 10_000
N_PERM = 10_000
ALPHA = 0.05
MIN_COMPLETED_PER_ARM = 20
MIN_TEST_SECONDS = 40.0
DEFAULT_SCENARIO = "real_gain"

ARM_COLOURS = {"untrained": "#2a78d6", "trained": "#eb6834"}

TRUE_WORDS = {"true", "1", "yes", "t", "y"}


# ---------------------------------------------------------------------------
# Refusal checks (hard rule 13)
# ---------------------------------------------------------------------------


class Refused(RuntimeError):
    """run() raises this with the sentence from guard(), so an import cannot skip the checks."""


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    # GIT_DIR, GIT_WORK_TREE, GIT_INDEX_FILE and the other GIT_ variables would let another
    # repository answer for this one, and replace refs could swap objects. Ignore them all.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(
        ["git", "--no-replace-objects", "-C", str(repo), *args],
        capture_output=True,
        check=False,
        env=env,
    )


def tag_exists(repo: Path, tag: str = PLAN_TAG) -> bool:
    done = _git(repo, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}")
    return done.returncode == 0


def tagged_commit(repo: Path, tag: str = PLAN_TAG) -> str | None:
    """The commit the tag points at. The full ref name means no other ref can shadow the tag."""
    done = _git(repo, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}")
    if done.returncode != 0:
        return None
    return done.stdout.decode("ascii").strip()


def tagged_plan(repo: Path, tag: str = PLAN_TAG, relative: str = PLAN_RELATIVE) -> bytes | None:
    done = _git(repo, "show", f"refs/tags/{tag}:{relative}")
    if done.returncode != 0:
        return None
    return done.stdout


def plan_sha256() -> str:
    """SHA-256 of the plan in this repository, recorded in every results JSON."""
    return hashlib.sha256((REPO_ROOT / PLAN_RELATIVE).read_bytes()).hexdigest()


def refusal_reason(now: datetime, repo: Path) -> str | None:
    """A plain sentence saying why real data cannot be analysed now, or None when it can."""
    if now < DATA_LOCK_UTC:
        return (
            f"Refusing to run: the data lock is {iso_utc(DATA_LOCK_UTC)} and it is now "
            f"{iso_utc(now)}, so real outcomes are not computed yet."
        )
    if not tag_exists(repo):
        return (
            f"Refusing to run: the git tag {PLAN_TAG} does not exist in {repo}, "
            "so the analysis plan is not registered."
        )
    tagged = tagged_plan(repo)
    working = repo / PLAN_RELATIVE
    if tagged is None or not working.exists():
        return (
            f"Refusing to run: {PLAN_RELATIVE} is missing from the tag {PLAN_TAG} "
            "or from the working tree."
        )
    if tagged != working.read_bytes():
        return (
            f"Refusing to run: {PLAN_RELATIVE} differs from the version tagged {PLAN_TAG}. "
            "Changes after the tag belong in docs/deviations.md."
        )
    if hashlib.sha256(tagged).hexdigest() != PLAN_SHA256:
        return (
            f"Refusing to run: the tagged {PLAN_RELATIVE} does not have the SHA-256 pinned in "
            f"{SCRIPT} and docs/notes/plan_hash.md, so it is not the registered plan."
        )
    if tagged_commit(repo) != PLAN_COMMIT:
        return (
            f"Refusing to run: the tag {PLAN_TAG} does not point at commit {PLAN_COMMIT[:7]}, "
            "the commit docs/notes/plan_hash.md records."
        )
    return None


def guard(input_dir: Path, *, synthetic: bool) -> str | None:
    """Why this run must not go ahead, or None. Both analysis scripts call it (hard rule 13).

    A synthetic run reads only a folder that evals/make_synthetic_sessions.py marked with
    SYNTHETIC.txt, never the real export. A real run never reads a marked folder, and it checks
    the real clock and this repository: no option or environment variable stands in for either.
    """
    marked = (input_dir / SYNTHETIC_MARKER).exists()
    if synthetic:
        if not marked or input_dir.resolve() == EXPORT_DIR.resolve():
            return (
                "Refusing to run: with --synthetic the input must be a folder that "
                f"evals/make_synthetic_sessions.py wrote, with {SYNTHETIC_MARKER} in it, and "
                f"never the real export. {input_dir} is not one."
            )
        return None
    if marked:
        return (
            f"Refusing to run: {input_dir} holds {SYNTHETIC_MARKER}, so it is generated data "
            "and not the real export. Add --synthetic to analyse it."
        )
    return refusal_reason(now_utc(), REPO_ROOT)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _as_bool(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.lower().isin(TRUE_WORDS)


def _as_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _as_utc(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.strip().replace("", None)
    return pd.to_datetime(text, utc=True, errors="coerce", format="ISO8601")


def tidy_sessions(sessions: pd.DataFrame) -> pd.DataFrame:
    """Coerce the export columns to typed columns. Missing columns are an error."""
    missing = [c for c in SESSION_COLUMNS if c not in sessions.columns]
    if missing:
        raise ValueError(f"sessions.csv is missing columns: {', '.join(missing)}")
    out = sessions.copy()
    out["session_id"] = out["session_id"].astype(str)
    out["arm"] = out["arm"].astype(str)
    for col in ("is_test", "post_lock", "hidden_field_filled"):
        out[col] = _as_bool(out[col])
    out["test_seconds"] = _as_float(out["test_seconds"])
    out["lesson_seconds_total"] = _as_float(out["lesson_seconds_total"])
    out["started_at_utc"] = _as_utc(out["started_at_utc"])
    out["completed_at_utc"] = _as_utc(out["completed_at_utc"])
    out["client_token_hash"] = out["client_token_hash"].fillna("").astype(str).str.strip()
    out["prior_experience"] = out["prior_experience"].fillna("").astype(str).str.strip().str.lower()
    for col in ("source_label", "ua_class", "warmup_choice"):
        out[col] = out[col].fillna("").astype(str).str.strip()
    return out


def tidy_responses(responses: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in RESPONSE_COLUMNS if c not in responses.columns]
    if missing:
        raise ValueError(f"responses.csv is missing columns: {', '.join(missing)}")
    out = responses.copy()
    out["session_id"] = out["session_id"].astype(str)
    out["answer"] = out["answer"].astype(str).str.strip().str.lower()
    out["gold"] = out["gold"].astype(str).str.strip().str.lower()
    # Correctness is recomputed from answer and gold; the export's own column is cross-checked.
    out["correct_export"] = _as_float(out["correct"]).fillna(0).astype(int)
    out["correct"] = (
        ((out["answer"] == "yes") & (out["gold"] == "present"))
        | ((out["answer"] == "no") & (out["gold"] == "absent"))
    ).astype(int)
    return out


def load_export(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    sessions = pd.read_csv(path / "sessions.csv", dtype=str, keep_default_na=False)
    responses = pd.read_csv(path / "responses.csv", dtype=str, keep_default_na=False)
    return tidy_sessions(sessions), tidy_responses(responses)


# ---------------------------------------------------------------------------
# Exclusions (plan item 5, in the plan's order)
# ---------------------------------------------------------------------------


@dataclass
class ExclusionStep:
    order: int
    rule: str
    removed: int
    remaining: int
    note: str = ""


@dataclass
class Exclusions:
    kept: pd.DataFrame
    steps: list[ExclusionStep] = field(default_factory=list)
    counts: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "steps": [step.__dict__ for step in self.steps],
            "counts": self.counts,
        }


def _by_arm(frame: pd.DataFrame) -> dict[str, int]:
    counts = frame["arm"].value_counts()
    return {arm: int(counts.get(arm, 0)) for arm in ARMS}


def apply_exclusions(
    sessions: pd.DataFrame,
    responses: pd.DataFrame,
    *,
    launch_utc: datetime | None = None,
    include_partial: bool = False,
) -> Exclusions:
    """Apply the plan's exclusions in order and count what each removes.

    include_partial=True is the sensitivity check: people who answered some items stay in and
    their unanswered items count as wrong. The first rule then removes only sessions with no
    answers at all.
    """
    answered = responses.groupby("session_id").size()
    frame = sessions.copy()
    frame["n_answered"] = frame["session_id"].map(answered).fillna(0).astype(int)
    steps: list[ExclusionStep] = []

    # Scope: sessions stored after the data lock are never analysed (plan item 7).
    lock = pd.Timestamp(DATA_LOCK_UTC)
    after_lock = frame["post_lock"] | (frame["started_at_utc"] >= lock)
    frame = frame[~after_lock]
    steps.append(
        ExclusionStep(
            0,
            "started at or after the data lock (never analysed, plan item 7)",
            int(after_lock.sum()),
            len(frame),
        )
    )
    counts = {
        "randomized": _by_arm(frame),
        "started": _by_arm(frame[frame["n_answered"] > 0]),
        "completed": _by_arm(
            frame[(frame["n_answered"] >= N_ITEMS) & frame["completed_at_utc"].notna()]
        ),
    }

    # 1. Did not finish all 16 items.
    if include_partial:
        drop = frame["n_answered"] == 0
        rule = "answered no items at all (sensitivity run keeps partial completers)"
    else:
        drop = (frame["n_answered"] < N_ITEMS) | frame["completed_at_utc"].isna()
        rule = "did not finish all 16 items"
    frame = frame[~drop]
    steps.append(ExclusionStep(1, rule, int(drop.sum()), len(frame)))

    # 2. Test finished in under 40 seconds.
    drop = frame["test_seconds"].notna() & (frame["test_seconds"] < MIN_TEST_SECONDS)
    frame = frame[~drop]
    steps.append(ExclusionStep(2, "test finished in under 40 seconds", int(drop.sum()), len(frame)))

    # 3. Repeat visits from the same browser token: only the first completed session counts.
    order_time = frame["completed_at_utc"].fillna(frame["started_at_utc"])
    ordered = frame.assign(_t=order_time).sort_values(["_t", "session_id"], kind="mergesort")
    has_token = ordered["client_token_hash"] != ""
    dup = has_token & ordered.duplicated(subset=["client_token_hash"], keep="first")
    frame = ordered[~dup].drop(columns="_t")
    steps.append(
        ExclusionStep(
            3,
            "repeat visit from the same browser token (only the first completed session counts)",
            int(dup.sum()),
            len(frame),
        )
    )

    # 4. Flagged as QA.
    drop = frame["is_test"]
    frame = frame[~drop]
    steps.append(ExclusionStep(4, "flagged as QA (is_test)", int(drop.sum()), len(frame)))

    # 5. Filled the hidden form field.
    drop = frame["hidden_field_filled"]
    frame = frame[~drop]
    steps.append(ExclusionStep(5, "filled the hidden form field", int(drop.sum()), len(frame)))

    # 6. Dry runs before launch. The table is wiped at launch, so this is normally zero.
    if launch_utc is not None:
        drop = frame["started_at_utc"] < pd.Timestamp(launch_utc)
        frame = frame[~drop]
        note = f"launch at {iso_utc(launch_utc)}"
        removed = int(drop.sum())
    else:
        note = "no launch time given; the table was wiped at launch, so nothing to remove here"
        removed = 0
    steps.append(ExclusionStep(6, "dry run before launch", removed, len(frame), note))

    counts["analysed"] = _by_arm(frame)
    # Flat README-facing keys. completed_<arm> is the number of completed sessions kept after
    # the exclusions, the n behind the estimate. completed.<arm> above is before the exclusions.
    flat: dict[str, Any] = {}
    for key in ("randomized", "started", "analysed"):
        for arm in ARMS:
            flat[f"{key}_{arm}"] = counts[key][arm]
    for arm in ARMS:
        flat[f"completed_{arm}"] = counts["analysed"][arm]
        flat[f"completed_before_exclusions_{arm}"] = counts["completed"][arm]
    flat["note"] = (
        "completed_<arm> counts completed sessions kept after the exclusions; "
        "completed.<arm> counts every session that finished all 16 items"
    )
    merged: dict[str, Any] = {**counts, **flat}
    return Exclusions(kept=frame.reset_index(drop=True), steps=steps, counts=merged)


# ---------------------------------------------------------------------------
# Scores and the primary estimate (plan items 4 and 6)
# ---------------------------------------------------------------------------


def participant_scores(kept: pd.DataFrame, responses: pd.DataFrame) -> pd.DataFrame:
    """One row per kept session: arm, items right, accuracy. Missing items count as wrong."""
    sub = responses[responses["session_id"].isin(kept["session_id"])]
    right = sub.groupby("session_id")["correct"].sum()
    out = kept[["session_id", "arm", "ua_class", "prior_experience", "source_label"]].copy()
    out["correct"] = out["session_id"].map(right).fillna(0).astype(int)
    out["accuracy"] = out["correct"] / N_ITEMS
    return out


def hedges_g(a: np.ndarray, b: np.ndarray) -> float | None:
    """Hedges g for mean(a) minus mean(b) with the small-sample correction."""
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return None
    pooled = ((n1 - 1) * a.var(ddof=1) + (n2 - 1) * b.var(ddof=1)) / (n1 + n2 - 2)
    if pooled <= 0:
        return None
    j = 1.0 - 3.0 / (4.0 * (n1 + n2) - 9.0)
    return float(j * (a.mean() - b.mean()) / np.sqrt(pooled))


def bootstrap_difference(
    trained: np.ndarray, untrained: np.ndarray, *, n_boot: int, rng: np.random.Generator
) -> np.ndarray:
    """Percentile bootstrap of mean(trained) minus mean(untrained), resampling inside each arm."""
    idx_t = rng.integers(0, len(trained), size=(n_boot, len(trained)))
    idx_u = rng.integers(0, len(untrained), size=(n_boot, len(untrained)))
    return trained[idx_t].mean(axis=1) - untrained[idx_u].mean(axis=1)


def permutation_p(
    trained: np.ndarray, untrained: np.ndarray, *, n_perm: int, rng: np.random.Generator
) -> float:
    """Two-sided permutation test on the difference in means, Monte Carlo p with the +1 rule."""
    observed = trained.mean() - untrained.mean()
    pooled = np.concatenate([trained, untrained])
    n_t = len(trained)
    shuffled = rng.permuted(np.broadcast_to(pooled, (n_perm, len(pooled))).copy(), axis=1)
    diffs = shuffled[:, :n_t].mean(axis=1) - shuffled[:, n_t:].mean(axis=1)
    hits = int(np.sum(np.abs(diffs) >= abs(observed) - 1e-12))
    return (hits + 1) / (n_perm + 1)


def primary_estimate(
    trained: np.ndarray,
    untrained: np.ndarray,
    *,
    n_boot: int = N_BOOT,
    n_perm: int = N_PERM,
    seed: int = PLAN_SEED,
) -> dict[str, Any]:
    """Plan item 6: estimate, bootstrap interval, permutation test, Hedges g."""
    trained = np.asarray(trained, dtype=float)
    untrained = np.asarray(untrained, dtype=float)
    n_t, n_u = len(trained), len(untrained)
    out: dict[str, Any] = {
        "n_trained": n_t,
        "n_untrained": n_u,
        "mean_trained": round_or_none(trained.mean()) if n_t else None,
        "mean_untrained": round_or_none(untrained.mean()) if n_u else None,
    }
    if n_t == 0 or n_u == 0:
        out.update(
            {
                "untrained_mean": None,
                "trained_mean": None,
                "difference": None,
                "ci_low": None,
                "ci_high": None,
                "difference_points": None,
                "ci95_points": None,
                "permutation_p": None,
                "rejects_at_alpha_05": None,
                "hedges_g": None,
                "status": "not computed: an arm is empty",
            }
        )
        return out
    diff = float(trained.mean() - untrained.mean())
    boot = bootstrap_difference(trained, untrained, n_boot=n_boot, rng=np.random.default_rng(seed))
    lo, hi = np.percentile(boot, [2.5, 97.5])
    p = permutation_p(trained, untrained, n_perm=n_perm, rng=np.random.default_rng(seed))
    enough = min(n_t, n_u) >= MIN_COMPLETED_PER_ARM
    out.update(
        {
            # README-facing keys: percentages of the 16 items, one decimal.
            "untrained_mean": round(float(untrained.mean()) * 100, 1),
            "trained_mean": round(float(trained.mean()) * 100, 1),
            "difference": round(diff * 100, 1),
            "ci_low": round(float(lo) * 100, 1),
            "ci_high": round(float(hi) * 100, 1),
            "difference_points": round(diff * 100, 2),
            "ci95_points": [round(float(lo) * 100, 2), round(float(hi) * 100, 2)],
            "difference_share": round_or_none(diff),
            "ci95_share": [round_or_none(lo), round_or_none(hi)],
            "permutation_p": round(p, 4),
            "rejects_at_alpha_05": bool(p < ALPHA),
            "hedges_g": round_or_none(hedges_g(trained, untrained)),
            "bootstrap_resamples": n_boot,
            "permutations": n_perm,
            "seed": seed,
            "status": "confirmatory" if enough else "descriptive",
            "status_note": (
                "at least 20 completed sessions in each arm, "
                "so the plan's one confirmatory test applies"
                if enough
                else "fewer than 20 completed sessions in an arm, "
                "so this is a description, not a test"
            ),
        }
    )
    return out


def _arms(scores: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    trained = scores.loc[scores["arm"] == "trained", "accuracy"].to_numpy(dtype=float)
    untrained = scores.loc[scores["arm"] == "untrained", "accuracy"].to_numpy(dtype=float)
    return trained, untrained


# ---------------------------------------------------------------------------
# Descriptive outcomes (plan item 4)
# ---------------------------------------------------------------------------


def _share(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def per_feature(kept: pd.DataFrame, responses: pd.DataFrame) -> dict[str, Any]:
    """Accuracy, hit rate and false-alarm rate per feature and arm. Can't tell is never a Yes."""
    sub = responses.merge(kept[["session_id", "arm"]], on="session_id", how="inner")
    out: dict[str, Any] = {}
    for feature, group in sub.groupby("feature", sort=True):
        row: dict[str, Any] = {}
        for arm in ARMS:
            g = group[group["arm"] == arm]
            present = g[g["gold"] == "present"]
            absent = g[g["gold"] == "absent"]
            row[arm] = {
                "n_answers": int(len(g)),
                "accuracy": _share(int(g["correct"].sum()), len(g)),
                "hit_rate": _share(int((present["answer"] == "yes").sum()), len(present)),
                "false_alarm_rate": _share(int((absent["answer"] == "yes").sum()), len(absent)),
                "cant_tell_share": _share(int((g["answer"] == "cant_tell").sum()), len(g)),
            }
        out[str(feature)] = row
    return out


def per_item(kept: pd.DataFrame, responses: pd.DataFrame) -> dict[str, Any]:
    """Accuracy per test item and arm, the input to pick_examples.py."""
    sub = responses.merge(kept[["session_id", "arm"]], on="session_id", how="inner")
    items = {row["id"]: row for row in load_test_items()}
    out: dict[str, Any] = {}
    for item_id in sorted(items):
        g = sub[sub["item_id"] == item_id]
        entry: dict[str, Any] = {
            "feature": items[item_id]["feature"],
            "gold": items[item_id]["gold"],
            "photo_id": items[item_id]["photo_id"],
        }
        for arm in ARMS:
            ga = g[g["arm"] == arm]
            entry[arm] = _share(int(ga["correct"].sum()), len(ga))
            entry[f"n_{arm}"] = int(len(ga))
        out[item_id] = entry
    return out


def cant_tell_share(kept: pd.DataFrame, responses: pd.DataFrame) -> dict[str, float | None]:
    sub = responses.merge(kept[["session_id", "arm"]], on="session_id", how="inner")
    return {
        arm: _share(
            int((sub.loc[sub["arm"] == arm, "answer"] == "cant_tell").sum()),
            int((sub["arm"] == arm).sum()),
        )
        for arm in ARMS
    }


def yes_share(kept: pd.DataFrame, responses: pd.DataFrame) -> dict[str, float | None]:
    sub = responses.merge(kept[["session_id", "arm"]], on="session_id", how="inner")
    return {
        arm: _share(
            int((sub.loc[sub["arm"] == arm, "answer"] == "yes").sum()),
            int((sub["arm"] == arm).sum()),
        )
        for arm in ARMS
    }


def median_times(kept: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {"test_seconds": {}, "lesson_seconds": {}}
    for arm in ARMS:
        g = kept[kept["arm"] == arm]
        test = g["test_seconds"].dropna()
        lesson = g["lesson_seconds_total"].dropna()
        lesson = lesson[lesson > 0]
        out["test_seconds"][arm] = {
            "median": round_or_none(float(test.median()), 1) if len(test) else None,
            "n": int(len(test)),
        }
        out["lesson_seconds"][arm] = {
            "median": round_or_none(float(lesson.median()), 1) if len(lesson) else None,
            "n": int(len(lesson)),
            "note": "lesson before the test"
            if arm == "trained"
            else "lesson offered after the test; only people who opened it are counted",
        }
    return out


def _group_accuracy(scores: pd.DataFrame, column: str, labels: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    values = scores[column].map(
        lambda v: labels.get(str(v), str(v)) if str(v) else labels.get("", "")
    )
    for value in sorted(values.unique()):
        row: dict[str, Any] = {}
        for arm in ARMS:
            g = scores[(values == value) & (scores["arm"] == arm)]
            row[arm] = {
                "n": int(len(g)),
                "mean_accuracy": round_or_none(float(g["accuracy"].mean())) if len(g) else None,
            }
        out[str(value)] = row
    return out


def by_source(kept: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Completed sessions by source label and arm. Never used in the confirmatory test."""
    out: dict[str, dict[str, int]] = {}
    labels = kept["source_label"].replace("", "unknown")
    for value in sorted(labels.unique()):
        out[str(value)] = {
            arm: int(((labels == value) & (kept["arm"] == arm)).sum()) for arm in ARMS
        }
    return out


def warmup_shares(kept: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {}
    choices = kept["warmup_choice"].replace("", "no_choice")
    for value in sorted(choices.unique()):
        picked = choices == value
        out[str(value)] = {
            "share": _share(int(picked.sum()), len(kept)),
            "n": int(picked.sum()),
            **{
                arm: _share(
                    int((picked & (kept["arm"] == arm)).sum()), int((kept["arm"] == arm).sum())
                )
                for arm in ARMS
            },
        }
    return out


# ---------------------------------------------------------------------------
# Whole analysis
# ---------------------------------------------------------------------------


def analyse(
    sessions: pd.DataFrame,
    responses: pd.DataFrame,
    *,
    n_boot: int = N_BOOT,
    n_perm: int = N_PERM,
    seed: int = PLAN_SEED,
    launch_utc: datetime | None = None,
) -> dict[str, Any]:
    """Everything the plan asks for, as one JSON-ready dictionary."""
    excl = apply_exclusions(sessions, responses, launch_utc=launch_utc)
    scores = participant_scores(excl.kept, responses)
    trained, untrained = _arms(scores)
    primary = primary_estimate(trained, untrained, n_boot=n_boot, n_perm=n_perm, seed=seed)

    # Sensitivity 1: partial completers stay in, unanswered items scored wrong.
    excl_partial = apply_exclusions(
        sessions, responses, launch_utc=launch_utc, include_partial=True
    )
    scores_partial = participant_scores(excl_partial.kept, responses)
    t_p, u_p = _arms(scores_partial)
    partial = primary_estimate(t_p, u_p, n_boot=n_boot, n_perm=n_perm, seed=seed)
    partial["exclusions"] = excl_partial.as_dict()["steps"]

    # Sensitivity 2: people who report prior stream assessment are left out.
    no_prior = scores[scores["prior_experience"] != "yes"]
    t_n, u_n = _arms(no_prior)
    without_prior = primary_estimate(t_n, u_n, n_boot=n_boot, n_perm=n_perm, seed=seed)
    without_prior["removed_for_prior_experience"] = int((scores["prior_experience"] == "yes").sum())

    sub = responses[responses["session_id"].isin(excl.kept["session_id"])]
    mismatches = int((sub["correct"] != sub["correct_export"]).sum())

    distribution = {
        arm: [
            int(v)
            for v in np.bincount(
                scores.loc[scores["arm"] == arm, "correct"].to_numpy(dtype=int),
                minlength=N_ITEMS + 1,
            )
        ]
        for arm in ARMS
    }

    return {
        "plan": {
            "items": "docs/analysis_plan.md items 4 to 7 and 9",
            "seed": seed,
            "bootstrap_resamples": n_boot,
            "permutations": n_perm,
            "alpha": ALPHA,
            "min_completed_per_arm": MIN_COMPLETED_PER_ARM,
            "min_test_seconds": MIN_TEST_SECONDS,
            "data_lock_utc": iso_utc(DATA_LOCK_UTC),
        },
        "counts": excl.counts,
        "exclusions": excl.as_dict()["steps"],
        "primary": primary,
        "score_distribution": {"bins": "items right, 0 to 16", **distribution},
        "per_feature": per_feature(excl.kept, responses),
        "per_item": per_item(excl.kept, responses),
        "cant_tell_share": cant_tell_share(excl.kept, responses),
        "yes_share": yes_share(excl.kept, responses),
        "median_times": median_times(excl.kept),
        "by_source": by_source(excl.kept),
        "by_device": _group_accuracy(scores, "ua_class", {"": "unknown"}),
        "by_prior_experience": _group_accuracy(
            scores, "prior_experience", {"": "not_answered", "yes": "yes", "no": "no"}
        ),
        "warmup": warmup_shares(excl.kept),
        "sensitivity": {
            "partial_completers_scored_wrong": partial,
            "without_prior_experience": without_prior,
        },
        "data_quality": {
            "correct_column_mismatches": mismatches,
            "note": (
                "correctness is recomputed from answer and gold; the export column is only checked"
            ),
        },
    }


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


def _fmt(value: Any, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _ci_text(ci: Any) -> str:
    return f"{_fmt(ci[0])} to {_fmt(ci[1])}" if ci else "n/a"


def markdown_report(result: dict[str, Any], *, synthetic: bool, title_extra: str) -> str:
    stamp = result["stamp"]
    lines: list[str] = []
    head = "SYNTHETIC results, not from people" if synthetic else "Usability test results"
    lines.append(f"# {head}{title_extra}")
    lines.append("")
    lines.append(f"Stamp: {stamp}. Generated {result['generated_at_utc']} by {result['script']}.")
    lines.append("")
    p = result["primary"]
    lines.append("## Primary estimate (plan item 6)")
    lines.append("")
    lines.append("| Quantity | Value |")
    lines.append("|---|---|")
    lines.append(f"| Status | {p['status']} |")
    lines.append(f"| Completed and kept, trained | {p['n_trained']} |")
    lines.append(f"| Completed and kept, untrained | {p['n_untrained']} |")
    lines.append(f"| Mean accuracy, trained | {_fmt(p['mean_trained'], 3)} |")
    lines.append(f"| Mean accuracy, untrained | {_fmt(p['mean_untrained'], 3)} |")
    lines.append(
        f"| Difference in points (trained minus untrained) | {_fmt(p.get('difference_points'))} |"
    )
    lines.append(f"| 95 percent bootstrap interval, points | {_ci_text(p.get('ci95_points'))} |")
    lines.append(f"| Permutation p (two-sided) | {_fmt(p.get('permutation_p'), 4)} |")
    lines.append(f"| Hedges g | {_fmt(p.get('hedges_g'), 3)} |")
    lines.append("")
    lines.append("## Sessions and exclusions (plan item 5)")
    lines.append("")
    lines.append("| Count | Untrained | Trained |")
    lines.append("|---|---|---|")
    for key in ("randomized", "started", "completed", "analysed"):
        row = result["counts"][key]
        lines.append(f"| {key} | {row['untrained']} | {row['trained']} |")
    lines.append("")
    lines.append("| Order | Rule | Removed | Remaining |")
    lines.append("|---|---|---|---|")
    for step in result["exclusions"]:
        lines.append(
            f"| {step['order']} | {step['rule']} | {step['removed']} | {step['remaining']} |"
        )
    lines.append("")
    lines.append("## Per feature (plan item 4)")
    lines.append("")
    lines.append("| Feature | Arm | Accuracy | Hit rate | False alarm rate | Can't tell |")
    lines.append("|---|---|---|---|---|---|")
    for feature, row in result["per_feature"].items():
        for arm in ARMS:
            r = row[arm]
            lines.append(
                f"| {feature} | {arm} | {_fmt(r['accuracy'], 3)} | {_fmt(r['hit_rate'], 3)} | "
                f"{_fmt(r['false_alarm_rate'], 3)} | {_fmt(r['cant_tell_share'], 3)} |"
            )
    lines.append("")
    lines.append("## Other descriptives")
    lines.append("")
    ct = result["cant_tell_share"]
    lines.append(
        f"- Share of Can't tell answers: untrained {_fmt(ct['untrained'], 3)}, "
        f"trained {_fmt(ct['trained'], 3)}."
    )
    ys = result["yes_share"]
    lines.append(
        f"- Share of Yes answers: untrained {_fmt(ys['untrained'], 3)}, "
        f"trained {_fmt(ys['trained'], 3)}."
    )
    mt = result["median_times"]
    lesson = mt["lesson_seconds"]
    lines.append(
        "- Median test time in seconds: "
        f"untrained {_fmt(mt['test_seconds']['untrained']['median'])}, "
        f"trained {_fmt(mt['test_seconds']['trained']['median'])}."
    )
    lines.append(
        "- Median lesson time in seconds: "
        f"trained {_fmt(lesson['trained']['median'])} (n {lesson['trained']['n']}), "
        f"untrained after the test {_fmt(lesson['untrained']['median'])} "
        f"(n {lesson['untrained']['n']})."
    )
    lines.append(
        "- Completed sessions by source: "
        + ", ".join(
            f"{src} {row['untrained']} untrained and {row['trained']} trained"
            for src, row in result["by_source"].items()
        )
        + "."
    )
    lines.append(
        "- Warm-up item: "
        + ", ".join(
            f"{k} chosen by {_fmt(v['share'], 3)} (n {v['n']})" for k, v in result["warmup"].items()
        )
        + "."
    )
    lines.append("")
    lines.append("## Sensitivity checks (plan item 6)")
    lines.append("")
    lines.append(
        "| Check | n trained | n untrained | Difference, points | 95 percent interval | p |"
    )
    lines.append("|---|---|---|---|---|---|")
    for name, s in result["sensitivity"].items():
        lines.append(
            f"| {name} | {s['n_trained']} | {s['n_untrained']} | "
            f"{_fmt(s.get('difference_points'))} | {_ci_text(s.get('ci95_points'))} | "
            f"{_fmt(s.get('permutation_p'), 4)} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def draw_chart(result: dict[str, Any], path: Path, *, synthetic: bool, title_extra: str) -> str:
    """Grouped bars of items right per person, one colour per arm. Returns the title used."""
    dist = result["score_distribution"]
    x = np.arange(N_ITEMS + 1)
    width = 0.42
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=120)
    p = result["primary"]
    for i, arm in enumerate(ARMS):
        counts = np.asarray(dist[arm], dtype=int)
        offset = (i - 0.5) * width
        mean = p.get(f"mean_{arm}")
        label = f"{arm} (n {counts.sum()}"
        label += f", mean {mean * N_ITEMS:.1f} right)" if mean is not None else ")"
        ax.bar(x + offset, counts, width=width, color=ARM_COLOURS[arm], label=label, linewidth=0)
        if mean is not None:
            ax.axvline(mean * N_ITEMS, color=ARM_COLOURS[arm], linestyle="--", linewidth=1.5)
    title = chart_title(
        f"items right out of 16, per person, by arm{title_extra}", synthetic=synthetic
    )
    ax.set_title(title, loc="left", fontsize=12)
    ax.set_xlabel("items right out of 16 (Can't tell counts as wrong)")
    ax.set_ylabel("people")
    ax.set_xticks(x)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e5e5e2", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left")
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


def write_outputs(
    result: dict[str, Any],
    *,
    out_dir: Path,
    stamp_name: str,
    synthetic: bool,
    title_extra: str = "",
) -> dict[str, Path]:
    json_path = out_dir / f"usability_{stamp_name}.json"
    md_path = out_dir / f"usability_{stamp_name}.md"
    png_path = out_dir / f"usability_{stamp_name}.png"
    title = draw_chart(result, png_path, synthetic=synthetic, title_extra=title_extra)
    result["chart_title"] = title
    result["outputs"] = {
        "json": str(json_path.name),
        "markdown": str(md_path.name),
        "chart": str(png_path.name),
    }
    write_json(json_path, result)
    md_path.write_text(
        markdown_report(result, synthetic=synthetic, title_extra=title_extra), encoding="utf-8"
    )
    return {"json": json_path, "markdown": md_path, "chart": png_path}


def run(
    *,
    input_dir: Path,
    out_dir: Path,
    synthetic: bool,
    stamp_name: str,
    scenario: str | None,
    n_boot: int = N_BOOT,
    n_perm: int = N_PERM,
    launch_utc: datetime | None = None,
) -> dict[str, Any]:
    reason = guard(input_dir, synthetic=synthetic)
    if reason:
        raise Refused(reason)
    sessions, responses = load_export(input_dir)
    result = result_header(SCRIPT, synthetic=synthetic, stamp=stamp_name)
    if synthetic:
        result["scenario"] = scenario
    result["input"] = str(input_dir)
    result["plan_sha256"] = plan_sha256()
    result.update(analyse(sessions, responses, n_boot=n_boot, n_perm=n_perm, launch_utc=launch_utc))
    title_extra = f" ({scenario} scenario)" if synthetic and scenario else ""
    paths = write_outputs(
        result, out_dir=out_dir, stamp_name=stamp_name, synthetic=synthetic, title_extra=title_extra
    )
    result["paths"] = {k: str(v) for k, v in paths.items()}
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--synthetic", action="store_true", help="run on generated data, stamp SYNTHETIC"
    )
    parser.add_argument(
        "--scenario", default=None, help=f"synthetic scenario (default {DEFAULT_SCENARIO})"
    )
    parser.add_argument(
        "--input", type=Path, default=None, help="folder with sessions.csv and responses.csv"
    )
    parser.add_argument("--out-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument(
        "--launch-utc", default=None, help="drop dry runs started before this UTC time"
    )
    parser.add_argument("--resamples", type=int, default=N_BOOT)
    parser.add_argument("--permutations", type=int, default=N_PERM)
    args = parser.parse_args(argv)
    launch = parse_utc(args.launch_utc) if args.launch_utc else None

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
        scenario = None
        input_dir = args.input if args.input is not None else EXPORT_DIR
        stamp_name = now_utc().strftime("%Y%m%d")

    reason = guard(input_dir, synthetic=args.synthetic)
    if reason:
        print(reason)
        return 3
    if not (input_dir / "sessions.csv").exists():
        print(
            f"No sessions.csv in {input_dir}. "
            "Run evals/make_synthetic_sessions.py first for synthetic data."
        )
        return 4

    result = run(
        input_dir=input_dir,
        out_dir=args.out_dir,
        synthetic=args.synthetic,
        stamp_name=stamp_name,
        scenario=scenario,
        n_boot=args.resamples,
        n_perm=args.permutations,
        launch_utc=launch,
    )
    p = result["primary"]
    ci = p.get("ci95_points")
    ci_text = f"{ci[0]} to {ci[1]}" if ci else "n/a"
    label = f"{result['stamp']} {scenario}" if args.synthetic else result["stamp"]
    print(
        f"{label}: trained minus untrained {p.get('difference_points')} points, "
        f"95 percent interval {ci_text}, permutation p {p.get('permutation_p')}, "
        f"Hedges g {p.get('hedges_g')}, status {p['status']} "
        f"(n trained {p['n_trained']}, n untrained {p['n_untrained']})"
    )
    for key, path in result["paths"].items():
        print(f"wrote {key}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
