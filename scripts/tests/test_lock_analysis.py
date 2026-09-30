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
import socket
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
import evals.wave2_analysis as w2
from core.lock import DATA_LOCK_UTC
from scripts import audit_log, judge_check, render_readme
from scripts import deploy_record as dr
from scripts import lock_analysis as la
from scripts.outward import Done, Reply
from scripts.tests.fake_outward import FakeOutward
from scripts.tests.test_study_export import make_dump, sample_sessions, session_row

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 9, 28, 1, 10, 0, tzinfo=UTC)
# The second run, ten minutes after the second lock (docs/analysis_plan_v3.md).
NOW2 = datetime(2026, 10, 3, 4, 10, 0, tzinfo=UTC)
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

    def __init__(
        self,
        tmp: Path,
        sessions: list[dict[str, Any]],
        *,
        now: datetime = NOW,
        files: Mapping[str, str] | None = None,
        tag: str | None = None,
    ) -> None:
        self.now = now
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
            **(files or {}),
        }
        for rel, text in files.items():
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(text)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "start")
        if tag:
            git(self.root, "tag", tag)
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
        copy = target / f"second-look-{self.now.strftime('%Y%m%dT%H%M%SZ')}.sql"
        shutil.copy(self.dump, copy)
        (target / "last_backup.json").write_text(
            json.dumps({"generated_at_utc": la.stamp(self.now), "file": str(copy)})
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
            clock=kw.pop("clock", lambda: self.now),
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
        self.cwds: list[Path] = []
        self.envs: list[dict[str, str]] = []
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
        self.cwds.append(cwd)
        self.envs.append(dict(env or {}))
        for prefix, result in self.fail.items():
            if tuple(args[: len(prefix)]) == prefix:
                return result
        if args[0] == "git":
            return self.world.real_git(args, cwd, env)
        if args[-1] == "evals/usability_analysis.py":
            return self.analysis(cwd)
        if args[-1] == "evals/assist_analysis.py":
            return self.part2(cwd)
        if args[-1] == "evals/wave2_analysis.py":
            return self.wave2(cwd)
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

    def wave2(self, cwd: Path) -> Done:
        """evals/wave2_analysis.py with no option, as the second run runs it, on the checkout's
        export, with the clock after the second lock. Its own checks run for real against the
        throwaway checkout, which holds the plan and the tag prereg-v3; only the clock, the
        repository it looks at and the two pins stand in, as they must for a checkout made a
        moment ago."""
        buf = io.StringIO()
        plan = (cwd / w2.PLAN_RELATIVE).read_bytes()
        with pytest.MonkeyPatch.context() as mp, contextlib.redirect_stdout(buf):
            mp.setattr(w2, "now_utc", lambda: NOW2)
            mp.setattr(common, "now_utc", lambda: NOW2)
            mp.setattr(w2, "REPO_ROOT", cwd)
            mp.setattr(w2, "PLAN_COMMIT", git(cwd, "rev-parse", "refs/tags/prereg-v3^{commit}"))
            mp.setattr(w2, "PLAN_SHA256", hashlib.sha256(plan).hexdigest())
            code = w2.main(
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


def scripts_named(world: World) -> list[str]:
    """Every script a finished run named, as a path from the root of the repository."""
    ran = [*zip(world.out.calls, world.out.cwds, strict=True)]
    ran += [*zip(world.local.calls, world.local.cwds, strict=True)]
    scripts = []
    for args, cwd in ran:
        for arg in args[1:]:
            if arg.endswith((".mjs", ".py", ".sh")) and not arg.startswith("-"):
                assert cwd is not None, args
                scripts.append((Path(cwd).relative_to(world.root) / arg).as_posix())
    return scripts


def test_every_script_the_job_runs_is_a_file_from_the_folder_it_runs_in(world: World) -> None:
    """The fakes answer any command, so a path that names no file passed every test and then
    crashed the real job at its last step (2026-09-29: demo-open-check.mjs, run from apps/web
    with a path from the root). Every script the whole chain names must exist in this repository,
    seen from the folder the job runs it in."""
    assert world.lock().run() == 0
    scripts = scripts_named(world)
    assert "apps/web/scripts/demo-open-check.mjs" in scripts
    assert "apps/web/scripts/live-readonly.mjs" in scripts and "scripts/deploy.sh" in scripts
    missing = sorted({s for s in scripts if not (la.ROOT / s).is_file()})
    assert missing == []


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


def test_ready_says_when_origin_main_and_depth_disagree(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(la.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    for folder in ("apps/web/node_modules", "worker/node_modules", "tools/diagrams/node_modules"):
        (world.root / folder).mkdir(parents=True)
    same = "a" * 40
    world.out.answer(
        ["git", "ls-remote"], Done(0, f"{same}\trefs/heads/depth\n{same}\trefs/heads/main\n")
    )
    assert world.lock().readiness() == []
    world.out.answer(
        ["git", "ls-remote"],
        Done(0, f"{'a' * 40}\trefs/heads/depth\n{'b' * 40}\trefs/heads/main\n"),
    )
    problems = world.lock().readiness()
    assert len(problems) == 1 and "git push origin main main:depth" in problems[0]
    assert "origin/main is at bbbbbbb and origin/depth at aaaaaaa" in problems[0]


def test_make_check_runs_on_a_port_that_is_free(world: World) -> None:
    # Another checkout's make check holds the port the job would take by default.
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", judge_check.preferred_web_port()))
        taken.listen(1)
        assert world.lock().run() == 0
    checks = [
        env
        for args, env in zip(world.local.calls, world.local.envs, strict=True)
        if args == ["make", "check"]
    ]
    assert len(checks) == 1 and checks[0]["WEB_PORT"].isdigit()
    port = int(checks[0]["WEB_PORT"])
    assert port != judge_check.preferred_web_port() and judge_check.port_free(port)


def test_a_network_drop_before_the_lock_work_is_tried_again(world: World) -> None:
    drops = {"n": 0}

    def flaky(args: list[str], cwd: Path | None, env: Mapping[str, str] | None) -> Done:
        drops["n"] += 1
        if drops["n"] <= 2:
            return Done(1, "", "getaddrinfo ENOTFOUND api.cloudflare.com")
        return Done(0, "logged in")

    world.out.answer(["npx", "wrangler", "whoami"], flaky)
    waits: list[float] = []
    assert world.lock(sleep=waits.append).run() == 0
    assert waits == [la.NETWORK_PAUSE, la.NETWORK_PAUSE] and drops["n"] == 3
    log = (world.backups / "lock.log").read_text()
    assert "wrangler whoami failed on try 1 of 3: getaddrinfo ENOTFOUND" in log
    assert "wrangler whoami failed on try 2 of 3" in log
    assert world.out.notes[-1][0] == "Second Look: Data lock done"
    assert world.out.notes[-1][1].startswith("Data lock done")


def test_a_drop_that_lasts_fails_the_step_after_three_tries_and_says_so_on_screen(
    world: World,
) -> None:
    world.out.answer(["git", "fetch"], Done(1, "", "nodename nor servname provided"))
    waits: list[float] = []
    start, origin = world.head(), world.origin_refs()
    assert world.lock(sleep=waits.append).run() == 1
    assert waits == [la.NETWORK_PAUSE, la.NETWORK_PAUSE]
    assert len(world.out.ran("git", "fetch")) == 3
    assert_as_it_was(world, start, origin)
    assert "FAILED at fresh checkout: git fetch origin failed on 3 tries" in world.out.comments[-1]
    assert world.out.notes == [
        ("Second Look: Data lock job FAILED", world.out.comments[-1].split(": ", 1)[1][:180])
    ]


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


# ---------------------------------------------------------------------------
# The second run, for the second wave (UPDATE_33, docs/analysis_plan_v3.md)
# ---------------------------------------------------------------------------

FIRST_ROWS = la.first_wave_rows((ROOT / "README.md").read_text(encoding="utf-8"))
README2 = f"""# Second Look

## Numbers at a glance

**The result, in short.** Models took the test. {la.NOBODY_FINISHED}

The full loop, from a desk.

{FIRST_ROWS}

{la.WAVE2_START}

A second wave of the same study is open until the second lock.

{la.WAVE2_END}

{la.WAVE2_PART2_START}
Part 2 of the second wave is reported here once, after the second lock.
{la.WAVE2_PART2_END}

## Gallery
"""
FIRST_FILES = (
    "results/usability_20260929.json",
    "results/assist_20260929.json",
    "results/lock_analysis.json",
)
PUSHED = {"base": "https://sandbox.example", "bundles": 2, "created": 0, "matched": 2}


def wave2_sessions() -> list[dict[str, Any]]:
    """Sittings from all four times. Only b1 and b2 are people inside the window."""
    done = "2026-10-01T10:03:02.999Z"

    def inside(sid: str, arm: str, **over: Any) -> dict[str, Any]:
        row = {"started_at": "2026-10-01T10:00:00.000Z", "post_lock": 1, **over}
        return session_row(sid, arm, **row)

    return [
        session_row("a1", "trained", completed_at="2026-09-26T10:03:02.999Z"),
        inside(
            "c1",
            "untrained",
            started_at="2026-09-29T10:00:00.000Z",
            completed_at="2026-09-29T10:04:00.000Z",
        ),
        inside("b1", "trained", completed_at=done, prior_experience="no"),
        inside("b2", "untrained", completed_at=done, source_label="other"),
        inside("b3", "trained", completed_at=done, is_test=1),
        inside("b4", "untrained"),
        inside(
            "d1",
            "trained",
            started_at="2026-10-03T04:02:00.000Z",
            completed_at="2026-10-03T04:06:00.000Z",
        ),
    ]


def first_audit_log(path: Path) -> None:
    """The audit log as the first run left it: the plan's tag and the first data lock."""
    audit_log.append("plan_tagged", {"tag": "prereg-v1"}, path=path)
    audit_log.append("data_lock", {"analysis": FIRST_FILES[0]}, path=path)


def make_world2(tmp: Path, sessions: list[dict[str, Any]] | None = None) -> World:
    log = tmp / "first-audit.jsonl"
    first_audit_log(log)
    files = {rel: (ROOT / rel).read_text(encoding="utf-8") for rel in FIRST_FILES}
    files |= {
        rel: (ROOT / rel).read_text(encoding="utf-8") for rel in (w2.PLAN_RELATIVE, *w2.REGISTERED)
    }
    files |= {"README.md": README2, la.AUDIT_LOG: log.read_text(encoding="utf-8")}
    w = World(
        tmp,
        wave2_sessions() if sessions is None else sessions,
        now=NOW2,
        files=files,
        tag="prereg-v3",
    )
    (w.root / "results/ots.json").write_text('{"proofs": 2}\n')
    (w.root / "proofs/audit-head-2026-09-28.ots").write_text("new proof\n")
    return w


@pytest.fixture
def world2(tmp_path: Path) -> World:
    return make_world2(tmp_path)


def second(w: World, **kw: Any) -> la.Lock:
    return w.lock(wave=la.SECOND, **kw)


def re_push_adds_a_line(w: World) -> str:
    """What the re-push job does when the sandbox answers: one line more, nothing committed."""
    audit_log.append("sandbox_push", PUSHED, path=w.root / la.AUDIT_LOG)
    return (w.root / la.AUDIT_LOG).read_text(encoding="utf-8").splitlines()[-1]


def test_wave2_refuses_before_the_second_lock_though_the_first_has_passed(world2: World) -> None:
    for when in (NOW, datetime(2026, 10, 3, 3, 59, 59, tzinfo=UTC)):
        assert second(world2, clock=lambda when=when: when).run() == 3
    assert world2.out.calls == [] and world2.local.calls == [] and world2.out.comments == []
    log = (world2.backups / "lock.log").read_text()
    assert "lock 2: refused" in log
    assert "before the second data lock at 2026-10-03T04:00:00Z" in log
    # The first run, handed the same clock, is past its own lock and sees its own result.
    assert world2.lock(clock=lambda: NOW).run() == 0
    assert (
        "already ran: results/usability_20260929.json" in (world2.backups / "lock.log").read_text()
    )


def test_wave2_the_whole_chain_and_the_first_waves_result_does_not_stop_it(world2: World) -> None:
    start = world2.head()
    first = {rel: (world2.root / rel).read_bytes() for rel in FIRST_FILES}
    assert la.real_results(world2.root) and not la.real_results(world2.root, la.SECOND)
    assert second(world2).run() == 0
    depth, main = world2.origin_refs()
    assert depth == main == world2.head() != start
    assert git(world2.root, "rev-list", "--count", f"{start}..HEAD") == "2"
    assert outward_order(world2.out) == [
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
    # One script, run once. The two registered scripts are never run as commands of their own.
    ran = [c[-1] for c in world2.local.calls if c[:3] == ["uv", "run", "python"]]
    assert ran == ["evals/wave2_analysis.py"]
    result = json.loads(git(world2.root, "show", "origin/main:results/usability_w2_20261003.json"))
    assert result["synthetic"] is False and result["primary"]["status"] == "descriptive"
    assert result["script"] == "evals/wave2_analysis.py"
    counts = result["counts"]
    assert counts["completed_trained"] == 1 and counts["completed_untrained"] == 1
    assert result["by_source"] == {
        "other": {"trained": 0, "untrained": 1},
        "panel": {"trained": 1, "untrained": 0},
    }
    assert result["window"]["by_start_time"] == {
        "before_the_first_lock": 1,
        "between_the_first_lock_and_the_opening": 1,
        "inside_the_window": 4,
        "at_or_after_the_second_lock": 1,
        "no_start_time": 0,
    }
    part2 = json.loads(git(world2.root, "show", "origin/main:results/assist_w2_20261003.json"))
    assert part2["primary"]["status"] == "not computed: an arm is empty"
    # Its own record, and the first wave's files exactly as they were.
    record = json.loads(git(world2.root, "show", f"origin/main:{la.SECOND.record}"))
    assert la.SECOND.record == "results/lock_analysis_w2.json"
    assert record["analysis"] == "results/usability_w2_20261003.json"
    assert record["part2_analysis"] == "results/assist_w2_20261003.json"
    assert record["wave"] == 2 and record["plan"] == "docs/analysis_plan_v3.md"
    assert record["window"] == {
        "open_utc": "2026-09-30T04:00:00Z",
        "lock_utc": "2026-10-03T04:00:00Z",
    }
    assert record["backup_file"] == "second-look-20261003T041000Z.sql"
    assert set(record["export_sha256"]) == {"sessions.csv", "responses.csv", *la.PART2_FILES}
    for rel, was in first.items():
        assert git(world2.root, "show", f"origin/main:{rel}").encode() + b"\n" == was, rel
    tree = git(world2.root, "ls-tree", "-r", "--name-only", "origin/depth")
    assert "data/export/sessions.csv" not in tree
    # The audit log: the two lines it had, then one data_lock line whose payload is the record.
    lines = git(world2.root, "show", f"origin/main:{la.AUDIT_LOG}").splitlines()
    entries = [json.loads(line) for line in lines]
    assert [e["kind"] for e in entries] == ["plan_tagged", "data_lock", "data_lock"]
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
    assert entries[-1]["payload_sha256"] == hashlib.sha256(canonical.encode()).hexdigest()
    assert audit_log.verify(world2.root / la.AUDIT_LOG) == 3
    # The README: the second wave's rows are filled, the first wave's are word for word.
    readme = git(world2.root, "show", "origin/main:README.md")
    assert la.first_wave_rows(readme) == FIRST_ROWS
    assert "{{claim:" not in readme and la.NOBODY_FINISHED not in readme
    assert la.SECOND_SOMEBODY in readme
    row = readme[readme.index(la.WAVE2_START) : readme.index(la.WAVE2_END)]
    rel = "results/usability_w2_20261003.json"
    assert f"<!--v:{rel}#/window/open_utc-->2026-09-30T04:00:00Z<!--/v-->" in row
    assert f"<!--v:{rel}#/window/lock_utc-->2026-10-03T04:00:00Z<!--/v-->" in row
    assert f"<!--v:{rel}#/counts/completed_trained-->1<!--/v-->" in row
    assert f"(`panel`) | <!--v:{rel}#/by_source/panel/trained-->1<!--/v-->" in row
    assert "plan `prereg-v3`" in row and "so this is a description, not a test" in row
    assert "A second wave of the same study is open" not in readme
    row2 = readme[readme.index(la.WAVE2_PART2_START) : readme.index(la.WAVE2_PART2_END)]
    assert "in the second wave? Too few people finished part 2" in row2
    assert "results/assist_w2_20261003.json#/primary/n_assisted-->0<!--/v-->" in row2
    assert "does not show that the checker cannot mislead anyone" in row2
    # The two commits, the status issue and the log say which lock this was.
    subjects = git(world2.root, "log", "--format=%s", f"{start}..HEAD").splitlines()
    assert subjects == [
        "Record the deploy after the second data lock as good",
        "Second data lock: the second wave's one analysis, and its README rows",
    ]
    body = git(world2.root, "log", "--format=%b", "-1", "HEAD~1")
    assert "after the lock at 2026-10-03T04:00:00Z" in body
    assert len(world2.out.comments) == 1
    said = world2.out.comments[0]
    assert said.startswith("Second data lock done (2026-10-03T04:10:00Z)")
    assert "under plan prereg-v3 (results/usability_w2_20261003.json, descriptive)" in said
    assert "trained 1 and untrained 1" in said and "judge mode is open" in said
    log = (world2.backups / "lock.log").read_text()
    assert "lock 2: ran the second wave's analysis once" in log and "pushed" in log
    mac_files_untouched(world2)


def test_wave2_every_script_the_second_run_names_is_a_file(world2: World) -> None:
    assert second(world2).run() == 0
    scripts = scripts_named(world2)
    assert "evals/wave2_analysis.py" in scripts
    assert "evals/usability_analysis.py" not in scripts
    assert "apps/web/scripts/demo-open-check.mjs" in scripts
    assert "apps/web/scripts/live-readonly.mjs" in scripts and "scripts/deploy.sh" in scripts
    missing = sorted({s for s in scripts if not (la.ROOT / s).is_file()})
    assert missing == []


def test_wave2_it_runs_once_only(world2: World) -> None:
    assert second(world2).run() == 0
    calls = len(world2.out.calls), len(world2.local.calls)
    assert second(world2).run() == 0
    assert (len(world2.out.calls), len(world2.local.calls)) == calls
    assert len(world2.out.comments) == 1
    log = (world2.backups / "lock.log").read_text()
    assert "nothing to do: the lock analysis already ran: results/usability_w2_20261003" in log


def test_wave2_nobody_kept_says_so_in_its_own_row(tmp_path: Path) -> None:
    sessions = [s for s in wave2_sessions() if s["id"] not in ("b1", "b2")]
    w = make_world2(tmp_path, sessions)
    assert second(w).run() == 0
    readme = git(w.root, "show", "origin/main:README.md")
    row = readme[readme.index(la.WAVE2_START) : readme.index(la.WAVE2_END)]
    assert "no finished test from a person was kept from" in row and "|" not in row
    assert "so the second wave has no human row either" in row
    assert la.SECOND_NOBODY in readme and la.first_wave_rows(readme) == FIRST_ROWS
    result = json.loads(git(w.root, "show", "origin/main:results/usability_w2_20261003.json"))
    assert result["primary"]["status"] == "not computed: an arm is empty"


def as_it_was_before_the_second_run(w: World, start: str, origin: tuple[str, str]) -> None:
    assert w.origin_refs() == origin, "something was pushed"
    assert w.head() == start
    assert git(w.root, "diff", "--name-only", "HEAD", "--", "README.md", la.HOSTING) == ""
    assert not (w.root / la.SECOND.record).exists()
    assert not list((w.root / "results").glob("*_w2_*"))
    for rel in FIRST_FILES:
        assert (w.root / rel).read_bytes() == (ROOT / rel).read_bytes()


def test_wave2_a_failed_make_check_leaves_everything_as_it_was(world2: World) -> None:
    world2.local.fail[("make", "check")] = Done(2, "", "FAILED scripts/tests/test_x.py::test_y")
    start, origin = world2.head(), world2.origin_refs()
    log_before = (world2.root / la.AUDIT_LOG).read_bytes()
    assert second(world2).run() == 1
    as_it_was_before_the_second_run(world2, start, origin)
    assert (world2.root / la.AUDIT_LOG).read_bytes() == log_before
    assert world2.live == {"worker": V1, "pages": "c1c1c1c"}
    said = world2.out.comments[-1]
    assert said.startswith("Second data lock job: FAILED at make check") and "test_y" in said
    assert "run make lock-analysis-2 again" in said
    mac_files_untouched(world2)


def test_wave2_judge_mode_still_shut_fails_the_second_run(world2: World) -> None:
    world2.out.pages[f"POST {la.SITE}/api/demo/answer"] = Reply(403, '{"detail":"Shut."}')
    start, origin = world2.head(), world2.origin_refs()
    assert second(world2).run() == 1
    as_it_was_before_the_second_run(world2, start, origin)
    assert world2.live == {"worker": V1, "pages": "c1c1c1c"}
    assert "FAILED at judge mode" in world2.out.comments[-1]


def test_wave2_a_refused_analysis_undoes_the_whole_run(world2: World) -> None:
    refused = Done(3, "Refusing to run: the git tag prereg-v3 does not exist", "")
    world2.local.fail[("uv", "run", "python", "evals/wave2_analysis.py")] = refused
    start, origin = world2.head(), world2.origin_refs()
    assert second(world2).run() == 1
    as_it_was_before_the_second_run(world2, start, origin)
    assert "FAILED at analysis" in world2.out.comments[-1]
    assert "prereg-v3 does not exist" in world2.out.comments[-1]


def test_wave2_the_analysis_itself_refuses_when_the_tag_is_gone(world2: World) -> None:
    git(world2.root, "tag", "-d", "prereg-v3")
    git(world2.root, "tag", "prereg-v3", "HEAD")
    (world2.root / w2.PLAN_RELATIVE).write_text("another plan\n")
    git(world2.root, "commit", "-q", "-am", "the plan, edited after the tag")
    git(world2.root, "push", "-q", "origin", "depth", "depth:main")
    start, origin = world2.head(), world2.origin_refs()
    assert second(world2).run() == 1
    as_it_was_before_the_second_run(world2, start, origin)
    assert "differs from the version tagged prereg-v3" in world2.out.comments[-1]


# -- the lines the re-push job adds to the audit log ---------------------------------------


def test_wave2_a_line_the_re_push_job_added_goes_into_the_locks_commit(world2: World) -> None:
    line = re_push_adds_a_line(world2)
    assert git(world2.root, "diff", "--name-only") == f"{la.AUDIT_LOG}\nresults/ots.json"
    assert second(world2).run() == 0
    lines = git(world2.root, "show", f"origin/main:{la.AUDIT_LOG}").splitlines()
    kinds = [json.loads(x)["kind"] for x in lines]
    assert kinds == ["plan_tagged", "data_lock", "sandbox_push", "data_lock"]
    # As written, byte for byte, so a proof the anchor job made of it stays good.
    assert lines[2] == line
    assert json.loads(lines[3])["prev_hash"] == json.loads(line)["hash"]
    assert audit_log.verify(world2.root / la.AUDIT_LOG) == 4
    assert git(world2.root, "status", "--porcelain", "--", la.AUDIT_LOG) == ""
    log = (world2.backups / "lock.log").read_text()
    assert "carried 1 line(s) another Mac job added to the audit log (sandbox_push)" in log
    assert "as written" in log
    assert not list(world2.backups.glob("set-aside-*"))
    mac_files_untouched(world2)


def test_wave2_the_site_is_checked_and_built_with_the_carried_line_in_place(world2: World) -> None:
    line = re_push_adds_a_line(world2)
    seen: list[str] = []
    real = world2.local.run

    def watch(argv: Sequence[str], **kw: Any) -> Done:
        if list(argv) == ["make", "check"]:
            seen.append((world2.root / la.AUDIT_LOG).read_text())
        return real(argv, **kw)

    world2.local.run = watch  # type: ignore[method-assign]
    assert second(world2).run() == 0
    assert len(seen) == 1 and seen[0].splitlines()[2] == line
    assert [json.loads(x)["kind"] for x in seen[0].splitlines()][-1] == "data_lock"
    assert la.AUDIT_LOG not in world2.shipped


def test_wave2_after_a_failure_the_added_line_is_back_as_it_was(world2: World) -> None:
    re_push_adds_a_line(world2)
    before = (world2.root / la.AUDIT_LOG).read_bytes()
    world2.local.fail[("make", "check")] = Done(2, "", "FAILED")
    start, origin = world2.head(), world2.origin_refs()
    assert second(world2).run() == 1
    as_it_was_before_the_second_run(world2, start, origin)
    assert (world2.root / la.AUDIT_LOG).read_bytes() == before
    assert git(world2.root, "diff", "--name-only") == f"{la.AUDIT_LOG}\nresults/ots.json"
    # And the next run carries it again.
    del world2.local.fail[("make", "check")]
    assert second(world2).run() == 0
    kinds = [
        json.loads(x)["kind"]
        for x in git(world2.root, "show", f"origin/main:{la.AUDIT_LOG}").splitlines()
    ]
    assert kinds == ["plan_tagged", "data_lock", "sandbox_push", "data_lock"]


def test_wave2_lines_origin_added_meanwhile_come_first_and_the_carried_line_is_chained_again(
    world2: World,
) -> None:
    line = json.loads(re_push_adds_a_line(world2))
    other = world2.tmp / "other"
    git(world2.tmp, "clone", "-q", "-b", "depth", str(world2.origin), str(other))
    audit_log.append("plan_tagged", {"tag": "prereg-v3"}, path=other / la.AUDIT_LOG)
    git(other, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "plan v3 tagged")
    git(other, "push", "-q", "origin", "depth", "depth:main")
    assert second(world2).run() == 0
    lines = git(world2.root, "show", f"origin/main:{la.AUDIT_LOG}").splitlines()
    entries = [json.loads(x) for x in lines]
    kinds = [e["kind"] for e in entries]
    assert kinds == ["plan_tagged", "data_lock", "plan_tagged", "sandbox_push", "data_lock"]
    again = entries[3]
    for key in ("ts_utc", "kind", "payload_sha256"):
        assert again[key] == line[key]
    assert again["seq"] == 4 and again["prev_hash"] == entries[2]["hash"]
    assert again["hash"] != line["hash"]
    assert audit_log.verify(world2.root / la.AUDIT_LOG) == 5
    kept = list(world2.backups.glob(f"set-aside-*/{la.AUDIT_LOG}"))
    assert kept and json.loads(kept[0].read_text()) == line
    assert (
        "chained again after the lines origin/depth added"
        in (world2.backups / "lock.log").read_text()
    )


def test_wave2_a_line_already_committed_by_hand_is_not_added_twice(world2: World) -> None:
    line = re_push_adds_a_line(world2)
    other = world2.tmp / "other"
    git(world2.tmp, "clone", "-q", "-b", "depth", str(world2.origin), str(other))
    with (other / la.AUDIT_LOG).open("a") as f:
        f.write(line + "\n")
    git(other, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "by hand")
    git(other, "push", "-q", "origin", "depth", "depth:main")
    assert second(world2).run() == 0
    lines = git(world2.root, "show", f"origin/main:{la.AUDIT_LOG}").splitlines()
    assert lines.count(line) == 1 and len(lines) == 4
    assert audit_log.verify(world2.root / la.AUDIT_LOG) == 4


@pytest.mark.parametrize(
    ("change", "why"),
    [
        ("edited", "it was changed, not only added to at its end"),
        ("cut", "it was changed, not only added to at its end"),
        ("other kind", "an added line is of a kind no Mac job writes: key_frozen"),
        ("broken chain", "its chain does not hold with the added lines"),
    ],
)
def test_wave2_any_other_change_to_the_audit_log_is_refused_by_name(
    world2: World, change: str, why: str
) -> None:
    path = world2.root / la.AUDIT_LOG
    text = path.read_text()
    if change == "edited":
        path.write_text(text.replace("plan_tagged", "key_frozen"))
    elif change == "cut":
        path.write_text(text.splitlines()[0] + "\n")
    elif change == "other kind":
        audit_log.append("key_frozen", {"x": 1}, path=path)
    else:
        added = json.loads(re_push_adds_a_line(world2))
        path.write_text(text + json.dumps({**added, "prev_hash": "0" * 64}) + "\n")
    after = path.read_bytes()
    assert second(world2).run() == 1
    assert not world2.out.ran("git", "fetch") and not world2.out.ran("bash")
    said = world2.out.comments[-1]
    assert "other than the Mac jobs' files" in said and f"{la.AUDIT_LOG} ({why}" in said
    assert path.read_bytes() == after


def test_the_first_run_still_refuses_a_line_added_to_the_audit_log(world2: World) -> None:
    """Its behaviour is as it was on Sep 29, when the line had to be committed by hand."""
    for rel in FIRST_FILES:
        git(world2.root, "rm", "-q", rel)
    git(world2.root, "commit", "-q", "-m", "as before the first lock")
    git(world2.root, "push", "-q", "origin", "depth", "depth:main")
    re_push_adds_a_line(world2)
    after = (world2.root / la.AUDIT_LOG).read_bytes()
    assert world2.lock(clock=lambda: NOW).run() == 1
    assert not world2.out.ran("git", "fetch")
    said = world2.out.comments[-1]
    assert said.startswith("Data lock job: FAILED at fresh checkout")
    assert f"other than the Mac jobs' files: {la.AUDIT_LOG}." in said
    assert "run make lock-analysis again" in said
    assert (world2.root / la.AUDIT_LOG).read_bytes() == after


def test_wave2_ready_lets_the_re_push_jobs_line_pass_and_the_first_run_does_not(
    world2: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(la.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    for folder in ("apps/web/node_modules", "worker/node_modules", "tools/diagrams/node_modules"):
        (world2.root / folder).mkdir(parents=True)
    re_push_adds_a_line(world2)
    before = (world2.root / la.AUDIT_LOG).read_bytes()
    # The script is pinned to the tag by the session lead; here the checkout's own tag stands in.
    tagged = git(world2.root, "rev-parse", "refs/tags/prereg-v3^{commit}")
    plan = (world2.root / w2.PLAN_RELATIVE).read_bytes()
    monkeypatch.setattr(w2, "PLAN_COMMIT", tagged)
    monkeypatch.setattr(w2, "PLAN_SHA256", hashlib.sha256(plan).hexdigest())
    assert second(world2).readiness() == []
    assert world2.lock().readiness() == [f"local changes the lock job would refuse: {la.AUDIT_LOG}"]
    audit_log.append("key_frozen", {"x": 1}, path=world2.root / la.AUDIT_LOG)
    (problem,) = second(world2).readiness()
    assert la.AUDIT_LOG in problem and "of a kind no Mac job writes" in problem
    assert not world2.out.ran("git", "fetch") and world2.out.comments == []
    assert (world2.root / la.AUDIT_LOG).read_bytes() != before


# -- the rows ---------------------------------------------------------------------------------


def test_wave2_rows_are_claim_tokens_in_their_own_places() -> None:
    rel = "results/usability_w2_20261003.json"
    kept = {"counts": {"completed_trained": 21, "completed_untrained": 20}}
    primary = {"status": "confirmatory", "trained_mean": 70.0, "untrained_mean": 60.0}
    row = la.human_row({**kept, "primary": primary, "by_source": {"panel": {}}}, rel, la.SECOND)
    assert row.startswith(la.WAVE2_START) and row.endswith(la.WAVE2_END)
    assert la.HUMAN_START not in row and "before the data lock" not in row
    assert "{{claim:" + rel + "#/window/open_utc}}" in row
    assert "{{claim:" + rel + "#/window/lock_utc}}" in row
    assert "{{claim:" + rel + "#/primary/difference}}" in row and "plan `prereg-v3`" in row
    # Every count and every time in it is a claim token, which render_readme fills.
    bare = re.sub(r"\{\{claim:[^}]*\}\}", "", row)
    assert not re.search(r"\d{4}-\d{2}-\d{2}", bare) and "21" not in bare
    none = la.human_row({"counts": {}}, rel, la.SECOND)
    assert "so the second wave has no human row either" in none
    few = la.part2_row(
        {"primary": {"status": "descriptive"}}, "results/assist_w2_x.json", la.SECOND
    )
    assert few.startswith(la.WAVE2_PART2_START) and few.endswith(la.WAVE2_PART2_END)
    assert "in the second wave? Too few people finished part 2" in few
    test = la.part2_row({"primary": {"status": "confirmatory"}}, "results/a.json", la.SECOND)
    assert "difference {{claim:results/a.json#/primary/difference}}" in test
    assert "under plan `prereg-v3`" in test
    assert "Nobody took part 2 in the second wave" in la.part2_row(None, "", la.SECOND)
    # The first wave's rows read as they always did.
    assert la.human_row({"counts": {}}, "results/usability_20260929.json").startswith(
        f"{la.HUMAN_START}\n\nNo finished test from a person was kept before the data lock at "
    )
    assert la.part2_row(None, "").startswith(f"{la.PART2_START}\nDoes the checker's question")


def test_wave2_rows_are_never_placed_at_the_cost_of_the_first_waves() -> None:
    row = f"{la.WAVE2_START}\n\nx\n\n{la.WAVE2_END}"
    part2 = f"{la.WAVE2_PART2_START}\ny\n{la.WAVE2_PART2_END}"
    placed = la.place_wave2_rows(README2, row, part2, True)
    assert la.first_wave_rows(placed) == FIRST_ROWS
    assert placed.count(la.WAVE2_START) == 1 and "\n\nx\n\n" in placed and "\ny\n" in placed
    assert la.SECOND_SOMEBODY in placed
    assert la.SECOND_NOBODY in la.place_wave2_rows(README2, row, part2, False)
    with pytest.raises(la.Failed, match="no place for the second wave's row"):
        la.place_wave2_rows(README2.replace(la.WAVE2_START, ""), row, part2, True)
    with pytest.raises(la.Failed, match="no place for the second wave's part 2 row"):
        la.place_wave2_rows(README2.replace(la.WAVE2_PART2_END, ""), row, part2, True)
    # A place that reaches into the first wave's rows is refused, and nothing is written.
    reaching = README2.replace(la.WAVE2_START, "").replace(
        la.PART2_START, f"{la.WAVE2_START}\n{la.PART2_START}"
    )
    with pytest.raises(la.Failed, match="the first wave's rows would have changed"):
        la.place_wave2_rows(reaching, row, part2, True)


def test_the_real_readme_has_the_place_for_the_second_waves_rows() -> None:
    """If this fails, the second run would fail on Oct 2 at 21:10 PDT: keep both pairs of
    markers in the README, after the first wave's rows."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    row = f"{la.WAVE2_START}\n\nx\n\n{la.WAVE2_END}"
    part2 = f"{la.WAVE2_PART2_START}\ny\n{la.WAVE2_PART2_END}"
    placed = la.place_wave2_rows(readme, row, part2, True)
    assert la.first_wave_rows(placed) == la.first_wave_rows(readme)
    assert readme.index(la.PART2_END) < readme.index(la.WAVE2_START)
    assert readme.index(la.WAVE2_END) < readme.index(la.WAVE2_PART2_START)
    assert (
        la.NOBODY_FINISHED in readme or la.SECOND_SOMEBODY in readme or la.SECOND_NOBODY in readme
    )
    if not la.real_results(ROOT, la.SECOND):
        # Until the second run, the place says what is true, with the window from results/.
        held = readme[readme.index(la.WAVE2_START) : readme.index(la.WAVE2_END)]
        assert "<!--v:results/wave2_window.json#/lock_utc-->2026-10-03T04:00:00Z<!--/v-->" in held
        assert "docs/analysis_plan_v3.md" in held and "reported here once" in held


def test_the_command_takes_the_wave_and_nothing_else() -> None:
    for argv in (["--wave", "3"], ["--wave", "2", "--now", "2026-10-04T00:00:00Z"]):
        with pytest.raises(SystemExit):
            la.main(argv)
    assert la.WAVES == {1: la.FIRST, 2: la.SECOND}
    assert la.FIRST.lock_utc == DATA_LOCK_UTC and la.FIRST.record == la.RECORD
    assert la.SECOND.lock_utc == w2.SECOND_LOCK_UTC == datetime(2026, 10, 3, 4, tzinfo=UTC)


before_the_second_lock = pytest.mark.skipif(
    datetime.now(UTC) >= w2.SECOND_LOCK_UTC,
    reason="the second lock has passed; this proves the refusal only before it",
)


@before_the_second_lock
def test_wave2_the_command_itself_refuses_before_the_second_lock(tmp_path: Path) -> None:
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
        [sys.executable, str(ROOT / "scripts" / "lock_analysis.py"), "--wave", "2"],
        env=env,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert re.search(
        r"lock 2: refused: it is \S+, before the second data lock at 2026-10-03T04:00:00Z",
        proc.stdout,
    )
    assert not (tmp_path / "calls.log").exists()
    assert "refused" in (tmp_path / "second-look-backups" / "lock.log").read_text()


def test_wave2_ready_says_what_the_analysis_would_refuse_for(
    world2: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(la.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    for folder in ("apps/web/node_modules", "worker/node_modules", "tools/diagrams/node_modules"):
        (world2.root / folder).mkdir(parents=True)
    # Not pinned yet, as the script is until the session lead has made the tag.
    monkeypatch.setattr(w2, "PLAN_COMMIT", None)
    monkeypatch.setattr(w2, "PLAN_SHA256", None)
    (problem,) = second(world2).readiness()
    assert problem.startswith("the second wave's analysis would refuse: the tagged ")
    assert "does not have the SHA-256 pinned" in problem
    # The clock is never the reason: it asks as if the lock had just passed.
    assert "second data lock" not in problem
    git(world2.root, "tag", "-d", "prereg-v3")
    (problem,) = second(world2).readiness()
    assert "the git tag prereg-v3 does not exist" in problem
    # The first run asks none of this.
    assert world2.lock().readiness() == []
