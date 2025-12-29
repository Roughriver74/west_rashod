"""
SQLAlchemy models for Fin module (Financial Data Warehouse)
Imported and adapted from west_fin project
All tables have 'fin_' prefix to avoid conflicts with main app tables
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Date, DateTime,
    Numeric, Boolean, ForeignKey, func, Index
)
from sqlalchemy.orm import relationship

from app.db.models import Base


class FinBankAccount(Base):
    """Model for bank accounts (Банковские счета) - FTP data source"""
    __tablename__ = "fin_bank_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_number = Column(String(255), unique=True, nullable=False, index=True)
    bank_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    receipts = relationship("FinReceipt", back_populates="bank")
    expenses = relationship("FinExpense", back_populates="bank")

    def __repr__(self):
        return f"<FinBankAccount(id={self.id}, account='{self.account_number}')>"


class FinContract(Base):
    """Model for contracts (Договоры) - credits, loans, etc."""
    __tablename__ = "fin_contracts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_number = Column(String(255), unique=True, nullable=False, index=True)
    contract_date = Column(Date, index=True)
    contract_type = Column(String(100))  # Кредит, Заем, и т.д.
    counterparty = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    receipts = relationship("FinReceipt", back_populates="contract")
    expenses = relationship("FinExpense", back_populates="contract")

    def __repr__(self):
        return f"<FinContract(id={self.id}, number='{self.contract_number}')>"


class FinReceipt(Base):
    """Model for receipts (Поступления) - from FTP Excel import"""
    __tablename__ = "fin_receipts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    operation_id = Column(String(255), unique=True, nullable=False, index=True)

    # Foreign keys
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True, nullable=True)
    bank_account_id = Column(Integer, ForeignKey("fin_bank_accounts.id"), index=True)
    contract_id = Column(Integer, ForeignKey("fin_contracts.id"), index=True)

    operation_type = Column(String(255))
    accounting_account = Column(String(50))
    document_number = Column(String(255))
    document_date = Column(Date, index=True)
    payer = Column(String(255), index=True)
    payer_account = Column(String(255))
    settlement_account = Column(String(100))
    contract_date = Column(Date)
    currency = Column(String(10))
    amount = Column(Numeric(15, 2), nullable=False)
    commission = Column(Numeric(15, 2))
    payment_purpose = Column(Text)
    responsible_person = Column(String(255))
    comment = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    org = relationship("Organization", foreign_keys=[organization_id])
    bank = relationship("FinBankAccount", back_populates="receipts")
    contract = relationship("FinContract", back_populates="receipts")

    def __repr__(self):
        return f"<FinReceipt(id={self.id}, operation_id='{self.operation_id}', amount={self.amount})>"


class FinExpense(Base):
    """Model for expenses (Списания) - from FTP Excel import"""
    __tablename__ = "fin_expenses"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    operation_id = Column(String(255), unique=True, nullable=False, index=True)

    # Foreign keys
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True, nullable=True)
    bank_account_id = Column(Integer, ForeignKey("fin_bank_accounts.id"), index=True)
    contract_id = Column(Integer, ForeignKey("fin_contracts.id"), index=True)

    operation_type = Column(String(255))
    accounting_account = Column(String(50))
    document_number = Column(String(255))
    document_date = Column(Date, index=True)
    recipient = Column(String(255), index=True)
    recipient_account = Column(String(255))
    debit_account = Column(String(100))
    contract_date = Column(Date)
    currency = Column(String(10))
    amount = Column(Numeric(15, 2), nullable=False)
    expense_article = Column(String(255), index=True)
    payment_purpose = Column(Text)
    responsible_person = Column(String(255))
    comment = Column(Text)
    tax_period = Column(String(10))
    unconfirmed_by_bank = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    org = relationship("Organization", foreign_keys=[organization_id])
    bank = relationship("FinBankAccount", back_populates="expenses")
    contract = relationship("FinContract", back_populates="expenses")
    details = relationship("FinExpenseDetail", back_populates="expense", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FinExpense(id={self.id}, operation_id='{self.operation_id}', amount={self.amount})>"


class FinExpenseDetail(Base):
    """Model for expense details (Расшифровка) - VAT, payment types"""
    __tablename__ = "fin_expense_details"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    expense_operation_id = Column(
        String(255),
        ForeignKey("fin_expenses.operation_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    contract_number = Column(String(255), index=True)
    repayment_type = Column(String(100))
    settlement_account = Column(String(100), index=True)
    advance_account = Column(String(100))
    payment_type = Column(String(255), index=True)
    payment_amount = Column(Numeric(15, 2))
    settlement_rate = Column(Numeric(15, 6), default=1)
    settlement_amount = Column(Numeric(15, 2))
    vat_amount = Column(Numeric(15, 2))
    expense_amount = Column(Numeric(15, 2))
    vat_in_expense = Column(Numeric(15, 2))
    created_at = Column(DateTime, default=func.now())

    # Relationship to expense
    expense = relationship("FinExpense", back_populates="details")

    def __repr__(self):
        return f"<FinExpenseDetail(id={self.id}, expense_operation_id='{self.expense_operation_id}')>"


class FinImportLog(Base):
    """Model for FTP import logs"""
    __tablename__ = "fin_import_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    import_date = Column(DateTime, default=func.now(), index=True)
    source_file = Column(String(255), index=True)
    table_name = Column(String(50), index=True)
    rows_inserted = Column(Integer, default=0)
    rows_updated = Column(Integer, default=0)
    rows_failed = Column(Integer, default=0)
    status = Column(String(50), index=True)
    error_message = Column(Text)
    processed_by = Column(String(100))
    processing_time_seconds = Column(Numeric(10, 2))

    def __repr__(self):
        return (
            f"<FinImportLog(id={self.id}, source_file='{self.source_file}', "
            f"status='{self.status}')>"
        )


class FinManualAdjustment(Base):
    """Model for manual adjustments (Ручные корректировки)

    These records are NOT deleted during import from FTP.
    Used to manually add receipts/expenses that may be missing or incorrect.
    """
    __tablename__ = "fin_manual_adjustments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Contract reference
    contract_id = Column(Integer, ForeignKey("fin_contracts.id", ondelete="SET NULL"), index=True)
    contract_number = Column(String(255), index=True)

    # Adjustment type: 'receipt' or 'expense'
    adjustment_type = Column(String(20), nullable=False, index=True)

    # Payment type for expenses: 'Погашение долга', 'Уплата процентов'
    payment_type = Column(String(100), index=True)

    # Financial data
    amount = Column(Numeric(15, 2), nullable=False)
    document_date = Column(Date, nullable=False, index=True)
    document_number = Column(String(255))

    # Counterparty (payer for receipts, recipient for expenses)
    counterparty = Column(String(255), index=True)

    # Organization and bank account
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), index=True)
    bank_account_id = Column(Integer, ForeignKey("fin_bank_accounts.id", ondelete="SET NULL"), index=True)

    # Accounting account
    accounting_account = Column(String(50))

    # Metadata
    description = Column(Text)
    comment = Column(Text)
    created_by = Column(String(255))

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    contract = relationship("FinContract")
    org = relationship("Organization", foreign_keys=[organization_id])
    bank = relationship("FinBankAccount")

    def __repr__(self):
        return (
            f"<FinManualAdjustment(id={self.id}, type='{self.adjustment_type}', "
            f"amount={self.amount}, contract='{self.contract_number}')>"
        )


class FinExcludedPayer(Base):
    """Persisted list of payers to exclude from analytics/dashboards"""
    __tablename__ = "fin_excluded_payers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    payer_name = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<FinExcludedPayer(id={self.id}, payer_name='{self.payer_name}')>"
