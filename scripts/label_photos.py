"""A local page for labelling photos blind. One labeller, one file, nothing from anyone else.

Run: uv run python scripts/label_photos.py --name rachel --roles test,practice,lesson
It prints a http://127.0.0.1:<random port>/ link. The page shows one photo at a time with the
feature question from content/features.yaml and three buttons: present, absent, ambiguous.
Labels go to labels_<name>.csv in the repo root (gitignored). The page never opens, reads or
shows another labeller's file, and never shows the manifest's gold_label, notes or scene.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]{1,20}$")
LABELS = ("present", "absent", "ambiguous")
LABEL_COLUMNS = ["photo_id", "feature", "label", "labelled_at_utc"]
DEFAULT_ROLES = ("test", "practice", "lesson")


def labels_path(root: Path, name: str) -> Path:
    return root / f"labels_{name}.csv"


class LabelStore:
    """Read and write exactly one labels file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.rows: dict[str, dict[str, str]] = {}
        if path.exists():
            with path.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    self.rows[row["photo_id"]] = dict(row)

    def set(self, photo_id: str, feature: str, label: str) -> None:
        if label not in LABELS:
            raise ValueError(f"label must be one of {LABELS}")
        self.rows[photo_id] = {
            "photo_id": photo_id,
            "feature": feature,
            "label": label,
            "labelled_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with self.path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=LABEL_COLUMNS)
            w.writeheader()
            for pid in sorted(self.rows):
                w.writerow({c: self.rows[pid].get(c, "") for c in LABEL_COLUMNS})


def load_queue(root: Path, roles: tuple[str, ...]) -> list[dict[str, str]]:
    """Photos to label: id, file and feature only. Gold labels and notes are not read."""
    with (root / "photos" / "manifest.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    queue = [
        {"id": r["id"], "file": r["file"], "feature": r["feature"]}
        for r in rows
        if r["role"] in roles and r["feature"]
    ]
    return sorted(queue, key=lambda r: r["id"])


def load_questions(root: Path) -> dict[str, dict[str, str]]:
    with (root / "content" / "features.yaml").open(encoding="utf-8") as f:
        features = yaml.safe_load(f).get("features", [])
    return {f["id"]: {"name": f["name"], "question": f["question"]} for f in features}


def render(
    queue: list[dict[str, str]],
    store: LabelStore,
    questions: dict[str, dict[str, str]],
    name: str,
    photo_id: str | None,
) -> str:
    done = [p for p in queue if p["id"] in store.rows]
    todo = [p for p in queue if p["id"] not in store.rows]
    current = next((p for p in queue if p["id"] == photo_id), None) if photo_id else None
    if current is None:
        current = todo[0] if todo else None
    head = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Label photos: {html.escape(name)}</title>"
        "<style>body{font-family:system-ui;max-width:52rem;margin:1rem auto;padding:0 1rem}"
        "img{max-width:100%;height:auto;border:1px solid #888}"
        "button{font-size:1.25rem;padding:.75rem 1.5rem;margin:.5rem .5rem .5rem 0;min-width:9rem}"
        ".muted{color:#555}</style></head><body>"
    )
    parts = [head, f"<h1>Labelling as {html.escape(name)}</h1>"]
    parts.append(
        f"<p class='muted'>{len(done)} of {len(queue)} labelled. "
        f"Your labels go to {html.escape(store.path.name)} and nowhere else.</p>"
    )
    if current is None:
        parts.append("<p><strong>All done.</strong> Close this tab and run merge_labels.py.</p>")
    else:
        q = questions.get(current["feature"], {"name": current["feature"], "question": ""})
        parts.append(f"<h2>{html.escape(q['name'])}</h2>")
        parts.append(f"<p><strong>{html.escape(q['question'])}</strong></p>")
        parts.append(
            f"<p><img src='/photo/{html.escape(current['id'])}' alt='Creek photo to label'></p>"
        )
        parts.append("<form method='post' action='/label'>")
        parts.append(f"<input type='hidden' name='photo_id' value='{html.escape(current['id'])}'>")
        for label in LABELS:
            parts.append(f"<button type='submit' name='label' value='{label}'>{label}</button>")
        parts.append("</form>")
        parts.append(f"<p class='muted'>Photo id {html.escape(current['id'])}</p>")
    if done:
        links = " ".join(
            f"<a href='/?photo={html.escape(p['id'])}'>{html.escape(p['id'])}</a>" for p in done
        )
        parts.append(f"<p class='muted'>Change a label: {links}</p>")
    parts.append("</body></html>")
    return "".join(parts)


def make_server(
    root: Path, name: str, roles: tuple[str, ...] = DEFAULT_ROLES, port: int = 0
) -> ThreadingHTTPServer:
    if not NAME_RE.match(name):
        raise SystemExit("name must be 1 to 20 lowercase letters or digits, for example rachel")
    root = root.resolve()
    queue = load_queue(root, roles)
    questions = load_questions(root)
    store = LabelStore(labels_path(root, name))
    by_id = {p["id"]: p for p in queue}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return  # quiet; nothing here is worth logging

        def _send(self, status: HTTPStatus, body: bytes, ctype: str = "text/html") -> None:
            self.send_response(status)
            self.send_header(
                "Content-Type", f"{ctype}; charset=utf-8" if "text" in ctype else ctype
            )
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            url = urlparse(self.path)
            if url.path == "/":
                chosen = parse_qs(url.query).get("photo", [None])[0]
                page = render(queue, store, questions, name, chosen)
                self._send(HTTPStatus.OK, page.encode("utf-8"))
                return
            if url.path.startswith("/photo/"):
                photo = by_id.get(url.path[len("/photo/") :])
                if photo is None:
                    self._send(HTTPStatus.NOT_FOUND, b"no such photo", "text/plain")
                    return
                file = (root / "photos" / photo["file"]).resolve()
                if root / "photos" not in file.parents or not file.is_file():
                    self._send(HTTPStatus.NOT_FOUND, b"no such file", "text/plain")
                    return
                ctype = "image/png" if file.suffix.lower() == ".png" else "image/jpeg"
                self._send(HTTPStatus.OK, file.read_bytes(), ctype)
                return
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/label":
                self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")
                return
            length = int(self.headers.get("Content-Length") or 0)
            form = parse_qs(self.rfile.read(length).decode("utf-8"))
            photo_id = form.get("photo_id", [""])[0]
            label = form.get("label", [""])[0]
            photo = by_id.get(photo_id)
            if photo is None or label not in LABELS:
                self._send(HTTPStatus.BAD_REQUEST, b"unknown photo or label", "text/plain")
                return
            store.set(photo_id, photo["feature"], label)
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", "/")
            self.end_headers()

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", required=True, help="your first name, lowercase")
    parser.add_argument("--roles", default=",".join(DEFAULT_ROLES), help="comma separated roles")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    roles = tuple(r.strip() for r in args.roles.split(",") if r.strip())
    server = make_server(args.root, args.name, roles)
    host, port = str(server.server_address[0]), int(server.server_address[1])
    print(f"label page for {args.name}: http://{host}:{port}/  (Ctrl-C to stop)")
    print(f"labels are written to {labels_path(args.root.resolve(), args.name)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
