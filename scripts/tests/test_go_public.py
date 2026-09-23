"""go-public: every mention of the private folder is rewritten, the dry run changes nothing, and
nothing is published unless submit-check fails only on the repo not being public yet."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import go_public as gp

ROOT = Path(__file__).resolve().parents[2]


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


MAKE_ERROR = "make: *** [submit-check] Error 1"


def submit_stdout(*failed: str) -> str:
    """What make submit-check prints to stdout: its echoed command, the checks, the summary."""
    lines = ["uv run python scripts/submit_check.py", "PASS  readme"]
    lines += [f"FAIL  {name}" for name in failed]
    lines.append(f"submit-check: {len(failed)} failed: {', '.join(failed) or 'none'}")
    return "\n".join(lines) + "\n"


def fake_repo(monkeypatch: pytest.MonkeyPatch, submit: tuple[int, str, str]) -> list[list[str]]:
    """Answer every command main runs; nothing reaches git, make or gh for real."""
    calls: list[list[str]] = []

    def run_parts(cmd: list[str]) -> tuple[int, str, str]:
        calls.append(cmd)
        if cmd[:2] == ["git", "grep"]:
            return 1, "", ""  # no mentions to rewrite, so no file is written
        if cmd[:2] == ["git", "rev-parse"]:
            return 0, "main\n", ""
        if cmd == ["make", "submit-check"]:
            return submit
        return 0, "", ""

    monkeypatch.setattr(gp, "run_parts", run_parts)
    return calls


def published(calls: list[list[str]]) -> bool:
    return gp.PUBLIC_CMD in calls or any(cmd[:2] == ["git", "push"] for cmd in calls)


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


def test_a_real_failure_stops_the_run_before_anything_is_published(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = fake_repo(monkeypatch, (2, submit_stdout("video_link", "repo_public"), MAKE_ERROR))
    assert gp.main(["--yes"]) == 1
    assert not published(calls)
    assert not any(cmd[:2] == ["git", "commit"] for cmd in calls)


def test_a_crash_with_no_summary_line_stops_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    stdout = "uv run python scripts/submit_check.py\nPASS  readme\n"
    stderr = "Traceback (most recent call last):\nKeyError: 'visibility'\n" + MAKE_ERROR
    calls = fake_repo(monkeypatch, (2, stdout, stderr))
    assert gp.main(["--yes"]) == 1
    assert not published(calls)
    assert gp.submit_blocker(2, "") is not None
    assert gp.submit_blocker(0, stdout) is not None
    # A failing exit that names no failed check, or a count that disagrees with its names.
    assert gp.submit_blocker(2, submit_stdout()) is not None
    assert gp.submit_blocker(2, "submit-check: 2 failed: repo_public\n") is not None


def test_only_the_repo_not_being_public_yet_lets_it_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = fake_repo(monkeypatch, (2, submit_stdout("repo_public"), MAKE_ERROR))
    assert gp.main(["--yes"]) == 0
    after_check = calls[calls.index(["make", "submit-check"]) + 1 :]
    # Commit, a plain push, and only then the visibility change; nothing rewrites history.
    assert after_check == [
        ["git", "add", "-A"],
        ["git", "commit", "-q", "-m", gp.COMMIT_MESSAGE],
        ["git", "push", "-q", "origin", "main"],
        gp.PUBLIC_CMD,
    ]


def test_the_commit_message_says_history_keeps_the_notes() -> None:
    assert "history keeps them" in gp.COMMIT_MESSAGE
    assert "private" not in gp.COMMIT_MESSAGE


def test_the_dry_run_says_the_history_still_holds_the_folder(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert gp.main([]) == 0
    assert "the git history still holds docs/internal" in capsys.readouterr().out


def test_the_dry_run_changes_nothing() -> None:
    before = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
    ).stdout
    assert gp.main([]) == 0
    after = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
    ).stdout
    assert before == after
