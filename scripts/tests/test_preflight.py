"""Preflight fails on the current repo for human reasons and passes on a fully faked green root."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from scripts import audit_log, freeze_key, label_photos, merge_labels, preflight
from scripts.ingest_photos import MANIFEST_COLUMNS

REPO = Path(__file__).parents[2]


def ok_runner(argv: list[str]) -> tuple[int, str]:
    """Subprocess checks pass; git says there is no tag."""
    if argv[:2] == ["git", "tag"]:
        return 0, ""
    return 0, "ok"


def git_runner(root: Path) -> preflight.Runner:
    def run(argv: list[str]) -> tuple[int, str]:
        if argv[0] == "git":
            proc = subprocess.run(
                ["git", "-C", str(root), *argv[1:]], capture_output=True, text=True
            )
            return proc.returncode, proc.stdout + proc.stderr
        return 0, "ok"

    return run


def test_current_repo_fails_only_for_known_reasons() -> None:
    checks = preflight.run_checks(REPO, runner=ok_runner)
    failed = {c.name: c for c in checks if not c.passed}
    human = {n for n, c in failed.items() if c.owner == "HUMAN"}
    build = {n for n, c in failed.items() if c.owner == "BUILD"}
    # contact_email passes now that the consent email is real (Update 11C).
    # Everything a person owed has landed except the tag, which Alex makes himself (Update 11D).
    assert "prereg_tag" in human
    assert {
        "human_inputs",
        "key_frozen",
        "key_agreement",
        "contact_email",
        "marks_approved",
    } & human == set()
    assert "marks_approved" not in human, "all 24 marks approved in Update 11D"
    # plan_wording passes now: the four question wordings are frozen in the plan (Update 11C).
    assert "plan_wording" not in human, "no TODO-TEAM left in docs/analysis_plan.md"
    reasons = [r for c in checks for r in c.reasons]
    # The real photos are in as of Update 11b, so no role is on a gray placeholder any more.
    assert not any("placeholder photo in role" in r for r in reasons)
    assert any("no second label for test photo" in r for r in reasons)
    assert any("prereg-v1 tag missing" in r for r in reasons)
    # BUILD failures today can only come from other workstreams' half-finished files.
    others = {"hidden_field", "model_pass_table_exists", "content_loads", "verify_claims"}
    assert build <= others, build


def green_root(tmp_path: Path) -> Path:
    root = tmp_path / "green"
    shutil.copytree(REPO / "content", root / "content")
    shutil.copytree(REPO / "photos", root / "photos")
    (root / "docs").mkdir()
    (root / "results").mkdir()
    (root / "apps" / "web" / "app" / "t").mkdir(parents=True)

    # Update 11 section 6 puts backups in the launch gate, so a green repo has a drill on record
    # and a fresh backup receipt. The receipt lives outside the repo, so point it somewhere
    # harmless: no test may depend on whether this machine ran a real backup today.
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "backup.yml").write_text("name: backup", encoding="utf-8")
    (root / "results" / "backup_drill.json").write_text(
        json.dumps({"restored": True}), encoding="utf-8"
    )
    backups = root / "backups"
    backups.mkdir()
    (backups / "last_backup.json").write_text(
        json.dumps({"generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}),
        encoding="utf-8",
    )

    features_path = root / "content" / "features.yaml"
    doc = yaml.safe_load(features_path.read_text())
    for f in doc["features"]:
        f["wording_status"] = "frozen"
        f["verified_against_app"] = True
    features_path.write_text(yaml.safe_dump(doc))
    form_path = root / "content" / "form.yaml"
    doc = yaml.safe_load(form_path.read_text())
    for item in doc["items"]:
        item["verified_against_app"] = True
    form_path.write_text(yaml.safe_dump(doc))
    for lesson in (root / "content" / "lessons").glob("*.yaml"):
        doc = yaml.safe_load(lesson.read_text())
        doc["approved"] = True
        for _, mark in label_photos.iter_marks(doc):
            mark["approved"] = True  # green means Rachel has been through every mark
        lesson.write_text(yaml.safe_dump(doc))
    locale_path = root / "content" / "locales" / "en.json"
    locale = json.loads(locale_path.read_text())
    locale = {
        k: v.replace("PLACEHOLDER contact email (Alex supplies it)", "fake@example.org")
        for k, v in locale.items()
    }
    locale_path.write_text(json.dumps(locale, indent=2))

    manifest = root / "photos" / "manifest.csv"
    with manifest.open(newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["license"] = "own-CC-BY-4.0"
        if row["role"] == "test":
            row["labeller_2"] = row["gold_label"]
    with manifest.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        w.writeheader()
        w.writerows(rows)

    for name in ("rachel", "alex"):
        with (root / f"labels_{name}.csv").open("w", newline="") as f:
            cw = csv.writer(f)
            cw.writerow(["photo_id", "feature", "label", "labelled_at_utc"])
            for row in rows:
                if row["role"] == "test":
                    cw.writerow(
                        [row["id"], row["feature"], row["gold_label"], "2026-09-22T10:00:00Z"]
                    )
    assert (
        merge_labels.main(
            [str(root / "labels_rachel.csv"), str(root / "labels_alex.csv"), "--root", str(root)]
        )
        == 0
    )
    freeze_key.freeze(root)
    (root / "results" / "model_pass_table.json").write_text(
        json.dumps({"real": True, "synthetic": False, "generated_at_utc": "x", "models": {}})
    )
    (root / "README.md").write_text(
        "Track statement.\n\n<!-- claim: results/model_pass_table.json#/real = True -->\n"
        "real: True\n"
    )
    (root / "apps" / "web" / "app" / "t" / "consent.tsx").write_text(
        '<input type="text" name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" />'
    )
    plan = (REPO / "docs" / "analysis_plan.md").read_text().replace("TODO-TEAM", "frozen wording")
    (root / "docs" / "analysis_plan.md").write_text(plan)
    git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.org"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "docs/analysis_plan.md"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "plan"], check=True)
    subprocess.run([*git, "tag", "prereg-v1"], check=True)
    return root


def test_green_root_passes_every_check(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = green_root(tmp_path)
    checks = preflight.run_checks(root, runner=git_runner(root))
    failed = {c.name: c.reasons for c in checks if not c.passed}
    assert failed == {}, failed
    assert preflight.report(checks) == (0, 0)
    assert "preflight: 0 failed, of which 0 need a human" in capsys.readouterr().out


def test_green_root_guards_fire_when_broken(tmp_path: Path) -> None:
    root = green_root(tmp_path)
    run = git_runner(root)

    def failed(owner: str | None = None) -> dict[str, str]:
        return {
            c.name: c.owner
            for c in preflight.run_checks(root, runner=run)
            if not c.passed and (owner is None or c.owner == owner)
        }

    table = root / "results" / "model_pass_table.json"
    table.write_text(json.dumps({"real": True, "synthetic": True, "models": {}}))
    assert failed() == {"results_real": "HUMAN"}
    table.write_text(json.dumps({"real": False, "synthetic": False, "models": {}}))
    # the README claim says real = True, so the claim drifts too: that part is ours to fix
    assert failed() == {"model_pass_table_real": "HUMAN", "verify_claims": "BUILD"}
    table.write_text(json.dumps({"real": True, "synthetic": False, "models": {}}))

    # The backup guard fires too: remove the drill and the launch gate blocks on it.
    drill = root / "results" / "backup_drill.json"
    kept = drill.read_text()
    drill.unlink()
    assert "backups" in failed("HUMAN")
    drill.write_text(kept, encoding="utf-8")
    assert "backups" not in failed()

    plan = root / "docs" / "analysis_plan.md"
    original = plan.read_text()
    plan.write_text(original + "\nan edit after the tag\n")
    assert failed() == {"plan_matches_tag": "BUILD"}
    plan.write_text(original)

    log = root / "audit" / "log.jsonl"
    lines = log.read_text().splitlines()
    entry = json.loads(lines[0])
    entry["kind"] = "plan_tagged"
    log.write_text(json.dumps(entry) + "\n")
    assert failed() == {"audit_log": "BUILD"}
    log.write_text("\n".join(lines) + "\n")
    assert audit_log.verify(log) == 1

    items = root / "content" / "test_items.yaml"
    doc = yaml.safe_load(items.read_text())
    doc["items"][0]["gold"], doc["items"][2]["gold"] = "absent", "present"
    items.write_text(yaml.safe_dump(doc))
    names = failed()
    assert names.get("key_matches") == "BUILD" and names.get("content_loads") == "BUILD"

    def fail_pytest(argv: list[str]) -> tuple[int, str]:
        if argv[:3] == ["uv", "run", "pytest"]:
            return 1, "1 failed"
        return run(argv)

    items.write_text(
        yaml.safe_dump(yaml.safe_load((REPO / "content" / "test_items.yaml").read_text()))
    )
    broken = {c.name for c in preflight.run_checks(root, runner=fail_pytest) if not c.passed}
    assert broken == {"analysis_tests", "lock_tests"}


def test_report_groups_by_what_clears_it_and_counts_reasons(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Update 09 section 1: grouped by the work, not by who owes it, and a NOTE never blocks."""
    checks = [
        preflight.Check("a", "HUMAN", ["one", "two"], clears="real photos"),
        preflight.Check("b", "BUILD", ["three"]),
        preflight.Check("c", "BUILD"),
        preflight.Check("d", "NOTE", ["four"], clears="a second labeller, optional"),
    ]
    assert preflight.report(checks) == (3, 2)
    out = capsys.readouterr().out
    assert "CLEARED BY: real photos  (2 lines)" in out
    assert "CLEARED BY: our build  (1 lines)" in out
    assert "CLEARED BY: a second labeller, optional  (1 lines)" in out
    assert "HUMAN  a: one" in out and "BUILD  b: three" in out and "NOTE   d: four" in out
    assert "PASS   1 checks: c" in out
    # Two checks failed and one is a note. The note is never counted as a failure.
    assert "checks: 4 run, 1 passed, 2 failed, 1 notes" in out
    assert out.strip().endswith("preflight: 3 failed, of which 2 need a human")


def test_main_exits_1_on_the_current_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preflight, "default_runner", lambda root: ok_runner)
    assert preflight.main([]) == 1


def test_the_launch_gate_leaves_out_what_the_two_minute_test_never_touches(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Update 11 section 1: the creek check form must not hold up Wednesday."""
    checks = [
        preflight.Check("human_inputs", "HUMAN", ["placeholder photo in role test: ph-test-01"]),
        preflight.Check(
            "judges_inputs", "HUMAN", ["form item bank_type not verified"], gate="judges"
        ),
        preflight.Check("results_real", "HUMAN", ["README cites synthetic"], gate="judges"),
    ]
    launch_failed, _ = preflight.report(checks, "launch")
    launch_out = capsys.readouterr().out
    assert launch_failed == 1
    assert "placeholder photo" in launch_out
    assert "form item" not in launch_out and "synthetic" not in launch_out

    judges_failed, _ = preflight.report(checks, "judges")
    judges_out = capsys.readouterr().out
    assert judges_failed == 2
    assert "form item" in judges_out and "synthetic" in judges_out
    assert "placeholder photo" not in judges_out

    # With no gate the run is everything, which is what make preflight still does.
    both, _ = preflight.report(checks)
    assert both == 3


def test_a_form_item_is_a_judges_reason_and_a_photo_is_a_launch_one() -> None:
    launch, judges = preflight.split_by_gate(
        [
            "placeholder photo in role test: ph-test-01",
            "feature artificial_bank question wording not frozen",
            "form item bank_type not verified against the app",
            "sentence s01 not approved",
            "lesson pipe_running not approved",
        ]
    )
    assert launch == [
        "placeholder photo in role test: ph-test-01",
        "feature artificial_bank question wording not frozen",
        "lesson pipe_running not approved",
    ]
    assert judges == [
        "form item bank_type not verified against the app",
        "sentence s01 not approved",
    ]


def test_backups_block_the_launch_until_a_drill_has_run(tmp_path: Path) -> None:
    """Update 11 section 6. A study with no backup is one bad afternoon from having no data."""
    root = green_root(tmp_path)
    drill = root / "results" / "backup_drill.json"

    def backups() -> preflight.Check:
        return {
            c.name: c
            for c in preflight.run_checks(root, runner=ok_runner, backup_dir=root / "backups")
        }["backups"]

    assert backups().gate == "launch", "a lost database would sink the study, so it gates launch"
    assert backups().passed, "the green fixture records a drill"

    # No drill at all: the launch is blocked and the line says what to do.
    drill.unlink()
    blocked = backups()
    assert not blocked.passed
    assert "make restore-drill" in blocked.reasons[0]

    # A drill that ran and did not match is worse than none, so it must not pass either.
    drill.write_text(json.dumps({"restored": False}), encoding="utf-8")
    mismatch = backups()
    assert not mismatch.passed
    assert "did not match" in mismatch.reasons[0]

    # A drill on record but no backup for days is not a backup. The GitHub workflow stays on
    # manual, so its file being there proves nothing and is no longer part of this check
    # (Update 11D item 4).
    drill.write_text(json.dumps({"restored": True}), encoding="utf-8")
    receipt = root / "backups" / "last_backup.json"
    stale = datetime.now(UTC) - timedelta(hours=27)
    receipt.write_text(
        json.dumps({"generated_at_utc": stale.strftime("%Y-%m-%dT%H:%M:%SZ")}), encoding="utf-8"
    )
    old_backup = backups()
    assert not old_backup.passed
    assert "27 hours old" in old_backup.reasons[0]

    # Just inside the window, because a Mac asleep at 21:00 catches up at wake.
    fresh = datetime.now(UTC) - timedelta(hours=25)
    receipt.write_text(
        json.dumps({"generated_at_utc": fresh.strftime("%Y-%m-%dT%H:%M:%SZ")}), encoding="utf-8"
    )
    assert backups().passed, "26 hours of slack covers a missed 21:00 run"

    # And no backup at all is named plainly.
    receipt.unlink()
    gone = backups()
    assert not gone.passed
    assert "no backup receipt" in gone.reasons[0]
