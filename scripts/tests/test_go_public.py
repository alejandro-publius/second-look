"""go-public (UPDATE_30 section 8): every step in its order, nothing published unless every step
before the flip passed, the dry run stops before anything leaves the Mac, and a second run is
safe. Every outward call (git, gh, make, curl, gitleaks, the link check) is replaced here, except
in the notes tests, which run real git in a temporary repository."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tomllib
from collections.abc import Mapping
from datetime import date
from pathlib import Path

import pytest

from scripts import go_public as gp

ROOT = Path(__file__).resolve().parents[2]
SLUG = gp.REPO_SLUG
HEAD = "abc1234def5678abc1234def5678abc1234def56"
PAGE = f"https://github.com/{SLUG}"
BADGE = f"https://github.com/{SLUG}/actions/workflows/check.yml/badge.svg"
LIVE = "https://second-look-79t.pages.dev"


# The rewrite of the working notes' mentions


def test_a_path_to_an_update_becomes_a_phrase_with_its_name() -> None:
    before = "The look and feel gate from docs/internal/updates/UPDATE_06.md section 6."
    assert (
        gp.rewrite(before)
        == "The look and feel gate from the team's working notes (UPDATE 06) section 6."
    )


def test_a_backticked_path_and_the_bare_folder_are_rewritten() -> None:
    assert "docs/internal" not in gp.rewrite(
        "See `docs/internal/MASTER_BRIEF.md` and docs/internal/."
    )


def test_a_path_inside_a_json_string_is_rewritten() -> None:
    before = '{"target": "docs/internal/updates/", "detail": "docs/internal"}'
    assert gp.rewrite(before) == (
        '{"target": "the team\'s working notes", "detail": "the team\'s working notes"}'
    )


def test_the_readme_line_about_the_folder_goes() -> None:
    line = (
        "docs/        product docs; docs/internal/ holds the working notes, removed before the "
        "repo opens"
    )
    assert gp.rewrite(line) == "docs/        product docs"


def test_every_mention_in_the_repository_is_rewritten() -> None:
    for path, _count in gp.mentions():
        text = (ROOT / path).read_text(encoding="utf-8")
        assert "docs/internal" not in gp.rewrite(text), path


def test_the_gitleaks_allowlist_keeps_the_real_path() -> None:
    # History keeps the review patch files after go-public, and gitleaks reads history, so the
    # allowlist must still match their path: go-public leaves .gitleaks.toml alone.
    assert gp.GITLEAKS_CONFIG not in dict(gp.mentions())
    config = tomllib.loads((ROOT / gp.GITLEAKS_CONFIG).read_text(encoding="utf-8"))
    paths = [p for allow in config["allowlists"] for p in allow["paths"]]
    patch = "docs/internal/reviews/patches/18-secrets-scan-in-check.patch"
    assert any(re.search(p, patch) for p in paths)


def test_code_that_opens_the_folder_is_listed_as_a_reader_and_kept() -> None:
    """A path built from parts is code that opens the folder: rewording it would break the code,
    so each such file must be a named reader that copes once the folder is gone."""
    proc = subprocess.run(
        ["git", "grep", "-l", "-E", r"\"docs\", \"internal\"", "--", "*.py", "*.mjs", "*.ts"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    builders = set(proc.stdout.split())
    assert builders, "the search found nothing, so it proves nothing"
    assert builders <= gp.KEEP, builders - gp.KEEP
    for path in gp.READERS:
        assert (ROOT / path).is_file(), path
        assert path not in dict(gp.mentions())


def test_notes_gone_is_true_only_inside_the_folder_once_it_is_removed(tmp_path: Path) -> None:
    page = tmp_path / "docs" / "internal" / "reviews" / "LINKS_00.md"
    assert gp.notes_gone(page, tmp_path)
    assert not gp.notes_gone(tmp_path / "results" / "x.json", tmp_path)
    marker = tmp_path / gp.NOTES_MARKER
    marker.parent.mkdir(parents=True)
    marker.write_text("# Internal notes\n")
    assert not gp.notes_gone(page, tmp_path)


def test_the_link_and_axe_pages_are_not_written_once_the_notes_are_gone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from scripts import harden_axe, harden_links

    page = tmp_path / "docs" / "internal" / "reviews" / "LINKS_00.md"
    monkeypatch.setattr(harden_links, "ROOT", tmp_path)
    assert harden_links.write_page(page, "# Link check\n") is False
    monkeypatch.setattr(harden_axe, "ROOT", tmp_path)
    harden_axe.render({}, page.with_name("A11Y_00.md"))
    assert not (tmp_path / "docs").exists()
    (tmp_path / gp.NOTES_MARKER).parent.mkdir(parents=True)
    (tmp_path / gp.NOTES_MARKER).write_text("# Internal notes\n")
    assert harden_links.write_page(page, "# Link check\n") is True
    assert page.read_text() == "# Link check\n"


# submit-check's summary line

MAKE_ERROR = "make: *** [submit-check] Error 1"


def submit_stdout(*failed: str) -> str:
    """What make submit-check prints to stdout: its echoed command, the checks, the summary."""
    lines = ["uv run python scripts/submit_check.py", "PASS  readme"]
    lines += [f"FAIL  {name}" for name in failed]
    lines.append(f"submit-check: {len(failed)} failed: {', '.join(failed) or 'none'}")
    return "\n".join(lines) + "\n"


def test_a_submit_check_that_fails_only_on_the_public_repo_is_accepted() -> None:
    assert gp.submit_blocker(2, submit_stdout("repo_public")) is None
    assert gp.submit_blocker(0, submit_stdout()) is None
    assert gp.submit_blocker(2, submit_stdout("video_link", "repo_public")) is not None
    assert gp.submit_blocker(2, submit_stdout("video_link")) is not None


@pytest.mark.parametrize(
    "tail",
    [
        MAKE_ERROR,
        "make[1]: *** [submit-check] Error 1",
        "make[1]: Leaving directory '/repo'",
    ],
)
def test_make_lines_after_the_summary_do_not_hide_it(tail: str) -> None:
    real_failure = submit_stdout("video_link", "repo_public") + tail + "\n"
    assert gp.submit_blocker(2, real_failure) is not None
    only_public = submit_stdout("repo_public") + tail + "\n"
    assert gp.submit_blocker(2, only_public) is None


def test_the_summary_line_submit_check_really_prints_is_read(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from scripts.submit_check import Check, report

    def printed(*checks: Check) -> str:
        report(list(checks))
        return capsys.readouterr().out

    readme = Check("readme")
    public = Check("repo_public", reasons=["GitHub repo is PRIVATE; it goes public on Sep 30"])
    video = Check("video_link", reasons=["no video link yet"])
    assert gp.submit_failures(printed(readme, public)) == {"repo_public"}
    assert gp.submit_failures(printed(readme, video, public)) == {"video_link", "repo_public"}
    assert gp.submit_failures(printed(readme)) == set()


def test_a_crashed_submit_check_is_never_read_as_a_pass() -> None:
    stdout = "uv run python scripts/submit_check.py\nPASS  readme\n"
    assert gp.submit_blocker(2, "") is not None
    assert gp.submit_blocker(0, stdout) is not None
    # A failing exit that names no failed check, or a count that disagrees with its names.
    assert gp.submit_blocker(2, submit_stdout()) is not None
    assert gp.submit_blocker(2, "submit-check: 2 failed: repo_public\n") is not None


# A fake world: every command main runs gets an answer here


README = f"""Track 3, the statement.

# Second Look

[![check]({BADGE})](https://github.com/{SLUG}/actions/workflows/check.yml)

![Two creeks](docs/screens/landing.webp)

Take the test: **{LIVE}**, and read [the model card](docs/MODEL_CARD.md#what-it-may-do).

## Known weaknesses

[Back up](#second-look).
"""
MODEL_CARD = "# Model card\n\n## What it may do\n\nAsk one question.\n"
DEVPOST = f"Track 3, the statement.\n\n## Live link\n\n```text\n{LIVE}\n```\n"
CHANGELOG = """# Changelog

## v1.0, Sep 30 2026

### Sep 16 to 19

- Nothing was committed yet.

### Sun Sep 20

- The first commit.
"""
TRACKED = ["README.md", "docs/MODEL_CARD.md", "docs/screens/landing.webp", "docs/devpost.md"]


def html_of(markdown: str) -> str:
    return gp.local_html(markdown)


class World:
    """Answers every command go-public runs, and remembers each one with where it ran."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[tuple[list[str], Path, Mapping[str, str] | None]] = []
        self.branch = "main"
        self.status = ""
        self.behind = "0"
        self.fetch_code = 0
        self.gitleaks = (0, "", "INF 612 commits scanned.\nINF no leaks found")
        self.tree_scan = (0, "secrets: 0 found in the 900 files git would commit\n", "")
        self.notes = "docs/internal/README.md\ndocs/internal/DONE.md\n"
        self.lint = (0, "All checks passed!\n", "")
        self.pytest = (0, "3000 passed, 40 skipped in 190.00s\n", "")
        self.submit = (2, submit_stdout("repo_public"), MAKE_ERROR)
        self.readable = True
        self.days = ["2026-09-20", "2026-09-20", "2026-09-10"]
        self.visibility = "PRIVATE"
        self.flip_works = True
        self.http: dict[str, list[tuple[int, str, str]]] = {}
        self.tag: str | None = None
        self.release = False

    def names(self) -> list[str]:
        return [" ".join(cmd[:3]) for cmd, _cwd, _env in self.calls]

    def ran(self, *prefix: str) -> list[tuple[list[str], Path]]:
        return [(cmd, cwd) for cmd, cwd, _ in self.calls if tuple(cmd[: len(prefix)]) == prefix]

    def index(self, *prefix: str) -> int:
        return next(
            i for i, (cmd, _, _) in enumerate(self.calls) if tuple(cmd[: len(prefix)]) == prefix
        )

    def get(self, url: str) -> tuple[int, str, str]:
        answers = self.http.get(url)
        if answers:
            return answers.pop(0) if len(answers) > 1 else answers[0]
        if url == PAGE:
            return 200, "text/html", "<article>Second Look</article>"
        if url == BADGE:
            return 200, "image/svg+xml", ""
        return 200, "image/webp", ""

    def __call__(
        self, cmd: list[str], cwd: Path = ROOT, env: Mapping[str, str] | None = None
    ) -> tuple[int, str, str]:
        self.calls.append((cmd, cwd, env))
        c = cmd
        if c[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return 0, self.branch + "\n", ""
        if c[:3] == ["git", "rev-parse", "--short"]:
            return 0, HEAD[:7] + "\n", ""
        if c == ["git", "rev-parse", "HEAD"]:
            return 0, HEAD + "\n", ""
        if c[:4] == ["git", "rev-parse", "-q", "--verify"]:
            return (0, self.tag + "\n", "") if self.tag else (1, "", "")
        if c[:3] == ["git", "status", "--porcelain"]:
            return 0, self.status, ""
        if c[:2] == ["git", "fetch"]:
            return self.fetch_code, "", "" if self.fetch_code == 0 else "fatal: no route"
        if c[:2] == ["git", "for-each-ref"]:
            refs = ["refs/remotes/origin/HEAD", "refs/remotes/origin/main"]
            refs += ["refs/remotes/origin/depth", "refs/remotes/origin/pull/5", "refs/tags/x"]
            return 0, "\n".join(refs) + "\n", ""
        if c[:3] == ["git", "rev-list", "--count"]:
            return 0, self.behind + "\n", ""
        if c[0] == "gitleaks":
            return self.gitleaks
        if "--secrets-only" in c:
            return self.tree_scan
        if c[:4] == ["git", "ls-files", "--", gp.INTERNAL]:
            return 0, self.notes, ""
        if c[:3] == ["git", "ls-files", "-z"]:
            return 0, "\0".join(TRACKED) + "\0", ""
        if c[:2] == ["git", "grep"]:
            return 1, "", ""  # no mention left to reword, so no file is written
        if c[:2] == ["git", "rm"]:
            self.notes = ""
            return 0, "", ""
        if c[:2] in (["git", "add"], ["git", "commit"], ["git", "reset"], ["git", "tag"]):
            if c[:2] == ["git", "tag"]:
                self.tag = HEAD
            return 0, "", ""
        if c[:2] == ["git", "push"]:
            return 0, "", ""
        if c[:2] == ["git", "worktree"]:
            if c[2] == "add":
                Path(c[-2]).mkdir(parents=True)
                for name in ("README.md", "CHANGELOG.md"):
                    (Path(c[-2]) / name).write_text((self.root / name).read_text())
                (Path(c[-2]) / "docs").mkdir()
                for name in ("MODEL_CARD.md", "devpost.md"):
                    text = (self.root / "docs" / name).read_text()
                    (Path(c[-2]) / "docs" / name).write_text(text)
            return 0, "", ""
        if c[:2] == ["git", "log"]:
            return 0, "\n".join(self.days) + "\n", ""
        if c == ["make", "lint"]:
            return self.lint
        if c[:3] == ["uv", "run", "pytest"]:
            return self.pytest
        if c == ["make", "submit-check"]:
            return self.submit
        if c[:3] == ["gh", "repo", "view"]:
            if "visibility" in c:
                return 0, json.dumps({"visibility": self.visibility}), ""
            return (0, '{"name": "second-look"}', "") if self.readable else (1, "", "HTTP 404")
        if c[:3] == ["gh", "api", "markdown"]:
            text = json.loads(Path(c[-1]).read_text())["text"]
            return 0, html_of(text), ""
        if c[:3] == ["gh", "repo", "edit"]:
            if self.flip_works:
                self.visibility = "PUBLIC"
            return 0, "", ""
        if c[0] == "curl":
            status, ctype, body = self.get(c[-1])
            shown = body if "-" in c[c.index("-o") + 1 :][:1] else ""
            return 0, f"{shown}\n{status} {ctype}", ""
        if c[:3] == ["gh", "release", "view"]:
            url = f"{PAGE}/releases/tag/v1.0"
            return (0, url + "\n", "") if self.release else (1, "", "release not found")
        if c[:3] == ["gh", "release", "create"]:
            self.release = True
            return 0, f"{PAGE}/releases/tag/v1.0\n", ""
        raise AssertionError(f"go-public ran a command the fake does not know: {c}")


def make_tree(root: Path) -> Path:
    (root / "docs" / "screens").mkdir(parents=True)
    (root / "README.md").write_text(README)
    (root / "CHANGELOG.md").write_text(CHANGELOG)
    (root / "docs" / "MODEL_CARD.md").write_text(MODEL_CARD)
    (root / "docs" / "devpost.md").write_text(DEVPOST)
    return root


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> World:
    fake = World(make_tree(tmp_path / "checkout"))
    monkeypatch.setattr(gp, "run_parts", fake)
    monkeypatch.setattr(gp.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(gp, "check_links", lambda urls: {u: ("ok", "200") for u in urls})
    monkeypatch.setattr(gp.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(gp, "Run", _dated_run)
    return fake


REAL_RUN = gp.Run


def _dated_run(**kwargs: object) -> gp.Run:
    """Sep 21 in the Pacific, so the changelog step asks for Sep 20 and not today; and no real
    waiting between the public pass's tries unless a test asks for its own sleep."""
    run = REAL_RUN(**kwargs)  # type: ignore[arg-type]
    run.today = date(2026, 9, 21)
    if "sleep" not in kwargs:
        run.sleep = lambda seconds: None
    return run


def go(world: World, *flags: str) -> int:
    return gp.main([*flags, "--root", str(world.root)])


PUBLISHING = (("git", "push"), ("gh", "repo", "edit"), ("git", "tag"), ("gh", "release"))


def published(world: World) -> bool:
    return any(world.ran(*p) for p in PUBLISHING) or any(c[0] == "curl" for c, _, _ in world.calls)


# The order


def test_the_full_run_does_every_step_in_order(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    assert go(world, "--yes") == 0
    out = capsys.readouterr().out
    steps = [line.split()[1] for line in out.splitlines() if line.startswith(("PASS", "SKIP"))]
    assert steps == gp.STEP_NAMES
    assert "FAIL" not in out
    order = [
        world.index("git", "fetch"),
        world.index("gitleaks"),
        world.index("git", "rm"),
        world.index("git", "commit"),
        world.index("make", "lint"),
        world.index("make", "submit-check"),
        world.index("gh", "api", "markdown"),
        world.index("git", "log"),
        world.index("git", "push", "-q", "origin", "main"),
        world.index(*gp.public_cmd(SLUG)),
        world.index("curl"),
        world.index("git", "tag"),
        world.index("gh", "release", "create"),
    ]
    assert order == sorted(order)
    # One commit, one flip, and only by the one command the brief names.
    assert len(world.ran("git", "commit")) == 1
    assert [c for c, _ in world.ran("gh", "repo", "edit")] == [gp.public_cmd(SLUG)]
    assert "--accept-visibility-change-consequences" in gp.PUBLIC_CMD
    assert out.strip().endswith(f"go-public: {SLUG} is public, tagged v1.0 and released")


def test_gitleaks_reads_every_branch_tag_and_pull_request_head(world: World) -> None:
    assert go(world, "--yes") == 0
    fetch = world.ran("git", "fetch")[0][0]
    assert "+refs/pull/*/head:refs/remotes/origin/pull/*" in fetch and "--tags" in fetch
    scan = world.ran("gitleaks")[0][0]
    opts = next(a for a in scan if a.startswith("--log-opts="))
    assert set(opts.removeprefix("--log-opts=").split()) == {
        "--full-history",
        "--remotes=origin",
        "--tags",
        "HEAD",
    }
    assert "--exit-code" in scan and "--redact" in scan
    assert world.ran("uv", "run", "python", "scripts/submit_check.py", "--secrets-only")


@pytest.mark.parametrize(
    ("setup", "stops_at"),
    [
        (lambda w: setattr(w, "branch", "depth"), "start"),
        (lambda w: setattr(w, "status", " M README.md\n"), "start"),
        (lambda w: setattr(w, "behind", "2"), "start"),
        (lambda w: setattr(w, "fetch_code", 1), "start"),
        (lambda w: setattr(w, "gitleaks", (1, "", "WRN leaks found: 1")), "secrets"),
        (lambda w: setattr(w, "tree_scan", (1, "secrets: 1 found", "")), "secrets"),
        (lambda w: setattr(w, "lint", (1, "E501 Line too long", "")), "tests"),
        (
            lambda w: setattr(w, "pytest", (1, "FAILED scripts/tests/x.py::t\n1 failed", "")),
            "tests",
        ),
        (
            lambda w: setattr(w, "submit", (2, submit_stdout("video_link", "repo_public"), "")),
            "submit",
        ),
        (lambda w: setattr(w, "submit", (2, "Traceback\nKeyError\n", MAKE_ERROR)), "submit"),
        (
            lambda w: (w.root / "CHANGELOG.md").write_text(
                CHANGELOG.replace("Sun Sep 20", "Later")
            ),
            "changelog",
        ),
    ],
)
def test_any_failure_before_the_flip_stops_the_run_and_publishes_nothing(
    world: World, capsys: pytest.CaptureFixture[str], setup: object, stops_at: str
) -> None:
    setup(world)  # type: ignore[operator]
    assert go(world, "--yes") == 1
    out = capsys.readouterr().out.splitlines()
    fails = [line.split()[1] for line in out if line.startswith("FAIL")]
    assert fails == [stops_at]
    assert out[-1].startswith("go-public:") and stops_at in out[-1]
    assert not published(world)


def test_a_flip_that_does_not_take_stops_before_the_public_pass(world: World) -> None:
    world.flip_works = False
    assert go(world, "--yes") == 1
    assert not any(c[0] == "curl" for c, _, _ in world.calls)
    assert not world.ran("git", "tag")


# The dry run


def test_the_dry_run_works_in_a_throwaway_worktree_and_stops_before_the_push(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.branch = "p30/go-public"  # a dry run may start anywhere; it reads HEAD
    assert go(world, "--no-flip") == 0
    out = capsys.readouterr().out
    assert "stopped before the push and the flip, as GO=dry does" in out
    assert not published(world)
    added = world.ran("git", "worktree", "add")
    assert len(added) == 1 and added[0][0][3:5] == ["--detach", "--quiet"]
    tree = Path(added[0][0][-2])
    # Everything that changes a tree ran in the throwaway worktree, never in the checkout.
    for prefix in (("git", "rm"), ("git", "commit"), ("make", "lint"), ("make", "submit-check")):
        assert [cwd for _, cwd in world.ran(*prefix)] == [tree], prefix
    removed = world.ran("git", "worktree", "remove")
    assert removed and removed[0][0][-1] == str(tree)
    assert world.index("git", "worktree", "remove") == len(world.calls) - 2


def test_the_dry_run_shows_every_gap_in_one_run(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.gitleaks = (1, "", "WRN leaks found: 1")
    world.submit = (2, submit_stdout("video_link", "repo_public"), MAKE_ERROR)
    assert go(world, "--no-flip") == 1
    out = capsys.readouterr().out.splitlines()
    assert [line.split()[1] for line in out if line.startswith("FAIL")] == ["secrets", "submit"]
    ran = [line.split()[1] for line in out if line.startswith(("PASS", "FAIL", "SKIP"))]
    assert ran == gp.STEP_NAMES[: gp.STEP_NAMES.index("changelog") + 1]
    assert not published(world)


def test_a_dry_run_whose_worktree_fails_touches_nothing(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gp, "make_worktree", lambda checkout: (None, "fatal: no space"))
    assert go(world, "--no-flip") == 1
    assert not world.ran("git", "rm") and not world.ran("make")


def test_the_json_names_each_step_and_what_was_not_run(world: World, tmp_path: Path) -> None:
    out = tmp_path / "dry.json"
    assert go(world, "--no-flip", "--json", str(out), "--note", "a local mirror") == 0
    report = json.loads(out.read_text())
    assert report["mode"] == "GO=dry (--no-flip)" and report["note"] == "a local mirror"
    assert [s["step"] for s in report["steps"]] == gp.STEP_NAMES[:7]
    assert all(s["result"] in ("PASS", "SKIP") and "\n" not in s["output"] for s in report["steps"])
    assert report["not_run"] == ["push", "flip", "public", "tag", "release"]
    assert report["failed"] == []


# Safe to run again


def test_a_second_run_skips_what_the_first_did(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    assert go(world, "--yes") == 0
    capsys.readouterr()
    assert go(world, "--yes") == 0
    out = capsys.readouterr().out.splitlines()
    skipped = [line.split()[1] for line in out if line.startswith("SKIP")]
    assert skipped == ["notes", "flip", "tag", "release"]
    assert len(world.ran("git", "commit")) == 1
    assert len(world.ran("gh", "repo", "edit")) == 1
    assert len(world.ran("gh", "release", "create")) == 1


def test_a_tag_already_on_another_commit_is_never_moved(world: World) -> None:
    world.tag = "0" * 40
    assert go(world, "--yes") == 1
    assert not world.ran("git", "tag") and not world.ran("gh", "release", "create")


# The README, before the flip


def readme_step(world: World) -> gp.Step:
    return gp.step_readme(gp.Run(root=world.root))


def test_the_readme_is_rendered_by_github_when_it_can_read_the_repo(world: World) -> None:
    step = readme_step(world)
    assert step.result == "PASS", step.output
    assert step.output.startswith("rendered by GitHub: 2 images and")
    world.readable = False
    step = readme_step(world)
    assert step.result == "PASS" and "rendered by the local renderer" in step.output


@pytest.mark.parametrize(
    ("old", "new", "says"),
    [
        ("docs/screens/landing.webp", "docs/screens/gone.webp", "gone.webp: not a tracked file"),
        ("#what-it-may-do", "#what-it-does", "no such heading in docs/MODEL_CARD.md"),
        ("[Back up](#second-look)", "[Back up](#nowhere)", "#nowhere: no such heading"),
        (f"[![check]({BADGE})", "[![check](https://img.shields.io/x)", "no CI badge"),
    ],
)
def test_a_dead_image_link_or_heading_fails_the_readme_step(
    world: World, old: str, new: str, says: str
) -> None:
    (world.root / "README.md").write_text(README.replace(old, new))
    step = readme_step(world)
    assert step.result == "FAIL" and says in step.output, step.output


def test_an_address_that_does_not_answer_fails_and_a_blocked_one_is_named(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    results = {LIVE: ("dead", "404")}
    monkeypatch.setattr(
        gp, "check_links", lambda urls: {u: results.get(u, ("ok", "200")) for u in urls}
    )
    step = readme_step(world)
    assert step.result == "FAIL" and f"{LIVE}: 404" in step.output
    results[LIVE] = ("blocked", "the name does not resolve")
    step = readme_step(world)
    assert step.result == "PASS" and f"open by hand: {LIVE} (the name" in step.output


# The changelog


def changelog_step(root: Path, today: date = date(2026, 9, 21)) -> gp.Step:
    run = gp.Run(root=root)
    run.today = today
    return gp.step_changelog(run)


def test_the_changelog_names_every_day_with_commits_before_today(world: World) -> None:
    assert changelog_step(world.root).result == "PASS"
    # A day with commits that has no line fails; today's commits, and days before Sep 16, do not.
    world.days = ["2026-09-21", "2026-09-10", "2026-09-17"]
    assert changelog_step(world.root).result == "PASS"
    world.days = ["2026-09-22"]
    step = changelog_step(world.root, today=date(2026, 9, 23))
    assert step.result == "FAIL" and "Tue Sep 22" in step.output
    (world.root / "CHANGELOG.md").write_text("# Changelog\n\nNothing yet.\n")
    assert "no ## v1.0 section" in changelog_step(world.root).output
    (world.root / "CHANGELOG.md").unlink()
    assert changelog_step(world.root).output == "CHANGELOG.md is missing"


def test_the_release_notes_are_the_v1_section() -> None:
    notes = gp.release_notes(CHANGELOG + "\n## v0.9\n\nOlder.\n")
    assert notes.startswith("### Sep 16 to 19") and "Older" not in notes
    assert gp.days_named(notes) == {date(2026, 9, d) for d in (16, 17, 18, 19, 20)}


def test_the_real_changelog_starts_on_sep_16_and_parses() -> None:
    notes = gp.release_notes((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
    days = gp.days_named(notes)
    assert min(days) == date(2026, 9, 16)
    assert {date(2026, 9, d) for d in range(16, 26)} <= days
    assert chr(0x2014) not in notes and chr(0x2013) not in notes


# The flip and the pass after it


def test_the_public_pass_is_logged_out_and_reads_every_image(world: World) -> None:
    assert go(world, "--yes") == 0
    curls = [(c, env) for c, _, env in world.calls if c[0] == "curl"]
    for cmd, env in curls:
        assert cmd[:2] == ["curl", "-q"], "-q first, so no .curlrc is read"
        assert not {"-b", "--cookie", "-H", "--header", "-n", "--netrc", "-u"} & set(cmd)
        assert env is not None and set(env) <= {"PATH", "HOME", "LC_ALL"}
        assert not any("TOKEN" in k for k in env)
    urls = [cmd[-1] for cmd, _ in curls]
    assert urls == [PAGE, BADGE, f"{PAGE}/raw/main/docs/screens/landing.webp", LIVE]


def test_the_public_pass_waits_for_github_and_then_gives_up(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    waits: list[float] = []
    world.http[PAGE] = [(404, "text/html", ""), (200, "text/html", "<p>Second Look</p>")]
    run = gp.Run(root=world.root, sleep=waits.append, attempts=3, wait=10)
    gp.step_readme(run)
    assert gp.step_public(run).result == "PASS" and waits == [10]
    world.http[PAGE] = [(404, "text/html", "")]
    waits.clear()
    step = gp.step_public(run)
    assert step.result == "FAIL" and "the README page" in step.output and waits == [10, 10]


@pytest.mark.parametrize(
    ("url", "answer", "says"),
    [
        (PAGE, (200, "text/html", "<p>Sign in</p>"), "does not show the README"),
        (BADGE, (200, "text/html", "<p>Not found</p>"), "came back as text/html"),
        (LIVE, (503, "text/html", ""), "the live link"),
        (f"{PAGE}/raw/main/docs/screens/landing.webp", (404, "text/plain", ""), "an image"),
    ],
)
def test_the_public_pass_fails_on_what_a_stranger_would_miss(
    world: World, url: str, answer: tuple[int, str, str], says: str
) -> None:
    world.http[url] = [answer]
    run = gp.Run(root=world.root, sleep=lambda s: None, attempts=2)
    gp.step_readme(run)
    step = gp.step_public(run)
    assert step.result == "FAIL" and says in step.output, step.output


def test_the_tag_and_release_carry_the_changelog_notes(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    messages: list[str] = []

    def keep(
        cmd: list[str], cwd: Path = ROOT, env: Mapping[str, str] | None = None
    ) -> tuple[int, str, str]:
        for flag in ("-F", "--notes-file"):
            if flag in cmd:
                messages.append(Path(cmd[cmd.index(flag) + 1]).read_text())
        return world(cmd, cwd, env)

    monkeypatch.setattr(gp, "run_parts", keep)
    assert go(world, "--yes") == 0
    tag, release = messages
    assert tag.startswith("Second Look v1.0\n\n### Sep 16 to 19")
    assert release.startswith("### Sep 16 to 19") and "The first commit." in release
    create = world.ran("gh", "release", "create")[0][0]
    assert "--verify-tag" in create and create[create.index("--repo") + 1] == SLUG


# The notes step, with real git in a temporary repository


def git(root: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(
        ["git", *args], cwd=root, env=env, capture_output=True, text=True, check=True
    ).stdout


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for key in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(key)
    root = tmp_path / "repo"
    files = {
        "docs/internal/README.md": "# Internal notes\n",
        "docs/internal/updates/UPDATE_06.md": "# Update 06\n",
        "docs/DESIGN.md": "It follows docs/internal/updates/UPDATE_06.md, which wins.\n",
        "scripts/done_check.py": 'DONE = "docs/internal/DONE.md"\n',
        "README.md": "docs/  product docs; docs/internal/ holds the working notes, removed "
        "before the repo opens\n",
    }
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    git(root, "init", "-q", "-b", "main")
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        git(root, "config", key, value)
    git(root, "config", "commit.gpgsign", "false")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "start")
    return root


def test_the_notes_go_in_one_commit_and_code_that_opens_them_is_kept(repo: Path) -> None:
    step = gp.step_notes(gp.Run(root=repo))
    assert step.result == "PASS", step.output
    assert "removed 2 files" in step.output and "reworded 2 mentions in 2 files" in step.output
    assert git(repo, "log", "--format=%s").splitlines() == [gp.COMMIT_MESSAGE, "start"]
    assert git(repo, "status", "--porcelain") == ""
    assert not (repo / "docs" / "internal").exists()
    assert (repo / "docs" / "DESIGN.md").read_text() == (
        "It follows the team's working notes (UPDATE 06), which wins.\n"
    )
    assert (repo / "README.md").read_text() == "docs/  product docs\n"
    assert (repo / "scripts" / "done_check.py").read_text() == 'DONE = "docs/internal/DONE.md"\n'
    again = gp.step_notes(gp.Run(root=repo))
    assert again.result == "SKIP" and len(git(repo, "log", "--format=%s").splitlines()) == 2


def test_a_notes_step_that_cannot_commit_puts_the_tree_back(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = gp.run_parts

    def no_commit(
        cmd: list[str], cwd: Path = ROOT, env: Mapping[str, str] | None = None
    ) -> tuple[int, str, str]:
        if cmd[:2] == ["git", "commit"]:
            return 1, "", "error: the hook said no"
        return real(cmd, cwd, env)

    monkeypatch.setattr(gp, "run_parts", no_commit)
    step = gp.step_notes(gp.Run(root=repo))
    assert step.result == "FAIL" and "the hook said no" in step.output
    assert git(repo, "status", "--porcelain") == ""
    assert (repo / "docs" / "internal" / "README.md").is_file()
    assert "docs/internal" in (repo / "docs" / "DESIGN.md").read_text()


# The plan, and the make target


def test_the_plan_changes_nothing_and_says_history_keeps_the_notes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    before = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
    ).stdout
    assert gp.main([]) == 0
    after = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
    ).stdout
    assert before == after
    out = capsys.readouterr().out
    assert "the git history still holds docs/internal" in out
    for name in gp.STEP_NAMES:
        assert f"  {name} " in out
    for path in gp.READERS:
        assert path in out


def test_make_go_public_maps_go_to_the_flags() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    recipe = re.search(r"^go-public:\n\t(.*)$", makefile, re.M)
    assert recipe is not None
    line = recipe.group(1)
    assert "$(filter yes,$(GO)),--yes" in line and "$(filter dry,$(GO)),--no-flip" in line
    script = (ROOT / "scripts" / "go_public.sh").read_text(encoding="utf-8")
    assert "--dry" in script and "--no-flip" in script


def test_the_commit_message_says_history_keeps_the_notes() -> None:
    assert "history keeps them" in gp.COMMIT_MESSAGE
    assert "private" not in gp.COMMIT_MESSAGE
