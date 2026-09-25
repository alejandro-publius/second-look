"""DEPLOY.md stays true to the code: every setting, every D1 table and every Mac job has a row.

The names come from scripts/config_inventory.py, which reads the code; the tables come from
worker/schema.sql; the jobs from the launchd installers. A name the code reads with no row fails,
and so does a row for a name nothing reads any more, or a default that differs from settings.py.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from scripts import config_inventory, mac_jobs

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "DEPLOY.md"


def section(heading: str) -> str:
    text = DEPLOY.read_text(encoding="utf-8")
    start = text.index(f"\n## {heading}\n")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def config_rows() -> dict[str, list[str]]:
    """Each name in the first cell of the configuration table, with that row's cells."""
    out: dict[str, list[str]] = {}
    for line in section("Configuration").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        for name in re.findall(r"`([A-Z][A-Z0-9_]+)`", cells[0]):
            assert name not in out, f"two rows for {name}"
            out[name] = cells
    return out


def settings_defaults() -> dict[str, object]:
    """Settings fields with a literal default, a module constant resolved to its value."""
    tree = ast.parse((ROOT / "apps" / "api" / "settings.py").read_text(encoding="utf-8"))
    constants = {
        t.id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
        for t in node.targets
        if isinstance(t, ast.Name)
    }
    out: dict[str, object] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Settings":
            for item in node.body:
                if not (isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)):
                    continue
                if isinstance(item.value, ast.Constant):
                    out[item.target.id.upper()] = item.value.value
                elif isinstance(item.value, ast.Name) and item.value.id in constants:
                    out[item.target.id.upper()] = constants[item.value.id]
    return out


def test_every_setting_the_code_reads_has_a_row_and_no_row_is_stale() -> None:
    found = set(config_inventory.inventory())
    documented = set(config_rows())
    assert found - documented == set(), "read by the code, missing from DEPLOY.md"
    assert documented - found == set(), "in DEPLOY.md, read by nothing"


def test_every_row_says_which_file_reads_it() -> None:
    rows = config_rows()
    for name, files in config_inventory.inventory().items():
        cell = rows[name][2]
        named = [f for f in files if f"`{f}`" in cell]
        assert named, f"{name}: the Read by cell names none of {sorted(files)}"


def test_the_settings_defaults_are_the_ones_in_settings_py() -> None:
    rows = config_rows()
    for name, value in settings_defaults().items():
        cell = rows[name][1]
        if isinstance(value, bool):
            want = "true" if value else "false"
        elif value == "":
            assert "empty" in cell, f"{name}: default is empty, the row says {cell!r}"
            continue
        else:
            want = str(value)
        assert f"`{want}`" in cell, f"{name}: settings.py says {want!r}, DEPLOY.md {cell!r}"


def test_every_d1_table_has_a_row() -> None:
    schema = (ROOT / "worker" / "schema.sql").read_text(encoding="utf-8")
    tables = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", schema))
    documented = set(re.findall(r"^\| `(\w+)` \|", section("The D1 schema"), re.M))
    assert tables and tables == documented


def test_every_launchd_job_has_a_row() -> None:
    labels = {job.label for job in mac_jobs.JOBS}
    for path in (ROOT / "scripts").glob("install_*_job.sh"):
        m = re.search(r'^LABEL="([\w.]+)"', path.read_text(encoding="utf-8"), re.M)
        assert m, path
        assert m.group(1) in labels, f"{path.name} installs a job scripts/mac_jobs.py does not list"
    documented = set(re.findall(r"^\| `(com\.[\w.]+)` \|", section("Jobs on the Mac"), re.M))
    assert labels and labels == documented


def test_every_daily_job_row_names_the_time_the_table_sets() -> None:
    rows = {
        m.group(1): m.group(2)
        for m in re.finditer(r"^\| `(com\.[\w.]+)` \| ([^|]+) \|", section("Jobs on the Mac"), re.M)
    }
    for job in mac_jobs.JOBS:
        if job.calendar and "Month" not in job.calendar:
            when = f"{job.calendar['Hour']:02d}:{job.calendar['Minute']:02d}"
            assert when in rows[job.label], f"{job.label}: {when} is not in its row"
    assert "every 10 minutes" in rows["com.secondlook.uptime"]
    assert "2026-09-28T01:10:00Z" in rows["com.secondlook.lock"]


def test_every_launchd_job_row_names_the_time_its_installer_sets() -> None:
    """The "When" cell says the HH:MM each installer writes into its plist."""
    rows = {
        m.group(1): m.group(2)
        for m in re.finditer(r"^\| `(com\.[\w.]+)` \| ([^|]+) \|", section("Jobs on the Mac"), re.M)
    }
    for path in sorted((ROOT / "scripts").glob("install_*_job.sh")):
        text = path.read_text(encoding="utf-8")
        label = re.search(r'^LABEL="([\w.]+)"', text, re.M)
        assert label, path
        times = re.findall(
            r"<key>Hour</key><integer>(\d+)</integer><key>Minute</key><integer>(\d+)</integer>",
            text,
        )
        assert times, f"{path.name} sets no time"
        for hour, minute in times:
            when = f"{int(hour):02d}:{int(minute):02d}"
            assert when in rows[label.group(1)], f"{label.group(1)}: {when} is not in {path.name}"


# A literal default in code: process.env.X ?? "v" or || 3102 in JavaScript, ${X:-v} in a shell
# script. Each one the inventory finds must be written in backticks in that row's default cell.
JS_DEFAULT = re.compile(
    r"process\.env\.([A-Z][A-Z0-9_]+)\s*(?:\?\?|\|\|)\s*(?:\"([^\"]*)\"|'([^']*)'|(-?\d+(?:\.\d+)?))"
)
SHELL_DEFAULT = re.compile(r"\$\{([A-Z][A-Z0-9_]+):-([^}$\"']*)\}")


def literal_defaults() -> dict[str, set[str]]:
    wanted = config_inventory.inventory()
    found: dict[str, set[str]] = {}
    for path in config_inventory._web_files():
        for m in JS_DEFAULT.finditer(path.read_text(encoding="utf-8")):
            value = next((g for g in m.groups()[1:] if g is not None), "")
            found.setdefault(m.group(1), set()).add(value)
    for path in sorted((ROOT / "scripts").glob("*.sh")):
        for name, value in SHELL_DEFAULT.findall(path.read_text(encoding="utf-8")):
            found.setdefault(name, set()).add(value)
    return {n: {v for v in vs if v} for n, vs in found.items() if n in wanted}


def test_every_literal_default_in_code_is_the_one_in_its_row() -> None:
    rows = config_rows()
    checked = 0
    for name, values in literal_defaults().items():
        for value in values:
            assert f"`{value}`" in rows[name][1], f"{name}: the code says {value!r}, {rows[name]}"
            checked += 1
    assert checked >= 10, "the reader found almost no default; has the code's shape changed?"


def test_the_worker_secrets_are_named_and_their_values_are_not() -> None:
    secrets = section("Secrets")
    for name in ("QA_KEY", "EXPORT_TOKEN", "ANTHROPIC_API_KEY"):
        assert f"`{name}`" in secrets
    assert not re.search(r"[0-9a-f]{32}", DEPLOY.read_text(encoding="utf-8"))


def test_the_inventory_reads_writes_apart_from_reads() -> None:
    text = 'os.environ["WRITTEN"] = "x"\nos.environ.get("READ_ONE")\nx = os.environ["READ_TWO"]\n'
    found = {n for p in config_inventory.PY_PATTERNS for n in p.findall(text)}
    assert found == {"READ_ONE", "READ_TWO"}
