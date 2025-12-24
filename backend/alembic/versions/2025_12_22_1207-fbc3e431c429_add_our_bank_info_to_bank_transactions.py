"""add our bank info to bank transactions

Revision ID: fbc3e431c429
Revises: 2c1db3345c56
Create Date: 2025-12-22 12:07:27.297001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fbc3e431c429'
down_revision: Union[str, None] = '2c1db3345c56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем поля для информации о нашем банке (где открыт счет)
    op.add_column('bank_transactions', sa.Column('our_bank_name', sa.String(length=500), nullable=True))
    op.add_column('bank_transactions', sa.Column('our_bank_bik', sa.String(length=20), nullable=True))

    # Создаем индекс для быстрого поиска по банку
    op.create_index('ix_bank_transactions_our_bank_bik', 'bank_transactions', ['our_bank_bik'])


def downgrade() -> None:
    # Удаляем индекс
    op.drop_index('ix_bank_transactions_our_bank_bik', table_name='bank_transactions')

    # Удаляем колонки
    op.drop_column('bank_transactions', 'our_bank_bik')
    op.drop_column('bank_transactions', 'our_bank_name')
