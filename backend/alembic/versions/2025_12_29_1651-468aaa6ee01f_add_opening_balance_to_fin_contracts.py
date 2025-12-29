"""add_opening_balance_to_fin_contracts

Revision ID: 468aaa6ee01f
Revises: f4cf8e924ce7
Create Date: 2025-12-29 16:51:09.021713

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '468aaa6ee01f'
down_revision: Union[str, None] = 'f4cf8e924ce7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавить поле opening_balance в таблицу fin_contracts
    # Это начальное сальдо договора на момент его заключения
    op.add_column(
        'fin_contracts',
        sa.Column('opening_balance', sa.Numeric(15, 2), nullable=True, server_default='0')
    )

    # Добавить комментарий к колонке
    op.execute("""
        COMMENT ON COLUMN fin_contracts.opening_balance IS
        'Начальное сальдо договора на момент заключения (руб.)'
    """)


def downgrade() -> None:
    # Удалить поле opening_balance
    op.drop_column('fin_contracts', 'opening_balance')
