"""Repair deployments whose baseline was stamped without llm_usage_events."""

from __future__ import annotations

from alembic import op

revision = "039_repair_llm_usage_events"
down_revision = "038_ai_transparency_generation_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_usage_events (
            id VARCHAR(36) PRIMARY KEY,
            recorded_at TIMESTAMPTZ NOT NULL,
            workspace_id TEXT NOT NULL DEFAULT 'default',
            user_id TEXT,
            session_id TEXT,
            run_id TEXT,
            channel TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cache_read_tokens INTEGER NOT NULL DEFAULT 0,
            cache_write_tokens INTEGER NOT NULL DEFAULT 0,
            reasoning_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd NUMERIC,
            cost_status TEXT NOT NULL,
            cost_source TEXT NOT NULL,
            duration_ms INTEGER,
            metadata JSON NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_llm_usage_recorded_at "
        "ON llm_usage_events(recorded_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_llm_usage_workspace_recorded "
        "ON llm_usage_events(workspace_id, recorded_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_llm_usage_user_recorded "
        "ON llm_usage_events(user_id, recorded_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_llm_usage_model_recorded "
        "ON llm_usage_events(model, recorded_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_llm_usage_channel_recorded "
        "ON llm_usage_events(channel, recorded_at)"
    )


def downgrade() -> None:
    # This is a schema-drift repair. Dropping a potentially pre-existing usage
    # ledger during rollback would destroy operational evidence.
    pass
