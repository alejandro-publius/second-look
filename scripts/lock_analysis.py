"""make lock-analysis: the data lock, from the backup to the line on the status issue.

UPDATE_30 section 5.1. launchd runs it once at 2026-09-28T01:10:00Z (scripts/mac_jobs.py, the job
`lock`), ten minutes after the lock in core/lock.py; anyone can run it by hand after the lock
until it has succeeded once. In order:

 1. refuse before the lock, by the real clock (tests hand it another clock; nothing else can);
 2. refuse if the lock analysis already ran (a real results/usability_<date>.json exists);
 3. fetch, and fast-forward this checkout to origin/depth. It refuses if the checkout holds local
    changes other than the files the other Mac jobs write, and the log names them. Those files
    are set aside for the run, so make check, the commit and the deploy see exactly what is
    committed, and put back at the end (a copy origin/depth changed meanwhile is kept aside);
 4. check before touching anything: main can move to depth by fast-forward, wrangler and gh are
    logged in, the QA key is there, and what is live on production is a good row in the deploy
    record with its files kept, so there is something to go back to;
 5. back up D1 (scripts/backup_d1.sh) and export the study tables from that backup
    (scripts/study_export.py) into data/export, with a copy kept next to the backup;
 6. run the pre-registered analysis once, exactly as tagged: evals/usability_analysis.py with no
    option, which itself refuses unless the plan is byte for byte the one tagged prereg-v1; then
    add the audit log's data_lock line, whose payload is the record in results/lock_analysis.json;
 7. put the human row into the README (the counts per arm and per source label, or the sentence
    that nobody finished), render every number, rebuild the report and verify every claim;
 8. make check; commit on depth; main will be that same commit (a fast-forward);
 9. prove the push would be taken (git push --dry-run --atomic), deploy in the order of
    docs/notes/hosting.md with the phone tests after each half, and confirm judge mode opened;
10. mark the deploy good in the record, commit it, push depth and main in one atomic push;
11. a line on the status issue, and the panel counts in its body.

The push comes after the deploy, not before: a pushed commit cannot be taken back without
rewriting history (hard rule 15), and a deploy can. So on any failure up to and including the
push, it rolls production back to what was live when it started, resets this checkout to where it
started (keeping the other jobs' files), and writes the failure to the status issue and to
~/second-look-backups/lock.log. Nothing is ever half pushed: the push is atomic.

The second run (UPDATE_33, docs/analysis_plan_v3.md): `make lock-analysis-2`, which is this
script with `--wave 2`. launchd runs it once at 2026-10-03T04:10:00Z (the job `lock2`), ten
minutes after the second lock. It is the same chain with four differences. It refuses before the
second lock. "Already done" looks at the second wave's own results, results/usability_w2_<date>
.json, so the first wave's result does not stop it. It runs evals/wave2_analysis.py once, which
runs both registered analyses on the second window, and writes results/lock_analysis_w2.json and
a data_lock line of its own in the audit log. And it fills the second wave's own two rows in the
README; the first wave's rows stay as they are, word for word.

One more difference, which closes a trap of Sep 29. The daily re-push job adds a line to
audit/log.jsonl in this checkout when the partner's sandbox answers, and commits nothing. The
first run refuses that change like any other, so the line had to be committed by hand before it
could run. The second run carries such lines: when the only change to the audit log is lines
added at its end, of a kind a Mac job writes (scripts/mac_jobs.py, `audit_kinds`), and the chain
holds, the lines stay in the log, in their place, and go into the lock's commit ahead of its own
data_lock line. Nothing is set aside and nothing is lost. If origin/depth added lines of its own
meanwhile, the carried lines no longer follow the last one, so they are chained again after it
with their own time, kind and payload hash, and the lines as they were are kept in
~/second-look-backups/set-aside-<time>/. Any other change to the audit log is refused by name.

Everything that leaves this Mac goes through scripts/outward.py; commands that stay on it go
through Local. The tests replace both (scripts/tests/test_lock_analysis.py).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.lock import DATA_LOCK_UTC
from evals import wave2_analysis
from evals.wave2_analysis import SECOND_LOCK_UTC
from scripts import audit_log, mac_jobs, panel_status, study_export
from scripts import deploy_record as dr
from scripts import rollback as rb
from scripts.outward import Done, Outward

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://second-look-79t.pages.dev"
SCRIPT = "scripts/lock_analysis.py"
RECORD = "results/lock_analysis.json"
HOSTING = "docs/notes/hosting.md"
PART2_START = "<!-- human-row-2 -->"
PART2_END = "<!-- /human-row-2 -->"
PART2_FILES = ("part2_sessions.csv", "part2_responses.csv")
# What this design can show, and only that (the planner, 2026-09-26): every committed flag points
# the way of its gold label, so the question only ever follows a wrong or Can't tell first answer.
PART2_SCOPE = (
    "This measures one thing only: whether the checker's question helps a person whose first "
    "answer was wrong or Can't tell. It does not show that the checker cannot mislead anyone, "
    "because every flag in this set was correct (Known weaknesses)."
)
HUMAN_START = "<!-- human-row -->"
HUMAN_END = "<!-- /human-row -->"
# The README paragraph that holds the place of the human row until the lock.
HUMAN_LEAD = "The test runs as a pre-registered study that stays open"
NOBODY_YET = "Nobody has taken the test yet, so nothing here measures people."
NOBODY_FINISHED = "Nobody finished the test before the lock, so nothing here measures people."
SOMEBODY = "What people did before the lock is in the human row below the AI tables."
# make check's web build and FHIR validation rewrite these two; they are not the lock's to commit.
REWRITTEN_BY_CHECK = ("apps/web/public/_headers", "results/fhir_validation.json")
# The second wave's two rows (docs/analysis_plan_v3.md), beside the first wave's and never in
# their place.
WAVE2_START = "<!-- wave2-row -->"
WAVE2_END = "<!-- /wave2-row -->"
WAVE2_PART2_START = "<!-- wave2-row-2 -->"
WAVE2_PART2_END = "<!-- /wave2-row-2 -->"
# The summary sentence once the second wave has run, with people in it or without.
SECOND_SOMEBODY = (
    "Nobody finished the test before the first lock. What people did in the second wave is in "
    "its own rows below the AI tables."
)
SECOND_NOBODY = "Nobody finished the test before either lock, so nothing here measures people."
AUDIT_LOG = "audit/log.jsonl"
SOURCE_WORDS = {
    "panel": "the research panel",
    "poster": "a poster",
    "chat": "a chat link",
    "friends": "friends",
    "creek_group": "a creek group",
    "other": "another link",
    "unknown": "no label",
}
Clock = Callable[[], datetime]


def real_clock() -> datetime:
    return datetime.now(UTC)


def stamp(ts: datetime) -> str:
    return ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Wave:
    """What differs between the two runs of the lock job. Everything else is shared."""

    number: int
    lock_utc: datetime
    lock_words: str  # how a log line names the lock
    job_words: str  # how a line on the status issue names the job
    analysis: str  # the script that is run once
    results: str  # the file name of a real result of this wave, as a pattern
    record: str
    make: str  # the make target that runs it again
    # Whether lines a Mac job added to the audit log are carried into the lock's commit.
    carries_audit_lines: bool


FIRST = Wave(
    number=1,
    lock_utc=DATA_LOCK_UTC,
    lock_words="the data lock",
    job_words="Data lock",
    analysis="evals/usability_analysis.py",
    results=r"usability_\d{8}\.json",
    record=RECORD,
    make="lock-analysis",
    carries_audit_lines=False,
)
SECOND = Wave(
    number=2,
    lock_utc=SECOND_LOCK_UTC,
    lock_words="the second data lock",
    job_words="Second data lock",
    analysis="evals/wave2_analysis.py",
    results=r"usability_w2_\d{8}\.json",
    record="results/lock_analysis_w2.json",
    make="lock-analysis-2",
    carries_audit_lines=True,
)
WAVES = {1: FIRST, 2: SECOND}


class Failed(Exception):
    def __init__(self, step: str, detail: str) -> None:
        super().__init__(f"{step}: {detail}")
        self.step = step
        self.detail = detail


class Local:
    """Commands that stay on this Mac: git in this checkout, make, uv run."""

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str] | None = None,
        timeout: float = 3600,
    ) -> Done:
        try:
            proc = subprocess.run(
                list(argv),
                cwd=cwd,
                env={**os.environ, **(env or {})},
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            return Done(127, "", f"{argv[0]}: {e}")
        return Done(proc.returncode, proc.stdout, proc.stderr)


# ---------------------------------------------------------------------------
# The README's human row
# ---------------------------------------------------------------------------


def people_kept(result: dict[str, Any]) -> int:
    counts = result.get("counts") or {}
    return int(counts.get("completed_trained", 0)) + int(counts.get("completed_untrained", 0))


def human_row(result: dict[str, Any], rel: str, wave: Wave = FIRST) -> str:
    """The README text for the one real result: claim tokens only, filled by render_readme."""
    md = rel.removesuffix(".json") + ".md"

    def claim(pointer: str) -> str:
        return "{{claim:" + rel + "#" + pointer + "}}"

    if wave.number == 1:
        start, end = HUMAN_START, HUMAN_END
        nobody = (
            "No finished test from a person was kept before the data lock at "
            f"{claim('/plan/data_lock_utc')}: {claim('/counts/completed_trained')} with the "
            f"lesson and {claim('/counts/completed_untrained')} without it, so there is no human "
            f"row. The one pre-registered run, with what each of the plan's rules removed, is in "
            f"[`{md}`]({md})."
        )
        people = (
            f"People, before the data lock at {claim('/plan/data_lock_utc')}, in the one "
            f"pre-registered run ([`{md}`]({md})):"
        )
    else:
        start, end = WAVE2_START, WAVE2_END
        window = (
            f"from {claim('/window/open_utc')} to the second lock at {claim('/window/lock_utc')}"
        )
        nobody = (
            f"The second wave, under plan `prereg-v3`: no finished test from a person was kept "
            f"{window}: {claim('/counts/completed_trained')} with the lesson and "
            f"{claim('/counts/completed_untrained')} without it, so the second wave has no "
            f"human row either. Its one run, with what each of the plan's rules removed, is in "
            f"[`{md}`]({md})."
        )
        people = (
            f"People in the second wave, under plan `prereg-v3`: sittings that started {window}, "
            f"in the wave's one run ([`{md}`]({md})):"
        )
    # Only counts after the plan's exclusions: the counts before them hold the QA sittings too.
    if people_kept(result) == 0:
        return f"{start}\n\n{nobody}\n\n{end}"
    primary = result.get("primary") or {}
    lines = [
        start,
        "",
        people,
        "",
        "| People | With the lesson | Without it |",
        "|---|---|---|",
        f"| Finished the test, kept by the plan's rules | {claim('/counts/completed_trained')} | "
        f"{claim('/counts/completed_untrained')} |",
    ]
    if primary.get("trained_mean") is not None and primary.get("untrained_mean") is not None:
        lines.append(
            "| Share of the 16 answered right, on average, in percent | "
            f"{claim('/primary/trained_mean')} | {claim('/primary/untrained_mean')} |"
        )
    for label in sorted(result.get("by_source") or {}):
        words = SOURCE_WORDS.get(label, label)
        lines.append(
            f"| Kept, who came through {words} (`{label}`) | "
            f"{claim(f'/by_source/{label}/trained')} | {claim(f'/by_source/{label}/untrained')} |"
        )
    lines += ["", status_line(primary, claim), "", end]
    return "\n".join(lines)


def status_line(primary: dict[str, Any], claim: Callable[[str], str]) -> str:
    """One line: a test, a description, or nothing to compare. The plan's rule, item 7."""
    status = str(primary.get("status", ""))
    if status == "confirmatory":
        return (
            "Each arm kept 20 or more people, so the plan's one test applies: the lesson moved "
            f"the share answered right by {claim('/primary/difference')} points, with a 95 "
            f"percent interval from {claim('/primary/ci_low')} to {claim('/primary/ci_high')}."
        )
    if status == "descriptive":
        return (
            "Fewer than 20 people were kept in an arm, so this is a description, not a test, "
            "as the plan says."
        )
    return "An arm kept nobody, so there is no difference to work out; this is a description."


def part2_row(result: dict[str, Any] | None, rel: str, wave: Wave = FIRST) -> str:
    """The README's second human row (UPDATE_31): claim tokens only, or why there is none."""
    if wave.number != 1:
        return wave2_part2_row(result, rel)
    if result is None:
        return (
            f"{PART2_START}\nDoes the checker's question help? Nobody took part 2 before the data "
            f"lock, so there is nothing to report.\n{PART2_END}"
        )
    md = rel.removesuffix(".json") + ".md"

    def claim(pointer: str) -> str:
        return "{{claim:" + rel + "#" + pointer + "}}"

    n = f"assisted {claim('/primary/n_assisted')}, unassisted {claim('/primary/n_unassisted')}"
    primary = result.get("primary") or {}
    if primary.get("status") == "confirmatory":
        body = (
            f"Does the checker's question help? {n}, difference {claim('/primary/difference')} "
            f"points, interval {claim('/primary/ci_low')} to {claim('/primary/ci_high')}, in the "
            f"one run tagged `prereg-v2` ([`{md}`]({md}))."
        )
    else:
        body = (
            f"Does the checker's question help? Too few people finished part 2 for the plan's "
            f"test: {n}, and the plan needs 20 in each ([`{md}`]({md}))."
        )
    return f"{PART2_START}\n{body} {PART2_SCOPE}\n{PART2_END}"


def wave2_part2_row(result: dict[str, Any] | None, rel: str) -> str:
    """Part 2's row for the second wave: the same words, the wave named, its own place."""
    lead = "Does the checker's question help, in the second wave?"
    if result is None:
        return (
            f"{WAVE2_PART2_START}\n{lead} Nobody took part 2 in the second wave, so there is "
            f"nothing to report.\n{WAVE2_PART2_END}"
        )
    md = rel.removesuffix(".json") + ".md"

    def claim(pointer: str) -> str:
        return "{{claim:" + rel + "#" + pointer + "}}"

    n = f"assisted {claim('/primary/n_assisted')}, unassisted {claim('/primary/n_unassisted')}"
    primary = result.get("primary") or {}
    if primary.get("status") == "confirmatory":
        body = (
            f"{lead} {n}, difference {claim('/primary/difference')} points, interval "
            f"{claim('/primary/ci_low')} to {claim('/primary/ci_high')}, in the wave's one run "
            f"under plan `prereg-v3` ([`{md}`]({md}))."
        )
    else:
        body = (
            f"{lead} Too few people finished part 2 for the plan's test: {n}, and the plan "
            f"needs 20 in each ([`{md}`]({md}))."
        )
    return f"{WAVE2_PART2_START}\n{body} {PART2_SCOPE}\n{WAVE2_PART2_END}"


def place_part2_row(readme: str, row: str) -> str:
    a, b = readme.find(PART2_START), readme.find(PART2_END)
    if a < 0 or b < a:
        raise Failed("readme", "the README has no place for part 2's row")
    return readme[:a] + row + readme[b + len(PART2_END) :]


def place_between(readme: str, row: str, start: str, end: str, what: str) -> str:
    a, b = readme.find(start), readme.find(end)
    if a < 0 or b < a:
        raise Failed("readme", f"the README has no place for {what}")
    return readme[:a] + row + readme[b + len(end) :]


def first_wave_rows(readme: str) -> str:
    """The first wave's two rows as the README holds them, markers included."""
    a, b = readme.find(HUMAN_START), readme.find(PART2_END)
    if a < 0 or b < a:
        raise Failed("readme", "the README does not hold the first wave's rows")
    return readme[a : b + len(PART2_END)]


def place_wave2_rows(readme: str, row: str, part2: str, finished: bool) -> str:
    """The README with the second wave's two rows in their own places. The first wave's rows
    must come out exactly as they went in, or nothing is written."""
    before = first_wave_rows(readme)
    out = place_between(readme, row, WAVE2_START, WAVE2_END, "the second wave's row")
    out = place_between(
        out, part2, WAVE2_PART2_START, WAVE2_PART2_END, "the second wave's part 2 row"
    )
    out = out.replace(NOBODY_FINISHED, SECOND_SOMEBODY if finished else SECOND_NOBODY)
    try:
        after = first_wave_rows(out)
    except Failed:
        after = ""
    if after != before:
        raise Failed("readme", "the first wave's rows would have changed")
    return out


def place_human_row(readme: str, row: str, finished: bool) -> str:
    """The README with the human row in its place, and the numbers' summary sentence updated."""
    a, b = readme.find(HUMAN_START), readme.find(HUMAN_END)
    if a >= 0 and b > a:
        out = readme[:a] + row + readme[b + len(HUMAN_END) :]
    else:
        m = re.search(rf"^{re.escape(HUMAN_LEAD)}.*$", readme, re.M)
        if not m:
            raise Failed("readme", "the README has no paragraph for the human row")
        out = readme[: m.start()] + row + readme[m.end() :]
    return out.replace(NOBODY_YET, SOMEBODY if finished else NOBODY_FINISHED)


def real_results(root: Path, wave: Wave = FIRST) -> list[Path]:
    """Real analysis results of one wave already in results/: after its lock, exactly one."""
    found = []
    for path in sorted((root / "results").glob("usability_*.json")):
        if not re.fullmatch(wave.results, path.name):
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if isinstance(doc, dict) and doc.get("synthetic") is False:
            found.append(path)
    return found


def allowed(path: str, patterns: Sequence[str]) -> bool:
    return any(path.startswith(p) if p.endswith("/") else path == p for p in patterns)


def porcelain(text: str) -> list[str]:
    """Paths from `git status --porcelain=v1 -z`, both sides of a rename."""
    paths: list[str] = []
    parts = text.split("\0")
    i = 0
    while i < len(parts):
        entry = parts[i]
        i += 1
        if len(entry) < 4:
            continue
        paths.append(entry[3:])
        if entry[0] in "RC":
            paths.append(parts[i])
            i += 1
    return paths


def added_lines(committed: str, working: str) -> list[str] | None:
    """The lines added at the end of a file, or None when the change is anything else."""
    if not working.startswith(committed) or (committed and not committed.endswith("\n")):
        return None
    added = working[len(committed) :]
    if not added.endswith("\n"):
        return None
    return added.splitlines()


def qa_key_from(root: Path) -> str | None:
    """The QA key from the environment or this checkout's .env. It is never printed."""
    key = os.environ.get("QA_KEY")
    if key:
        return key
    env = root / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "QA_KEY" and value.strip():
                return value.strip().strip('"').strip("'")
    return None


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# The job
# ---------------------------------------------------------------------------


@dataclass
class Start:
    head: str  # where the checkout is once it is current, which a failure returns to
    before: str  # where it was when the job began, before the fast-forward
    kept: dict[str, bytes | None]  # the other Mac jobs' files, set aside for the run
    carried: tuple[str, ...] = ()  # lines a Mac job added to the audit log, which stay in it


class Lock:
    def __init__(
        self,
        *,
        root: Path,
        out: Outward,
        local: Local,
        clock: Clock = real_clock,
        backups: Path | None = None,
        qa_key: Callable[[], str | None] = lambda: None,
        say: Callable[[str], None] = print,
        wave: Wave = FIRST,
    ) -> None:
        self.wave = wave
        self.root = root
        self.out = out
        self.local = local
        self.clock = clock
        self.backups = backups or Path.home() / "second-look-backups"
        self.log_path = self.backups / "lock.log"
        self.read_qa_key = qa_key
        self.qa_key: str | None = None
        self.say = say
        self.start: Start | None = None
        self.started_at = clock()
        self.backup_file: Path | None = None
        self.result: dict[str, Any] = {}
        self.result_rel = ""
        self.result2: dict[str, Any] | None = None
        self.result2_rel = ""
        self.targets: tuple[dr.Row | None, dr.Row | None] = (None, None)
        self.deploy_started = False
        self.pushed = False

    # -- small helpers -----------------------------------------------------

    def log(self, line: str) -> None:
        name = "lock" if self.wave.number == 1 else f"lock {self.wave.number}"
        text = f"{stamp(self.clock())} {name}: {line}"
        self.say(text)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(text + "\n")

    def git(self, *args: str) -> Done:
        return self.local.run(["git", *args], cwd=self.root, timeout=600)

    def must(self, step: str, done: Done, what: str) -> Done:
        if not done.ok:
            raise Failed(step, f"{what} failed: {done.tail()}")
        return done

    def head(self) -> str:
        return self.must("git", self.git("rev-parse", "HEAD"), "git rev-parse").out.strip()

    # -- the steps ---------------------------------------------------------

    def already_done(self) -> str | None:
        found = real_results(self.root, self.wave)
        if found:
            return f"the lock analysis already ran: {found[0].relative_to(self.root)}"
        return None

    def audit_lines(self) -> tuple[list[str], str]:
        """The lines a Mac job added to the audit log in this checkout, and why they cannot be
        carried, which is empty when they can."""
        if not self.wave.carries_audit_lines:
            return [], "this run carries no lines"
        path = self.root / AUDIT_LOG
        committed = self.git("show", f"HEAD:{AUDIT_LOG}")
        working = path.read_text(encoding="utf-8") if path.is_file() else ""
        added = added_lines(committed.out if committed.ok else "", working)
        if not added:
            return [], "it was changed, not only added to at its end"
        kinds = mac_jobs.mac_job_audit_kinds()
        try:
            entries = [json.loads(line) for line in added]
            other = sorted({str(e["kind"]) for e in entries} - set(kinds))
            audit_log.verify(path)
        except (ValueError, KeyError, TypeError, audit_log.AuditError) as e:
            return [], f"its chain does not hold with the added lines: {e}"
        if other:
            return [], f"an added line is of a kind no Mac job writes: {', '.join(other)}"
        return added, ""

    def refused(self, changed: Sequence[str]) -> list[str]:
        """The local changes this run will not start with, each by name, the reason with it."""
        theirs = mac_jobs.mac_job_files()
        out = []
        for path in changed:
            if allowed(path, theirs):
                continue
            if path == AUDIT_LOG and self.wave.carries_audit_lines:
                why = self.audit_lines()[1]
                if why:
                    out.append(f"{path} ({why})")
                continue
            out.append(path)
        return out

    def carry(self, start: Start) -> None:
        """Put the carried lines at the end of the audit log, unless it holds them already."""
        if not start.carried:
            return
        path = self.root / AUDIT_LOG
        have = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
        missing = [line for line in start.carried if line not in have]
        if not missing:
            self.log("the audit log already holds the lines the other Mac job added")
            return
        entries = [json.loads(line) for line in missing]
        last, n = audit_log.last_hash(path), len(have)
        follows = entries[0]["prev_hash"] == last and entries[0]["seq"] == n + 1
        if not follows:
            # origin/depth added lines of its own, so these no longer follow the last one. They
            # are chained again after it: the same time, kind and payload hash, a new place.
            aside = self.backups / f"set-aside-{self.started_at.strftime('%Y%m%dT%H%M%SZ')}"
            (aside / AUDIT_LOG).parent.mkdir(parents=True, exist_ok=True)
            (aside / AUDIT_LOG).write_text("\n".join(missing) + "\n", encoding="utf-8")
            chained = []
            for entry in entries:
                n += 1
                again = {**entry, "seq": n, "prev_hash": last}
                again["hash"] = hashlib.sha256(audit_log.hashed_text(again).encode()).hexdigest()
                last = again["hash"]
                chained.append(json.dumps(again, separators=(",", ":")))
            missing = chained
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write("\n".join(missing) + "\n")
        audit_log.verify(path)
        kinds = ", ".join(sorted({str(e["kind"]) for e in entries}))
        self.log(
            f"carried {len(missing)} line(s) another Mac job added to the audit log ({kinds}), "
            + (
                "as written"
                if follows
                else "chained again after the lines origin/depth added; as written they are in "
                f"set-aside-{self.started_at.strftime('%Y%m%dT%H%M%SZ')}"
            )
        )

    def freshen(self) -> None:
        step = "fresh checkout"
        branch = self.must(step, self.git("rev-parse", "--abbrev-ref", "HEAD"), "git").out.strip()
        if branch != "depth":
            raise Failed(step, f"the checkout is on {branch}, not depth")
        status = self.must(
            step, self.git("status", "--porcelain=v1", "-z", "--untracked-files=all"), "git status"
        )
        changed = sorted(set(porcelain(status.out)))
        other = self.refused(changed)
        if other:
            raise Failed(step, "local changes other than the Mac jobs' files: " + ", ".join(other))
        carried: tuple[str, ...] = ()
        if AUDIT_LOG in changed:
            carried = tuple(self.audit_lines()[0])
        # The other jobs' files are set aside for the whole run, so make check, the commit and
        # the deploy all see exactly what is committed; put_back returns them at the end. The
        # lines added to the audit log are not set aside: carry() puts them back below.
        kept: dict[str, bytes | None] = {}
        for rel in changed:
            if rel == AUDIT_LOG and carried:
                continue
            path = self.root / rel
            kept[rel] = path.read_bytes() if path.is_file() else None
        before = self.head()
        self.start = Start(before, before, kept, carried)
        for rel in changed:
            if self.git("cat-file", "-e", f"HEAD:{rel}").ok:
                self.must(
                    step,
                    self.git("restore", "--source=HEAD", "--staged", "--worktree", "--", rel),
                    "git restore",
                )
            else:
                (self.root / rel).unlink(missing_ok=True)
        if changed:
            self.log(
                "set aside until the end, written by the other Mac jobs: " + ", ".join(changed)
            )
        fetched = self.out.run(["git", "fetch", "origin", "depth", "main"], cwd=self.root)
        self.must(step, fetched, "git fetch origin")
        self.must(step, self.git("merge", "--ff-only", "origin/depth"), "fast-forward")
        after = self.head()
        self.start = Start(after, before, kept, carried)
        self.log(
            f"fast-forwarded from {before[:7]} to {after[:7]}"
            if before != after
            else f"already at origin/depth, {after[:7]}"
        )
        try:
            self.carry(self.start)
        except (OSError, ValueError, KeyError, audit_log.AuditError) as e:
            raise Failed(step, f"the lines added to the audit log could not be carried: {e}") from e

    def preflight(self) -> None:
        step = "preflight"
        ff = self.git("merge-base", "--is-ancestor", "origin/main", "HEAD")
        if not ff.ok:
            raise Failed(step, "origin/main has commits depth does not; merge forward by hand")
        self.must(
            step,
            self.out.run(["npx", "wrangler", "whoami"], cwd=self.root / "worker"),
            "wrangler whoami",
        )
        self.must(step, self.out.run(["gh", "auth", "status"], cwd=self.root), "gh auth status")
        self.qa_key = self.read_qa_key()
        if not self.qa_key:
            raise Failed(
                step, "no QA_KEY in the environment or .env, so the phone check cannot run"
            )
        hosting = self.root / HOSTING
        rows = dr.load(hosting)
        live_w, live_p = dr.live_worker(self.out, self.root), dr.live_pages(self.out, self.root)
        # A recorded deploy that passes the read-only phone check now counts as good.
        readonly = self.out.run(
            ["node", "apps/web/scripts/live-readonly.mjs"], cwd=self.root, env={"SITE_URL": SITE}
        )
        self.must(
            step, readonly, "the read-only phone check against production before the lock work"
        )
        live_commit = (live_p or {}).get("commit", "")[:7]

        def is_live(r: dr.Row) -> bool:
            if r.part == "worker":
                return r.id == live_w
            return bool(live_commit) and r.commit[:7] == live_commit

        marked = [replace(r, checked=True) if is_live(r) else r for r in rows]
        if marked != rows:
            dr.save(marked, hosting)
            self.log("the live deploy passed the phone check, so its rows are marked good")
        w, p, problems = dr.good_for_live(marked, live_w, live_p)
        if problems:
            raise Failed(step, "; ".join(problems))
        self.targets = (w, p)
        assert w is not None and p is not None
        self.log(f"production to return to on failure: Worker {w.id}, Pages {p.id} ({p.commit})")

    def backup(self) -> None:
        step = "backup"
        done = self.out.run(
            ["bash", "scripts/backup_d1.sh"],
            cwd=self.root,
            env={"BACKUP_DIR": str(self.backups)},
            timeout=900,
        )
        self.must(step, done, "scripts/backup_d1.sh")
        try:
            meta = json.loads((self.backups / "last_backup.json").read_text(encoding="utf-8"))
            made = datetime.fromisoformat(str(meta["generated_at_utc"]).replace("Z", "+00:00"))
            path = Path(str(meta["file"]))
        except (OSError, ValueError, KeyError) as e:
            raise Failed(step, f"no readable last_backup.json: {e}") from e
        if made < self.started_at.replace(microsecond=0) or not path.is_file():
            raise Failed(step, f"the newest backup, {path.name}, is not from this run")
        self.backup_file = path
        self.log(f"backed up D1 to {path.name}")

    def export(self) -> None:
        assert self.backup_file is not None
        out_dir = self.root / "data" / "export"
        counts = study_export.export(self.backup_file, out_dir)
        keep = self.backups / f"lock-{self.clock().strftime('%Y%m%dT%H%M%SZ')}"
        keep.mkdir(parents=True, exist_ok=True)
        os.chmod(keep, 0o700)
        for name in ("sessions.csv", "responses.csv", *PART2_FILES):
            if not (out_dir / name).exists():
                continue  # part 2's files only exist once its tables do
            shutil.copy2(out_dir / name, keep / name)
            os.chmod(keep / name, 0o600)
        self.log(
            f"exported {counts['sessions']} sessions and {counts['responses']} responses from "
            f"{self.backup_file.name}; a copy is in {keep.name}"
        )

    def analysis(self) -> None:
        step = "analysis"
        done = self.local.run(
            ["uv", "run", "python", self.wave.analysis], cwd=self.root, timeout=1800
        )
        self.must(step, done, self.wave.analysis)
        m = re.search(r"^wrote json: (.+)$", done.out, re.M)
        if not m:
            raise Failed(step, "the analysis did not say where it wrote its result")
        path = Path(m.group(1).strip())
        path = path if path.is_absolute() else self.root / path
        self.result = json.loads(path.read_text(encoding="utf-8"))
        if self.result.get("synthetic") is not False:
            raise Failed(step, f"{path.name} is not a real result")
        self.result_rel = path.relative_to(self.root).as_posix()
        export = self.root / "data" / "export"
        hashed: tuple[str, ...] = ("sessions.csv", "responses.csv")
        if self.wave.number != 1:
            hashed += tuple(n for n in PART2_FILES if (export / n).exists())
        record = {
            "generated_at_utc": stamp(self.clock()),
            "script": SCRIPT,
            "synthetic": False,
            "stamp": self.result.get("stamp"),
            "analysis": self.result_rel,
            "status": (self.result.get("primary") or {}).get("status"),
            "backup_file": self.backup_file.name if self.backup_file else None,
            "export_sha256": {n: sha256_file(export / n) for n in hashed},
            "checkout_at_start": self.start.head if self.start else None,
        }
        if self.wave.number == 1:
            self.part2_analysis(export)
        else:
            self.part2_of_the_wave(done.out)
        record["part2_analysis"] = self.result2_rel or None
        record["part2_status"] = ((self.result2 or {}).get("primary") or {}).get("status")
        if self.wave.number != 1:
            window = self.result.get("window") or {}
            record["wave"] = self.wave.number
            record["plan"] = window.get("plan")
            record["window"] = {k: window.get(k) for k in ("open_utc", "lock_utc")}
        (self.root / self.wave.record).write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )
        self.log(
            f"ran the pre-registered analysis once: {self.result_rel}, {record['status']}"
            if self.wave.number == 1
            else f"ran the second wave's analysis once: {self.result_rel}, {record['status']}"
        )
        # The audit log's own line for the lock, which the done list asks for and nothing wrote
        # (found on 2026-09-29): the record above, by its hash, chained to every line before it.
        # It goes into the lock's commit, and a failed run undoes it with everything else.
        try:
            receipt = audit_log.append("data_lock", record, path=self.root / "audit" / "log.jsonl")
        except audit_log.AuditError as e:
            raise Failed(step, f"the audit log refused the data_lock line: {e}") from e
        self.log(f"the audit log holds the data lock, receipt {receipt[:12]}")

    def part2_of_the_wave(self, said: str) -> None:
        """The second wave's part 2 result, which the wave's one script wrote in the same run,
        or none at all when the export has no part 2 files."""
        step = "part 2 analysis"
        m = re.search(r"^wrote part 2 json: (.+)$", said, re.M)
        if not m:
            if not re.search(r"^part 2: the export holds no part 2 files", said, re.M):
                raise Failed(step, "the analysis did not say what it did with part 2")
            self.log("part 2 has no files in the export, so its row says nobody took it")
            return
        path = Path(m.group(1).strip())
        path = path if path.is_absolute() else self.root / path
        self.result2 = json.loads(path.read_text(encoding="utf-8"))
        if self.result2.get("synthetic") is not False:
            raise Failed(step, f"{path.name} is not a real result")
        self.result2_rel = path.relative_to(self.root).as_posix()
        status = (self.result2.get("primary") or {}).get("status")
        self.log(f"ran the second wave's part 2 analysis once: {self.result2_rel}, {status}")

    def part2_analysis(self, export: Path) -> None:
        """Part 2 (UPDATE_31), right after part 1: the one run tagged prereg-v2, or none at all
        when the export has no part 2 files, because part 2 never had a table to fill."""
        step = "part 2 analysis"
        if not all((export / n).exists() for n in PART2_FILES):
            self.log("part 2 has no files in the export, so its row says nobody took it")
            return
        done = self.local.run(
            ["uv", "run", "python", "evals/assist_analysis.py"], cwd=self.root, timeout=1800
        )
        self.must(step, done, "evals/assist_analysis.py")
        m = re.search(r"^wrote json: (.+)$", done.out, re.M)
        if not m:
            raise Failed(step, "the part 2 analysis did not say where it wrote its result")
        path = Path(m.group(1).strip())
        path = path if path.is_absolute() else self.root / path
        self.result2 = json.loads(path.read_text(encoding="utf-8"))
        if self.result2.get("synthetic") is not False:
            raise Failed(step, f"{path.name} is not a real result")
        self.result2_rel = path.relative_to(self.root).as_posix()
        status = (self.result2.get("primary") or {}).get("status")
        self.log(f"ran the part 2 analysis once: {self.result2_rel}, {status}")

    def readme(self) -> None:
        step = "readme"
        finished = people_kept(self.result) > 0
        path = self.root / "README.md"
        text = path.read_text(encoding="utf-8")
        if self.wave.number == 1:
            placed = place_part2_row(
                place_human_row(text, human_row(self.result, self.result_rel), finished),
                part2_row(self.result2, self.result2_rel),
            )
        else:
            placed = place_wave2_rows(
                text,
                human_row(self.result, self.result_rel, self.wave),
                part2_row(self.result2, self.result2_rel, self.wave),
                finished,
            )
        path.write_text(placed, encoding="utf-8")

        # The README quotes the report's page count and the report quotes the README, so render
        # and rebuild until both settle, then check every claim.
        def make(target: str) -> None:
            self.must(step, self.local.run(["make", target], cwd=self.root), f"make {target}")

        make("render-readme")
        make("report-pdf")
        before = path.read_bytes()
        make("render-readme")
        if path.read_bytes() != before:
            make("report-pdf")
            make("render-readme")
        if "{{claim:" in path.read_text(encoding="utf-8"):
            raise Failed(step, "a number in the human row found no value in the result")
        make("verify-claims")
        self.log(
            ("the README's human row is in, " if self.wave.number == 1 else "")
            + ("the README's rows for the second wave are in, " if self.wave.number != 1 else "")
            + ("with people" if finished else "saying nobody finished")
        )

    def check(self) -> None:
        done = self.local.run(["make", "check"], cwd=self.root, timeout=5400)
        self.must("make check", done, "make check")
        self.git("checkout", "--", *REWRITTEN_BY_CHECK)
        self.log("make check is green")

    def commit(self, message: str, only: Sequence[str] | None = None) -> str:
        step = "commit"
        assert self.start is not None
        status = self.must(
            step, self.git("status", "--porcelain=v1", "-z", "--untracked-files=all"), "git status"
        )
        mine = [p for p in porcelain(status.out) if p not in self.start.kept]
        if only is not None:
            mine = [p for p in mine if p in only]
        if not mine:
            raise Failed(step, "nothing to commit")
        self.must(step, self.git("add", "--all", "--", *mine), "git add")
        self.must(step, self.git("commit", "-q", "-m", message), "git commit")
        head = self.head()
        self.log(f"committed {head[:7]} on depth: {len(mine)} file(s)")
        return head

    def deploy(self) -> None:
        env = {"ALLOW_BRANCH": "yes"}
        self.deploy_started = True
        self.must(
            "deploy worker",
            self.out.run(["bash", "scripts/deploy.sh", "worker"], cwd=self.root, env=env),
            "scripts/deploy.sh worker",
        )
        self.log("the Worker is deployed")
        step = "phone tests after the Worker"
        self.must(
            step,
            self.local.run(
                ["uv", "run", "pytest", "-q", "apps/api/tests/test_study.py"], cwd=self.root
            ),
            "the study contract tests",
        )
        live = self.out.run(
            ["node", "apps/web/scripts/live-check.mjs"],
            cwd=self.root,
            env={"SITE_URL": SITE, "QA_KEY": self.qa_key or ""},
        )
        self.must(step, live, "the phone check with the QA key")
        self.must(
            "deploy web",
            self.out.run(["bash", "scripts/deploy.sh", "web"], cwd=self.root, env=env),
            "scripts/deploy.sh web",
        )
        self.log("the site is deployed")
        step = "phone tests after the site"
        readonly = self.out.run(
            ["node", "apps/web/scripts/live-readonly.mjs"], cwd=self.root, env={"SITE_URL": SITE}
        )
        self.must(step, readonly, "the read-only phone check")
        for path in ("/health", "/api/test/counts"):
            reply = self.out.get(f"{SITE}{path}")
            if reply.status != 200:
                raise Failed(step, f"{SITE}{path} answered {reply.status or reply.error}")
        # The site's build rewrote these, as make check's did; they are not part of the lock.
        self.git("checkout", "--", *REWRITTEN_BY_CHECK)
        self.log("the phone tests pass against production")

    def judge_mode(self) -> None:
        step = "judge mode"
        # From the checkout's root, like every other script here. It once ran from apps/web with
        # this same path, which names no file from there, so the last step of the first full run
        # crashed and the whole lock was undone (2026-09-29).
        page = self.out.run(["node", "apps/web/scripts/demo-open-check.mjs"], cwd=self.root)
        self.must(step, page, "the /demo check (the shut page must be gone)")
        reply = self.out.http(
            f"{SITE}/api/demo/answer",
            method="POST",
            body=json.dumps({"item_id": "lock-job-check", "answer": "yes"}).encode(),
            headers={"content-type": "application/json"},
        )
        # Open, the route answers an unknown item with 404; shut, with 403 whatever it is asked.
        if reply.status != 404:
            raise Failed(step, f"/api/demo/answer answered {reply.status or reply.error}, not 404")
        self.log("judge mode is open on production: /demo shows it and /api/demo/answer answers")

    def mark_good(self) -> None:
        hosting = self.root / HOSTING
        rows = dr.load(hosting)
        dr.save(dr.mark_good(rows, self.head()[:7]), hosting)

    def push(self, dry: bool) -> None:
        argv = ["git", "push", "--atomic", *(["--dry-run"] if dry else []), "origin",
                "HEAD:refs/heads/depth", "HEAD:refs/heads/main"]  # fmt: skip
        step = "push dry run" if dry else "push"
        self.must(step, self.out.run(argv, cwd=self.root, timeout=600), " ".join(argv[:4]))
        if not dry:
            self.pushed = True
            self.log(f"pushed {self.head()[:7]} to depth and main in one atomic push")

    def status_line(self) -> str:
        counts = self.result.get("counts") or {}
        status = (self.result.get("primary") or {}).get("status")
        if self.wave.number != 1:
            return (
                f"Second data lock done ({stamp(self.clock())}): the second wave's analysis ran "
                f"once under plan prereg-v3 ({self.result_rel}, {status}); completed and kept, "
                f"trained {counts.get('completed_trained', 0)} and untrained "
                f"{counts.get('completed_untrained', 0)}. {self.part2_status()} "
                f"Commit {self.head()[:7]} is on depth and main, deployed, the phone tests "
                "pass, and judge mode is open."
            )
        return (
            f"Data lock done ({stamp(self.clock())}): the pre-registered analysis ran once "
            f"({self.result_rel}, {status}); completed and kept, trained "
            f"{counts.get('completed_trained', 0)} and untrained "
            f"{counts.get('completed_untrained', 0)}. {self.part2_status()} "
            f"Commit {self.head()[:7]} is on depth and main, deployed, the phone tests pass, "
            "and judge mode is open."
        )

    def part2_status(self) -> str:
        if self.result2 is None:
            return "Part 2: nobody took it before the lock."
        if self.wave.number != 1:
            p = self.result2.get("primary") or {}
            return (
                f"Part 2 of the second wave ({self.result2_rel}, {p.get('status')}): assisted "
                f"{p.get('n_assisted')}, unassisted {p.get('n_unassisted')}."
            )
        p = self.result2.get("primary") or {}
        return (
            f"Part 2 ({self.result2_rel}, {p.get('status')}): assisted {p.get('n_assisted')}, "
            f"unassisted {p.get('n_unassisted')}."
        )

    # -- undo --------------------------------------------------------------

    def undo(self, failure: Failed) -> None:
        notes = []
        if self.deploy_started:
            notes.append(self.undo_production())
        if self.start is not None:
            notes.append(self.undo_repo(self.start))
        line = (
            f"FAILED at {failure.step}: {failure.detail}. " + " ".join(notes) +
            f" Nothing was pushed. Fix it, then run make {self.wave.make} again."
        )  # fmt: skip
        self.log(line)
        posted = self.out.comment(
            f"{self.wave.job_words} job: {line} (log: ~/second-look-backups/lock.log)"
        )
        if not posted.ok:
            self.log(f"could not write to the status issue either: {posted.tail()}")

    def undo_production(self) -> str:
        worker_row, web_row = self.targets
        live_w, live_p = dr.live_worker(self.out, self.root), dr.live_pages(self.out, self.root)
        back_w = worker_row if worker_row and live_w != worker_row.id else None
        live_commit = (live_p or {}).get("commit", "")[:7]
        back_p = web_row if web_row and live_commit != web_row.commit[:7] else None
        if back_w is None and back_p is None:
            return "Production was not changed."
        ok = rb.carry_out(rb.to_targets(back_w, back_p, self.root), self.out, self.log)
        parts = ", ".join(p for p, r in (("the Worker", back_w), ("the site", back_p)) if r)
        return (
            f"Production was rolled back ({parts})."
            if ok
            else f"Production could NOT be rolled back ({parts}); run make rollback ROLLBACK=yes."
        )

    def undo_repo(self, start: Start) -> str:
        self.git("reset", "-q", "--hard", start.head)
        # The run began with no untracked file but the other jobs', which are set aside.
        for rel in self.git("ls-files", "--others", "--exclude-standard").out.splitlines():
            (self.root / rel).unlink(missing_ok=True)
        self.put_back(start)
        try:
            self.carry(start)
        except (OSError, ValueError, KeyError, audit_log.AuditError) as e:
            return (
                f"The checkout is back at {start.head[:7]}, with the other jobs' files kept, "
                f"but the lines added to the audit log could not be put back: {e}."
            )
        return f"The checkout is back at {start.head[:7]}, with the other jobs' files kept."

    def put_back(self, start: Start) -> None:
        """Return the other jobs' files, unless origin/depth brought a newer copy of one."""
        dropped = []
        aside = self.backups / f"set-aside-{self.started_at.strftime('%Y%m%dT%H%M%SZ')}"
        for rel, data in start.kept.items():
            if not self.git("diff", "--quiet", start.before, "HEAD", "--", rel).ok:
                dropped.append(rel)
                if data is not None:  # nothing is lost: the job's copy is kept outside the repo
                    (aside / rel).parent.mkdir(parents=True, exist_ok=True)
                    (aside / rel).write_bytes(data)
                continue
            path = self.root / rel
            if data is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        if dropped:
            self.log(
                "origin/depth changed these, so its copy stands; the other job's copy is in "
                f"{aside}: " + ", ".join(dropped)
            )

    # -- is this Mac ready? -------------------------------------------------

    def readiness(self) -> list[str]:
        """What would stop the lock job, checked without changing anything, on any day."""
        problems = []
        branch = self.git("rev-parse", "--abbrev-ref", "HEAD").out.strip()
        if branch != "depth":
            problems.append(f"the checkout {self.root} is on {branch or 'nothing'}, not depth")
        status = self.git("status", "--porcelain=v1", "-z", "--untracked-files=all")
        other = self.refused(porcelain(status.out))
        if other:
            problems.append("local changes the lock job would refuse: " + ", ".join(other[:8]))
        for tool in ("uv", "npx", "node", "gh", "make", "pandoc", "java", "gitleaks"):
            if shutil.which(tool) is None:
                problems.append(f"{tool} is not on PATH; make check or the deploy needs it")
        for folder in (
            "apps/web/node_modules",
            "worker/node_modules",
            "tools/diagrams/node_modules",
        ):
            if not (self.root / folder).is_dir():
                problems.append(f"{folder} is missing; run npm ci there")
        if not self.out.run(["npx", "wrangler", "whoami"], cwd=self.root / "worker").ok:
            problems.append("wrangler is not logged in (npx wrangler login in worker/)")
        if not self.out.run(["gh", "auth", "status"], cwd=self.root).ok:
            problems.append("gh is not logged in (gh auth login)")
        if not self.read_qa_key():
            problems.append("no QA_KEY in the environment or this checkout's .env")
        rows = dr.load(self.root / HOSTING)
        live_w, live_p = dr.live_worker(self.out, self.root), dr.live_pages(self.out, self.root)
        # Rows not yet marked good still count: the job marks them after its read-only check.
        as_if_good = [replace(r, checked=True) for r in rows]
        problems += dr.good_for_live(as_if_good, live_w, live_p)[2]
        if self.wave.number != 1:
            # What the second wave's analysis would refuse for once the lock has passed: the
            # tag missing from this checkout, the script not pinned, a plan or a script changed.
            why = wave2_analysis.refusal_reason(self.wave.lock_utc, self.root)
            if why:
                problems.append(
                    "the second wave's analysis would refuse: "
                    + why.removeprefix("Refusing to run: ")
                )
        return problems

    # -- the whole thing ---------------------------------------------------

    def run(self) -> int:
        now = self.clock()
        if now < self.wave.lock_utc:
            self.log(
                f"refused: it is {stamp(now)}, before {self.wave.lock_words} at "
                f"{stamp(self.wave.lock_utc)}; nothing was done"
            )
            return 3
        try:
            done_before = self.already_done()
            if done_before:
                self.log(f"nothing to do: {done_before}")
                return 0
            self.freshen()
            done_before = self.already_done()
            if done_before:
                self.log(f"nothing to do after the fast-forward: {done_before}")
                assert self.start is not None
                self.put_back(self.start)
                return 0
            self.preflight()
            self.backup()
            self.export()
            self.analysis()
            self.readme()
            self.check()
            head = self.commit(
                (
                    "Data lock: the one pre-registered analysis, and the README's human row\n\n"
                    if self.wave.number == 1
                    else "Second data lock: the second wave's one analysis, and its README rows\n\n"
                )
                + f"Run by {SCRIPT} after the lock at {stamp(self.wave.lock_utc)}, from the "
                f"backup {self.backup_file.name if self.backup_file else ''}. main moves here "
                "by fast-forward."
            )
            self.log(f"main will move to {head[:7]} by fast-forward")
            self.push(dry=True)
            self.deploy()
            self.judge_mode()
            self.mark_good()
            self.commit(
                f"Record the deploy after {self.wave.lock_words} as good\n\n"
                "The phone tests passed.",
                only=[HOSTING],
            )
            self.push(dry=False)
            assert self.start is not None
            self.put_back(self.start)
        except Failed as failure:
            self.undo(failure)
            return 1
        except Exception as e:  # any surprise must still undo and report
            self.undo(Failed("unexpected", f"{type(e).__name__}: {e}"))
            return 1
        line = self.status_line()
        self.log(line)
        posted = self.out.comment(line)
        if not posted.ok:
            self.log(
                f"the lock is done, but the status issue could not be written: {posted.tail()}"
            )
        counts = panel_status.read_counts(self.out, SITE)
        if counts is not None:
            self.log(
                panel_status.update_issue(
                    self.out, counts, when=self.clock().strftime("%Y-%m-%d %H:%M UTC"), force=True,
                    state=self.backups / "state" / "panel_counts.json",
                )
            )  # fmt: skip
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--ready",
        action="store_true",
        help="only say whether this Mac and checkout are ready for the lock; change nothing",
    )
    parser.add_argument(
        "--wave",
        type=int,
        choices=sorted(WAVES),
        default=1,
        help="2 is the second run, for the second wave, after the second lock",
    )
    args = parser.parse_args(argv)
    lock = Lock(
        root=ROOT,
        out=Outward(),
        local=Local(),
        qa_key=lambda: qa_key_from(ROOT),
        wave=WAVES[args.wave],
    )
    if args.ready:
        problems = lock.readiness()
        for p in problems:
            print(f"lock-ready: {p}")
        print("lock-ready: ready" if not problems else f"lock-ready: {len(problems)} problem(s)")
        return 1 if problems else 0
    return lock.run()


if __name__ == "__main__":
    sys.exit(main())
