"""DEPLOY.md stays true to the code: every setting, every D1 table and every Mac job has a row.

The names come from scripts/config_inventory.py, which reads the code; the tables come from
worker/schema.sql; the jobs from the launchd installers. A name the code reads with no row fails,
and so does a row for a name nothing reads any more, or a default that differs from settings.py.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from scripts import config_inventory

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
    labels = set()
    for path in (ROOT / "scripts").glob("install_*_job.sh"):
        m = re.search(r'^LABEL="([\w.]+)"', path.read_text(encoding="utf-8"), re.M)
        assert m, path
        labels.add(m.group(1))
    documented = set(re.findall(r"^\| `(com\.[\w.]+)` \|", section("Jobs on the Mac"), re.M))
    assert labels and labels == documented


def test_the_worker_secrets_are_named_and_their_values_are_not() -> None:
    secrets = section("Secrets")
    for name in ("QA_KEY", "EXPORT_TOKEN", "ANTHROPIC_API_KEY"):
        assert f"`{name}`" in secrets
    assert not re.search(r"[0-9a-f]{32}", DEPLOY.read_text(encoding="utf-8"))


def test_the_inventory_reads_writes_apart_from_reads() -> None:
    text = 'os.environ["WRITTEN"] = "x"\nos.environ.get("READ_ONE")\nx = os.environ["READ_TWO"]\n'
    found = {n for p in config_inventory.PY_PATTERNS for n in p.findall(text)}
    assert found == {"READ_ONE", "READ_TWO"}
