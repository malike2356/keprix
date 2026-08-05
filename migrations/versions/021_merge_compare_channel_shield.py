"""Merge Alembic heads 018_compare_metrics and 020_channel_shield."""

from __future__ import annotations

revision = "021_merge_compare_channel_shield"
down_revision = ("018_compare_metrics", "020_channel_shield")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
