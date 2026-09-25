"""Scaffold a follower city (Update 10 tier 2 item 3).

  uv run python scripts/new_city.py --name Heraklion --country Greece --lat 35.3387 --lon 25.1442

Given a name and coordinates it writes four things and makes no claim about any of them:

- content/regions/<slug>.yaml, a region pack stub: no plants, no creeks, every field that a local
  checker has to fill marked as such.
- fhir/fsh/city-<slug>.fsh, the nested Locations in FSH under their LocationOah profile: the city,
  one creek, one reach, one spot, each partOf the one above, in a Bundle that scripts/fhir_build.sh
  builds inside their guide and the HL7 validator checks in make check.
- docs/cities/<slug>/poster.html, the recruiting poster with the city's name, the same words as
  ours, a QR code drawn locally, and two empty slots where local photos go.
- docs/cities/<slug>/CHECKLIST.md, the five replication steps OneAquaHealth gives a follower
  city, each with the files and commands in this repository that do it.

It also records how long it took in docs/cities/TIMES.md. It never overwrites a city that exists
unless --force is given.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from core.content_loader import resolve_locale
from core.fhir_emit import FHIR_BASE, ID_SYSTEM_LOCATION
from core.regions import slugify

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SITE = "https://second-look-79t.pages.dev"
CITY_TYPE = ("288520005", "City environment")  # their own choice for Benevento and Oslo
RIVER_TYPE = ("420531007", "River")


class CityExists(Exception):
    pass


def region_pack(slug: str, name: str, country: str) -> str:
    return f"""# Region pack for {name}, {country}. A stub: every list below is empty until a local
# checker fills it. Species names appear on screen only on a photo a named person has verified,
# with a source.
region: {slug}
name: "{name}, {country}"
approved: false
invasive_plants: []
source: "to be filled by a local checker, from the regional invasive species inventory"

# Creeks and their reaches. Each creek has a readable slug, so the analyst's link reads
# /city?creek=<slug>. `flows_into` names the reach below; the downstream note appears only where it
# is set. `bbox` is [south, west, north, east] in degrees, approximate, from public maps.
# One creek with two reaches would look like this:
#
# creeks:
#   - slug: example-creek
#     name: Example Creek
#     source: "Hand filled <date> from public maps. Boxes are approximate."
#     reaches:
#       - slug: upper
#         name: Upper reach
#         flows_into: lower
#         bbox: [{0}, {1}, {2}, {3}]
#       - slug: lower
#         name: Lower reach
#         flows_into: null
#         bbox: [{0}, {1}, {2}, {3}]
creeks: []
"""


def locations_fsh(slug: str, name: str, country: str, lat: float, lon: float) -> str:
    city = f"sl-city-{slug}"
    creek = f"{city}-creek-1"
    reach = f"{creek}-reach-1"
    spot = f"{reach}-spot-1"
    today = datetime.now(UTC).date().isoformat()

    def loc(
        inst: str, title: str, ident: str, lname: str, kind: tuple[str, str], part_of: str | None
    ) -> str:
        lines = [
            f"Instance: {inst}",
            "InstanceOf: LocationOah",
            f'Title: "{title}"',
            "Usage: #inline",
            f'* identifier.system = "{ID_SYSTEM_LOCATION}"',
            f'* identifier.value = "{ident}"',
            f'* name = "{lname}"',
            "* mode = #instance",
            f'* type = $sct#{kind[0]} "{kind[1]}"',
        ]
        if part_of:
            lines.append(f"* partOf = Reference(Location/{part_of})")
        return "\n".join(lines)

    city_block = loc(city, f"{name} (city)", slug, name, CITY_TYPE, None)
    city_block += (
        f'\n* description = "City of {name}, {country}. Scaffolded by scripts/new_city.py on '
        f'{today}. A follower city stub: no creek has been checked here."'
        f"\n* position.latitude = {lat}\n* position.longitude = {lon}"
    )
    blocks = [
        f"// {name}, {country}: a follower city scaffold. scripts/new_city.py, {today}.",
        "// Four nested Locations under their LocationOah profile, each partOf the one above, in",
        "// one Bundle that builds inside their guide and passes the HL7 validator. The creek,",
        "// reach and spot are placeholders to be renamed by the city; nothing here is a finding.",
        "",
        city_block,
        "",
        loc(
            creek,
            f"{name}, creek to be named",
            f"{slug}-creek-1",
            f"{name}, creek 1 (to be named)",
            RIVER_TYPE,
            city,
        ),
        "",
        loc(
            reach,
            f"{name}, creek 1, reach to be named",
            f"{slug}-creek-1-reach-1",
            f"{name}, creek 1, reach 1 (to be named)",
            RIVER_TYPE,
            creek,
        ),
        "",
        loc(
            spot,
            f"{name}, creek 1, reach 1, spot 1",
            f"{slug}-creek-1-reach-1-spot-1",
            f"{name}, creek 1, reach 1, spot 1 (to be placed)",
            RIVER_TYPE,
            reach,
        ),
        "",
        f"Instance: {city}-bundle",
        "InstanceOf: Bundle",
        f'Title: "{name}: the nested Locations of a follower city"',
        f'Description: "City, creek, reach and spot for {name}, {country}, each partOf the one '
        "above, under the OneAquaHealth Location profile. A scaffold with placeholders, not a "
        'record."',
        "Usage: #example",
        "* type = #collection",
    ]
    for i, inst in enumerate((city, creek, reach, spot)):
        blocks.append(f'* entry[{i}].fullUrl = "{FHIR_BASE}/Location/{inst}"')
        blocks.append(f"* entry[{i}].resource = {inst}")
    return "\n".join(blocks) + "\n"


def qr_svg(url: str) -> str | None:
    """The QR code as SVG through the qrcode package the web app already has. None without it."""
    web = ROOT / "apps" / "web"
    if not (web / "node_modules" / "qrcode").exists() or shutil.which("node") is None:
        return None
    script = (
        "require('qrcode').toString(process.argv[1],{type:'svg',errorCorrectionLevel:'M',margin:1},"
        "(e,s)=>{if(e){process.exit(1)};process.stdout.write(s)})"
    )
    try:
        proc = subprocess.run(
            ["node", "-e", script, url], cwd=web, capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 and proc.stdout.startswith("<svg") else None


def poster_html(name: str, hook: str, scan: str, url: str, svg: str | None) -> str:
    qr = svg or (
        '<p class="note">QR code not drawn: run <code>cd apps/web && npm ci</code>, '
        "then this script again.</p>"
    )
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Second Look poster: {name}</title>
<style>
  body {{ margin: 0; font-family: system-ui, sans-serif; background: #fffdf7; color: #1b1b1b; }}
  .poster {{ min-height: 100vh; padding: 3rem; display: flex; flex-direction: column;
            align-items: center; gap: 2rem; text-align: center; }}
  h1 {{ font-size: 3rem; margin: 0; }}
  .pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; width: 100%;
          max-width: 44rem; }}
  .slot {{ aspect-ratio: 4 / 3; border: 2px dashed #1b1b1b; display: flex; align-items: center;
          justify-content: center; padding: 1rem; font-size: 1rem; }}
  .qr {{ width: 14rem; height: 14rem; }}
  .qr svg {{ width: 100%; height: 100%; }}
  .scan {{ font-size: 1.5rem; font-weight: 700; margin: 0; }}
  .url, .small, .note {{ font-size: 1rem; margin: 0; }}
  @media print {{ .poster {{ min-height: auto; }} }}
</style>
<div class="poster">
  <h1>{name}: {hook}</h1>
  <div class="pair" role="group" aria-label="Two local creek photos">
    <div class="slot">Local creek photo 1 goes here. Own or openly licensed, with a manifest
      row, no faces.</div>
    <div class="slot">Local creek photo 2 goes here. Own or openly licensed, with a manifest
      row, no faces.</div>
  </div>
  <p class="scan">{scan}</p>
  <div class="qr" role="img" aria-label="QR code that opens the two minute test">{qr}</div>
  <p class="url">{url}</p>
  <p class="small">Second Look. Print on Letter or A4. The answer is not printed here.</p>
</div>
</html>
"""


def checklist(slug: str, name: str, country: str, lat: float, lon: float) -> str:
    today = datetime.now(UTC).date().isoformat()
    return f"""# {name}, {country}: a follower city checklist

**A dry example in English. No claims.** Nobody has run Second Look in {name}. Nothing in this
folder is a finding about any creek. It was written by `scripts/new_city.py` on {today} from a
name and one pair of coordinates ({lat}, {lon}), to show that a new city is a checklist, not a
rebuild. OneAquaHealth calls a city that adopts the method a follower city and gives five steps.
Each step below names the files and commands in this repository that do it.

## 1. Name the streams

- [ ] Rename the placeholder creek, reach and spot in `fhir/fsh/city-{slug}.fsh` and add a
      Location per real creek, reach and spot, each `partOf` the one above.
- [ ] Fill `creeks:` in `content/regions/{slug}.yaml`: a readable slug per creek, its reaches
      from the hills down, `flows_into` on each, an approximate box from public maps.
- [ ] `bash scripts/fhir_build.sh` builds the guide with the new Locations inside it;
      `make check` runs the HL7 validator over the Bundle.

## 2. Adopt the form

- [ ] The creek check mirrors the official Citizen Science App in `content/form.yaml`. Check
      each item's wording against the app in the city's language; set `verified_against_app`.
- [ ] The two minute test and its scores are already a Questionnaire and a
      QuestionnaireResponse in `fhir/fsh/questionnaires-second-look.fsh`. Nothing to add.
- [ ] A new language is a file in `content/locales/`, shipped only with a named fluent checker
      recorded in it (PLAN.md, COULD list).

## 3. Train and test the volunteers

- [ ] About 40 local photos per the shot list, own or openly licensed, no faces or plates:
      `scripts/find_open_photos.py`, then `scripts/ingest_photos.py`.
- [ ] Two people label the 16 test photos blind through `scripts/label_photos.py`;
      `scripts/merge_labels.py` prints Cohen's kappa and refuses to freeze while they disagree.
- [ ] Fill `invasive_plants:` in `content/regions/{slug}.yaml` from the regional inventory,
      with the source named.
- [ ] `scripts/freeze_key.py`, then the lesson checked on strangers before launch.

## 4. Collect and validate

- [ ] Every visit becomes Observations under their indicator profile with Provenance back to
      the observer's score: `core/fhir_emit.py`, nothing to change.
- [ ] `make check` validates every emitted record in CI before it is stored or mirrored.
- [ ] Print `docs/cities/{slug}/poster.html` on Letter or A4 once two local photos are in.

## 5. Publish and repeat

- [ ] Mirror records to the sandbox with the tag and the ledger:
      `scripts/repush_sandbox.py`.
- [ ] Register the city's Library entry there: `scripts/repush_sandbox.py --library`.
- [ ] Return visits through the quick check, so one snapshot becomes a story.

## What this scaffold did not do

It did not choose any creek, place any pin, name any plant or state anything about the water.
Those are the city's to fill in, by hand, with sources.
"""


def _times_row(city: str, seconds: float, files: int) -> str:
    return (
        f"| {city} | `scripts/new_city.py` | wall clock of the script, measured by the script | "
        f"{seconds:.1f} seconds, {files} files |"
    )


def record_time(root: Path, city: str, seconds: float, files: int) -> Path:
    path = root / "docs" / "cities" / "TIMES.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            "# How long a follower city took\n\n"
            "Berkeley was built by hand as the first city. Every later city runs `make new-city`,\n"
            "which writes its own row here.\n\n"
            "| City | What | How measured | Time |\n|---|---|---|---|\n",
            encoding="utf-8",
        )
    with path.open("a", encoding="utf-8") as f:
        f.write(_times_row(city, seconds, files) + "\n")
    return path


def scaffold(
    *,
    root: Path,
    name: str,
    country: str,
    lat: float,
    lon: float,
    slug: str | None = None,
    site: str = DEFAULT_SITE,
    force: bool = False,
) -> list[Path]:
    started = time.monotonic()
    slug = slug or slugify(name)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("latitude must be within 90 and longitude within 180")
    targets = {
        "pack": root / "content" / "regions" / f"{slug}.yaml",
        "fsh": root / "fhir" / "fsh" / f"city-{slug}.fsh",
        "poster": root / "docs" / "cities" / slug / "poster.html",
        "checklist": root / "docs" / "cities" / slug / "CHECKLIST.md",
    }
    existing = [p for p in targets.values() if p.exists()]
    if existing and not force:
        raise CityExists(f"{slug} exists ({existing[0].relative_to(root)}); use --force to redo it")
    locale_path = root / "content" / "locales" / "en.json"
    raw = json.loads(locale_path.read_text(encoding="utf-8")) if locale_path.exists() else {}
    # As a person reads them: poster.scan quotes the test's time from time.test (judge walk W09).
    locale = resolve_locale(raw)
    hook = locale.get("landing.hook", "Which creek is healthier?")
    scan = locale.get("poster.scan", "Scan to find out. Anonymous.")
    url = f"{site.rstrip('/')}/?src=poster"
    written: list[Path] = []
    for key, text in (
        ("pack", region_pack(slug, name, country)),
        ("fsh", locations_fsh(slug, name, country, lat, lon)),
        ("poster", poster_html(name, hook, scan, url, qr_svg(url))),
        ("checklist", checklist(slug, name, country, lat, lon)),
    ):
        path = targets[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)
    written.append(record_time(root, name, time.monotonic() - started, len(written)))
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--name", required=True, help="the city's name, as people write it")
    parser.add_argument("--country", default="", help="the country, for the pack and the FSH")
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--slug", help="the link id; made from the name when not given")
    parser.add_argument("--site", default=DEFAULT_SITE, help="the site the poster's QR opens")
    parser.add_argument("--root", default=str(ROOT), help="the repository root to write into")
    parser.add_argument("--force", action="store_true", help="redo a city that exists")
    args = parser.parse_args(argv)
    try:
        written = scaffold(
            root=Path(args.root),
            name=args.name,
            country=args.country,
            lat=args.lat,
            lon=args.lon,
            slug=args.slug,
            site=args.site,
            force=args.force,
        )
    except (CityExists, ValueError) as exc:
        print(f"new-city: {exc}", file=sys.stderr)
        return 2
    root = Path(args.root)
    for path in written:
        print(f"new-city: wrote {path.relative_to(root)}")
    print("new-city: no claim was made; the checklist says what the city fills in by hand")
    return 0


if __name__ == "__main__":
    sys.exit(main())
