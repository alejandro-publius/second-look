"""Mirror our FHIR store to the shared OneAquaHealth sandbox (hard rule 10).

The store under data/fhir_store is the source of truth. Every stored visit becomes a transaction
Bundle of conditional creates with our meta.tag on every resource. Created ids are appended to
fhir/sandbox_ledger.jsonl (SANDBOX_LEDGER overrides the path for local servers). Deletes happen
only for one id named on the command line that appears in the ledger. Never by search, never
$expunge.

  uv run python scripts/repush_sandbox.py --dry-run          prints what would be sent, no network
  SANDBOX_MIRROR_ENABLED=true uv run python scripts/repush_sandbox.py
  SANDBOX_MIRROR_ENABLED=true uv run python scripts/repush_sandbox.py --delete-ledger-id 451
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from core.fhir_emit import to_transaction

ROOT = Path(__file__).resolve().parents[1]
LEDGER = Path(os.environ.get("SANDBOX_LEDGER") or ROOT / "fhir" / "sandbox_ledger.jsonl")
DEFAULT_STORE = ROOT / "data" / "fhir_store"
DEFAULT_BASE = "https://sandbox.hl7europe.eu/oneaquahealth/fhir"
DEFAULT_REPO_URL = "https://github.com/alejandro-publius/second-look"
TAG_CODE = "second-look"
FORBIDDEN_HOST = "api.enora-oah.eu"
MIN_INTERVAL_SECONDS = 1.0
TIMEOUT_SECONDS = 30.0


class RepushError(RuntimeError):
    pass


def repo_url() -> str:
    return os.environ.get("REPO_URL", DEFAULT_REPO_URL).rstrip("/")


def user_agent() -> str:
    return f"second-look (+{repo_url()})"


def load_bundles(store: Path) -> list[tuple[Path, dict[str, Any]]]:
    if not store.exists():
        return []
    out: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(store.glob("*.json")):
        if path.name == "index.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("resourceType") == "Bundle":
            out.append((path, data))
    return out


def transactions(store: Path) -> list[tuple[Path, dict[str, Any]]]:
    return [
        (path, to_transaction(bundle, tag_system=repo_url(), tag_code=TAG_CODE))
        for path, bundle in load_bundles(store)
    ]


def describe(path: Path, tx: dict[str, Any]) -> list[str]:
    lines = [f"{path.name}: {len(tx['entry'])} conditional creates"]
    for entry in tx["entry"]:
        request = entry["request"]
        lines.append(f"  POST {request['url']} if none exist {request['ifNoneExist']}")
    return lines


def dry_run(store: Path, out: Callable[[str], None] = print) -> int:
    txs = transactions(store)
    total = 0
    for path, tx in txs:
        for line in describe(path, tx):
            out(line)
        total += len(tx["entry"])
    tag = f"{repo_url()}|{TAG_CODE}"
    out(f"dry run: {len(txs)} bundle(s), {total} resource(s), tag {tag}, no network")
    return 0


def read_ledger() -> list[dict[str, Any]]:
    if not LEDGER.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def append_ledger(rows: Iterable[dict[str, Any]]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _audit(payload: dict[str, Any]) -> None:
    """Append a sandbox_push line to the audit log when W7's module exists."""
    try:
        from scripts.audit_log import append
    except ImportError:
        return
    try:
        append("sandbox_push", payload)
    except Exception as exc:  # noqa: BLE001  (the audit log must never block a mirror)
        print(f"audit log not written: {exc}", file=sys.stderr)


def check_base(base: str) -> str:
    base = base.rstrip("/")
    if FORBIDDEN_HOST in base:
        raise RepushError(f"refusing to call {FORBIDDEN_HOST} (hard rule 9)")
    if not base.startswith(("http://", "https://")):
        raise RepushError(f"base url must start with http:// or https://: {base}")
    return base


def mirror_enabled() -> bool:
    return os.environ.get("SANDBOX_MIRROR_ENABLED", "").strip().lower() == "true"


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=TIMEOUT_SECONDS,
        headers={
            "User-Agent": user_agent(),
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json",
        },
    )


def _parse_location(location: str) -> tuple[str, str] | None:
    """'Observation/12/_history/1' or a full URL -> ('Observation', '12')."""
    parts = [p for p in location.split("/") if p]
    if "_history" in parts:
        parts = parts[: parts.index("_history")]
    if len(parts) < 2:
        return None
    return parts[-2], parts[-1]


def push(
    store: Path,
    base: str,
    *,
    sleep: Callable[[float], None] = time.sleep,
    out: Callable[[str], None] = print,
) -> int:
    base = check_base(base)
    txs = transactions(store)
    if not txs:
        out("nothing to push: the store is empty")
        return 0
    created = 0
    matched = 0
    with _client() as client:
        for i, (path, tx) in enumerate(txs):
            if i:
                sleep(MIN_INTERVAL_SECONDS)
            response = client.post(base, content=json.dumps(tx))
            if response.status_code != 200:
                out(f"{path.name}: sandbox answered {response.status_code}, stopping")
                out(response.text[:400])
                return 1
            body = response.json()
            rows: list[dict[str, Any]] = []
            for entry in body.get("entry", []):
                resp = entry.get("response", {})
                status = str(resp.get("status", ""))
                parsed = _parse_location(str(resp.get("location", "")))
                if parsed is None:
                    continue
                rtype, rid = parsed
                action = "create" if status.startswith("201") else "exists"
                if action == "create":
                    created += 1
                else:
                    matched += 1
                rows.append(
                    {
                        "ts_utc": _now(),
                        "action": action,
                        "resourceType": rtype,
                        "id": rid,
                        "bundle": path.name,
                        "base": base,
                    }
                )
            append_ledger(rows)
            out(f"{path.name}: {len(rows)} resources, {created} created so far")
    _audit({"base": base, "bundles": len(txs), "created": created, "matched": matched})
    out(f"pushed {len(txs)} bundle(s): {created} created, {matched} already there")
    return 0


def delete_ledger_id(ledger_id: str, base: str, *, out: Callable[[str], None] = print) -> int:
    """Delete exactly one resource whose id was recorded as created in the ledger."""
    base = check_base(base)
    if "?" in ledger_id or "$" in ledger_id or "/" in ledger_id:
        raise RepushError("a ledger id is a plain id, not a search or an operation")
    rows = read_ledger()
    creates = [r for r in rows if r.get("action") == "create" and str(r.get("id")) == ledger_id]
    if not creates:
        raise RepushError(f"id {ledger_id} was never created by us according to the ledger")
    deleted = [r for r in rows if r.get("action") == "delete" and str(r.get("id")) == ledger_id]
    if deleted:
        raise RepushError(f"id {ledger_id} is already recorded as deleted")
    row = creates[-1]
    rtype = row["resourceType"]
    url = f"{base}/{rtype}/{ledger_id}"
    assert "?" not in url and "$" not in url
    with _client() as client:
        response = client.delete(url)
    ok = response.status_code in {200, 204}
    # A refused delete (for example 409 when another resource still points here) is recorded
    # as delete_failed so the id can be tried again later.
    append_ledger(
        [
            {
                "ts_utc": _now(),
                "action": "delete" if ok else "delete_failed",
                "resourceType": rtype,
                "id": ledger_id,
                "status": str(response.status_code),
                "base": base,
            }
        ]
    )
    out(f"DELETE {rtype}/{ledger_id}: {response.status_code}")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="print what would be sent")
    parser.add_argument("--store", default=str(DEFAULT_STORE), help="folder of visit Bundles")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SANDBOX_BASE_URL", DEFAULT_BASE),
        help="FHIR base url (default: the OneAquaHealth sandbox)",
    )
    parser.add_argument(
        "--delete-ledger-id", metavar="ID", help="delete this one id, which must be in the ledger"
    )
    args = parser.parse_args(argv)
    store = Path(args.store)
    try:
        if args.dry_run:
            return dry_run(store)
        if not mirror_enabled():
            print("mirror is off: set SANDBOX_MIRROR_ENABLED=true to push, or use --dry-run")
            return 2
        if args.delete_ledger_id:
            return delete_ledger_id(args.delete_ledger_id, args.base_url)
        return push(store, args.base_url)
    except RepushError as exc:
        print(f"repush: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
