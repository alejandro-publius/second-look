"""Mirror our FHIR store to the shared OneAquaHealth sandbox (hard rule 10).

The store under data/fhir_store is the source of truth. Every stored visit becomes a transaction
Bundle of conditional creates with our meta.tag on every resource. Created ids are appended to
fhir/sandbox_ledger.jsonl (SANDBOX_LEDGER overrides the path for local servers). Deletes happen
only for one id named on the command line that appears in the ledger. Never by search, never
$expunge.

  uv run python scripts/repush_sandbox.py --dry-run          prints what would be sent, no network
  SANDBOX_MIRROR_ENABLED=true uv run python scripts/repush_sandbox.py
  SANDBOX_MIRROR_ENABLED=true uv run python scripts/repush_sandbox.py --delete-ledger-id 451
  SANDBOX_MIRROR_ENABLED=true uv run python scripts/repush_sandbox.py \
      --bundle fhir/golden/visit-strawberry-creek-1.json --library --evidence docs/notes/x.md

--bundle names one collection Bundle to mirror instead of the whole store. --library then
registers our Library entry (core/fhir_library.py), which describes the data set and points at the
repository and at every Provenance the ledger says we created here, and --evidence writes what came
back to a note, because anyone can delete records on a shared sandbox (Update 10 tier 2 item 1).
Only collection Bundles are mirrored: a transaction, a referral or an example is never sent.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx

from core.fhir_emit import to_transaction
from core.fhir_library import LIBRARY_ID, check_library, library_entry
from core.walks import is_demo

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


def _is_visit_bundle(data: object) -> bool:
    """A collection Bundle with one Provenance: a visit record. Nothing else is ever mirrored,
    so a transaction file, a referral, an example laboratory result or a demo walk cannot be sent
    by mistake."""
    if not isinstance(data, dict) or data.get("resourceType") != "Bundle":
        return False
    if data.get("type") != "collection":
        return False
    tags = data.get("meta", {}).get("tag", [])
    if any(t.get("code") == "example" for t in tags):
        return False
    # A video walk's record is a demo made on a phone. It is never stored, so never mirrored.
    if is_demo(data):
        return False
    types = [e.get("resource", {}).get("resourceType") for e in data.get("entry", [])]
    return types.count("Provenance") == 1 and "ServiceRequest" not in types


def load_bundles(store: Path, only: Sequence[Path] = ()) -> list[tuple[Path, dict[str, Any]]]:
    """Every visit Bundle in the store, or only the files named with --bundle."""
    paths: list[Path]
    if only:
        paths = [Path(p) for p in only]
    elif store.exists():
        paths = [p for p in sorted(store.glob("*.json")) if p.name != "index.json"]
    else:
        return []
    out: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        if _is_visit_bundle(data):
            out.append((path, data))
        elif only:
            raise RepushError(f"{path.name}: not a visit Bundle, refusing to mirror it")
    return out


def transactions(store: Path, only: Sequence[Path] = ()) -> list[tuple[Path, dict[str, Any]]]:
    return [
        (path, to_transaction(bundle, tag_system=repo_url(), tag_code=TAG_CODE))
        for path, bundle in load_bundles(store, only)
    ]


def describe(path: Path, tx: dict[str, Any]) -> list[str]:
    lines = [f"{path.name}: {len(tx['entry'])} conditional creates"]
    for entry in tx["entry"]:
        request = entry["request"]
        lines.append(f"  POST {request['url']} if none exist {request['ifNoneExist']}")
    return lines


def dry_run(store: Path, out: Callable[[str], None] = print, only: Sequence[Path] = ()) -> int:
    txs = transactions(store, only)
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
        append(
            "sandbox_push", payload, path=Path(os.environ.get("AUDIT_LOG_PATH", "audit/log.jsonl"))
        )
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
    only: Sequence[Path] = (),
    provenances: list[str] | None = None,
) -> int:
    """Mirror every visit Bundle. When `provenances` is a list, every Provenance this run created
    or found already there is appended to it as "Provenance/<id>", so the Library entry can list
    exactly what is on the server after this run (Update 10C answer 3)."""
    base = check_base(base)
    txs = transactions(store, only)
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
                if rtype == "Provenance" and provenances is not None:
                    provenances.append(f"Provenance/{rid}")
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


def created_provenances(base: str) -> list[str]:
    """ "Provenance/<id>" for every Provenance the ledger says we created on this server and
    never deleted, oldest first."""
    rows = read_ledger()
    deleted = {str(r["id"]) for r in rows if r.get("action") == "delete"}
    out: list[str] = []
    for r in rows:
        if r.get("action") != "create" or r.get("resourceType") != "Provenance":
            continue
        if r.get("base", base) != base or str(r["id"]) in deleted:
            continue
        ref = f"Provenance/{r['id']}"
        if ref not in out:
            out.append(ref)
    return out


def library_on_server(base: str) -> str | None:
    """The id of our Library on this server according to the ledger, or None."""
    found: str | None = None
    for r in read_ledger():
        if r.get("resourceType") != "Library" or r.get("base", base) != base:
            continue
        if r.get("action") in {"create", "exists", "update"}:
            found = str(r["id"])
        elif r.get("action") == "delete" and str(r.get("id")) == found:
            found = None
    return found


def register_library(
    base: str,
    *,
    today: date | None = None,
    sleep: Callable[[float], None] = time.sleep,
    out: Callable[[str], None] = print,
    evidence: Path | None = None,
    refs: Sequence[str] | None = None,
) -> int:
    """Register our Library entry, or update the one that is there, read it back, and write the
    evidence. `refs` are the Provenances the push just put on the server; without them the
    ledger's created and not deleted ones are used. The first time it is a conditional create.
    Every later time it is a conditional update on our own identifier, which can only match our
    own resource, so the count and the list follow each push (Update 10C answer 3)."""
    base = check_base(base)
    day = today or datetime.now(UTC).date()
    listed = list(refs) if refs is not None else created_provenances(base)
    library = library_entry(today=day, n_records=len(listed), provenance_refs=listed)
    problems = check_library(library)
    if problems:
        raise RepushError("library: " + "; ".join(problems))
    collection = {"resourceType": "Bundle", "type": "collection", "entry": [{"resource": library}]}
    tx = to_transaction(collection, tag_system=repo_url(), tag_code=TAG_CODE)
    tagged = dict(tx["entry"][0]["resource"])
    ident = library["identifier"][0]
    existing = library_on_server(base)
    with _client() as client:
        if existing is not None:
            # A conditional update by our identifier: PUT Library?identifier=system|value.
            url = f"{base}/Library?identifier={ident['system']}|{ident['value']}"
            response = client.put(url, content=json.dumps(tagged))
            if response.status_code not in {200, 201}:
                out(f"library: sandbox answered {response.status_code} to the update")
                out(response.text[:400])
                return 1
            body = response.json() if response.content else {}
            rid = str(body.get("id") or existing)
            rtype = "Library"
            action = "update"
        else:
            response = client.post(base, content=json.dumps(tx))
            if response.status_code != 200:
                out(f"library: sandbox answered {response.status_code}, nothing recorded")
                out(response.text[:400])
                return 1
            entry = (response.json().get("entry") or [{}])[0].get("response", {})
            parsed = _parse_location(str(entry.get("location", "")))
            if parsed is None:
                out("library: the sandbox gave no location back, nothing recorded")
                return 1
            rtype, rid = parsed
            action = "create" if str(entry.get("status", "")).startswith("201") else "exists"
        append_ledger(
            [
                {
                    "ts_utc": _now(),
                    "action": action,
                    "resourceType": rtype,
                    "id": rid,
                    "bundle": f"library:{LIBRARY_ID}",
                    "base": base,
                }
            ]
        )
        sleep(MIN_INTERVAL_SECONDS)
        back = client.get(f"{base}/{rtype}/{rid}")
    out(f"library: {action} {rtype}/{rid}, read back {back.status_code}, {len(listed)} records")
    _audit(
        {"base": base, "library": f"{rtype}/{rid}", "action": action, "provenances": len(listed)}
    )
    if evidence is not None:
        _write_evidence(evidence, base=base, ref=f"{rtype}/{rid}", action=action, back=back)
    return 0 if back.status_code == 200 else 1


def _write_evidence(path: Path, *, base: str, ref: str, action: str, back: httpx.Response) -> None:
    """What came back, saved at once, because anyone can delete records on a shared sandbox."""
    body: Any
    try:
        body = back.json()
    except ValueError:
        body = back.text[:2000]
    shown = json.dumps(body, indent=2, ensure_ascii=False) if not isinstance(body, str) else body
    screenshot = path.parent / "sandbox-library.png"
    shot = screenshot.relative_to(ROOT) if screenshot.is_relative_to(ROOT) else screenshot
    lines = [
        "# Sandbox evidence: the Library entry",
        "",
        f"Written by `scripts/repush_sandbox.py --library` at {_now()}. The ledger is",
        "`fhir/sandbox_ledger.jsonl`; every id below is in it.",
        "",
        f"- Server: `{base}`",
        f"- Library: `{ref}` ({action})",
        f"- Read back: HTTP {back.status_code}",
        f"- Screenshot: `{shot}`",
        f"- GET it yourself: `curl -H 'Accept: application/fhir+json' {base}/{ref}`",
        "",
        "## The Library as the sandbox returned it",
        "",
        "```json",
        shown,
        "```",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


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
    parser.add_argument(
        "--bundle",
        action="append",
        default=[],
        metavar="PATH",
        help="mirror this visit Bundle instead of the store (repeatable)",
    )
    parser.add_argument(
        "--library", action="store_true", help="then register our Library entry, or find it"
    )
    parser.add_argument(
        "--evidence", metavar="PATH", help="write what the sandbox returned for the Library here"
    )
    args = parser.parse_args(argv)
    store = Path(args.store)
    only = [Path(b) for b in args.bundle]
    try:
        if args.dry_run:
            return dry_run(store, only=only)
        if not mirror_enabled():
            print("mirror is off: set SANDBOX_MIRROR_ENABLED=true to push, or use --dry-run")
            return 2
        if args.delete_ledger_id:
            return delete_ledger_id(args.delete_ledger_id, args.base_url)
        seen: list[str] | None = None
        if only or not args.library:
            seen = []
            code = push(store, args.base_url, only=only, provenances=seen)
            if code != 0:
                return code
        if args.library:
            evidence = Path(args.evidence) if args.evidence else None
            return register_library(args.base_url, evidence=evidence, refs=seen)
        return 0
    except RepushError as exc:
        print(f"repush: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
