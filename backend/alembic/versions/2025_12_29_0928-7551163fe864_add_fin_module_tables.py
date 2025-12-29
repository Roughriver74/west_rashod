"""Add fin module tables

Revision ID: 7551163fe864
Revises: 300e46a3b3c6
Create Date: 2025-12-29 09:28:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7551163fe864'
down_revision = '300e46a3b3c6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === fin_bank_accounts ===
    op.create_table('fin_bank_accounts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('account_number', sa.String(length=255), nullable=False),
        sa.Column('bank_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fin_bank_accounts_account_number', 'fin_bank_accounts', ['account_number'], unique=True)

    # === fin_contracts ===
    op.create_table('fin_contracts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('contract_number', sa.String(length=255), nullable=False),
        sa.Column('contract_date', sa.Date(), nullable=True),
        sa.Column('contract_type', sa.String(length=100), nullable=True),
        sa.Column('counterparty', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fin_contracts_contract_number', 'fin_contracts', ['contract_number'], unique=True)
    op.create_index('ix_fin_contracts_contract_date', 'fin_contracts', ['contract_date'], unique=False)

    # === fin_receipts ===
    op.create_table('fin_receipts',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('operation_id', sa.String(length=255), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('bank_account_id', sa.Integer(), nullable=True),
        sa.Column('contract_id', sa.Integer(), nullable=True),
        sa.Column('operation_type', sa.String(length=255), nullable=True),
        sa.Column('accounting_account', sa.String(length=50), nullable=True),
        sa.Column('document_number', sa.String(length=255), nullable=True),
        sa.Column('document_date', sa.Date(), nullable=True),
        sa.Column('payer', sa.String(length=255), nullable=True),
        sa.Column('payer_account', sa.String(length=255), nullable=True),
        sa.Column('settlement_account', sa.String(length=100), nullable=True),
        sa.Column('contract_date', sa.Date(), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('commission', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('payment_purpose', sa.Text(), nullable=True),
        sa.Column('responsible_person', sa.String(length=255), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['bank_account_id'], ['fin_bank_accounts.id'], ),
        sa.ForeignKeyConstraint(['contract_id'], ['fin_contracts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fin_receipts_operation_id', 'fin_receipts', ['operation_id'], unique=True)
    op.create_index('ix_fin_receipts_organization_id', 'fin_receipts', ['organization_id'], unique=False)
    op.create_index('ix_fin_receipts_bank_account_id', 'fin_receipts', ['bank_account_id'], unique=False)
    op.create_index('ix_fin_receipts_contract_id', 'fin_receipts', ['contract_id'], unique=False)
    op.create_index('ix_fin_receipts_document_date', 'fin_receipts', ['document_date'], unique=False)
    op.create_index('ix_fin_receipts_payer', 'fin_receipts', ['payer'], unique=False)

    # === fin_expenses ===
    op.create_table('fin_expenses',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('operation_id', sa.String(length=255), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('bank_account_id', sa.Integer(), nullable=True),
        sa.Column('contract_id', sa.Integer(), nullable=True),
        sa.Column('operation_type', sa.String(length=255), nullable=True),
        sa.Column('accounting_account', sa.String(length=50), nullable=True),
        sa.Column('document_number', sa.String(length=255), nullable=True),
        sa.Column('document_date', sa.Date(), nullable=True),
        sa.Column('recipient', sa.String(length=255), nullable=True),
        sa.Column('recipient_account', sa.String(length=255), nullable=True),
        sa.Column('debit_account', sa.String(length=100), nullable=True),
        sa.Column('contract_date', sa.Date(), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('expense_article', sa.String(length=255), nullable=True),
        sa.Column('payment_purpose', sa.Text(), nullable=True),
        sa.Column('responsible_person', sa.String(length=255), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('tax_period', sa.String(length=10), nullable=True),
        sa.Column('unconfirmed_by_bank', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['bank_account_id'], ['fin_bank_accounts.id'], ),
        sa.ForeignKeyConstraint(['contract_id'], ['fin_contracts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fin_expenses_operation_id', 'fin_expenses', ['operation_id'], unique=True)
    op.create_index('ix_fin_expenses_organization_id', 'fin_expenses', ['organization_id'], unique=False)
    op.create_index('ix_fin_expenses_bank_account_id', 'fin_expenses', ['bank_account_id'], unique=False)
    op.create_index('ix_fin_expenses_contract_id', 'fin_expenses', ['contract_id'], unique=False)
    op.create_index('ix_fin_expenses_document_date', 'fin_expenses', ['document_date'], unique=False)
    op.create_index('ix_fin_expenses_recipient', 'fin_expenses', ['recipient'], unique=False)
    op.create_index('ix_fin_expenses_expense_article', 'fin_expenses', ['expense_article'], unique=False)

    # === fin_expense_details ===
    op.create_table('fin_expense_details',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('expense_operation_id', sa.String(length=255), nullable=False),
        sa.Column('contract_number', sa.String(length=255), nullable=True),
        sa.Column('repayment_type', sa.String(length=100), nullable=True),
        sa.Column('settlement_account', sa.String(length=100), nullable=True),
        sa.Column('advance_account', sa.String(length=100), nullable=True),
        sa.Column('payment_type', sa.String(length=255), nullable=True),
        sa.Column('payment_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('settlement_rate', sa.Numeric(precision=15, scale=6), nullable=True, default=1),
        sa.Column('settlement_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('vat_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('expense_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('vat_in_expense', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['expense_operation_id'], ['fin_expenses.operation_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fin_expense_details_expense_operation_id', 'fin_expense_details', ['expense_operation_id'], unique=False)
    op.create_index('ix_fin_expense_details_contract_number', 'fin_expense_details', ['contract_number'], unique=False)
    op.create_index('ix_fin_expense_details_settlement_account', 'fin_expense_details', ['settlement_account'], unique=False)
    op.create_index('ix_fin_expense_details_payment_type', 'fin_expense_details', ['payment_type'], unique=False)

    # === fin_import_logs ===
    op.create_table('fin_import_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('import_date', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('source_file', sa.String(length=255), nullable=True),
        sa.Column('table_name', sa.String(length=50), nullable=True),
        sa.Column('rows_inserted', sa.Integer(), nullable=True, default=0),
        sa.Column('rows_updated', sa.Integer(), nullable=True, default=0),
        sa.Column('rows_failed', sa.Integer(), nullable=True, default=0),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processed_by', sa.String(length=100), nullable=True),
        sa.Column('processing_time_seconds', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fin_import_logs_import_date', 'fin_import_logs', ['import_date'], unique=False)
    op.create_index('ix_fin_import_logs_source_file', 'fin_import_logs', ['source_file'], unique=False)
    op.create_index('ix_fin_import_logs_table_name', 'fin_import_logs', ['table_name'], unique=False)
    op.create_index('ix_fin_import_logs_status', 'fin_import_logs', ['status'], unique=False)

    # === fin_manual_adjustments ===
    op.create_table('fin_manual_adjustments',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('contract_id', sa.Integer(), nullable=True),
        sa.Column('contract_number', sa.String(length=255), nullable=True),
        sa.Column('adjustment_type', sa.String(length=20), nullable=False),
        sa.Column('payment_type', sa.String(length=100), nullable=True),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('document_date', sa.Date(), nullable=False),
        sa.Column('document_number', sa.String(length=255), nullable=True),
        sa.Column('counterparty', sa.String(length=255), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('bank_account_id', sa.Integer(), nullable=True),
        sa.Column('accounting_account', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['contract_id'], ['fin_contracts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['bank_account_id'], ['fin_bank_accounts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fin_manual_adjustments_contract_id', 'fin_manual_adjustments', ['contract_id'], unique=False)
    op.create_index('ix_fin_manual_adjustments_contract_number', 'fin_manual_adjustments', ['contract_number'], unique=False)
    op.create_index('ix_fin_manual_adjustments_adjustment_type', 'fin_manual_adjustments', ['adjustment_type'], unique=False)
    op.create_index('ix_fin_manual_adjustments_payment_type', 'fin_manual_adjustments', ['payment_type'], unique=False)
    op.create_index('ix_fin_manual_adjustments_document_date', 'fin_manual_adjustments', ['document_date'], unique=False)
    op.create_index('ix_fin_manual_adjustments_counterparty', 'fin_manual_adjustments', ['counterparty'], unique=False)
    op.create_index('ix_fin_manual_adjustments_organization_id', 'fin_manual_adjustments', ['organization_id'], unique=False)
    op.create_index('ix_fin_manual_adjustments_bank_account_id', 'fin_manual_adjustments', ['bank_account_id'], unique=False)

    # === fin_excluded_payers ===
    op.create_table('fin_excluded_payers',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('payer_name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_fin_excluded_payers_payer_name', 'fin_excluded_payers', ['payer_name'], unique=True)


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('fin_excluded_payers')
    op.drop_table('fin_manual_adjustments')
    op.drop_table('fin_import_logs')
    op.drop_table('fin_expense_details')
    op.drop_table('fin_expenses')
    op.drop_table('fin_receipts')
    op.drop_table('fin_contracts')
    op.drop_table('fin_bank_accounts')
