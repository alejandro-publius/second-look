"""Build docs/THIRD_PARTY.md from uv.lock and the npm lockfiles (hard rule 1).

Run: uv run python scripts/third_party.py
Python licenses come from the installed package metadata (importlib.metadata); npm licenses from
the lockfile or each installed package's package.json. The npm lockfiles are apps/web's, the
Worker's and tools/diagrams', the pinned Mermaid renderer. Where neither says, the table says so.
The external services section is written here too, so the file is always whole.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
NOT_STATED = "not stated in package metadata"
LICENSE_FILES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "license", "license.md", "LICENCE")
MIT_HEADING = re.compile(r"(The )?MIT License( \(MIT\))?")

SERVICES = """## External services

- Open-Meteo (https://open-meteo.com): rainfall lookups for the dry pipe rule in `core/rainfall.py`.
  Attribution shown wherever a rainfall figure appears: "Weather data by Open-Meteo.com, CC BY 4.0".
  Terms: https://open-meteo.com/en/terms (non-commercial use, fair rate limits, attribution).
  On any failure the app says "unknown" and skips the question; it never guesses.
- OneAquaHealth FHIR sandbox (https://sandbox.hl7europe.eu/oneaquahealth/fhir): read-only GETs at
  one per second with a user agent that names this repo, and a tagged mirror of our own records
  when `SANDBOX_MIRROR_ENABLED` is true. Conditional creates only, deletes by ledger id only.
- hl7-eu/oah implementation guide, commit b907cf0, built from source in CI with SUSHI 3.20.1 and
  validated with the HL7 validator. That repo has no LICENSE file, so nothing from it is
  redistributed here; `fhir/ig.lock` records the commit and the package sha256.
- Cloudflare Pages (web) and Cloudflare Workers with D1 (API) host the app (Update 09). What
  they log on their own is written in docs/DATA_HANDLING.md.
- The MCP server in `apps/mcp/` runs locally over stdio through the `mcp` Python SDK (MIT). It
  reads our own read only endpoint or a local export and calls no other service.
"""

REFERENCES = """## Design references

Read during the design pass (docs/internal/updates/UPDATE_06.md). Nothing is copied from either:
no brand colour, name, logo or font was taken. They informed structure and restraint only.

- Vercel Web Interface Guidelines, MIT
  (https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md).
  `apps/web` was audited against every rule in it; the findings are in
  docs/internal/reviews/DESIGN_REVIEW_01.md.
- VoltAgent awesome-design-md, MIT (https://github.com/VoltAgent/awesome-design-md). The Airbnb
  file for how a product lets photographs lead, the Wise file for how forms stay clear. Structure
  of docs/design/DESIGN.md borrows their shape: one read, tokens, components, do and do not.

## Fonts and icons

- Atkinson Hyperlegible Next and Atkinson Hyperlegible Mono, Braille Institute, SIL Open Font
  License 1.1, through the `@fontsource-variable/atkinson-hyperlegible-next` and
  `@fontsource/atkinson-hyperlegible-mono` packages. Self hosted through `next/font/local`, so no
  request leaves our origin and `font-src 'self'` stays as it is.
- Phosphor Icons, MIT, through `@phosphor-icons/core` (a devDependency). Regular weight only.
  `apps/web/scripts/build-icons.mjs` generates `components/ui/Icon.tsx` from its SVG assets, so
  there is no icon runtime in the bundle and no second icon family can appear.
"""

DIAGRAMS = """## The diagram renderer

- `tools/diagrams` draws the diagrams in `docs/diagrams/*.mmd` as SVG for `make diagrams`
  and `make diagrams-render` (UPDATE_27 block 23). It pins the Mermaid CLI (MIT), which loads
  Mermaid (MIT) and drives a browser through Puppeteer (Apache-2.0). Puppeteer downloads no
  browser of its own (`tools/diagrams/.puppeteerrc.cjs`): `playwright-core` (Apache-2.0), at the
  same version as apps/web's, finds the Chromium that `npx playwright install chromium` already
  installed, so a render needs no network. Chosen over a hosted renderer because it runs offline
  in CI, and over `npx @mermaid-js/mermaid-cli` because that fetches whatever version is newest.
  Nothing from these packages is served or shipped; only the SVGs they draw from our own sources
  are committed.
"""

TIMESTAMPS = """## Timestamps

- OpenTimestamps (https://opentimestamps.org), a public timestamp service, not our own chain,
  through the `opentimestamps-client` package (a dev dependency, the `ots` command). `ots stamp`
  sends only a SHA-256 hash to its public calendars (a.pool.opentimestamps.org,
  b.pool.opentimestamps.org, a.pool.eternitywall.com, ots.btc.catallaxy.com), which gather many
  hashes and write one summary of them into a Bitcoin transaction. No file, answer or name
  leaves this Mac. The proofs are in `proofs/`. `scripts/ots_status.py` asks the calendars for
  the finished proof and reads block headers from the public Blockstream explorer
  (https://blockstream.info/api), read only, to check a confirmed proof without a Bitcoin node.
"""


def python_license(name: str) -> str:
    try:
        meta = metadata.metadata(name)
    except metadata.PackageNotFoundError:
        return "not installed here"
    expr = meta.get("License-Expression")
    if expr:
        return str(expr).strip()
    lic = (meta.get("License") or "").strip()
    if lic and lic.upper() != "UNKNOWN" and len(lic) <= 60 and "\n" not in lic:
        return lic
    for c in meta.get_all("Classifier") or []:
        if c.startswith("License :: OSI Approved :: "):
            return c.split(" :: ")[-1].removesuffix(" License")
        if c.startswith("License :: "):
            return c.split(" :: ")[-1]
    return NOT_STATED


def python_packages(lock_path: Path) -> list[tuple[str, str, str]]:
    doc = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    rows: list[tuple[str, str, str]] = []
    for pkg in doc.get("package", []):
        source = pkg.get("source", {})
        if "editable" in source or "virtual" in source:
            continue  # this project itself
        name, version = str(pkg["name"]), str(pkg.get("version", ""))
        rows.append((name, version, python_license(name)))
    return sorted(rows, key=lambda r: r[0].lower())


def npm_name(path: str) -> str:
    return path.rsplit("node_modules/", 1)[-1]


def npm_license(entry: dict[str, Any], installed: Path) -> str:
    lic = entry.get("license")
    if isinstance(lic, str) and lic:
        return lic
    pkg_json = installed / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return NOT_STATED
        lic = data.get("license")
        if isinstance(lic, str) and lic:
            return lic
        if isinstance(lic, dict) and lic.get("type"):
            return str(lic["type"])
        licenses = data.get("licenses")
        if isinstance(licenses, list) and licenses:
            return " OR ".join(str(x.get("type", "")) for x in licenses if isinstance(x, dict))
    return license_file(installed) or NOT_STATED


def license_file(installed: Path) -> str | None:
    """MIT, when a package says so only in its license file and not in its package.json."""
    for name in LICENSE_FILES:
        path = installed / name
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        first = next((line.strip() for line in lines if line.strip()), "")
        if MIT_HEADING.fullmatch(first):
            return "MIT (from its license file)"
    return None


def npm_packages(lock_path: Path) -> list[tuple[str, str, str, bool]]:
    doc = json.loads(lock_path.read_text(encoding="utf-8"))
    web = lock_path.parent
    rows: list[tuple[str, str, str, bool]] = []
    for path, entry in doc.get("packages", {}).items():
        if not path:
            continue  # the app itself
        rows.append(
            (
                npm_name(path),
                str(entry.get("version", "")),
                npm_license(entry, web / path),
                bool(entry.get("dev", False)),
            )
        )
    rows.sort(key=lambda r: (r[0].lower(), r[1]))
    return rows


def build(root: Path) -> str:
    py = python_packages(root / "uv.lock")
    web_lock = root / "apps" / "web" / "package-lock.json"
    web = npm_packages(web_lock) if web_lock.exists() else []
    worker_lock = root / "worker" / "package-lock.json"
    worker = npm_packages(worker_lock) if worker_lock.exists() else []
    diagrams_lock = root / "tools" / "diagrams" / "package-lock.json"
    diagrams = npm_packages(diagrams_lock) if diagrams_lock.exists() else []
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    out = [
        "# Third party dependencies",
        "",
        f"Generated on {today} by `uv run python scripts/third_party.py` from `uv.lock`, "
        "`apps/web/package-lock.json`, `worker/package-lock.json` and "
        "`tools/diagrams/package-lock.json`. Do not edit by hand; rerun the script. Our own code "
        "is MIT; our photos and copy are CC BY 4.0 (README).",
        "",
        SERVICES.rstrip(),
        "",
        REFERENCES.rstrip(),
        "",
        DIAGRAMS.rstrip(),
        "",
        TIMESTAMPS.rstrip(),
        "",
        f"## Python packages ({len(py)}, from uv.lock)",
        "",
        "| Package | Version | License |",
        "|---|---|---|",
    ]
    out += [f"| {n} | {v} | {lic} |" for n, v, lic in py]
    out += [
        "",
        f"## Web packages ({len(web)}, from apps/web/package-lock.json)",
        "",
        "dev = only used to build or test, not shipped to a browser.",
        "",
        "| Package | Version | License | dev |",
        "|---|---|---|---|",
    ]
    out += [f"| {n} | {v} | {lic} | {'yes' if dev else ''} |" for n, v, lic, dev in web]
    out += [
        "",
        f"## Worker packages ({len(worker)}, from worker/package-lock.json)",
        "",
        "All dev: the toolchain that type checks, tests and runs the Worker locally. The deployed "
        "Worker bundles only our own code and worker/src/content.json.",
        "",
        "| Package | Version | License | dev |",
        "|---|---|---|---|",
    ]
    out += [f"| {n} | {v} | {lic} | {'yes' if dev else ''} |" for n, v, lic, dev in worker]
    out += [
        "",
        f"## Diagram tool packages ({len(diagrams)}, from tools/diagrams/package-lock.json)",
        "",
        "All dev: they draw the SVGs in docs/diagrams and do nothing else.",
        "",
        "| Package | Version | License | dev |",
        "|---|---|---|---|",
    ]
    out += [f"| {n} | {v} | {lic} | {'yes' if dev else ''} |" for n, v, lic, dev in diagrams]
    unknown_py = sum(1 for _, _, lic in py if lic in {NOT_STATED, "not installed here"})
    unknown_web = sum(1 for _, _, lic, _ in web + worker + diagrams if lic == NOT_STATED)
    out += [
        "",
        f"Licenses not found for {unknown_py} Python and {unknown_web} npm packages; "
        "check those by hand before the repo goes public.",
        "",
    ]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--out", type=Path, default=None, help="default docs/THIRD_PARTY.md")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    text = build(root)
    out = args.out or (root / "docs" / "THIRD_PARTY.md")
    out.write_text(text, encoding="utf-8")
    py = text.count("\n| ") - text.count("| Package |") - text.count("|---|")
    shown = out.relative_to(root) if out.is_relative_to(root) else out
    print(f"third-party: wrote {shown} with {py} package rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
