"""Alembic migration for voice template tables (optional PG persistence)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "009_voice_templates"
down_revision = "50f1bef7a5f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voice_template_categories",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("domain", sa.Text(), nullable=False, server_default="generic"),
        sa.Column("is_dynamic", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("dynamic_placeholder", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "voice_templates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "category_id",
            sa.Text(),
            sa.ForeignKey("voice_template_categories.id"),
            nullable=False,
        ),
        sa.Column("language_code", sa.Text(), nullable=False),
        sa.Column("dialect_note", sa.Text(), nullable=True),
        sa.Column("audio_file_id", sa.String(length=36), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("transcript_english", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("recorded_by", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.Date(), nullable=True),
        sa.Column("quality_rating", sa.SmallInteger(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("approved_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("play_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("workspace_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("category_id", "language_code", "workspace_id", name="uq_voice_templates_slot"),
    )
    op.create_index(
        "ix_voice_templates_category_language_status",
        "voice_templates",
        ["category_id", "language_code", "status"],
    )
    op.create_index(
        "ix_voice_templates_workspace_status",
        "voice_templates",
        ["workspace_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_voice_templates_workspace_status", table_name="voice_templates")
    op.drop_index("ix_voice_templates_category_language_status", table_name="voice_templates")
    op.drop_table("voice_templates")
    op.drop_table("voice_template_categories")
