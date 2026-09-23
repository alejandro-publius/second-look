"""Load test for Update 16A section 4: 50 sessions a minute for 5 minutes, p50 and p95 per endpoint.

Two targets, never the study endpoints in production:

- local: a wrangler dev of the Worker on a port from 8900 to 8999, with a fresh local D1 kept in a
  folder outside the repo. Each session is the whole two-minute test the way the browser drives it
  (session, the lesson for the trained arm, 16 answers, complete) plus the read endpoints.
- live: the production landing page and the API's read endpoints, GET only. /api/two is left out
  because a GET there can write its cache row to D1, and every /api/test/ route is left out.

Arrivals are open loop: session i starts at i times 60 / rate seconds whatever the server does, so a
slow answer shows up as latency and not as a lower rate.

  uv run python scripts/harden_load.py --target local --state /tmp/some/folder
  uv run python scripts/harden_load.py --target live
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import random
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "worker"
WRANGLER_CLI = WORKER / "node_modules" / "wrangler" / "wrangler-dist" / "cli.js"
SITE = "https://second-look-79t.pages.dev"
API = "https://second-look-api.thealexschroeder.workers.dev"
LIVE_READS = [(SITE, "/"), (API, "/health"), (API, "/api/content/hash")]
LOCAL_READS = ["/health", "/api/content/hash", "/api/creeks", "/api/fhir/validation", "/api/two"]
CLOSED = "http://127.0.0.1:9"  # nothing listens here, so rain and the sandbox fail closed at once
WRANGLER_ENV = {
    **os.environ,
    "CI": "true",
    "WRANGLER_SEND_METRICS": "false",
    "NO_UPDATE_NOTIFIER": "1",
    "FORCE_COLOR": "0",
}


@dataclass
class Sample:
    target: str
    endpoint: str
    status: int
    ms: float
    error: str = ""


@dataclass
class Run:
    samples: list[Sample] = field(default_factory=list)
    sessions_started: int = 0
    sessions_done: int = 0
    session_errors: list[str] = field(default_factory=list)


def percentile(values: list[float], q: float) -> float:
    """Nearest rank percentile, so p95 is a latency somebody actually waited."""
    if not values:
        return float("nan")
    ordered = sorted(values)
    rank = max(1, min(len(ordered), round(q / 100 * len(ordered) + 0.5)))
    return ordered[rank - 1]


async def timed(
    client: httpx.AsyncClient,
    run: Run,
    target: str,
    endpoint: str,
    method: str,
    url: str,
    **kw: Any,
) -> httpx.Response | None:
    start = time.perf_counter()
    try:
        response = await client.request(method, url, **kw)
    except httpx.HTTPError as exc:
        ms = (time.perf_counter() - start) * 1000
        run.samples.append(Sample(target, endpoint, 0, ms, type(exc).__name__))
        return None
    ms = (time.perf_counter() - start) * 1000
    run.samples.append(Sample(target, endpoint, response.status_code, ms))
    return response


async def local_session(
    client: httpx.AsyncClient, run: Run, base: str, i: int, think: tuple[float, float]
) -> None:
    content = json.loads((WORKER / "src" / "content.json").read_text(encoding="utf-8"))
    rng = random.Random(20260922 + i)

    async def pause() -> None:
        await asyncio.sleep(rng.uniform(*think))

    run.sessions_started += 1
    for path in ("/health", "/api/content/hash"):
        await timed(client, run, "local", f"GET {path}", "GET", base + path)
    created = await timed(
        client,
        run,
        "local",
        "POST /api/test/session",
        "POST",
        base + "/api/test/session",
        json={
            "consent_version": "v1",
            "content_hash": content["content_hash"],
            "build_hash": "load",
            "source_label": "other",
            "hidden_field": "",
            "client_token_hash": f"load-{i:04d}-{rng.getrandbits(64):016x}",
            "ua_class": "phone",
            "warmup_choice": content["warmup_ids"][rng.randrange(2)],
        },
    )
    if created is None or created.status_code != 200:
        run.session_errors.append(
            f"session {i}: create {created.status_code if created else 'no answer'}"
        )
        return
    body = created.json()
    sid = body["session_id"]
    if body.get("lesson_first"):
        await pause()
        await timed(
            client,
            run,
            "local",
            "POST /api/test/lesson-done",
            "POST",
            base + "/api/test/lesson-done",
            json={"session_id": sid, "lesson_seconds": {"bank": 9.5, "channel": 8.0}},
        )
    for position, item_id in enumerate(body["item_order"]):
        await pause()
        r = await timed(
            client,
            run,
            "local",
            "POST /api/test/response",
            "POST",
            base + "/api/test/response",
            json={
                "session_id": sid,
                "item_id": item_id,
                "answer": rng.choice(["yes", "no", "cant_tell"]),
                "rt_ms": rng.randint(700, 6000),
                "position": position,
            },
        )
        if r is None or r.status_code != 200:
            run.session_errors.append(
                f"session {i}: response {r.status_code if r else 'no answer'}"
            )
    done = await timed(
        client,
        run,
        "local",
        "POST /api/test/complete",
        "POST",
        base + "/api/test/complete",
        json={
            "session_id": sid,
            "prior_experience": "no",
            "keep_score": False,
            "answered_count": len(body["item_order"]),
        },
    )
    if done is None or done.status_code != 200:
        run.session_errors.append(
            f"session {i}: complete {done.status_code if done else 'no answer'}"
        )
        return
    await timed(client, run, "local", "GET /api/test/counts", "GET", base + "/api/test/counts")
    for path in LOCAL_READS[2:]:
        await timed(client, run, "local", f"GET {path}", "GET", base + path)
    run.sessions_done += 1


async def live_session(
    client: httpx.AsyncClient, run: Run, i: int, think: tuple[float, float]
) -> None:
    rng = random.Random(20260922 + i)
    run.sessions_started += 1
    for origin, path in LIVE_READS:
        name = f"GET {'site' if origin == SITE else 'api'} {path}"
        r = await timed(client, run, "live", name, "GET", origin + path)
        if r is None or r.status_code != 200:
            run.session_errors.append(f"session {i}: {name} {r.status_code if r else 'no answer'}")
        await asyncio.sleep(rng.uniform(*think))
    run.sessions_done += 1


async def drive(
    target: str, rate: float, minutes: float, base: str, think: tuple[float, float]
) -> tuple[Run, float]:
    run = Run()
    total = int(round(rate * minutes))
    gap = 60.0 / rate
    limits = httpx.Limits(max_connections=400, max_keepalive_connections=100)
    headers = {"User-Agent": "second-look-harden-load/1 (github.com/alejandro-publius/second-look)"}
    async with httpx.AsyncClient(timeout=30.0, limits=limits, headers=headers) as client:
        t0 = time.perf_counter()
        tasks = []
        for i in range(total):
            delay = t0 + i * gap - time.perf_counter()
            if delay > 0:
                await asyncio.sleep(delay)
            if target == "local":
                tasks.append(asyncio.create_task(local_session(client, run, base, i, think)))
            else:
                tasks.append(asyncio.create_task(live_session(client, run, i, think)))
        await asyncio.gather(*tasks)
        return run, time.perf_counter() - t0


def wrangler(args: list[str]) -> None:
    subprocess.run(
        ["node", "--no-warnings", str(WRANGLER_CLI), *args],
        cwd=WORKER,
        env=WRANGLER_ENV,
        check=True,
        capture_output=True,
        timeout=300,
    )


def start_local(port: int, state: Path) -> subprocess.Popen[bytes]:
    if not WRANGLER_CLI.exists():
        raise SystemExit("worker/node_modules is missing: run npm ci in worker/ first")
    if ROOT in state.resolve().parents or state.resolve() == ROOT:
        raise SystemExit("--state must be outside the repo")
    if not 8900 <= port <= 8999:
        raise SystemExit(
            "--port must be from 8900 to 8999, so it never meets another session's server"
        )
    persist = state / "wrangler"
    subprocess.run(["rm", "-rf", str(persist)], check=True)
    for extra in (
        ["--file", "schema.sql"],
        ["--file", "arms.sql"],
        ["--command", "INSERT OR IGNORE INTO counter (id, next_position) VALUES (1, 0)"],
    ):
        wrangler(["d1", "execute", "second-look", "--local", "--persist-to", str(persist), *extra])
    log = (state / "wrangler-dev.log").open("wb")
    proc = subprocess.Popen(
        [
            "node",
            "--no-warnings",
            str(WRANGLER_CLI),
            "dev",
            "--local",
            "--port",
            str(port),
            "--persist-to",
            str(persist),
            "--compatibility-date",
            "2026-08-18",
            "--var",
            f"RAIN_URL:{CLOSED}/v1/forecast",
            "--var",
            f"SANDBOX_BASE_URL:{CLOSED}/fhir",
            "--show-interactive-dev-session=false",
        ],
        cwd=WORKER,
        env=WRANGLER_ENV,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    base = f"http://127.0.0.1:{port}"
    end = time.time() + 120
    while time.time() < end:
        try:
            if httpx.get(base + "/health", timeout=2).status_code == 200:
                return proc
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    stop_local(proc)
    raise SystemExit(
        f"wrangler dev did not answer on {base} in 120 s; see {state}/wrangler-dev.log"
    )


def stop_local(proc: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=20)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def summarise(run: Run, seconds: float, target: str, rate: float, minutes: float) -> dict[str, Any]:
    by: dict[str, list[Sample]] = {}
    for s in run.samples:
        by.setdefault(s.endpoint, []).append(s)
    rows = []
    for endpoint in sorted(by):
        got = by[endpoint]
        ok = [s.ms for s in got if 200 <= s.status < 400]
        statuses: dict[str, int] = {}
        for s in got:
            key = s.error or str(s.status)
            statuses[key] = statuses.get(key, 0) + 1
        rows.append(
            {
                "endpoint": endpoint,
                "requests": len(got),
                "ok": len(ok),
                "statuses": statuses,
                "p50_ms": round(percentile(ok, 50), 1),
                "p95_ms": round(percentile(ok, 95), 1),
                "p99_ms": round(percentile(ok, 99), 1),
                "max_ms": round(max(ok), 1) if ok else None,
            }
        )
    return {
        "target": target,
        "rate_sessions_per_minute": rate,
        "minutes": minutes,
        "wall_seconds": round(seconds, 1),
        "sessions_started": run.sessions_started,
        "sessions_done": run.sessions_done,
        "requests": len(run.samples),
        "session_errors": run.session_errors[:50],
        "session_error_count": len(run.session_errors),
        "endpoints": rows,
    }


def render(out: Path) -> Path:
    """results/harden/load.md from whichever of load_local.json and load_live.json exist."""
    parts = []
    for target in ("local", "live"):
        path = out / f"load_{target}.json"
        if path.exists():
            parts.append(json.loads(path.read_text(encoding="utf-8")))
    lines = [
        "# Load test",
        "",
        "Made by `uv run python scripts/harden_load.py`. Arrivals are open loop at the rate "
        "below: session i starts at i times 60 / rate seconds whatever the server does, so a "
        "slow answer shows as latency, not as a lower rate. p50 and p95 are nearest rank over "
        "the requests that got a 2xx or 3xx answer; the answers column counts every answer.",
        "",
        "- local: `wrangler dev --local` of the Worker on this Mac, a fresh local D1, rain and the "
        "sandbox pointed at a closed port so they fail closed at once. Each session is the whole "
        "two-minute test the way the browser drives it (session, the lesson for the trained arm, "
        "16 answers with a pause of a few seconds before each, complete) plus the read endpoints. "
        "Local numbers measure the code and D1 in miniflare, not Cloudflare's edge.",
        "- live: production, GET only: the landing page and the API's read endpoints. Every "
        "/api/test/ route is left out, and so is /api/two, because a GET there can write its "
        "cache row to D1. Nothing was written to production.",
        "",
    ]
    for s in parts:
        lines += [
            f"## {s['target']}",
            "",
            f"{s['rate_sessions_per_minute']:g} sessions a minute for {s['minutes']:g} minutes: "
            f"{s['sessions_done']} of {s['sessions_started']} sessions finished, "
            f"{s['requests']} requests in {s['wall_seconds']} s, "
            f"{s['session_error_count']} session errors. Pause between steps "
            f"{s['think_seconds'][0]:g} to {s['think_seconds'][1]:g} s. Finished "
            f"{s['finished_utc']} on {s['machine']}.",
            "",
            "| Endpoint | Requests | p50 ms | p95 ms | p99 ms | Max ms | Answers |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in s["endpoints"]:
            answers = ", ".join(f"{k}: {v}" for k, v in sorted(r["statuses"].items()))
            lines.append(
                f"| {r['endpoint']} | {r['requests']} | {r['p50_ms']} | {r['p95_ms']} | "
                f"{r['p99_ms']} | {r['max_ms']} | {answers} |"
            )
        if s["session_errors"]:
            lines += ["", "First session errors:", ""]
            lines += [f"- {e}" for e in s["session_errors"][:10]]
        lines.append("")
    md = out / "load.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    return md


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--target", choices=["local", "live"])
    ap.add_argument("--rate", type=float, default=50.0, help="sessions started per minute")
    ap.add_argument("--minutes", type=float, default=5.0)
    ap.add_argument("--port", type=int, default=8950)
    ap.add_argument("--state", type=Path, help="local only: a folder outside the repo for D1 state")
    ap.add_argument("--think", type=float, nargs=2, default=None, help="seconds between steps")
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "harden")
    ap.add_argument("--render-only", action="store_true", help="rewrite load.md from the JSON")
    args = ap.parse_args()
    if args.render_only:
        print(f"wrote {render(args.out)}")
        return 0
    if args.target is None:
        raise SystemExit("--target is required unless --render-only")
    think = (
        tuple(args.think) if args.think else ((2.0, 4.0) if args.target == "local" else (0.5, 1.5))
    )

    proc = None
    base = ""
    if args.target == "local":
        if args.state is None:
            raise SystemExit("--state is required for --target local")
        args.state.mkdir(parents=True, exist_ok=True)
        proc = start_local(args.port, args.state)
        base = f"http://127.0.0.1:{args.port}"
    try:
        run, seconds = asyncio.run(drive(args.target, args.rate, args.minutes, base, think))
    finally:
        if proc is not None:
            stop_local(proc)
    summary = summarise(run, seconds, args.target, args.rate, args.minutes)
    summary["think_seconds"] = list(think)
    summary["machine"] = f"{platform.system()} {platform.release()}, {os.cpu_count()} CPUs"
    summary["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"load_{args.target}.json"
    path.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(
        f"{args.target}: {summary['sessions_done']} of {summary['sessions_started']} sessions "
        f"done, {summary['requests']} requests in {summary['wall_seconds']} s, "
        f"{summary['session_error_count']} session errors; wrote {path}"
    )
    render(args.out)
    for row in summary["endpoints"]:
        print(
            f"  {row['endpoint']:<32} n={row['requests']:<5} p50={row['p50_ms']} ms  "
            f"p95={row['p95_ms']} ms  {row['statuses']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
