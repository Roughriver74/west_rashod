"""add_sync_settings_table

Revision ID: add_sync_settings
Revises: 6dda2710c840
Create Date: 2025-12-21 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_sync_settings'
down_revision: Union[str, None] = '6dda2710c840'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add sync_settings table for automatic synchronization configuration."""
    op.create_table(
        'sync_settings',
        sa.Column('id', sa.Integer(), primary_key=True, default=1),
        sa.Column('auto_sync_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sync_interval_hours', sa.Integer(), nullable=False, server_default='4'),
        sa.Column('sync_time_hour', sa.Integer(), nullable=True),
        sa.Column('sync_time_minute', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('auto_classify', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sync_days_back', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('last_sync_started_at', sa.DateTime(), nullable=True),
        sa.Column('last_sync_completed_at', sa.DateTime(), nullable=True),
        sa.Column('last_sync_status', sa.String(50), nullable=True),
        sa.Column('last_sync_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    )

    # Insert default settings row
    op.execute("""
        INSERT INTO sync_settings (id, auto_sync_enabled, sync_interval_hours, sync_time_minute, auto_classify, sync_days_back)
        VALUES (1, false, 4, 0, true, 30)
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    """Remove sync_settings table."""
    op.drop_table('sync_settings')
