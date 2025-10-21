"""Initial migration with users, categories and transactions tables

Revision ID: 001
Revises: 
Create Date: 2025-01-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Применение изменений к БД."""
    
    ## Создание ENUM типов (только для PostgreSQL)
    ## SQLite не поддерживает ENUM, использует VARCHAR
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("CREATE TYPE category_type AS ENUM ('income', 'expense')")
        op.execute("CREATE TYPE transaction_type AS ENUM ('income', 'expense')")
    
    # Создание таблицы users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(255), nullable=False),
        sa.Column('last_name', sa.String(255), nullable=True),
        sa.Column('max_transaction_limit', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('telegram_id', name=op.f('uq_users_telegram_id')),
        comment='Пользователи бота'
    )
    op.create_index(op.f('ix_telegram_id'), 'users', ['telegram_id'], unique=False)
    
    # Создание таблицы categories
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('type', sa.Enum('income', 'expense', name='category_type', create_type=False), nullable=False),
        sa.Column('emoji', sa.String(10), nullable=False, server_default='📝'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_categories_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_categories')),
        comment='Категории доходов и расходов'
    )
    op.create_index(op.f('ix_type'), 'categories', ['type'], unique=False)
    op.create_index(op.f('ix_is_default'), 'categories', ['is_default'], unique=False)
    op.create_index(op.f('ix_user_id'), 'categories', ['user_id'], unique=False)
    
    # Создание таблицы transactions
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('income', 'expense', name='transaction_type', create_type=False), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_transactions_user_id_users'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_transactions_category_id_categories'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_transactions')),
        comment='Финансовые транзакции пользователей'
    )
    op.create_index(op.f('ix_transactions_user_id'), 'transactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_transactions_type'), 'transactions', ['type'], unique=False)
    op.create_index(op.f('ix_transactions_category_id'), 'transactions', ['category_id'], unique=False)
    op.create_index(op.f('ix_transactions_created_at'), 'transactions', ['created_at'], unique=False)


def downgrade() -> None:
    """Откат изменений в БД."""
    
    # Удаление таблиц в обратном порядке
    op.drop_index(op.f('ix_transactions_created_at'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_category_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_type'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_user_id'), table_name='transactions')
    op.drop_table('transactions')
    
    op.drop_index(op.f('ix_user_id'), table_name='categories')
    op.drop_index(op.f('ix_is_default'), table_name='categories')
    op.drop_index(op.f('ix_type'), table_name='categories')
    op.drop_table('categories')
    
    op.drop_index(op.f('ix_telegram_id'), table_name='users')
    op.drop_table('users')
    
    ## Удаление ENUM типов (только для PostgreSQL)
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE transaction_type')
        op.execute('DROP TYPE category_type')

