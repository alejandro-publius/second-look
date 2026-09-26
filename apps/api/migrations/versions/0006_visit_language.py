"""visit language

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-26

UPDATE_32 section 2. One additive column: the language a creek check's questions were shown in,
which its QuestionnaireResponse states. Empty on older rows, which read as English. Mirrors
apps/api/models.py, worker/schema.sql and worker/migrations/0001_visit_language.sql.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("visit") as batch:
        batch.add_column(sa.Column("language", sa.String(length=8), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("visit") as batch:
        batch.drop_column("language")
