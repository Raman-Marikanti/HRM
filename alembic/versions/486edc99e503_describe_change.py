"""describe change

Revision ID: 486edc99e503
Revises: 
Create Date: 2026-03-26 13:25:33.455265
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '486edc99e503'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column(
            'is_employee_created',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false')
        )
    )
    op.alter_column('users', 'is_employee_created', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'is_employee_created')