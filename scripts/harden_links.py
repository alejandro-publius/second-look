"""Link check over README.md and the public docs/ for Update 16A section 4. Reports, never fixes.

Three kinds of reference are checked:

- relative links in Markdown, [text](path) and ![alt](path), resolved from the file that holds
  them, with #anchors checked against the headings of the target the way GitHub makes them;
- paths written in backticks that look like repo paths (docs/notes/sources.md), resolved from the
  repo root, because the README points at files that way;
- absolute http and https URLs, with one GET each (redirects followed).

Hosts we must not call are skipped and listed: api.enora-oah.eu and the Resilience Map API (hard
rule 9). The HL7 sandbox gets read-only GETs at most one a second and 50 in all (hard rule 10).
localhost and example addresses are skipped. Writes docs/internal/reviews/LINKS_00.md and
results/harden/links.json.

  uv run python scripts/harden_links.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

from scripts.go_public import INTERNAL

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("api.enora-oah.eu", "resilience")  # hard rule 9: never called, only listed
SANDBOX = "sandbox.hl7europe.eu"  # hard rule 10: read-only GETs, one a second, 50 at most
SANDBOX_CAP = 50
LOCAL = ("localhost", "127.0.0.1", "0.0.0.0", "example.org", "example.com", "example.net")
UA = "second-look-harden-links/1 (github.com/alejandro-publius/second-look)"
# FHIR canonicals and XML namespaces name things; nobody promised they resolve.
CANONICAL = (
    "http://hl7.org/fhir",
    "http://hl7.eu/fhir",
    "http://terminology.hl7.org",
    "http://snomed.info",
    "http://loinc.org",
    "http://unitsofmeasure.org",
    "http://www.w3.org/",
)
REPO = "https://github.com/alejandro-publius/second-look"

MD_LINK = re.compile(r"!?\[(?P<text>[^\]]*)\]\((?P<target><[^>]+>|[^)\s]+)(?:\s+\"[^\"]*\")?\)")
REF_DEF = re.compile(r"^\s*\[[^\]]+\]:\s+(?P<target>\S+)", re.M)
BARE_URL = re.compile(r"https?://[^\s<>()\[\]\"'`]+")
CODE_SPAN = re.compile(r"`([^`\n]+)`")
PATHLIKE = re.compile(r"^[A-Za-z0-9_.][A-Za-z0-9_./-]*/[A-Za-z0-9_.-]+/?$")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


@dataclass
class Ref:
    file: str
    line: int
    kind: str  # relative, backtick, url
    target: str
    in_code: bool


@dataclass
class Result:
    target: str
    kind: str
    status: str  # ok, dead, blocked, private, ignored, skipped
    detail: str


# What a reader of the public repository sees: go-public removes docs/internal, whose dated
# updates, reviews and reports cite files as they were on their day. The two live checklists are
# read too, because the loop works from them until the end.
LIVE_INTERNAL = ("docs/internal/DONE.md", "docs/internal/PLAN_TO_DONE.md")


def tracked_markdown() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "README.md", "docs"], cwd=ROOT, check=True, capture_output=True
    ).stdout.decode()
    return sorted(
        ROOT / p
        for p in out.split("\0")
        if p.endswith(".md") and (not p.startswith("docs/internal/") or p in LIVE_INTERNAL)
    )


def tracked_paths() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout.decode()
    files = {p for p in out.split("\0") if p}
    dirs = {str(Path(p).parent) for p in files}
    expanded = set(dirs)
    for d in dirs:
        parts = Path(d).parts
        expanded.update(str(Path(*parts[:i])) for i in range(1, len(parts)))
    return files | expanded


def github_slug(text: str) -> str:
    """The anchor GitHub gives a heading: lower case, punctuation dropped, spaces to hyphens."""
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors_of(path: Path) -> set[str]:
    seen: dict[str, int] = defaultdict(int)
    out: set[str] = set()
    fenced = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        m = None if fenced else HEADING.match(line)
        if not m:
            continue
        slug = github_slug(m.group(2))
        out.add(slug if seen[slug] == 0 else f"{slug}-{seen[slug]}")
        seen[slug] += 1
    return out


def collect(files: list[Path]) -> list[Ref]:
    refs: list[Ref] = []
    for path in files:
        rel = str(path.relative_to(ROOT))
        fenced = False
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            code_spans = CODE_SPAN.findall(line) if not fenced else []
            plain = CODE_SPAN.sub(" ", line) if not fenced else ""
            if not fenced:
                for m in MD_LINK.finditer(plain):
                    target = m.group("target").strip("<>")
                    kind = "url" if re.match(r"https?://", target) else "relative"
                    if target.startswith(("mailto:", "tel:")):
                        continue
                    refs.append(Ref(rel, n, kind, target, False))
                for m in REF_DEF.finditer(plain):
                    target = m.group("target")
                    kind = "url" if re.match(r"https?://", target) else "relative"
                    refs.append(Ref(rel, n, kind, target, False))
            linked = {r.target for r in refs if r.file == rel and r.line == n}
            for m in BARE_URL.finditer(line):
                url = m.group(0).rstrip(".,;:!?*_")
                if url not in linked:
                    refs.append(
                        Ref(rel, n, "url", url, fenced or any(url in c for c in code_spans))
                    )
            for span in code_spans:
                token = span.strip()
                if not PATHLIKE.match(token) or "://" in token or token.startswith(("../", "./")):
                    continue
                if token.split("/")[0] not in TOP_LEVEL:
                    continue
                refs.append(Ref(rel, n, "backtick", token, True))
    return refs


TOP_LEVEL: set[str] = set()


def check_relative(ref: Ref, known: set[str], anchor_cache: dict[str, set[str]]) -> Result:
    target, _, anchor = ref.target.partition("#")
    target = unquote(target.split("?")[0])
    base = (ROOT / ref.file).parent if ref.kind == "relative" else ROOT
    if not target:
        resolved = ROOT / ref.file
    else:
        resolved = (base / target).resolve()
    try:
        rel = str(resolved.relative_to(ROOT))
    except ValueError:
        return Result(ref.target, ref.kind, "dead", "points outside the repo")
    rel = rel.rstrip("/") or "."
    if rel not in known and rel != ".":
        ignored = any(
            subprocess.run(["git", "check-ignore", "-q", p], cwd=ROOT).returncode == 0
            for p in (rel, rel + "/")  # a folder pattern only matches with the slash
        )
        if ignored:
            return Result(
                ref.target, ref.kind, "ignored", f"{rel} is gitignored build or local data"
            )
        if resolved.exists():
            return Result(ref.target, ref.kind, "dead", f"{rel} exists here but is not tracked")
        return Result(ref.target, ref.kind, "dead", f"{rel} does not exist")
    if anchor and resolved.suffix == ".md" and resolved.is_file():
        if rel not in anchor_cache:
            anchor_cache[rel] = anchors_of(resolved)
        if anchor.lower() not in anchor_cache[rel]:
            return Result(ref.target, ref.kind, "dead", f"no heading #{anchor} in {rel}")
    return Result(ref.target, ref.kind, "ok", rel)


def repo_link(url: str) -> Result:
    """Our repo is private until Sep 30, so GitHub answers 404 to a script: check it in git."""
    rest = url[len(REPO) :].strip("/")
    if not rest:
        return Result(url, "url", "private", "our repo, private until Sep 30, so 404 to the public")
    m = re.match(r"(?:blob|tree)/([^/]+)/(.+)", rest)
    if not m:
        return Result(url, "url", "skipped", "a name under our repo address, not a page")
    ref, path = m.group(1), unquote(m.group(2).split("#")[0])
    for rev in (f"origin/{ref}", ref):
        if subprocess.run(["git", "cat-file", "-e", f"{rev}:{path}"], cwd=ROOT).returncode == 0:
            return Result(url, "url", "private", f"exists on {rev}; public from Sep 30")
    return Result(url, "url", "dead", f"{path} is not on {ref}")


# Hosts that are down for a cause outside this repository, named with the date and the evidence.
# A link to one is listed as blocked, not dead. Only a named host: a blanket rule for any name that
# does not resolve would hide a misspelled host.
OUTSIDE_DOWN = {
    "sandbox.hl7europe.eu": "the name does not resolve (NXDOMAIN at their own nameserver since "
    "2026-09-23; hl7-eu/oah issue 8)",
}


# Addresses that are a base, not a page, quoted inside a verbatim copy of a resource: the route
# needs an id after them. Listed by the full address, with where the route is.
BASES = {
    "https://second-look-api.thealexschroeder.workers.dev/api/fhir/Bundle": "a base inside the "
    "copy of our sandbox Library entry; the route is /api/fhir/Bundle/<visit id> "
    "(worker/src/index.ts)",
}


async def check_urls(urls: list[str]) -> dict[str, Result]:
    results: dict[str, Result] = {}
    todo: list[str] = []
    for url in urls:
        host = (urlparse(url).hostname or "").lower()
        if url.startswith(CANONICAL):
            results[url] = Result(url, "url", "skipped", "FHIR canonical or namespace, a name")
        elif url.startswith(REPO):
            results[url] = repo_link(url)
        elif any(f in host or f in url.lower() for f in FORBIDDEN):
            results[url] = Result(url, "url", "skipped", "hard rule 9: never called")
        elif host in LOCAL or host.endswith(".local"):
            results[url] = Result(url, "url", "skipped", "local or example address")
        elif url in BASES:
            results[url] = Result(url, "url", "skipped", BASES[url])
        elif "{" in url or "<" in url or host.isupper() or "SITE_URL" in url:
            results[url] = Result(url, "url", "skipped", "template, not a real address")
        else:
            todo.append(url)
    sandbox = [u for u in todo if SANDBOX in u]
    others = [u for u in todo if SANDBOX not in u]
    for url in sandbox[SANDBOX_CAP:]:
        results[url] = Result(url, "url", "skipped", f"hard rule 10: over {SANDBOX_CAP} GETs")
    sem = asyncio.Semaphore(8)
    per_host: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def one(client: httpx.AsyncClient, url: str) -> None:
        host = urlparse(url).hostname or ""
        async with sem, per_host[host]:
            try:
                r = await client.get(url)
                code = r.status_code
                if code < 400:
                    results[url] = Result(url, "url", "ok", str(code))
                elif code in (401, 403, 405, 406, 429, 999):
                    results[url] = Result(
                        url, "url", "blocked", f"{code}, the site refuses scripts"
                    )
                else:
                    results[url] = Result(url, "url", "dead", str(code))
            except httpx.HTTPError as exc:
                if host in OUTSIDE_DOWN:
                    results[url] = Result(url, "url", "blocked", OUTSIDE_DOWN[host])
                else:
                    results[url] = Result(url, "url", "dead", type(exc).__name__)

    headers = {"User-Agent": UA, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"}
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=headers) as client:
        await asyncio.gather(*(one(client, u) for u in others))
        for url in sandbox[:SANDBOX_CAP]:
            started = time.monotonic()
            await one(client, url)
            await asyncio.sleep(max(0.0, 1.1 - (time.monotonic() - started)))
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument(
        "--md", type=Path, default=ROOT / "docs" / "internal" / "reviews" / "LINKS_00.md"
    )
    ap.add_argument("--json", type=Path, default=ROOT / "results" / "harden" / "links.json")
    ap.add_argument("--no-network", action="store_true", help="check files and anchors only")
    args = ap.parse_args()

    known = tracked_paths()
    TOP_LEVEL.update(p for p in known if "/" not in p)
    files = tracked_markdown()
    refs = collect(files)
    anchor_cache: dict[str, set[str]] = {}
    local = {id(r): check_relative(r, known, anchor_cache) for r in refs if r.kind != "url"}
    urls = sorted({r.target for r in refs if r.kind == "url"})
    remote = {} if args.no_network else asyncio.run(check_urls(urls))

    rows = []
    for r in refs:
        res = local.get(id(r)) if r.kind != "url" else remote.get(r.target)
        if res is None:
            res = Result(r.target, r.kind, "skipped", "network off")
        rows.append({**asdict(r), "status": res.status, "detail": res.detail})
    count: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        count[row["kind"]][row["status"]] += 1
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(
            {"checked_utc": stamp, "commit": commit, "files": len(files), "rows": rows}, indent=1
        )
        + "\n",
        encoding="utf-8",
    )

    def table(status: str, internal: bool | None) -> list[str]:
        hit = [
            r
            for r in rows
            if r["status"] == status
            and (internal is None or r["file"].startswith(INTERNAL + "/") == internal)
        ]
        if not hit:
            return ["None.", ""]
        out = ["| File and line | Kind | Link | What happened |", "|---|---|---|---|"]
        for r in hit:
            where = " (in code)" if r["in_code"] and r["kind"] == "url" else ""
            target = r["target"].replace("|", "%7C")
            out.append(
                f"| {r['file']}:{r['line']} | {r['kind']}{where} | {target} | {r['detail']} |"
            )
        return [*out, ""]

    kinds = ("relative", "backtick", "url")
    statuses = ("ok", "dead", "blocked", "private", "ignored", "skipped")
    lines = [
        "# Link check 00",
        "",
        f"Checked {stamp} at commit {commit} by `uv run python scripts/harden_links.py`, over "
        f"README.md and every tracked Markdown file under docs/ ({len(files)} files). Nothing was "
        "fixed. Raw rows: `results/harden/links.json`.",
        "",
        "Relative links are resolved from the file that holds them and their #anchors are checked "
        "against the target's headings the way GitHub makes them. Paths in backticks are resolved "
        "from the repo root. Each web address got one GET with redirects followed. A site that "
        "answers 401, 403, 405, 429 or 999 to a script is listed as blocked, not dead: open it by "
        "hand. A path that git ignores (build output, local data) is listed as ignored, not dead. "
        "api.enora-oah.eu and the Resilience Map API were never called (hard rule 9); the HL7 "
        f"sandbox got at most one GET a second and {SANDBOX_CAP} in all (hard rule 10).",
        "",
        "## Counts",
        "",
        "| Kind | " + " | ".join(statuses) + " |",
        "|---|" + "---|" * len(statuses),
        *[f"| {k} | " + " | ".join(str(count[k][s]) for s in statuses) + " |" for k in kinds],
        "",
        "## Dead, in the README and product docs",
        "",
        *table("dead", False),
        "## Dead, in docs/internal (working notes)",
        "",
        *table("dead", True),
        "## Blocked, check by hand",
        "",
        *table("blocked", None),
        "## Skipped on purpose",
        "",
        *table("skipped", None),
    ]
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(
        f"{len(files)} files, {len(rows)} references: "
        + ", ".join(f"{s} {sum(count[k][s] for k in kinds)}" for s in statuses)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
