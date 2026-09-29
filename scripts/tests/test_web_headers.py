"""The landing page and the poster send their two photos as Early Hints (Link headers).

Pages wrote these headers itself from the pages' preload tags until the project gained the /api
Functions. After that the first screen on a throttled phone went from about 1.5 to 8.5 seconds.
Since Update 22 the two warm-up photos have smaller AVIF and WebP copies, and the header preloads
the AVIF set the page will use instead of the JPEG, so no phone downloads both.

The file that carries them, apps/web/public/_headers, is tracked, and Cloudflare Pages sends what
it says. So the tracked copy has to be the policy production sends: a test build once left its
mock API's local address in the committed policy line.
"""

from __future__ import annotations

import csv
import json
import os
import re
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
TRACKED = "apps/web/public/_headers"
# An address on this machine or on the local network, as a policy line would hold it.
LOCAL_ADDRESS = re.compile(
    r"(?:^|[/.\s])localhost(?=[:/;\s]|$)|\[::1\]|\b(?:127|10)\.\d+\.\d+\.\d+|\b0\.0\.0\.0\b"
    r"|\b192\.168\.\d+\.\d+|\b169\.254\.\d+\.\d+|\b172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+"
)

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


PERMISSIONS = (
    "  Permissions-Policy: geolocation=(self), camera=(self), microphone=(), payment=(), usb=()"
)


def test_every_page_allows_location_and_the_camera_for_our_own_origin_only() -> None:
    """CRITIC_09 R01: a permissions policy belongs to the page that was loaded, and a tap on a
    link inside the app loads none. With geolocation=() on every page but /check, a check opened
    from /judges could never find the phone's position. One policy for every page, the committed
    file included, and no page rule that changes it."""
    built = call("m.headersFile({ apiOrigin: '' })")
    committed = (WEB / "public" / "_headers").read_text(encoding="utf-8")
    for text in (built, committed):
        lines = [ln for ln in text.splitlines() if "Permissions-Policy" in ln]
        assert lines == [PERMISSIONS]
        every_page = text.split("\n/*\n", 1)[1].split("\n\n", 1)[0]
        assert PERMISSIONS in every_page.splitlines()


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


def tracked_copies() -> dict[str, str]:
    """The headers file as it is on disk and, in a git checkout, as the last commit holds it."""
    copies = {"the file on disk": (ROOT / TRACKED).read_text(encoding="utf-8")}
    if shutil.which("git") is not None:
        shown = subprocess.run(
            ["git", "show", f"HEAD:{TRACKED}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if shown.returncode == 0:
            copies["the copy in the last commit"] = shown.stdout
    return copies


def production_headers() -> str:
    """The headers file as scripts/deploy.sh builds it: an empty API origin, the real photos."""
    rows = manifest(ROOT / "photos" / "manifest.csv")
    derived = manifest(ROOT / "photos" / "derived" / "manifest.csv")
    warmup = yaml.safe_load((ROOT / "content" / "test_items.yaml").read_text(encoding="utf-8"))[
        "warmup"
    ]
    copies = call(f"m.derivedSources({json.dumps(rows)}, {json.dumps(derived)})", SOURCES)
    photos = {
        w["photo_id"]: {"url": f"/photos/{w['photo_id']}.jpg", **copies.get(w["photo_id"], {})}
        for w in warmup
    }
    content = {"warmup": warmup, "photos": photos}
    built: str = call(
        f"m.headersFile({{ apiOrigin: '', preloads: m.photoPreloads({json.dumps(content)}) }})"
    )
    return built


@pytest.mark.parametrize(
    ("origin", "local"),
    [
        ("", False),
        ("https://api.example", False),
        ("https://localhost.example.org", False),
        ("https://172.32.0.1", False),
        ("not an address", False),
        ("http://localhost:8000", True),
        ("http://127.0.0.1:8100", True),
        ("http://[::1]:8000", True),
        ("http://0.0.0.0:8000", True),
        ("http://app.localhost:3000", True),
        ("http://192.168.1.4:8000", True),
        ("http://10.0.0.2", True),
        ("http://172.16.0.1", True),
    ],
)
def test_an_address_on_this_machine_or_the_local_network_is_local(origin: str, local: bool) -> None:
    assert call(f"m.isLocalOrigin({json.dumps(origin)})") is local
    assert bool(LOCAL_ADDRESS.search(origin)) is local


def test_a_headers_file_is_never_built_for_a_local_address() -> None:
    for origin in ("http://127.0.0.1:8100", "http://localhost:8000"):
        err = fails(f"m.headersFile({{ apiOrigin: {json.dumps(origin)} }})")
        assert "is a local address" in err
    apart = call("m.headersFile({ apiOrigin: 'https://api.example' })")
    assert "connect-src 'self' https://api.example;" in apart


def test_the_tracked_headers_file_is_the_one_production_sends() -> None:
    """privacy-security-5: the committed policy line held connect-src 'self'
    http://127.0.0.1:8100, left by a test build, while production sent connect-src 'self'."""
    want = production_headers()
    policy = "  Content-Security-Policy: " + call("m.buildHeaders({ apiOrigin: '' }).csp")
    assert "connect-src 'self';" in policy
    for where, text in tracked_copies().items():
        found = LOCAL_ADDRESS.search(text)
        assert found is None, f"{where} holds the local address {found and found.group(0)}"
        assert policy in text.splitlines(), f"{where} does not hold production's policy line"
        assert text == want, f"{where} is not what a production build writes"


def build_headers_in_a_copy(tmp_path: Path, origin: str | None) -> tuple[str, str]:
    """Runs scripts/build-headers.mjs in a copy of the web folder, so the tracked file stays."""
    if shutil.which("node") is None:
        pytest.skip("needs node")
    web = tmp_path / "web"
    (web / "scripts").mkdir(parents=True)
    (web / "public").mkdir()
    for name in ("security-headers.mjs", "photo-sources.mjs", "scripts/build-headers.mjs"):
        shutil.copy(WEB / name, web / name)
    env = {k: v for k, v in os.environ.items() if k != "NEXT_PUBLIC_API_ORIGIN"}
    if origin is not None:
        env["NEXT_PUBLIC_API_ORIGIN"] = origin
    done = subprocess.run(
        ["node", "scripts/build-headers.mjs"],
        cwd=web,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return (web / "public" / "_headers").read_text(encoding="utf-8"), done.stdout


@pytest.mark.parametrize("origin", ["http://127.0.0.1:8100", "http://localhost:8000", None, ""])
def test_a_test_build_writes_the_policy_production_sends(
    tmp_path: Path, origin: str | None
) -> None:
    """make e2e builds with the mock API's address and a plain build with no address at all,
    which means localhost. Neither may change the tracked policy line."""
    text, said = build_headers_in_a_copy(tmp_path, origin)
    assert LOCAL_ADDRESS.search(text) is None
    assert "connect-src 'self';" in text
    assert "own origin only" in said


def test_a_build_for_an_api_on_another_host_names_it_in_the_policy(tmp_path: Path) -> None:
    text, said = build_headers_in_a_copy(tmp_path, "https://api.example/")
    assert "connect-src 'self' https://api.example;" in text
    assert "api origin https://api.example," in said
