"""Pick twelve videos out of the candidates by rule, not by taste (Update 14 section 3 item 3).

In: videos/candidates.json from scripts/find_open_videos.py.
Out: videos/manifest.csv, the twelve we use, and videos/picked.json with the reason each one was
kept or dropped, so the choosing can be argued with.

The rules, in the order they run. Nothing here is a judgement call:

1. Licence must be Creative Commons Attribution, CC0 or public domain. Nothing else.
2. Duration 60 to 1200 seconds, height 720 or more.
3. Topic: the title or the description must name a creek, stream, brook or urban river, AND
   must not match the off-topic list. A piece of music called "The Brook" is not creek footage.
   Night footage is dropped too: asking a vision model to judge a bank in the dark is a
   different question from the one our test asks.
4. Country. A Wikimedia Commons file page states where the subject is, so that is used. A
   YouTube country is the channel's country, not the creek's, so it is ignored and the country
   comes from a place name matched in the title or description, with the name kept as evidence.
   No country means the video can still be picked, it just wins no spread points.
5. Label: from the full description only, through a short list of phrases that can only mean
   one thing. "Restoration project" is deliberately NOT one of them: a restoration video very
   often shows the degraded before state, so the word says nothing about what is on screen.
6. A video already tried whose frames failed the screen (videos/failed_videos.json, written by
   scripts/make_frames.py) is dropped: it is not mostly footage of water and banks.
7. Pick twelve, greedily: a new country first, then a feature we have least of, then the
   shorter video, because a shorter video is a smaller download for the same number of frames.

Run: uv run python scripts/pick_videos.py              pick, and fetch full descriptions
     uv run python scripts/pick_videos.py --offline    pick from the excerpts already on disk
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
VIDEOS = ROOT / "videos"
CANDIDATES = VIDEOS / "candidates.json"
MANIFEST = VIDEOS / "manifest.csv"
PICKED = VIDEOS / "picked.json"
FAILURES = VIDEOS / "failed_videos.json"
WANTED = 12
# Slots kept for videos whose description supports a label, filled before the spread rule runs.
RESERVED_LABELLED = 4
MIN_SECONDS = 60
MAX_SECONDS = 1200
MIN_HEIGHT = 720
USER_AGENT = "SecondLook/0.1 (https://github.com/alejandro-publius/second-look) httpx"

MANIFEST_COLUMNS = [
    "id",
    "title",
    "author",
    "license",
    "source_url",
    "source",
    "country",
    "country_evidence",
    "duration_s",
    "height",
    "cache_file",
    "label_feature",
    "label_value",
    "label_evidence",
    "notes",
]

# Licence strings we accept, matched case insensitively as substrings.
LICENCE_OK = (
    "creative commons attribution",
    "cc by",
    "cc-by",
    "cc0",
    "public domain",
    "publicdomain",
)
LICENCE_NO = ("share-alike", "sharealike", "-sa", "noncommercial", "non-commercial", "noderiv")

CREEK_WORDS = (
    "creek",
    "stream",
    "brook",
    "burn",
    "river walk",
    "riverwalk",
    "urban river",
    "arroyo",
    "quebrada",
    "ruisseau",
    "ручей",
    "小川",
    "하천",
    "천 ",
    "bach",
    "beek",
    "ribeira",
    "riacho",
    "torrente",
)
# A word here means the video is about something else that happens to share a name.
OFF_TOPIC = (
    "healing music",
    "ensemble",
    "op.",
    "opus",
    "symphon",
    "piano",
    "baile",
    "murga",
    "food bank",
    "prescribed fire",
    "hot springs",
    "adventure ride",
    "africa twin",
    "motorcycle",
    "painter",
    "paintings",
    "芋銭",
    "ヒーリング",
)
# Night footage. A bank in the dark is a different question from the one our test asks.
NIGHT_WORDS = (
    "nocturno",
    "nocturna",
    "de noche",
    "night walk",
    "nights -",
    "after dark",
    "at night",
    "저녁",
    "nighttime",
    "night)",
)

# Phrases that can only mean one thing about the channel or the bank. Kept short on purpose.
# "Concrete creek" was here and came out: it matched a video whose project is called Concrete
# Creek and whose every frame is a man reading at a desk. A name is not a description.
# No plant label ever comes from a description (docs/REAL_VS_SYNTHETIC.md): a species call needs
# someone at the plant, and our own rule is a Cal-IPC listing with a link.
LABEL_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    (
        "artificial_bank",
        "present",
        (
            "concrete channel",
            "concrete flood channel",
            "concrete-lined",
            "concrete lined",
            "lined with concrete",
            "concrete culvert",
            "culverted",
            "flood channel",
            "storm channel",
            "encased in concrete",
            "concrete banks",
            "concrete walls",
            "riprap",
            "rip-rap",
            "rip rap",
            "gabion",
            "retaining wall",
        ),
    ),
    (
        "dug_out_channel",
        "present",
        (
            "straightened",
            "channelized",
            "channelised",
            "canalised",
            "canalized",
            "dug out",
            "trapezoidal channel",
        ),
    ),
    (
        "dug_out_channel",
        "absent",
        ("wild and scenic", "free-flowing", "free flowing", "unmodified channel"),
    ),
    (
        "pipe_running",
        "present",
        ("outfall", "storm drain outlet", "discharge pipe", "sewer outlet"),
    ),
]


class PickError(Exception):
    pass


@dataclass
class Candidate:
    raw: dict[str, Any]
    description: str = ""
    dropped_for: str = ""
    country: str = ""
    country_evidence: str = ""
    label_feature: str = ""
    label_value: str = ""
    label_evidence: str = ""
    notes: str = ""
    reasons: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return str(self.raw["id"])

    @property
    def text(self) -> str:
        body = self.description or self.raw.get("description_excerpt", "")
        return f"{self.raw.get('title', '')} {body}".lower()


# A place name we can match, and the country it is in. Only names with one obvious answer.
PLACES: tuple[tuple[str, str], ...] = (
    # City names come before country names: a Buenos Aires video that mentions a street called
    # Israel is in Argentina.
    ("buenos aires", "Argentina"),
    ("sheffield", "United Kingdom"),
    ("wyming brook", "United Kingdom"),
    ("rivelin", "United Kingdom"),
    ("beverley brook", "United Kingdom"),
    ("glenlee", "United Kingdom"),
    ("dalry", "United Kingdom"),
    ("scotland", "United Kingdom"),
    ("new england", "United States"),
    ("england", "United Kingdom"),
    ("dordogne", "France"),
    ("ontario", "Canada"),
    ("canadian rockies", "Canada"),
    ("catlins", "New Zealand"),
    ("new zealand", "New Zealand"),
    ("woolgoolga", "Australia"),
    ("nebraska", "United States"),
    ("reno tahoe", "United States"),
    ("monterrey", "Mexico"),
    ("distritotec", "Mexico"),
    ("jujuy", "Argentina"),
    ("zion national park", "United States"),
    ("idaho", "United States"),
    ("seoul", "South Korea"),
    ("cheonggyecheon", "South Korea"),
    ("gimhae", "South Korea"),
    ("시흥", "South Korea"),
    ("김해", "South Korea"),
    ("korea", "South Korea"),
    ("dubai", "United Arab Emirates"),
    ("wombourne", "United Kingdom"),
    ("black country", "United Kingdom"),
    ("drakensberg", "South Africa"),
    ("south africa", "South Africa"),
    ("wungong", "Australia"),
    ("bibbulmun", "Australia"),
    ("western australia", "Australia"),
    ("walcha", "Australia"),
    ("maipú", "Chile"),
    ("maipu", "Chile"),
    ("приморского", "Russia"),
    ("партизанск", "Russia"),
    ("south bronx", "United States"),
    ("oklahoma", "United States"),
    ("san antonio", "United States"),
    ("sioux falls", "United States"),
    ("baton rouge", "United States"),
    ("atlanta", "United States"),
    ("oregon", "United States"),
    ("columbia water", "United States"),
    ("shai zakai", "Israel"),
    ("israel", "Israel"),
)


def licence_ok(licence: str) -> bool:
    low = licence.lower()
    if any(bad in low for bad in LICENCE_NO):
        return False
    return any(good in low for good in LICENCE_OK)


def sentence_with(text: str, phrase: str) -> str:
    """The sentence the phrase sits in, so the manifest quotes the source rather than a word."""
    for part in re.split(r"(?<=[.!?])\s+|\n", text):
        if phrase in part.lower():
            return " ".join(part.split())[:300]
    return phrase


def fetch_description(candidate: Candidate, client: httpx.Client) -> str:
    source = candidate.raw.get("source")
    url = str(candidate.raw.get("url", ""))
    if source == "wikimedia-commons":
        title = url.rsplit("/", 1)[-1]
        response = client.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "titles": title.replace("_", " "),
                "prop": "imageinfo",
                "iiprop": "extmetadata",
                "format": "json",
            },
        )
        pages = response.json().get("query", {}).get("pages", {})
        for page in pages.values():
            for info in page.get("imageinfo", []) or []:
                meta = info.get("extmetadata", {})
                parts = [
                    meta.get("ImageDescription", {}).get("value", ""),
                    meta.get("Categories", {}).get("value", ""),
                ]
                return re.sub(r"<[^>]+>", " ", " ".join(p for p in parts if p))
        return ""
    proc = subprocess.run(
        ["uv", "run", "yt-dlp", "--skip-download", "--dump-json", "--no-warnings", url],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if proc.returncode != 0:
        return ""
    try:
        return str(json.loads(proc.stdout).get("description", ""))
    except json.JSONDecodeError:
        return ""


def place_country(text: str) -> tuple[str, str]:
    for place, country in PLACES:
        if place in text:
            return country, f"the title or description says {place!r}"
    return "", ""


def label_for(text: str, full: str) -> tuple[str, str, str]:
    for feature, value, phrases in LABEL_RULES:
        for phrase in phrases:
            if phrase in text:
                quote = sentence_with(full, phrase)
                return feature, value, f'The description says: "{quote}"'
    return "", "", ""


def screen(candidate: Candidate) -> bool:
    raw = candidate.raw
    if not licence_ok(str(raw.get("licence", ""))):
        candidate.dropped_for = f"licence not allowed: {raw.get('licence')}"
        return False
    duration = float(raw.get("duration_s") or 0)
    if not (MIN_SECONDS <= duration <= MAX_SECONDS):
        candidate.dropped_for = (
            f"duration {duration:.0f} s is outside {MIN_SECONDS} to {MAX_SECONDS}"
        )
        return False
    if int(raw.get("height") or 0) < MIN_HEIGHT:
        candidate.dropped_for = f"height {raw.get('height')} is under {MIN_HEIGHT}"
        return False
    text = candidate.text
    if not any(word in text for word in CREEK_WORDS):
        candidate.dropped_for = "no creek, stream, brook or urban river in the title or description"
        return False
    off = [w for w in OFF_TOPIC if w in text]
    if off:
        candidate.dropped_for = f"off topic: the words {off} say this is about something else"
        return False
    night = [w for w in NIGHT_WORDS if w in text]
    if night:
        candidate.dropped_for = (
            f"night footage: the words {night} say so, and the dark is a different test"
        )
        return False
    return True


def choose(
    kept: list[Candidate], wanted: int, reserved: int = RESERVED_LABELLED
) -> list[Candidate]:
    """Labelled videos first, up to the reserve, then a new country, then the rarest feature."""
    chosen: list[Candidate] = []
    countries: Counter[str] = Counter()
    features: Counter[str] = Counter()
    pool = sorted(kept, key=lambda c: float(c.raw.get("duration_s") or 0))
    labelled = [c for c in pool if c.label_feature][:reserved]
    for c in labelled:
        pool.remove(c)
        c.reasons = [
            f"kept a reserved slot: its description supports {c.label_feature} {c.label_value}"
        ]
        countries[c.country] += 1
        features[c.label_feature] += 1
        chosen.append(c)
    while pool and len(chosen) < wanted:

        def rank(c: Candidate) -> tuple[int, int, float]:
            country_seen = countries[c.country] if c.country else 99
            feature_seen = features[c.label_feature or "unlabelled"]
            return (country_seen, feature_seen, float(c.raw.get("duration_s") or 0))

        best = min(pool, key=rank)
        pool.remove(best)
        why = []
        if best.country and countries[best.country] == 0:
            why.append(f"first video from {best.country}")
        if best.label_feature:
            why.append(f"its description supports {best.label_feature} {best.label_value}")
        else:
            why.append("unlabelled, so it only ever feeds the agreement figure")
        best.reasons = why
        countries[best.country] += 1
        features[best.label_feature or "unlabelled"] += 1
        chosen.append(best)
    return chosen


def cache_name(candidate: Candidate, index: int) -> str:
    """Named by the source id only, so picking again never downloads the same video twice."""
    del index
    return f"{re.sub(r'[^a-z0-9]+', '-', candidate.id.lower()).strip('-')}.mp4"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="use the excerpts already on disk")
    parser.add_argument("--wanted", type=int, default=WANTED)
    args = parser.parse_args(argv)

    if not CANDIDATES.exists():
        print(f"pick-videos: {CANDIDATES} is missing; run scripts/find_open_videos.py first")
        return 1
    candidates = [Candidate(raw=raw) for raw in json.loads(CANDIDATES.read_text(encoding="utf-8"))]
    # A video whose frames failed the screen in scripts/make_frames.py is not mostly water and
    # banks. It is dropped here with the reason the frame screen gave, and the rule picks again.
    failed = json.loads(FAILURES.read_text(encoding="utf-8")) if FAILURES.exists() else {}
    for c in candidates:
        if str(c.raw.get("url", "")) in failed:
            c.dropped_for = f"frames: {failed[str(c.raw.get('url', ''))]}"
    kept = [c for c in candidates if not c.dropped_for and screen(c)]
    dropped = [c for c in candidates if c.dropped_for]
    print(f"pick-videos: {len(candidates)} candidates, {len(kept)} pass the hard filters")

    if not args.offline:
        headers = {"User-Agent": USER_AGENT}
        with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
            for candidate in kept:
                candidate.description = fetch_description(candidate, client)
        got = sum(1 for c in kept if c.description)
        print(f"pick-videos: full description fetched for {got} of {len(kept)}")

    for candidate in kept:
        full = candidate.description or str(candidate.raw.get("description_excerpt") or "")
        text = candidate.text
        # A Commons file page states where the subject is. A YouTube country is the channel's
        # country, which is often not where the creek is, so it is not used.
        if candidate.raw.get("source") == "wikimedia-commons":
            candidate.country = str(candidate.raw.get("country_if_stated") or "")
            candidate.country_evidence = (
                "the Commons file page states it" if candidate.country else ""
            )
        else:
            candidate.country, candidate.country_evidence = "", ""
        if not candidate.country:
            candidate.country, candidate.country_evidence = place_country(text)
        feature, value, evidence = label_for(text, full)
        candidate.label_feature, candidate.label_value, candidate.label_evidence = (
            feature,
            value,
            evidence,
        )
        candidate.notes = " ".join(full.split())[:200]

    chosen = choose(kept, args.wanted)
    VIDEOS.mkdir(exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for index, c in enumerate(chosen, start=1):
            writer.writerow(
                {
                    "id": f"v{index:02d}",
                    "title": c.raw.get("title", ""),
                    "author": c.raw.get("author", ""),
                    "license": c.raw.get("licence", ""),
                    "source_url": c.raw.get("url", ""),
                    "source": c.raw.get("source", ""),
                    "country": c.country,
                    "country_evidence": c.country_evidence,
                    "duration_s": int(float(c.raw.get("duration_s") or 0)),
                    "height": c.raw.get("height", ""),
                    "cache_file": cache_name(c, index),
                    "label_feature": c.label_feature,
                    "label_value": c.label_value,
                    "label_evidence": c.label_evidence,
                    "notes": c.notes,
                }
            )
    PICKED.write_text(
        json.dumps(
            {
                "candidates": len(candidates),
                "passed_filters": len(kept),
                "chosen": len(chosen),
                "countries": sorted({c.country for c in chosen if c.country}),
                "labelled": sum(1 for c in chosen if c.label_feature),
                "kept": [
                    {
                        "id": c.id,
                        "manifest_id": f"v{i:02d}",
                        "country": c.country,
                        "label": f"{c.label_feature} {c.label_value}".strip() or "unlabelled",
                        "why": c.reasons,
                        "description": " ".join((c.description or "").split())[:800],
                    }
                    for i, c in enumerate(chosen, start=1)
                ],
                "not_chosen": [
                    {"id": c.id, "why": "passed the filters but the spread rule chose another"}
                    for c in kept
                    if c not in chosen
                ],
                "dropped": [{"id": c.id, "why": c.dropped_for} for c in dropped],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    countries = sorted({c.country for c in chosen if c.country})
    labelled = sum(1 for c in chosen if c.label_feature)
    print(
        f"pick-videos: {len(chosen)} videos from {len(countries)} countries "
        f"({', '.join(countries)}); {labelled} carry a description that supports a label, "
        f"{len(chosen) - labelled} are unlabelled. "
        f"videos/manifest.csv and videos/picked.json written"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
