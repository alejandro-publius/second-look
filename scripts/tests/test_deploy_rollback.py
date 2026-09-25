"""The deploy record in docs/notes/hosting.md, scripts/deploy.sh writing it, and make rollback.

Nothing here deploys: scripts/deploy.sh runs with stand-ins for npx, npm and uv on PATH, and
make rollback runs with scripts/tests/fake_outward.py in place of the real outward layer. A
rollback was never tried against a Pages preview, because a preview's API is the production
Worker and the rules for this work forbid any deploy.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import deploy_record as dr
from scripts import rollback as rb
from scripts.outward import Done, Reply
from scripts.tests.fake_outward import FakeOutward

ROOT = Path(__file__).resolve().parents[2]
V1, V2, V3 = (f"{n}{n}{n}{n}{n}{n}{n}{n}-0000-4000-8000-00000000000{n}" for n in (1, 2, 3))
WRANGLER_DEPLOY = f"Uploaded second-look-api (3.1 sec)\nCurrent Version ID: {V3}\n"
PAGES_DEPLOY = (
    "Deployment complete! Take a peek over at https://ab12cd34.second-look-79t.pages.dev\n"
)


@pytest.fixture
def hosting(tmp_path: Path) -> Path:
    path = tmp_path / "hosting.md"
    path.write_text(
        "# Hosting\n\nBefore.\n\n"
        + dr.START
        + "\n"
        + dr.HEAD
        + "\n"
        + dr.RULE
        + "\n"
        + dr.END
        + "\n\nAfter.\n"
    )
    return path


def web_dir(tmp_path: Path) -> Path:
    web = tmp_path / "web"
    (web / "out").mkdir(parents=True)
    (web / "out" / "index.html").write_text("<title>Second Look</title>")
    (web / "functions" / "api").mkdir(parents=True)
    (web / "functions" / "api" / "[[path]].js").write_text("export default {}")
    (web / "wrangler.jsonc").write_text('{"name": "second-look"}')
    return web


def test_the_real_hosting_notes_carry_the_block_and_it_reads() -> None:
    assert dr.load() == [] or all(r.part in dr.PARTS for r in dr.load())


def test_a_worker_deploy_is_recorded_with_its_version_and_unchecked(hosting: Path) -> None:
    row = dr.record(
        "worker", WRANGLER_DEPLOY, commit="abc1234", when="2026-09-28T01:30:00Z", hosting=hosting
    )
    assert row == dr.Row("2026-09-28T01:30:00Z", "worker", "abc1234", V3, "", False)
    text = hosting.read_text()
    assert text.startswith("# Hosting\n\nBefore.") and text.endswith("After.\n")
    assert dr.load(hosting) == [row]


def test_a_site_deploy_keeps_the_files_that_went_up(
    hosting: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    archives = tmp_path / "second-look-backups" / "deploys"
    row = dr.record(
        "web", PAGES_DEPLOY, commit="abc1234", when="2026-09-28T01:40:00Z",
        hosting=hosting, web_dir=web_dir(tmp_path), archives=archives,
    )  # fmt: skip
    assert row.id == "ab12cd34" and not row.checked
    assert row.archive.startswith("~/second-look-backups/deploys/web-")
    kept = dr.expand(row.archive)
    assert (kept / "out" / "index.html").read_text() == "<title>Second Look</title>"
    assert (kept / "functions" / "api" / "[[path]].js").exists()
    assert (kept / "wrangler.jsonc").exists() and (kept / "COMMIT").read_text() == "abc1234\n"


def test_output_without_an_id_is_refused(hosting: Path) -> None:
    with pytest.raises(dr.RecordError):
        dr.record("worker", "Uploaded, no id here", commit="a", when="t", hosting=hosting)
    with pytest.raises(dr.RecordError):
        dr.pages_deployment("https://second-look-79t.pages.dev only the alias")


def test_good_marks_only_the_newest_commits_rows() -> None:
    rows = [
        dr.Row("t3", "web", "ccc3333", "c3", "", False),
        dr.Row("t3", "worker", "ccc3333", V3, "", False),
        dr.Row("t2", "worker", "bbb2222", V2, "", False),
    ]
    marked = dr.mark_good(rows)
    assert [r.checked for r in marked] == [True, True, False]


def rows_with_archives(tmp_path: Path) -> list[dr.Row]:
    a1, a2, a3 = (tmp_path / f"web-{n}" for n in (1, 2, 3))
    for a in (a1, a2, a3):
        (a / "out").mkdir(parents=True)
    return [
        dr.Row("t3", "web", "ccc3333", "c3", str(a3), False),
        dr.Row("t3", "worker", "ccc3333", V3, "", False),
        dr.Row("t2", "web", "bbb2222", "b2", str(a2), True),
        dr.Row("t2", "worker", "bbb2222", V2, "", True),
        dr.Row("t1", "web", "aaa1111", "a1", str(a1), True),
        dr.Row("t1", "worker", "aaa1111", V1, "", True),
    ]


def test_rollback_goes_to_the_newest_good_row_that_is_not_live(tmp_path: Path) -> None:
    rows = rows_with_archives(tmp_path)
    plan = rb.plan(rows, V3, {"id": "c3", "commit": "ccc3333"})
    assert [(s.part, s.row.id) for s in plan.steps] == [("worker", V2), ("web", "b2")]
    worker, web = plan.steps
    assert worker.argv[:4] == ["npx", "wrangler", "rollback", V2]
    assert web.cwd == tmp_path / "web-2"
    assert web.argv[:4] == ["npx", "wrangler", "pages", "deploy"]
    assert web.argv[web.argv.index("--commit-hash") + 1] == "bbb2222"
    # Live is already the newest good row: go one further back.
    again = rb.plan(rows, V2, {"id": "x", "commit": "bbb2222"})
    assert [s.row.id for s in again.steps] == [V1, "a1"]


def test_rollback_never_picks_a_build_whose_files_are_gone(tmp_path: Path) -> None:
    rows = rows_with_archives(tmp_path)
    shutil.rmtree(tmp_path / "web-2")
    plan = rb.plan(rows, V3, {"id": "c3", "commit": "ccc3333"}, only="web")
    assert [s.row.id for s in plan.steps] == ["a1"]
    shutil.rmtree(tmp_path / "web-1")
    plan = rb.plan(rows, V3, {"id": "c3", "commit": "ccc3333"}, only="web")
    assert plan.steps == [] and any("nothing to go back to" in n for n in plan.notes)


def fake_live(out: FakeOutward, worker: str, commit: str) -> None:
    out.answer(
        ["npx", "wrangler", "deployments"],
        Done(0, json.dumps({"versions": [{"version_id": worker, "percentage": 100}]})),
    )
    listed = {
        "Id": "c3000000-1",
        "Source": commit,
        "Deployment": f"https://c3000000.{dr.PAGES_HOST}",
    }
    out.answer(["npx", "wrangler", "pages", "deployment", "list"], Done(0, json.dumps([listed])))


def test_make_rollback_is_a_dry_run_unless_told_yes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(dr, "load", lambda path=dr.HOSTING: rows_with_archives(tmp_path))
    out = FakeOutward()
    fake_live(out, V3, "ccc3333")
    assert rb.main([], out=out) == 0
    printed = capsys.readouterr().out
    assert f"would worker: back to {V2}" in printed and "would web: back to b2" in printed
    assert "dry run, nothing changed" in printed
    assert not out.ran("npx", "wrangler", "rollback") and not out.ran(
        "npx", "wrangler", "pages", "deploy"
    )
    assert out.fetched == []


def test_make_rollback_yes_redeploys_both_and_reads_health(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dr, "load", lambda path=dr.HOSTING: rows_with_archives(tmp_path))
    out = FakeOutward()
    fake_live(out, V3, "ccc3333")
    out.pages[f"{rb.SITE}/health"] = Reply(200, '{"status":"ok"}')
    assert rb.main(["--yes"], out=out) == 0
    assert out.ran("npx", "wrangler", "rollback", V2)
    deploys = out.ran("npx", "wrangler", "pages", "deploy")
    assert len(deploys) == 1
    assert out.cwds[out.calls.index(deploys[0])] == tmp_path / "web-2"
    assert out.fetched == [("GET", f"{rb.SITE}/health")]


def test_a_failed_rollback_step_says_so_and_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dr, "load", lambda path=dr.HOSTING: rows_with_archives(tmp_path))
    out = FakeOutward()
    fake_live(out, V3, "ccc3333")
    out.answer(["npx", "wrangler", "rollback"], Done(1, "", "version not found"))
    out.pages[f"{rb.SITE}/health"] = Reply(200, "{}")
    assert rb.main(["--yes"], out=out) == 1


def test_check_live_needs_good_rows_for_both_parts_with_files_kept(tmp_path: Path) -> None:
    rows = rows_with_archives(tmp_path)
    w, p, problems = dr.good_for_live(rows, V2, {"id": "b2", "commit": "bbb2222"})
    assert problems == [] and w and p and p.id == "b2"
    _, _, problems = dr.good_for_live(rows, V3, {"id": "c3", "commit": "ccc3333"})
    assert len(problems) == 2
    shutil.rmtree(tmp_path / "web-2")
    _, _, problems = dr.good_for_live(rows, V2, {"id": "b2", "commit": "bbb2222"})
    assert problems and "files kept" in problems[0]


# ---------------------------------------------------------------------------
# scripts/deploy.sh records every deploy
# ---------------------------------------------------------------------------


def stand_ins(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    (bin_dir / "npx").write_text(
        "#!/bin/sh\n"
        f'echo "npx $*" >> "{log}"\n'
        'case "$*" in\n'
        f'  "wrangler deploy") printf "%s" "{WRANGLER_DEPLOY}" ;;\n'
        f'  "wrangler pages deploy"*) printf "%s" "{PAGES_DEPLOY}" ;;\n'
        "esac\n"
    )
    (bin_dir / "npm").write_text(f'#!/bin/sh\necho "npm $*" >> "{log}"\n')
    # uv: log the call, and for the recorder also what wrangler printed into its output file.
    (bin_dir / "uv").write_text(
        "#!/bin/sh\n"
        f'echo "uv $*" >> "{log}"\n'
        'while [ $# -gt 0 ]; do if [ "$1" = "--output-file" ]; then '
        f'cat "$2" >> "{log}"; fi; shift; done\n'
    )
    for f in bin_dir.iterdir():
        f.chmod(0o755)
    return {**os.environ, "PATH": f"{bin_dir}:/usr/bin:/bin", "ALLOW_BRANCH": "yes"}


@pytest.mark.parametrize(
    ("part", "deploy_words", "printed"),
    [("worker", "npx wrangler deploy", V3), ("web", "npx wrangler pages deploy out", "ab12cd34")],
)
def test_deploy_sh_records_each_deploy_right_after_it(
    tmp_path: Path, part: str, deploy_words: str, printed: str
) -> None:
    env = stand_ins(tmp_path)
    proc = subprocess.run(
        ["bash", str(ROOT / "scripts" / "deploy.sh"), part],
        env=env,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = (tmp_path / "calls.log").read_text().splitlines()
    deployed = next(i for i, c in enumerate(calls) if c.startswith(deploy_words))
    recorded = next(
        i for i, c in enumerate(calls) if f"scripts/deploy_record.py record {part}" in c
    )
    assert deployed < recorded
    assert any(printed in c for c in calls[recorded:]), (
        "the recorder was not given wrangler's output"
    )
