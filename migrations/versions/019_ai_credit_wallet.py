"""Alembic: placeholder for retired AI credit wallet revision.

The original script body was emptied in a reconcile commit; Alembic still
requires a revision id because 020_channel_shield depends on this id.
"""

from __future__ import annotations

revision = "019_ai_credit_wallet"
down_revision = "018_compare_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op: wallet tables (if any) are owned by later billing migrations.
    pass


def downgrade() -> None:
    pass
