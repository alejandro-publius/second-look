"""submit-check fails today only on the expected items; third_party reads both lockfiles."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import submit_check, third_party

REPO = Path(__file__).parents[2]
STATEMENT = (REPO / "docs" / "track_statement.md").read_text().strip()
HEADERS = "".join(f"\n## {h}\n\ntext\n" for h in submit_check.HEADERS)
MAP_LINE = "How this answers the organizers' five headers: " + "; ".join(
    f"*{h}* under a section" for h in submit_check.HEADERS
)


def fake_runner(visibility: str = "PRIVATE", claims_rc: int = 0) -> submit_check.Runner:
    def run(argv: list[str]) -> tuple[int, str]:
        if argv[0] == "gh":
            return 0, json.dumps({"visibility": visibility})
        if argv[:2] == ["git", "ls-files"]:
            return 1, ""  # not a git repo: fall back to walking the folder
        if "verify_claims.py" in " ".join(argv):
            return claims_rc, "verify-claims: 0 claim(s) checked" if claims_rc == 0 else "synthetic"
        if argv[0] == "ffprobe":
            return 0, "225.5"
        return 0, ""

    return run


def build_root(tmp_path: Path, *, video: bool = True, headers: str = HEADERS) -> Path:
    root = tmp_path / "sub"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "track_statement.md").write_text(STATEMENT + "\n")
    video_line = "\nVideo: https://youtu.be/fake\n" if video else ""
    # The five headers live in the Devpost text; the README names each one in its map line.
    (root / "README.md").write_text(f"{STATEMENT}\n\n# Second Look\n{video_line}\n{MAP_LINE}\n")
    (root / "docs" / "devpost.md").write_text(
        f"Demo: https://example.org/demo\n{video_line}{headers}"
    )
    (root / "LICENSE").write_text("MIT License\n\nCopyright 2026\n")
    return root


def names_failed(checks: list[submit_check.Check]) -> set[str]:
    return {c.name for c in checks if not c.passed}


def test_faked_root_fails_only_on_private_repo(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    checks = submit_check.run_checks(root, runner=fake_runner(), fetch=lambda url: 200)
    assert names_failed(checks) == {"repo_public"}
    checks = submit_check.run_checks(root, runner=fake_runner("PUBLIC"), fetch=lambda url: 200)
    assert names_failed(checks) == set()
    notes = {c.name: c.notes for c in checks}
    assert notes["demo_url"] == ["https://example.org/demo answered 200"]
    assert "skipped" in notes["video_duration"][0]


def test_each_guard_fires(tmp_path: Path) -> None:
    root = build_root(tmp_path, video=False)
    fetch_500 = lambda url: 503  # noqa: E731
    checks = submit_check.run_checks(
        root, runner=fake_runner("PUBLIC", claims_rc=1), fetch=fetch_500
    )
    assert names_failed(checks) == {"video_link", "demo_url", "verify_claims"}

    reordered = HEADERS.replace("## The problem", "## Zzz").replace(
        "## A clear demonstration of what was built", "## The problem"
    )
    root = build_root(tmp_path / "b", headers=reordered)
    checks = submit_check.run_checks(root, runner=fake_runner("PUBLIC"), fetch=lambda url: 200)
    reasons = {c.name: c.reasons for c in checks}
    assert any("A clear demonstration" in r for r in reasons["five_headers"])

    root = build_root(tmp_path / "d")
    (root / "README.md").write_text(
        STATEMENT + "\n\nHow this answers the organizers' five headers: none\n"
    )
    checks = submit_check.run_checks(root, runner=fake_runner("PUBLIC"), fetch=lambda url: 200)
    reasons = {c.name: c.reasons for c in checks}
    assert any("map line does not name 'The problem'" in r for r in reasons["five_headers"])

    root = build_root(tmp_path / "c")
    (root / "README.md").write_text("# Not the statement\n" + MAP_LINE + "\n")
    (root / "LICENSE").write_text("Proprietary\n")
    (root / "audit").mkdir()
    (root / "audit" / "log.jsonl").write_text("{}\n")
    checks = submit_check.run_checks(root, runner=fake_runner("PUBLIC"), fetch=lambda url: 200)
    assert {"track_statement", "license", "audit_log", "video_link"} <= names_failed(checks)


def test_secrets_scan_catches_planted_keys_and_passes_clean(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    assert submit_check.scan_secrets(root, submit_check.candidate_files(root, fake_runner())) == []
    planted = root / "config.py"
    aws = "AKIA" + "Q" * 16
    anthropic = "sk-ant-" + "a1" * 12
    planted.write_text(f'AWS = "{aws}"\napi_key = "{"x" * 24}"\nnote = "{anthropic}"\n')
    (root / "photo.jpg").write_bytes(b"\xff\xd8" + aws.encode())
    hits = submit_check.scan_secrets(root, submit_check.candidate_files(root, fake_runner()))
    assert [h.split(":")[0] for h in hits] == ["config.py", "config.py", "config.py"]
    assert "AWS access key" in hits[0] and "assigned secret" in hits[1] and "Anthropic" in hits[2]
    checks = submit_check.run_checks(root, runner=fake_runner("PUBLIC"), fetch=lambda url: 200)
    assert names_failed(checks) == {"secrets_scan"}


def test_video_duration_uses_ffprobe_when_a_file_is_given(tmp_path: Path) -> None:
    if not submit_check.shutil.which("ffprobe"):
        pytest.skip("ffprobe not installed")
    root = build_root(tmp_path)
    clip = root / "demo.mp4"
    clip.write_bytes(b"fake")
    checks = submit_check.run_checks(
        root, runner=fake_runner("PUBLIC"), fetch=lambda url: 200, video=clip
    )
    notes = {c.name: c.notes for c in checks}
    assert notes["video_duration"] == ["video runs 226 s"]

    def short(argv: list[str]) -> tuple[int, str]:
        return (0, "90.0") if argv[0] == "ffprobe" else fake_runner("PUBLIC")(argv)

    checks = submit_check.run_checks(root, runner=short, fetch=lambda url: 200, video=clip)
    assert names_failed(checks) == {"video_duration"}


def test_report_line_names_the_failures(capsys: pytest.CaptureFixture[str]) -> None:
    checks = [
        submit_check.Check("a", ["why"]),
        submit_check.Check("b"),
        submit_check.Check("c", ["x"]),
    ]
    assert submit_check.report(checks) == 2
    assert capsys.readouterr().out.strip().endswith("submit-check: 2 failed: a, c")


def test_real_repo_gh_reports_private() -> None:
    """The proving command's expected failure: the repo is private until Sep 30."""
    rc, out = submit_check.default_runner(REPO)(["gh", "repo", "view", "--json", "visibility"])
    if rc != 0:
        pytest.skip("gh not logged in")
    assert json.loads(out)["visibility"] == "PRIVATE"


def test_third_party_parses_both_lockfiles(tmp_path: Path) -> None:
    py = third_party.python_packages(REPO / "uv.lock")
    names = {n for n, _, _ in py}
    assert {"fastapi", "pillow", "pytest"} <= names and "second-look" not in names
    licenses = {n: lic for n, _, lic in py}
    assert licenses["pillow"] == "MIT-CMU"
    assert all(v for _, v, _ in py), "every package has a version"
    web = third_party.npm_packages(REPO / "apps" / "web" / "package-lock.json")
    web_names = {n for n, _, _, _ in web}
    assert {"next", "react", "typescript"} <= web_names
    by_name = {n: (lic, dev) for n, _, lic, dev in web}
    assert by_name["react"][0] == "MIT" and by_name["typescript"][1] is True
    assert third_party.npm_name("node_modules/a/node_modules/@scope/b") == "@scope/b"
    text = third_party.build(REPO)
    assert "Weather data by Open-Meteo.com, CC BY 4.0" in text
    assert "https://open-meteo.com/en/terms" in text
    assert "sandbox.hl7europe.eu" in text and "b907cf0" in text
    assert "| pillow |" in text and "| react |" in text
    assert chr(0x2014) not in text and chr(0x2013) not in text
    out = tmp_path / "TP.md"
    assert third_party.main(["--root", str(REPO), "--out", str(out)]) == 0
    assert out.read_text() == text.replace(text.split("\n")[2], out.read_text().split("\n")[2])


def test_an_mit_license_file_names_the_license(tmp_path: Path) -> None:
    """khroma, which Mermaid loads, says MIT only in its license file."""
    pkg = tmp_path / "node_modules" / "khroma"
    pkg.mkdir(parents=True)
    (pkg / "package.json").write_text('{"name": "khroma"}')
    assert third_party.npm_license({}, pkg) == third_party.NOT_STATED
    (pkg / "license").write_text("\nThe MIT License (MIT)\n\nCopyright (c) 2019 someone\n")
    assert third_party.npm_license({}, pkg) == "MIT (from its license file)"
    (pkg / "license").write_text("Apache License\nVersion 2.0\n")
    assert third_party.npm_license({}, pkg) == third_party.NOT_STATED
