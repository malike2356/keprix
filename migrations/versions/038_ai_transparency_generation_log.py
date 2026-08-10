"""Alembic: append-only generation_log with UPDATE/DELETE revoked for app roles."""

from __future__ import annotations

from alembic import op

revision = "038_ai_transparency_generation_log"
down_revision = "037_vical_calendar_invitations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Alembic creates version_num as VARCHAR(32) by default. This revision id is
    # longer than that, so widen the control column before Alembic records the
    # completed revision at the end of this transaction.
    op.execute(
        "ALTER TABLE alembic_version "
        "ALTER COLUMN version_num TYPE VARCHAR(128)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS generation_log (
            log_id TEXT PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            user_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            model_version TEXT,
            input_hash TEXT NOT NULL,
            output_hash TEXT NOT NULL,
            content_type TEXT NOT NULL,
            feature_endpoint TEXT NOT NULL,
            session_id TEXT,
            workspace_id TEXT NOT NULL DEFAULT 'default',
            locale TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_generation_log_ts ON generation_log (timestamp)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_generation_log_user_ts "
        "ON generation_log (user_id, timestamp)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_generation_log_model_ts "
        "ON generation_log (model_name, timestamp)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_generation_log_feature_ts "
        "ON generation_log (feature_endpoint, timestamp)"
    )

    # Application roles may INSERT/SELECT only. UPDATE and DELETE are revoked.
    # Table owners in Postgres retain mutation rights even after REVOKE, so also
    # install a BEFORE UPDATE/DELETE trigger that hard-blocks mutations.
    op.execute(
        """
        DO $$
        DECLARE
            role_name TEXT;
        BEGIN
            FOREACH role_name IN ARRAY ARRAY['keprix', 'app_user']
            LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
                    EXECUTE format('GRANT SELECT, INSERT ON generation_log TO %I', role_name);
                    EXECUTE format('REVOKE UPDATE, DELETE ON generation_log FROM %I', role_name);
                END IF;
            END LOOP;
        END
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION forbid_generation_log_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'generation_log is append-only; UPDATE and DELETE are forbidden';
        END;
        $$;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS generation_log_no_update ON generation_log")
    op.execute("DROP TRIGGER IF EXISTS generation_log_no_delete ON generation_log")
    op.execute(
        """
        CREATE TRIGGER generation_log_no_update
        BEFORE UPDATE ON generation_log
        FOR EACH ROW
        EXECUTE FUNCTION forbid_generation_log_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER generation_log_no_delete
        BEFORE DELETE ON generation_log
        FOR EACH ROW
        EXECUTE FUNCTION forbid_generation_log_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS generation_log")
