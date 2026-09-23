"""go-public: every mention of the private folder is rewritten, and the dry run changes nothing."""

from __future__ import annotations

import subprocess
from pathlib import Path

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


def test_a_submit_check_that_fails_only_on_the_public_repo_is_accepted() -> None:
    out = "PASS readme\nFAIL repo_public\nsubmit-check: 1 failed: repo_public"
    assert gp.submit_failures(out) <= gp.ALLOWED_SUBMIT_FAILURES
    assert (
        not gp.submit_failures("submit-check: 2 failed: video, repo_public")
        <= gp.ALLOWED_SUBMIT_FAILURES
    )


def test_the_dry_run_changes_nothing() -> None:
    before = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
    ).stdout
    assert gp.main([]) == 0
    after = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
    ).stdout
    assert before == after
