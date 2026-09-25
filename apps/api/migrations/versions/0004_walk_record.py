"""walk record

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-25

UPDATE_30 section 1 item 3. One additive table: a finished video walk's demo record, so its link
opens on any device, deleted 30 days after it is stored. Nothing that counts, maps or mirrors
creek checks reads it. Mirrors apps/api/models.py and worker/schema.sql.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "walk_record",
        sa.Column("record_id", sa.String(length=32), nullable=False),
        sa.Column("walk_id", sa.String(length=16), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answers_json", sa.Text(), nullable=False),
        sa.Column("bundle_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delete_after", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("record_id"),
    )
    op.create_index("ix_walk_record_created_at", "walk_record", ["created_at"])
    op.create_index("ix_walk_record_delete_after", "walk_record", ["delete_after"])


def downgrade() -> None:
    op.drop_index("ix_walk_record_delete_after", table_name="walk_record")
    op.drop_index("ix_walk_record_created_at", table_name="walk_record")
    op.drop_table("walk_record")
