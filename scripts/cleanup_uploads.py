"""Delete uploads older than 30 days: the database rows, their files, and any orphan file.

    uv run python scripts/cleanup_uploads.py [--days 30] [--dry-run]

Reads DATABASE_URL and UPLOAD_DIR the same way the API does. Prints counts only.
Run it daily from cron or the host's scheduler, beside scripts/backup_db.sh.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlmodel import Session, select

from apps.api.db import as_utc, engine
from apps.api.models import UploadRow
from apps.api.settings import settings


def cleanup(
    db: Session, upload_dir: Path, *, now: datetime, days: int = 30, dry_run: bool = False
) -> dict[str, int]:
    """Returns how many rows, files and orphan files were (or would be) removed."""
    cutoff = now - timedelta(days=days)
    rows = db.exec(select(UploadRow)).all()
    stale = [r for r in rows if (as_utc(r.created_at) or now) < cutoff]
    files_removed = 0
    for row in stale:
        path = upload_dir / row.file
        if path.is_file():
            files_removed += 1
            if not dry_run:
                path.unlink()
        if not dry_run:
            db.delete(row)
    if not dry_run:
        db.commit()
    known = {r.file for r in rows}
    orphans = 0
    if upload_dir.is_dir():
        for path in upload_dir.iterdir():
            if not path.is_file() or path.name in known:
                continue
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            if modified < cutoff:
                orphans += 1
                if not dry_run:
                    path.unlink()
    return {"rows": len(stale), "files": files_removed, "orphans": orphans}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    with Session(engine) as db:
        result = cleanup(
            db,
            Path(settings.upload_dir),
            now=datetime.now(UTC),
            days=args.days,
            dry_run=args.dry_run,
        )
    verb = "would remove" if args.dry_run else "removed"
    print(
        f"cleanup_uploads: {verb} {result['rows']} rows, {result['files']} files, "
        f"{result['orphans']} orphan files older than {args.days} days"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
