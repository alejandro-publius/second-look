"""The item checks behind the definition of done: each passes on a tree that has the thing and
fails, naming the gap, on the same tree with the thing broken or missing."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PIL import Image

from scripts import done_items as di

STATEMENT = "Track 3, AI-Supported Assessment. We measure how well a volunteer sees."

README = f"""{STATEMENT}

# Second Look

> **A creek observation should carry how well its observer sees.**

[![check](https://github.com/o/r/actions/workflows/check.yml/badge.svg)](https://github.com/o/r)
![licence: MIT](https://img.shields.io/badge/licence-MIT-blue)

Which creek is healthier?

| Left | Right |
|---|---|
| ![A park by a creek](photos/warmup/a.jpg) | ![A bend in a field](photos/warmup/b.jpg) |

<details>
<summary>The answer</summary>

The bend on the right.

</details>

[Take the test](https://site.example), [watch the video](https://video.example), [judges](https://site.example/judges)

![The two-minute test, start to finish](docs/screens/test.gif)

## Numbers at a glance

<!--v:results/x.json#/a-->1<!--/v--> number.

## Gallery

![Lesson photo one with marks](docs/screens/marks/one.jpg)
![Lesson photo two with marks](docs/screens/marks/two.jpg)

## Why trust a volunteer, and the AI?

Because each is tested.

## What the AI cannot do

Decide.

## Architecture

```mermaid
flowchart LR
  T[Train] -->|lesson| C[Check]
  C -->|answers| V[Verify]
  V -->|flags| R[Record]
  R -->|FHIR| A[Act]
```

```mermaid
flowchart LR
  O[Observation] --> L[Location]
  O --> P[Practitioner]
```

```mermaid
sequenceDiagram
  participant Model
  participant Gate as core/gate.py
  Model->>Gate: raw output
  Gate-->>Model: a flag or nothing
```

### The gate, the heart of it

1. The model answers, and `core/gate.py` reads its output.
2. The pass table in `results/model_pass_table.json` says which features it may flag.
3. A flag makes one question eligible in `core/followups.py`.

### Three properties

1. The person answers first: `core/tests/test_gate.py::test_person_first`
2. Two questions at most: `core/tests/test_followups.py`
3. The ports agree: `worker/test/golden.test.ts`

## How OneAquaHealth is used

### The API

| Method | Route | What it does |
|---|---|---|
| GET | `/health` | alive |
| GET | `/api/creeks` | every creek |
| GET | `/api/city/{{creek_id}}` | one creek |
| POST | `/api/test/start` | a sitting |
| GET | `/api/fhir/referral/{{spot_id}}` | a referral |

### MCP tools

| Tool | What it answers |
|---|---|
| `list_creeks` | every creek |
| `get_creek_record` | one record |

## Evals

### Tests

<!--v:results/tests.json#/python-->10<!--/v--> Python tests and
<!--v:results/tests.json#/ts-->3<!--/v--> TypeScript suites.

## What is real and what is synthetic

Said plainly.

## Security and privacy

No names, no emails.
Uploads are deleted after 30 days.
What the host logs is in [data handling](docs/DATA_HANDLING.md).

## Tech stack

| Part | What |
|---|---|
| Web | Next.js |
| API | FastAPI |
| Worker | Cloudflare |
| Store | D1 |
| FHIR | SUSHI |

## Quickstart

```
make judge-check
```

## Running locally

Offline, with the demo data:

```
make dev
```

## For judges

Start here.

## Known weaknesses

Few people.

## How this was built

Read [the write-up](WRITEUP.md).

## Credits

Photos.

## Repo map

Folders.

## Licence

MIT.
"""

WRITEUP = """# Write-up

## Engineering challenges

Hard parts.

## The gate

Words.

## What we would do next

More.
"""

DEPLOY = """# Deploy

| Setting | Where | What |
|---|---|---|
| `QA_KEY` | Worker secret | tests |
| `EXPORT_TOKEN` | Worker secret | export |
| `NEXT_PUBLIC_API_ORIGIN` | build | API |
| `NEXT_PUBLIC_SITE_URL` | build | site |
| `ANTHROPIC_API_KEY` | .env | evals |
"""

ENV_EXAMPLE = """QA_KEY=change-me
EXPORT_TOKEN=change-me
NEXT_PUBLIC_API_ORIGIN=
NEXT_PUBLIC_SITE_URL=
ANTHROPIC_API_KEY=change-me
"""

ADR = """# {n}. A decision

## Status

Accepted.

## Context

Why.

## Decision

What.

## Consequences

Then.
"""

DEPENDABOT = """version: 2
updates:
  - package-ecosystem: uv
    directory: /
    schedule: {interval: weekly}
  - package-ecosystem: npm
    directories: [/apps/web, /worker]
    schedule: {interval: weekly}
  - package-ecosystem: github-actions
    directory: /
    schedule: {interval: weekly}
"""

PRECOMMIT = """repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: local
    hooks:
      - id: dashes
        name: no em or en dashes
        entry: uv run python scripts/check_dashes.py
        language: system
        pass_filenames: false
"""

SERVER = """from mcp.server.mcpserver import MCPServer

def build(server):
    @server.tool(description="Every creek (with ids).")
    def list_creeks():
        return {}

    @server.tool(
        description="One record.",
    )
    def get_creek_record(creek):
        return {}
"""

SHOT = (39, 84)


def png(path: Path, size: tuple[int, int] = SHOT, color: str = "white") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A small tree that has every block 23 and 24 item."""
    root = tmp_path
    write(root, "README.md", README)
    write(root, "docs/track_statement.md", STATEMENT + "\n")
    frames = [Image.new("RGB", (40, 30), c) for c in ("white", "black")]
    (root / "docs" / "screens").mkdir(parents=True)
    frames[0].save(root / "docs/screens/test.gif", save_all=True, append_images=frames[1:])
    for name in ("one", "two"):
        png(root / f"docs/screens/marks/{name}.jpg")
    for rel in ("core/gate.py", "core/followups.py", "results/model_pass_table.json"):
        write(root, rel, "x\n")
    write(root, "core/tests/test_gate.py", "def test_person_first():\n    pass\n")
    write(root, "core/tests/test_followups.py", "def test_two():\n    pass\n")
    write(root, "worker/test/golden.test.ts", "test('agree', () => {});\n")
    write(root, "docs/DATA_HANDLING.md", "What the host logs.\n")
    write(
        root,
        "worker/src/index.ts",
        'if (path === "/health") {}\nif (path === "/api/creeks") {}\n'
        'if (path.startsWith("/api/city/")) {}\nif (path === "/api/test/start") {}\n'
        'if (path.startsWith("/api/fhir/referral/")) {}\n',
    )
    write(root, "apps/mcp/server.py", SERVER)
    write(root, "Makefile", "dev:\n\techo dev\njudge-check:\n\techo j\ndiagrams:\n\techo d\n")
    write(root, ".github/workflows/check.yml", "env:\n  MERMAID_CLI: 1\n")
    write(root, "WRITEUP.md", WRITEUP)
    write(root, "DEPLOY.md", DEPLOY)
    write(root, ".env.example", ENV_EXAMPLE)
    for n in range(1, 9):
        write(root, f"docs/adr/{n:04d}-decision-{n}.md", ADR.format(n=n))
    write(root, ".github/dependabot.yml", DEPENDABOT)
    write(root, ".pre-commit-config.yaml", PRECOMMIT)
    for page in ("page.tsx", "about/page.tsx", "t/page.tsx", "walk/[id]/page.tsx"):
        write(root, f"apps/web/app/{page}", "export default function P() {}\n")
    for i, name in enumerate(
        ("landing", "about", "walk", "consent", "warm-up", "lesson", "test-item", "end-score"), 1
    ):
        png(root / f"docs/screens/{i:02d}-{name}.png")
    png(root / "docs/screens/09-landing-desktop.png", (128, 80))
    png(root / "docs/social-preview.png", di.SOCIAL_SIZE, "navy")
    return root


def edit(root: Path, rel: str, old: str, new: str) -> None:
    path = root / rel
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} is not in {rel}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


BLOCK_23_24 = [
    "screens",
    "gif",
    "lesson-marks",
    "diagrams",
    "readme-order",
    "social-image",
    "gate-steps",
    "properties",
    "writeup",
    "security",
    "api-table",
    "mcp-table",
    "tech-stack",
    "run-locally",
    "tests-paragraph",
    "deploy-doc",
    "adrs",
    "dependabot",
    "precommit",
]


@pytest.mark.parametrize("name", BLOCK_23_24)
def test_each_check_passes_on_a_tree_that_has_the_thing(repo: Path, name: str) -> None:
    assert di.CHECKS[name](repo) == []


@pytest.mark.parametrize("name", BLOCK_23_24)
def test_each_check_fails_on_an_empty_tree(tmp_path: Path, name: str) -> None:
    assert di.CHECKS[name](tmp_path)


def has(problems: list[str], words: str) -> bool:
    return any(words in p for p in problems)


# Block 23


def test_screens_catch_size_a_missing_screen_and_a_second_frame(repo: Path) -> None:
    big = repo / "docs/screens/02-about.png"
    big.write_bytes(big.read_bytes() + b"\0" * di.SCREEN_MAX_BYTES)
    assert has(di.check_screens(repo), "02-about.png is")
    big.unlink()
    assert has(di.check_screens(repo), "named for the screen 'about'")
    png(repo / "docs/screens/02-about.png", (40, 84))
    assert has(di.check_screens(repo), "not in one device frame")


def test_screens_need_every_screen_of_the_test_flow(repo: Path) -> None:
    (repo / "docs/screens/05-warm-up.png").unlink()
    assert has(di.check_screens(repo), "'warmup'")


def test_a_new_route_needs_its_own_screenshot(repo: Path) -> None:
    write(repo, "apps/web/app/accessibility/page.tsx", "x")
    assert has(di.check_screens(repo), "'accessibility'")


def test_the_gif_must_exist_be_small_and_move(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(di, "GIF_MAX_BYTES", 10)
    assert has(di.check_gif(repo), "over 10")
    monkeypatch.undo()
    Image.new("RGB", (4, 4)).save(repo / "docs/screens/test.gif")
    assert has(di.check_gif(repo), "one frame")
    (repo / "docs/screens/test.gif").unlink()
    assert has(di.check_gif(repo), "does not exist")
    edit(repo, "README.md", "docs/screens/test.gif", "https://cdn.example/test.gif")
    assert has(di.check_gif(repo), "not in the repo")


def test_two_lesson_photos_with_marks(repo: Path) -> None:
    (repo / "docs/screens/marks/two.jpg").unlink()
    assert di.check_lesson_marks(repo) == ["README.md shows 1 lesson photos with marks, not 2"]


@pytest.mark.parametrize(
    ("old", "new", "words"),
    [
        ("sequenceDiagram", "flowchart LR", "sequence diagram of the AI gate"),
        ("-->|answers|", "-->", None),
        ("  R -->|FHIR| A[Act]", "  R --> A[Done]", "five verbs"),
        ("P[Practitioner]", "P[Person]", "FHIR resource graph"),
    ],
)
def test_diagrams_need_each_of_the_three(repo: Path, old: str, new: str, words: str | None) -> None:
    edit(repo, "README.md", old, new)
    problems = di.check_diagrams(repo)
    assert problems if words else not problems
    if words:
        assert has(problems, words)


def test_diagrams_need_labelled_edges_and_ci_rendering(repo: Path) -> None:
    text = (repo / "README.md").read_text()
    for label in ("|lesson|", "|answers|", "|flags|", "|FHIR|"):
        text = text.replace(label, "")
    (repo / "README.md").write_text(text)
    assert has(di.check_diagrams(repo), "carry no labels")
    # CI renders only when a workflow installs tools/diagrams and runs make check with a diagrams
    # target that renders (render.mjs --check), or sets MERMAID_CLI.
    write(repo, ".github/workflows/check.yml", "run: make check\n")
    assert has(di.check_diagrams(repo), "does not render the diagrams")
    write(
        repo, ".github/workflows/check.yml", "run: cd tools/diagrams && npm ci\nrun: make check\n"
    )
    write(
        repo,
        "Makefile",
        "check: lint diagrams\ndiagrams:\n\tcd tools/diagrams && node render.mjs --check\n",
    )
    assert not has(di.check_diagrams(repo), "does not render the diagrams")
    write(
        repo, "Makefile", "check: lint\ndiagrams:\n\tcd tools/diagrams && node render.mjs --check\n"
    )
    assert has(di.check_diagrams(repo), "does not render the diagrams")


@pytest.mark.parametrize(
    ("old", "new", "words"),
    [
        (STATEMENT + "\n", "Another first line.\n", "1 track statement"),
        (
            "> **A creek observation should carry how well its observer sees.**",
            "> Two sentences here. And here.",
            "not one sentence",
        ),
        (
            "[![check](https://github.com/o/r/actions/workflows/check.yml/badge.svg)](https://github.com/o/r)\n"
            "![licence: MIT](https://img.shields.io/badge/licence-MIT-blue)",
            "",
            "3 badges",
        ),
        ("[![check](https://github.com/o/r/actions/workflows/check.yml/badge.svg)]", "[x]", None),
        ("Which creek is healthier?", "Which is better?", "4 the question"),
        ("photos/warmup/b.jpg", "photos/other/b.jpg", "two warm-up photos"),
        ("<details>", "<div>", "4 the answer in a details block"),
        ("<summary>The answer</summary>", "The answer", "no <summary>"),
        (", [judges](https://site.example/judges)", "", "5 three links"),
        ("docs/screens/test.gif", "docs/screens/test.png", "6 the GIF"),
        ("## Numbers at a glance", "## Numbers", "numbers at a glance"),
        ("## Gallery", "## Pictures", "the gallery"),
        ("## What the AI cannot do", "## Limits", "what the AI cannot do"),
        ("## How OneAquaHealth is used", "## OneAquaHealth", "how OneAquaHealth is used"),
        ("## What is real and what is synthetic", "## Data", "real versus synthetic"),
        ("make judge-check", "make check", "does not say make judge-check"),
        ("## Known weaknesses", "## Weak spots", "known weaknesses"),
        ("## Repo map", "## Folders", "repo map"),
        ("## Licence", "## Rights", "licence"),
    ],
)
def test_readme_order_names_each_missing_part(
    repo: Path, old: str, new: str, words: str | None
) -> None:
    assert di.check_readme_order(repo) == []
    edit(repo, "README.md", old, new)
    problems = di.check_readme_order(repo)
    if words is None:  # one badge is enough
        assert problems == []
    else:
        assert has(problems, words), problems


def test_readme_order_catches_two_sections_swapped(repo: Path) -> None:
    text = (repo / "README.md").read_text()
    credits = "## Credits\n\nPhotos.\n\n"
    text = text.replace(credits, "")
    text = text.replace("## Why trust", credits + "## Why trust")
    (repo / "README.md").write_text(text)
    problems = di.check_readme_order(repo)
    assert has(problems, "credits"), problems


def test_readme_top_block_must_sit_above_the_first_section(repo: Path) -> None:
    text = (repo / "README.md").read_text()
    top = "![The two-minute test, start to finish](docs/screens/test.gif)\n\n"
    text = text.replace(top, "").replace(
        "## Numbers at a glance\n", "## Numbers at a glance\n" + top
    )
    (repo / "README.md").write_text(text)
    assert has(di.check_readme_order(repo), "6 the GIF")


def test_social_image_must_be_1280_by_640_and_under_1_mb(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(di, "SOCIAL_MAX_BYTES", 10)
    assert has(di.check_social_image(repo), "1 MB or more")
    monkeypatch.undo()
    png(repo / "docs/social-preview.png", (1280, 641))
    assert has(di.check_social_image(repo), "no 1280 by 640 image")


# Block 24


def test_gate_steps_name_files_that_exist(repo: Path) -> None:
    (repo / "core/followups.py").unlink()
    assert has(di.check_gate_steps(repo), "names core/followups.py, which does not exist")
    edit(repo, "README.md", "3. A flag makes", "A flag makes")
    assert has(di.check_gate_steps(repo), "2 numbered steps")


def test_an_earlier_gate_heading_without_steps_does_not_hide_them(repo: Path) -> None:
    edit(
        repo,
        "README.md",
        "## Architecture\n",
        "## Architecture\n\n### The gate as a diagram\n\nSee below.\n",
    )
    assert di.check_gate_steps(repo) == []
    edit(repo, "README.md", "### The gate, the heart of it", "### The heart of it")
    assert has(di.check_gate_steps(repo), "has 0 numbered steps")


def test_adrs_may_carry_an_adr_prefix_and_a_plain_status_line(repo: Path) -> None:
    folder = repo / "docs" / "adr"
    for p in sorted(folder.glob("*.md")):
        p.rename(folder / f"ADR-{p.name}")
    edit(repo, "docs/adr/ADR-0001-decision-1.md", "## Status\n\nAccepted.", "Status: accepted")
    assert di.check_adrs(repo) == []


def test_gate_steps_must_name_the_gate_file(repo: Path) -> None:
    edit(repo, "README.md", "`core/gate.py` reads", "`core/followups.py` reads")
    assert has(di.check_gate_steps(repo), "never name core/gate.py")


def test_gate_step_without_a_file(repo: Path) -> None:
    edit(repo, "README.md", "in `results/model_pass_table.json` says", "says")
    assert has(di.check_gate_steps(repo), "gate step 2 names no file")


def test_properties_are_tied_to_tests_that_exist(repo: Path) -> None:
    edit(repo, "core/tests/test_gate.py", "test_person_first", "test_other")
    problems = di.check_properties(repo)
    assert has(problems, "not in that file") and has(problems, "2 properties")
    (repo / "worker/test/golden.test.ts").unlink()
    assert has(di.check_properties(repo), "which does not exist")


def test_writeup_needs_challenges_sections_and_a_link(repo: Path) -> None:
    edit(repo, "WRITEUP.md", "## Engineering challenges", "## Hard parts")
    assert has(di.check_writeup(repo), "engineering challenges")
    edit(repo, "README.md", "(WRITEUP.md)", "(docs/other.md)")
    assert has(di.check_writeup(repo), "does not link to WRITEUP.md")
    edit(repo, "WRITEUP.md", "## What we would do next", "What next")
    assert has(di.check_writeup(repo), "fewer than three sections")


def test_security_points_at_data_handling(repo: Path) -> None:
    (repo / "docs/DATA_HANDLING.md").unlink()
    assert has(di.check_security(repo), "which does not exist")
    edit(repo, "README.md", "[data handling](docs/DATA_HANDLING.md)", "a page")
    assert has(di.check_security(repo), "does not point at docs/DATA_HANDLING.md")


def test_api_table_routes_must_be_served(repo: Path) -> None:
    edit(repo, "README.md", "`/api/creeks`", "`/api/rivers`")
    assert has(di.check_api_table(repo), "/api/rivers, which no route")
    edit(repo, "README.md", "| GET | `/health` | alive |\n", "")
    assert has(di.check_api_table(repo), "fewer than 5")


def test_mcp_table_matches_the_server(repo: Path) -> None:
    edit(repo, "README.md", "| `get_creek_record` | one record |\n", "")
    assert has(di.check_mcp_table(repo), "leaves out the tool get_creek_record")
    edit(repo, "README.md", "`list_creeks`", "`list_rivers`")
    assert has(di.check_mcp_table(repo), "list_rivers, which apps/mcp/server.py does not define")


def test_tech_stack_needs_five_parts(repo: Path) -> None:
    edit(repo, "README.md", "| FHIR | SUSHI |\n", "")
    assert di.check_tech_stack(repo) == ["the tech stack lists 4 parts, fewer than 5"]


def test_running_locally_needs_offline_and_real_targets(repo: Path) -> None:
    edit(repo, "README.md", "make dev\n", "make serve\n")
    assert has(di.check_run_locally(repo), "make serve, which the Makefile lacks")
    edit(repo, "README.md", "Offline, with the demo data:", "With the demo data:")
    assert has(di.check_run_locally(repo), "how to run offline")


def test_tests_paragraph_counts_come_from_results(repo: Path) -> None:
    edit(repo, "README.md", "<!--v:results/tests.json#/ts-->3<!--/v-->", "3")
    assert has(di.check_tests_paragraph(repo), "1 counts traced")


def test_deploy_table_names_settings_the_code_uses(repo: Path) -> None:
    edit(repo, ".env.example", "EXPORT_TOKEN=change-me\n", "")
    assert has(di.check_deploy_doc(repo), "EXPORT_TOKEN, which no config")
    edit(repo, "DEPLOY.md", "| Setting |", "| Thing |")
    assert has(di.check_deploy_doc(repo), "no configuration table")


def test_deploy_table_needs_five_settings(repo: Path) -> None:
    edit(repo, "DEPLOY.md", "| `ANTHROPIC_API_KEY` | .env | evals |\n", "")
    assert di.check_deploy_doc(repo) == ["the configuration table has 4 rows, fewer than 5"]


def test_adrs_count_and_parts(repo: Path) -> None:
    edit(repo, "docs/adr/0003-decision-3.md", "## Consequences", "## Then")
    assert has(di.check_adrs(repo), "0003-decision-3.md has no Consequences part")
    (repo / "docs/adr/0008-decision-8.md").unlink()
    assert has(di.check_adrs(repo), "7 numbered ADRs")
    for n in range(8, 12):
        write(repo, f"docs/adr/{n:04d}-decision-{n}.md", ADR.format(n=n))
    # Eleven is fine: UPDATE_29 adds the iNaturalist record to UPDATE_24's 8 to 10.
    assert not has(di.check_adrs(repo), "numbered ADRs")


def test_dependabot_covers_every_ecosystem_and_folder(repo: Path) -> None:
    edit(repo, ".github/dependabot.yml", "[/apps/web, /worker]", "[/apps/web]")
    assert has(di.check_dependabot(repo), "leave out worker")
    edit(repo, ".github/dependabot.yml", "github-actions", "docker")
    assert has(di.check_dependabot(repo), "does not watch github-actions")
    edit(repo, ".github/dependabot.yml", "ecosystem: uv", "ecosystem: gomod")
    assert has(di.check_dependabot(repo), "Python dependencies")


def test_precommit_runs_ruff_and_the_dash_check(repo: Path) -> None:
    edit(repo, ".pre-commit-config.yaml", "scripts/check_dashes.py", "scripts/other.py")
    assert di.check_precommit(repo) == ["pre-commit does not run scripts/check_dashes.py"]


# Hardening


@pytest.fixture
def fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only the commit 'abcdef1' counts as measured after the base commit."""

    def problem(root: Path, sha: str | None, what: str) -> str | None:
        return None if sha == "abcdef1" else f"{what} was measured at {sha}, before the base"

    monkeypatch.setattr(di, "commit_problem", problem)
    monkeypatch.setattr(di, "base_time", lambda root: datetime(2026, 9, 24, 5, 46, tzinfo=UTC))


def reviews(root: Path) -> Path:
    folder = root.joinpath("docs", "internal", "reviews")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def critic(sev: str, sha: str = "abcdef1") -> str:
    return f"# Critic\n\nCommit: {sha}\nHighest severity: {sev}\n\nNotes.\n"


def test_the_second_review_reads_the_finished_repo(tmp_path: Path, fresh: None) -> None:
    folder = reviews(tmp_path)
    (folder / "REVIEW_01.md").write_text("Read at commit 1111111.\n")
    assert has(di.check_review(tmp_path), "1 adversarial reviews")
    (folder / "REVIEW_02.md").write_text("They read the repo at commit 2222222 on harden.\n")
    assert has(di.check_review(tmp_path), "measured at 2222222")
    (folder / "REVIEW_03.md").write_text("They read the repo at commit abcdef1 on depth.\n")
    assert di.check_review(tmp_path) == []


def critic2(sha: str = "abcdef1", checked: str = "", resolution: str = "") -> str:
    return (
        f"# Critic\n\nHighest severity: minor\nCommit: {sha}\n\nNotes.\n\n"
        f"## Checked by independent skeptics\n\n{checked}\n## Resolution\n\n{resolution}"
    )


def test_critic_rounds_new_rule_no_confirmed_major_and_every_minor_resolved(
    tmp_path: Path, fresh: None
) -> None:
    # UPDATE_30 section 2: same commit, no confirmed major, each confirmed minor fixed or listed.
    folder = reviews(tmp_path)
    (tmp_path / "README.md").write_text(
        "# R\n\n## Known weaknesses\n\n- Walks live in one tab.\n\n## Credits\n"
    )
    (folder / "CRITIC_01.md").write_text(critic2())
    assert has(di.check_critics(tmp_path), "1 critic rounds")
    (folder / "CRITIC_02.md").write_text(critic2(checked="- X01: confirmed, major.\n"))
    assert has(di.check_critics(tmp_path), "X01 is confirmed at major")
    (folder / "CRITIC_03.md").write_text(critic2(checked="- Y01: not confirmed, major.\n"))
    (folder / "CRITIC_04.md").write_text(critic2(checked="- Z01: confirmed, minor.\n"))
    assert has(di.check_critics(tmp_path), "Z01 has no Resolution line")
    (folder / "CRITIC_04.md").write_text(
        critic2(checked="- Z01: confirmed, minor.\n", resolution='- Z01: known weakness: "Nope."\n')
    )
    assert has(di.check_critics(tmp_path), "not in the README's Known weaknesses")
    (folder / "CRITIC_04.md").write_text(
        critic2(
            checked="- Z01: confirmed, minor.\n",
            resolution='- Z01: known weakness: "Walks live in one tab."\n',
        )
    )
    assert di.check_critics(tmp_path) == []
    (folder / "CRITIC_05.md").write_text(critic2(sha="9999999"))
    assert has(di.check_critics(tmp_path), "measured at 9999999")
    assert has(di.check_critics(tmp_path), "read different commits")
    (folder / "CRITIC_05.md").write_text(
        critic2().replace("## Checked by independent skeptics", "")
    )
    assert has(di.check_critics(tmp_path), "no section 'Checked by independent skeptics'")


def judge_sim(n_judges: int, sha: str = "abcdef1") -> str:
    rows = "\n".join(f"| Judge {i} | 6 | 7 | 5 | 6 | 5 | 5.85 |" for i in range(n_judges))
    return (
        f"# Judge simulation\n\nThe README at commit {sha}.\n\n"
        "| Judge | Impact | Innovation | Technical | Usability | Feasibility | Weighted |\n"
        "|---|---|---|---|---|---|---|\n"
        f"{rows}\n| **Mean** | 6.00 | 7.00 | 5.00 | 6.00 | 5.00 | 5.85 |\n"
    )


def test_the_judge_simulation_is_rerun_with_six_judges(tmp_path: Path, fresh: None) -> None:
    folder = reviews(tmp_path)
    (folder / "JUDGE_SIM_00_before.md").write_text(judge_sim(6, "1111111"))
    assert has(di.check_judge_sim(tmp_path), "no rerun")
    (folder / "JUDGE_SIM_01_after.md").write_text(judge_sim(5))
    assert has(di.check_judge_sim(tmp_path), "scores 5 judges, not 6")
    (folder / "JUDGE_SIM_01_after.md").write_text(judge_sim(6, "2222222"))
    assert has(di.check_judge_sim(tmp_path), "measured at 2222222")
    (folder / "JUDGE_SIM_01_after.md").write_text(judge_sim(6))
    assert di.check_judge_sim(tmp_path) == []


def harden(root: Path, name: str, doc: Mapping[str, object]) -> None:
    write(root, f"results/harden/{name}", json.dumps(doc))


def screen(path: str, violations: list[object] | None = None, status: int = 200) -> dict:
    return {"path": path, "viewport": "phone", "status": status, "error": "",
            "violations": violations or []}  # fmt: skip


def test_axe_clean_with_an_accessibility_page(tmp_path: Path, fresh: None) -> None:
    write(tmp_path, "apps/web/app/accessibility/page.tsx", "x")
    good = {"commit": "abcdef1", "screens": [screen("/"), screen("/accessibility")]}
    harden(tmp_path, "axe.json", good)
    assert di.check_axe(tmp_path) == []
    harden(tmp_path, "axe.json", {**good, "commit": "1111111"})
    assert has(di.check_axe(tmp_path), "measured at 1111111")
    harden(tmp_path, "axe.json", {**good, "screens": [screen("/", [{"id": "color-contrast"}])]})
    problems = di.check_axe(tmp_path)
    assert has(problems, "color-contrast on /") and has(
        problems, "does not check the /accessibility"
    )
    harden(tmp_path, "axe.json", {**good, "screens": [screen("/accessibility", status=404)]})
    assert has(di.check_axe(tmp_path), "could not check")
    (tmp_path / "apps/web/app/accessibility/page.tsx").unlink()
    harden(tmp_path, "axe.json", good)
    assert has(di.check_axe(tmp_path), "no /accessibility page")


def lh_page(url: str, perf: int = 97, a11y: int = 100, status: int = 200) -> dict:
    median = {"scores": {"performance": perf, "accessibility": a11y}}
    return {"url": url, "status": status, "median": median if status == 200 else None}


def test_lighthouse_every_page_loads_and_scores(tmp_path: Path, fresh: None) -> None:
    harden(tmp_path, "lighthouse.json", {"commit": "abcdef1", "pages": [lh_page("/")]})
    assert di.check_lighthouse(tmp_path) == []
    pages = [lh_page("/"), lh_page("/city", status=404), lh_page("/walk", perf=80, a11y=94)]
    harden(tmp_path, "lighthouse.json", {"commit": "abcdef1", "pages": pages})
    problems = di.check_lighthouse(tmp_path)
    assert has(problems, "did not measure /city")
    assert has(problems, "/walk: performance 80, under 90")
    assert has(problems, "/walk: accessibility 94, under 95")


def test_axe_and_lighthouse_must_measure_every_page(tmp_path: Path, fresh: None) -> None:
    for page in (
        "page.tsx",
        "t/page.tsx",
        "walk/page.tsx",
        "walk/[id]/page.tsx",
        "share/[score]/page.tsx",
        "accessibility/page.tsx",
        "how-we-know/page.tsx",
    ):
        write(tmp_path, f"apps/web/app/{page}", "x")  # fmt: skip
    paths = ["/", "/t", "/walk", "/share/12", "/accessibility", "/how-we-know?x=1"]
    harden(tmp_path, "axe.json", {"commit": "abcdef1", "screens": [screen(p) for p in paths]})
    assert di.check_axe(tmp_path) == []
    site = "https://second-look-79t.pages.dev"
    harden(tmp_path, "lighthouse.json",
           {"commit": "abcdef1", "pages": [lh_page(site + p) for p in paths]})  # fmt: skip
    assert di.check_lighthouse(tmp_path) == []
    for gone, slug in (("/walk", "walk"), ("/", "landing"), ("/t", "t"), ("/share/12", "share")):
        left = [p for p in paths if p != gone]
        harden(tmp_path, "axe.json", {"commit": "abcdef1", "screens": [screen(p) for p in left]})
        assert di.check_axe(tmp_path) == [f"axe never measured the page '{slug}'"], gone
        doc = {"commit": "abcdef1", "pages": [lh_page(site + p) for p in left]}
        harden(tmp_path, "lighthouse.json", doc)
        assert di.check_lighthouse(tmp_path) == [f"Lighthouse never measured the page '{slug}'"]


def test_lighthouse_counts_a_page_that_did_not_load(tmp_path: Path, fresh: None) -> None:
    # A page that answered 404 is not measured, even when the file carries scores for it.
    page = lh_page("/")
    harden(tmp_path, "lighthouse.json", {"commit": "abcdef1", "pages": [{**page, "status": 404}]})
    assert has(di.check_lighthouse(tmp_path), "did not measure /")


def load_doc(**change: object) -> dict[str, object]:
    doc: dict[str, object] = {
        "finished_utc": "2026-09-25T00:00:00Z",
        "sessions_started": 250,
        "sessions_done": 250,
        "session_error_count": 0,
        "endpoints": [{"endpoint": "GET /", "requests": 250, "ok": 250}],
    }
    return {**doc, **change}


def test_the_load_test_is_fresh_and_clean(tmp_path: Path, fresh: None) -> None:
    write(tmp_path, "results/harden/load_live.json", json.dumps(load_doc()))
    assert di.check_load(tmp_path) == []
    for change, words in (
        ({"finished_utc": "2026-09-23T04:45:26Z"}, "run it again"),
        ({"sessions_done": 249}, "finished 249 of 250"),
        ({"session_error_count": 2}, "2 session errors"),
        ({"endpoints": [{"endpoint": "GET /", "requests": 250, "ok": 249}]}, "249 of 250"),
    ):
        write(tmp_path, "results/harden/load_live.json", json.dumps(load_doc(**change)))
        assert has(di.check_load(tmp_path), words), change


def flaky_run(n: int, web: int | None = 0) -> dict[str, object]:
    return {"run": n, "suites": {"pytest": {"code": 0}, "web e2e": {"code": web}}}


def test_no_flaky_tests_over_three_full_runs(tmp_path: Path, fresh: None) -> None:
    runs = [flaky_run(n) for n in (1, 2, 3)]
    harden(tmp_path, "flaky.json", {"commit": "abcdef1", "runs": runs, "flaky": []})
    assert di.check_flaky(tmp_path) == []
    harden(tmp_path, "flaky.json", {"commit": "abcdef1", "runs": runs[:2], "flaky": []})
    assert has(di.check_flaky(tmp_path), "2 runs, not 3")
    harden(tmp_path, "flaky.json", {"commit": "abcdef1", "runs": runs, "flaky": ["test_x"]})
    assert has(di.check_flaky(tmp_path), "test_x")
    runs[2] = flaky_run(3, None)
    harden(tmp_path, "flaky.json", {"commit": "abcdef1", "runs": runs, "flaky": []})
    assert has(di.check_flaky(tmp_path), "run 3: web e2e exited None")


def test_every_readme_command_was_executed(tmp_path: Path, fresh: None) -> None:
    write(tmp_path, "README.md", "Run `make judge-check`, then `make check`, not `make deploy`.\n")
    ran = [{"command": "make judge-check", "ran": True, "result": "pass"}]
    harden(tmp_path, "commands.json", {"commit": "abcdef1", "commands": ran})
    assert di.check_readme_commands(tmp_path) == ["never executed: make check"]
    ran.append({"command": "make check", "ran": False, "result": "not run"})
    harden(tmp_path, "commands.json", {"commit": "abcdef1", "commands": ran})
    assert di.check_readme_commands(tmp_path) == ["not run: make check"]
    ran[1] = {"command": "make check", "ran": True, "result": "pass"}
    harden(tmp_path, "commands.json", {"commit": "abcdef1", "commands": ran})
    assert di.check_readme_commands(tmp_path) == []  # make deploy is never run, by design


def test_a_link_check_with_no_dead_link(tmp_path: Path, fresh: None) -> None:
    rows = [{"file": "README.md", "line": 3, "target": "docs/x.md", "status": "ok"}]
    harden(tmp_path, "links.json", {"commit": "abcdef1", "rows": rows})
    assert di.check_links(tmp_path) == []
    rows.append({"file": "README.md", "line": 9, "target": "docs/gone.md", "status": "dead"})
    harden(tmp_path, "links.json", {"commit": "abcdef1", "rows": rows})
    assert di.check_links(tmp_path) == ["dead link docs/gone.md in README.md:9"]


def test_a_stale_or_missing_results_file_fails(tmp_path: Path, fresh: None) -> None:
    for name, check in (
        ("axe.json", di.check_axe),
        ("lighthouse.json", di.check_lighthouse),
        ("flaky.json", di.check_flaky),
        ("links.json", di.check_links),
        ("commands.json", di.check_readme_commands),
    ):
        assert has(check(tmp_path), "is missing or is not JSON"), name


def test_commit_problem_uses_git_ancestry(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    assert di.commit_problem(root, di.BASE_COMMIT, "x") is None
    assert "before" in (di.commit_problem(root, "b876a2b", "x") or "")
    assert "does not have" in (di.commit_problem(root, "0000000", "x") or "")
    assert "names no commit" in (di.commit_problem(root, None, "x") or "")


# The submission pack


@pytest.mark.parametrize(
    ("summary", "ok"),
    [
        ("submit-check: 2 failed: video_link, repo_public", True),
        ("submit-check: 1 failed: repo_public", True),
        ("submit-check: 0 failed: none", True),
        ("submit-check: 3 failed: video_link, repo_public, verify_claims", False),
        ("submit-check: 1 failed: license", False),
        ("Traceback (most recent call last):", False),
    ],
)
def test_submit_check_red_only_on_video_and_public(tmp_path: Path, summary: str, ok: bool) -> None:
    out = f"PASS  track_statement\n{summary}\nmake: *** [submit-check] Error 1\n"
    problems = di.check_submit_pack(tmp_path, lambda root: (1, out))
    assert (problems == []) is ok


ALEX = """# Alex: what only you can do

1. **By Fri Sep 25, 20 minutes: record your voice.** Read the teleprompter.

2. **Wed Sep 30, morning: go public.** On `main`.
   Then open the pull request.

If you want to, tell their team.
"""


def done_file(root: Path, humans: int) -> None:
    rows = "\n".join(
        f"| D{n:02d} | human step | HUMAN | | | | `test -f x{n}` |" for n in range(1, humans + 1)
    )
    header = (
        "| ID | Item | Kind | Date | Outside cause | Cause test | Command |\n"
        "|---|---|---|---|---|---|---|\n"
    )
    # Joined from parts, so the go-public rewrite of the working notes folder leaves it alone.
    write(root, "/".join(("docs", "internal", "DONE.md")), header + rows + "\n")


def test_alex_todo_holds_only_dated_human_steps(tmp_path: Path) -> None:
    write(tmp_path, "docs/ALEX_TODO.md", ALEX)
    done_file(tmp_path, 2)
    assert di.check_alex_todo(tmp_path) == []
    done_file(tmp_path, 1)
    assert has(di.check_alex_todo(tmp_path), "2 steps, more than the 1 HUMAN items")
    done_file(tmp_path, 3)
    edit(tmp_path, "docs/ALEX_TODO.md", "Read the teleprompter.", "A session lays it over.")
    assert has(di.check_alex_todo(tmp_path), "step 1 mentions 'A session'")
    edit(tmp_path, "docs/ALEX_TODO.md", "**Wed Sep 30, morning:", "**Later:")
    assert has(di.check_alex_todo(tmp_path), "step 2 gives no date or day")


# Dated items


def test_data_lock_needs_an_entry_after_the_lock(tmp_path: Path) -> None:
    before = {"kind": "data_lock", "ts_utc": "2026-09-27T23:00:00Z"}
    write(tmp_path, "audit/log.jsonl", json.dumps(before) + "\n")
    assert di.check_data_lock(tmp_path)
    after = {"kind": "data_lock", "ts_utc": "2026-09-28T01:00:00Z"}
    write(tmp_path, "audit/log.jsonl", json.dumps(before) + "\n" + json.dumps(after) + "\n")
    assert di.check_data_lock(tmp_path) == []


def analysis(when: str, synthetic: bool = False, status: str = "descriptive") -> str:
    return json.dumps(
        {"generated_at_utc": when, "synthetic": synthetic, "primary": {"status": status}}
    )


def test_the_analysis_runs_once_on_real_data_after_the_lock(tmp_path: Path) -> None:
    write(tmp_path, "results/usability_synthetic.json", analysis("2026-09-22T00:00:00Z", True))
    assert has(di.check_analysis_once(tmp_path), "0 real analysis results")
    write(tmp_path, "results/usability_20260927.json", analysis("2026-09-27T20:00:00Z"))
    assert has(di.check_analysis_once(tmp_path), "before the lock")
    (tmp_path / "results/usability_20260927.json").unlink()
    write(tmp_path, "results/usability_20260928.json", analysis("2026-09-28T02:00:00Z"))
    assert di.check_analysis_once(tmp_path) == []
    write(tmp_path, "results/usability_20260929.json", analysis("2026-09-29T02:00:00Z"))
    assert has(di.check_analysis_once(tmp_path), "2 real analysis results")


@pytest.mark.parametrize(
    ("status", "ok"),
    [
        ("descriptive", True),
        ("confirmatory", True),
        ("not computed: an arm is empty", True),
        (None, False),
        ("", False),
        ("significant", False),
    ],
)
def test_the_analysis_says_what_kind_of_result_it_is(
    tmp_path: Path, status: str | None, ok: bool
) -> None:
    doc = json.loads(analysis("2026-09-28T02:00:00Z"))
    doc["primary"] = {} if status is None else {"status": status}
    write(tmp_path, "results/usability_20260928.json", json.dumps(doc))
    problems = di.check_analysis_once(tmp_path)
    assert (problems == []) is ok, problems
    if not ok:
        assert problems == [
            "usability_20260928.json does not say whether it is a description or a test"
        ]


def test_the_sandbox_repush_needs_a_push_after_the_lock(tmp_path: Path) -> None:
    old = {"ts_utc": "2026-09-21T06:53:46Z", "action": "create"}
    write(tmp_path, "fhir/sandbox_ledger.jsonl", json.dumps(old) + "\n")
    assert di.check_sandbox_repush(tmp_path)
    new = {"ts_utc": "2026-09-28T02:00:00Z", "action": "create"}
    write(tmp_path, "fhir/sandbox_ledger.jsonl", json.dumps(old) + "\n" + json.dumps(new) + "\n")
    assert di.check_sandbox_repush(tmp_path) == []


# Human items


def test_the_voice_recording_is_long_enough(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SECOND_LOOK_MEDIA", str(tmp_path))
    assert has(di.check_voice(tmp_path, lambda p: 200.0), "no recording")
    write(tmp_path, "voice/take1.m4a", "audio")
    assert has(di.check_voice(tmp_path, lambda p: 30.0), "runs 30 s")
    assert di.check_voice(tmp_path, lambda p: 200.0) == []


def fake_get(status: int, text: str = "") -> Callable[[str], tuple[int, str]]:
    return lambda url: (status, text)


def test_the_video_link_is_in_both_files_and_answers(tmp_path: Path) -> None:
    write(tmp_path, "README.md", "Video: https://youtu.be/abc\n")
    write(tmp_path, "docs/devpost.md", "Video: [VIDEO LINK]\n")
    assert has(di.check_video_link(tmp_path, fake_get(200)), "docs/devpost.md has no line")
    write(tmp_path, "docs/devpost.md", "Video: https://youtu.be/abc\n")
    assert di.check_video_link(tmp_path, fake_get(200)) == []
    assert has(di.check_video_link(tmp_path, fake_get(404)), "answered 404")


@pytest.mark.parametrize(
    ("link", "asked"),
    [
        ("https://youtu.be/abc", "https://www.youtube.com/oembed?format=json&url=https%3A%2F%2Fyoutu.be%2Fabc"),
        ("https://www.youtube.com/watch?v=abc", "https://www.youtube.com/oembed?format=json&url="),
        ("https://m.youtube.com/watch?v=abc", "https://www.youtube.com/oembed?format=json&url="),
        ("https://vimeo.com/123", "https://vimeo.com/123"),
        ("https://notyoutube.com/abc", "https://notyoutube.com/abc"),
    ],
)  # fmt: skip
def test_a_youtube_link_is_asked_through_oembed(tmp_path: Path, link: str, asked: str) -> None:
    # YouTube's watch page answers 200 for a video that is not there; its oEmbed answers 400.
    for rel in ("README.md", "docs/devpost.md"):
        write(tmp_path, rel, f"Video: {link}\n")
    seen: list[str] = []

    def get(url: str) -> tuple[int, str]:
        seen.append(url)
        return (400, "") if "oembed" in url else (200, "")

    problems = di.check_video_link(tmp_path, get)
    assert len(seen) == 1 and seen[0].startswith(asked)
    assert (problems == []) is ("oembed" not in asked)


def devpost_page(hackathon: str, site: str = "https://second-look-79t.pages.dev") -> str:
    """The shape of a real Devpost project page: links in the story, then the submissions list."""
    return (
        f'<div id="app-details-left"><a href="{site}">Try it out</a></div>'
        '<div id="submissions" class="section"><h4>Submitted to</h4>'
        f'<ul class="software-list-with-thumbnail"><li><a href="https://{hackathon}/">'
        "A hackathon</a></li></ul></div>"
        '<section id="app-team"><ul><li>A person</li></ul></section>'
    )


OURS = devpost_page("oneaquahealth-ieee-hackathon.devpost.com")
# devpost.com/software/second-look is another team's "Second Look", submitted elsewhere.
THEIRS = devpost_page("mac-a-thon-2026.devpost.com", site="https://github.com/someone/else")


def test_devpost_page_and_submission(tmp_path: Path) -> None:
    write(tmp_path, "docs/devpost.md", "Paste from here.\n")
    assert di.check_devpost_page(tmp_path, fake_get(200, OURS))
    write(tmp_path, "docs/devpost.md", "Page: https://devpost.com/software/second-look-x1\n")
    assert di.check_devpost_page(tmp_path, fake_get(200, OURS)) == []
    assert di.check_devpost_page(tmp_path, fake_get(404, OURS))
    assert has(di.check_devpost_page(tmp_path, fake_get(200, THEIRS)), "not our project page")
    assert has(di.check_devpost_submitted(tmp_path, fake_get(200, "Built with")), "not say")
    assert di.check_devpost_submitted(tmp_path, fake_get(200, OURS)) == []


def test_a_page_submitted_to_another_hackathon_does_not_count(tmp_path: Path) -> None:
    write(tmp_path, "docs/devpost.md", "Page: https://devpost.com/software/second-look\n")
    assert has(di.check_devpost_submitted(tmp_path, fake_get(200, THEIRS)), "does not say")
    assert has(di.check_devpost_submitted(tmp_path, fake_get(200, THEIRS)), "not our project")
    # Our page, submitted elsewhere, with our hackathon named in the story above the list.
    story = devpost_page("mac-a-thon-2026.devpost.com").replace(
        "Try it out", "Built for oneaquahealth-ieee-hackathon.devpost.com"
    )
    problems = di.check_devpost_submitted(tmp_path, fake_get(200, story))
    assert len(problems) == 1 and "does not say it was submitted to" in problems[0]


def test_main_prints_the_first_gap_last_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert di.main(["gif", "--root", str(tmp_path)]) == 1
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert last == "done-item gif: 1 missing, first: README.md shows no GIF"
    assert di.main(["--list"]) == 0


def test_the_invasive_list_counts_once_a_plant_with_a_taxon_id_is_approved(tmp_path: Path) -> None:
    pack = "content/regions/california-bay-area.yaml"
    assert has(di.check_invasive_list(tmp_path), "no invasive plant")
    write(tmp_path, pack, "region: california-bay-area\ninvasive_plants: []\n")
    assert has(di.check_invasive_list(tmp_path), "no invasive plant")
    write(tmp_path, pack, "invasive_plants:\n  - latin_name: Arundo donax\n")
    assert has(di.check_invasive_list(tmp_path), "no invasive plant")
    write(
        tmp_path,
        pack,
        "invasive_plants:\n  - latin_name: Arundo donax\n    inaturalist_taxon_id: 64017\n",
    )
    assert di.check_invasive_list(tmp_path) == []


@pytest.mark.skipif(
    not Path(__file__)
    .resolve()
    .parents[2]
    .joinpath("docs", "internal", "PANEL_STUDY.md")
    .is_file(),
    reason="the working notes were removed at go-public",
)
def test_the_panel_study_checks_codes_against_finished_sessions_before_paying(
    tmp_path: Path,
) -> None:
    # REVIEW_03 R06: the completion code is in the page source, so a code alone proves nothing.
    root = Path(__file__).resolve().parents[2]
    assert di.check_panel_prep(root) == []
    study = (root / "docs" / "internal" / "PANEL_STUDY.md").read_text(encoding="utf-8")
    write(tmp_path, "docs/internal/PANEL_STUDY.md", study.replace("Before you approve", "Then"))
    assert has(di.check_panel_prep(tmp_path), "the check of submitted codes against make panel")
    write(tmp_path, "docs/internal/PANEL_STUDY.md", study.replace("page source", "page"))
    assert has(di.check_panel_prep(tmp_path), "visible in the page source")


# UPDATE_29: a tree that has every item, as block 23 and 24 have one (REVIEW_03 R51)

OTS_MAGIC = b"\x00OpenTimestamps\x00\x00Proof\x00"
UPDATE_29_README = """Track 3. What the model may do: [the model card](docs/MODEL_CARD.md).

# Second Look

The numbers cite results/mutation.json, and `make reproduce` grades every AI number again.
The one real analysis: <!--v:results/usability_20260928.json#/primary/status-->x<!--/v-->.
The trust table: `.venv/bin/ots verify proofs/audit-head-2026-09-24.ots`.
An iNaturalist context line on each creek. The report: docs/REPORT.pdf.

### Contributed back

- https://github.com/hl7-eu/oah/pull/1
- https://github.com/hl7-eu/oah/issues/2
- https://github.com/hl7-eu/oah/issues/3
- https://github.com/hl7-eu/oah/issues/4

## Licence

MIT.
"""
PANEL_STUDY = """# Panel study

Study title: Second Look. Description for participants: a creek test.
It takes 5 minutes, paid at the panel's minimum hourly rate.
Screening: 18 or older, fluent in English. Device: a phone or a laptop.
Target: 80 completed sessions. Link: https://second-look-79t.pages.dev/t?src=panel
Watch with make panel-status, which reads /api/test/counts. Completion code: C1A2B3.
Before you approve any payment, compare the codes with make panel-status. The code is
visible in the page source, and the analysis counts only finished sessions.
"""
UPDATE_29_MAKEFILE = (
    "panel-status:\n\techo counts\n"
    "report-pdf:\n\techo pdf\n"
    "judge-check:  # its second step is make reproduce\n\tuv run python scripts/judge_check.py\n"
    "reproduce:\n\t@echo reproduce: 1 file regraded\n"
)
JUDGE_CHECK = """def step_reproduce(root, env):
    return run(["make", "--no-print-directory", "reproduce"], root, env)


def main():
    for make in (
        lambda: step_tests(root, env),
        lambda: step_reproduce(root, env),
    ):
        make()
"""
ANCHOR_JOB = """#!/usr/bin/env bash
RUN="'$UV' run python scripts/anchor_audit_head.py; '$UV' run python scripts/ots_status.py"
cat > "$PLIST" <<PLIST_END
    <string>$RUN</string>
PLIST_END
"""
THREAT_TESTS = [f"tests/test_{n}.py" for n in ("one", "two", "three", "four")]


def git(root: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false"]
    proc = subprocess.run(
        ["git", *who, *args], cwd=root, env=env, capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


@pytest.fixture
def update29(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A small tree that has every UPDATE_29 item. gh is not asked: every issue reads open."""
    root = tmp_path
    monkeypatch.setattr(di, "github_state", lambda kind, number: "open")
    write(root, "README.md", UPDATE_29_README)
    write(root, "Makefile", UPDATE_29_MAKEFILE)
    locale = {
        "consent_panel": di.PANEL_SENTENCE,
        "verify_what": "OpenTimestamps is a public timestamp service.",
        "inat_none": "No recent sightings on record.",
        "credits_inat": "Plant photos from iNaturalist.",
    }
    write(root, "content/locales/en.json", json.dumps(locale))
    # panel-prep
    write(root, "apps/web/lib/panel.ts", 'export const PANEL_COMPLETION_CODE = "C1A2B3";\n')
    # Built from parts, as done_items builds them, so the go-public rewrite leaves them alone.
    write(root, "/".join(("docs", "internal", "PANEL_STUDY.md")), PANEL_STUDY)
    write(
        root,
        "apps/web/tests/panel.spec.ts",
        "await page.goto(`/t?src=panel`); // consent-panel, panel-code, PROLIFIC_PID, not panel\n",
    )
    for rel in ("apps/api/study.py", "worker/src/index.ts", "apps/web/lib/session.ts"):
        write(root, rel, 'SOURCE_LABELS = ["poster", "panel"]\n')
    write(root, "docs/deviations.md", "- 2026-09-24: the panel study.\n")
    # panel-analysis: the three tests it runs
    for rel in (
        "evals/tests/test_panel_source.py",
        "evals/tests/test_usability_refusal.py",
        "apps/api/tests/test_panel.py",
    ):
        write(root, rel, "def test_it():\n    assert True\n")
    # human-row
    real = {
        "synthetic": False,
        "generated_at_utc": "2026-09-28T02:00:00Z",
        "primary": {"status": "descriptive"},
    }
    write(root, "results/usability_20260928.json", json.dumps(real))
    # ots
    for rel in ("prereg-v1.tag.ots", "analysis_plan.md.ots", "audit-head-2026-09-24.ots"):
        (root / "proofs").mkdir(exist_ok=True)
        (root / "proofs" / rel).write_bytes(OTS_MAGIC + b"\x01")
    write(root, "scripts/install_anchor_job.sh", ANCHOR_JOB)
    # verify-page
    write(root, "apps/web/app/verify/page.tsx", "export default function Verify() {}\n")
    # reproduce
    write(root, "scripts/judge_check.py", JUDGE_CHECK)
    write(root, "evals/fixtures/raw/sweep.jsonl", "{}\n")
    # mutation and lighthouse-landing
    modules = {t: {"score_percent": 90} for t in di.MUTATION_TARGETS}
    write(root, "results/mutation.json", json.dumps({"modules": modules}))
    scores = {"performance": 96, "accessibility": 100, "best-practices": 100, "seo": 100}
    write(root, "results/lighthouse_landing.json", json.dumps({"median": {"scores": scores}}))
    # model-card, threat-model, data-card, report-pdf
    write(
        root,
        "docs/MODEL_CARD.md",
        "# Model card\n\n## What it may do\n\n## What it may not do\n\n## The pass table\n\n"
        "## The benchmark\n\n## Failure cases\n\n## Cost\n\n## The gate\n",
    )
    for rel in THREAT_TESTS:
        write(root, rel, "def test_it():\n    pass\n")
    named = ", ".join(f"`{t}`" for t in [*THREAT_TESTS, "apps/web/tests/panel.spec.ts"])
    write(
        root,
        "docs/THREAT_MODEL.md",
        "# Threat model\n\nAssets: the study table.\n\n"
        f"Attackers: a participant, a competitor, a judge, the model.\n\nTests: {named}.\n",
    )
    write(root, "docs/DATA_CARD.md", "# Data card\n\n## Source\n\n## Licence\n\n## Labels\n")
    (root / "docs" / "REPORT.pdf").write_bytes(b"%PDF-1.4\n" + b"/Type /Page\n" * 6)
    write(root, "docs/devpost.md", "The report: docs/REPORT.pdf.\n")
    # second-labeller
    write(root, "photos/labels_alex.csv", "photo_id,label\n")
    write(root, "photos/labels_rachel.csv", "photo_id,label\n")
    write(root, "results/kappa.json", "{}\n")
    # inaturalist
    write(root, "docs/THIRD_PARTY.md", "iNaturalist's public API.\n")
    write(root, "scripts/cache_inaturalist.py", "print('daily')\n")
    write(root, "docs/adr/0011-inaturalist-context.md", "# iNaturalist context\n")
    web = "apps/web/components"
    write(root, f"{web}/InatContext.tsx", "export function InatContext({ creek }) {}\n")
    write(root, f"{web}/CityView.tsx", "export function CityView() { return <InatContext />; }\n")
    write(root, f"{web}/SpotRecord.tsx", "export function Spot() { return <InatContext />; }\n")
    write(root, f"{web}/LocationStep.tsx", "export function L() { return 'coordinates'; }\n")
    # rerun-after-update: each review, judge simulation and critic names a commit with the files
    git(root, "init", "-q")
    git(root, "add", *di.UPDATE_29_FILES)
    git(root, "commit", "-q", "-m", "UPDATE_29 files")
    sha = git(root, "rev-parse", "--short", "HEAD")
    for name in ("REVIEW_01", "JUDGE_SIM_01", "CRITIC_01", "CRITIC_02"):
        (reviews(root) / f"{name}.md").write_text(f"# {name}\n\nCommit: {sha}\n")
    return root


UPDATE_29 = [
    "panel-prep",
    "panel-analysis",
    "human-row",
    "contributed-back",
    "ots",
    "verify-page",
    "reproduce",
    "mutation",
    "lighthouse-landing",
    "model-card",
    "threat-model",
    "report-pdf",
    "data-card",
    "second-labeller",
    "inaturalist",
    "rerun-after-update",
]


@pytest.mark.parametrize("name", UPDATE_29)
def test_each_update_29_check_passes_on_a_tree_that_has_the_thing(
    update29: Path, name: str
) -> None:
    assert di.CHECKS[name](update29) == []


@pytest.mark.parametrize("name", UPDATE_29)
def test_each_update_29_check_fails_on_an_empty_tree(tmp_path: Path, name: str) -> None:
    assert di.CHECKS[name](tmp_path)


def test_every_check_is_called_by_a_test() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    listed = {*BLOCK_23_24, *UPDATE_29}
    untested = [
        name
        for name, check in di.CHECKS.items()
        if name not in listed and f"di.{check.__name__}(" not in source
    ]
    assert untested == []


def test_inaturalist_needs_the_component_by_name_not_the_letters_inat(update29: Path) -> None:
    # R51 mutation 1: the component gone and every word starting inat replaced. The check read
    # "coordinates" in LocationStep.tsx as the context line.
    (update29 / "apps/web/components/InatContext.tsx").unlink()
    for page in ("CityView.tsx", "SpotRecord.tsx"):
        write(update29, f"apps/web/components/{page}", "export function P() { return null; }\n")
    problems = di.check_inaturalist(update29)
    assert has(problems, "no component shows the iNaturalist context line")
    assert has(problems, "CityView.tsx does not show") and has(problems, "SpotRecord.tsx does not")


def test_ots_needs_the_anchor_in_the_jobs_command_not_the_letters_ots(update29: Path) -> None:
    # R51 mutation 2: an installer that does nothing passed, because robots holds ots.
    write(
        update29, "scripts/install_anchor_job.sh", "# robots only: this job does nothing\nexit 0\n"
    )
    assert has(di.check_ots(update29), "does not anchor the audit head daily")


def test_reproduce_needs_judge_check_to_call_its_step_not_a_comment(update29: Path) -> None:
    # R51 mutation 3: the Makefile comment still says judge check's second step is make reproduce.
    judge = update29 / "scripts" / "judge_check.py"
    judge.write_text(judge.read_text().replace("lambda: step_reproduce(root, env),", ""))
    assert "its second step is make reproduce" in (update29 / "Makefile").read_text()
    assert has(di.check_reproduce_wired(update29), "does not run make reproduce")
