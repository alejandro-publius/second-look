"""inaturalist cache

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-24

UPDATE_29 section 8. One additive table: a short summary of iNaturalist sightings near each
creek, stored by scripts/cache_inaturalist.py, for the context line on the record page and /city.
Mirrors apps/api/models.py and worker/schema.sql.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inaturalist_cache",
        sa.Column("creek", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("creek"),
    )


def downgrade() -> None:
    op.drop_table("inaturalist_cache")
