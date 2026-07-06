"""Alembic migration: control plane and retrieval graph edges (Prompt 32)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "012_data_architecture"
down_revision = "011_localization_flywheel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "control_plane_tenants",
        sa.Column("tenant_id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_table(
        "control_plane_workspaces",
        sa.Column("workspace_id", sa.Text(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), sa.ForeignKey("control_plane_tenants.tenant_id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("data_plane_path", sa.Text(), nullable=True),
        sa.Column("scout_enrolled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_control_plane_workspaces_tenant", "control_plane_workspaces", ["tenant_id"])

    op.create_table(
        "retrieval_graph_edges",
        sa.Column("edge_id", sa.Text(), primary_key=True),
        sa.Column("workspace_id", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("target_kind", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=False),
        sa.Column("relation", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index(
        "ix_retrieval_graph_edges_workspace_source",
        "retrieval_graph_edges",
        ["workspace_id", "source_kind", "source_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_retrieval_graph_edges_workspace_source", table_name="retrieval_graph_edges")
    op.drop_table("retrieval_graph_edges")
    op.drop_index("ix_control_plane_workspaces_tenant", table_name="control_plane_workspaces")
    op.drop_table("control_plane_workspaces")
    op.drop_table("control_plane_tenants")
