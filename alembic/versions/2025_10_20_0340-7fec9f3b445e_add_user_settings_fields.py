"""add_user_settings_fields

Revision ID: 7fec9f3b445e
Revises: 001
Create Date: 2025-10-20 03:40:52.490706

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7fec9f3b445e'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Применение изменений к БД."""
    op.add_column('users', sa.Column('monthly_limit', sa.Integer(), nullable=True, comment='Месячный лимит трат (в рублях)'))


def downgrade() -> None:
    """Откат изменений в БД."""
    op.drop_column('users', 'monthly_limit')

