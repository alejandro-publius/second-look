"""resume and confirmed answers

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-21

Update 07 sections 1.2 and 1.3. The session learns how many answers never reached us after the
browser tried to resend them. A response learns what was picked first, when, and how many times
the person changed their mind before pressing Next. Mirrors apps/api/models.py.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "session",
        sa.Column("unsent_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("response", sa.Column("first_choice", sa.String(length=16), nullable=True))
    op.add_column("response", sa.Column("t_first_ms", sa.Integer(), nullable=True))
    op.add_column(
        "response",
        sa.Column("n_changes", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("response", "n_changes")
    op.drop_column("response", "t_first_ms")
    op.drop_column("response", "first_choice")
    op.drop_column("session", "unsent_count")
