"""The daily and ten-minute Mac jobs: the sandbox retry, the hl7-eu/oah watch, uptime, and the
panel counts on the status issue. Nothing here reaches their sandbox, GitHub or the site:
scripts/tests/fake_outward.py stands in, except for the uptime test the brief asks for, which
keeps the network real and points the job at an address that cannot resolve.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts import hl7_watch, panel_status, sandbox_retry, uptime
from scripts.outward import Done, Outward, Reply
from scripts.tests.fake_outward import FakeOutward

T0 = datetime(2026, 10, 2, 8, 0, tzinfo=UTC)
HOST = "sandbox.hl7europe.eu"
COUNTS = {
    "by_arm": {
        "trained": {"randomized": 3, "completed": 2},
        "untrained": {"randomized": 2, "completed": 1},
    },
    "by_source": {"panel": 2, "other": 1, "poster": 0},
}


# ---------------------------------------------------------------------------
# The sandbox retry (6.1)
# ---------------------------------------------------------------------------


def retry(out: FakeOutward, tmp_path: Path, day: int = 0) -> tuple[int, list[str]]:
    said: list[str] = []
    code = sandbox_retry.run(
        out,
        state_path=tmp_path / "sandbox.json",
        clock=lambda: T0 + timedelta(days=day),
        say=said.append,
    )
    return code, said


def test_while_the_name_does_not_resolve_nothing_is_sent(tmp_path: Path) -> None:
    out = FakeOutward()
    code, said = retry(out, tmp_path)
    assert code == 0
    assert out.calls == [["resolve", HOST]]
    assert out.comments == []
    assert "still does not resolve, so nothing was sent" in said[0]


def test_when_the_name_resolves_it_pushes_updates_two_and_says_so_once(tmp_path: Path) -> None:
    out = FakeOutward()
    retry(out, tmp_path, 0)
    out.hosts[HOST] = True
    code, said = retry(out, tmp_path, 1)
    assert code == 0
    push = out.ran("uv", "run", "python", "scripts/repush_sandbox.py")
    assert push == [
        [
            "uv", "run", "python", "scripts/repush_sandbox.py",
            "--bundle", "fhir/golden/visit-strawberry-creek-1.json", "--library",
        ]
    ]  # fmt: skip
    assert out.envs[out.calls.index(push[0])]["SANDBOX_MIRROR_ENABLED"] == "true"
    assert out.ran("uv", "run", "python", "scripts/cache_their_records.py")
    assert len(out.comments) == 1 and "answers again" in out.comments[0]
    # The next day it pushes again, since anyone can delete records there, but says nothing new.
    retry(out, tmp_path, 2)
    assert len(out.ran("uv", "run", "python", "scripts/repush_sandbox.py")) == 2
    assert len(out.comments) == 1


def test_a_failed_push_is_said_once_and_the_job_fails(tmp_path: Path) -> None:
    out = FakeOutward()
    out.hosts[HOST] = True
    out.answer(["uv", "run", "python", "scripts/repush_sandbox.py"], Done(1, "", "HTTP 503"))
    code, said = retry(out, tmp_path, 0)
    assert code == 1 and "the re-push failed: HTTP 503" in said[0]
    assert len(out.comments) == 1 and "HTTP 503" in out.comments[0]
    retry(out, tmp_path, 1)
    assert len(out.comments) == 1


def test_it_never_goes_near_the_forbidden_api(tmp_path: Path) -> None:
    out = FakeOutward()
    code = sandbox_retry.run(
        out, base="https://api.enora-oah.eu/fhir", state_path=tmp_path / "s.json", say=print
    )
    assert code == 2 and out.calls == []


# ---------------------------------------------------------------------------
# The hl7-eu/oah watch (6.2)
# ---------------------------------------------------------------------------


def gh_answers(out: FakeOutward, comments: dict[int, list[dict]], state: str = "OPEN") -> None:
    for kind, number in hl7_watch.WATCHED:
        doc = {
            "state": state,
            "url": f"https://github.com/hl7-eu/oah/{'pull' if kind == 'pr' else 'issues'}/{number}",
            "comments": comments.get(number, []),
        }
        if kind == "pr":
            doc["reviews"] = []
        out.answer(["gh", kind, "view", str(number)], Done(0, json.dumps(doc)))


def comment(cid: str, login: str, role: str, body: str) -> dict:
    return {
        "id": cid,
        "author": {"login": login},
        "authorAssociation": role,
        "createdAt": "2026-10-01T10:00:00Z",
        "url": f"https://github.com/hl7-eu/oah/issues/6#{cid}",
        "body": body,
    }


def test_a_new_maintainer_comment_goes_to_the_status_issue_and_the_log(tmp_path: Path) -> None:
    out = FakeOutward()
    log, state = tmp_path / "hl7.log", tmp_path / "seen.json"
    gh_answers(out, {6: [comment("c1", "Jah-yee", "NONE", "nice")]})
    assert hl7_watch.run(out, log=log, state_path=state, say=lambda s: None) == 0
    assert out.comments == []  # a comment from outside the project is logged only
    assert "new comment on issue 6 by Jah-yee" in log.read_text()
    gh_answers(
        out,
        {
            6: [comment("c1", "Jah-yee", "NONE", "nice")],
            7: [comment("c2", "jkiddo", "MEMBER", "Please rename the field\nand add a test.")],
        },
    )
    hl7_watch.run(out, log=log, state_path=state, say=lambda s: None)
    assert len(out.comments) == 1
    assert (
        "jkiddo" in out.comments[0] and "Please rename the field and add a test." in out.comments[0]
    )
    assert "new maintainer comment on issue 7 by jkiddo (member)" in log.read_text()
    # Seen once, told once.
    hl7_watch.run(out, log=log, state_path=state, say=lambda s: None)
    assert len(out.comments) == 1
    # It only ever reads: every command it ran is gh ... view.
    assert all(c[:1] == ["gh"] and c[2] == "view" for c in out.calls)


def test_a_review_asking_for_changes_counts_and_a_merge_is_told(tmp_path: Path) -> None:
    out = FakeOutward()
    log, state = tmp_path / "hl7.log", tmp_path / "seen.json"
    gh_answers(out, {})
    hl7_watch.run(out, log=log, state_path=state, say=lambda s: None)
    review = {
        "id": "r1",
        "author": {"login": "owner1"},
        "authorAssociation": "OWNER",
        "state": "CHANGES_REQUESTED",
        "submittedAt": "2026-10-03T09:00:00Z",
        "body": "",
    }
    doc = {"state": "MERGED", "url": "https://github.com/hl7-eu/oah/pull/5", "comments": []}
    out.answer(["gh", "pr", "view", "5"], Done(0, json.dumps({**doc, "reviews": [review]})))
    hl7_watch.run(out, log=log, state_path=state, say=lambda s: None)
    assert any("pull request 5 is now MERGED" in c for c in out.comments)
    assert any("CHANGES_REQUESTED" in c and "owner1" in c for c in out.comments)


def test_gh_that_cannot_read_anything_fails_the_run(tmp_path: Path) -> None:
    out = FakeOutward()
    out.answer(["gh"], Done(1, "", "gh: not logged in"))
    code = hl7_watch.run(out, log=tmp_path / "l", state_path=tmp_path / "s", say=lambda s: None)
    assert code == 1 and out.comments == []


# ---------------------------------------------------------------------------
# Uptime (7.1)
# ---------------------------------------------------------------------------


def outputs(tmp_path: Path) -> uptime.Outputs:
    return uptime.Outputs(
        log=tmp_path / "uptime.log",
        state=tmp_path / "uptime.json",
        panel_state=tmp_path / "panel.json",
    )


def test_a_wrong_address_with_the_real_network_alerts_once_on_the_second_failure(
    tmp_path: Path,
) -> None:
    """The brief's test: the network layer is real, the outputs are replaced. The address is
    under .invalid, which never resolves (RFC 2606), so no server anywhere is asked."""
    told = FakeOutward()
    real = Outward()
    where = outputs(tmp_path)
    site = "https://second-look-uptime-test.invalid"

    def check(minutes: int) -> int:
        return uptime.run(
            told,
            site=site,
            outputs=where,
            network=real,
            clock=lambda: T0 + timedelta(minutes=minutes),
            say=lambda s: None,
        )

    assert check(0) == 1
    assert not where.log.exists() and told.comments == [] and told.notes == []
    assert check(10) == 1
    assert "DOWN: 2 failed checks in a row" in where.log.read_text()
    assert len(told.comments) == 1 and site in told.comments[0]
    assert len(told.notes) == 1 and told.notes[0][0] == "Second Look is down"
    assert check(20) == 1
    assert len(told.comments) == 1 and len(told.notes) == 1, "one comment per outage"
    assert "still down since" in where.log.read_text()
    assert told.calls == [], "the stand-in made no request; the real layer did"


def site_pages(out: FakeOutward, site: str, *, broken: str | None = None) -> None:
    for path in uptime.PATHS:
        body = "<title>Second Look</title>"
        if path == "/health":
            body = '{"status":"ok"}'
        if path == "/api/test/counts":
            body = json.dumps(COUNTS)
        out.pages[f"{site}{path}"] = Reply(500 if path == broken else 200, body)


def test_a_recovery_is_told_once_and_the_counts_reach_the_issue(tmp_path: Path) -> None:
    out = FakeOutward()
    where = outputs(tmp_path)
    site = "https://site.test"

    def check(minutes: int) -> int:
        return uptime.run(
            out,
            site=site,
            outputs=where,
            clock=lambda: T0 + timedelta(minutes=minutes),
            say=lambda s: None,
        )

    site_pages(out, site, broken="/judges")
    check(0)
    check(10)
    assert len(out.comments) == 1 and "/judges answered 500" in out.comments[0]
    site_pages(out, site)
    assert check(20) == 0
    assert len(out.comments) == 2 and "answers again, after about 10 minutes" in out.comments[1]
    assert "UP again" in where.log.read_text()
    assert panel_status.START in (out.issue or "")
    # A second good run: no comment, and the issue is not edited again with the same counts.
    edits = len(out.issue_edits)
    check(30)
    assert len(out.comments) == 2 and len(out.issue_edits) == edits


@pytest.mark.parametrize(
    ("path", "reply", "bad"),
    [
        ("/", Reply(200, "<title>Cloudflare error</title>"), True),
        ("/health", Reply(200, '{"status":"down"}'), True),
        ("/api/test/counts", Reply(200, "[]"), True),
        ("/api/test/counts", Reply(200, json.dumps(COUNTS)), False),
        ("/judges", Reply(0, "", "timed out"), True),
    ],
)
def test_what_counts_as_a_working_page(path: str, reply: Reply, bad: bool) -> None:
    assert (uptime.problem(path, reply) is not None) is bad


# ---------------------------------------------------------------------------
# The panel counts on the status issue (5.2)
# ---------------------------------------------------------------------------


def test_panel_status_prints_by_source_and_by_arm_and_the_rule_of_twenty() -> None:
    text = panel_status.render(COUNTS)
    assert "panel        2" in text and "trained      3, 2" in text and "untrained    2, 1" in text
    assert "needs 20 completed sessions in each arm" in text
    many = {"by_arm": {"trained": {"completed": 20}, "untrained": {"completed": 25}}}
    assert "the plan's one test applies" in panel_status.render(many)


def test_the_counts_go_under_the_top_paragraph_and_are_replaced_in_place() -> None:
    body = "Alex: 1. launch the panel (Sep 26).\n\nOlder notes.\n\nMore."
    once = panel_status.put_block(body, panel_status.issue_block(COUNTS, "t1"))
    assert once.startswith("Alex: 1. launch the panel (Sep 26).\n\n<!-- panel-counts -->")
    assert "trained 2, untrained 1; by source: other 1, panel 2." in once
    twice = panel_status.put_block(once, panel_status.issue_block(COUNTS, "t2"))
    assert twice.count(panel_status.START) == 1 and "t2" in twice and "t1" not in twice
    assert twice.endswith("Older notes.\n\nMore.")


def test_the_issue_is_edited_only_when_a_count_moves(tmp_path: Path) -> None:
    out = FakeOutward()
    state = tmp_path / "panel.json"
    assert "shows the new counts" in panel_status.update_issue(out, COUNTS, when="a", state=state)
    assert "unchanged" in panel_status.update_issue(out, COUNTS, when="b", state=state)
    moved = {**COUNTS, "by_source": {"panel": 3, "other": 1}}
    panel_status.update_issue(out, moved, when="c", state=state)
    assert len(out.issue_edits) == 2


def test_panel_status_issue_flag_reads_the_counts_and_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(panel_status, "STATE", tmp_path / "panel.json")
    monkeypatch.delenv("SITE_URL", raising=False)
    out = FakeOutward()
    out.pages[f"{panel_status.SITE}/api/test/counts"] = Reply(200, json.dumps(COUNTS))
    assert panel_status.main([], out=out) == 0 and out.issue_edits == []
    assert panel_status.main(["--issue"], out=out) == 0 and len(out.issue_edits) == 1
    assert out.fetched[-1] == ("GET", f"{panel_status.SITE}/api/test/counts")
    assert (tmp_path / "panel.json").exists()
