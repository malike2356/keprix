"""Alembic: outreach automation tables (K02)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "024_outreach_automation"
down_revision = "023_aiva_scout_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "outreach_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("source_type", sa.Text(), nullable=True),
        sa.Column("daily_cap", sa.Integer(), server_default="50"),
        sa.Column("timezone", sa.Text(), server_default="Europe/London"),
        sa.Column("business_hours_only", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("warmup_days", sa.Integer(), server_default="3"),
        sa.Column("require_approval", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("default_sequence_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("default_booking_link", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_outreach_campaigns_workspace", "outreach_campaigns", ["workspace_id"])

    op.create_table(
        "outreach_sequences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("channel_default", sa.Text(), server_default="email"),
        sa.Column("stop_on_reply", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("stop_on_booking", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("stop_on_unsubscribe", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_outreach_sequences_workspace", "outreach_sequences", ["workspace_id"])

    op.create_table(
        "outreach_sequence_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("sequence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outreach_sequences.id", ondelete="CASCADE"), nullable=True),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False, server_default="email"),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("cta", sa.Text(), nullable=True),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("delay_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.UniqueConstraint("sequence_id", "step_order", name="uq_outreach_sequence_step_order"),
    )

    op.create_table(
        "outreach_leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outreach_campaigns.id"), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="new"),
        sa.Column("first_name", sa.Text(), nullable=True),
        sa.Column("last_name", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), server_default="manual"),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_outreach_leads_workspace", "outreach_leads", ["workspace_id"])
    op.create_index("ix_outreach_leads_email", "outreach_leads", ["workspace_id", "email"])

    op.create_table(
        "outreach_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outreach_leads.id", ondelete="CASCADE"), nullable=True),
        sa.Column("sequence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outreach_sequences.id"), nullable=True),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_outreach_enrollments_due", "outreach_enrollments", ["status", "next_run_at"])

    op.create_table(
        "outreach_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("enrollment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outreach_enrollments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outreach_sequence_steps.id"), nullable=True),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bounced", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "outreach_replies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outreach_leads.id"), nullable=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outreach_messages.id"), nullable=True),
        sa.Column("from_address", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("classification", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("resolved", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("outreach_replies")
    op.drop_table("outreach_messages")
    op.drop_index("ix_outreach_enrollments_due", table_name="outreach_enrollments")
    op.drop_table("outreach_enrollments")
    op.drop_index("ix_outreach_leads_email", table_name="outreach_leads")
    op.drop_index("ix_outreach_leads_workspace", table_name="outreach_leads")
    op.drop_table("outreach_leads")
    op.drop_table("outreach_sequence_steps")
    op.drop_index("ix_outreach_sequences_workspace", table_name="outreach_sequences")
    op.drop_table("outreach_sequences")
    op.drop_index("ix_outreach_campaigns_workspace", table_name="outreach_campaigns")
    op.drop_table("outreach_campaigns")
