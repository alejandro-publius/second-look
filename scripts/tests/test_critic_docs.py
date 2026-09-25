"""The docs say what the code and the files say (critic rounds 14 and 15).

Each test pins one finding: a sentence that had drifted from the file it describes. They read
words, so each names the file that decides what the words must be.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from scripts.tests.test_judge_docs import JUDGE_PAGES, sentences, text

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
DATA_HANDLING = ROOT / "docs" / "DATA_HANDLING.md"
BACKUP_WORKFLOW = ROOT / ".github" / "workflows" / "backup.yml"


def heading_body(body: str, heading: str) -> str:
    start = body.index(f"\n## {heading}\n")
    end = body.find("\n## ", start + 1)
    return body[start : end if end > 0 else len(body)]


def workflow_triggers(path: Path) -> set[str]:
    data = yaml.safe_load(text(path))
    # YAML 1.1 reads the bare key `on` as True.
    on = data.get("on", data.get(True))
    return set(on) if isinstance(on, dict) else {on} if isinstance(on, str) else set(on or [])


def test_the_backup_workflow_is_manual_and_never_runs_on_a_public_repository() -> None:
    # A03: an artifact on a public repository can be downloaded by anyone signed in to GitHub, and
    # the repository turns public on Sep 30, so the dump must never become one there.
    assert workflow_triggers(BACKUP_WORKFLOW) == {"workflow_dispatch"}
    jobs = yaml.safe_load(text(BACKUP_WORKFLOW))["jobs"]
    for name, job in jobs.items():
        uploads = any("upload-artifact" in str(s.get("uses", "")) for s in job.get("steps", []))
        if uploads:
            assert "github.event.repository.private" in str(job.get("if", "")), name


def test_no_page_says_the_database_backup_is_a_private_github_artifact() -> None:
    # A03: DATA_HANDLING said a GitHub workflow backed the database up daily as a private
    # artifact; the backup runs on the Mac, and the workflow is manual and unused.
    said = [
        f"{p.relative_to(ROOT)}: {s}"
        for p in JUDGE_PAGES
        for s in sentences(text(p))
        if re.search(r"private (GitHub )?(Actions )?artifact", s)
    ]
    assert said == [], said


def test_data_handling_names_the_backup_that_runs() -> None:
    # A03: the job, its script and its folder, as scripts/mac_jobs.py installs them.
    from scripts import mac_jobs

    backup = next(j for j in mac_jobs.jobs() if j.name == "backup")
    body = heading_body(text(DATA_HANDLING), "Backups")
    first = body.split("\n\n", 2)[1]
    assert f"`{backup.script()}`" in first
    assert f"`{mac_jobs.BACKUPS}/`" in first
    assert f"`{backup.label}`" in first
    assert "`.github/workflows/backup.yml`" not in first, "the first paragraph names the workflow"


def test_no_page_says_the_repush_job_runs_on_set_days() -> None:
    # A05: the repush job runs daily in place of the three dated runs (DECISIONS 2026-09-25).
    from scripts import mac_jobs

    repush = next(j for j in mac_jobs.jobs() if j.name == "repush")
    assert repush.when.startswith("daily"), repush.when
    pages = [*JUDGE_PAGES, *sorted((ROOT / "docs" / "adr").glob("*.md"))]
    said = [
        f"{p.relative_to(ROOT)}: {s}"
        for p in pages
        for s in sentences(text(p))
        if re.search(r"re-?push\w*\b.*\bon set (days|dates)\b", s)
    ]
    assert said == [], said


def test_a_readme_section_in_the_report_names_only_sections_the_report_has() -> None:
    # A05: the report took "What the AI cannot do" from the README, and it sent the reader to
    # "The gate, the heart of it", a README heading the report does not have (its 2.2 is "The
    # gate").
    from scripts import build_report

    source = text(ROOT / build_report.SOURCE)
    readme = text(README)

    def headings(body: str) -> set[str]:
        found = (build_report.HEADING_RE.match(line) for line in body.splitlines())
        return {re.sub(r"^[\d.]+\s+", "", m.group(2)) for m in found if m}

    ours = headings(source)
    theirs = {h for h in headings(readme) if len(h.split()) >= 3}
    taken = re.findall(r"^\{\{section:README\.md#([^}]+)\}\}$", source, re.M)
    assert "What the AI cannot do" in taken
    named = {
        f"{title}: {h}"
        for title in taken
        for h in theirs - ours
        if h in re.sub(r"\s+", " ", build_report.section_body(readme, title))
    }
    assert named == set(), named
