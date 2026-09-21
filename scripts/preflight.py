"""The launch gate. Fails closed, prints every failed check with a one line reason, then counts.

Run: make preflight  (uv run python scripts/preflight.py)
Each check is marked HUMAN (a person must supply something: photos, labels, wording, approved
copy, verified app items, the contact email, the tag, a real model run) or BUILD (our fault).
The last line is "preflight: N failed, of which M need a human", counting reasons. The goal
before launch is N == M == 0; the goal of a placeholder build is N == M.

End-to-end checks (consent before assignment, no third-party request, no client address in the
server log, accessibility) run against a live stack in `make e2e`, not here.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from core.content_loader import load_content, placeholder_report
from core.records import FEATURES
from scripts import audit_log, freeze_key, label_photos
from scripts.verify_claims import CLAIM_RE, resolve_pointer

ROOT = Path(__file__).resolve().parents[1]
Owner = Literal["HUMAN", "BUILD"]
Runner = Callable[[list[str]], tuple[int, str]]
WEB_SKIP = {"node_modules", ".next", "out", "playwright-report", "test-results"}
WEB_SUFFIXES = {".tsx", ".ts", ".jsx", ".js", ".html"}


@dataclass
class Check:
    name: str
    owner: Owner
    reasons: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.reasons


def default_runner(root: Path) -> Runner:
    def run(argv: list[str]) -> tuple[int, str]:
        try:
            proc = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=900)
        except (OSError, subprocess.TimeoutExpired) as e:
            return 1, f"could not run {' '.join(argv)}: {e}"
        return proc.returncode, (proc.stdout + proc.stderr)

    return run


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _last_line(text: str) -> str:
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else "(no output)"


def unapproved_marks(lessons: dict[str, Any]) -> list[str]:
    """One line per mark still waiting for Rachel, naming the lesson and the label."""
    out: list[str] = []
    for fid, lesson in sorted(lessons.items()):
        for where, mark in label_photos.iter_marks(lesson):
            if mark.get("approved") is not True:
                label = str(mark.get("label") or "(no label)")
                out.append(f'lesson {fid} {where}: mark "{label}" is not approved by Rachel yet')
    return out


def run_checks(root: Path, *, runner: Runner | None = None) -> list[Check]:
    root = root.resolve()
    run = runner or default_runner(root)
    checks: list[Check] = []

    # 1. The loader passes, 2. every human input the loader knows about is present, and
    # 2b. Rachel has approved every mark on a lesson photo. Alex places the marks with
    # scripts/label_photos.py --marks, which always writes approved: false, so this check is
    # what waits for her yes.
    content_loads = Check("content_loads", "BUILD")
    human_inputs = Check("human_inputs", "HUMAN")
    marks_approved = Check("marks_approved", "HUMAN")
    try:
        content = load_content(root, strict=False)
        content_loads.reasons = list(content.problems)
        human_inputs.reasons = placeholder_report(content)
        marks_approved.reasons = unapproved_marks(content.lessons)
    except Exception as e:  # a missing or unreadable content file
        content_loads.reasons = [f"content did not load: {e}"]
        human_inputs.reasons = ["content did not load, so human inputs cannot be checked"]
        marks_approved.reasons = ["content did not load, so marks cannot be checked"]
    checks += [content_loads, human_inputs, marks_approved]

    # 3. The analysis plan carries no TODO wording.
    plan_wording = Check("plan_wording", "HUMAN")
    plan_path = root / "docs" / "analysis_plan.md"
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    if not plan_text:
        plan_wording.reasons.append("docs/analysis_plan.md missing")
    for n, line in enumerate(plan_text.splitlines(), 1):
        if "TODO" in line:
            plan_wording.reasons.append(f"analysis plan line {n} still has TODO wording")
    checks.append(plan_wording)

    # 4. The key is frozen, on real labels, and its hash matches the items file.
    key_frozen = Check("key_frozen", "HUMAN")
    key_matches = Check("key_matches", "BUILD")
    key_record = _read_json(root / "results" / "key_hash.json")
    if key_record is None:
        key_frozen.reasons.append(
            "key not frozen: run scripts/freeze_key.py once both labels are in the manifest"
        )
    else:
        if key_record.get("placeholders"):
            key_frozen.reasons.append("key was frozen on placeholders (synthetic dry run)")
        try:
            current = freeze_key.key_hash(freeze_key.load_items(root))
        except Exception as e:
            key_matches.reasons.append(f"cannot hash content/test_items.yaml: {e}")
        else:
            if key_record.get("key_sha256") != current:
                key_matches.reasons.append(
                    "results/key_hash.json does not match content/test_items.yaml: "
                    "the key changed after it was frozen"
                )
    checks += [key_frozen, key_matches]

    # 5. Two labellers agreed, and kappa is written per feature.
    agreement = Check("key_agreement", "HUMAN")
    agree = _read_json(root / "results" / "key_agreement.json")
    if agree is None:
        agreement.reasons.append(
            "results/key_agreement.json missing: run scripts/merge_labels.py on both label files"
        )
    else:
        per_feature = agree.get("per_feature", {})
        for f in FEATURES:
            kappa = per_feature.get(f, {}).get("kappa")
            if not isinstance(kappa, int | float):
                agreement.reasons.append(f"no kappa for {f} in results/key_agreement.json")
        if agree.get("disagreements"):
            agreement.reasons.append(f"{len(agree['disagreements'])} label disagreements unsettled")
        if agree.get("ambiguous"):
            agreement.reasons.append(f"{len(agree['ambiguous'])} test photos labelled ambiguous")
    checks.append(agreement)

    # 6. The prereg-v1 tag exists and the plan matches the tagged blob.
    tag = Check("prereg_tag", "HUMAN")
    plan_matches = Check("plan_matches_tag", "BUILD")
    rc, out = run(["git", "tag", "-l", "prereg-v1"])
    if rc != 0:
        tag.reasons.append(f"git tag lookup failed: {_last_line(out)}")
    elif "prereg-v1" not in out.split():
        tag.reasons.append("prereg-v1 tag missing: Alex tags after the key and the wording freeze")
    else:
        rc, blob = run(["git", "show", "prereg-v1:docs/analysis_plan.md"])
        if rc != 0:
            plan_matches.reasons.append(f"cannot read the tagged plan: {_last_line(blob)}")
        elif blob != plan_text:
            plan_matches.reasons.append(
                "docs/analysis_plan.md differs from the prereg-v1 tag (record it in deviations.md)"
            )
    checks += [tag, plan_matches]

    # 7. The analysis tests pass.
    analysis = Check("analysis_tests", "BUILD")
    rc, out = run(["uv", "run", "pytest", "evals", "-q"])
    if rc == 5:
        analysis.reasons.append("no analysis tests found under evals/")
    elif rc != 0:
        analysis.reasons.append(f"uv run pytest evals -q failed: {_last_line(out)}")
    checks.append(analysis)

    # 8. The UTC lock tests pass.
    lock = Check("lock_tests", "BUILD")
    rc, out = run(["uv", "run", "pytest", "core/tests/test_lock.py", "-q"])
    if rc != 0:
        lock.reasons.append(f"lock tests failed: {_last_line(out)}")
    checks.append(lock)

    # 9. Every README claim resolves (same rules as scripts/verify_claims.py), and
    # 10. no cited result file is synthetic.
    claims = Check("verify_claims", "BUILD")
    results_real = Check("results_real", "HUMAN")
    readme = root / "README.md"
    if not readme.exists():
        claims.reasons.append("README.md missing")
    else:
        for m in CLAIM_RE.finditer(readme.read_text(encoding="utf-8")):
            rel, pointer, expected = m.group(1), m.group(2), m.group(3)
            doc = _read_json(root / rel)
            if doc is None:
                claims.reasons.append(f"claim points at a missing or unreadable file: {rel}")
                continue
            if isinstance(doc, dict) and doc.get("synthetic"):
                results_real.reasons.append(
                    f"README cites synthetic results: {rel} (real sessions or a real model run)"
                )
            try:
                value = resolve_pointer(doc, pointer)
            except (KeyError, IndexError, ValueError):
                claims.reasons.append(f"claim pointer not found: {rel}#{pointer}")
                continue
            if expected is not None and str(value) != expected:
                claims.reasons.append(f"claim value drifted: {rel}#{pointer} is {value}")
    checks += [claims, results_real]

    # 11. The audit log exists, verifies, and holds the key_frozen entry.
    # An empty or missing log is a human step, not our bug: the first entry is written by
    # scripts/freeze_key.py, which a person runs once the real labels are in.
    log_path = root / "audit" / "log.jsonl"
    audit = Check("audit_log", "HUMAN" if not log_path.exists() else "BUILD")
    if not log_path.exists():
        audit.reasons.append(
            "no audit log yet: nobody has run scripts/freeze_key.py, so nothing is recorded"
        )
    else:
        try:
            audit_log.verify(log_path)
        except audit_log.AuditError as e:
            audit.reasons.append(f"audit log broken: {e}")
        else:
            kinds = {e["kind"] for e in audit_log._entries(log_path)}
            if key_record is not None and "key_frozen" not in kinds:
                audit.reasons.append(
                    "results/key_hash.json exists but the audit log has no key_frozen"
                )
    checks.append(audit)

    # 12. The consent screen carries the hidden bot-trap field.
    hidden = Check("hidden_field", "BUILD")
    web = root / "apps" / "web"
    found = False
    if web.exists():
        for p in web.rglob("*"):
            if p.suffix in WEB_SUFFIXES and not (WEB_SKIP & set(p.relative_to(web).parts)):
                try:
                    if 'name="website"' in p.read_text(encoding="utf-8"):
                        found = True
                        break
                except (OSError, UnicodeDecodeError):
                    continue
    if not found:
        hidden.reasons.append('no consent source under apps/web contains name="website"')
    checks.append(hidden)

    # 13. The consent contact email and every other locale string is real.
    contact = Check("contact_email", "HUMAN")
    locale = _read_json(root / "content" / "locales" / "en.json")
    if not isinstance(locale, dict):
        contact.reasons.append("content/locales/en.json missing or not an object")
    else:
        for key, value in locale.items():
            if isinstance(value, str) and re.search(r"\bPLACEHOLDER\b", value):
                contact.reasons.append(f"locale string {key} is a placeholder")
    checks.append(contact)

    # 14. The model pass table exists and comes from a real run.
    table_exists = Check("model_pass_table_exists", "BUILD")
    table_real = Check("model_pass_table_real", "HUMAN")
    table = _read_json(root / "results" / "model_pass_table.json")
    if not isinstance(table, dict):
        table_exists.reasons.append("results/model_pass_table.json missing (evals/model_sweep.py)")
    elif not table.get("real"):
        table_real.reasons.append(
            "model pass table is from the fake client: the real model run has not happened"
        )
    checks += [table_exists, table_real]
    return checks


def report(checks: list[Check]) -> tuple[int, int]:
    failed = human = 0
    for c in checks:
        if c.passed:
            print(f"PASS  {'':5}  {c.name}")
            continue
        for reason in c.reasons:
            print(f"FAIL  {c.owner:5}  {c.name}: {reason}")
            failed += 1
            human += c.owner == "HUMAN"
    n_failed = sum(1 for c in checks if not c.passed)
    print(f"checks: {len(checks)} run, {len(checks) - n_failed} passed, {n_failed} failed")
    print(f"preflight: {failed} failed, of which {human} need a human")
    return failed, human


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    failed, _ = report(run_checks(args.root))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
