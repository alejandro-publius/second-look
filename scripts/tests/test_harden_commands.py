"""Which README commands the command check runs, and which it lists with a reason (D31)."""

from __future__ import annotations

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
