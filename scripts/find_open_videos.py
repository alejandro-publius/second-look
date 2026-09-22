"""Search Wikimedia Commons and YouTube for openly licensed creek footage to choose from.

Run: uv run python scripts/find_open_videos.py
     uv run python scripts/find_open_videos.py --source commons

Writes videos/candidates.json, one row per candidate, and videos/candidates.html, a contact sheet
for a person to read: the title, the link to the source page, the author, the exact licence words
the source showed, the length, the height, the country if the source names one, the query that
found it, and a few words of the description. Commons is read through the MediaWiki API and
YouTube through yt-dlp metadata only, so no video bytes are fetched and nothing is cached.

Filters, all hard: CC BY of any version, CC0 or public domain only, so CC BY-SA, NC, ND and any
unstated licence are dropped; 1 to 20 minutes; height 720 or better; the title or the description
has to say creek, stream, brook, burn, urban river, river walk, or the same thing in another
language we can read. One request a second to each site, with a user agent that names this repo,
because both are other people's machines.

This script never labels anything and never opens a video. A person picks, a person labels.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yt_dlp

ROOT = Path(__file__).resolve().parents[1]

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# YouTube's own Creative Commons filter. The sp token is the one the site puts in the address bar
# when a person ticks Creative Commons under Filters, so the cheap pass already skips most of the
# all rights reserved videos. The licence of every kept video is checked again below.
YOUTUBE_CC_SEARCH = "https://www.youtube.com/results?search_query={terms}&sp=EgIwAQ%3D%3D"
PROJECT_URL = "https://github.com/alejandro-publius/second-look"
CONTACT = os.environ.get(
    "SECOND_LOOK_CONTACT", "82622360+alejandro-publius@users.noreply.github.com"
)
USER_AGENT = f"SecondLookVideoSearch/0.1 (Second Look, {PROJECT_URL}; contact {CONTACT})"
MIN_SECONDS = 1.0

# A clip has to be long enough to hold a bank and short enough for a person to watch.
MIN_DURATION = 60
MAX_DURATION = 1200
MIN_HEIGHT = 720
TARGET = 40
PER_QUERY = 2  # candidates kept per query per source
YOUTUBE_LOOKUPS = 3  # metadata lookups per query, the only slow step
COMMONS_ROWS = 40  # search results asked for per Commons query
YOUTUBE_ROWS = 12  # search results asked for per YouTube query
VIDEO_SUFFIXES = {".webm", ".ogv", ".ogg", ".mp4", ".mpg", ".mpeg", ".mov"}

# Licences we may use: CC BY of any version, CC0, public domain. Anything with SA, NC or ND in it,
# and anything the source leaves unstated, is dropped rather than guessed at (hard rule 6).
COMMONS_LICENCE_RE = re.compile(r"^(cc0(?:-1\.0)?|cc-by-\d(?:\.\d)?)(?:-(?:migrated|[a-z]{2}))?$")
# Commons marks a public domain file License=pd and Copyrighted=False. Both signals are required:
# a pd claim with the file still marked copyrighted is the kind of unclear claim we drop.
PUBLIC_DOMAIN = "public-domain"
COMMONS_PD_RE = re.compile(r"^(pd|cc-pd-mark)(?:-.*)?$")
# YouTube offers one open licence and writes it out in these words. Standard YouTube License, and
# a missing licence line, both mean no.
YOUTUBE_CC = "creative commons attribution"
CLOSED_WORDS = ("sharealike", "share alike", "noncommercial", "non-commercial", "noderiv", "-sa-")

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
# Emoji and the other picture characters, dropped from anything we quote, because hard rule 18
# keeps them out of every file in the repo and a source title is free to use them.
EMOJI_RE = re.compile(
    "[←-⇿⌀-⏿☀-➿⬀-⯿️‍"
    "\U0001f000-\U0001faff]"
)

# Words that say the water is a creek rather than a lake, a canal or a harbour. A title or a
# description has to carry one of them, in any of these languages, or the video is dropped.
CREEK_WORDS = (
    "creek",
    "stream",
    "brook",
    "burn",
    "beck",
    "rivulet",
    "river walk",
    "riverwalk",
    "urban river",
    "river restoration",
    "arroyo",
    "quebrada",
    "riachuelo",
    "ruisseau",
    "riviere urbaine",
    "bachlauf",
    "stadtbach",
    "dorfbach",
    "wildbach",
    "renaturierung",
    "torrente",
    "ruscello",
    "fosso",
    "corrego",
    "riacho",
    "ribeiro",
    "beek",
    "stadsbeek",
    "back",
    "baeck",
    "elv",
    "puro",
    "oja",
    "strumien",
    "potok",
    "patak",
    "poток",
    "ruchei",
    "rucheek",
    "arroio",
    "nullah",
    "kali",
)
# The same words where the language writes no spaces, so a word boundary cannot be looked for.
CREEK_SIGNS = ("小川", "小溪", "溪流", "渓流", "河川", "하천", "개울", "실개천")
# Cyrillic reads fine with word boundaries, so these sit with the boundary words.
CREEK_WORDS_CYRILLIC = ("ручей", "ручеек", "речка", "ручья", "струмок")

# Words that name a country, and words for a region or a city whose country is not in doubt. A
# candidate gets a country only when one of these shows up in what the source wrote, so an empty
# country means the source did not say, not that we made a guess.
COUNTRY_WORDS: dict[str, tuple[str, ...]] = {
    "United States": (
        "united states",
        "usa",
        "u.s.a",
        "california",
        "oregon",
        "texas",
        "colorado",
        "ohio",
        "michigan",
        "minnesota",
        "wisconsin",
        "virginia",
        "maryland",
        "north carolina",
        "pennsylvania",
        "new york",
        "new jersey",
        "florida",
        "arizona",
        "utah",
        "idaho",
        "montana",
        "alaska",
        "hawaii",
        "seattle",
        "portland oregon",
        "chicago",
        "san francisco",
        "los angeles",
        "washington dc",
    ),
    "Canada": (
        "canada",
        "british columbia",
        "ontario",
        "alberta",
        "quebec",
        "nova scotia",
        "toronto",
        "vancouver",
        "montreal",
        "calgary",
        "ottawa",
        "edmonton",
    ),
    "Mexico": ("mexico", "guadalajara", "monterrey"),
    "Brazil": ("brazil", "brasil", "sao paulo", "rio de janeiro", "curitiba", "belo horizonte"),
    "Argentina": ("argentina", "buenos aires"),
    "Chile": ("chile", "valparaiso"),
    "Colombia": ("colombia", "bogota", "medellin"),
    "Peru": ("peru",),
    "Ecuador": ("ecuador", "quito"),
    "Costa Rica": ("costa rica",),
    "United Kingdom": (
        "united kingdom",
        "england",
        "scotland",
        "wales",
        "northern ireland",
        "london",
        "manchester",
        "sheffield",
        "glasgow",
        "edinburgh",
        "yorkshire",
        "cornwall",
        "devon",
    ),
    "Ireland": ("ireland", "dublin", "cork city"),
    "France": ("france", "paris", "lyon", "marseille", "grenoble", "nantes"),
    "Germany": (
        "germany",
        "deutschland",
        "bavaria",
        "bayern",
        "berlin",
        "hamburg",
        "munich",
        "muenchen",
        "cologne",
        "koeln",
        "freiburg",
        "leipzig",
        "stuttgart",
    ),
    "Austria": ("austria", "oesterreich", "vienna", "wien", "graz"),
    "Switzerland": ("switzerland", "schweiz", "suisse", "zurich", "zuerich", "geneva", "bern"),
    "Netherlands": ("netherlands", "nederland", "holland", "amsterdam", "rotterdam", "utrecht"),
    "Belgium": ("belgium", "brussels", "antwerp", "ghent", "leuven"),
    "Spain": ("spain", "espana", "catalonia", "barcelona", "madrid", "valencia", "bilbao"),
    "Portugal": ("portugal", "lisbon", "lisboa", "porto"),
    "Italy": ("italy", "italia", "rome", "roma", "milan", "milano", "turin", "florence", "naples"),
    "Greece": ("greece", "athens", "thessaloniki"),
    "Croatia": ("croatia", "zagreb"),
    "Slovenia": ("slovenia", "ljubljana"),
    "Serbia": ("serbia", "belgrade"),
    "Romania": ("romania", "bucharest", "cluj"),
    "Bulgaria": ("bulgaria", "sofia"),
    "Hungary": ("hungary", "budapest"),
    "Czechia": ("czechia", "czech republic", "prague", "praha", "brno"),
    "Slovakia": ("slovakia", "bratislava"),
    "Poland": ("poland", "polska", "warsaw", "warszawa", "krakow", "wroclaw", "gdansk"),
    "Lithuania": ("lithuania", "vilnius"),
    "Latvia": ("latvia", "riga"),
    "Estonia": ("estonia", "tallinn"),
    "Finland": ("finland", "suomi", "helsinki", "tampere"),
    "Sweden": ("sweden", "sverige", "stockholm", "gothenburg", "malmo"),
    "Norway": ("norway", "norge", "oslo", "bergen", "trondheim"),
    "Denmark": ("denmark", "danmark", "copenhagen", "aarhus"),
    "Iceland": ("iceland", "reykjavik"),
    "Ukraine": ("ukraine", "kyiv", "lviv"),
    "Russia": ("russia", "moscow", "saint petersburg", "россия", "москва"),
    "Turkey": ("turkey", "turkiye", "istanbul", "ankara", "eskisehir"),
    "Israel": ("israel", "tel aviv", "jerusalem"),
    "Japan": ("japan", "tokyo", "osaka", "kyoto", "日本", "東京"),
    "South Korea": ("south korea", "seoul", "busan", "한국", "서울"),
    "China": ("china", "shanghai", "beijing", "shenzhen", "chengdu"),
    "Taiwan": ("taiwan", "taipei"),
    "Hong Kong": ("hong kong",),
    "Singapore": ("singapore",),
    "Malaysia": ("malaysia", "kuala lumpur"),
    "Indonesia": ("indonesia", "jakarta", "bandung"),
    "Philippines": ("philippines", "manila", "cebu"),
    "Vietnam": ("vietnam", "hanoi", "ho chi minh"),
    "Thailand": ("thailand", "bangkok", "chiang mai"),
    "India": (
        "india",
        "mumbai",
        "bengaluru",
        "bangalore",
        "chennai",
        "kolkata",
        "hyderabad",
        "pune",
        "new delhi",
    ),
    "Pakistan": ("pakistan", "karachi", "lahore"),
    "Nepal": ("nepal", "kathmandu"),
    "Sri Lanka": ("sri lanka", "colombo"),
    "Bangladesh": ("bangladesh", "dhaka"),
    "Australia": (
        "australia",
        "sydney",
        "melbourne",
        "brisbane",
        "adelaide",
        "queensland",
        "new south wales",
        "tasmania",
    ),
    "New Zealand": ("new zealand", "auckland", "christchurch", "dunedin"),
    "South Africa": ("south africa", "cape town", "johannesburg", "durban"),
    "Kenya": ("kenya", "nairobi"),
    "Tanzania": ("tanzania", "dar es salaam"),
    "Uganda": ("uganda", "kampala"),
    "Nigeria": ("nigeria", "lagos", "abuja"),
    "Ghana": ("ghana", "accra"),
    "Ethiopia": ("ethiopia", "addis ababa"),
    "Morocco": ("morocco", "casablanca", "rabat"),
    "Egypt": ("egypt", "cairo"),
}
# Longest first, so northern ireland is not read as ireland and new york is not read as york.
COUNTRY_LOOKUP: tuple[tuple[str, str], ...] = tuple(
    sorted(
        ((word, name) for name, words in COUNTRY_WORDS.items() for word in words),
        key=lambda pair: -len(pair[0]),
    )
)


@dataclass(frozen=True)
class Licence:
    code: str  # our tidy code, for example cc-by-4.0
    label: str  # what the card shows, for example CC BY 4.0
    raw: str  # the exact licence words the source showed
    credit: bool  # true when the licence asks us to name the author


@dataclass(frozen=True)
class Candidate:
    id: str
    source: str
    title: str
    author: str
    licence: Licence
    duration_s: int
    height: int
    country: str
    url: str
    query: str
    words: str  # the source's own description, cut short
    match: str  # the creek word that kept it

    def row(self) -> dict[str, Any]:
        """The one shape videos/candidates.json holds. The licence is the source's own words."""
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "author": self.author,
            "licence": self.licence.raw,
            "duration_s": self.duration_s,
            "height": self.height,
            "country_if_stated": self.country,
            "url": self.url,
            "query": self.query,
            "description_excerpt": self.words,
        }


@dataclass(frozen=True)
class Search:
    source: str  # commons or youtube
    term: str


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


def _commons(*terms: str) -> list[Search]:
    return [Search("commons", t) for t in terms]


def _youtube(*terms: str) -> list[Search]:
    return [Search("youtube", t) for t in terms]


def _both(*terms: str) -> list[Search]:
    return _commons(*terms) + _youtube(*terms)


# Many queries, in many languages, across the four things we want to see: concrete channels,
# restored creeks, plain natural streams, and pipes running into water. The query that found a
# candidate is written next to it, so a thin query can be dropped next time.
SEARCHES: list[Search] = [
    *_both(
        "urban creek walk",
        "creek restoration",
        "stream restoration project",
        "concrete channel creek",
        "storm drain outfall stream",
        "culvert creek outlet",
        "daylighting buried creek",
        "river walk city centre",
        "forest stream walk",
        "brook countryside walk",
        "creek cleanup volunteers",
        "urban river renaturation",
    ),
    # Other languages. The keyword gate reads the same words back out of the title.
    *_both(
        "arroyo urbano",
        "quebrada urbana",
        "ruisseau urbain",
        "stadtbach",
        "bachlauf renaturierung",
        "torrente urbano",
        "corrego urbano",
        "stadsbeek",
        "strumien miejski",
        "mestsky potok",
        "городской ручей",
        "小川 散歩",
        "도시 하천 산책",
    ),
    # Commons keeps its video files in categories, and a category is itself a statement about
    # what is in the shot, so these earn their second.
    *_commons(
        'incategory:"Videos of rivers"',
        'incategory:"Videos of streams"',
        'incategory:"Videos of brooks"',
        'incategory:"Videos of creeks in the United States"',
        "creek",
        "stream bank",
        "riverwalk",
        "river restoration",
    ),
    # Phrasings that suit spoken titles, so they only go to YouTube.
    *_youtube(
        "creek walk 4k",
        "urban stream india nullah",
        "creek walk australia",
        "stream walk new zealand",
        "river walk japan small stream",
        "creek walk south africa",
        "restored urban stream korea",
        "outfall pipe into river",
        "gabion stream bank repair",
    ),
]


def plain_text(value: str, limit: int = 400) -> str:
    """Source words arrive as HTML. Flatten to one line so a card and a JSON cell stay sane.

    En and em dashes become plain hyphens and picture characters are dropped. Hard rule 18 bans
    both anywhere in the repo, and a source we quote is free to use them.
    """
    text = html.unescape(TAG_RE.sub(" ", value or ""))
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    text = EMOJI_RE.sub("", text)
    text = SPACE_RE.sub(" ", text).strip()
    return text[: limit - 3] + "..." if len(text) > limit else text


def licence_label(code: str) -> str:
    if code.startswith("cc0"):
        return "CC0 1.0"
    return f"CC BY {code.split('-')[-1]}"


def licence_from_commons(raw: str, short_name: str = "", copyrighted: str = "") -> Licence | None:
    """None means the claim is not CC BY, CC0 or public domain, so we drop the video.

    raw is the page's License field, short_name is the words the page prints, copyrighted is the
    page's own Copyrighted field. A public domain claim is only taken when the page also says the
    file is not copyrighted.
    """
    value = SPACE_RE.sub("", (raw or "").strip().lower())
    shown = plain_text(short_name, 80) or value
    if any(word in value for word in CLOSED_WORDS) or "-sa-" in f"-{value}-":
        return None
    if COMMONS_PD_RE.match(value):
        if SPACE_RE.sub("", (copyrighted or "").strip().lower()) != "false":
            return None
        return Licence(PUBLIC_DOMAIN, "Public domain", shown, False)
    match = COMMONS_LICENCE_RE.match(value)
    if match is None:
        return None
    base = "cc0-1.0" if match.group(1) == "cc0" else match.group(1)
    return Licence(base, licence_label(base), shown, base.startswith("cc-by"))


def licence_from_youtube(raw: str | None) -> Licence | None:
    """YouTube's open licence is CC BY 3.0 and the page says so in a sentence. Nothing else."""
    value = plain_text(raw or "", 120)
    low = value.lower()
    if YOUTUBE_CC not in low or any(word in low for word in CLOSED_WORDS):
        return None
    return Licence("cc-by-3.0", "CC BY 3.0", value, True)


def creek_word(*parts: str) -> str:
    """The creek word a source wrote, or an empty string when it wrote none of them."""
    text = " ".join(parts).lower()
    for sign in CREEK_SIGNS:
        if sign in text:
            return sign
    for word in CREEK_WORDS + CREEK_WORDS_CYRILLIC:
        if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text):
            return word
    return ""


def country_word(*parts: str) -> str:
    """The country a source named, or an empty string. Never a guess from the language or the IP."""
    text = " ".join(parts).lower()
    for word, name in COUNTRY_LOOKUP:
        if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text):
            return name
    return ""


def minutes(seconds: int) -> str:
    return f"{seconds // 60} min {seconds % 60:02d} s"


def in_range(duration: float, height: int) -> bool:
    return MIN_DURATION <= duration <= MAX_DURATION and height >= MIN_HEIGHT


def get_json(
    client: httpx.Client, url: str, params: dict[str, Any], limiter: RateLimit
) -> dict[str, Any]:
    limiter.wait()
    response = client.get(url, params=params, timeout=30.0)
    response.raise_for_status()
    body: dict[str, Any] = response.json()
    return body


def commons_candidates(payload: dict[str, Any], term: str) -> list[Candidate]:
    out: list[Candidate] = []
    for page in (payload.get("query") or {}).get("pages") or []:
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        meta = info.get("extmetadata") or {}

        def field(name: str, meta: dict[str, Any] = meta, limit: int = 400) -> str:
            return plain_text(str((meta.get(name) or {}).get("value", "")), limit)

        title = plain_text(str(page.get("title", "")), 200)
        if Path(title).suffix.lower() not in VIDEO_SUFFIXES:
            continue
        if str(info.get("mediatype", "")).upper() != "VIDEO":
            continue
        duration = float(info.get("duration") or 0.0)
        height = int(info.get("height") or 0)
        if not in_range(duration, height):
            continue
        licence = licence_from_commons(
            str((meta.get("License") or {}).get("value", "")),
            str((meta.get("LicenseShortName") or {}).get("value", "")),
            str((meta.get("Copyrighted") or {}).get("value", "")),
        )
        if licence is None:
            continue
        words = field("ImageDescription", limit=300) or field("ObjectName", limit=300)
        categories = field("Categories", limit=300).replace("|", ", ")
        match = creek_word(title, words, categories)
        if not match:
            continue
        author = field("Artist", limit=160) or field("Attribution", limit=160)
        if not author:
            # No named author. Under CC BY we could not credit anyone, so drop it.
            if licence.credit:
                continue
            uploader = str(info.get("user", "")).strip()
            if not uploader:
                continue
            author = f"Wikimedia Commons user {plain_text(uploader, 80)}"
        page_url = str(info.get("descriptionurl") or "")
        if not page_url:
            continue
        out.append(
            Candidate(
                id=f"commons-{page.get('pageid')}",
                source="wikimedia-commons",
                title=title.removeprefix("File:"),
                author=author,
                licence=licence,
                duration_s=int(round(duration)),
                height=height,
                country=country_word(title, words, categories),
                url=page_url,
                query=term,
                words=words or title,
                match=match,
            )
        )
    return out


def commons_search(
    client: httpx.Client, limiter: RateLimit, term: str, rows: int
) -> dict[str, Any]:
    """One File: namespace search, video files only."""
    return get_json(
        client,
        COMMONS_API,
        {
            "action": "query",
            "generator": "search",
            # filetype keeps the search on moving pictures, away from stills, maps and sound.
            "gsrsearch": f"{term} filetype:video",
            "gsrnamespace": "6",
            "gsrlimit": str(rows),
            "prop": "imageinfo",
            # size is what carries the height and the duration.
            "iiprop": "url|user|size|mime|mediatype|extmetadata",
            "format": "json",
            "formatversion": "2",
        },
        limiter,
    )


def youtube_options(**extra: Any) -> dict[str, Any]:
    """Metadata only. skip_download and download=False together mean no video bytes ever."""
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": False,
        "ignoreerrors": True,
        "http_headers": {"User-Agent": USER_AGENT},
    }
    options.update(extra)
    return options


def youtube_search(limiter: RateLimit, term: str, rows: int) -> list[dict[str, Any]]:
    """The cheap pass: titles and lengths from a flat search, no per video request yet."""
    urls = [
        YOUTUBE_CC_SEARCH.format(terms=urllib.parse.quote_plus(term)),
        f"ytsearch{rows}:{term}",
    ]
    for url in urls:
        limiter.wait()
        options = youtube_options(extract_flat="in_playlist", playlistend=rows)
        with yt_dlp.YoutubeDL(options) as ydl:
            payload = ydl.extract_info(url, download=False) or {}
        entries = [e for e in (payload.get("entries") or []) if e]
        if entries:
            return entries
    return []


def youtube_details(limiter: RateLimit, video_id: str) -> dict[str, Any]:
    """One metadata read for one video. This is where the licence and the height come from."""
    limiter.wait()
    with yt_dlp.YoutubeDL(youtube_options()) as ydl:
        payload = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    return payload or {}


def youtube_height(payload: dict[str, Any]) -> int:
    heights = [int(f["height"]) for f in payload.get("formats") or [] if f.get("height")]
    best = int(payload.get("height") or 0)
    return max([best, *heights]) if heights else best


def youtube_candidate(payload: dict[str, Any], term: str) -> Candidate | None:
    title = plain_text(str(payload.get("title") or ""), 200)
    words = plain_text(str(payload.get("description") or ""), 300)
    place = plain_text(str(payload.get("location") or ""), 120)
    licence = licence_from_youtube(payload.get("license"))
    if licence is None:
        return None
    duration = float(payload.get("duration") or 0.0)
    height = youtube_height(payload)
    if not in_range(duration, height):
        return None
    match = creek_word(title, words)
    if not match:
        return None
    author = plain_text(str(payload.get("uploader") or payload.get("channel") or ""), 160)
    video_id = str(payload.get("id") or "")
    if not author or not video_id:
        return None
    return Candidate(
        id=f"youtube-{video_id}",
        source="youtube",
        title=title,
        author=author,
        licence=licence,
        duration_s=int(round(duration)),
        height=height,
        country=country_word(title, words, place),
        url=f"https://www.youtube.com/watch?v={video_id}",
        query=term,
        words=words or title,
        match=match,
    )


def youtube_candidates(
    limiter: RateLimit, term: str, rows: int, lookups: int, seen: set[str]
) -> list[Candidate]:
    """Flat search first, then a metadata read for the few entries that could still pass."""
    out: list[Candidate] = []
    spent = 0
    for entry in youtube_search(limiter, term, rows):
        if spent >= lookups:
            break
        video_id = str(entry.get("id") or "")
        url = f"https://www.youtube.com/watch?v={video_id}"
        if not video_id or url in seen:
            continue
        duration = float(entry.get("duration") or 0.0)
        if not MIN_DURATION <= duration <= MAX_DURATION:
            continue
        # The flat search gives no description, so the cheap gate reads the title only. The full
        # read below looks at the description too.
        if not creek_word(plain_text(str(entry.get("title") or ""), 200)):
            continue
        spent += 1
        candidate = youtube_candidate(youtube_details(limiter, video_id), term)
        if candidate is not None:
            out.append(candidate)
    return out


def collect(
    searches: list[Search],
    client: httpx.Client,
    commons_limit: RateLimit,
    youtube_limit: RateLimit,
    per_query: int = PER_QUERY,
    lookups: int = YOUTUBE_LOOKUPS,
) -> tuple[list[Candidate], dict[str, int], list[str]]:
    found: list[Candidate] = []
    seen: set[str] = set()
    tally: dict[str, int] = {}
    problems: list[str] = []
    for search in searches:
        key = f"{search.source}: {search.term}"
        tally.setdefault(key, 0)
        try:
            if search.source == "commons":
                payload = commons_search(client, commons_limit, search.term, COMMONS_ROWS)
                fresh = commons_candidates(payload, search.term)
            else:
                fresh = youtube_candidates(
                    youtube_limit, search.term, YOUTUBE_ROWS, lookups, seen
                )
        except (httpx.HTTPError, ValueError, OSError) as e:
            problems.append(f"{search.source} search {search.term!r} failed: {e}")
            continue
        except yt_dlp.utils.DownloadError as e:
            problems.append(f"youtube search {search.term!r} failed: {e}")
            continue
        kept = 0
        for candidate in fresh:
            if kept >= per_query:
                break
            if candidate.url in seen:
                continue
            seen.add(candidate.url)
            found.append(candidate)
            tally[key] += 1
            kept += 1
    return found, tally, problems


def spread(candidates: list[Candidate], cap: int) -> list[Candidate]:
    """Keep the sheet near the target without letting one country fill it."""
    if len(candidates) <= cap:
        return candidates
    groups: dict[str, list[Candidate]] = {}
    for c in candidates:
        groups.setdefault(c.country or "not stated", []).append(c)
    kept: list[Candidate] = []
    depth = 0
    while len(kept) < cap:
        row = [group[depth] for group in groups.values() if len(group) > depth]
        if not row:
            break
        kept.extend(row[: cap - len(kept)])
        depth += 1
    order = {id(c): n for n, c in enumerate(candidates)}
    return sorted(kept, key=lambda c: order[id(c)])


PICK_SCRIPT = """<script>
(function () {
  function rows() {
    var out = [];
    document.querySelectorAll('.take').forEach(function (box) {
      if (!box.checked) return;
      var pick = box.closest('.pick');
      out.push(box.dataset.row + ',' + JSON.stringify(pick.querySelector('.notes').value.trim()));
    });
    return out;
  }
  function csv() {
    var head = 'id,url,source,licence,author,duration_s,height,country_if_stated,notes';
    return [head].concat(rows()).join('\\n') + '\\n';
  }
  function tally() {
    var n = rows().length;
    document.getElementById('tally').textContent = n + ' picked, 12 wanted';
  }
  document.addEventListener('change', tally);
  document.addEventListener('input', tally);
  document.getElementById('save').addEventListener('click', function () {
    var blob = new Blob([csv()], { type: 'text/csv' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'picks-videos.csv';
    a.click();
    URL.revokeObjectURL(a.href);
  });
  document.getElementById('copy').addEventListener('click', function () {
    navigator.clipboard.writeText(csv()).then(function () {
      document.getElementById('copy').textContent = 'Copied';
    });
  });
  tally();
})();
</script>"""


def pick_control(c: Candidate) -> str:
    """A checkbox and a notes box. The picks file is built in the browser and goes nowhere else."""
    e = html.escape
    row = ",".join(
        json.dumps(str(value))
        for value in (
            c.id,
            c.url,
            c.source,
            c.licence.raw,
            c.author,
            c.duration_s,
            c.height,
            c.country,
        )
    )
    return (
        '<div class="pick">'
        f'<label><input type="checkbox" class="take" data-row="{e(row)}"> pick this</label>'
        '<input class="notes" size="30" placeholder="what you can see, optional">'
        "</div>"
    )


def sheet_html(candidates: list[Candidate], ran_at: datetime) -> str:
    e = html.escape
    sources: dict[str, list[Candidate]] = {}
    for c in candidates:
        sources.setdefault(c.source, []).append(c)
    for items in sources.values():
        items.sort(key=lambda c: (c.country == "", c.country, c.title))
    countries = sorted({c.country for c in candidates if c.country})
    counts = ", ".join(f"{name} {len(items)}" for name, items in sorted(sources.items()))
    parts: list[str] = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Second Look candidates: creek footage</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;margin:1rem;max-width:70rem;color:#111}",
        ".card{border:1px solid #bbb;border-radius:8px;padding:.6rem;margin:.4rem 0}",
        ".meta{font-size:.9rem;line-height:1.4}",
        ".meta p{margin:.25rem 0}",
        "code{background:#f2f2f2;padding:.15rem .3rem;display:inline-block;word-break:break-all}",
        ".warn{color:#8a1c1c}",
        "#bar{position:sticky;top:0;background:#fff;border-bottom:2px solid #333;padding:.6rem 0;"
        "margin-bottom:.6rem;font-size:1rem}",
        "#bar button{font-size:1rem;padding:.4rem .9rem;margin-left:.6rem}",
        ".pick{display:flex;gap:.6rem;align-items:center;margin-top:.4rem;flex-wrap:wrap}",
        ".pick label{font-weight:700}",
        "h2{margin-top:1.6rem;border-top:2px solid #333;padding-top:.6rem}",
        "</style></head><body>",
        "<h1>Creek footage candidates</h1>",
        f"<p>{len(candidates)} candidates ({e(counts)}) from "
        f"{len(countries)} named countries, searched "
        f"{e(ran_at.strftime('%Y-%m-%d %H:%M UTC'))}.</p>",
        f"<p>Countries named by the source: {e(', '.join(countries)) or 'none'}.</p>",
        "<p>Local sheet. Nothing here is in the repo, nothing here is deployed, and nothing loads "
        "from another site, so the page works offline. No video was downloaded to make it. Every "
        "clip below claims CC BY, CC0 or public domain, runs 1 to 20 minutes and is 720 or taller. "
        "Open the link, watch enough to be sure the shot is mostly water and banks, then pick 12 "
        "that spread across countries and across our four features.</p>",
        '<div id="bar"><span id="tally">Nothing picked yet.</span>'
        '<button id="save" type="button">Download the picks file</button>'
        '<button id="copy" type="button">Copy as CSV</button></div>',
    ]
    for name, items in sorted(sources.items()):
        parts.append(f"<h2>{e(name)} ({len(items)})</h2>")
        for c in items:
            credit = (
                "this licence asks us to name the author wherever the clip appears"
                if c.licence.credit
                else "this licence asks for no credit, and we give it anyway"
            )
            parts.extend(
                [
                    '<div class="card"><div class="meta">',
                    f'<p><a href="{e(c.url)}" target="_blank" rel="noreferrer">'
                    f"{e(c.title)}</a></p>",
                    f"<p>Author: {e(c.author)}</p>",
                    f"<p>Licence: {e(c.licence.label)}. The source says: "
                    f"<code>{e(c.licence.raw)}</code> ({credit})</p>",
                    f"<p>Length: {e(minutes(c.duration_s))}. Height: {c.height} pixels.</p>",
                    f"<p>Country the source names: {e(c.country) or 'not stated'}. "
                    f"Word that kept it: {e(c.match)}.</p>",
                    f"<p>Found by the query: {e(c.query)}</p>",
                    f"<p>Source says: {e(c.words)}</p>",
                    f"<p><code>{e(c.id)}</code></p>",
                    pick_control(c),
                    "</div></div>",
                ]
            )
    parts.append(PICK_SCRIPT)
    parts.append("</body></html>")
    return "\n".join(parts)


def write_outputs(candidates: list[Candidate], root: Path = ROOT) -> tuple[Path, Path]:
    folder = root / "videos"
    folder.mkdir(parents=True, exist_ok=True)
    rows = [c.row() for c in candidates]
    data = folder / "candidates.json"
    data.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sheet = folder / "candidates.html"
    sheet.write_text(sheet_html(candidates, datetime.now(UTC)), encoding="utf-8")
    return data, sheet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument(
        "--source",
        choices=["both", "commons", "youtube"],
        default="both",
        help="which site to search",
    )
    parser.add_argument("--cap", type=int, default=TARGET, help="how many to write out")
    parser.add_argument(
        "--per-query", type=int, default=PER_QUERY, help="keep this many per query per site"
    )
    parser.add_argument(
        "--lookups", type=int, default=YOUTUBE_LOOKUPS, help="YouTube metadata reads per query"
    )
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    searches = [s for s in SEARCHES if args.source in (s.source, "both")]
    commons_limit = RateLimit()
    youtube_limit = RateLimit()
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        found, tally, problems = collect(
            searches, client, commons_limit, youtube_limit, args.per_query, args.lookups
        )
    candidates = spread(found, args.cap)
    data, sheet = write_outputs(candidates, args.root)

    sources: dict[str, int] = {}
    for c in candidates:
        sources[c.source] = sources.get(c.source, 0) + 1
    countries = sorted({c.country for c in candidates if c.country})
    split = ", ".join(f"{k} {v}" for k, v in sorted(sources.items()))
    dropped = len(found) - len(candidates)
    print(
        f"find-open-videos: {len(candidates)} candidates ({split}), "
        f"{len(countries)} named countries, {len(found)} passed every filter"
        f"{f', {dropped} left out to keep the spread' if dropped else ''}"
    )
    print(f"find-open-videos: rows at {data.relative_to(args.root)}, "
          f"sheet at {sheet.relative_to(args.root)}")
    empty = [key for key, n in tally.items() if n == 0]
    if empty:
        print(f"find-open-videos: {len(empty)} queries found nothing useful:")
        for key in empty:
            print(f"  nothing from {key}")
    for problem in problems:
        print(f"  search problem: {problem}")
    print("find-open-videos: no video bytes fetched, nothing labelled. A person picks next.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
