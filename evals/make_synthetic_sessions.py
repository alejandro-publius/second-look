"""Write fake usability sessions in the export schema from docs/CONTRACTS.md.

Five scenarios, all seeded:

- no_effect: both arms answer about 60 percent of items correctly.
- real_gain: the trained arm is about 10 points more accurate.
- yes_bias: the trained arm says Yes more often but is no more accurate.
- skill_spread: people differ a lot in skill from feature to feature.
- equal_skill: everyone in an arm has the same skill on every feature.

Every scenario also contains sessions the analysis must throw out: unfinished sessions,
tests done in under 40 seconds, repeat visits from one browser token, QA sessions,
sessions that filled the hidden field, and sessions stored after the data lock.

Usage: uv run python evals/make_synthetic_sessions.py [--scenario NAME] [--out DIR] [--seed N]
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from core.lock import DATA_LOCK_UTC
from evals.common import (
    ARMS,
    ITEMS_PER_FEATURE,
    N_ITEMS,
    PLAN_SEED,
    RESPONSE_COLUMNS,
    SESSION_COLUMNS,
    SYNTHETIC_DIR,
    iso_utc,
    load_test_items,
)

SCENARIOS = ("no_effect", "real_gain", "yes_bias", "skill_spread", "equal_skill")

# Answer codes used inside the simulation.
YES, NO, CANT_TELL = 0, 1, 2
ANSWER_TEXT = {YES: "yes", NO: "no", CANT_TELL: "cant_tell"}

FIRST_START = datetime(2026, 9, 23, 17, 0, 0, tzinfo=DATA_LOCK_UTC.tzinfo)
STUDY_HOURS = 100  # sessions start inside about four days
SOURCES = ("poster", "chat", "friends", "creek_group", "other")
SOURCE_WEIGHTS = (0.25, 0.30, 0.25, 0.10, 0.10)
DEVICES = ("phone", "desktop", "tablet")
DEVICE_WEIGHTS = (0.65, 0.30, 0.05)
CONTENT_HASH = hashlib.sha256(b"synthetic content").hexdigest()[:16]
BUILD_HASH = hashlib.sha256(b"synthetic build").hexdigest()[:12]


@dataclass(frozen=True)
class ScenarioSpec:
    """How each arm answers. Skill is the chance of a correct answer on one item."""

    name: str
    untrained_mean: float
    trained_mean: float
    person_sd: float  # between-person spread of skill, shared across features
    feature_sd: float  # extra spread of one person's skill from feature to feature
    yes_bias: float  # chance a trained-arm answer is forced to Yes, whatever the skill
    cant_tell_rate: float = 0.20  # share of wrong answers that come out as Can't tell
    item_sd: float = 0.06  # item difficulty spread, same for both arms


SPECS: dict[str, ScenarioSpec] = {
    "no_effect": ScenarioSpec("no_effect", 0.60, 0.60, 0.10, 0.05, 0.0),
    "real_gain": ScenarioSpec("real_gain", 0.60, 0.70, 0.10, 0.05, 0.0),
    "yes_bias": ScenarioSpec("yes_bias", 0.60, 0.60, 0.10, 0.05, 0.25),
    "skill_spread": ScenarioSpec("skill_spread", 0.60, 0.70, 0.15, 0.22, 0.0),
    "equal_skill": ScenarioSpec("equal_skill", 0.60, 0.70, 0.0, 0.0, 0.0),
}


@dataclass(frozen=True)
class ExtraCounts:
    """How many sessions of each kind the analysis must remove."""

    incomplete_no_answers: int = 4
    incomplete_partial: int = 4
    fast: int = 3
    repeat_token: int = 4
    qa: int = 2
    hidden_field: int = 2
    post_lock: int = 3

    def total(self) -> int:
        return (
            self.incomplete_no_answers
            + self.incomplete_partial
            + self.fast
            + self.repeat_token
            + self.qa
            + self.hidden_field
            + self.post_lock
        )


NO_EXTRAS = ExtraCounts(0, 0, 0, 0, 0, 0, 0)
DEFAULT_EXTRAS = ExtraCounts()


def item_offsets(spec: ScenarioSpec, rng: np.random.Generator) -> np.ndarray:
    """Per-item difficulty shift, drawn once per data set and shared by both arms."""
    if spec.item_sd == 0:
        return np.zeros(N_ITEMS)
    return rng.normal(0.0, spec.item_sd, size=N_ITEMS)


def skill_matrix(
    spec: ScenarioSpec, arm: str, n: int, rng: np.random.Generator, offsets: np.ndarray
) -> np.ndarray:
    """n by 16 matrix of the chance of a correct answer on each item."""
    mean = spec.trained_mean if arm == "trained" else spec.untrained_mean
    person = (
        rng.normal(0.0, spec.person_sd, size=(n, 1)) if spec.person_sd > 0 else np.zeros((n, 1))
    )
    n_features = N_ITEMS // ITEMS_PER_FEATURE
    if spec.feature_sd > 0:
        per_feature = rng.normal(0.0, spec.feature_sd, size=(n, n_features))
    else:
        per_feature = np.zeros((n, n_features))
    feature_of_item = np.repeat(np.arange(n_features), ITEMS_PER_FEATURE)
    skill = mean + person + per_feature[:, feature_of_item] + offsets[None, :]
    return np.clip(skill, 0.03, 0.98)


def simulate_answers(
    spec: ScenarioSpec,
    arm: str,
    n: int,
    rng: np.random.Generator,
    offsets: np.ndarray,
    gold_present: np.ndarray,
) -> np.ndarray:
    """n by 16 matrix of answer codes (YES, NO, CANT_TELL)."""
    skill = skill_matrix(spec, arm, n, rng, offsets)
    correct = rng.random(size=(n, N_ITEMS)) < skill
    cant_tell = rng.random(size=(n, N_ITEMS)) < spec.cant_tell_rate
    right_answer = np.where(gold_present[None, :], YES, NO)
    wrong_answer = np.where(gold_present[None, :], NO, YES)
    answers = np.where(correct, right_answer, np.where(cant_tell, CANT_TELL, wrong_answer))
    if arm == "trained" and spec.yes_bias > 0:
        forced = rng.random(size=(n, N_ITEMS)) < spec.yes_bias
        answers = np.where(forced, YES, answers)
    return answers


def accuracy_from_answers(answers: np.ndarray, gold_present: np.ndarray) -> np.ndarray:
    """Share of 16 items right per row. Can't tell counts as wrong."""
    right_answer = np.where(gold_present[None, :], YES, NO)
    return (answers == right_answer).mean(axis=1)


def simulate_accuracy(scenario: str, n_per_arm: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Quick path for tests: (untrained accuracies, trained accuracies), no CSV shapes."""
    spec = SPECS[scenario]
    rng = np.random.default_rng(seed)
    gold_present = np.array([row["gold"] == "present" for row in load_test_items()])
    offsets = item_offsets(spec, rng)
    untrained = simulate_answers(spec, "untrained", n_per_arm, rng, offsets, gold_present)
    trained = simulate_answers(spec, "trained", n_per_arm, rng, offsets, gold_present)
    return accuracy_from_answers(untrained, gold_present), accuracy_from_answers(
        trained, gold_present
    )


def permuted_block_arms(n: int, rng: np.random.Generator, block: int = 4) -> list[tuple[str, int]]:
    """Arm and block id for n sessions, two of each arm inside every block of four."""
    out: list[tuple[str, int]] = []
    n_blocks = math.ceil(n / block)
    for b in range(n_blocks):
        arms = [ARMS[0]] * (block // 2) + [ARMS[1]] * (block // 2)
        rng.shuffle(arms)
        out.extend((arm, b) for arm in arms)
    return out[:n]


def _token(rng: np.random.Generator) -> str:
    return hashlib.sha256(rng.bytes(16)).hexdigest()


def _session_id(rng: np.random.Generator) -> str:
    return "s-" + rng.bytes(8).hex()


def generate(
    scenario: str,
    *,
    seed: int = PLAN_SEED,
    n_per_arm: int = 42,
    extras: ExtraCounts = DEFAULT_EXTRAS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sessions and responses for one scenario, in the export schema and column order."""
    if scenario not in SPECS:
        raise ValueError(f"unknown scenario {scenario!r}; pick one of {', '.join(SCENARIOS)}")
    spec = SPECS[scenario]
    rng = np.random.default_rng(seed)
    items = load_test_items()
    gold_present = np.array([row["gold"] == "present" for row in items])
    offsets = item_offsets(spec, rng)

    # Build the list of session kinds, then shuffle so the kinds are spread over the timeline.
    kinds: list[str] = ["clean"] * (2 * n_per_arm)
    kinds += ["incomplete_none"] * extras.incomplete_no_answers
    kinds += ["incomplete_partial"] * extras.incomplete_partial
    kinds += ["fast"] * extras.fast
    kinds += ["repeat"] * extras.repeat_token
    kinds += ["qa"] * extras.qa
    kinds += ["hidden"] * extras.hidden_field
    kinds_arr = np.array(kinds)
    rng.shuffle(kinds_arr)
    kinds = [str(k) for k in kinds_arr]
    # A repeat visit needs an earlier clean session to copy a token from, so a clean one leads.
    if kinds and kinds[0] != "clean" and "clean" in kinds:
        first_clean = kinds.index("clean")
        kinds[0], kinds[first_clean] = kinds[first_clean], kinds[0]
    kinds += ["post_lock"] * extras.post_lock

    n_total = len(kinds)
    assignment = permuted_block_arms(n_total, rng)
    start_hours = np.sort(rng.uniform(0, STUDY_HOURS, size=n_total))

    session_rows: list[dict[str, object]] = []
    response_rows: list[dict[str, object]] = []
    clean_tokens: list[str] = []

    for idx, kind in enumerate(kinds):
        arm, block_id = assignment[idx]
        sid = _session_id(rng)
        if kind == "repeat" and clean_tokens:
            token = str(rng.choice(clean_tokens))
        else:
            token = _token(rng)
        if kind == "clean":
            clean_tokens.append(token)

        if kind == "post_lock":
            started = DATA_LOCK_UTC + timedelta(minutes=float(rng.uniform(1, 600)))
        else:
            started = FIRST_START + timedelta(hours=float(start_hours[idx]))
            started = min(started, DATA_LOCK_UTC - timedelta(minutes=5))

        lesson_seconds: float | None
        if arm == "trained":
            lesson_seconds = float(rng.lognormal(math.log(130), 0.30))
        elif rng.random() < 0.55:
            lesson_seconds = float(rng.lognormal(math.log(95), 0.35))  # offered after the test
        else:
            lesson_seconds = 0.0

        if kind == "fast":
            test_seconds = float(rng.uniform(18, 36))
        else:
            test_seconds = float(rng.lognormal(math.log(115), 0.30))
        test_seconds = max(test_seconds, 12.0)

        answers = simulate_answers(spec, arm, 1, rng, offsets, gold_present)[0]
        if kind == "incomplete_none":
            n_answered = 0
        elif kind == "incomplete_partial":
            n_answered = int(rng.integers(1, N_ITEMS))
        else:
            n_answered = N_ITEMS
        completed = n_answered == N_ITEMS

        order = rng.permutation(N_ITEMS)
        for position, item_idx in enumerate(order[:n_answered], start=1):
            item = items[item_idx]
            answer = ANSWER_TEXT[int(answers[item_idx])]
            correct = int(
                (answer == "yes" and item["gold"] == "present")
                or (answer == "no" and item["gold"] == "absent")
            )
            response_rows.append(
                {
                    "session_id": sid,
                    "item_id": item["id"],
                    "feature": item["feature"],
                    "gold": item["gold"],
                    "answer": answer,
                    "correct": correct,
                    "rt_ms": int(rng.lognormal(math.log(5500), 0.5)),
                    "position": position,
                }
            )

        consent_seconds = float(rng.uniform(10, 40))
        lesson_before = lesson_seconds if arm == "trained" else 0.0
        finish = started + timedelta(seconds=consent_seconds + lesson_before + test_seconds)
        prior_roll = rng.random()
        prior = "yes" if prior_roll < 0.20 else ("" if prior_roll < 0.30 else "no")
        session_rows.append(
            {
                "session_id": sid,
                "arm": arm,
                "block_id": block_id,
                "source_label": str(rng.choice(SOURCES, p=SOURCE_WEIGHTS)),
                "ua_class": str(rng.choice(DEVICES, p=DEVICE_WEIGHTS)),
                "consent_version": "v1",
                "content_hash": CONTENT_HASH,
                "build_hash": BUILD_HASH,
                "started_at_utc": iso_utc(started),
                "lesson_seconds_total": round(lesson_seconds, 1),
                "completed_at_utc": iso_utc(finish) if completed else "",
                "test_seconds": round(test_seconds, 1) if completed else "",
                "is_test": kind == "qa",
                "post_lock": kind == "post_lock",
                "hidden_field_filled": kind == "hidden",
                "client_token_hash": token,
                "prior_experience": prior if completed else "",
                "warmup_choice": "w02" if rng.random() < 0.62 else "w01",
            }
        )

    sessions = pd.DataFrame(session_rows, columns=SESSION_COLUMNS)
    responses = pd.DataFrame(response_rows, columns=RESPONSE_COLUMNS)
    return sessions, responses


def write_scenario(
    scenario: str, out_root: Path, *, seed: int = PLAN_SEED, n_per_arm: int = 42
) -> Path:
    """Write sessions.csv and responses.csv under out_root/<scenario>/."""
    sessions, responses = generate(scenario, seed=seed, n_per_arm=n_per_arm)
    out_dir = out_root / scenario
    out_dir.mkdir(parents=True, exist_ok=True)
    sessions.to_csv(out_dir / "sessions.csv", index=False)
    responses.to_csv(out_dir / "responses.csv", index=False)
    (out_dir / "SYNTHETIC.txt").write_text(
        f"SYNTHETIC data, scenario {scenario}, seed {seed}. Not from people.\n", encoding="utf-8"
    )
    return out_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--scenario", choices=SCENARIOS, default=None, help="default: all five")
    parser.add_argument("--out", type=Path, default=SYNTHETIC_DIR)
    parser.add_argument("--seed", type=int, default=PLAN_SEED)
    parser.add_argument(
        "--n-per-arm", type=int, default=42, help="clean completed sessions per arm"
    )
    args = parser.parse_args(argv)
    names = [args.scenario] if args.scenario else list(SCENARIOS)
    for name in names:
        out_dir = write_scenario(name, args.out, seed=args.seed, n_per_arm=args.n_per_arm)
        sessions = pd.read_csv(out_dir / "sessions.csv")
        print(f"wrote {out_dir}: {len(sessions)} sessions (SYNTHETIC, seed {args.seed})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
