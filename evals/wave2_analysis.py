"""The second wave of the study: the two registered analyses, run as they are on a second window.

docs/analysis_plan_v3.md says why. Nobody took part before the first lock, 2026-09-28T01:00:00Z,
and the hackathon's deadline moved, so the same study runs a second time. Nothing in the analysis
changes. This script does not copy it: it calls the code of evals/usability_analysis.py (plan
tagged prereg-v1) and evals/assist_analysis.py (plan tagged prereg-v2), neither of which is
edited, and hands them the sittings of the second window.

What this script does, and nothing else:

1. It reads the export and decides by each sitting's start time, never by the stored post_lock
   mark. The server marks every sitting made after the FIRST lock as post_lock, so that mark is
   true for the whole second wave and says nothing here. A sitting that started at or after
   SECOND_LOCK_UTC is marked post_lock and the analysis drops it under its own first rule. A
   sitting with no start time that can be read cannot be placed in the window, so it is marked
   the same way.
2. It gives WAVE2_OPEN_UTC to the analysis as the launch time, so a sitting that started before
   the wave opened is left out by the plan's own dry run rule, as a dry run is.
3. It keeps a part 2 sitting only when the part 1 sitting it follows started inside the window.
4. While the two analyses run, the constants they read (SWAPPED below) hold wave 2's values. A
   context manager sets them and always puts them back, also when the run fails.

Without --synthetic it refuses to run before the second lock by the real clock, without the git
tag prereg-v3 on the pinned commit, when docs/analysis_plan_v3.md differs from the tagged and
pinned version, when one of the two plans or the two analysis scripts differs from its copy at
that tag, or on a folder marked SYNTHETIC.txt. The pins are None until the tag exists, and while
they are None it refuses real data.

Why it has its own checks and does not call the two scripts' run(): evals/usability_analysis.py
binds PLAN_TAG and PLAN_RELATIVE as default arguments of its git helpers when it is imported, so
setting those constants later does not move its tag checks. The helpers are called here with the
tag and the path given.

Usage:
  uv run python evals/wave2_analysis.py --synthetic [--out-dir DIR]
  uv run python evals/wave2_analysis.py [--input data/export]
  uv run python evals/wave2_analysis.py --window [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from core.lock import DATA_LOCK_UTC as FIRST_LOCK_UTC
from evals import assist_analysis as aa
from evals import make_synthetic_sessions as mss
from evals import usability_analysis as ua
from evals.common import (
    EXPORT_DIR,
    RESULTS_DIR,
    ROOT,
    iso_utc,
    now_utc,
    result_header,
    write_json,
)

SCRIPT = "evals/wave2_analysis.py"
REPO_ROOT = ROOT
PLAN_RELATIVE = "docs/analysis_plan_v3.md"
PLAN_TAG = "prereg-v3"
# Pinned when the plan is tagged, as docs/notes/plan_hash.md records them. Until then the
# script refuses real data: an unpinned plan is not a registered plan.
PLAN_COMMIT: str | None = None
PLAN_SHA256: str | None = None

# The window, written once here. core/lock.py may hold the same two instants under the same
# names; evals/tests/test_wave2_analysis.py fails if it does and they differ.
WAVE2_OPEN_UTC = datetime(2026, 9, 30, 4, 0, 0, tzinfo=UTC)
SECOND_LOCK_UTC = datetime(2026, 10, 3, 4, 0, 0, tzinfo=UTC)
# When the lock job runs this script (scripts/mac_jobs.py, the job lock2).
LOCK_JOB_UTC = datetime(2026, 10, 3, 4, 10, 0, tzinfo=UTC)
PACIFIC = ZoneInfo("America/Los_Angeles")

# What plan v3 rests on. Each must be, byte for byte, its copy at the tag prereg-v3.
REGISTERED = (
    "docs/analysis_plan.md",
    "docs/analysis_plan_v2.md",
    "evals/usability_analysis.py",
    "evals/assist_analysis.py",
)
# The constants the two analysis scripts read while they run.
SWAPPED = ("DATA_LOCK_UTC", "PLAN_RELATIVE", "PLAN_TAG", "PLAN_COMMIT", "PLAN_SHA256", "SCRIPT")

SYNTHETIC_MARKER = ua.SYNTHETIC_MARKER
SYNTHETIC_DIR = ROOT / "data" / "synthetic_wave2"
SYNTHETIC_SEED = 20261003
WINDOW_FILE = RESULTS_DIR / "wave2_window.json"
PART2_FILES = ("part2_sessions.csv", "part2_responses.csv")
TITLE_EXTRA = " (second wave)"


class Refused(RuntimeError):
    """run() raises this with the sentence from guard()."""


# ---------------------------------------------------------------------------
# Refusal checks (hard rule 13), the same order and words as the two scripts'
# ---------------------------------------------------------------------------


def refusal_reason(now: datetime, repo: Path) -> str | None:
    """A plain sentence saying why real data cannot be analysed now, or None when it can."""
    if now < SECOND_LOCK_UTC:
        return (
            f"Refusing to run: the second data lock is {iso_utc(SECOND_LOCK_UTC)} and it is now "
            f"{iso_utc(now)}, so the second wave's outcomes are not computed yet."
        )
    if not ua.tag_exists(repo, PLAN_TAG):
        return (
            f"Refusing to run: the git tag {PLAN_TAG} does not exist in {repo}, "
            "so the second wave's plan is not registered."
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
    for relative in REGISTERED:
        at_tag = ua.tagged_plan(repo, PLAN_TAG, relative)
        here = repo / relative
        if at_tag is None or not here.exists() or at_tag != here.read_bytes():
            return (
                f"Refusing to run: {relative} differs from its copy at the tag {PLAN_TAG}, or "
                "is missing, so the second wave would not run the registered analysis."
            )
    return None


def guard(input_dir: Path, *, synthetic: bool) -> str | None:
    """Why this run must not go ahead, or None. The real clock and this repository, always."""
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
# The constants the two scripts read, set for the run and always put back
# ---------------------------------------------------------------------------


def wave2_values() -> dict[str, Any]:
    return {
        "DATA_LOCK_UTC": SECOND_LOCK_UTC,
        "PLAN_RELATIVE": PLAN_RELATIVE,
        "PLAN_TAG": PLAN_TAG,
        "PLAN_COMMIT": PLAN_COMMIT,
        "PLAN_SHA256": PLAN_SHA256,
        "SCRIPT": SCRIPT,
    }


@contextmanager
def wave2_constants() -> Iterator[None]:
    """Inside, the two analysis modules hold wave 2's constants. Outside, their own, always."""
    values = wave2_values()
    saved = [(module, name, getattr(module, name)) for module in (ua, aa) for name in SWAPPED]
    try:
        for module in (ua, aa):
            for name in SWAPPED:
                setattr(module, name, values[name])
        yield
    finally:
        for module, name, value in saved:
            setattr(module, name, value)


# ---------------------------------------------------------------------------
# The window
# ---------------------------------------------------------------------------


def local_label(ts: datetime) -> str:
    """The instant as California reads it, such as Friday Oct 2, 2026 at 21:00 PDT."""
    local = ts.astimezone(PACIFIC)
    return f"{local:%A} {local:%b} {local.day}, {local.year} at {local:%H:%M} {local.tzname()}"


def in_window(start: pd.Series) -> pd.Series:
    """True where a start time is at or after the opening and before the second lock."""
    opened = pd.Timestamp(WAVE2_OPEN_UTC)
    locked = pd.Timestamp(SECOND_LOCK_UTC)
    return start.notna() & (start >= opened) & (start < locked)


def by_start(start: pd.Series) -> dict[str, int]:
    """How many sittings started in each of the four times, and how many have no time."""
    first = pd.Timestamp(FIRST_LOCK_UTC)
    opened = pd.Timestamp(WAVE2_OPEN_UTC)
    locked = pd.Timestamp(SECOND_LOCK_UTC)
    return {
        "before_the_first_lock": int((start < first).sum()),
        "between_the_first_lock_and_the_opening": int(((start >= first) & (start < opened)).sum()),
        "inside_the_window": int(in_window(start).sum()),
        "at_or_after_the_second_lock": int((start >= locked).sum()),
        "no_start_time": int(start.isna().sum()),
    }


def window_part1(sessions: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Part 1's sittings with post_lock set from the start time, and what the window saw.

    Every row stays in the frame. The analysis then drops a sitting at or after the second lock
    under its first rule and one before the opening under its dry run rule, each counted where
    the plan counts it.
    """
    start = sessions["started_at_utc"]
    out = sessions.copy()
    out["post_lock"] = start.isna() | (start >= pd.Timestamp(SECOND_LOCK_UTC))
    seen = {
        "sittings_in_the_export": int(len(sessions)),
        "by_start_time": by_start(start),
        "stored_post_lock_marks_ignored": int(sessions["post_lock"].sum()),
    }
    return out, seen


def window_part2(part2: pd.DataFrame, part1: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Part 2's sittings whose part 1 sitting started inside the window, post_lock set by time.

    Part 2's analysis has no dry run rule, so a part 2 sitting that follows a part 1 sitting from
    outside the window is left out here, before the analysis, and counted in the window block.
    """
    inside = set(part1.loc[in_window(part1["started_at_utc"]), "session_id"].astype(str))
    linked = part2["session_id"].astype(str).isin(inside)
    out = part2[linked].copy()
    when = out["started_at_utc"].fillna(out["offered_at_utc"])
    out["post_lock"] = when.isna() | (when >= pd.Timestamp(SECOND_LOCK_UTC))
    seen = {
        "part2_sittings_in_the_export": int(len(part2)),
        "left_out_because_part1_started_outside_the_window": int((~linked).sum()),
        "part1_sitting_inside_the_window": int(linked.sum()),
        "stored_post_lock_marks_ignored": int(part2["post_lock"].sum()),
    }
    return out.reset_index(drop=True), seen


def window_block(seen: dict[str, Any]) -> dict[str, Any]:
    """What wave 2 adds to a results file: the window, the plan, and what the window saw."""
    return {
        "wave": 2,
        "plan": PLAN_RELATIVE,
        "plan_tag": PLAN_TAG,
        "same_design_and_analysis_as": ["prereg-v1", "prereg-v2"],
        "first_lock_utc": iso_utc(FIRST_LOCK_UTC),
        "open_utc": iso_utc(WAVE2_OPEN_UTC),
        "lock_utc": iso_utc(SECOND_LOCK_UTC),
        "rule": (
            "a sitting counts when it started at or after open_utc and before lock_utc; the "
            "stored post_lock mark is ignored"
        ),
        **seen,
    }


def window_record() -> dict[str, Any]:
    """results/wave2_window.json: the window as the README quotes it before the second lock."""
    record = result_header(SCRIPT, synthetic=False, stamp="window")
    record.update(
        {
            "wave": 2,
            "plan": PLAN_RELATIVE,
            "plan_tag": PLAN_TAG,
            "first_lock_utc": iso_utc(FIRST_LOCK_UTC),
            "open_utc": iso_utc(WAVE2_OPEN_UTC),
            "open_local": local_label(WAVE2_OPEN_UTC),
            "lock_utc": iso_utc(SECOND_LOCK_UTC),
            "lock_local": local_label(SECOND_LOCK_UTC),
            "lock_job_utc": iso_utc(LOCK_JOB_UTC),
            "window_hours": int((SECOND_LOCK_UTC - WAVE2_OPEN_UTC) / timedelta(hours=1)),
            "min_per_arm": ua.MIN_COMPLETED_PER_ARM,
        }
    )
    return record


def window_differs(path: Path = WINDOW_FILE) -> list[str]:
    """The fields of the committed window file that are not what this script writes."""
    try:
        have = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"{path.name} cannot be read: {e}"]
    want = window_record()
    keys = [k for k in want if k != "generated_at_utc"]
    return [
        f"{k}: the file says {have.get(k)!r}, the script says {want[k]!r}"
        for k in keys
        if have.get(k) != want[k]
    ] + [f"{k}: not written by the script" for k in have if k not in want]


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def plan_sha256() -> str:
    return hashlib.sha256((REPO_ROOT / PLAN_RELATIVE).read_bytes()).hexdigest()


def window_words(window: dict[str, Any]) -> str:
    """The lines a results page adds about the window, under the analysis' own report."""
    lines = [
        "## The second wave",
        "",
        f"Plan: `{window['plan']}`, tag `{window['plan_tag']}`. The design and the analysis are "
        "those of `prereg-v1` and `prereg-v2`.",
        "",
        f"A sitting counts when it started at or after {window['open_utc']} and before "
        f"{window['lock_utc']}. The stored post_lock mark is ignored.",
        "",
    ]
    for key, value in window.items():
        if isinstance(value, dict):
            for name, n in value.items():
                lines.append(f"- {key}, {name}: {n}")
        elif isinstance(value, int) and key != "wave":
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def run(
    *,
    input_dir: Path,
    out_dir: Path,
    synthetic: bool,
    stamp_name: str,
    n_boot: int = ua.N_BOOT,
    n_perm: int = ua.N_PERM,
    scenario: str | None = None,
) -> dict[str, Any]:
    """Both analyses on the second window. Returns part 1's result and part 2's, or None for
    part 2 when the export holds no part 2 files."""
    reason = guard(input_dir, synthetic=synthetic)
    if reason:
        raise Refused(reason)
    sessions, responses = ua.load_export(input_dir)
    has_part2 = all((input_dir / name).exists() for name in PART2_FILES)
    part1, seen1 = window_part1(sessions)
    sha = plan_sha256()
    part2_result: dict[str, Any] | None = None
    with wave2_constants():
        result = result_header(SCRIPT, synthetic=synthetic, stamp=stamp_name)
        if synthetic:
            result["scenario"] = scenario
        result["input"] = str(input_dir)
        result["plan_sha256"] = sha
        result.update(
            ua.analyse(part1, responses, n_boot=n_boot, n_perm=n_perm, launch_utc=WAVE2_OPEN_UTC)
        )
        result["window"] = window_block(seen1)
        paths = ua.write_outputs(
            result,
            out_dir=out_dir,
            stamp_name=stamp_name,
            synthetic=synthetic,
            title_extra=TITLE_EXTRA,
        )
        if has_part2:
            p2_sessions, p2_responses = aa.load_export(input_dir)
            part2, seen2 = window_part2(p2_sessions, sessions)
            part2_result = result_header(SCRIPT, synthetic=synthetic, stamp=stamp_name)
            if synthetic:
                part2_result["scenario"] = scenario
            part2_result["plan_sha256"] = sha
            part2_result.update(aa.analyse(part2, p2_responses, n_boot=n_boot, n_perm=n_perm))
            part2_result["readme_row"] = aa.readme_row(part2_result)
            part2_result["window"] = window_block(seen2)
            words = aa.markdown(part2_result, synthetic=synthetic)
    with paths["markdown"].open("a", encoding="utf-8") as f:
        f.write("\n" + window_words(result["window"]))
    result["paths"] = {k: str(v) for k, v in paths.items()}
    if part2_result is not None:
        json_path = out_dir / f"assist_{stamp_name}.json"
        write_json(json_path, part2_result)
        (out_dir / f"assist_{stamp_name}.md").write_text(
            words + "\n" + window_words(part2_result["window"]), encoding="utf-8"
        )
        part2_result["paths"] = {"json": str(json_path)}
    return {"part1": result, "part2": part2_result}


# ---------------------------------------------------------------------------
# Synthetic data: the four times, and the sittings the plan's rules drop
# ---------------------------------------------------------------------------


def _iso(ts: pd.Timestamp) -> str:
    return iso_utc(ts.to_pydatetime())


def make_synthetic(out: Path, *, seed: int = SYNTHETIC_SEED, n_per_arm: int = 42) -> Path:
    """Write a marked folder with all four files, made up. Deterministic from the seed.

    Part 1 is the real_gain scenario of evals/make_synthetic_sessions.py moved into the window,
    with the sittings its rules drop, and with the stored post_lock mark set as the server sets
    it: true for every sitting after the first lock. Six more sittings are from before the wave
    opened, three before the first lock and three after it. Part 2 is the helps scenario of
    evals/assist_analysis.py, each sitting placed after a finished part 1 sitting; four of them
    follow the six early sittings and must be left out.
    """
    sessions, responses = mss.generate("real_gain", seed=seed, n_per_arm=n_per_arm)
    start = pd.to_datetime(sessions["started_at_utc"], utc=True)
    done = pd.to_datetime(sessions["completed_at_utc"].replace("", None), utc=True)
    first = pd.Timestamp(FIRST_LOCK_UTC)
    span = (SECOND_LOCK_UTC - WAVE2_OPEN_UTC) / (FIRST_LOCK_UTC - mss.FIRST_START)
    moved = pd.Timestamp(WAVE2_OPEN_UTC) + (start - pd.Timestamp(mss.FIRST_START)) * span
    late = start >= first
    moved = moved.where(~late, pd.Timestamp(SECOND_LOCK_UTC) + (start - first))
    sessions["started_at_utc"] = [_iso(t) for t in moved]
    sessions["completed_at_utc"] = [
        "" if pd.isna(d) else _iso(m + (d - s)) for m, d, s in zip(moved, done, start, strict=True)
    ]
    sessions["post_lock"] = True

    early, early_responses = mss.generate(
        "real_gain", seed=seed + 1, n_per_arm=3, extras=mss.NO_EXTRAS
    )
    early_start = [FIRST_LOCK_UTC - timedelta(days=2) + timedelta(hours=i) for i in range(3)] + [
        FIRST_LOCK_UTC + timedelta(hours=6 + i) for i in range(3)
    ]
    early["started_at_utc"] = [iso_utc(t) for t in early_start]
    early["completed_at_utc"] = [iso_utc(t + timedelta(seconds=200)) for t in early_start]
    early["post_lock"] = [t >= FIRST_LOCK_UTC for t in early_start]

    with tempfile.TemporaryDirectory() as tmp:
        folder = aa.make_synthetic("helps", Path(tmp) / "helps", n_per_arm=30, seed=seed)
        part2 = pd.read_csv(folder / "part2_sessions.csv", dtype=str, keep_default_na=False)
        part2_responses = pd.read_csv(
            folder / "part2_responses.csv", dtype=str, keep_default_na=False
        )
    clean = sessions[
        (sessions["completed_at_utc"] != "")
        & ~sessions["is_test"]
        & ~sessions["hidden_field_filled"]
        & (pd.to_datetime(sessions["started_at_utc"], utc=True) < pd.Timestamp(SECOND_LOCK_UTC))
    ].drop_duplicates(subset=["client_token_hash"])
    before = pd.concat([early.head(4), clean], ignore_index=True)
    if len(before) < len(part2):
        raise ValueError("too few finished part 1 sittings to place the part 2 sittings after")
    for i in range(len(part2)):
        p1 = before.iloc[i]
        offered = pd.Timestamp(str(p1["completed_at_utc"])) + timedelta(seconds=10)
        started = part2.at[i, "started_at_utc"] != ""
        part2.at[i, "session_id"] = str(p1["session_id"])
        part2.at[i, "part1_arm"] = str(p1["arm"])
        part2.at[i, "client_token_hash"] = str(p1["client_token_hash"])
        part2.at[i, "offered_at_utc"] = _iso(offered)
        part2.at[i, "started_at_utc"] = _iso(offered) if started else ""
        part2.at[i, "completed_at_utc"] = _iso(offered + timedelta(seconds=90)) if started else ""
        part2.at[i, "post_lock"] = str(offered >= pd.Timestamp(FIRST_LOCK_UTC)).lower()

    out.mkdir(parents=True, exist_ok=True)
    pd.concat([early, sessions], ignore_index=True).to_csv(out / "sessions.csv", index=False)
    pd.concat([early_responses, responses], ignore_index=True).to_csv(
        out / "responses.csv", index=False
    )
    part2.to_csv(out / "part2_sessions.csv", index=False)
    part2_responses.to_csv(out / "part2_responses.csv", index=False)
    (out / SYNTHETIC_MARKER).write_text(
        f"SYNTHETIC data for the second wave, generated by {SCRIPT}, seed {seed}. "
        "Not from people.\n",
        encoding="utf-8",
    )
    return out


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def summary(result: dict[str, Any]) -> str:
    p = result["primary"]
    ci = p.get("ci95_points")
    ci_text = f"{ci[0]} to {ci[1]}" if ci else "n/a"
    return (
        f"{result['stamp']}: second wave, trained minus untrained {p.get('difference_points')} "
        f"points, 95 percent interval {ci_text}, permutation p {p.get('permutation_p')}, "
        f"status {p['status']} (n trained {p['n_trained']}, n untrained {p['n_untrained']})"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--synthetic", action="store_true", help="generate and analyse made up data"
    )
    parser.add_argument("--input", type=Path, default=None, help="folder with the export's files")
    parser.add_argument("--out-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--resamples", type=int, default=ua.N_BOOT)
    parser.add_argument("--permutations", type=int, default=ua.N_PERM)
    parser.add_argument(
        "--window", action="store_true", help="write results/wave2_window.json and stop"
    )
    parser.add_argument(
        "--check", action="store_true", help="with --window: write nothing, fail if it differs"
    )
    args = parser.parse_args(argv)

    if args.check and not args.window:
        print("The --check option only makes sense with --window.")
        return 2
    if args.window:
        if args.check:
            problems = window_differs()
            for line in problems:
                print(f"wave2-window: {line}")
            print("wave2-window: ok" if not problems else "wave2-window: run it without --check")
            return 1 if problems else 0
        if window_differs():
            write_json(WINDOW_FILE, window_record())
            print(f"wrote json: {WINDOW_FILE}")
        else:
            print(f"wave2-window: {WINDOW_FILE.name} is already what this script writes")
        return 0

    if args.synthetic:
        input_dir = args.input if args.input is not None else make_synthetic(SYNTHETIC_DIR)
        stamp_name = "w2_synthetic"
    else:
        input_dir = args.input if args.input is not None else EXPORT_DIR
        stamp_name = "w2_" + now_utc().strftime("%Y%m%d")

    reason = guard(input_dir, synthetic=args.synthetic)
    if reason:
        print(reason)
        return 3
    if not (input_dir / "sessions.csv").exists():
        print(f"No sessions.csv in {input_dir}.")
        return 4

    results = run(
        input_dir=input_dir,
        out_dir=args.out_dir,
        synthetic=args.synthetic,
        stamp_name=stamp_name,
        n_boot=args.resamples,
        n_perm=args.permutations,
        scenario="second_wave" if args.synthetic else None,
    )
    part1, part2 = results["part1"], results["part2"]
    print(summary(part1))
    print(f"wrote json: {part1['paths']['json']}")
    if part2 is None:
        print("part 2: the export holds no part 2 files, so nothing was analysed")
    else:
        print(f"part 2: {part2['readme_row']}")
        print(f"wrote part 2 json: {part2['paths']['json']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
