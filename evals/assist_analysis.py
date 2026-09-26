"""The pre-registered analysis of part 2, the assisted second look: docs/analysis_plan_v2.md.

Without --synthetic this script refuses to run before the data lock, without the git tag
prereg-v2 on the pinned commit, when docs/analysis_plan_v2.md differs from the tagged and pinned
version, or on a folder marked SYNTHETIC.txt. It always reads the real clock and this repository,
exactly like evals/usability_analysis.py, whose git helpers it uses. With --synthetic it first
writes one of three generated data sets (the question helps, does nothing, or people change to a
wrong answer when asked) and analyses only that, stamping every output SYNTHETIC.

Input: part2_sessions.csv and part2_responses.csv from the export, columns below.

Usage:
  uv run python evals/assist_analysis.py --synthetic [--scenario helps|nothing|wrong_changes]
  uv run python evals/assist_analysis.py [--input data/export]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from core.lock import DATA_LOCK_UTC
from evals import usability_analysis as ua
from evals.common import (
    EXPORT_DIR,
    RESULTS_DIR,
    ROOT,
    iso_utc,
    now_utc,
    result_header,
    round_or_none,
    write_json,
)
from evals.power import beta_params

SCRIPT = "evals/assist_analysis.py"
REPO_ROOT = ROOT
PLAN_RELATIVE = "docs/analysis_plan_v2.md"
PLAN_TAG = "prereg-v2"
# The commit the tag points at and the SHA-256 of the tagged plan, as docs/notes/plan_hash.md
# records them (tagged 2026-09-26).
PLAN_COMMIT: str | None = "d2ada333ea3c710589504e1bac7b9c6bb55b91a8"
PLAN_SHA256: str | None = "723f7980a2e05eba3b74f43826e0afbf2211a7c35da6dcc18581dba3df73a8c3"
SYNTHETIC_MARKER = ua.SYNTHETIC_MARKER
SYNTHETIC_DIR = ROOT / "data" / "synthetic_part2"
SEED = 20260926
N_BOOT = 10_000
N_PERM = 10_000
ALPHA = 0.05
N_ITEMS = 8
MIN_FINISHED_PER_ARM = 20
MIN_SECONDS = 20.0
ARMS = ("unassisted", "assisted")
PART1_ARMS = ("untrained", "trained")
ANSWERS = ("yes", "no", "cant_tell")
SCENARIOS = ("helps", "nothing", "wrong_changes")
DEFAULT_SCENARIO = "helps"

SESSION_COLUMNS = [
    "part2_id",
    "session_id",
    "part1_arm",
    "arm",
    "block_id",
    "offered_at_utc",
    "declined",
    "started_at_utc",
    "completed_at_utc",
    "test_seconds",
    "client_token_hash",
    "is_test",
    "post_lock",
]
RESPONSE_COLUMNS = [
    "part2_id",
    "item_id",
    "feature",
    "gold",
    "position",
    "first_answer",
    "final_answer",
    "question_shown",
    "choice",
    "t_first_ms",
    "t_final_ms",
    "correct",
]


class Refused(RuntimeError):
    """run() raises this with the sentence from guard()."""


# ---------------------------------------------------------------------------
# Refusal checks (hard rule 13), the same order and words as part 1's
# ---------------------------------------------------------------------------


def refusal_reason(now: datetime, repo: Path) -> str | None:
    if now < DATA_LOCK_UTC:
        return (
            f"Refusing to run: the data lock is {iso_utc(DATA_LOCK_UTC)} and it is now "
            f"{iso_utc(now)}, so real outcomes are not computed yet."
        )
    if not ua.tag_exists(repo, PLAN_TAG):
        return (
            f"Refusing to run: the git tag {PLAN_TAG} does not exist in {repo}, "
            "so the part 2 analysis plan is not registered."
        )
    tagged = ua.tagged_plan(repo, PLAN_TAG, PLAN_RELATIVE)
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
    if PLAN_SHA256 is None or hashlib.sha256(tagged).hexdigest() != PLAN_SHA256:
        return (
            f"Refusing to run: the tagged {PLAN_RELATIVE} does not have the SHA-256 pinned in "
            f"{SCRIPT} and docs/notes/plan_hash.md, so it is not the registered plan."
        )
    if PLAN_COMMIT is None or ua.tagged_commit(repo, PLAN_TAG) != PLAN_COMMIT:
        return (
            f"Refusing to run: the tag {PLAN_TAG} does not point at the commit "
            "docs/notes/plan_hash.md records."
        )
    return None


def guard(input_dir: Path, *, synthetic: bool) -> str | None:
    marked = (input_dir / SYNTHETIC_MARKER).exists()
    if synthetic:
        if not marked or input_dir.resolve() == EXPORT_DIR.resolve():
            return (
                "Refusing to run: with --synthetic the input must be a folder this script "
                f"generated, with {SYNTHETIC_MARKER} in it, and never the real export. "
                f"{input_dir} is not one."
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


def _bool(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.lower().isin(ua.TRUE_WORDS)


def tidy(sessions: pd.DataFrame, responses: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    for name, frame, cols in (
        ("part2_sessions.csv", sessions, SESSION_COLUMNS),
        ("part2_responses.csv", responses, RESPONSE_COLUMNS),
    ):
        missing = [c for c in cols if c not in frame.columns]
        if missing:
            raise ValueError(f"{name} is missing columns: {', '.join(missing)}")
    s = sessions.copy()
    for col in ("declined", "is_test", "post_lock"):
        s[col] = _bool(s[col])
    for col in ("offered_at_utc", "started_at_utc", "completed_at_utc"):
        text = s[col].fillna("").astype(str).str.strip().replace("", None)
        s[col] = pd.to_datetime(text, utc=True, errors="coerce", format="ISO8601")
    s["test_seconds"] = pd.to_numeric(s["test_seconds"], errors="coerce")
    for col in ("part2_id", "session_id", "part1_arm", "arm", "client_token_hash"):
        s[col] = s[col].fillna("").astype(str).str.strip()
    r = responses.copy()
    for col in ("first_answer", "final_answer", "gold", "choice", "feature"):
        r[col] = r[col].fillna("").astype(str).str.strip().str.lower()
    r["part2_id"] = r["part2_id"].astype(str)
    r["question_shown"] = _bool(r["question_shown"])
    for col in ("t_first_ms", "t_final_ms"):
        r[col] = pd.to_numeric(r[col], errors="coerce")
    r["correct"] = correct(r["final_answer"], r["gold"])
    r["first_correct"] = correct(r["first_answer"], r["gold"])
    r["changed"] = r["first_answer"] != r["final_answer"]
    return s, r


def correct(answer: pd.Series, gold: pd.Series) -> pd.Series:
    """Yes on present or No on absent. Can't tell is incorrect (plan item 6)."""
    return (
        ((answer == "yes") & (gold == "present")) | ((answer == "no") & (gold == "absent"))
    ).astype(int)


def load_export(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    s = pd.read_csv(path / "part2_sessions.csv", dtype=str, keep_default_na=False)
    r = pd.read_csv(path / "part2_responses.csv", dtype=str, keep_default_na=False)
    return tidy(s, r)


# ---------------------------------------------------------------------------
# Exclusions (plan item 8, in the plan's order)
# ---------------------------------------------------------------------------


@dataclass
class Step:
    order: int
    rule: str
    removed: int
    remaining: int


@dataclass
class Kept:
    frame: pd.DataFrame
    steps: list[Step] = field(default_factory=list)
    counts: dict[str, Any] = field(default_factory=dict)


def _by_arm(frame: pd.DataFrame) -> dict[str, int]:
    vc = frame["arm"].value_counts()
    return {a: int(vc.get(a, 0)) for a in ARMS}


def apply_exclusions(sessions: pd.DataFrame, responses: pd.DataFrame) -> Kept:
    answered = responses.groupby("part2_id").size()
    f = sessions.copy()
    f["n_answered"] = f["part2_id"].map(answered).fillna(0).astype(int)
    steps: list[Step] = []
    lock = pd.Timestamp(DATA_LOCK_UTC)
    when = f["started_at_utc"].fillna(f["offered_at_utc"])
    drop = f["post_lock"] | (when >= lock)
    f = f[~drop]
    steps.append(Step(0, "offered or started at or after the data lock", int(drop.sum()), len(f)))
    offered_by_part1 = {a: int((f["part1_arm"] == a).sum()) for a in PART1_ARMS}
    declined = f[f["declined"]]
    counts: dict[str, Any] = {
        "offered": len(f),
        "offered_by_part1_arm": offered_by_part1,
        "declined": len(declined),
        "declined_by_part1_arm": {a: int((declined["part1_arm"] == a).sum()) for a in PART1_ARMS},
    }
    f = f[~f["declined"]]
    counts["randomized"] = _by_arm(f)
    counts["started"] = _by_arm(f[f["n_answered"] > 0])
    counts["finished"] = _by_arm(f[(f["n_answered"] >= N_ITEMS) & f["completed_at_utc"].notna()])

    drop = (f["n_answered"] < N_ITEMS) | f["completed_at_utc"].isna()
    f = f[~drop]
    steps.append(Step(1, "did not finish all 8 items", int(drop.sum()), len(f)))
    drop = f["test_seconds"].notna() & (f["test_seconds"] < MIN_SECONDS)
    f = f[~drop]
    steps.append(Step(2, "finished the 8 in under 20 seconds", int(drop.sum()), len(f)))
    drop = f["is_test"]
    f = f[~drop]
    steps.append(Step(3, "QA session, or its part 1 session was QA", int(drop.sum()), len(f)))
    ordered = f.sort_values(["completed_at_utc", "part2_id"], kind="mergesort")
    dup = (ordered["client_token_hash"] != "") & ordered.duplicated(
        subset=["client_token_hash"], keep="first"
    )
    f = ordered[~dup]
    steps.append(
        Step(4, "repeat part 2 session from the same browser token", int(dup.sum()), len(f))
    )
    counts["analysed"] = _by_arm(f)
    return Kept(frame=f.reset_index(drop=True), steps=steps, counts=counts)


# ---------------------------------------------------------------------------
# Estimates
# ---------------------------------------------------------------------------


def primary(
    assisted: np.ndarray, unassisted: np.ndarray, *, n_boot: int, n_perm: int
) -> dict[str, Any]:
    a = np.asarray(assisted, dtype=float)
    u = np.asarray(unassisted, dtype=float)
    out: dict[str, Any] = {"n_assisted": len(a), "n_unassisted": len(u)}
    if len(a) == 0 or len(u) == 0:
        out.update({"difference": None, "ci_low": None, "ci_high": None, "permutation_p": None})
        out["status"] = "not computed: an arm is empty"
        return out
    diff = float(a.mean() - u.mean())
    boot = ua.bootstrap_difference(a, u, n_boot=n_boot, rng=np.random.default_rng(SEED))
    lo, hi = np.percentile(boot, [2.5, 97.5])
    p = ua.permutation_p(a, u, n_perm=n_perm, rng=np.random.default_rng(SEED))
    enough = min(len(a), len(u)) >= MIN_FINISHED_PER_ARM
    out.update(
        {
            "assisted_mean": round(float(a.mean()) * 100, 1),
            "unassisted_mean": round(float(u.mean()) * 100, 1),
            "difference": round(diff * 100, 1),
            "ci_low": round(float(lo) * 100, 1),
            "ci_high": round(float(hi) * 100, 1),
            "permutation_p": round(p, 4),
            "rejects_at_alpha_05": bool(p < ALPHA),
            "bootstrap_resamples": n_boot,
            "permutations": n_perm,
            "seed": SEED,
            "status": "confirmatory" if enough else "descriptive",
            "status_note": (
                "at least 20 finished part 2 sessions in each arm, so the plan's one "
                "confirmatory test applies"
                if enough
                else "fewer than 20 finished part 2 sessions in an arm, so this is a "
                "description, not a test"
            ),
        }
    )
    return out


def _share(num: float, den: float) -> float | None:
    return round_or_none(num / den) if den else None


def secondary(kept: pd.DataFrame, responses: pd.DataFrame) -> dict[str, Any]:
    r = responses.merge(kept[["part2_id", "arm", "part1_arm"]], on="part2_id")
    assisted = r[r["arm"] == "assisted"]
    shown = assisted[assisted["question_shown"]]
    changed = shown[shown["changed"]]
    kept_ans = shown[~shown["changed"]]
    out: dict[str, Any] = {
        "assisted_items": len(assisted),
        "question_shown": len(shown),
        "question_shown_share": _share(len(shown), len(assisted)),
        "changed_after_question": len(changed),
        "changed_share_of_shown": _share(len(changed), len(shown)),
        "accuracy_changed": _share(changed["correct"].sum(), len(changed)),
        "accuracy_kept_after_question": _share(kept_ans["correct"].sum(), len(kept_ans)),
        "right_to_wrong": int(((changed["first_correct"] == 1) & (changed["correct"] == 0)).sum()),
        "wrong_to_right": int(((changed["first_correct"] == 0) & (changed["correct"] == 1)).sum()),
        "changed_without_question": int((r["changed"] & ~r["question_shown"]).sum()),
    }
    out["accuracy_by_feature"] = {
        arm: {
            feat: _share(g["correct"].sum(), len(g))
            for feat, g in r[r["arm"] == arm].groupby("feature")
        }
        for arm in ARMS
    }
    scores = r.groupby(["part2_id", "arm", "part1_arm"])["correct"].mean().reset_index()
    out["accuracy_by_part1_arm"] = {
        arm: {
            p1: round_or_none(g["correct"].mean()) if len(g) else None
            for p1, g in scores[scores["arm"] == arm].groupby("part1_arm")
        }
        for arm in ARMS
    }
    out["median_seconds_per_item"] = {
        arm: round_or_none(float(r[r["arm"] == arm]["t_final_ms"].median()) / 1000)
        if len(r[r["arm"] == arm])
        else None
        for arm in ARMS
    }
    out["cant_tell_share"] = {
        arm: _share(
            (r[r["arm"] == arm]["final_answer"] == "cant_tell").sum(), len(r[r["arm"] == arm])
        )
        for arm in ARMS
    }
    return out


def analyse(
    sessions: pd.DataFrame, responses: pd.DataFrame, *, n_boot: int = N_BOOT, n_perm: int = N_PERM
) -> dict[str, Any]:
    kept = apply_exclusions(sessions, responses)
    sub = responses[responses["part2_id"].isin(kept.frame["part2_id"])]
    acc = sub.groupby("part2_id")["correct"].sum() / N_ITEMS
    scores = kept.frame.assign(accuracy=kept.frame["part2_id"].map(acc).fillna(0.0))
    arm = {a: scores[scores["arm"] == a]["accuracy"].to_numpy() for a in ARMS}
    return {
        "exclusions": [s.__dict__ for s in kept.steps],
        "counts": kept.counts,
        "primary": primary(arm["assisted"], arm["unassisted"], n_boot=n_boot, n_perm=n_perm),
        "secondary": secondary(kept.frame, sub),
    }


def readme_row(result: dict[str, Any]) -> str:
    """The second human row of the README's numbers table, or the too-few sentence."""
    p = result["primary"]
    if p.get("difference") is None or p["status"] != "confirmatory":
        return (
            f"Too few people finished part 2 for the plan's test: {p['n_assisted']} assisted and "
            f"{p['n_unassisted']} unassisted, and the plan needs 20 in each."
        )
    return (
        f"Does the checker's question help? assisted {p['n_assisted']}, unassisted "
        f"{p['n_unassisted']}, difference {p['difference']} points, interval "
        f"{p['ci_low']} to {p['ci_high']}"
    )


# ---------------------------------------------------------------------------
# Synthetic data (plan item 7): helps, nothing, wrong_changes
# ---------------------------------------------------------------------------

SYNTHETIC_FLAGS = {
    # Like the real rule: no plant flags (no model passed plants), one wrong flag on a08.
    "a01": "present",
    "a02": "absent",
    "a03": "present",
    "a04": "absent",
    "a07": "present",
    "a08": "present",
}


def _items() -> list[dict[str, str]]:
    doc = yaml.safe_load((ROOT / "content" / "part2_items.yaml").read_text(encoding="utf-8"))
    return [{k: str(v) for k, v in row.items()} for row in doc["items"]]


def _right(gold: str) -> str:
    return "yes" if gold == "present" else "no"


def _wrong(gold: str, rng: np.random.Generator) -> str:
    return "cant_tell" if rng.random() < 0.3 else ("no" if gold == "present" else "yes")


def agrees(answer: str, points_to: str) -> bool:
    return answer == _right(points_to)


def make_synthetic(scenario: str, out: Path, *, n_per_arm: int = 60, seed: int = SEED) -> Path:
    """Write a marked folder of part 2 sessions for one scenario. Deterministic from the seed."""
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario!r}, one of {', '.join(SCENARIOS)}")
    rng = np.random.default_rng(seed + SCENARIOS.index(scenario))
    items = _items()
    a, b = beta_params(0.6, 0.1)
    start = DATA_LOCK_UTC - timedelta(days=1)
    sess: list[dict[str, Any]] = []
    resp: list[dict[str, Any]] = []
    n = 0
    for arm in ARMS:
        for i in range(n_per_arm + 6):
            n += 1
            pid = f"p2-{n:04d}"
            declined = i >= n_per_arm
            t0 = start + timedelta(minutes=n)
            sess.append(
                {
                    "part2_id": pid,
                    "session_id": f"s-{n:04d}",
                    "part1_arm": PART1_ARMS[i % 2],
                    "arm": "" if declined else arm,
                    "block_id": "" if declined else str(i // 4),
                    "offered_at_utc": iso_utc(t0),
                    "declined": str(declined).lower(),
                    "started_at_utc": "" if declined else iso_utc(t0),
                    "completed_at_utc": "" if declined else iso_utc(t0 + timedelta(seconds=90)),
                    "test_seconds": "" if declined else "90",
                    "client_token_hash": f"tok{n:04d}",
                    "is_test": "false",
                    "post_lock": "false",
                }
            )
            if declined:
                continue
            skill = rng.beta(a, b)
            for pos, it in enumerate(rng.permutation(len(items))):
                item = items[int(it)]
                gold = item["gold"]
                first = _right(gold) if rng.random() < skill else _wrong(gold, rng)
                flag = SYNTHETIC_FLAGS.get(item["id"])
                shown = arm == "assisted" and flag is not None and not agrees(first, flag)
                final, choice = first, ""
                if shown:
                    choice = "keep"
                    if scenario == "helps" and first != _right(gold) and rng.random() < 0.7:
                        final, choice = _right(gold), "change"
                    elif scenario == "wrong_changes":
                        # Asked, the person always moves to a wrong answer they had not given.
                        wrong = [x for x in ANSWERS if x not in (_right(gold), first)]
                        final, choice = str(rng.choice(wrong)), "change"
                t_first = int(rng.integers(3000, 12000))
                resp.append(
                    {
                        "part2_id": pid,
                        "item_id": item["id"],
                        "feature": item["feature"],
                        "gold": gold,
                        "position": pos,
                        "first_answer": first,
                        "final_answer": final,
                        "question_shown": str(shown).lower(),
                        "choice": choice,
                        "t_first_ms": t_first,
                        "t_final_ms": t_first + (int(rng.integers(1500, 5000)) if shown else 0),
                        "correct": int(final == _right(gold)),
                    }
                )
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(sess, columns=SESSION_COLUMNS).to_csv(out / "part2_sessions.csv", index=False)
    pd.DataFrame(resp, columns=RESPONSE_COLUMNS).to_csv(out / "part2_responses.csv", index=False)
    (out / SYNTHETIC_MARKER).write_text(
        f"Generated by {SCRIPT}, scenario {scenario}, seed {seed}. Not real data.\n",
        encoding="utf-8",
    )
    return out


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def markdown(result: dict[str, Any], *, synthetic: bool) -> str:
    p, s = result["primary"], result["secondary"]
    head = "SYNTHETIC. " if synthetic else ""
    lines = [
        f"# {head}Part 2: does the checker's question help?",
        "",
        readme_row(result),
        "",
        "| | assisted | unassisted |",
        "|---|---|---|",
        f"| finished and analysed | {p['n_assisted']} | {p['n_unassisted']} |",
        f"| mean accuracy, percent | {p.get('assisted_mean')} | {p.get('unassisted_mean')} |",
        "",
        f"Difference {p.get('difference')} points, 95 percent interval {p.get('ci_low')} to "
        f"{p.get('ci_high')}, permutation p {p.get('permutation_p')}, status {p['status']}.",
        "",
        f"Questions shown: {s['question_shown']} of {s['assisted_items']} assisted answers. "
        f"Changed after a question: {s['changed_after_question']}, "
        f"wrong to right {s['wrong_to_right']}, right to wrong {s['right_to_wrong']}.",
        "",
        "Exclusions:",
        "",
    ]
    lines += [
        f"- {e['rule']}: {e['removed']} removed, {e['remaining']} left"
        for e in result["exclusions"]
    ]
    return "\n".join(lines) + "\n"


def run(
    *,
    input_dir: Path,
    out_dir: Path,
    synthetic: bool,
    stamp_name: str,
    n_boot: int = N_BOOT,
    n_perm: int = N_PERM,
    scenario: str | None = None,
) -> dict[str, Any]:
    reason = guard(input_dir, synthetic=synthetic)
    if reason:
        raise Refused(reason)
    sessions, responses = load_export(input_dir)
    result = result_header(SCRIPT, synthetic=synthetic, stamp=stamp_name)
    if scenario:
        result["scenario"] = scenario
    plan = REPO_ROOT / PLAN_RELATIVE
    result["plan_sha256"] = hashlib.sha256(plan.read_bytes()).hexdigest()
    result.update(analyse(sessions, responses, n_boot=n_boot, n_perm=n_perm))
    result["readme_row"] = readme_row(result)
    write_json(out_dir / f"assist_{stamp_name}.json", result)
    (out_dir / f"assist_{stamp_name}.md").write_text(markdown(result, synthetic=synthetic), "utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--synthetic", action="store_true", help="generate and analyse a scenario")
    p.add_argument("--scenario", default=None, choices=[*SCENARIOS, "all"])
    p.add_argument("--input", type=Path, default=None)
    p.add_argument("--out-dir", type=Path, default=RESULTS_DIR)
    p.add_argument("--resamples", type=int, default=N_BOOT)
    p.add_argument("--permutations", type=int, default=N_PERM)
    args = p.parse_args(argv)
    if not args.synthetic:
        if args.scenario:
            print("The --scenario option only makes sense with --synthetic.")
            return 2
        input_dir = args.input if args.input is not None else EXPORT_DIR
        reason = guard(input_dir, synthetic=False)
        if reason:
            print(reason)
            return 3
        if not (input_dir / "part2_sessions.csv").exists():
            print(f"No part2_sessions.csv in {input_dir}.")
            return 2
        result = run(
            input_dir=input_dir,
            out_dir=args.out_dir,
            synthetic=False,
            stamp_name=now_utc().strftime("%Y%m%d"),
            n_boot=args.resamples,
            n_perm=args.permutations,
        )
        print(result["readme_row"])
        print(f"wrote json: {args.out_dir / ('assist_' + result['stamp'] + '.json')}")
        return 0
    names = SCENARIOS if args.scenario in (None, "all") else (args.scenario,)
    for name in names:
        folder = (
            args.input if args.input is not None else make_synthetic(name, SYNTHETIC_DIR / name)
        )
        reason = guard(folder, synthetic=True)
        if reason:
            print(reason)
            return 3
        result = run(
            input_dir=folder,
            out_dir=args.out_dir,
            synthetic=True,
            stamp_name=f"synthetic_{name}",
            n_boot=args.resamples,
            n_perm=args.permutations,
            scenario=name,
        )
        pr, s = result["primary"], result["secondary"]
        print(
            f"SYNTHETIC {name}: assisted {pr['assisted_mean']} vs unassisted "
            f"{pr['unassisted_mean']}, difference {pr['difference']} points "
            f"[{pr['ci_low']}, {pr['ci_high']}], p {pr['permutation_p']}; "
            f"questions {s['question_shown']}, changed {s['changed_after_question']}, "
            f"right to wrong {s['right_to_wrong']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
