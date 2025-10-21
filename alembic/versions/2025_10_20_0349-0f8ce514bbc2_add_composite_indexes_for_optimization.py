"""add_composite_indexes_for_optimization

Revision ID: 0f8ce514bbc2
Revises: 7fec9f3b445e
Create Date: 2025-10-20 03:49:58.073324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f8ce514bbc2'
down_revision: Union[str, None] = '7fec9f3b445e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Применение изменений к БД.
    
    Добавляет составные индексы для оптимизации часто используемых запросов:
    - transactions(user_id, type) - фильтрация транзакций по пользователю и типу
    - transactions(user_id, created_at) - фильтрация по пользователю и дате
    - transactions(category_id, created_at) - статистика по категориям за период
    """
    ## Составной индекс для фильтрации транзакций по пользователю и типу
    op.create_index(
        'ix_transactions_user_type',
        'transactions',
        ['user_id', 'type'],
        unique=False
    )
    
    ## Составной индекс для фильтрации транзакций по пользователю и дате
    op.create_index(
        'ix_transactions_user_created',
        'transactions',
        ['user_id', 'created_at'],
        unique=False
    )
    
    ## Составной индекс для статистики по категориям
    op.create_index(
        'ix_transactions_category_created',
        'transactions',
        ['category_id', 'created_at'],
        unique=False
    )
    
    ## Индекс для поиска категорий по пользователю и типу
    op.create_index(
        'ix_categories_user_type',
        'categories',
        ['user_id', 'type'],
        unique=False
    )


def downgrade() -> None:
    """
    Откат изменений в БД.
    
    Удаляет добавленные составные индексы.
    """
    op.drop_index('ix_categories_user_type', table_name='categories')
    op.drop_index('ix_transactions_category_created', table_name='transactions')
    op.drop_index('ix_transactions_user_created', table_name='transactions')
    op.drop_index('ix_transactions_user_type', table_name='transactions')

