"""A locale string may quote another by its key, as {time.test} (judge walk W09).

How long the test and the creek check take is written once, under time., and the strings that
quote it read it from there. The web build resolves the same way (apps/web/scripts/locale-refs.mjs,
apps/web/tests/times.spec.ts).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.content_loader import ContentError, load_content, locale_ref_problems, resolve_locale

ROOT = Path(__file__).resolve().parents[2]


def test_a_reference_is_replaced_by_the_string_it_names_and_fill_ins_are_left_alone() -> None:
    locale = {
        "time.test": "about four minutes",
        "end.share": "{correct} of 16. It takes {time.test}.",
    }
    assert resolve_locale(locale)["end.share"] == "{correct} of 16. It takes about four minutes."
    assert resolve_locale(locale)["time.test"] == "about four minutes"


def test_a_missing_key_and_a_chain_are_refused() -> None:
    assert locale_ref_problems({"a.b": "It takes {time.gone}."}) == [
        "a.b quotes time.gone, which the locale does not have"
    ]
    chained = {"time.test": "{time.other}", "time.other": "four", "a.b": "{time.test}"}
    assert locale_ref_problems(chained) == [
        "a.b quotes time.test, which quotes another string in turn"
    ]
    with pytest.raises(ContentError):
        resolve_locale(chained)


def test_the_repository_locale_resolves_and_its_hash_is_over_the_file_as_written() -> None:
    content = load_content(ROOT)
    written = json.loads((ROOT / "content" / "locales" / "en.json").read_text(encoding="utf-8"))
    assert content.locale == written, "Content.locale must stay as written: the hash is over it"
    shown = resolve_locale(content.locale)
    assert shown["consent.what"].startswith(
        "This is a usability test of a training tool. It takes about four minutes. "
    )
    assert not [k for k, v in shown.items() if isinstance(v, str) and "{time." in v]
