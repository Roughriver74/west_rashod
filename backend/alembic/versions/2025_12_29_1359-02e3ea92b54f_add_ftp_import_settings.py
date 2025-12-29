"""add_ftp_import_settings

Revision ID: 02e3ea92b54f
Revises: 7551163fe864
Create Date: 2025-12-29 13:59:39.502847

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '02e3ea92b54f'
down_revision: Union[str, None] = '7551163fe864'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add FTP import settings columns to sync_settings table
    op.add_column('sync_settings', sa.Column('ftp_import_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('sync_settings', sa.Column('ftp_import_interval_hours', sa.Integer(), nullable=False, server_default='24'))
    op.add_column('sync_settings', sa.Column('ftp_import_time_hour', sa.Integer(), nullable=True))
    op.add_column('sync_settings', sa.Column('ftp_import_time_minute', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('sync_settings', sa.Column('ftp_import_clear_existing', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('sync_settings', sa.Column('last_ftp_import_started_at', sa.DateTime(), nullable=True))
    op.add_column('sync_settings', sa.Column('last_ftp_import_completed_at', sa.DateTime(), nullable=True))
    op.add_column('sync_settings', sa.Column('last_ftp_import_status', sa.String(length=50), nullable=True))
    op.add_column('sync_settings', sa.Column('last_ftp_import_message', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('sync_settings', 'last_ftp_import_message')
    op.drop_column('sync_settings', 'last_ftp_import_status')
    op.drop_column('sync_settings', 'last_ftp_import_completed_at')
    op.drop_column('sync_settings', 'last_ftp_import_started_at')
    op.drop_column('sync_settings', 'ftp_import_clear_existing')
    op.drop_column('sync_settings', 'ftp_import_time_minute')
    op.drop_column('sync_settings', 'ftp_import_time_hour')
    op.drop_column('sync_settings', 'ftp_import_interval_hours')
    op.drop_column('sync_settings', 'ftp_import_enabled')
