#!/usr/bin/env bash
# Kept so a launchd job installed before UPDATE_30 still does the right thing: the re-push is now
# scripts/sandbox_retry.py, run daily at 08:00 by `make mac-jobs-install` (scripts/mac_jobs.py).
# It retries their sandbox every day and pushes only when the sandbox's name resolves.
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run python scripts/sandbox_retry.py
