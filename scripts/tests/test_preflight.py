"""Preflight fails on the current repo for human reasons and passes on a fully faked green root."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts import audit_log, freeze_key, merge_labels, preflight
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
    assert {"human_inputs", "key_frozen", "key_agreement", "prereg_tag", "contact_email"} <= human
    assert "plan_wording" in human, "TODO-RACHEL wording in the plan"
    reasons = [r for c in checks for r in c.reasons]
    assert any("placeholder photo in role test" in r for r in reasons)
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
    plan = (REPO / "docs" / "analysis_plan.md").read_text().replace("TODO-RACHEL", "frozen wording")
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


def test_report_counts_reasons_and_marks_owner(capsys: pytest.CaptureFixture[str]) -> None:
    checks = [
        preflight.Check("a", "HUMAN", ["one", "two"]),
        preflight.Check("b", "BUILD", ["three"]),
        preflight.Check("c", "BUILD"),
    ]
    assert preflight.report(checks) == (3, 2)
    out = capsys.readouterr().out
    assert "FAIL  HUMAN  a: one" in out and "FAIL  BUILD  b: three" in out and "PASS" in out
    assert "checks: 3 run, 1 passed, 2 failed" in out
    assert out.strip().endswith("preflight: 3 failed, of which 2 need a human")


def test_main_exits_1_on_the_current_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preflight, "default_runner", lambda root: ok_runner)
    assert preflight.main([]) == 1
