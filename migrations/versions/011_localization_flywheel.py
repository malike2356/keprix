"""Alembic migration: localization corrections and training samples (Prompt 50)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "011_localization_flywheel"
down_revision = "010_localization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "localization_corrections",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("audit_record_id", sa.Text(), nullable=False),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("correction_type", sa.Text(), nullable=False),
        sa.Column("original_value", sa.Text(), nullable=False),
        sa.Column("corrected_value", sa.Text(), nullable=False),
        sa.Column("source_language", sa.Text(), nullable=False),
        sa.Column("target_language", sa.Text(), nullable=True),
        sa.Column("domain", sa.Text(), nullable=False, server_default="generic"),
        sa.Column("submitted_by_user_id", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("reviewed_by_user_id", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("applied_to_glossary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("staged_for_training", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("training_sample_id", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_localization_corrections_workspace_status",
        "localization_corrections",
        ["workspace_id", "status", "correction_type"],
    )
    op.create_index(
        "ix_localization_corrections_lang_domain",
        "localization_corrections",
        ["source_language", "domain", "status"],
    )
    op.create_index(
        "ix_localization_corrections_staged",
        "localization_corrections",
        ["staged_for_training"],
    )

    op.create_table(
        "localization_training_samples",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("correction_id", sa.Text(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("source_language", sa.Text(), nullable=False),
        sa.Column("target_language", sa.Text(), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("source_audio_file_id", sa.Text(), nullable=True),
        sa.Column("target_text", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=False, server_default="generic"),
        sa.Column("quality_score", sa.SmallInteger(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("included_in_export_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_localization_training_samples_export",
        "localization_training_samples",
        ["task_type", "source_language", "included_in_export_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_localization_training_samples_export", table_name="localization_training_samples")
    op.drop_table("localization_training_samples")
    op.drop_index("ix_localization_corrections_staged", table_name="localization_corrections")
    op.drop_index("ix_localization_corrections_lang_domain", table_name="localization_corrections")
    op.drop_index("ix_localization_corrections_workspace_status", table_name="localization_corrections")
    op.drop_table("localization_corrections")
