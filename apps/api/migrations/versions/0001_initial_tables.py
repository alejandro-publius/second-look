"""initial tables

Revision ID: 0001
Revises:
Create Date: 2026-09-20

Mirrors apps/api/models.py. Runs on SQLite and Postgres: only portable types are used and
JSON-shaped values are Text.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skeleton_ping",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "randomization_counter",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("seed", sa.String(length=64), nullable=False),
        sa.Column("next_position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "session",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("arm", sa.String(length=16), nullable=False),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column("item_order", sa.Text(), nullable=False),
        sa.Column("consent_version", sa.String(length=32), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("build_hash", sa.String(length=64), nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lesson_seconds", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_token_hash", sa.String(length=64), nullable=False),
        sa.Column("ua_class", sa.String(length=16), nullable=False),
        sa.Column("is_test", sa.Boolean(), nullable=False),
        sa.Column("source_label", sa.String(length=16), nullable=False),
        sa.Column("hidden_field_filled", sa.Boolean(), nullable=False),
        sa.Column("post_lock", sa.Boolean(), nullable=False),
        sa.Column("prior_experience", sa.String(length=8), nullable=True),
        sa.Column("warmup_choice", sa.String(length=16), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "response",
        sa.Column("session_id", sa.String(length=32), nullable=False),
        sa.Column("item_id", sa.String(length=16), nullable=False),
        sa.Column("answer", sa.String(length=16), nullable=False),
        sa.Column("rt_ms", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["session.id"]),
        sa.PrimaryKeyConstraint("session_id", "item_id"),
    )
    op.create_table(
        "observer",
        sa.Column("contributor_token", sa.String(length=32), nullable=False),
        sa.Column("scores_json", sa.Text(), nullable=False),
        sa.Column("tested_on", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("contributor_token"),
    )
    op.create_table(
        "spot",
        sa.Column("spot_id", sa.String(length=32), nullable=False),
        sa.Column("spot_name", sa.String(length=80), nullable=False),
        sa.Column("reach_id", sa.String(length=40), nullable=False),
        sa.Column("reach_name", sa.String(length=80), nullable=False),
        sa.Column("creek_id", sa.String(length=40), nullable=False),
        sa.Column("creek_name", sa.String(length=80), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("coarse", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("spot_id"),
    )
    op.create_table(
        "visit",
        sa.Column("visit_id", sa.String(length=32), nullable=False),
        sa.Column("spot_id", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("contributor_token", sa.String(length=32), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answers_json", sa.Text(), nullable=False),
        sa.Column("first_rating", sa.String(length=16), nullable=True),
        sa.Column("final_rating", sa.String(length=16), nullable=True),
        sa.Column("photo_ids_json", sa.Text(), nullable=False),
        sa.Column("followups_json", sa.Text(), nullable=False),
        sa.Column("site_json", sa.Text(), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("software_version", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["spot_id"], ["spot.spot_id"]),
        sa.PrimaryKeyConstraint("visit_id"),
    )
    op.create_index("ix_visit_spot_id", "visit", ["spot_id"])
    op.create_table(
        "check_result",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("visit_id", sa.String(length=32), nullable=False),
        sa.Column("rule_id", sa.String(length=32), nullable=False),
        sa.Column("asked", sa.Boolean(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=True),
        sa.Column("answer", sa.String(length=64), nullable=True),
        sa.Column("detail_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["visit.visit_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_check_result_visit_id", "check_result", ["visit_id"])
    op.create_table(
        "upload",
        sa.Column("photo_id", sa.String(length=32), nullable=False),
        sa.Column("file", sa.String(length=255), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("photo_id"),
    )
    op.create_index("ix_upload_created_at", "upload", ["created_at"])
    op.create_table(
        "sandbox_cache",
        sa.Column("cache_key", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("cache_key"),
    )


def downgrade() -> None:
    op.drop_table("sandbox_cache")
    op.drop_index("ix_upload_created_at", table_name="upload")
    op.drop_table("upload")
    op.drop_index("ix_check_result_visit_id", table_name="check_result")
    op.drop_table("check_result")
    op.drop_index("ix_visit_spot_id", table_name="visit")
    op.drop_table("visit")
    op.drop_table("spot")
    op.drop_table("observer")
    op.drop_table("response")
    op.drop_table("session")
    op.drop_table("randomization_counter")
    op.drop_table("skeleton_ping")
