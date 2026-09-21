"""Small helpers shared by the W2 analysis scripts: paths, stamps and the 16 test items."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
SYNTHETIC_DIR = ROOT / "data" / "synthetic"
EXPORT_DIR = ROOT / "data" / "export"
TEST_ITEMS_PATH = ROOT / "content" / "test_items.yaml"

SYNTHETIC_STAMP = "SYNTHETIC"
PLAN_SEED = 20260920
N_ITEMS = 16
ITEMS_PER_FEATURE = 4

SESSION_COLUMNS = [
    "session_id",
    "arm",
    "block_id",
    "source_label",
    "ua_class",
    "consent_version",
    "content_hash",
    "build_hash",
    "started_at_utc",
    "lesson_seconds_total",
    "completed_at_utc",
    "test_seconds",
    "is_test",
    "post_lock",
    "hidden_field_filled",
    "client_token_hash",
    "prior_experience",
    "warmup_choice",
]
RESPONSE_COLUMNS = [
    "session_id",
    "item_id",
    "feature",
    "gold",
    "answer",
    "correct",
    "rt_ms",
    "position",
]

ARMS = ("untrained", "trained")


def now_utc() -> datetime:
    return datetime.now(UTC)


def iso_utc(ts: datetime) -> str:
    """ISO 8601 with a Z suffix, seconds precision."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(text: str) -> datetime:
    """Parse an ISO timestamp; a bare Z or a missing zone both mean UTC."""
    cleaned = text.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    ts = datetime.fromisoformat(cleaned)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def load_test_items(path: Path = TEST_ITEMS_PATH) -> list[dict[str, str]]:
    """The 16 items in file order: id, feature, photo_id, gold."""
    with path.open(encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    items = [dict(row) for row in doc["items"]]
    if len(items) != N_ITEMS:
        raise ValueError(f"expected {N_ITEMS} test items, found {len(items)}")
    return items


def result_header(
    script: str, *, synthetic: bool, stamp: str, when: datetime | None = None
) -> dict[str, Any]:
    """The fields every results JSON must carry (docs/CONTRACTS.md, results conventions)."""
    return {
        "generated_at_utc": iso_utc(when or now_utc()),
        "script": script,
        "synthetic": synthetic,
        "stamp": SYNTHETIC_STAMP if synthetic else stamp,
    }


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path


def chart_title(base: str, *, synthetic: bool) -> str:
    """Every synthetic chart title starts with SYNTHETIC."""
    return f"{SYNTHETIC_STAMP}: {base}" if synthetic else base


def round_or_none(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)
