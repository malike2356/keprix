"""Alembic migration: localization preferences and audit (optional PG persistence)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "010_localization"
down_revision = "009_voice_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_language_preferences",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("preferred_input_language", sa.Text(), nullable=True),
        sa.Column("preferred_output_language", sa.Text(), nullable=True),
        sa.Column("voice_output_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("preferred_voice_id", sa.Text(), nullable=True),
        sa.Column("bilingual_replies", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_user_language_preferences_workspace_user"),
    )
    op.create_index(
        "ix_user_language_preferences_workspace",
        "user_language_preferences",
        ["workspace_id"],
    )

    op.create_table(
        "localization_audit",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("input_type", sa.Text(), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("translated_input", sa.Text(), nullable=True),
        sa.Column("final_response", sa.Text(), nullable=True),
        sa.Column("detected_language", sa.Text(), nullable=True),
        sa.Column("output_language", sa.Text(), nullable=True),
        sa.Column("detection_confidence", sa.Float(), nullable=True),
        sa.Column("transcription_provider", sa.Text(), nullable=True),
        sa.Column("translation_provider", sa.Text(), nullable=True),
        sa.Column("speech_provider", sa.Text(), nullable=True),
        sa.Column("glossary_id", sa.Text(), nullable=True),
        sa.Column("glossary_warnings", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("human_review_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(
        "ix_localization_audit_workspace_created",
        "localization_audit",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_localization_audit_human_review",
        "localization_audit",
        ["workspace_id", "human_review_required"],
    )


def downgrade() -> None:
    op.drop_index("ix_localization_audit_human_review", table_name="localization_audit")
    op.drop_index("ix_localization_audit_workspace_created", table_name="localization_audit")
    op.drop_table("localization_audit")
    op.drop_index("ix_user_language_preferences_workspace", table_name="user_language_preferences")
    op.drop_table("user_language_preferences")
