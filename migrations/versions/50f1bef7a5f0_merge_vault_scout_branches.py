"""merge_vault_scout_branches

Revision ID: 50f1bef7a5f0
Revises: 004_vault_oauth, 008_scout_governance
Create Date: 2026-07-05 16:01:07.085235

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50f1bef7a5f0'
down_revision: Union[str, Sequence[str], None] = ('004_vault_oauth', '008_scout_governance')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
