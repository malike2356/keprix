"""Research, playbook, and compare tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "002_research_playbook_compare"
down_revision = "001_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("depth", sa.Text(), nullable=False, server_default="standard"),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("sub_questions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("sources", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("report_markdown", sa.Text(), nullable=True),
        sa.Column("model_used", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_research_jobs_user_started", "research_jobs", ["user_id", "started_at"])

    op.create_table(
        "model_comparisons",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("model_a", sa.Text(), nullable=False),
        sa.Column("model_b", sa.Text(), nullable=False),
        sa.Column("response_a", sa.Text(), nullable=False),
        sa.Column("response_b", sa.Text(), nullable=False),
        sa.Column("winner", sa.Text(), nullable=True),
        sa.Column("voted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("winner IN ('a','b','tie')", name="ck_model_comparisons_winner"),
    )

    op.create_table(
        "playbook_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("backend", sa.Text(), nullable=False, server_default="ollama"),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("logs", sa.Text(), nullable=False, server_default=""),
        sa.Column("result", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "job_type IN ('download','serve','benchmark','stop')",
            name="ck_playbook_jobs_job_type",
        ),
    )


def downgrade() -> None:
    op.drop_table("playbook_jobs")
    op.drop_table("model_comparisons")
    op.drop_index("ix_research_jobs_user_started", table_name="research_jobs")
    op.drop_table("research_jobs")
