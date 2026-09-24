"""Seed a local demo database with made up creek checks, with no network and no key.

  uv run python scripts/seed_demo.py                 seeds data/demo, emptied first
  uv run python scripts/seed_demo.py --out DIR       seeds another folder
  make demo-offline                                  seeds, then serves the API and the site

What it makes, through the Python API's own routes in this process (no server, no socket): two
test sittings that answer every photo right and keep their score, one creek check each at the
Faculty Glade pin on Strawberry Creek reporting a built bank and a pipe running after a dry
week, and one quiet check with no score in Strawberry Creek Park, three reaches below. So the
city view has findings, a pipe worth testing with a referral, and a downstream note.

Everything here is demo data, in a folder of its own that git ignores. The sittings are marked
as tests by a QA key made for this run and thrown away, so they never count. The rain answer is
a fixed dry week, not Open-Meteo. The audit log line each record writes goes to the demo folder,
never to audit/log.jsonl. Nothing is mirrored anywhere.

No network: before the API is imported, every socket to anything but this machine is refused and
counted, and the script fails if one was tried. No key: ANTHROPIC_API_KEY is removed from the
environment first, and nothing here calls a model.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import socket
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "demo"
KEY_NAMES = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "0.0.0.0", ""}
SEEDED_AT = datetime(2026, 9, 25, 15, 0, tzinfo=UTC)

# Pins the person placed, so they are kept as given rather than rounded to about a kilometre.
FACULTY_GLADE = {
    "new": {
        "name": "Faculty Glade bridge",
        "latitude": 37.8716,
        "longitude": -122.256,
        "coarse": False,
    }
}
PARK = {
    "new": {
        "name": "Daylighted reach in the park",
        "latitude": 37.8666,
        "longitude": -122.2885,
        "coarse": False,
    }
}
REPORTED = {
    "channel_form": "u_shape",
    "bank_type": "present",
    "draining_pipes": "present",
    "water_flow": "slow",
    "habitats": ["riffles", "sand_banks"],
    "water_height_m": 0.3,
    "invasive_species": "absent",
    "feelings": ["joy:4", "fear:not_applicable"],
    "overall_rating": "good",
}
QUIET = {**REPORTED, "bank_type": "absent", "draining_pipes": "absent"}


class NetworkRefused(OSError):
    """A socket to another machine, refused on purpose."""


class NoNetwork:
    """Refuses every connection and name lookup that leaves this machine, and counts them."""

    def __init__(self) -> None:
        self.tried: list[str] = []
        self._connect: Callable[..., Any] | None = None
        self._connect_ex: Callable[..., Any] | None = None
        self._getaddrinfo: Callable[..., Any] | None = None

    def _local(self, host: object) -> bool:
        return str(host) in LOCAL_HOSTS

    def install(self) -> None:
        guard = self
        self._connect = socket.socket.connect
        self._connect_ex = socket.socket.connect_ex
        self._getaddrinfo = socket.getaddrinfo
        real_connect, real_connect_ex, real_lookup = (
            self._connect,
            self._connect_ex,
            self._getaddrinfo,
        )

        def check(sock: socket.socket, address: Any) -> None:
            if sock.family == socket.AF_UNIX:
                return
            host = address[0] if isinstance(address, tuple) and address else address
            if not guard._local(host):
                guard.tried.append(f"connect {host}")
                raise NetworkRefused(f"seed_demo: no network, refused a connection to {host}")

        def connect(sock: socket.socket, address: Any) -> Any:
            check(sock, address)
            return real_connect(sock, address)

        def connect_ex(sock: socket.socket, address: Any) -> Any:
            check(sock, address)
            return real_connect_ex(sock, address)

        def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
            if not guard._local(host if not isinstance(host, bytes) else host.decode()):
                guard.tried.append(f"lookup {host!r}")
                raise NetworkRefused(f"seed_demo: no network, refused a lookup of {host!r}")
            return real_lookup(host, *args, **kwargs)

        setattr(socket.socket, "connect", connect)  # noqa: B010
        setattr(socket.socket, "connect_ex", connect_ex)  # noqa: B010
        setattr(socket, "getaddrinfo", getaddrinfo)  # noqa: B010

    def remove(self) -> None:
        if self._connect is not None:
            setattr(socket.socket, "connect", self._connect)  # noqa: B010
        if self._connect_ex is not None:
            setattr(socket.socket, "connect_ex", self._connect_ex)  # noqa: B010
        if self._getaddrinfo is not None:
            setattr(socket, "getaddrinfo", self._getaddrinfo)  # noqa: B010


def demo_environment(out: Path, qa_key: str) -> dict[str, str]:
    """What the API reads at import, all pointed into the demo folder."""
    return {
        "DATABASE_URL": f"sqlite:///{out / 'demo.db'}",
        "FHIR_STORE_DIR": str(out / "fhir_store"),
        "UPLOAD_DIR": str(out / "uploads"),
        "AUDIT_LOG_PATH": str(out / "audit.jsonl"),
        "SANDBOX_CACHE_DIR": str(out / "sandbox_cache"),
        "QA_KEY": qa_key,
        "EXPORT_TOKEN": "",
        "RANDOMIZATION_SEED": "demo-offline",
        "BUILD_HASH": "demo",
        "CHECKER_ENABLED": "false",
        "SANDBOX_MIRROR_ENABLED": "false",
    }


def seed(out: Path) -> dict[str, Any]:
    """Make the demo records in out. Call only in a fresh process: settings are read once."""
    qa_key = secrets.token_hex(16)
    os.environ.update(demo_environment(out, qa_key))

    from fastapi.testclient import TestClient

    from apps.api import content, core_calls, deps
    from apps.api.main import app

    def dry_week(*_a: object, **_k: object) -> core_calls.RainView:
        return core_calls.RainView(status="dry", mm_in_window=0.0, dry_days=7, source="demo")

    core_calls.rain_status = dry_week
    app.dependency_overrides[deps.get_now] = lambda: SEEDED_AT
    qa = {"x-qa-key": qa_key}

    def sitting(client: TestClient) -> str:
        """A sitting that answers every photo right, marked as a test, keeping its score."""
        body = {
            "consent_version": "demo",
            "client_token_hash": secrets.token_hex(16),
            "source_label": "other",
            "ua_class": "desktop",
        }
        made = client.post("/api/test/session", json=body, headers=qa)
        made.raise_for_status()
        sid = made.json()["session_id"]
        for position, item_id in enumerate(made.json()["item_order"]):
            answer = "yes" if content.gold_for(item_id) == "present" else "no"
            client.post(
                "/api/test/response",
                json={
                    "session_id": sid,
                    "item_id": item_id,
                    "answer": answer,
                    "rt_ms": 1500,
                    "position": position,
                },
            ).raise_for_status()
        done = client.post("/api/test/complete", json={"session_id": sid, "keep_score": True})
        done.raise_for_status()
        return str(done.json()["contributor_token"])

    def visit(client: TestClient, token: str | None, spot: dict[str, Any], answers: dict) -> dict:
        body: dict[str, Any] = {
            "spot": spot,
            "answers": answers,
            "first_rating": "good",
            "photo_ids": [],
        }
        if token:
            body["contributor_token"] = token
        draft = client.post("/api/check/draft", json=body)
        draft.raise_for_status()
        asked = {f["rule_id"] for f in draft.json()["followups"]}
        done = client.post(
            "/api/check/finalize",
            json={
                "draft_id": draft.json()["draft_id"],
                "followup_answers": {"dry_pipe": "yes"} if "dry_pipe" in asked else {},
                "final_rating": "good",
            },
        )
        done.raise_for_status()
        return dict(done.json())

    with TestClient(app) as client:
        first = visit(client, sitting(client), FACULTY_GLADE, REPORTED)
        second = visit(client, sitting(client), {"spot_id": first["spot_id"]}, REPORTED)
        quiet = visit(client, None, PARK, QUIET)
        city = client.get("/api/city/strawberry-creek").json()
        counts = client.get("/api/test/counts").json()
    return {
        "made_by": "scripts/seed_demo.py",
        "demo": True,
        "visits": [first["visit_id"], second["visit_id"], quiet["visit_id"]],
        "spots": {"faculty_glade": first["spot_id"], "park": quiet["spot_id"]},
        "city_visits": city["visits"],
        "pipes_worth_testing": len(city["pipes_worth_testing"]),
        "sittings_counted": sum(arm["randomized"] for arm in counts["by_arm"].values()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="the demo folder")
    args = parser.parse_args(argv)
    out = args.out.resolve()
    # The folder is emptied first, so it must be one this script made, or new, or empty.
    if out == ROOT or out in ROOT.parents or out == Path(out.anchor):
        print(f"seed-demo: refusing to empty {out}", file=sys.stderr)
        return 2
    if out.exists() and any(out.iterdir()) and not (out / "SEEDED.json").exists():
        print(
            f"seed-demo: {out} holds files this script did not make; pick another", file=sys.stderr
        )
        return 2
    for name in KEY_NAMES:
        os.environ.pop(name, None)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    guard = NoNetwork()
    guard.install()
    try:
        made = seed(out)
    except NetworkRefused as exc:
        print(f"seed-demo: {exc}", file=sys.stderr)
        return 1
    finally:
        guard.remove()
    if guard.tried:
        print(f"seed-demo: tried the network: {', '.join(guard.tried)}", file=sys.stderr)
        return 1
    made["network_attempts"] = 0
    (out / "SEEDED.json").write_text(json.dumps(made, indent=2) + "\n", encoding="utf-8")
    print(
        f"seed-demo: {len(made['visits'])} demo visits on Strawberry Creek in {out}, "
        f"{made['pipes_worth_testing']} pipe worth testing, no network used"
    )
    print(f"seed-demo: the record at /spot?id={made['spots']['faculty_glade']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
