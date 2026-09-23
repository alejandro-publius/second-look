"""The landing page and the poster send their two photos as Early Hints (Link headers).

Pages wrote these headers itself from the pages' preload tags until the project gained the /api
Functions. After that the first screen on a throttled phone went from about 1.5 to 8.5 seconds.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "apps" / "web" / "security-headers.mjs"

CONTENT = {
    "warmup": [{"photo_id": "a"}, {"photo_id": "b"}, {"photo_id": "c"}],
    "photos": {k: {"url": f"/photos/{k}.jpg"} for k in "abc"},
}


def call(expr: str) -> Any:
    if shutil.which("node") is None:
        pytest.skip("needs node")
    body = (
        f"const m = await import({json.dumps(MODULE.as_uri())});\n"
        f"process.stdout.write(JSON.stringify({expr}));"
    )
    done = subprocess.run(
        ["node", "--input-type=module", "-e", body],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_the_first_two_warmup_photos_are_preloaded_on_the_landing_page_and_the_poster() -> None:
    urls = ["/photos/a.jpg", "/photos/b.jpg"]
    assert call(f"m.photoPreloads({json.dumps(CONTENT)})") == {"/": urls, "/poster": urls}
    assert call("m.photoPreloads({})") == {}


def test_the_headers_file_carries_one_link_header_per_page() -> None:
    text = call(
        f"m.headersFile({{ apiOrigin: '', preloads: m.photoPreloads({json.dumps(CONTENT)}) }})"
    )
    link = "  Link: </photos/a.jpg>; rel=preload; as=image, </photos/b.jpg>; rel=preload; as=image"
    assert f"/\n{link}\n" in text
    assert f"/poster\n{link}\n" in text
    assert "c.jpg" not in text
