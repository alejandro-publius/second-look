"""scripts/study_export.py: the export from a backup is what the live export route would give.

The parity test bundles worker/src/index.ts with esbuild, the way `npm test` in worker/ does,
hands its fetch handler a stand-in D1 that answers the export's two SELECTs with the rows SQLite
gave for the same backup, asks for /api/test/export and unzips what comes back. Both sides must
be equal byte for byte. Needs worker/node_modules (`cd worker && npm ci`), as make check does.
"""

from __future__ import annotations

import io
import json
import shutil
import sqlite3
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import pytest

from scripts import study_export as se

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "worker" / "schema.sql"
ESBUILD = ROOT / "worker" / "node_modules" / ".bin" / "esbuild"
TOKEN = "t" * 32


def study_items() -> list[str]:
    content = json.loads((ROOT / "worker" / "src" / "content.json").read_text())
    return [str(i["id"]) for i in content["test_items"]]


def session_row(sid: str, arm: str, **over: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": sid,
        "arm": arm,
        "block_id": 0,
        "item_order": "[]",
        "consent_version": "c3",
        "content_hash": "abc",
        "build_hash": "def",
        "consent_at": "2026-09-26T10:00:00.000Z",
        "started_at": "2026-09-26T10:00:00.000Z",
        "lesson_seconds": None,
        "completed_at": None,
        "client_token_hash": f"tok-{sid}",
        "ua_class": "phone",
        "is_test": 0,
        "source_label": "panel",
        "hidden_field_filled": 0,
        "post_lock": 0,
        "prior_experience": None,
        "warmup_choice": None,
        "unsent_count": 0,
    }
    row.update(over)
    return row


def make_dump(tmp_path: Path, sessions: list[dict[str, Any]], answers: dict[str, str]) -> Path:
    """A backup file in the shape `wrangler d1 export` writes, from made up rows."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA.read_text())
    for s in sessions:
        conn.execute(
            f"INSERT INTO session ({','.join(s)}) VALUES ({','.join('?' * len(s))})",
            list(s.values()),
        )
    items = study_items()
    for s in sessions:
        n = 16 if s.get("completed_at") else 5
        for pos, item in enumerate(items[:n]):
            conn.execute(
                "INSERT INTO response (session_id, item_id, answer, rt_ms, position, first_choice,"
                " t_first_ms, n_changes, received_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    s["id"],
                    item,
                    answers.get(s["id"], "yes") if pos % 3 else "cant_tell",
                    1200 + pos,
                    pos,
                    None if pos == 2 else "no",
                    None if pos == 4 else 700 + pos,
                    pos % 2,
                    f"2026-09-26T10:0{1 + pos // 10}:{10 + pos:02d}.{pos:03d}Z",
                ),
            )
    lines = ["PRAGMA defer_foreign_keys=TRUE;"]
    for line in conn.iterdump():
        if line in ("BEGIN TRANSACTION;", "COMMIT;"):
            continue
        lines.append(line)
    path = tmp_path / "second-look-20260928T011000Z.sql"
    path.write_text("\n".join(lines) + "\n")
    return path


def sample_sessions() -> list[dict[str, Any]]:
    done = "2026-09-26T10:03:02.999Z"
    return [
        session_row(
            "a1",
            "trained",
            completed_at=done,
            lesson_seconds=json.dumps({"lesson_b": 12.3, "1": 4.05, "0": 0.1, "x": None}),
            prior_experience="no",
            warmup_choice="left",
        ),
        session_row(
            "a2",
            "untrained",
            completed_at=done,
            source_label="other",
            lesson_seconds="{}",
            started_at="2026-09-26T09:00:00.000Z",
            content_hash='has "quotes", a comma',
        ),
        session_row("a3", "trained", is_test=1, completed_at=done, ua_class="desktop"),
        session_row("a4", "untrained", lesson_seconds=json.dumps({"l1": 0.05, "l2": 0.25})),
    ]


def worker_export(
    tmp_path: Path,
    sessions: list[dict],
    responses: list[dict],
    part2: tuple[list[dict], list[dict]] = ([], []),
) -> tuple[str, str]:
    """What the Worker's own export route writes for these rows."""
    bundle = tmp_path / "worker.mjs"
    subprocess.run(
        [
            str(ESBUILD),
            str(ROOT / "worker" / "src" / "index.ts"),
            "--bundle",
            "--platform=node",
            "--format=esm",
            f"--outfile={bundle}",
            "--log-level=warning",
        ],
        check=True,
        cwd=ROOT / "worker",
    )
    data = tmp_path / "rows.json"
    data.write_text(
        json.dumps(
            {
                "sessions": sessions,
                "responses": responses,
                "part2_sessions": part2[0],
                "part2_responses": part2[1],
            }
        )
    )
    harness = tmp_path / "harness.mjs"
    harness.write_text(
        f"""
import {{ readFileSync, writeFileSync }} from "node:fs";
import worker from {json.dumps(str(bundle))};
const rows = JSON.parse(readFileSync({json.dumps(str(data))}, "utf8"));
const statement = (sql) => ({{
  bind() {{ return this; }},
  async all() {{
    if (sql === {json.dumps(se.SESSIONS_SQL)}) return {{ results: rows.sessions }};
    if (sql === {json.dumps(se.RESPONSES_SQL)}) return {{ results: rows.responses }};
    if (sql === {json.dumps(se.PART2_SESSIONS_SQL)}) return {{ results: rows.part2_sessions }};
    if (sql === {json.dumps(se.PART2_RESPONSES_SQL)}) return {{ results: rows.part2_responses }};
    throw new Error("unexpected query: " + sql);
  }},
  async first() {{ throw new Error("unexpected first: " + sql); }},
  async run() {{ throw new Error("unexpected run: " + sql); }},
}});
const env = {{ DB: {{ prepare: statement }}, EXPORT_TOKEN: {json.dumps(TOKEN)} }};
const res = await worker.fetch(
  new Request("https://example.test/api/test/export?token={TOKEN}"), env);
if (res.status !== 200) throw new Error("export answered " + res.status);
writeFileSync({json.dumps(str(tmp_path / "export.zip"))}, Buffer.from(await res.arrayBuffer()));
"""
    )
    subprocess.run(["node", str(harness)], check=True, capture_output=True, text=True)
    with zipfile.ZipFile(io.BytesIO((tmp_path / "export.zip").read_bytes())) as zf:
        (tmp_path / "part2_sessions.csv").write_bytes(zf.read("part2_sessions.csv"))
        (tmp_path / "part2_responses.csv").write_bytes(zf.read("part2_responses.csv"))
        return zf.read("sessions.csv").decode(), zf.read("responses.csv").decode()


@pytest.mark.skipif(not ESBUILD.exists(), reason="run (cd worker && npm ci) first")
@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_the_export_from_a_backup_is_the_live_routes_export_byte_for_byte(tmp_path: Path) -> None:
    dump = make_dump(tmp_path, sample_sessions(), {"a1": "yes", "a2": "no"})
    conn = se.load_dump(dump)
    sessions, responses = se.rows(conn)
    ours = se.export_texts(sessions, responses)
    theirs = worker_export(tmp_path, sessions, responses)
    assert ours[0] == theirs[0]
    assert ours[1] == theirs[1]
    # The rows cover what makes the two languages differ: a sum of tenths, number-like keys, a
    # null, halves that Math.round sends up, quotes and a comma, and missing values.
    assert '"has ""quotes"", a comma"' in ours[0]
    assert ",16.5," in ours[0] and ",0.3," in ours[0]


def test_export_writes_both_files_with_the_workers_line_ends(tmp_path: Path) -> None:
    dump = make_dump(tmp_path, sample_sessions(), {})
    counts = se.export(dump, tmp_path / "export")
    assert counts == {
        "sessions": 4,
        "responses": 16 * 3 + 5,
        "part2_sessions": 0,
        "part2_responses": 0,
    }
    raw = (tmp_path / "export" / "sessions.csv").read_bytes()
    assert raw.startswith(b"session_id,arm,block_id,") and raw.endswith(b"\r\n")
    assert raw.count(b"\r\n") == 5
    header = (tmp_path / "export" / "responses.csv").read_text().splitlines()[0]
    assert header.split(",") == se.RESPONSE_HEAD


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (12.0, "12"),
        (0.1 + 0.2, "0.30000000000000004"),
        (1e-7, "1e-7"),
        (0.000001, "0.000001"),
        (1e21, "1e+21"),
        (123456789012345680000.0, "123456789012345680000"),
        (-2.5, "-2.5"),
        (float("nan"), "NaN"),
    ],
)
def test_numbers_are_written_as_javascript_writes_them(value: float, text: str) -> None:
    assert se.js_number(value) == text


def test_math_round_sends_halves_up_like_javascript() -> None:
    assert se.js_round(2.5) == 3.0 and se.js_round(-2.5) == -2.0 and se.js_round(0.5) == 1.0


def part2_sample(conn: sqlite3.Connection) -> None:
    """Part 2 rows that cover a decline, both arms, a pending question, Keep and Change."""
    rows = [
        ("p1", "a1", "trained", "assisted", 0, '["a01","a02"]', "2026-09-26T10:05:00Z", 0,
         "2026-09-26T10:05:00Z", "2026-09-26T10:06:31.450Z", "tok1", 0, 0),
        ("p2", "a2", "untrained", None, None, None, "2026-09-26T09:05:00Z", 1, None, None,
         "tok2", 0, 0),
        ("p3", "a3", "trained", "unassisted", -1, '["a01"]', "2026-09-26T11:00:00Z", 0,
         "2026-09-26T11:00:00Z", None, "tok3", 1, 0),
    ]  # fmt: skip
    conn.executemany(f"INSERT INTO part2_session VALUES ({','.join('?' * 13)})", rows)
    answers = [
        ("p1", "a01", 0, "no", "no", 1, "keep", 4000, 6100, "2026-09-26T10:05:10.100Z"),
        ("p1", "a02", 1, "no", "yes", 1, "change", 3000, 5000, "2026-09-26T10:05:20.000Z"),
        ("p1", "a03", 2, "cant_tell", None, 1, "", 2500, None, "2026-09-26T10:05:30.000Z"),
        ("p3", "a01", 0, "yes", "yes", 0, "", 900, 900, "2026-09-26T11:00:05.000Z"),
    ]  # fmt: skip
    conn.executemany(f"INSERT INTO part2_response VALUES ({','.join('?' * 10)})", answers)


@pytest.mark.skipif(not ESBUILD.exists(), reason="run (cd worker && npm ci) first")
@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_part2_files_from_a_backup_are_the_live_routes_byte_for_byte(tmp_path: Path) -> None:
    conn = se.load_dump(make_dump(tmp_path, sample_sessions(), {}))
    part2_sample(conn)
    sessions, responses = se.rows(conn)
    part2 = se.part2_rows(conn)
    assert part2 is not None
    ours = se.part2_export_texts(*part2)
    worker_export(tmp_path, sessions, responses, part2)
    assert ours[0] == (tmp_path / "part2_sessions.csv").read_bytes().decode()
    assert ours[1] == (tmp_path / "part2_responses.csv").read_bytes().decode()
    assert ",81.4," in ours[0] and "p2,a2,untrained,,,2026-09-26T09:05:00Z,1," in ours[0]
    assert ours[0].splitlines()[0].split(",") == se.PART2_SESSION_HEAD


def test_a_backup_from_before_part2_has_no_part2_files(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    assert se.part2_rows(conn) is None
