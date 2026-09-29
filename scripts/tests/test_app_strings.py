"""The creek check quotes the official app: the quotes, their source and the bundle reader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts import app_strings as a

ROOT = Path(__file__).resolve().parents[2]
DOC = json.loads((ROOT / "content" / "app_strings.json").read_text(encoding="utf-8"))
FORM = yaml.safe_load((ROOT / "content" / "form.yaml").read_text(encoding="utf-8"))


def test_the_reader_reads_data_and_refuses_code() -> None:
    src = (
        'const e={legacy:!1,messages:{en:{q:{question:"Bank Type",'
        'labels:{"I am not sure":"I\\u2019m not sure"}},n:[1,2]},'
        "fr:{q:{question:'Berges'}}}};export{e as default};"
    )
    got = a.parse_bundle(src)
    assert got["en"]["q"]["labels"]["I am not sure"] == "I’m not sure"
    assert got["fr"]["q"]["question"] == "Berges"
    with pytest.raises(a.LiteralError):
        a.parse_bundle("const e={messages:{en:{q:alert(1)}}};")
    with pytest.raises(a.LiteralError):
        a.parse_bundle("const e={messages:{en:{q:`x${alert(1)}`}}};")


def test_tidy_makes_only_the_documented_edits() -> None:
    assert a.tidy("Flat (A)") == "Flat"
    assert a.tidy("U Shape (Β)") == "U Shape"
    assert (
        a.tidy("Artificial (concrete or stones with concrete) (B)")
        == "Artificial (concrete or stones with concrete)"
    )
    assert a.tidy("Dams (see the images)?", drop_picture_note=True) == "Dams?"
    assert a.tidy("Dams (see the images)?") == "Dams (see the images)?"
    assert a.tidy("5" + chr(0x2013) + "10 m") == "5-10 m"


def test_every_quote_names_its_source_and_the_bundle_is_not_committed() -> None:
    src = DOC["source"]
    assert src["app"] == "OneAquaHealth Citizen Science App"
    assert "OneAquaHealth" in src["attribution"]
    assert len(src["bundle_sha256"]) == 64
    assert not list(ROOT.rglob("i18n.config*.js")), "the app's bundle is never committed"


def test_form_english_is_the_app_english_for_every_mirrored_item() -> None:
    en = DOC["strings"]["en"]
    prefix = DOC["source"]["bundle_sha256"][:12]
    for item in FORM["items"]:
        quoted = en["items"].get(item["id"])
        assert quoted, f"{item['id']} is not mirrored"
        assert item["text"] == quoted["text"], item["id"]
        assert item.get("name") == quoted.get("name"), item["id"]
        assert item["verified_against_app"] is True, item["id"]
        assert item["source"] == f"app public bundle, {prefix}, {DOC['source']['fetched']}", item[
            "id"
        ]
        for o in item.get("options", []):
            assert o["label"] == quoted["options"][o["id"]], f"{item['id']}.{o['id']}"
            if "description" in o:
                assert o["description"] == quoted["descriptions"][o["id"]]
    for section in FORM["sections"]:
        if section["id"] in en["sections"]:
            assert section["title"] == en["sections"][section["id"]]


def test_every_mirrored_item_has_each_language_or_an_explicit_fallback() -> None:
    en = DOC["strings"]["en"]["items"]
    for lang in DOC["languages"]:
        block = DOC["strings"][lang]["items"]
        fallback = DOC["fallback"].get(lang, {})
        for iid, entry in en.items():
            for field, _value in [("text", entry["text"])] + [
                (f"option:{o}", v) for o, v in entry.get("options", {}).items()
            ]:
                got = (
                    block.get(iid, {}).get("text")
                    if field == "text"
                    else block.get(iid, {}).get("options", {}).get(field.split(":", 1)[1])
                )
                assert got or f"{iid}.{field}" in fallback, (
                    f"{lang} {iid} {field} has neither a translation nor a fallback"
                )


def test_every_fallback_says_why() -> None:
    for lang, entries in DOC["fallback"].items():
        assert lang in DOC["languages"]
        for key, why in entries.items():
            iid = key.split(".", 1)[0]
            assert iid in DOC["strings"]["en"]["items"], key
            assert len(why) > 20, f"{lang} {key}: say why it falls back"


def test_the_check_notices_a_changed_quote() -> None:
    fresh = json.loads(json.dumps(DOC))
    fresh["strings"]["it"]["items"]["draining_pipes"]["text"] = "Something else?"
    assert any("it draining_pipes text" in d for d in a.compare(DOC, fresh))
    assert a.compare(DOC, DOC) == []


def test_no_quoted_string_carries_a_dash_the_repository_bans() -> None:
    text = json.dumps(DOC, ensure_ascii=False)
    assert chr(0x2013) not in text and chr(0x2014) not in text


def test_the_plant_list_ends_on_the_apps_own_not_sure() -> None:
    """Which ones? is the app's invasive species placeholder, so its not sure answer is that
    question's own, in every language."""
    key = "questions_3_3.invasive_species.labels.I am not sure"
    assert DOC["app_keys"]["items"]["invasive_which"]["options"]["cant_tell"] == key
    for lang in DOC["languages"]:
        items = DOC["strings"][lang]["items"]
        mine = items["invasive_which"]["options"]["cant_tell"]
        assert mine and mine == items["invasive_species"]["options"]["cant_tell"], lang


def test_the_same_bundle_read_again_keeps_its_date_and_a_new_bundle_moves_it() -> None:
    src = 'const e={messages:{en:{feelings:{question:"How?"}}}};'
    first = a.build("https://example.org/one.js", src, "2026-09-26", None)
    again = a.build("/tmp/a-saved-copy.js", src, "2026-09-29", first)
    assert again["source"]["fetched"] == "2026-09-26"
    assert again["source"]["bundle_url"] == "https://example.org/one.js"
    moved = a.build("https://example.org/two.js", src + " ", "2026-09-29", first)
    assert moved["source"]["fetched"] == "2026-09-29"
    assert moved["source"]["bundle_url"] == "https://example.org/two.js"
