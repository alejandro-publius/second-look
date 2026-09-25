"""Which README commands the command check runs, and which it lists with a reason (D31)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts import harden_commands as hc
from scripts.done_items import NEVER_RUN

SANDBOX = (
    'curl -H "Accept: application/fhir+json" '
    "https://sandbox.hl7europe.eu/oneaquahealth/fhir/Library/466"
)


def test_a_curl_to_a_named_down_host_is_blocked_outside_with_its_evidence() -> None:
    why = hc.policy(SANDBOX)
    assert why.startswith(hc.OUTSIDE)
    assert "NXDOMAIN" in why
    # The done check lists it, it does not fail on it: its item is D41, blocked outside.
    assert why.startswith(NEVER_RUN)


def test_a_curl_to_our_own_site_still_runs() -> None:
    assert hc.policy("curl -s https://second-look-79t.pages.dev/api/test/counts") == ""


def test_the_setup_a_judge_types_runs_and_a_bare_npm_ci_does_not() -> None:
    for cmd in (
        "uv sync",
        "(cd apps/web && npm ci)",
        "uv sync && (cd apps/web && npm ci) && (cd worker && npm ci)"
        " && (cd tools/diagrams && npm ci)",
        "uv tool install pre-commit && pre-commit install",
        "uv sync && (cd apps/web && npm ci && npx playwright install chromium)"
        " && (cd worker && npm ci) && (cd tools/diagrams && npm ci)",
    ):
        assert hc.policy(cmd) == "", cmd
    assert hc.policy("npm ci") == "not on the safe list"
    assert hc.policy("(cd apps/web && npm ci) && rm -rf /") != ""
    assert hc.policy("uv sync && make deploy") != ""


def test_the_port_bound_suites_are_not_refused_by_policy() -> None:
    # They run when 3100 and 8100 are free at their turn; the run loop checks the ports.
    for cmd in ("make e2e", "make check", "make judge-check"):
        assert hc.policy(cmd) == "", cmd
        assert any(s in cmd for s in hc.SERVES_3100), cmd


def test_submit_check_red_only_on_the_video_link_and_the_public_repo_counts_as_the_row_says() -> (
    None
):
    # docs/ACCEPTANCE.md row 14: every item except the video link and the repo being public.
    red = "PASS  license\nFAIL  video_link\nFAIL  repo_public\n"
    assert hc.expected_red("make submit-check", red)
    assert not hc.expected_red("make submit-check", red + "FAIL  secrets_scan\n")
    assert not hc.expected_red("make submit-check", "PASS  license\n")
    assert not hc.expected_red("make check", red)


def test_rollback_and_the_video_are_run_not_skipped() -> None:
    assert hc.policy("make rollback") == ""
    assert hc.policy("make video-final") == ""


# ---- no machine paths in what is kept (critic round 15 N03) -------------------------------------

WARNING = (
    "warning: `VIRTUAL_ENV=/Users/someone/second-look/.venv` does not match the project "
    "environment path `.venv` and will be ignored; use `--active` to target the active "
    "environment instead\n"
)
MACHINE = re.compile(r"/Users/|/home/|/private/|/tmp/|/var/folders/|-Users-|VIRTUAL_ENV=|--active")


def test_what_a_command_printed_is_kept_without_this_machines_paths() -> None:
    clone = "/private/tmp/claude-501/-Users-someone/abc/scratchpad/cmds/tree"
    out = (
        "nt path `.venv` and will be ignored; use `--active` to target the active environment "
        f"instead\n{WARNING}mutation: wrote {clone}/results/mutation.json\n{WARNING}"
        "ad/cmds/tree/fhir/build/a.json ok\n"
        "screens from /Users/someone/second-look-media/screens into /tmp/x/video-final-out\n"
        "see https://github.com/a/b/tree/main/docs\n"
    )
    kept = hc.scrub(out)
    assert MACHINE.search(kept) is None, kept
    assert kept.splitlines() == [
        "mutation: wrote results/mutation.json",
        "fhir/build/a.json ok",
        "screens from ~/second-look-media/screens into <temp folder>",
        "see https://github.com/a/b/tree/main/docs",
    ]


def test_a_command_runs_without_the_shells_virtual_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIRTUAL_ENV", "/Users/someone/elsewhere/.venv")
    r = hc.run('echo "venv=${VIRTUAL_ENV:-none}"; echo /Users/someone/x', Path.cwd())
    assert r["tail"] == "venv=none\n~/x\n"


def test_the_committed_command_tables_hold_no_machine_path_and_are_what_render_writes(
    tmp_path: Path,
) -> None:
    folder = hc.ROOT / "results" / "harden"
    for name in ("commands", "commands_depth"):
        committed = (folder / f"{name}.json").read_text(encoding="utf-8")
        doc = json.loads(committed)
        for r in doc["commands"]:
            assert MACHINE.search(str(r["detail"])) is None, (name, r["command"])
        page = (folder / f"{name}.md").read_text(encoding="utf-8")
        assert MACHINE.search(page) is None, name
        hc.write(doc, tmp_path, name)
        assert (tmp_path / f"{name}.md").read_text(encoding="utf-8") == page, name
        assert (tmp_path / f"{name}.json").read_text(encoding="utf-8") == committed, name
