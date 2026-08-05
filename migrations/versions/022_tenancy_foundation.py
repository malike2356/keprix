"""Extend control_plane_tenants for product multi-tenancy (slug, owner)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "022_tenancy_foundation"
down_revision = "021_merge_compare_channel_shield"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("control_plane_tenants", sa.Column("slug", sa.Text(), nullable=True))
    op.add_column("control_plane_tenants", sa.Column("display_name", sa.Text(), nullable=True))
    op.add_column("control_plane_tenants", sa.Column("owner_user_id", sa.Text(), nullable=True))
    op.execute("UPDATE control_plane_tenants SET slug = tenant_id WHERE slug IS NULL")
    op.execute("UPDATE control_plane_tenants SET display_name = name WHERE display_name IS NULL")
    op.create_index("uq_control_plane_tenants_slug", "control_plane_tenants", ["slug"], unique=True)

    op.create_table(
        "control_plane_memberships",
        sa.Column("tenant_id", sa.Text(), sa.ForeignKey("control_plane_tenants.tenant_id"), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default=sa.text("'member'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("control_plane_memberships")
    op.drop_index("uq_control_plane_tenants_slug", table_name="control_plane_tenants")
    op.drop_column("control_plane_tenants", "owner_user_id")
    op.drop_column("control_plane_tenants", "display_name")
    op.drop_column("control_plane_tenants", "slug")
