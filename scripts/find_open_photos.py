"""Search Wikimedia Commons and iNaturalist for openly licensed creek photos to choose from.

Run: uv run python scripts/find_open_photos.py invasive_plant
     uv run python scripts/find_open_photos.py all

Writes photos/candidates/<feature>.html, a contact sheet for a person to read: a thumbnail served
from the source, the link to the source page, the author, the licence, and the source's own
caption or identification. Nothing is downloaded into the repo. photos/candidates/ is gitignored,
so a sheet is never deployed.

Filters: photo licence CC0, CC BY or CC BY-SA only, iNaturalist research grade only, California
first for plants. One request a second, no faster, with a user agent that names this project and
a contact, because both APIs are other people's machines.

This script never labels anything and never opens an image. A person picks, a person labels.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

from core import content_loader
from core.records import FEATURES

ROOT = Path(__file__).resolve().parents[1]
WARMUP = "warmup"
SHEETS: tuple[str, ...] = tuple(FEATURES) + (WARMUP,)

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
INAT_API = "https://api.inaturalist.org/v1/observations"
PROJECT_URL = "https://github.com/alejandro-publius/second-look"
CONTACT = os.environ.get(
    "SECOND_LOOK_CONTACT", "82622360+alejandro-publius@users.noreply.github.com"
)
USER_AGENT = f"SecondLookPhotoSearch/0.1 (Second Look, {PROJECT_URL}; contact {CONTACT})"
MIN_SECONDS = 1.0
CALIFORNIA_PLACE_ID = 14  # iNaturalist place id for the state of California
PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png"}
PER_TERM = 8
PER_SHEET = 120
TARGET = 40

# Licence codes we may use. Anything else, including any NC or ND licence and any unclear claim,
# is dropped rather than guessed at (hard rule 6).
# Built from the one allowlist in core/content_loader.py, so widening it there widens the pool
# here in the same commit. Keys are the tidy lowercase code this file parses out of a source.
MANIFEST_LICENCES = {
    code.lower(): code for code in content_loader.REAL_LICENSES if code.startswith(("CC0", "CC-BY"))
}
COMMONS_LICENCE_RE = re.compile(
    r"^(cc0(?:-1\.0)?|cc-by(?:-sa)?-\d(?:\.\d)?)(?:-(?:migrated|[a-z]{2}))?$"
)
# Commons marks a public domain file License=pd and Copyrighted=False. The manifest allowlist has
# had public-domain in it all along; only this parser could not read it, so half a dozen usable
# photos, among them US government work, were refused for no reason anyone chose (Update 11b).
# Both signals are required: a pd claim on its own, with the file still marked copyrighted, is the
# kind of unclear claim hard rule 6 says to drop.
PUBLIC_DOMAIN = "public-domain"
COMMONS_PD_RE = re.compile(r"^(pd|cc-pd-mark)(?:-.*)?$")
# iNaturalist licence codes carry no version because the site applies version 4.0 of each licence.
INAT_LICENCES = {"cc0": "cc0-1.0", "cc-by": "cc-by-4.0", "cc-by-sa": "cc-by-sa-4.0"}

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
INAT_AUTHOR_RE = re.compile(r"^\(c\)\s*(.+?),\s*(?:some|all|no) rights reserved", re.IGNORECASE)


@dataclass(frozen=True)
class Licence:
    code: str  # our tidy code, for example cc-by-sa-3.0
    label: str  # what the card shows, for example CC BY-SA 3.0
    manifest: str  # the manifest value, empty when this version has no allowlist entry yet
    raw: str  # what the source said


@dataclass(frozen=True)
class Candidate:
    feature: str
    side: str
    source: str
    title: str
    page_url: str
    image_url: str
    thumb_url: str
    author: str
    licence: Licence
    words: str  # the source's own caption or identification
    evidence: str  # what fetch_open_photo would write into label_evidence
    term: str
    place: str = ""


@dataclass(frozen=True)
class Search:
    kind: str  # commons, inat_taxon or inat_text
    term: str
    side: str


class RateLimit:
    """One request a second, no faster. The clock and sleep are arguments so a test can watch."""

    def __init__(
        self,
        min_seconds: float = MIN_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.min_seconds = min_seconds
        self.clock = clock
        self.sleeper = sleeper
        self._last: float | None = None

    def wait(self) -> None:
        if self._last is not None:
            gap = self.min_seconds - (self.clock() - self._last)
            if gap > 0:
                self.sleeper(gap)
        self._last = self.clock()


def _commons(side: str, *terms: str) -> list[Search]:
    return [Search("commons", t, side) for t in terms]


def _inat_taxa(side: str, *names: str) -> list[Search]:
    return [Search("inat_taxon", n, side) for n in names]


def _inat_text(side: str, *terms: str) -> list[Search]:
    return [Search("inat_text", t, side) for t in terms]


PRESENT = "present"
ABSENT = "absent"
LOOKALIKE = "look-alike"
TIDY = "tidy but damaged"
MESSY = "messy but healthy"

SEARCHES: dict[str, list[Search]] = {
    "artificial_bank": [
        *_commons(
            PRESENT,
            "concrete lined channel creek",
            "concrete channel wall stream",
            "riprap stream bank",
            "gabion river bank",
            "retaining wall creek",
            "sheet pile river bank",
            "revetment stream bank",
            "flood control channel concrete",
            "channelized creek concrete wall",
            "concrete bank protection river",
            # A Commons category is itself label evidence, so category searches earn their second.
            'incategory:"Riprap"',
            'incategory:"Gabions"',
            'incategory:"Concrete river channels"',
        ),
        *_commons(
            ABSENT,
            "natural stream bank vegetation",
            "eroding earth bank creek",
            "undercut bank stream",
            "riparian bank willow creek",
            "natural creek bank California",
            "river bank trees natural",
            "stream bank grass natural",
            "creek bank soil erosion",
        ),
        # Laid stone counts as a built bank (Update 09 section 4 item 3), so it belongs on the
        # present side of the lesson and out of the test. It sits here so a person sees it.
        *_commons(
            LOOKALIKE,
            "laid stone wall river bank",
            "boulder natural stream bank",
            "bedrock stream bank",
            "dry stone wall stream",
        ),
        *_inat_text(PRESENT, "riprap", "concrete channel"),
        *_inat_text(ABSENT, "creek bank willow"),
    ],
    "dug_out_channel": [
        *_commons(
            PRESENT,
            "straightened channel stream",
            "trapezoidal channel drainage",
            "channelized river straight",
            "resectioned river channel",
            "uniform drainage ditch water",
            "engineered stream channel straight",
            'incategory:"Channelized rivers"',
        ),
        *_commons(
            ABSENT,
            "meandering stream",
            "riffle pool stream",
            "gravel bar stream",
            "large woody debris stream",
            "natural meander creek",
            'incategory:"Meanders"',
        ),
        *_commons(
            LOOKALIKE,
            "straight natural stream reach",
            "canal water countryside",
            "concrete flume water",
        ),
        *_inat_text(PRESENT, "channelized creek", "drainage ditch"),
        *_inat_text(ABSENT, "riffle creek"),
    ],
    "invasive_plant": [
        # California first: every taxon search below runs inside California, then again wider
        # only if the sheet is still short.
        *_inat_taxa(
            PRESENT,
            "Arundo donax",
            "Hedera helix",
            "Hedera canariensis",
            "Delairea odorata",
            "Rubus armeniacus",
            "Vinca major",
            "Foeniculum vulgare",
            "Conium maculatum",
            "Ailanthus altissima",
            "Cortaderia jubata",
        ),
        *_inat_taxa(
            ABSENT,
            "Salix lasiolepis",
            "Alnus rhombifolia",
            "Populus fremontii",
            "Baccharis pilularis",
            "Umbellularia californica",
        ),
        # Natives that fool people: our blackberry, our bunchgrass, our climbing vine.
        *_inat_taxa(
            LOOKALIKE,
            "Rubus ursinus",
            "Muhlenbergia rigens",
            "Toxicodendron diversilobum",
        ),
        *_commons(
            PRESENT,
            "Arundo donax river",
            "Hedera helix bank",
            "Rubus armeniacus thicket",
            "Vinca major ground cover",
            "Cortaderia selloana river",
            'incategory:"Arundo donax"',
            'incategory:"Rubus armeniacus"',
        ),
        *_commons(
            ABSENT,
            "Salix lasiolepis creek",
            "Alnus rhombifolia creek",
            "riparian native vegetation California creek",
        ),
    ],
    "pipe_running": [
        *_commons(
            PRESENT,
            "storm drain outfall flowing",
            "outfall pipe discharge stream",
            "culvert outfall water",
            "sewage outfall creek",
            "stormwater outfall staining",
            "drainage pipe discharging river",
            'incategory:"Outfalls"',
        ),
        *_commons(
            ABSENT,
            "dry storm drain outfall",
            "culvert outlet dry",
            "spring seep stream bank",
            "natural spring hillside water",
            "dry culvert outlet stream",
            "outfall pipe no flow",
            "spring water emerging rock",
        ),
        *_commons(
            LOOKALIKE,
            "outfall pipe rain",
            "iron bacteria seep orange",
            "drain pipe wall creek",
            'incategory:"Culverts"',
        ),
        *_inat_text(PRESENT, "storm drain", "outfall"),
        *_inat_text(ABSENT, "seep spring"),
    ],
    WARMUP: [
        *_commons(
            TIDY,
            "urban park concrete stream channel",
            "mown grass bank stream park",
            "manicured urban creek",
            "straightened urban stream lawn",
            "concrete channel city park",
            "canalised stream town",
            "urban river promenade wall",
            "landscaped creek park lawn",
            "tidy river bank mown grass",
            'incategory:"Concrete river channels"',
        ),
        *_commons(
            MESSY,
            "woody debris natural stream",
            "riparian forest creek California",
            "natural creek fallen log",
            "wild stream vegetation bank",
        ),
        *_inat_text(TIDY, "urban creek concrete"),
        *_inat_text(MESSY, "riparian creek willow"),
    ],
}


def licence_label(code: str) -> str:
    if code.startswith("cc0"):
        return "CC0 1.0"
    parts = code.split("-")
    name = "CC BY-SA" if "sa" in parts else "CC BY"
    return f"{name} {parts[-1]}"


def licence_from_commons(raw: str, copyrighted: str = "") -> Licence | None:
    """None means the claim is not CC0, CC BY, CC BY-SA or public domain, so we drop the photo.

    copyrighted is the page's own Copyrighted field. A public domain claim is only taken when the
    page also says the file is not copyrighted.
    """
    value = SPACE_RE.sub("", (raw or "").strip().lower())
    if COMMONS_PD_RE.match(value):
        if SPACE_RE.sub("", (copyrighted or "").strip().lower()) != "false":
            return None
        manifest = PUBLIC_DOMAIN if PUBLIC_DOMAIN in content_loader.REAL_LICENSES else ""
        return Licence(PUBLIC_DOMAIN, "Public domain", manifest, value)
    match = COMMONS_LICENCE_RE.match(value)
    if match is None:
        return None
    base = "cc0-1.0" if match.group(1) == "cc0" else match.group(1)
    return Licence(base, licence_label(base), MANIFEST_LICENCES.get(base, ""), value)


def licence_from_inat(code: str | None) -> Licence | None:
    base = INAT_LICENCES.get((code or "").strip().lower())
    if base is None:
        return None
    return Licence(base, licence_label(base), MANIFEST_LICENCES[base], (code or "").lower())


def plain_text(value: str, limit: int = 400) -> str:
    """Source captions arrive as HTML. Flatten to one line so a card and a CSV cell stay sane.

    En and em dashes become plain hyphens. Hard rule 18 bans them anywhere in the repo, and a
    source we quote, a Commons category for instance, is free to use them. A hyphen keeps the
    quote readable and keeps the rule true without anyone editing a manifest cell by hand.
    """
    text = html.unescape(TAG_RE.sub(" ", value or ""))
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = SPACE_RE.sub(" ", text).strip()
    return text[: limit - 3] + "..." if len(text) > limit else text


def cal_ipc_index(root: Path = ROOT) -> dict[str, dict[str, str]]:
    """Latin name to its Cal-IPC entry, from the region packs. Plants not here have no link."""
    index: dict[str, dict[str, str]] = {}
    for rel in ("content/regions", "content/drafts/regions"):
        folder = root / rel
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.yaml")):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                continue
            for plant in data.get("invasive_plants") or []:
                name = str(plant.get("latin_name", "")).strip()
                link = str(plant.get("source", "")).strip()
                if name and "cal-ipc.org" in link:
                    index.setdefault(
                        name.lower(),
                        {
                            "latin_name": name,
                            "common_name": str(plant.get("common_name", "")),
                            "rating": str(plant.get("cal_ipc_rating", "")),
                            "link": link,
                        },
                    )
    return index


def get_json(
    client: httpx.Client, url: str, params: dict[str, Any], limiter: RateLimit
) -> dict[str, Any]:
    limiter.wait()
    response = client.get(url, params=params, timeout=30.0)
    response.raise_for_status()
    body: dict[str, Any] = response.json()
    return body


def commons_candidates(payload: dict[str, Any], search: Search, feature: str) -> list[Candidate]:
    out: list[Candidate] = []
    pages = (payload.get("query") or {}).get("pages") or []
    for page in pages:
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        meta = info.get("extmetadata") or {}

        def field(name: str, meta: dict[str, Any] = meta, limit: int = 400) -> str:
            return plain_text(str((meta.get(name) or {}).get("value", "")), limit)

        licence = licence_from_commons(
            str((meta.get("License") or {}).get("value", "")),
            str((meta.get("Copyrighted") or {}).get("value", "")),
        )
        if licence is None:
            continue
        title = str(page.get("title", ""))
        if Path(title).suffix.lower() not in PHOTO_SUFFIXES:
            continue
        author = field("Artist", limit=160) or field("Attribution", limit=160)
        if not author:
            # No named author. Under CC BY and CC BY-SA we could not credit anyone, so drop it.
            if licence.code not in {"cc0-1.0", PUBLIC_DOMAIN}:
                continue
            uploader = str(info.get("user", "")).strip()
            if not uploader:
                continue
            author = f"Wikimedia Commons user {uploader}"
        page_url = str(info.get("descriptionurl") or "")
        image_url = str(info.get("url") or "")
        if not page_url or not image_url:
            continue
        words = field("ImageDescription") or field("ObjectName") or title
        categories = field("Categories", limit=300).replace("|", ", ")
        evidence = f"Wikimedia Commons file page {page_url}. The page says: {words}"
        if categories:
            evidence = f"{evidence} Commons categories: {categories}."
        out.append(
            Candidate(
                feature=feature,
                side=search.side,
                source="wikimedia-commons",
                title=title,
                page_url=page_url,
                image_url=image_url,
                thumb_url=str(info.get("thumburl") or image_url),
                author=author,
                licence=licence,
                words=words,
                evidence=plain_text(evidence, 700),
                term=search.term,
            )
        )
    return out


def inat_author(photo: dict[str, Any], user: dict[str, Any]) -> str:
    text = plain_text(str(photo.get("attribution", "")), 200)
    match = INAT_AUTHOR_RE.match(text)
    if match:
        return match.group(1).strip()
    return str(user.get("name") or user.get("login") or "").strip()


def inat_candidates(
    payload: dict[str, Any],
    search: Search,
    feature: str,
    cal_ipc: dict[str, dict[str, str]],
    scope: str = "California",
) -> list[Candidate]:
    out: list[Candidate] = []
    for obs in payload.get("results") or []:
        # Research grade only. A casual or needs-id record is somebody's guess, not evidence.
        if str(obs.get("quality_grade", "")) != "research":
            continue
        taxon = obs.get("taxon") or {}
        latin = str(taxon.get("name", "")).strip()
        common = str(taxon.get("preferred_common_name", "")).strip()
        user = obs.get("user") or {}
        place = plain_text(str(obs.get("place_guess", "")), 120)
        observed = str(obs.get("observed_on") or "")
        agreements = obs.get("num_identification_agreements")
        uri = str(obs.get("uri") or "")
        for photo in obs.get("photos") or []:
            licence = licence_from_inat(photo.get("license_code"))
            if licence is None:
                continue
            author = inat_author(photo, user)
            if not author:
                continue
            url = str(photo.get("url") or "")
            if "square." not in url:
                continue
            named = f"{latin} ({common})" if common else latin
            words = f"Identified as {named}" + (f", observed at {place}" if place else "")
            evidence = (
                f"iNaturalist observation {uri}, research grade, community identification "
                f"{named}, {agreements or 0} agreeing identifications, "
                f"observed {observed or 'on an unrecorded date'}"
            )
            if place:
                evidence = f"{evidence} at {place}"
            listed = cal_ipc.get(latin.lower())
            if listed:
                evidence = (
                    f"{evidence}. On the Cal-IPC Inventory, rating {listed['rating']}: "
                    f"{listed['link']}"
                )
            out.append(
                Candidate(
                    feature=feature,
                    side=search.side,
                    source="inaturalist",
                    title=named or uri,
                    page_url=uri,
                    image_url=url.replace("square.", "original."),
                    thumb_url=url.replace("square.", "medium."),
                    author=author,
                    licence=licence,
                    words=words,
                    evidence=plain_text(evidence + ".", 700),
                    term=f"{search.term} ({scope})",
                    place=place,
                )
            )
            break  # One photo per observation keeps the sheet varied.
    return out


def run_search(
    client: httpx.Client,
    limiter: RateLimit,
    search: Search,
    feature: str,
    cal_ipc: dict[str, dict[str, str]],
    per_term: int,
    california_only: bool = True,
) -> list[Candidate]:
    if search.kind == "commons":
        payload = get_json(
            client,
            COMMONS_API,
            {
                "action": "query",
                "generator": "search",
                # filemime keeps the search on photographs, away from maps, plans and scans.
                "gsrsearch": f"{search.term} filemime:image/jpeg",
                "gsrnamespace": "6",
                "gsrlimit": str(max(per_term * 3, 20)),
                "prop": "imageinfo",
                "iiprop": "url|user|extmetadata",
                "iiurlwidth": "320",
                "format": "json",
                "formatversion": "2",
            },
            limiter,
        )
        return commons_candidates(payload, search, feature)[:per_term]
    params: dict[str, Any] = {
        "quality_grade": "research",
        "photo_license": "cc0,cc-by,cc-by-sa",
        "photos": "true",
        "per_page": str(max(per_term * 3, 20)),
        "order_by": "votes",
    }
    if search.kind == "inat_taxon":
        params["taxon_name"] = search.term
    else:
        params["q"] = search.term
    scope = "anywhere"
    if california_only:
        params["place_id"] = str(CALIFORNIA_PLACE_ID)
        scope = "California"
    payload = get_json(client, INAT_API, params, limiter)
    return inat_candidates(payload, search, feature, cal_ipc, scope)[:per_term]


def trim(candidates: list[Candidate], per_sheet: int) -> list[Candidate]:
    """Keep the sheet readable without letting one search term crowd out the rest."""
    if len(candidates) <= per_sheet:
        return candidates
    by_term: dict[str, list[Candidate]] = {}
    for c in candidates:
        by_term.setdefault(f"{c.side}|{c.term}", []).append(c)
    kept: list[Candidate] = []
    depth = 0
    while len(kept) < per_sheet:
        row = [group[depth] for group in by_term.values() if len(group) > depth]
        if not row:
            break
        kept.extend(row[: per_sheet - len(kept)])
        depth += 1
    order = {id(c): n for n, c in enumerate(candidates)}
    return sorted(kept, key=lambda c: order[id(c)])


def collect(
    feature: str,
    client: httpx.Client,
    limiter: RateLimit,
    per_term: int = PER_TERM,
    per_sheet: int = PER_SHEET,
    target: int = TARGET,
    root: Path = ROOT,
) -> tuple[list[Candidate], list[str]]:
    cal_ipc = cal_ipc_index(root)
    searches = SEARCHES[feature]
    found: list[Candidate] = []
    seen: set[str] = set()
    problems: list[str] = []

    def take(new: list[Candidate]) -> None:
        for c in new:
            if c.page_url and c.page_url not in seen:
                seen.add(c.page_url)
                found.append(c)

    for search in searches:
        try:
            take(run_search(client, limiter, search, feature, cal_ipc, per_term))
        except (httpx.HTTPError, ValueError) as e:
            problems.append(f"{search.kind} search {search.term!r} failed: {e}")
    # California first, then wider, and only when the sheet is still short.
    if len(found) < target:
        for search in searches:
            if search.kind not in {"inat_taxon", "inat_text"}:
                continue
            try:
                take(
                    run_search(
                        client, limiter, search, feature, cal_ipc, per_term, california_only=False
                    )
                )
            except (httpx.HTTPError, ValueError) as e:
                problems.append(f"{search.kind} wider search {search.term!r} failed: {e}")
    return trim(found, per_sheet), problems


# What a finished pick list holds, per sheet. 16 test items is 4 per feature; a lesson is two
# contrast pairs (4 photos) plus one practice photo; the warm-up is one pair.
PICK_TARGETS = {
    "warmup": {"warmup": 2},
    # spare has no target: it is the stand-in used when a fetch fails on the day (Update 11b
    # step 3), so any number of them is fine and none of them is missing.
    "_feature": {"test": 4, "lesson": 4, "practice": 1, "spare": 0},
}


def pick_targets(feature: str) -> dict[str, int]:
    return PICK_TARGETS.get(feature, PICK_TARGETS["_feature"])


def pick_control(feature: str, c: Candidate) -> str:
    """The checkbox, the role and the optional scene id for one candidate.

    Only a candidate fetch can actually record gets one, so a person cannot pick something the
    tool will refuse afterwards. The guard lives here rather than in the caller, so a second
    caller cannot forget it.
    """
    if not c.licence.manifest:
        return ""
    e = html.escape
    roles = list(pick_targets(feature))
    options = "".join(f'<option value="{e(r)}">{e(r)}</option>' for r in roles)
    return (
        '<div class="pick">'
        f'<label><input type="checkbox" class="take" data-url="{e(c.page_url)}" '
        f'data-side="{e(c.side)}"> pick this</label>'
        f'<select class="role">{options}</select>'
        '<input class="scene" size="14" placeholder="scene id, optional">'
        "</div>"
    )


def pick_script(feature: str) -> str:
    """Builds the picks file in the browser. No server, no upload, nothing leaves the machine."""
    targets = json.dumps(pick_targets(feature))
    return f"""<script>
(function () {{
  var TARGETS = {targets};
  var FEATURE = {json.dumps(feature)};
  function rows() {{
    var out = [];
    document.querySelectorAll('.take').forEach(function (box) {{
      if (!box.checked) return;
      var pick = box.closest('.pick');
      out.push({{
        url: box.dataset.url,
        feature: FEATURE,
        role: pick.querySelector('.role').value,
        side: box.dataset.side,
        scene: pick.querySelector('.scene').value.trim()
      }});
    }});
    return out;
  }}
  function csv() {{
    var head = 'url,feature,role,side,scene,notes';
    var lines = rows().map(function (r) {{
      return [r.url, r.feature, r.role, r.side, r.scene, ''].map(function (v) {{
        return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
      }}).join(',');
    }});
    return [head].concat(lines).join('\n') + '\n';
  }}
  function tally() {{
    var got = {{}};
    rows().forEach(function (r) {{ got[r.role] = (got[r.role] || 0) + 1; }});
    var bits = Object.keys(TARGETS).map(function (role) {{
      var n = got[role] || 0, want = TARGETS[role];
      if (!want) return '<span>' + role + ' ' + n + '</span>';
      var cls = n === want ? 'full' : (n > want ? 'over' : '');
      return '<span class="' + cls + '">' + role + ' ' + n + ' of ' + want + '</span>';
    }});
    document.getElementById('tally').innerHTML = bits.join(' &middot; ');
  }}
  document.addEventListener('change', tally);
  document.addEventListener('input', tally);
  document.getElementById('save').addEventListener('click', function () {{
    var blob = new Blob([csv()], {{ type: 'text/csv' }});
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'picks-' + FEATURE + '.csv';
    a.click();
    URL.revokeObjectURL(a.href);
  }});
  document.getElementById('copy').addEventListener('click', function () {{
    navigator.clipboard.writeText(csv()).then(function () {{
      document.getElementById('copy').textContent = 'Copied';
    }});
  }});
  tally();
}})();
</script>"""


def sheet_html(feature: str, candidates: list[Candidate], ran_at: datetime) -> str:
    e = html.escape
    sides: dict[str, list[Candidate]] = {}
    for c in candidates:
        sides.setdefault(c.side, []).append(c)
    # A photo we can record today comes first, so a person does not scroll past ones fetch refuses.
    for items in sides.values():
        items.sort(key=lambda c: not c.licence.manifest)
    counts = ", ".join(f"{side} {len(items)}" for side, items in sides.items())
    ready_count = sum(1 for c in candidates if c.licence.manifest)
    parts: list[str] = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        f"<title>Second Look candidates: {e(feature)}</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;margin:1rem;max-width:80rem;color:#111}",
        ".card{border:1px solid #bbb;border-radius:8px;padding:.6rem;margin:.4rem 0;"
        "display:flex;gap:.8rem}",
        ".card img{width:320px;height:auto;background:#eee}",
        ".meta{font-size:.9rem;line-height:1.4}",
        "code{background:#f2f2f2;padding:.15rem .3rem;display:inline-block;word-break:break-all}",
        ".warn{color:#8a1c1c}",
        "#bar{position:sticky;top:0;background:#fff;border-bottom:2px solid #333;padding:.6rem 0;"
        "margin-bottom:.6rem;font-size:1rem}",
        "#bar button{font-size:1rem;padding:.4rem .9rem;margin-left:.6rem}",
        ".pick{display:flex;gap:.6rem;align-items:center;margin-top:.4rem;flex-wrap:wrap}",
        ".pick label{font-weight:700}",
        ".full{color:#1f7a4d;font-weight:700}",
        ".over{color:#8a1c1c;font-weight:700}",
        "h2{margin-top:1.6rem;border-top:2px solid #333;padding-top:.6rem}",
        "</style></head><body>",
        f"<h1>Candidates for {e(feature)}</h1>",
        f"<p>{len(candidates)} candidates ({e(counts)}), "
        f"searched {e(ran_at.strftime('%Y-%m-%d %H:%M UTC'))}.</p>",
        f"<p>{ready_count} of them are ready to fetch today. The rest are under a licence "
        "version the manifest has no entry for, so fetch refuses them until someone widens "
        "the allowlist.</p>",
        "<p>Local sheet. Nothing here is in the repo and nothing here is deployed. Thumbnails load "
        "from the source, so this page needs the internet. Every photo below claims CC0, CC BY or "
        "CC BY-SA, and every iNaturalist record below is research grade. You pick, you label. "
        "Check each photo you pick for faces, house numbers and plates before you fetch it.</p>",
        '<div id="bar"><span id="tally">Nothing picked yet.</span>'
        '<button id="save" type="button">Download the picks file</button>'
        '<button id="copy" type="button">Copy as CSV</button></div>',
    ]
    for side, items in sides.items():
        parts.append(f"<h2>{e(side)} ({len(items)})</h2>")
        for c in items:
            ready = (
                f"ready to fetch as {e(c.licence.manifest)}"
                if c.licence.manifest
                else '<span class="warn">licence version has no manifest entry yet, '
                "so fetch will refuse it</span>"
            )
            command = (
                f"uv run python scripts/fetch_open_photo.py {c.page_url} "
                f"--feature {feature} --role test"
            )
            parts.extend(
                [
                    '<div class="card">',
                    f'<a href="{e(c.page_url)}" target="_blank" rel="noreferrer">'
                    f'<img src="{e(c.thumb_url)}" alt="" loading="lazy"></a>',
                    '<div class="meta">',
                    f'<p><a href="{e(c.page_url)}" target="_blank" rel="noreferrer">'
                    f"{e(c.title)}</a></p>",
                    f"<p>Source: {e(c.source)}. Search term: {e(c.term)}.</p>",
                    f"<p>Author: {e(c.author)}</p>",
                    f"<p>Licence: {e(c.licence.label)} ({ready})</p>",
                    f"<p>Source says: {e(c.words)}</p>",
                    f"<p>Label evidence it would record: {e(c.evidence)}</p>",
                    f"<p><code>{e(command)}</code></p>",
                    pick_control(feature, c),
                    "</div></div>",
                ]
            )
    parts.append(pick_script(feature))
    parts.append("</body></html>")
    return "\n".join(parts)


def write_sheet(feature: str, candidates: list[Candidate], root: Path = ROOT) -> Path:
    out = root / "photos" / "candidates" / f"{feature}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(sheet_html(feature, candidates, datetime.now(UTC)), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("feature", choices=[*SHEETS, "all"], help="feature id, or all of them")
    parser.add_argument("--per-term", type=int, default=PER_TERM, help="keep this many per term")
    parser.add_argument("--per-sheet", type=int, default=PER_SHEET, help="cap on one sheet")
    parser.add_argument("--target", type=int, default=TARGET, help="search wider below this many")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    features = list(SHEETS) if args.feature == "all" else [args.feature]
    limiter = RateLimit()
    failed = 0
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for feature in features:
            candidates, problems = collect(
                feature, client, limiter, args.per_term, args.per_sheet, args.target, args.root
            )
            path = write_sheet(feature, candidates, args.root)
            sides: dict[str, int] = {}
            for c in candidates:
                sides[c.side] = sides.get(c.side, 0) + 1
            counts = ", ".join(f"{k} {v}" for k, v in sides.items())
            short = " (short of the target)" if len(candidates) < args.target else ""
            print(
                f"find-open-photos: {feature}, {len(candidates)} candidates ({counts}){short}, "
                f"sheet at {path.relative_to(args.root)}"
            )
            for problem in problems:
                failed += 1
                print(f"  search problem: {problem}")
    print("find-open-photos: nothing downloaded, nothing labelled. A person picks next.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
