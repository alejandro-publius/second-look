"""walk checks

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-25

Judge walk W01. One additive table: the follow-up checks a finished video walk ran and its final
rating, one row per walk record, stored with it and deleted with it. Mirrors apps/api/models.py
and worker/schema.sql.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "walk_checks",
        sa.Column("record_id", sa.String(length=32), nullable=False),
        sa.Column("final_rating", sa.String(length=16), nullable=True),
        sa.Column("checks_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("record_id"),
    )


def downgrade() -> None:
    op.drop_table("walk_checks")
