"""describe change

Revision ID: c146dcbf40a9
Revises: 815651c3c3a6
Create Date: 2026-03-25 13:09:53.791667

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c146dcbf40a9'
down_revision: Union[str, Sequence[str], None] = '815651c3c3a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
