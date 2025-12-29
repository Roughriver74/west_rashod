"""add_unique_constraint_to_fin_expense_details

Revision ID: f4cf8e924ce7
Revises: 02e3ea92b54f
Create Date: 2025-12-29 16:43:07.187119

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4cf8e924ce7'
down_revision: Union[str, None] = '02e3ea92b54f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Удалить существующие дубликаты перед созданием уникального индекса
    op.execute("""
        DELETE FROM fin_expense_details
        WHERE id IN (
            SELECT id
            FROM (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY
                            expense_operation_id,
                            COALESCE(contract_number, ''),
                            COALESCE(payment_type, ''),
                            COALESCE(payment_amount, 0),
                            COALESCE(settlement_account, '')
                        ORDER BY id ASC
                    ) as rn
                FROM fin_expense_details
            ) duplicates
            WHERE rn > 1
        )
    """)

    # Создать уникальный индекс
    # Используем выражение для учета NULL значений
    op.create_index(
        'uq_fin_expense_detail_composite',
        'fin_expense_details',
        [
            'expense_operation_id',
            sa.text('COALESCE(contract_number, \'\')'),
            sa.text('COALESCE(payment_type, \'\')'),
            sa.text('COALESCE(payment_amount, 0)'),
            sa.text('COALESCE(settlement_account, \'\')')
        ],
        unique=True
    )


def downgrade() -> None:
    # Удалить уникальный индекс
    op.drop_index('uq_fin_expense_detail_composite', table_name='fin_expense_details')
