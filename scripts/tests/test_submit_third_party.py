"""submit-check fails today only on the expected items; third_party reads both lockfiles."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import submit_check, third_party

REPO = Path(__file__).parents[2]
STATEMENT = (REPO / "docs" / "track_statement.md").read_text().strip()
HEADERS = "".join(f"\n## {h}\n\n```text\ntext\n```\n" for h in submit_check.HEADERS)
MAP_LINE = "How this answers the organizers' five headers: " + "; ".join(
    f"*{h}* under a section" for h in submit_check.HEADERS
)


def fake_runner(
    visibility: str = "PRIVATE", claims_rc: int = 0, devpost_claims_rc: int = 0
) -> submit_check.Runner:
    def run(argv: list[str]) -> tuple[int, str]:
        if argv[0] == "gh":
            return 0, json.dumps({"visibility": visibility})
        if argv[:2] == ["git", "ls-files"]:
            return 1, ""  # not a git repo: fall back to walking the folder
        if "verify_claims.py" in " ".join(argv):
            rc = devpost_claims_rc if "--file" in argv else claims_rc
            return rc, "verify-claims: 0 claim(s) checked" if rc == 0 else "drifted"
        if argv[0] == "ffprobe":
            return 0, "225.5"
        return 0, ""

    return run


def devpost_text(*, video: bool = True, headers: str = HEADERS) -> str:
    """A Devpost text that passes every check: the statement first, every field filled, the
    report attached and the team named. The five headers come as one block, so a test can
    reorder them."""
    fields = {
        name: "Plain words for this field."
        for name in submit_check.DEVPOST_FIELDS
        if name not in submit_check.HEADERS
    }
    fields[submit_check.TRACK_FIELD] = STATEMENT
    fields[submit_check.LIVE_FIELD] = "https://example.org/demo"
    fields[submit_check.VIDEO_FIELD] = (
        "https://youtu.be/fake" if video else "[VIDEO LINK: paste the upload URL here on the day]"
    )
    body = "".join(f"\n## {name}\n\n```text\n{text}\n```\n" for name, text in fields.items())
    video_line = "\nVideo: https://youtu.be/fake\n" if video else ""
    return (
        f"{STATEMENT}\n\n# Devpost\n{video_line}{headers}{body}\n"
        "## Technical report\n\nAttach `docs/REPORT.pdf` where Devpost takes a file.\n\n"
        "## Team\n\nAlex Velazquez and Rachel Selbrede.\n"
    )


def build_root(tmp_path: Path, *, video: bool = True, headers: str = HEADERS) -> Path:
    root = tmp_path / "sub"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "track_statement.md").write_text(STATEMENT + "\n")
    video_line = "\nVideo: https://youtu.be/fake\n" if video else ""
    # The five headers live in the Devpost text; the README names each one in its map line.
    (root / "README.md").write_text(f"{STATEMENT}\n\n# Second Look\n{video_line}\n{MAP_LINE}\n")
    (root / "docs" / "devpost.md").write_text(devpost_text(video=video, headers=headers))
    (root / "docs" / "REPORT.pdf").write_bytes(b"%PDF-1.7\nnot a real report\n")
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
    """The proving command's expected failure: the repo is private until Oct 3."""
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


# UPDATE_30 section 8 item 2: the Devpost text as the form will hold it.


def devpost_failures(root: Path, **runner: int) -> dict[str, list[str]]:
    checks = submit_check.run_checks(
        root, runner=fake_runner("PUBLIC", **runner), fetch=lambda url: 200
    )
    return {c.name: c.reasons for c in checks if not c.passed}


def edit_devpost(root: Path, old: str, new: str) -> None:
    path = root / "docs" / "devpost.md"
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new, 1))


def test_the_devpost_text_starts_with_the_track_statement(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    assert devpost_failures(root) == {}
    edit_devpost(root, STATEMENT + "\n\n# Devpost", "# Devpost\n\n" + STATEMENT)
    assert list(devpost_failures(root)) == ["devpost_track_statement"]

    root = build_root(tmp_path / "b")
    # The paste field says less than the statement: line one of the description must be all of it.
    edit_devpost(
        root, f"```text\n{STATEMENT}\n```", "```text\nTrack 3, AI-Supported Assessment.\n```"
    )
    reasons = devpost_failures(root)["devpost_track_statement"]
    assert reasons == [
        f"the '{submit_check.TRACK_FIELD}' field is not the track statement word for word"
    ]


@pytest.mark.parametrize(
    ("old", "new", "says"),
    [
        ("## Built with\n", "## Built by\n", "has no 'Built with' field"),
        ("```text\nPlain words for this field.\n```", "```text\n\n```", "is empty"),
        ("Plain words for this field.", "TODO: write this.", "placeholder: TODO"),
        ("Plain words for this field.", "See [SCREENSHOT HERE].", "placeholder: [SCREENSHOT HERE]"),
        (
            "Tagline (under 200 characters)\n\n```text\nPlain words for this field.",
            "Tagline (under 200 characters)\n\n```text\n" + "x" * 200,
            "has 200 characters, not under 200",
        ),
    ],
)
def test_every_devpost_field_is_filled(tmp_path: Path, old: str, new: str, says: str) -> None:
    root = build_root(tmp_path)
    edit_devpost(root, old, new)
    reasons = devpost_failures(root)["devpost_fields"]
    assert any(says in r for r in reasons), reasons


def test_a_link_and_a_wrong_count_are_not_failures(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    edit_devpost(root, "## Built with\n", "## Built with\n\n99 characters\n")
    edit_devpost(root, "Plain words for this field.", "Its [model card](https://example.org/m).")
    checks = submit_check.run_checks(root, runner=fake_runner("PUBLIC"), fetch=lambda url: 200)
    fields = next(c for c in checks if c.name == "devpost_fields")
    assert fields.passed
    assert fields.notes == ["'Built with' says 99 characters and has 27"]


def test_the_video_slot_fails_only_the_video_check(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    # The link is pasted in the Video link field and the README, but the slot inside the
    # demonstration field was left behind.
    edit_devpost(
        root,
        "## A clear demonstration of what was built\n\n```text\ntext",
        ("## A clear demonstration of what was built\n\n```text\nVideo: [VIDEO LINK]"),
    )
    failures = devpost_failures(root)
    assert list(failures) == ["video_link"]
    assert failures["video_link"] == ["docs/devpost.md still holds the video's slot [VIDEO LINK]"]

    root = build_root(tmp_path / "b")
    edit_devpost(root, "```text\nhttps://youtu.be/fake\n```", "```text\nsoon\n```")
    assert devpost_failures(root)["video_link"] == [
        "the 'Video link' field in docs/devpost.md holds no link"
    ]


def test_every_number_in_a_field_has_a_claim_or_is_a_fixed_fact(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    edit_devpost(root, "```text\ntext\n```", "```text\nThe gate dropped 29 of 64 flags.\n```")
    reasons = devpost_failures(root)["devpost_numbers"]
    assert [r.split(" says ")[1].split(" ")[0] for r in reasons] == ["29", "64"]

    # A marker in the same section covers its number; a marker elsewhere does not.
    root = build_root(tmp_path / "b")
    edit_devpost(
        root,
        "## The problem\n\n```text\ntext",
        (
            "## The problem\n\n<!-- claim: results/x.json#/dropped = 29 -->\n"
            "<!-- claim: results/x.json#/candidates = 64 -->\n\n```text\n"
            "The gate dropped 29 of 64 flags, on FHIR R4 4.0.1 with SUSHI 3.20.1 and hl7-eu at "
            "b907cf0, on cloudflare-d1, per https://example.org/v2/9 and /walk/v02"
        ),
    )
    assert "devpost_numbers" not in devpost_failures(root)
    edit_devpost(
        root,
        "## Innovation and practical value\n\n```text\ntext",
        ("## Innovation and practical value\n\n```text\nAgain 29 flags"),
    )
    reasons = devpost_failures(root)["devpost_numbers"]
    assert len(reasons) == 1 and "'Innovation and practical value' field says 29" in reasons[0]


def test_verify_claims_over_the_devpost_text_runs_in_submit_check(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    reasons = devpost_failures(root, devpost_claims_rc=1)["devpost_numbers"]
    assert reasons == ["verify_claims --file docs/devpost.md failed: drifted"]


def test_a_fixed_fact_from_code_is_checked_against_the_code(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    edit_devpost(root, "```text\ntext\n```", "```text\nUploads are deleted after 30 days.\n```")
    (root / "worker" / "src").mkdir(parents=True)
    (root / "worker" / "src" / "uploads.ts").write_text("export const KEEP_DAYS = 30;\n")
    assert devpost_failures(root) == {}
    (root / "worker" / "src" / "uploads.ts").write_text("export const KEEP_DAYS = 14;\n")
    assert devpost_failures(root)["devpost_numbers"] == [
        "the Devpost text says 30 days, and worker/src/uploads.ts no longer sets it"
    ]


def test_the_report_is_named_as_an_attachment_and_is_a_pdf(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    edit_devpost(root, "Attach `docs/REPORT.pdf`", "Link `docs/REPORT.pdf`")
    assert devpost_failures(root)["devpost_report"] == [
        "docs/devpost.md does not name docs/REPORT.pdf as an attachment"
    ]
    root = build_root(tmp_path / "b")
    (root / "docs" / "REPORT.pdf").write_text("# not a pdf\n")
    assert devpost_failures(root)["devpost_report"] == ["docs/REPORT.pdf is not a PDF"]
    (root / "docs" / "REPORT.pdf").unlink()
    assert devpost_failures(root)["devpost_report"] == ["docs/REPORT.pdf is missing"]


def test_the_team_lists_both_members(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    edit_devpost(root, "Alex Velazquez and Rachel Selbrede.", "Alex Velazquez.")
    assert devpost_failures(root)["devpost_team"] == [
        "the Team section does not name Rachel Selbrede"
    ]


def test_demo_url_is_the_live_link_field(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    edit_devpost(
        root, "```text\nhttps://example.org/demo\n```", "```text\nhttps://example.org/live\n```"
    )
    assert submit_check.demo_url(root, None) == "https://example.org/live"
    assert submit_check.demo_url(root, "https://env.example") == "https://env.example"


def test_the_real_devpost_text_passes_every_devpost_check() -> None:
    """Today's text fails nothing but the video's slot, which only the video_link check reads."""
    text = (REPO / "docs" / "devpost.md").read_text(encoding="utf-8")
    assert submit_check.devpost_track_problems(text, STATEMENT) == []
    assert submit_check.devpost_field_problems(text) == ([], [])
    assert submit_check.devpost_number_problems(REPO, text) == []
    assert submit_check.devpost_report_problems(REPO, text) == []
    assert submit_check.devpost_team_problems(text) == []
    assert set(submit_check.DEVPOST_FIELDS) <= set(submit_check.devpost_sections(text))
