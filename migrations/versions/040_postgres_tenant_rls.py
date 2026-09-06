"""Force PostgreSQL row-level isolation for tenant-bearing tables.

The migration discovers the final table shape after all product migrations have
run. This keeps the policy inventory complete when a later product migration
adds another tenant-bearing table, while the predicate rules remain explicit.
"""

from __future__ import annotations

from alembic import op

revision = "040_postgres_tenant_rls"
down_revision = "039_repair_llm_usage_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $keprix_rls$
        DECLARE
            item record;
            predicate text;
            policy_name text;
        BEGIN
            FOR item IN
                SELECT c.table_name,
                       bool_or(c.column_name = 'tenant_id') AS has_tenant_id,
                       bool_or(c.column_name = 'workspace_id') AS has_workspace_id,
                       bool_or(c.column_name = 'user_id') AS has_user_id
                FROM information_schema.columns c
                WHERE c.table_schema = 'public'
                  AND c.column_name IN ('tenant_id', 'workspace_id', 'user_id')
                  AND c.table_name NOT IN (
                      'control_plane_tenants',
                      'users',
                      'schema_migrations',
                      'alembic_version'
                  )
                GROUP BY c.table_name
                ORDER BY c.table_name
            LOOP
                IF item.has_tenant_id THEN
                    predicate := format(
                        'tenant_id = NULLIF(current_setting(''app.current_tenant_id'', true), '''')'
                    );
                ELSIF item.has_workspace_id THEN
                    predicate := format(
                        'EXISTS (SELECT 1 FROM control_plane_workspaces cpw '
                        'WHERE cpw.workspace_id = %I.%I '
                        'AND cpw.tenant_id = NULLIF(current_setting('
                        '''app.current_tenant_id'', true), ''''))',
                        item.table_name,
                        'workspace_id'
                    );
                ELSIF item.has_user_id THEN
                    predicate := format(
                        'EXISTS (SELECT 1 FROM control_plane_memberships cpm '
                        'WHERE cpm.user_id = %I.%I '
                        'AND cpm.tenant_id = NULLIF(current_setting('
                        '''app.current_tenant_id'', true), ''''))',
                        item.table_name,
                        'user_id'
                    );
                ELSE
                    CONTINUE;
                END IF;

                policy_name := format('keprix_tenant_isolation_%s', item.table_name);
                EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', item.table_name);
                EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', item.table_name);
                EXECUTE format('DROP POLICY IF EXISTS %I ON %I', policy_name, item.table_name);
                EXECUTE format(
                    'CREATE POLICY %I ON %I USING (%s) WITH CHECK (%s)',
                    policy_name, item.table_name, predicate, predicate
                );
            END LOOP;
        END
        $keprix_rls$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $keprix_rls$
        DECLARE
            item record;
            policy_name text;
        BEGIN
            FOR item IN
                SELECT DISTINCT tablename AS table_name
                FROM pg_policies
                WHERE schemaname = 'public'
                  AND policyname LIKE 'keprix_tenant_isolation_%'
            LOOP
                policy_name := format('keprix_tenant_isolation_%s', item.table_name);
                EXECUTE format('DROP POLICY IF EXISTS %I ON %I', policy_name, item.table_name);
                EXECUTE format('ALTER TABLE %I NO FORCE ROW LEVEL SECURITY', item.table_name);
                EXECUTE format('ALTER TABLE %I DISABLE ROW LEVEL SECURITY', item.table_name);
            END LOOP;
        END
        $keprix_rls$;
        """
    )
