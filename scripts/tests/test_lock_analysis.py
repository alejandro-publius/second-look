"""The data lock job, the whole chain, on a copy of a database with the clock set in the test.

The checkout is a throwaway clone of a throwaway bare repository, so git fetch, commit and the
atomic push are real, and "origin" is a folder. The database is a backup file in the shape
`wrangler d1 export` writes, made from worker/schema.sql and made up sessions. Everything else
that would leave the machine goes through scripts/tests/fake_outward.py, which plays wrangler,
the phone checks and production. make check, the report build and the contract tests are stood
in for; the export and the pre-registered analysis run for real, in this process, with the clock
set after the lock. With the real clock the job refuses before the lock, which the last tests
show from a separate process too.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import evals.assist_analysis as aa
import evals.common as common
import evals.usability_analysis as ua
from core.lock import DATA_LOCK_UTC
from scripts import audit_log, render_readme
from scripts import deploy_record as dr
from scripts import lock_analysis as la
from scripts.outward import Done, Reply
from scripts.tests.fake_outward import FakeOutward
from scripts.tests.test_study_export import make_dump, sample_sessions, session_row

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 9, 28, 1, 10, 0, tzinfo=UTC)
V1 = "11111111-0000-4000-8000-000000000001"
V2 = "22222222-0000-4000-8000-000000000002"
README = f"""# Second Look

## Numbers at a glance

**The result, in short.** Models took the test. {la.NOBODY_YET}

The full loop, from a desk.

{la.HUMAN_LEAD}: it is the volunteer's own calibration step. No session has arrived yet.

{la.PART2_START}
Does the checker's question help? Part 2 is analysed once, after the data lock.
{la.PART2_END}

## Gallery
"""


def git(cwd: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        GIT_AUTHOR_NAME="t",
        GIT_AUTHOR_EMAIL="t@t",
        GIT_COMMITTER_NAME="t",
        GIT_COMMITTER_EMAIL="t@t",
    )
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True
    ).stdout.strip()


class World:
    """The checkout, its origin, the backups folder, and production as the fake plays it."""

    def __init__(self, tmp: Path, sessions: list[dict[str, Any]]) -> None:
        self.tmp = tmp
        self.origin = tmp / "origin.git"
        self.root = tmp / "checkout"
        self.backups = tmp / "second-look-backups"
        self.archives = self.backups / "deploys"
        git(tmp, "init", "-q", "--bare", "-b", "depth", str(self.origin))
        git(tmp, "clone", "-q", str(self.origin), str(self.root))
        git(self.root, "checkout", "-q", "-b", "depth")
        # The job commits with git's own settings; a CI runner has no name set.
        git(self.root, "config", "user.name", "lock job test")
        git(self.root, "config", "user.email", "lock-job@test.invalid")
        self.good_web = self.archives / "web-good"
        (self.good_web / "out").mkdir(parents=True)
        web_row = dr.Row("2026-09-26T10:00", "web", "c1c1c1c", "c1c1c1c1", str(self.good_web), True)
        worker_row = dr.Row("2026-09-26T09:50", "worker", "c1c1c1c", V1, "", False)
        record = [dr.HEAD, dr.RULE, web_row.cells(), worker_row.cells()]
        files = {
            "README.md": README,
            ".gitignore": "data/\n",
            "results/ots.json": '{"proofs": 1}\n',
            "results/fhir_validation.json": '{"errors": 0}\n',
            "apps/web/public/_headers": "/*\n  X-Frame-Options: DENY\n",
            "proofs/audit-head-2026-09-27.ots": "proof\n",
            la.HOSTING: "\n".join(["# Hosting", "", dr.START, *record, dr.END, ""]),
        }
        for rel, text in files.items():
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(text)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "start")
        git(self.root, "push", "-q", "origin", "depth", "depth:main")
        self.dump = make_dump(tmp, sessions, {"a1": "yes", "a2": "no"})
        # Production as it is before the job: the Worker at V1, the site built from c1c1c1c.
        self.live = {"worker": V1, "pages": "c1c1c1c"}
        self.web_dir = tmp / "web"
        (self.web_dir / "out").mkdir(parents=True)
        (self.web_dir / "out" / "index.html").write_text("new build")
        (self.web_dir / "wrangler.jsonc").write_text("{}")
        self.out = FakeOutward()
        self.local = FakeLocal(self)
        self.wire()

    def head(self, ref: str = "HEAD", where: Path | None = None) -> str:
        return git(where or self.root, "rev-parse", ref)

    def origin_refs(self) -> tuple[str, str]:
        return self.head("depth", self.origin), self.head("main", self.origin)

    def real_git(self, args: list[str], cwd: Path | None, env: Mapping[str, str] | None) -> Done:
        proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
        return Done(proc.returncode, proc.stdout, proc.stderr)

    def wire(self) -> None:
        out = self.out
        out.answer(["git"], self.real_git)
        out.answer(
            ["npx", "wrangler", "deployments"],
            lambda a, c, e: Done(
                0,
                json.dumps({"versions": [{"version_id": self.live["worker"], "percentage": 100}]}),
            ),
        )
        out.answer(
            ["npx", "wrangler", "pages", "deployment", "list"],
            lambda a, c, e: Done(
                0,
                json.dumps(
                    [
                        {
                            "Id": "x",
                            "Source": self.live["pages"],
                            "Deployment": f"https://{self.live['pages'][:7]}0.{dr.PAGES_HOST}",
                        }
                    ]
                ),
            ),
        )
        out.answer(["bash", "scripts/backup_d1.sh"], self.backup)
        out.answer(["bash", "scripts/deploy.sh", "worker"], self.deploy_worker)
        out.answer(["bash", "scripts/deploy.sh", "web"], self.deploy_web)
        out.answer(["npx", "wrangler", "rollback"], self.rollback_worker)
        out.answer(["npx", "wrangler", "pages", "deploy"], self.rollback_web)
        out.pages[f"{la.SITE}/health"] = Reply(200, '{"status":"ok"}')
        out.pages[f"{la.SITE}/api/test/counts"] = Reply(
            200,
            json.dumps(
                {
                    "by_arm": {
                        "trained": {"randomized": 2, "completed": 1},
                        "untrained": {"randomized": 2, "completed": 1},
                    },
                    "by_source": {"panel": 1, "other": 1},
                }
            ),
        )
        out.pages[f"POST {la.SITE}/api/demo/answer"] = Reply(404, '{"detail":"Not known."}')

    def backup(self, args: list[str], cwd: Path | None, env: Mapping[str, str] | None) -> Done:
        target = Path((env or {})["BACKUP_DIR"])
        target.mkdir(parents=True, exist_ok=True)
        copy = target / "second-look-20260928T011000Z.sql"
        shutil.copy(self.dump, copy)
        (target / "last_backup.json").write_text(
            json.dumps({"generated_at_utc": la.stamp(NOW), "file": str(copy)})
        )
        return Done(0, f"backup-d1: {copy}")

    def commit7(self) -> str:
        return self.head()[:7]

    def deploy_worker(
        self, args: list[str], cwd: Path | None, env: Mapping[str, str] | None
    ) -> Done:
        assert (env or {}).get("ALLOW_BRANCH") == "yes"
        self.live["worker"] = V2
        dr.record(
            "worker",
            f"Current Version ID: {V2}",
            commit=self.commit7(),
            when="2026-09-28T01:20:00Z",
            hosting=self.root / la.HOSTING,
        )
        return Done(0, "deployed")

    def deploy_web(self, args: list[str], cwd: Path | None, env: Mapping[str, str] | None) -> Done:
        self.live["pages"] = self.commit7()
        # What the build would ship: the tree as committed, with no other job's file in it.
        self.shipped = git(self.root, "status", "--porcelain", "--untracked-files=all")
        self.shipped_ots = (self.root / "results/ots.json").read_text()
        (self.root / "apps/web/public/_headers").write_text("rewritten by the build\n")
        dr.record(
            "web",
            f"https://ab12cd34.{dr.PAGES_HOST}",
            commit=self.commit7(),
            when="2026-09-28T01:30:00Z",
            hosting=self.root / la.HOSTING,
            web_dir=self.web_dir,
            archives=self.archives,
        )
        return Done(0, "deployed")

    def rollback_worker(
        self, args: list[str], cwd: Path | None, env: Mapping[str, str] | None
    ) -> Done:
        self.live["worker"] = args[3]
        return Done(0)

    def rollback_web(
        self, args: list[str], cwd: Path | None, env: Mapping[str, str] | None
    ) -> Done:
        assert cwd == self.good_web
        self.live["pages"] = args[args.index("--commit-hash") + 1]
        return Done(0)

    def lock(self, **kw: Any) -> la.Lock:
        return la.Lock(
            root=self.root,
            out=self.out,
            local=self.local,
            clock=kw.pop("clock", lambda: NOW),
            backups=self.backups,
            qa_key=kw.pop("qa_key", lambda: "q" * 32),
            say=lambda s: None,
            **kw,
        )


class FakeLocal(la.Local):
    """git for real in the checkout; the analysis for real in this process; the rest stood in."""

    def __init__(self, world: World) -> None:
        self.world = world
        self.calls: list[list[str]] = []
        self.fail: dict[tuple[str, ...], Done] = {}

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str] | None = None,
        timeout: float = 3600,
    ) -> Done:
        args = list(argv)
        self.calls.append(args)
        for prefix, result in self.fail.items():
            if tuple(args[: len(prefix)]) == prefix:
                return result
        if args[0] == "git":
            return self.world.real_git(args, cwd, env)
        if args[-1] == "evals/usability_analysis.py":
            return self.analysis(cwd)
        if args[-1] == "evals/assist_analysis.py":
            return self.part2(cwd)
        if args[:2] == ["make", "render-readme"]:
            path = cwd / "README.md"
            text, missing = render_readme.render(path.read_text(), cwd)
            assert render_readme.broken_paragraph_lines(text) == []
            path.write_text(text)
            return Done(0, f"{len(missing)} missing")
        if args[:2] == ["make", "verify-claims"]:
            text = (cwd / "README.md").read_text()
            for ref, shown in render_readme.RENDERED_RE.findall(text):
                if shown != render_readme.display(render_readme.resolve(ref, cwd)):
                    return Done(1, "", f"{ref} shows {shown}")
            return Done(0)
        return Done(0)

    def analysis(self, cwd: Path) -> Done:
        """evals/usability_analysis.py with no option, as the job runs it, pointed at the
        checkout's data/export and results/ and with the clock after the lock."""
        buf = io.StringIO()
        with pytest.MonkeyPatch.context() as mp, contextlib.redirect_stdout(buf):
            mp.setattr(ua, "now_utc", lambda: NOW)
            mp.setattr(common, "now_utc", lambda: NOW)
            code = ua.main(
                [
                    "--input",
                    str(cwd / "data" / "export"),
                    "--out-dir",
                    str(cwd / "results"),
                    "--resamples",
                    "200",
                    "--permutations",
                    "200",
                ]
            )
        return Done(code, buf.getvalue())

    def part2(self, cwd: Path) -> Done:
        """evals/assist_analysis.py with no option, on the checkout's export, after the lock. Its
        tag and plan checks are tested in evals/tests/test_assist_analysis.py and stubbed here."""
        buf = io.StringIO()
        with pytest.MonkeyPatch.context() as mp, contextlib.redirect_stdout(buf):
            mp.setattr(aa, "now_utc", lambda: NOW)
            mp.setattr(aa, "refusal_reason", lambda now, repo: None)
            code = aa.main(
                [
                    "--input",
                    str(cwd / "data" / "export"),
                    "--out-dir",
                    str(cwd / "results"),
                    "--resamples",
                    "200",
                    "--permutations",
                    "200",
                ]
            )
        return Done(code, buf.getvalue())


@pytest.fixture
def world(tmp_path: Path) -> World:
    w = World(tmp_path, sample_sessions())
    # The other Mac jobs have been at work: an upgraded proof and a new one wait for a commit.
    (w.root / "results/ots.json").write_text('{"proofs": 2}\n')
    (w.root / "proofs/audit-head-2026-09-28.ots").write_text("new proof\n")
    return w


def outward_order(out: FakeOutward) -> list[str]:
    names = []
    for c in out.calls:
        text = " ".join(c)
        for key in (
            "git fetch",
            "wrangler whoami",
            "live-readonly",
            "backup_d1",
            "--dry-run",
            "deploy.sh worker",
            "live-check",
            "deploy.sh web",
            "demo-open-check",
        ):
            if key in text:
                names.append(key)
        if c[:2] == ["git", "push"] and "--dry-run" not in c:
            names.append("push")
    return names


def mac_files_untouched(w: World) -> None:
    assert (w.root / "results/ots.json").read_text() == '{"proofs": 2}\n'
    assert (w.root / "proofs/audit-head-2026-09-28.ots").read_text() == "new proof\n"
    assert git(w.root, "diff", "--name-only") == "results/ots.json"
    assert git(w.root, "diff", "--cached", "--name-only") == ""
    untracked = git(w.root, "ls-files", "--others", "--exclude-standard")
    assert untracked == "proofs/audit-head-2026-09-28.ots"


def test_the_whole_chain_on_a_copy_of_the_database(world: World) -> None:
    start = world.head()
    assert world.lock().run() == 0
    depth, main = world.origin_refs()
    assert depth == main == world.head() != start
    assert git(world.root, "rev-list", "--count", f"{start}..HEAD") == "2"
    # In order, and the push last, after the phone tests and judge mode.
    assert outward_order(world.out) == [
        "git fetch",
        "wrangler whoami",
        "live-readonly",
        "backup_d1",
        "--dry-run",
        "deploy.sh worker",
        "live-check",
        "deploy.sh web",
        "live-readonly",
        "demo-open-check",
        "push",
    ]
    push = world.out.ran("git", "push", "--atomic")
    assert push and all(p[-2:] == ["HEAD:refs/heads/depth", "HEAD:refs/heads/main"] for p in push)
    # The analysis ran once, on the export of the backup, and its result is committed.
    result = json.loads(git(world.root, "show", "origin/depth:results/usability_20260928.json"))
    assert result["synthetic"] is False and result["primary"]["status"] == "descriptive"
    assert (
        result["counts"]["completed_trained"] == 1 and result["counts"]["completed_untrained"] == 1
    )
    assert result["by_source"] == {
        "other": {"trained": 0, "untrained": 1},
        "panel": {"trained": 1, "untrained": 0},
    }
    assert sum(1 for c in world.local.calls if c[-1] == "evals/usability_analysis.py") == 1
    record = json.loads(git(world.root, "show", f"origin/depth:{la.RECORD}"))
    assert (
        record["analysis"] == "results/usability_20260928.json"
        and record["status"] == "descriptive"
    )
    # The README's human row: counts per arm and per source, rendered, and the one status line.
    readme = git(world.root, "show", "origin/main:README.md")
    assert "{{claim:" not in readme and la.HUMAN_LEAD not in readme and la.NOBODY_YET not in readme
    assert la.SOMEBODY in readme
    row = readme[readme.index(la.HUMAN_START) : readme.index(la.HUMAN_END)]
    assert "<!--v:results/usability_20260928.json#/counts/completed_trained-->1<!--/v-->" in row
    assert (
        "(`panel`) | <!--v:results/usability_20260928.json#/by_source/panel/trained-->1<!--/v-->"
        in row
    )
    assert "so this is a description, not a test" in row
    # No answers in git: the export stays in data/, with a copy next to the backup.
    tree = git(world.root, "ls-tree", "-r", "--name-only", "origin/depth")
    assert (
        "data/export/sessions.csv" not in tree
        and (world.root / "data/export/sessions.csv").exists()
    )
    assert list(world.backups.glob("lock-*/responses.csv"))
    # The deploy is recorded as good, the build's rewrite of _headers is not committed.
    rows = dr.read_rows(git(world.root, "show", f"origin/depth:{la.HOSTING}"))
    assert rows[0].part == "web" and rows[0].checked and rows[1].id == V2 and rows[1].checked
    assert git(world.root, "show", "origin/depth:apps/web/public/_headers").startswith("/*")
    # The other jobs' files were left alone and are in neither commit.
    mac_files_untouched(world)
    assert "results/ots.json" not in git(world.root, "diff", "--name-only", start, "HEAD")
    # One line on the status issue, the counts in its body, and the log.
    assert len(world.out.comments) == 1 and world.out.comments[0].startswith("Data lock done")
    assert "panel-counts" in (world.out.issue or "")
    log = (world.backups / "lock.log").read_text()
    assert "ran the pre-registered analysis once" in log and "pushed" in log
    # The audit log holds one data_lock line, in the lock's commit, whose payload is the record.
    lines = git(world.root, "show", "origin/main:audit/log.jsonl").splitlines()
    (entry,) = [json.loads(line) for line in lines]
    assert entry["kind"] == "data_lock" and entry["seq"] == 1
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
    assert entry["payload_sha256"] == hashlib.sha256(canonical.encode()).hexdigest()
    assert audit_log.verify(world.root / "audit" / "log.jsonl") == 1
    assert "the audit log holds the data lock" in log


def assert_as_it_was(world: World, start: str, origin: tuple[str, str]) -> None:
    assert world.origin_refs() == origin, "something was pushed"
    assert world.head() == start
    assert (
        git(
            world.root,
            "diff",
            "--name-only",
            "HEAD",
            "--",
            "README.md",
            la.HOSTING,
            "results/fhir_validation.json",
            "apps/web/public/_headers",
        )
        == ""
    )
    assert not (world.root / la.RECORD).exists()
    assert not list((world.root / "results").glob("usability_*"))
    # A failed lock leaves no data_lock line behind: the log is as it was, here not there at all.
    assert not (world.root / "audit" / "log.jsonl").exists()
    mac_files_untouched(world)


def test_a_failed_make_check_leaves_the_repo_and_production_as_they_were(world: World) -> None:
    world.local.fail[("make", "check")] = Done(2, "", "FAILED scripts/tests/test_x.py::test_y")
    start, origin = world.head(), world.origin_refs()
    assert world.lock().run() == 1
    assert_as_it_was(world, start, origin)
    assert not world.out.ran("bash", "scripts/deploy.sh") and not world.out.ran(
        "npx", "wrangler", "rollback"
    )
    assert world.live == {"worker": V1, "pages": "c1c1c1c"}
    assert "FAILED at make check" in world.out.comments[-1] and "test_y" in world.out.comments[-1]
    assert "FAILED at make check" in (world.backups / "lock.log").read_text()


def test_a_failed_phone_check_after_the_worker_rolls_the_worker_back(world: World) -> None:
    world.out.answer(
        ["node", "apps/web/scripts/live-check.mjs"], Done(1, "", "a real sitting appeared")
    )
    start, origin = world.head(), world.origin_refs()
    assert world.lock().run() == 1
    assert_as_it_was(world, start, origin)
    assert world.out.ran("npx", "wrangler", "rollback", V1)
    assert not world.out.ran("bash", "scripts/deploy.sh", "web")
    assert world.live == {"worker": V1, "pages": "c1c1c1c"}
    assert "rolled back (the Worker)" in world.out.comments[-1]


def test_a_failed_push_rolls_both_halves_back_and_pushes_nothing(world: World) -> None:
    def refuse(args: list[str], cwd: Path | None, env: Mapping[str, str] | None) -> Done:
        return Done(0) if "--dry-run" in args else Done(1, "", "! [rejected] main (fetch first)")

    world.out.answer(["git", "push"], refuse)
    start, origin = world.head(), world.origin_refs()
    assert world.lock().run() == 1
    assert_as_it_was(world, start, origin)
    assert world.live == {"worker": V1, "pages": "c1c1c1c"}
    assert (
        "FAILED at push" in world.out.comments[-1]
        and "the Worker, the site" in world.out.comments[-1]
    )


def test_judge_mode_still_shut_fails_the_lock(world: World) -> None:
    world.out.pages[f"POST {la.SITE}/api/demo/answer"] = Reply(
        403, '{"detail":"Judge mode opens on Sep 28."}'
    )
    start, origin = world.head(), world.origin_refs()
    assert world.lock().run() == 1
    assert_as_it_was(world, start, origin)
    assert "FAILED at judge mode" in world.out.comments[-1]


def test_other_local_changes_are_refused_by_name_before_anything(world: World) -> None:
    (world.root / "README.md").write_text("edited by hand\n")
    assert world.lock().run() == 1
    assert not world.out.ran("git", "fetch") and not world.out.ran("bash")
    assert (
        "README.md" in world.out.comments[-1]
        and "other than the Mac jobs' files" in world.out.comments[-1]
    )
    assert (world.root / "README.md").read_text() == "edited by hand\n"


def test_production_that_is_not_in_the_record_is_refused_before_anything_changes(
    world: World,
) -> None:
    world.live["pages"] = "9999999"
    start, origin = world.head(), world.origin_refs()
    assert world.lock().run() == 1
    assert_as_it_was(world, start, origin)
    assert not world.out.ran("bash", "scripts/backup_d1.sh")
    assert "is not a good row" in world.out.comments[-1]


def test_nobody_kept_writes_the_sentence_and_no_table(tmp_path: Path) -> None:
    sessions = [
        session_row("q1", "trained", is_test=1, completed_at="2026-09-26T10:03:02.999Z"),
        session_row("n1", "untrained"),
    ]
    world = World(tmp_path, sessions)
    assert world.lock().run() == 0
    readme = git(world.root, "show", "origin/main:README.md")
    row = readme[readme.index(la.HUMAN_START) : readme.index(la.HUMAN_END)]
    assert "No finished test from a person was kept before the data lock" in row and "|" not in row
    assert la.NOBODY_FINISHED in readme
    assert json.loads(git(world.root, "show", "origin/main:results/usability_20260928.json"))[
        "primary"
    ]["status"].startswith("not computed")


def test_the_deploy_ships_the_commit_and_the_other_jobs_files_come_back(world: World) -> None:
    assert world.lock().run() == 0
    assert world.shipped_ots == '{"proofs": 1}\n', "the site was built with an uncommitted file"
    assert "proofs/audit-head-2026-09-28.ots" not in world.shipped
    mac_files_untouched(world)


def test_a_newer_copy_on_origin_wins_and_the_jobs_copy_is_kept_aside(world: World) -> None:
    other = world.tmp / "other"
    git(world.tmp, "clone", "-q", "-b", "depth", str(world.origin), str(other))
    (other / "results/ots.json").write_text('{"proofs": 3}\n')
    git(other, "commit", "-q", "-am", "the anchor job's results, committed elsewhere")
    git(other, "push", "-q", "origin", "depth", "depth:main")
    assert world.lock().run() == 0
    assert (world.root / "results/ots.json").read_text() == '{"proofs": 3}\n'
    assert (world.root / "proofs/audit-head-2026-09-28.ots").read_text() == "new proof\n"
    kept = list(world.backups.glob("set-aside-*/results/ots.json"))
    assert kept and kept[0].read_text() == '{"proofs": 2}\n'
    assert "origin/depth changed these" in (world.backups / "lock.log").read_text()


def test_it_runs_once_only(world: World) -> None:
    (world.root / "results/usability_20260928.json").write_text(json.dumps({"synthetic": False}))
    assert world.lock().run() == 0
    assert world.out.calls == [] and world.local.calls == []
    assert "already ran" in (world.backups / "lock.log").read_text()


def test_the_status_lines_follow_the_plans_rule() -> None:
    def claim(p: str) -> str:
        return p

    assert "the plan's one test applies" in la.status_line({"status": "confirmatory"}, claim)
    assert "description, not a test" in la.status_line({"status": "descriptive"}, claim)
    assert "no difference" in la.status_line({"status": "not computed: an arm is empty"}, claim)


def test_the_real_readme_still_has_the_place_for_the_human_row() -> None:
    """If this fails, the lock job would fail at 18:10 on Sep 27: keep the paragraph that starts
    with HUMAN_LEAD (or a human-row block) and the NOBODY_YET sentence in the README."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    placed = la.place_human_row(readme, f"{la.HUMAN_START}\n\nx\n\n{la.HUMAN_END}", True)
    assert placed.count(la.HUMAN_START) == 1 and la.HUMAN_LEAD not in placed
    assert la.NOBODY_YET in readme or la.SOMEBODY in readme or la.NOBODY_FINISHED in readme


# ---------------------------------------------------------------------------
# The real clock
# ---------------------------------------------------------------------------

before_the_lock = pytest.mark.skipif(
    datetime.now(UTC) >= DATA_LOCK_UTC,
    reason="the data lock has passed; this proves the refusal only before it",
)


@before_the_lock
def test_with_the_real_clock_it_refuses_before_the_lock_and_does_nothing(world: World) -> None:
    lock = la.Lock(
        root=world.root,
        out=world.out,
        local=world.local,
        backups=world.backups,
        qa_key=lambda: "q",
        say=lambda s: None,
    )
    assert lock.run() == 3
    assert world.out.calls == [] and world.local.calls == [] and world.out.comments == []
    assert "refused" in (world.backups / "lock.log").read_text()


@before_the_lock
def test_the_command_itself_refuses_before_the_lock_and_touches_nothing(tmp_path: Path) -> None:
    """From a separate process, as launchd runs it, with stand-ins for every outward command."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("git", "gh", "npx", "node", "make", "osascript"):
        (bin_dir / name).write_text(
            f'#!/bin/sh\necho "{name} $*" >> "{tmp_path}/calls.log"\nexit 1\n'
        )
        (bin_dir / name).chmod(0o755)
    env = {
        **{k: v for k, v in os.environ.items() if k != "QA_KEY"},
        "HOME": str(tmp_path),
        "PATH": f"{bin_dir}:/usr/bin:/bin",
    }
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "lock_analysis.py")],
        env=env,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert re.search(
        r"refused: it is \S+, before the data lock at 2026-09-28T01:00:00Z", proc.stdout
    )
    assert not (tmp_path / "calls.log").exists()
    assert "refused" in (tmp_path / "second-look-backups" / "lock.log").read_text()


def test_the_command_takes_no_clock_or_any_other_option() -> None:
    with pytest.raises(SystemExit):
        la.main(["--now", "2026-09-29T00:00:00Z"])


# ---------------------------------------------------------------------------
# make lock-analysis-ready: the same checks, on any day, changing nothing
# ---------------------------------------------------------------------------


def test_ready_says_nothing_when_all_is_in_place_and_changes_nothing(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(la.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    for folder in ("apps/web/node_modules", "worker/node_modules", "tools/diagrams/node_modules"):
        (world.root / folder).mkdir(parents=True)
    before = world.head(), world.origin_refs(), (world.root / la.HOSTING).read_text()
    assert world.lock().readiness() == []
    assert (world.head(), world.origin_refs(), (world.root / la.HOSTING).read_text()) == before
    assert not world.out.ran("git", "fetch") and not world.out.ran("bash")
    assert world.out.comments == []


def test_ready_names_each_problem(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(la.shutil, "which", lambda tool: None if tool == "pandoc" else tool)
    (world.root / "README.md").write_text("edited\n")
    world.live["pages"] = "9999999"
    world.out.answer(["gh", "auth"], Done(1, "", "not logged in"))
    problems = world.lock(qa_key=lambda: None).readiness()
    text = "\n".join(problems)
    for words in ("README.md", "pandoc", "worker/node_modules", "gh is not logged in", "QA_KEY"):
        assert words in text
    assert "commit 9999999" in text


def test_part2_row_says_too_few_with_claim_tokens_or_gives_the_test() -> None:
    rel = "results/assist_20260928.json"
    few = la.part2_row({"primary": {"status": "descriptive"}}, rel)
    assert few.startswith(la.PART2_START) and few.endswith(la.PART2_END)
    assert (
        "Too few people finished part 2" in few
        and "{{claim:" + rel + "#/primary/n_assisted}}" in few
    )
    test = la.part2_row({"primary": {"status": "confirmatory"}}, rel)
    assert "difference {{claim:" in test and "#/primary/ci_high}}" in test
    assert "Nobody took part 2" in la.part2_row(None, "")
    for row in (few, test):
        assert "helps a person whose first answer was wrong or Can't tell" in row
        assert "does not show that the checker cannot mislead anyone" in row
    with pytest.raises(la.Failed):
        la.place_part2_row("no place here", few)


def test_part2_the_lock_runs_part2_once_after_part1_and_fills_the_second_row(world: World) -> None:
    assert world.lock().run() == 0
    calls = [c[-1] for c in world.local.calls]
    assert calls.index("evals/assist_analysis.py") == calls.index("evals/usability_analysis.py") + 1
    assert calls.count("evals/assist_analysis.py") == 1
    readme = git(world.root, "show", "origin/main:README.md")
    row = readme[readme.index(la.PART2_START) : readme.index(la.PART2_END)]
    assert "Too few people finished part 2" in row and "{{claim:" not in row
    record = json.loads(git(world.root, "show", "origin/main:results/lock_analysis.json"))
    assert record["part2_analysis"].startswith("results/assist_")


def test_part2_a_refused_part2_run_undoes_the_whole_lock(world: World) -> None:
    world.local.fail[("uv", "run", "python", "evals/assist_analysis.py")] = Done(3, "", "refused")
    assert world.lock().run() == 1
    assert world.out.comments and "part 2 analysis" in world.out.comments[-1]
