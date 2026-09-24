"""Dependabot covers every package manager here, weekly and a few at a time, and every pre-commit
hook is a local one that calls a tool this repository has."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str) -> dict:
    data = yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))
    assert isinstance(data, dict), rel
    return data


def test_dependabot_covers_uv_both_npm_folders_and_the_actions() -> None:
    config = load(".github/dependabot.yml")
    assert config["version"] == 2
    seen = {(u["package-ecosystem"], u["directory"]) for u in config["updates"]}
    assert seen == {("uv", "/"), ("npm", "/apps/web"), ("npm", "/worker"), ("github-actions", "/")}


def test_dependabot_is_weekly_with_a_small_pull_request_limit() -> None:
    for update in load(".github/dependabot.yml")["updates"]:
        assert update["schedule"]["interval"] == "weekly", update
        assert 1 <= update["open-pull-requests-limit"] <= 5, update


def test_every_dependabot_folder_has_the_files_it_updates() -> None:
    needs = {
        "uv": ("pyproject.toml", "uv.lock"),
        "npm": ("package.json", "package-lock.json"),
        "github-actions": (".github/workflows",),
    }
    for update in load(".github/dependabot.yml")["updates"]:
        folder = ROOT / update["directory"].lstrip("/")
        for name in needs[update["package-ecosystem"]]:
            assert (folder / name).exists(), f"{update['directory']} has no {name}"


def hooks() -> list[dict]:
    config = load(".pre-commit-config.yaml")
    assert [r["repo"] for r in config["repos"]] == ["local"], "local hooks only"
    return list(config["repos"][0]["hooks"])


def test_pre_commit_has_the_six_checks() -> None:
    ids = {h["id"] for h in hooks()}
    assert ids == {
        "ruff",
        "ruff-format",
        "dash-check",
        "trailing-whitespace",
        "gitleaks",
        "secrets-in-tree",
    }


def test_every_script_a_hook_calls_exists_and_make_check_runs_it_too() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for hook in hooks():
        if hook["language"] == "pygrep":
            re.compile(hook["entry"])
            continue
        argv = shlex.split(hook["entry"])
        scripts = [a for a in argv if a.startswith("scripts/")]
        for script in scripts:
            assert (ROOT / script).is_file(), f"{hook['id']}: {script} is missing"
            assert script in makefile, f"{hook['id']}: make check does not run {script}"
        if argv[0] == "gitleaks":
            assert "--staged" in argv and "--redact" in argv


def test_the_whitespace_hook_matches_a_trailing_space_and_not_a_clean_line() -> None:
    (hook,) = [h for h in hooks() if h["id"] == "trailing-whitespace"]
    pattern = re.compile(hook["entry"])
    assert pattern.search("a line \n".rstrip("\n")) and not pattern.search("a line")
