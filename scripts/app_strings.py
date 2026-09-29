"""The official app's own words for the creek check, read from its public bundle.

The OneAquaHealth Citizen Science App (https://apps.oneaquahealth.eu) ships its translations to any
browser in a public JavaScript chunk, the Nuxt i18n config under /_nuxt/. This script reads that
chunk without logging in and without running it: a small parser reads the object literal as data.
It keeps only the strings the creek check quotes, each with the app key it came from, in
content/app_strings.json. The bundle itself is never committed.

  uv run python scripts/app_strings.py write   fetch, extract, write content/app_strings.json
  uv run python scripts/app_strings.py check   fetch again, fail if a string we quote has changed
  uv run python scripts/app_strings.py check --bundle FILE   the same against a saved copy

The map below says which app key each form item, option, section title, button and label quotes.
Our English buttons and labels stay our own: the app's English is kept beside the translations for
the check, and one of its labels has a typo. Two edits are
made to the app's text, the same way in every language, and both are listed in
docs/notes/app_strings.md: the answer letters such as "(A)" are dropped, because they point at the
app's example pictures, which we do not show; and the barriers question drops its note about those
pictures. A typographic dash inside a quoted string becomes a plain hyphen, as the repository has no
dashes of that kind (CLAUDE.md rule 18).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "content" / "app_strings.json"
APP_URL = "https://apps.oneaquahealth.eu/"
APP_NAME = "OneAquaHealth Citizen Science App"
ATTRIBUTION = (
    "Question and answer wording quoted from the OneAquaHealth Citizen Science App "
    "(https://apps.oneaquahealth.eu), read from its public translation bundle, so a volunteer sees "
    "the questions they already know. The wording belongs to the OneAquaHealth project."
)
USER_AGENT = "SecondLook-app-strings-check (+https://github.com/alejandro-publius/second-look)"

Q1, Q2, Q3 = "questions_1_3", "questions_2_3", "questions_3_3"
NOT_SURE = "I am not sure"
YESNO = {"present": "Yes", "absent": "No", "cant_tell": NOT_SURE}


def _yesno(group: str, key: str) -> dict[str, Any]:
    return {
        "text": [group, key, "questiontext"],
        "options": {v: [group, key, "labels", label] for v, label in YESNO.items()},
    }


def _choice(
    group: str,
    key: str,
    options: dict[str, str],
    *,
    text: str = "questiontext",
    field: str = "labels",
) -> dict[str, Any]:
    return {
        "text": [group, key, text],
        "options": {oid: [group, key, field, label] for oid, label in options.items()},
    }


# Our form item id -> the app keys it quotes. Option ids are ours (content/form.yaml); for a yes or
# no item they are the stored values present, absent and cant_tell.
ITEMS: dict[str, dict[str, Any]] = {
    "channel_form": _choice(
        Q1,
        "channel_form",
        {
            "flat": "Flat (A)",
            "u_shape": "U Shape (B)",
            "v_shape": "V Shape (C)",
            "not_sure": NOT_SURE,
        },
    ),
    "bottom_type": _choice(
        Q1,
        "bottom_type",
        {
            "natural": "Natural (A)",
            "artificial": "Artificial (concrete or stones with concrete) (B)",
            "not_sure": NOT_SURE,
        },
    ),
    "bank_type": _choice(
        Q1,
        "bank_type",
        {
            "natural": "Natural (A)",
            "artificial": "Artificial (concrete or stones with concrete) (B)",
            "laid_stones": "Layed stones with no concrete (C)",
            "not_sure": NOT_SURE,
        },
    ),
    "habitats": _choice(
        Q1,
        "habitats",
        {
            "sand_banks": "Sand banks (A)",
            "sand_islands": "Sand islands (B)",
            "stone_deposits": "Stone deposits (C)",
            "riffles": "Riffles, rapids, falls (D)",
            "aquatic_vegetation": "Aquatic vegetation (E)",
        },
        text="questiontextshow",
        field="options",
    ),
    "natural_debris": _choice(
        Q1,
        "natural_debris",
        {
            "fallen_trees": "Fallen trees (A)",
            "fallen_branches": "Fallen branches (B)",
            "leaf_deposits": "Deposits of fallen leaves (C)",
        },
        text="questiontextshow",
    ),
    "water_flow": _choice(
        Q1,
        "water_flow",
        {
            "fast": "Fast (with waves or high velocity) (A)",
            "slow": "Slow (B)",
            "stagnant": "Stagnant/intermittent (C)",
            "dry": "Dry (D)",
            "not_sure": NOT_SURE,
        },
    ),
    "water_aspect": _choice(
        Q2,
        "water_aspect_labels",
        {
            "clear": "Clear/transparent (A)",
            "muddy": "Muddy/turbid (B)",
            "foam": "Has foam (C)",
            "colour": "Has colors/altered color (D)",
            "not_sure": NOT_SURE,
        },
    ),
    "water_withdrawal": _yesno(Q2, "water_withdrawal"),
    "barriers": {**_yesno(Q2, "barriers"), "drop_picture_note": True},
    "draining_pipes": _yesno(Q2, "draining_pipes"),
    "sewage_discharge": _yesno(Q2, "sewage_discharge"),
    "construction": _yesno(Q2, "construction"),
    "water_height_m": {"text": [Q2, "water_height", "questiontext"]},
    "impervious_left": _yesno(Q3, "impervious_left"),
    "impervious_right": _yesno(Q3, "impervious_right"),
    "vegetation_left": _yesno(Q3, "vegetation_left"),
    "vegetation_right": _yesno(Q3, "vegetation_right"),
    "vegetation_type_left": _choice(
        Q3,
        "vegetation_type_left",
        {"herbs": "Herbs (A)", "shrubs": "Shrubs (B)", "trees": "Trees (C)", "not_sure": NOT_SURE},
    ),
    "vegetation_type_right": _choice(
        Q3,
        "vegetation_type_right",
        {"herbs": "Herbs (A)", "shrubs": "Shrubs (B)", "trees": "Trees (C)", "not_sure": NOT_SURE},
    ),
    "invasive_species": _yesno(Q3, "invasive_species"),
    # "Which ones?" is the placeholder of the app's invasive species question. Our plant list
    # ends on a not sure answer, worded as that same app question words its own.
    "invasive_which": {
        "text": [Q3, "invasive_species", "placeholder"],
        "options": {"cant_tell": [Q3, "invasive_species", "labels", NOT_SURE]},
    },
    "vegetation_cuts": _yesno(Q3, "vegetation_cut"),
    "feelings": {
        "text": ["feelings", "question"],
        "options": {
            "joy": ["feelings", "Joy"],
            "serenity": ["feelings", "Serenity"],
            "anger": ["feelings", "Anger"],
            "fear": ["feelings", "Fear"],
            "not_applicable": ["feelings", "NotApplicable"],
        },
    },
    "overall_rating": {
        "text": ["stream_health", "question"],
        "options": {
            "good": ["stream_health", "good_quality"],
            "moderate": ["stream_health", "moderate_quality"],
            "poor": ["stream_health", "poor_quality"],
        },
        "descriptions": {
            "good": ["stream_health", "good_quality_description"],
            "moderate": ["stream_health", "moderate_quality_description"],
            "poor": ["stream_health", "poor_quality_description"],
        },
    },
}

# Our form section id -> the app's section title.
SECTIONS: dict[str, list[str]] = {
    "what_you_see": [Q1, "title"],
    "margins": [Q3, "title"],
}

# Our own button or label -> the app's own word for the same thing. The English of these is
# ours (content/locales/en.json); the app's English, typo and all, is kept only to be checked.
UI: dict[str, list[str]] = {
    "back": ["previous"],
    "next": ["next"],
    "send": ["submit"],
    "latitude": ["latitude"],
    "longitude": ["longitude"],
    "spot_name": ["site_name"],
}

_LETTER = re.compile(r"\s*\((?:[A-E]|[Α-Ε])\)\s*$")
_PICTURE_NOTE = re.compile(r"\s*\([^()]*\)(?=\s*[?;]?\s*$)")
_DASHES = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")


def tidy(s: str, *, drop_picture_note: bool = False) -> str:
    """The two documented edits and the dash rule; nothing else changes."""
    s = _LETTER.sub("", s)
    if drop_picture_note:
        s = _PICTURE_NOTE.sub("", s)
    s = _DASHES.sub("-", s)
    return s.strip()


# A reader for the bundle's object literal. It reads data only: objects, arrays, strings, numbers,
# true, false and null. Anything else is an error, so no code from the bundle is ever run.


class LiteralError(ValueError):
    pass


class _Reader:
    def __init__(self, src: str, pos: int) -> None:
        self.s = src
        self.i = pos

    def ws(self) -> None:
        while self.i < len(self.s) and self.s[self.i] in " \t\r\n":
            self.i += 1

    def value(self) -> Any:
        self.ws()
        c = self.s[self.i]
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c in "\"'`":
            return self.string()
        m = re.compile(r"-?\d+(?:\.\d+)?|!0|!1|true|false|null").match(self.s, self.i)
        if not m:
            raise LiteralError(f"unexpected {self.s[self.i : self.i + 20]!r} at {self.i}")
        self.i = m.end()
        tok = m.group(0)
        return {"!0": True, "!1": False, "true": True, "false": False, "null": None}.get(tok, tok)

    def string(self) -> str:
        q = self.s[self.i]
        self.i += 1
        out: list[str] = []
        while True:
            c = self.s[self.i]
            if c == q:
                self.i += 1
                return "".join(out)
            if q == "`" and c == "$" and self.s[self.i + 1] == "{":
                raise LiteralError("template expression in bundle string")
            if c == "\\":
                n = self.s[self.i + 1]
                if n == "u":
                    if self.s[self.i + 2] == "{":
                        end = self.s.index("}", self.i)
                        out.append(chr(int(self.s[self.i + 3 : end], 16)))
                        self.i = end + 1
                    else:
                        out.append(chr(int(self.s[self.i + 2 : self.i + 6], 16)))
                        self.i += 6
                    continue
                if n == "x":
                    out.append(chr(int(self.s[self.i + 2 : self.i + 4], 16)))
                    self.i += 4
                    continue
                out.append(
                    {
                        "n": "\n",
                        "t": "\t",
                        "r": "\r",
                        "b": "\b",
                        "f": "\f",
                        "v": "\v",
                        "0": "\0",
                        "\n": "",
                    }.get(n, n)
                )
                self.i += 2
                continue
            out.append(c)
            self.i += 1

    def key(self) -> str:
        self.ws()
        c = self.s[self.i]
        if c in "\"'":
            return self.string()
        m = re.compile(r"[A-Za-z_$][\w$]*|\d+").match(self.s, self.i)
        if not m:
            raise LiteralError(f"bad key at {self.i}")
        self.i = m.end()
        return m.group(0)

    def obj(self) -> dict[str, Any]:
        self.i += 1
        out: dict[str, Any] = {}
        while True:
            self.ws()
            if self.s[self.i] == "}":
                self.i += 1
                return out
            k = self.key()
            self.ws()
            if self.s[self.i] != ":":
                raise LiteralError(f"expected : at {self.i}")
            self.i += 1
            out[k] = self.value()
            self.ws()
            if self.s[self.i] == ",":
                self.i += 1

    def arr(self) -> list[Any]:
        self.i += 1
        out: list[Any] = []
        while True:
            self.ws()
            if self.s[self.i] == "]":
                self.i += 1
                return out
            out.append(self.value())
            self.ws()
            if self.s[self.i] == ",":
                self.i += 1


def parse_bundle(src: str) -> dict[str, dict[str, Any]]:
    """The messages object of the i18n chunk, by language."""
    m = re.search(r"messages\s*:\s*\{", src)
    if not m:
        raise LiteralError("no messages object in the bundle")
    messages = _Reader(src, m.end() - 1).obj()
    return {lang: msgs for lang, msgs in messages.items() if isinstance(msgs, dict)}


def _get(msgs: dict[str, Any], path: list[str]) -> str | None:
    cur: Any = msgs
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur if isinstance(cur, str) else None


def fetch_bundle() -> tuple[str, str]:
    """(bundle URL, text). Reads the app's start page for the chunk's current name."""
    req = urllib.request.Request(APP_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310, a fixed https URL
        page = r.read().decode("utf-8")
    m = re.search(r"/_nuxt/i18n\.config\.[\w-]+\.js", page)
    if not m:
        raise SystemExit("app-strings: the app's start page no longer names an i18n config chunk")
    url = APP_URL.rstrip("/") + m.group(0)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
        return url, r.read().decode("utf-8")


def extract(messages: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Every quoted string, per language, with the raw app text it came from."""
    langs: dict[str, Any] = {}
    for lang, msgs in messages.items():
        items: dict[str, Any] = {}
        for item_id, spec in ITEMS.items():
            drop = bool(spec.get("drop_picture_note"))
            entry: dict[str, Any] = {}
            if spec["text"][-1] in ("questiontext", "questiontextshow"):
                name = _get(msgs, [*spec["text"][:-1], "question"])
                if name is not None:
                    entry["name"] = tidy(name)
            raw = _get(msgs, spec["text"])
            if raw is not None:
                entry["text"] = tidy(raw, drop_picture_note=drop)
            for field in ("options", "descriptions"):
                got = {}
                for oid, path in spec.get(field, {}).items():
                    r = _get(msgs, path)
                    if r is not None:
                        got[oid] = tidy(r)
                if got:
                    entry[field] = got
            if entry:
                items[item_id] = entry
        sections = {
            sid: tidy(s) for sid, path in SECTIONS.items() if (s := _get(msgs, path)) is not None
        }
        ui = {key: tidy(s) for key, path in UI.items() if (s := _get(msgs, path)) is not None}
        if items:
            langs[lang] = {"items": items, "sections": sections, "ui": ui}
    return langs


def app_keys() -> dict[str, Any]:
    """The app key each quoted string came from, written beside the strings for anyone checking."""
    return {
        "items": {
            iid: {
                f: (".".join(p) if f == "text" else {o: ".".join(q) for o, q in p.items()})
                for f, p in spec.items()
                if f in ("text", "options", "descriptions")
            }
            for iid, spec in ITEMS.items()
        },
        "sections": {sid: ".".join(p) for sid, p in SECTIONS.items()},
        "ui": {key: ".".join(p) for key, p in UI.items()},
    }


def build(
    url: str, text: str, fetched: str, previous: dict[str, Any] | None = None
) -> dict[str, Any]:
    messages = parse_bundle(text)
    langs = extract(messages)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    # The same bundle read again keeps the day and the address it was first fetched from, so
    # quoting one more of its strings does not move the date every form item names as its source.
    before = (previous or {}).get("source", {})
    if before.get("bundle_sha256") == sha:
        url, fetched = before.get("bundle_url", url), before.get("fetched", fetched)
    doc: dict[str, Any] = {
        "source": {
            "app": APP_NAME,
            "app_url": APP_URL,
            "bundle_url": url,
            "bundle_sha256": sha,
            "fetched": fetched,
            "attribution": ATTRIBUTION,
            "bundle_languages": sorted(messages),
            "languages_without_assessment": sorted(set(messages) - set(langs)),
        },
        "languages": [lang for lang in ["en", "pt", "nl", "no", "fr", "it", "el"] if lang in langs]
        + sorted(set(langs) - {"en", "pt", "nl", "no", "fr", "it", "el"}),
        "app_keys": app_keys(),
        "strings": langs,
        # Filled by hand from docs/notes/app_translations.md: a quoted string whose meaning differs
        # from the English falls back to English in that language. Kept across a rewrite.
        "fallback": (previous or {}).get("fallback", {}),
    }
    return doc


def compare(committed: dict[str, Any], fresh: dict[str, Any]) -> list[str]:
    """Every quoted string that differs, or is gone, in the fresh bundle."""
    out: list[str] = []
    for lang, block in committed["strings"].items():
        new = fresh["strings"].get(lang)
        if new is None:
            out.append(f"{lang}: the language is gone from the bundle")
            continue
        for sid, s in block["sections"].items():
            if new["sections"].get(sid) != s:
                out.append(f"{lang} section {sid}: {s!r} is now {new['sections'].get(sid)!r}")
        for key, s in block.get("ui", {}).items():
            if new.get("ui", {}).get(key) != s:
                out.append(f"{lang} ui {key}: {s!r} is now {new.get('ui', {}).get(key)!r}")
        # A button or label the map quotes and the bundle has, but the file does not hold.
        for key in sorted(set(new.get("ui", {})) - set(block.get("ui", {}))):
            out.append(f"{lang} ui {key}: not in the file, the bundle has {new['ui'][key]!r}")
        for iid, entry in block["items"].items():
            got = new["items"].get(iid, {})
            for field in ("name", "text"):
                if got.get(field) != entry.get(field):
                    out.append(
                        f"{lang} {iid} {field}: {entry.get(field)!r} is now {got.get(field)!r}"
                    )
            for field in ("options", "descriptions"):
                for oid, s in entry.get(field, {}).items():
                    if got.get(field, {}).get(oid) != s:
                        out.append(
                            f"{lang} {iid}.{oid}: {s!r} is now {got.get(field, {}).get(oid)!r}"
                        )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=["write", "check"])
    ap.add_argument("--bundle", type=Path, help="a saved copy of the chunk instead of fetching")
    ap.add_argument("--bundle-url", default=None)
    args = ap.parse_args(argv)
    if args.bundle:
        url, text = args.bundle_url or str(args.bundle), args.bundle.read_text(encoding="utf-8")
    else:
        url, text = fetch_bundle()
    today = datetime.now(UTC).date().isoformat()
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else None
    if args.action == "write":
        doc = build(url, text, today, previous)
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        n = sum(len(b["items"]) for b in doc["strings"].values())
        ui = sum(len(b["ui"]) for b in doc["strings"].values())
        print(
            f"app-strings: {len(doc['strings'])} languages, {n} items, {ui} buttons and labels, "
            f"sha256 {doc['source']['bundle_sha256'][:12]} into {OUT.relative_to(ROOT)}"
        )
        return 0
    if previous is None:
        print("app-strings: no content/app_strings.json to check", file=sys.stderr)
        return 1
    fresh = build(url, text, today, previous)
    diffs = compare(previous, fresh)
    same_bundle = fresh["source"]["bundle_sha256"] == previous["source"]["bundle_sha256"]
    for d in diffs:
        print(f"CHANGED {d}")
    note = (
        "the same bundle"
        if same_bundle
        else f"a new bundle, sha256 {fresh['source']['bundle_sha256'][:12]}, {url}"
    )
    if diffs:
        print(f"app-strings-check: FAIL, {len(diffs)} quoted strings changed ({note})")
        return 1
    print(f"app-strings-check: PASS, every quoted string unchanged ({note})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
