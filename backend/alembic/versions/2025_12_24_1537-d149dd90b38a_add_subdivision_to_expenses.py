"""add_subdivision_to_expenses

Revision ID: d149dd90b38a
Revises: 2cf57a21ee11
Create Date: 2025-12-24 15:37:03.035817

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd149dd90b38a'
down_revision: Union[str, None] = '2cf57a21ee11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавить поле подразделения в таблицу expenses
    op.add_column('expenses', sa.Column('subdivision', sa.String(length=255), nullable=True))
    op.add_column('expenses', sa.Column('subdivision_code', sa.String(length=50), nullable=True))


def downgrade() -> None:
    # Удалить поля подразделения
    op.drop_column('expenses', 'subdivision_code')
    op.drop_column('expenses', 'subdivision')
