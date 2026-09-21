"""Repo-wide test setup: no test may write the real audit chain or the real sandbox ledger."""

from __future__ import annotations

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="second-look-tests-")
os.environ.setdefault("AUDIT_LOG_PATH", os.path.join(_TMP, "audit.jsonl"))
os.environ.setdefault("SANDBOX_LEDGER", os.path.join(_TMP, "ledger.jsonl"))
