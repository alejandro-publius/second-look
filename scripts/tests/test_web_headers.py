"""The landing page and the poster send their two photos as Early Hints (Link headers).

Pages wrote these headers itself from the pages' preload tags until the project gained the /api
Functions. After that the first screen on a throttled phone went from about 1.5 to 8.5 seconds.
Since Update 22 the two warm-up photos have smaller AVIF and WebP copies, and the header preloads
the AVIF set the page will use instead of the JPEG, so no phone downloads both.
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "apps" / "web"
MODULE = WEB / "security-headers.mjs"
SOURCES = WEB / "photo-sources.mjs"

CONTENT: dict[str, Any] = {
    "warmup": [{"photo_id": "a"}, {"photo_id": "b"}, {"photo_id": "c"}],
    "photos": {k: {"url": f"/photos/{k}.jpg"} for k in "abc"},
}
AVIF = "/photos/a-480.avif 480w, /photos/a-800.avif 800w"
SIZES = "(min-width: 900px) 612px, 90vw"
WITH_COPIES: dict[str, Any] = {
    **CONTENT,
    "photos": {
        **CONTENT["photos"],
        "a": {
            "url": "/photos/a.jpg",
            "sources": [
                {"type": "image/avif", "srcset": AVIF},
                {"type": "image/webp", "srcset": "/photos/a-480.webp 480w"},
            ],
            "sizes": SIZES,
        },
    },
}


def run(expr: str, module: Path = MODULE) -> subprocess.CompletedProcess[str]:
    if shutil.which("node") is None:
        pytest.skip("needs node")
    body = (
        f"const m = await import({json.dumps(module.as_uri())});\n"
        f"process.stdout.write(JSON.stringify({expr}));"
    )
    return subprocess.run(
        ["node", "--input-type=module", "-e", body],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def call(expr: str, module: Path = MODULE) -> Any:
    done = run(expr, module)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def fails(expr: str, module: Path = MODULE) -> str:
    done = run(expr, module)
    assert done.returncode != 0, f"expected an error, got {done.stdout}"
    return done.stderr


def test_the_first_two_warmup_photos_are_preloaded_on_the_landing_page_and_the_poster() -> None:
    # The first is the landing page's largest paint, so it alone asks for high priority.
    links = [{"href": "/photos/a.jpg", "fetchpriority": "high"}, {"href": "/photos/b.jpg"}]
    assert call(f"m.photoPreloads({json.dumps(CONTENT)})") == {"/": links, "/poster": links}
    assert call("m.photoPreloads({})") == {}


def test_the_headers_file_carries_one_link_header_per_page() -> None:
    text = call(
        f"m.headersFile({{ apiOrigin: '', preloads: m.photoPreloads({json.dumps(CONTENT)}) }})"
    )
    link = (
        "  Link: </photos/a.jpg>; rel=preload; as=image; fetchpriority=high, "
        "</photos/b.jpg>; rel=preload; as=image"
    )
    assert f"/\n{link}\n" in text
    assert f"/poster\n{link}\n" in text
    assert "c.jpg" not in text


def test_a_photo_with_smaller_copies_preloads_its_avif_set_and_not_the_jpeg() -> None:
    text = call(
        f"m.headersFile({{ apiOrigin: '', preloads: m.photoPreloads({json.dumps(WITH_COPIES)}) }})"
    )
    avif = (
        f'</photos/a-480.avif>; rel=preload; as=image; type="image/avif"; '
        f'imagesrcset="{AVIF}"; imagesizes="{SIZES}"; fetchpriority=high'
    )
    link = f"  Link: {avif}, </photos/b.jpg>; rel=preload; as=image"
    assert f"/\n{link}\n" in text
    assert f"/poster\n{link}\n" in text
    assert "a.jpg" not in text
    assert "webp" not in text


def test_the_preload_asks_for_exactly_what_the_page_shows() -> None:
    """Same srcset and sizes as the page's AVIF source, or the browser may fetch two copies."""
    photo = WITH_COPIES["photos"]["a"]
    got = call(f"m.photoPreload({json.dumps(photo)})")
    assert got == {
        "href": "/photos/a-480.avif",
        "type": "image/avif",
        "imagesrcset": AVIF,
        "imagesizes": SIZES,
    }


def test_a_headers_line_longer_than_pages_reads_fails_the_build() -> None:
    long = ", ".join(f"/photos/a-{w}.avif {w}w" for w in range(1, 120))
    photo = {"url": "/photos/a.jpg", "sources": [{"type": "image/avif", "srcset": long}]}
    content = {"warmup": [{"photo_id": "a"}], "photos": {"a": {**photo, "sizes": SIZES}}}
    err = fails(
        f"m.headersFile({{ apiOrigin: '', preloads: m.photoPreloads({json.dumps(content)}) }})"
    )
    assert "over the 2000" in err


def test_a_link_fetchpriority_is_one_of_three_words() -> None:
    err = fails("""m.linkEntry({ href: "/a", fetchpriority: "high; rel=evil" })""")
    assert "high, low or auto" in err


def test_a_link_value_cannot_break_out_of_its_quotes() -> None:
    err = fails("""m.linkEntry({ href: "/a", imagesizes: '90vw", </evil>; rel=preload' })""")
    assert "cannot hold quotes" in err


def manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_copies_become_sources_avif_first_and_a_photo_without_copies_gets_none() -> None:
    rows = [
        {"id": "a", "sha256": "aaa"},
        {"id": "b", "sha256": "bbb"},
    ]
    derived = [
        {
            "file": "derived/a-800.webp",
            "source_id": "a",
            "source_sha256": "aaa",
            "format": "webp",
            "width": "800",
        },
        {
            "file": "derived/a-800.avif",
            "source_id": "a",
            "source_sha256": "aaa",
            "format": "avif",
            "width": "800",
        },
        {
            "file": "derived/a-480.avif",
            "source_id": "a",
            "source_sha256": "aaa",
            "format": "avif",
            "width": "480",
        },
    ]
    got = call(f"m.derivedSources({json.dumps(rows)}, {json.dumps(derived)})", SOURCES)
    assert list(got) == ["a"]
    assert got["a"]["sources"] == [
        {"type": "image/avif", "srcset": "/photos/a-480.avif 480w, /photos/a-800.avif 800w"},
        {"type": "image/webp", "srcset": "/photos/a-800.webp 800w"},
    ]
    assert got["a"]["sizes"] == SIZES
    assert sorted(got["a"]["files"]) == sorted(r["file"] for r in derived)


def test_a_copy_made_from_another_version_of_its_photo_fails_the_build() -> None:
    rows = [{"id": "a", "sha256": "new"}]
    derived = [
        {
            "file": "derived/a-480.avif",
            "source_id": "a",
            "source_sha256": "old",
            "format": "avif",
            "width": "480",
        }
    ]
    err = fails(f"m.derivedSources({json.dumps(rows)}, {json.dumps(derived)})", SOURCES)
    assert "another version" in err
    unknown = [{**derived[0], "source_id": "zz", "source_sha256": "new"}]
    err = fails(f"m.derivedSources({json.dumps(rows)}, {json.dumps(unknown)})", SOURCES)
    assert "no manifest row" in err


def test_the_committed_headers_file_preloads_the_avif_copies_of_the_real_warmup_photos() -> None:
    """public/_headers is committed, so it has to match the manifests it was built from."""
    rows = manifest(ROOT / "photos" / "manifest.csv")
    derived = manifest(ROOT / "photos" / "derived" / "manifest.csv")
    warmup = yaml.safe_load((ROOT / "content" / "test_items.yaml").read_text(encoding="utf-8"))[
        "warmup"
    ]
    copies = call(f"m.derivedSources({json.dumps(rows)}, {json.dumps(derived)})", SOURCES)
    photos = {
        w["photo_id"]: {"url": f"/photos/{w['photo_id']}.jpg", **copies[w["photo_id"]]}
        for w in warmup
    }
    content = {"warmup": warmup, "photos": photos}
    built = call(
        f"m.headersFile({{ apiOrigin: '', preloads: m.photoPreloads({json.dumps(content)}) }})"
    )
    committed = (WEB / "public" / "_headers").read_text(encoding="utf-8")
    for page in ("/", "/poster"):
        want = built.split(f"\n{page}\n", 1)[1].split("\n", 1)[0]
        assert f"\n{page}\n{want}\n" in committed
        assert 'type="image/avif"' in want and "imagesrcset=" in want
        assert ".jpg" not in want
