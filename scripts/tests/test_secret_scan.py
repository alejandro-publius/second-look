"""Hard rule 14: the secret scans see .env and .dev.vars lines, and run on every commit.

Every fake value here is built when the test runs, so this file holds nothing a scanner could
mistake for a key.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts import judge_check, submit_check

REPO = Path(__file__).parents[2]
LIVE = "a1b2c3d4" * 6  # 48 characters, the length openssl rand -hex 24 gives


def walk_only(argv: list[str]) -> tuple[int, str]:
    """A runner with no git, so candidate_files walks the folder."""
    return 1, ""


def scan(root: Path) -> list[str]:
    return submit_check.scan_secrets(root, submit_check.candidate_files(root, walk_only))


def git_repo() -> bool:
    return shutil.which("git") is not None and (REPO / ".git").exists()


def test_env_and_dev_vars_lines_are_caught(tmp_path: Path) -> None:
    lines = [
        f"EXPORT_TOKEN={LIVE}",
        f"QA_KEY={LIVE}",
        f"NEXT_PUBLIC_QA_KEY={LIVE}",
        f'export_token = "{LIVE}"',
        f'token = "{LIVE}"',
        f"export CLOUDFLARE_API_TOKEN={LIVE}",
    ]
    (tmp_path / "vars.txt").write_text("\n".join(lines) + "\n")
    hits = scan(tmp_path)
    assert [h.split(":")[1] for h in hits] == ["1", "2", "3", "4", "5", "6"]


def test_placeholders_and_code_are_not_hits(tmp_path: Path) -> None:
    lines = [
        "EXPORT_TOKEN=change-me-" + "x" * 16,
        'PLACEHOLDER_SECRET = "change-me-' + "x" * 16 + '"',
        'EXPORT_TOKEN = "test-' + "x" * 24 + '"',
        'const QA_KEY = "e2e-' + "x" * 24 + '";',
        'TOKEN_ALPHABET = "' + "abcdefghjkmnpqrstuvwxyz" + "23456789" + '"',
        "token = new_contributor_token()",
        "export_token: str = PLACEHOLDER_SECRET",
        f"QA_KEY={LIVE[:12]}",
    ]
    (tmp_path / "code.py").write_text("\n".join(lines) + "\n")
    assert scan(tmp_path) == []


def test_local_secret_files_that_git_would_commit_fail(tmp_path: Path) -> None:
    (tmp_path / "worker").mkdir()
    (tmp_path / "worker" / ".dev.vars").write_text("# empty\n")
    (tmp_path / ".env.local").write_text("# empty\n")
    (tmp_path / ".env.example").write_text("# placeholders only\n")
    hits = scan(tmp_path)
    assert sorted(h.split(":")[0] for h in hits) == [".env.local", "worker/.dev.vars"]
    assert all("not ignored" in h for h in hits)


def test_judge_check_uses_the_same_shapes(tmp_path: Path) -> None:
    (tmp_path / "run.sh").write_text(f"QA_KEY={LIVE}\n")
    assert judge_check.scan_tree(tmp_path) == ["run.sh"]


@pytest.mark.parametrize(
    "path",
    [
        ".dev.vars",
        "worker/.dev.vars",
        "worker/.dev.vars.production",
        ".env",
        ".env.local",
        ".env.production",
        "worker/.env.local",
        "apps/api/.env.test",
    ],
)
def test_local_secret_files_are_ignored_in_every_folder(path: str) -> None:
    if not git_repo():
        pytest.skip("not a git checkout")
    rc = subprocess.run(["git", "check-ignore", "-q", "--no-index", path], cwd=REPO).returncode
    assert rc == 0, f"{path} is not ignored"


def test_env_example_is_not_ignored() -> None:
    if not git_repo():
        pytest.skip("not a git checkout")
    proc = subprocess.run(["git", "check-ignore", "-q", "--no-index", ".env.example"], cwd=REPO)
    assert proc.returncode == 1


def test_make_check_runs_gitleaks_and_the_tree_scan() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    needs = " ".join(m.group(1) for m in re.finditer(r"^check:(.*)$", makefile, re.M)).split()
    assert "secrets" in needs
    recipe = re.search(r"^secrets:\n((?:\t.*\n)+)", makefile, re.M)
    assert recipe is not None
    assert "gitleaks git . --log-opts=HEAD" in recipe.group(1)
    assert "--exit-code 1" in recipe.group(1)
    assert "scripts/submit_check.py --secrets-only" in recipe.group(1)


def test_ci_installs_a_pinned_gitleaks_and_fetches_the_history() -> None:
    workflow = yaml.safe_load((REPO / ".github" / "workflows" / "check.yml").read_text())
    steps = workflow["jobs"]["check"]["steps"]
    checkout = next(s for s in steps if str(s.get("uses", "")).startswith("actions/checkout@"))
    assert checkout.get("with", {}).get("fetch-depth") == 0
    runs = [str(s.get("run", "")) for s in steps]
    install = next(i for i, r in enumerate(runs) if "gitleaks_8.30.1_linux_x64.tar.gz" in r)
    assert re.search(r"\b[0-9a-f]{64}\b", runs[install]) and "sha256sum --check" in runs[install]
    assert install < runs.index("make check")


def test_secrets_only_prints_one_line_and_passes_on_a_clean_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "ok.py").write_text("token = new_contributor_token()\n")
    assert submit_check.main(["--root", str(tmp_path), "--secrets-only"]) == 0
    assert capsys.readouterr().out.startswith("secrets: 0 found")
    (tmp_path / "bad.env").write_text(f"EXPORT_TOKEN={LIVE}\n")
    assert submit_check.main(["--root", str(tmp_path), "--secrets-only"]) == 1
    out = capsys.readouterr().out
    assert "bad.env:1" in out and LIVE not in out


def test_gitleaks_finds_nothing_new_in_this_history() -> None:
    """Every finding in the history is fake and fingerprinted in .gitleaksignore with a reason."""
    if not git_repo() or not shutil.which("gitleaks"):
        pytest.skip("gitleaks not installed or not a git checkout")
    shallow = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"], cwd=REPO, capture_output=True, text=True
    )
    if shallow.stdout.strip() == "true":
        pytest.skip("a shallow clone lacks the commits .gitleaksignore names")
    proc = subprocess.run(
        ["gitleaks", "git", ".", "--log-opts=HEAD", "--redact", "--no-banner", "--exit-code", "1"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]


def test_live_check_takes_the_qa_key_from_the_environment_only() -> None:
    """No fallback to a key file in the shared /tmp folder, where any local account can read it."""
    script = (REPO / "apps" / "web" / "scripts" / "live-check.mjs").read_text(encoding="utf-8")
    assert not re.search(r"readFileSync\(\s*[\"'`]/tmp/", script)
    assert "if (!qaKey) throw" in script
