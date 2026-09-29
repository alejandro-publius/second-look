"""No file git would commit names a personal mail address or a Cloudflare account id.

The repository turns public on Sep 30. `docs/internal` leaves the tip before it does
(`scripts/go_public.py`), so that folder alone is left out of the scan. An address at a
university or a company is not a hit: the consent screen gives one on purpose, as the contact.

A hit names the file and the line, never the value, so a red run does not print the address
again. Every fake value here is built when the test runs, so this file holds nothing the scan
could find in itself.

Two things a review on Sep 29 added. The documents wrap their lines, so an id on the line after
the words account id is a hit too. And a file with a byte that is not UTF-8 is still read, with
that byte replaced, where it used to be skipped without a word.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parents[2]
LEFT_OUT = "docs/internal/"

# Mail providers anyone can sign up to, so an address there is a person's own.
PROVIDERS = (
    r"gmail\.com|googlemail\.com|ymail\.com|yahoo\.[a-z]{2,3}(?:\.[a-z]{2})?"
    r"|outlook\.[a-z]{2,3}(?:\.[a-z]{2})?|hotmail\.[a-z]{2,3}(?:\.[a-z]{2})?"
    r"|live\.[a-z]{2,3}(?:\.[a-z]{2})?|msn\.com|icloud\.com|me\.com|mac\.com|aol\.com"
    r"|proton\.me|protonmail\.(?:com|ch)|pm\.me|gmx\.[a-z]{2,3}|mail\.com|yandex\.[a-z]{2,3}"
    r"|zoho\.com|fastmail\.(?:com|fm)|hey\.com|tutanota\.(?:com|de)|tuta\.io|qq\.com|163\.com"
)
ADDRESS = re.compile(
    r"[A-Za-z0-9._%+-]+@(?:" + PROVIDERS + r")(?![A-Za-z0-9-]|\.[A-Za-z0-9])", re.IGNORECASE
)
HEX32 = r"(?<![0-9A-Za-z])[0-9a-f]{32}(?![0-9A-Za-z])"
WORDS = r"account[ _-]?id"
ACCOUNT_ID = re.compile(rf"{WORDS}.{{0,80}}?{HEX32}|{HEX32}.{{0,80}}?{WORDS}", re.IGNORECASE)


def hits_in(text: str) -> list[tuple[int, str]]:
    """The line numbers that hold one, with what it is. Never the value."""
    found: list[tuple[int, str]] = []
    lines = text.splitlines()
    for n, line in enumerate(lines, 1):
        if ADDRESS.search(line):
            found.append((n, "a personal mail address"))
        if ACCOUNT_ID.search(line):
            found.append((n, "a Cloudflare account id"))
        elif n < len(lines) and not ACCOUNT_ID.search(lines[n]):
            # The words on one line and the id on the next, as a wrapped paragraph has them.
            if ACCOUNT_ID.search(line + " " + lines[n]):
                found.append((n, "a Cloudflare account id"))
    return found


def scan(root: Path, names: list[str]) -> list[str]:
    out: list[str] = []
    for name in names:
        if name.startswith(LEFT_OUT):
            continue
        path = root / name
        if not path.is_file():
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if b"\0" in raw[:8192]:
            continue
        text = raw.decode("utf-8", errors="replace")
        out += [f"{name}:{n}: holds {what}" for n, what in hits_in(text)]
    return out


def fake_address(domain: str) -> str:
    return "some.person" + "@" + domain


def fake_id() -> str:
    return "0a1b2c3d" * 4


def test_a_personal_address_is_a_hit() -> None:
    for domain in ("gmail.com", "GMAIL.COM", "yahoo.co.uk", "proton.me", "icloud.com"):
        line = f"Cloudflare account: `{fake_address(domain)}`."
        assert hits_in(line) == [(1, "a personal mail address")], domain


def test_an_account_id_beside_its_words_is_a_hit() -> None:
    for line in (
        f"account id `{fake_id()}`",
        f"CLOUDFLARE_ACCOUNT_ID={fake_id()}",
        f'"account_id": "{fake_id()}"',
        f"{fake_id()} is the account id",
    ):
        assert hits_in(line) == [(1, "a Cloudflare account id")], line.split(fake_id())[0]


def test_an_account_id_on_the_line_after_its_words_is_a_hit() -> None:
    wrapped = f"The Cloudflare account, whose account id\nis `{fake_id()}`, is the team's.\n"
    assert hits_in(wrapped) == [(1, "a Cloudflare account id")]
    other_way = f"`{fake_id()}`\nis the account id.\n"
    assert hits_in(other_way) == [(1, "a Cloudflare account id")]
    # One hit, on its own line, when the next line holds both the words and the id.
    assert hits_in(f"See below.\naccount id `{fake_id()}`\n") == [(2, "a Cloudflare account id")]
    # Two lines apart is not beside.
    assert hits_in(f"account id\n\n{fake_id()}\n") == []


def test_a_file_with_a_byte_that_is_not_utf8_is_still_read(tmp_path: Path) -> None:
    line = ("caf\xe9 login " + fake_address("gmail.com") + "\n").encode("latin-1")
    (tmp_path / "old.md").write_bytes(line)
    assert scan(tmp_path, ["old.md"]) == ["old.md:1: holds a personal mail address"]


def test_both_on_one_line_are_two_hits() -> None:
    line = f"Cloudflare account: `{fake_address('gmail.com')}`, account id `{fake_id()}`."
    assert [what for _, what in hits_in(line)] == [
        "a personal mail address",
        "a Cloudflare account id",
    ]


def test_what_may_stay_is_not_a_hit() -> None:
    lines = [
        "Questions: " + fake_address("berkeley.edu"),
        "Co-Authored-By: A Tool <noreply" + "@" + "anthropic.com>",
        "12345+someone" + "@" + "users.noreply.github.com",
        fake_address("example.com"),
        fake_address("mail.example.org"),
        fake_address("gmail.com.example"),
        "git" + "@" + "github.com:team/second-look.git",
        f'{{ "binding": "PHOTOS", "id": "{fake_id()}" }}',
        f"content hash {fake_id()}",
        "the account id is in the wrangler login on the Mac",
        "account id " + "0a1b2c3d" * 8,
        "https://second-look-api.someone.workers.dev",
    ]
    for line in lines:
        assert hits_in(line) == [], line[:30]


def test_the_scan_leaves_out_the_working_notes_and_files_that_are_not_text(tmp_path: Path) -> None:
    (tmp_path / "docs" / "internal").mkdir(parents=True)
    (tmp_path / "docs" / "notes").mkdir(parents=True)
    line = f"login {fake_address('gmail.com')}\n"
    (tmp_path / "docs" / "internal" / "report.md").write_text(line)
    (tmp_path / "docs" / "notes" / "hosting.md").write_text("# Hosting\n\n" + line)
    (tmp_path / "photo.jpg").write_bytes(b"\xff\xd8\0\0" + line.encode())
    names = ["docs/internal/report.md", "docs/notes/hosting.md", "photo.jpg", "gone.md"]
    assert scan(tmp_path, names) == ["docs/notes/hosting.md:3: holds a personal mail address"]


def test_no_file_git_would_commit_holds_one() -> None:
    if shutil.which("git") is None or not (REPO / ".git").exists():
        pytest.skip("not a git checkout")
    proc = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    names = [n for n in proc.stdout.split("\0") if n]
    assert len(names) > 500, "git listed too few files to trust the scan"
    found = scan(REPO, names)
    assert found == [], "\n".join(found)
