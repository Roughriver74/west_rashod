"""remove_department_id_from_business_operation_mappings

Revision ID: dc2ccbe74e5c
Revises: 659c268ebe0c
Create Date: 2025-12-20 13:28:40.844099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'dc2ccbe74e5c'
down_revision: Union[str, None] = '659c268ebe0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First: Drop all foreign keys and columns referencing departments

    # bank_transactions
    op.drop_index('ix_bank_transactions_department_id', table_name='bank_transactions')
    op.drop_constraint('bank_transactions_department_id_fkey', 'bank_transactions', type_='foreignkey')
    op.drop_column('bank_transactions', 'department_id')

    # budget_categories
    op.drop_index('idx_budget_category_dept_active', table_name='budget_categories')
    op.drop_index('ix_budget_categories_department_id', table_name='budget_categories')
    op.drop_constraint('budget_categories_department_id_fkey', 'budget_categories', type_='foreignkey')
    op.drop_column('budget_categories', 'department_id')

    # business_operation_mappings
    op.drop_index('ix_business_operation_mappings_department_id', table_name='business_operation_mappings')
    op.drop_index('ix_business_op_mapping_unique', table_name='business_operation_mappings')
    op.drop_constraint('business_operation_mappings_department_id_fkey', 'business_operation_mappings', type_='foreignkey')
    op.drop_column('business_operation_mappings', 'department_id')
    op.create_index('ix_business_op_mapping_unique', 'business_operation_mappings', ['business_operation', 'category_id'], unique=True)

    # contractors
    op.drop_index('idx_contractor_dept_active', table_name='contractors')
    op.drop_index('ix_contractors_department_id', table_name='contractors')
    op.drop_constraint('contractors_department_id_fkey', 'contractors', type_='foreignkey')
    op.drop_column('contractors', 'department_id')

    # organizations
    op.drop_index('ix_organizations_department_id', table_name='organizations')
    op.drop_constraint('organizations_department_id_fkey', 'organizations', type_='foreignkey')
    op.drop_column('organizations', 'department_id')

    # users
    op.drop_index('ix_users_department_id', table_name='users')
    op.drop_constraint('users_department_id_fkey', 'users', type_='foreignkey')
    op.drop_column('users', 'department_id')

    # Last: Drop departments table (after all references removed)
    op.drop_index('ix_departments_id', table_name='departments')
    op.drop_index('ix_departments_is_active', table_name='departments')
    op.drop_table('departments')


def downgrade() -> None:
    # First: Create departments table
    op.create_table('departments',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('code', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('parent_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('hierarchy_path', sa.VARCHAR(length=1024), autoincrement=False, nullable=True),
    sa.Column('hierarchy_level', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('region', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=True),
    sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['parent_id'], ['departments.id'], name='departments_parent_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='departments_pkey'),
    sa.UniqueConstraint('code', name='departments_code_key'),
    sa.UniqueConstraint('name', name='departments_name_key')
    )
    op.create_index('ix_departments_is_active', 'departments', ['is_active'], unique=False)
    op.create_index('ix_departments_id', 'departments', ['id'], unique=False)

    # Then: Add columns and foreign keys back
    op.add_column('users', sa.Column('department_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('users_department_id_fkey', 'users', 'departments', ['department_id'], ['id'])
    op.create_index('ix_users_department_id', 'users', ['department_id'], unique=False)

    op.add_column('organizations', sa.Column('department_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('organizations_department_id_fkey', 'organizations', 'departments', ['department_id'], ['id'])
    op.create_index('ix_organizations_department_id', 'organizations', ['department_id'], unique=False)

    op.add_column('contractors', sa.Column('department_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.create_foreign_key('contractors_department_id_fkey', 'contractors', 'departments', ['department_id'], ['id'])
    op.create_index('ix_contractors_department_id', 'contractors', ['department_id'], unique=False)
    op.create_index('idx_contractor_dept_active', 'contractors', ['department_id', 'is_active'], unique=False)

    op.add_column('business_operation_mappings', sa.Column('department_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.create_foreign_key('business_operation_mappings_department_id_fkey', 'business_operation_mappings', 'departments', ['department_id'], ['id'])
    op.drop_index('ix_business_op_mapping_unique', table_name='business_operation_mappings')
    op.create_index('ix_business_op_mapping_unique', 'business_operation_mappings', ['business_operation', 'department_id', 'category_id'], unique=True)
    op.create_index('ix_business_operation_mappings_department_id', 'business_operation_mappings', ['department_id'], unique=False)

    op.add_column('budget_categories', sa.Column('department_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('budget_categories_department_id_fkey', 'budget_categories', 'departments', ['department_id'], ['id'])
    op.create_index('ix_budget_categories_department_id', 'budget_categories', ['department_id'], unique=False)
    op.create_index('idx_budget_category_dept_active', 'budget_categories', ['department_id', 'is_active'], unique=False)

    op.add_column('bank_transactions', sa.Column('department_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.create_foreign_key('bank_transactions_department_id_fkey', 'bank_transactions', 'departments', ['department_id'], ['id'])
    op.create_index('ix_bank_transactions_department_id', 'bank_transactions', ['department_id'], unique=False)
