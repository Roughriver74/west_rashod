"""Database models for West Rashod - Bank Transactions Service."""
import enum
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Date, DateTime,
    Numeric, ForeignKey, Enum, Index, func
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# ============== ENUMS ==============

class UserRoleEnum(str, enum.Enum):
    """User roles."""
    ADMIN = "ADMIN"
    FOUNDER = "FOUNDER"
    MANAGER = "MANAGER"
    ACCOUNTANT = "ACCOUNTANT"
    HR = "HR"
    USER = "USER"
    REQUESTER = "REQUESTER"


class ExpenseTypeEnum(str, enum.Enum):
    """Budget category types."""
    OPEX = "OPEX"
    CAPEX = "CAPEX"


class BankTransactionTypeEnum(str, enum.Enum):
    """Bank transaction types."""
    DEBIT = "DEBIT"    # Outgoing (expense)
    CREDIT = "CREDIT"  # Incoming (revenue)


class BankTransactionStatusEnum(str, enum.Enum):
    """Bank transaction processing statuses."""
    NEW = "NEW"                    # Not processed
    CATEGORIZED = "CATEGORIZED"    # Category assigned
    MATCHED = "MATCHED"            # Kept for compatibility
    APPROVED = "APPROVED"          # Verified
    NEEDS_REVIEW = "NEEDS_REVIEW"  # Low confidence
    IGNORED = "IGNORED"            # Ignored


class PaymentSourceEnum(str, enum.Enum):
    """Payment source types."""
    BANK = "BANK"  # Bank transfer
    CASH = "CASH"  # Cash payment


class RegionEnum(str, enum.Enum):
    """Regions."""
    MOSCOW = "MOSCOW"
    SPB = "SPB"
    REGIONS = "REGIONS"
    FOREIGN = "FOREIGN"


class DocumentTypeEnum(str, enum.Enum):
    """Document types."""
    PAYMENT_ORDER = "PAYMENT_ORDER"
    CASH_ORDER = "CASH_ORDER"
    INVOICE = "INVOICE"
    ACT = "ACT"
    CONTRACT = "CONTRACT"
    OTHER = "OTHER"


class ExpenseStatusEnum(str, enum.Enum):
    """Expense request status."""
    DRAFT = "DRAFT"                  # Черновик
    PENDING = "PENDING"              # На согласовании
    APPROVED = "APPROVED"            # Согласовано
    REJECTED = "REJECTED"            # Отклонено
    PAID = "PAID"                    # Оплачено
    PARTIALLY_PAID = "PARTIALLY_PAID"  # Частично оплачено
    CANCELLED = "CANCELLED"          # Отменено


class ExpensePriorityEnum(str, enum.Enum):
    """Expense priority."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class CategorizationRuleTypeEnum(str, enum.Enum):
    """Categorization rule types."""
    COUNTERPARTY_INN = "COUNTERPARTY_INN"         # Match by contractor INN
    COUNTERPARTY_NAME = "COUNTERPARTY_NAME"       # Match by contractor name
    BUSINESS_OPERATION = "BUSINESS_OPERATION"     # Match by 1C business operation
    KEYWORD = "KEYWORD"                           # Match by keyword in payment purpose


class BackgroundTaskStatusEnum(str, enum.Enum):
    """Background task statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============== MODELS ==============

class Organization(Base):
    """Organization model."""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    legal_name = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # 1C Integration
    external_id_1c = Column(String(100), unique=True, nullable=True, index=True)
    full_name = Column(String(500), nullable=True)
    short_name = Column(String(255), nullable=True)
    inn = Column(String(20), nullable=True, index=True)
    kpp = Column(String(20), nullable=True)
    ogrn = Column(String(20), nullable=True)
    prefix = Column(String(10), nullable=True)
    okpo = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    status_1c = Column(String(50), nullable=True)
    synced_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    bank_transactions = relationship("BankTransaction", back_populates="organization_rel")


class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRoleEnum), default=UserRoleEnum.USER, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Profile
    position = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    last_login = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    reviewed_transactions = relationship("BankTransaction", back_populates="reviewed_by_rel",
                                         foreign_keys="BankTransaction.reviewed_by")


class BudgetCategory(Base):
    """Budget category model for transaction classification."""
    __tablename__ = "budget_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(Enum(ExpenseTypeEnum), nullable=False)  # OPEX/CAPEX
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Hierarchy
    parent_id = Column(Integer, ForeignKey("budget_categories.id"), nullable=True)

    # 1C Integration
    external_id_1c = Column(String(100), nullable=True, index=True)
    code_1c = Column(String(50), nullable=True)
    is_folder = Column(Boolean, default=False)
    order_index = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    parent = relationship("BudgetCategory", remote_side=[id], backref="children")
    bank_transactions = relationship("BankTransaction", back_populates="category_rel",
                                     foreign_keys="BankTransaction.category_id")
    suggested_transactions = relationship("BankTransaction", back_populates="suggested_category_rel",
                                          foreign_keys="BankTransaction.suggested_category_id")


class Contractor(Base):
    """Contractor (counterparty) model."""
    __tablename__ = "contractors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False)
    short_name = Column(String(255), nullable=True)
    inn = Column(String(20), nullable=True, index=True)
    kpp = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    contact_info = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # 1C Integration
    external_id_1c = Column(String(100), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    expenses = relationship("Expense", back_populates="contractor_rel")


class Expense(Base):
    """Expense request model - заявка на расход."""
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    number = Column(String(50), unique=True, nullable=False, index=True)  # Номер заявки
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Amounts
    amount = Column(Numeric(15, 2), nullable=False)
    amount_paid = Column(Numeric(15, 2), default=0)  # Уже оплачено
    currency = Column(String(3), default="RUB")

    # Dates
    request_date = Column(Date, nullable=False, index=True)  # Дата заявки
    due_date = Column(Date, nullable=True)  # Срок оплаты
    payment_date = Column(Date, nullable=True)  # Фактическая дата оплаты

    # Classification
    category_id = Column(Integer, ForeignKey("budget_categories.id"), nullable=True, index=True)
    expense_type = Column(Enum(ExpenseTypeEnum), nullable=True)  # OPEX/CAPEX

    # Counterparty
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=True, index=True)
    contractor_name = Column(String(500), nullable=True)  # Denormalized for search
    contractor_inn = Column(String(20), nullable=True, index=True)

    # Organization
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)

    # Status and workflow
    status = Column(Enum(ExpenseStatusEnum), default=ExpenseStatusEnum.DRAFT, nullable=False, index=True)
    priority = Column(Enum(ExpensePriorityEnum), default=ExpensePriorityEnum.NORMAL)

    # Approval
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Documents
    invoice_number = Column(String(100), nullable=True)
    invoice_date = Column(Date, nullable=True)
    contract_number = Column(String(100), nullable=True)

    # Additional
    notes = Column(Text, nullable=True)
    payment_purpose = Column(Text, nullable=True)  # Назначение платежа

    # 1C Integration
    external_id_1c = Column(String(100), nullable=True, unique=True, index=True)

    # System
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    category_rel = relationship("BudgetCategory")
    contractor_rel = relationship("Contractor", back_populates="expenses")
    organization_rel = relationship("Organization")
    requested_by_rel = relationship("User", foreign_keys=[requested_by])
    approved_by_rel = relationship("User", foreign_keys=[approved_by])
    bank_transactions = relationship("BankTransaction", back_populates="expense_rel",
                                     foreign_keys="BankTransaction.expense_id")


class BankTransaction(Base):
    """Bank transaction model - main entity."""
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, index=True)

    # Basic transaction info
    transaction_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    transaction_type = Column(Enum(BankTransactionTypeEnum), nullable=False,
                             default=BankTransactionTypeEnum.DEBIT, index=True)

    # VAT (НДС)
    vat_amount = Column(Numeric(15, 2), nullable=True)  # Сумма НДС
    vat_rate = Column(Numeric(5, 2), nullable=True)  # Ставка НДС в процентах (0, 10, 20 и т.д.)

    # Counterparty
    counterparty_name = Column(String(500), nullable=True)
    counterparty_inn = Column(String(12), nullable=True, index=True)
    counterparty_kpp = Column(String(9), nullable=True)
    counterparty_account = Column(String(20), nullable=True)
    counterparty_bank = Column(String(500), nullable=True)
    counterparty_bik = Column(String(20), nullable=True)

    # Payment details
    payment_purpose = Column(Text, nullable=True)
    business_operation = Column(String(100), nullable=True, index=True)  # For auto-categorization from 1C

    # Payment source
    payment_source = Column(Enum(PaymentSourceEnum), default=PaymentSourceEnum.BANK, index=True)

    # Our organization
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    account_number = Column(String(20), nullable=True, index=True)

    # Our bank info (where our account is opened)
    our_bank_name = Column(String(500), nullable=True)
    our_bank_bik = Column(String(20), nullable=True, index=True)

    # Document info
    document_number = Column(String(50), nullable=True, index=True)
    document_date = Column(Date, nullable=True)

    # AI Classification
    category_id = Column(Integer, ForeignKey("budget_categories.id"), nullable=True, index=True)
    category_confidence = Column(Numeric(5, 4), nullable=True)  # 0.0000 - 1.0000
    suggested_category_id = Column(Integer, ForeignKey("budget_categories.id"), nullable=True)

    # Expense linking
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=True, index=True)
    suggested_expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=True)
    matching_score = Column(Numeric(5, 2), nullable=True)  # 0.00 - 100.00

    # Status
    status = Column(Enum(BankTransactionStatusEnum),
                   default=BankTransactionStatusEnum.NEW, nullable=False, index=True)

    # Additional info
    notes = Column(Text, nullable=True)
    is_regular_payment = Column(Boolean, default=False, nullable=False, index=True)
    regular_payment_pattern_id = Column(Integer, nullable=True)

    # Extended fields
    region = Column(Enum(RegionEnum), nullable=True, index=True)
    exhibition = Column(String(255), nullable=True)
    document_type = Column(Enum(DocumentTypeEnum), nullable=True)

    # Currency breakdown
    amount_rub_credit = Column(Numeric(15, 2), nullable=True)
    amount_eur_credit = Column(Numeric(15, 2), nullable=True)
    amount_rub_debit = Column(Numeric(15, 2), nullable=True)
    amount_eur_debit = Column(Numeric(15, 2), nullable=True)

    # Time periods
    transaction_month = Column(Integer, nullable=True, index=True)
    transaction_year = Column(Integer, nullable=True, index=True)
    expense_acceptance_month = Column(Integer, nullable=True)
    expense_acceptance_year = Column(Integer, nullable=True)

    # Review
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # Import tracking
    import_source = Column(String(50), nullable=True)  # ODATA_1C, MANUAL_UPLOAD, API
    import_file_name = Column(String(255), nullable=True)
    imported_at = Column(DateTime, nullable=True)

    # 1C Integration
    external_id_1c = Column(String(100), nullable=True, unique=True, index=True)

    # System fields
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    organization_rel = relationship("Organization", back_populates="bank_transactions")
    category_rel = relationship("BudgetCategory", back_populates="bank_transactions",
                               foreign_keys=[category_id])
    suggested_category_rel = relationship("BudgetCategory", back_populates="suggested_transactions",
                                         foreign_keys=[suggested_category_id])
    reviewed_by_rel = relationship("User", back_populates="reviewed_transactions",
                                  foreign_keys=[reviewed_by])
    expense_rel = relationship("Expense", back_populates="bank_transactions",
                              foreign_keys=[expense_id])
    suggested_expense_rel = relationship("Expense", foreign_keys=[suggested_expense_id])


class BusinessOperationMapping(Base):
    """Mapping of 1C business operations to budget categories."""
    __tablename__ = "business_operation_mappings"

    id = Column(Integer, primary_key=True, index=True)
    business_operation = Column(String(100), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("budget_categories.id"), nullable=True, index=True)

    # Priority and confidence
    priority = Column(Integer, default=10)  # Higher = more important
    confidence = Column(Numeric(5, 4), default=0.98)  # 0.0000 - 1.0000

    # Notes
    notes = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    category_rel = relationship("BudgetCategory")
    created_by_user = relationship("User")

    # Unique constraint
    __table_args__ = (
        Index('ix_business_op_mapping_unique', 'business_operation', 'category_id', unique=True),
    )


class CategorizationRule(Base):
    """Categorization rules for automatic transaction classification."""
    __tablename__ = "categorization_rules"

    id = Column(Integer, primary_key=True, index=True)

    # Rule type
    rule_type = Column(Enum(CategorizationRuleTypeEnum), nullable=False, index=True)

    # Match criteria (only one should be set based on rule_type)
    counterparty_inn = Column(String(20), nullable=True, index=True)
    counterparty_name = Column(String(500), nullable=True, index=True)
    business_operation = Column(String(100), nullable=True, index=True)
    keyword = Column(String(255), nullable=True, index=True)

    # Target category
    category_id = Column(Integer, ForeignKey("budget_categories.id"), nullable=False, index=True)

    # Priority and confidence
    priority = Column(Integer, default=10, nullable=False)  # Higher = more important
    confidence = Column(Numeric(5, 4), default=0.95, nullable=False)  # 0.0000 - 1.0000

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    category_rel = relationship("BudgetCategory")
    created_by_user = relationship("User")


class SyncSettings(Base):
    """Settings for automatic 1C synchronization (singleton table)."""
    __tablename__ = "sync_settings"

    id = Column(Integer, primary_key=True, default=1)  # Singleton

    # Scheduler settings
    auto_sync_enabled = Column(Boolean, default=False, nullable=False)
    sync_interval_hours = Column(Integer, default=4, nullable=False)  # Every N hours
    sync_time_hour = Column(Integer, nullable=True)  # Specific hour (0-23) or None for interval
    sync_time_minute = Column(Integer, default=0, nullable=False)  # Minute (0-59)

    # Sync options
    auto_classify = Column(Boolean, default=True, nullable=False)
    sync_days_back = Column(Integer, default=30, nullable=False)  # How many days back to sync

    # Last sync info
    last_sync_started_at = Column(DateTime, nullable=True)
    last_sync_completed_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(50), nullable=True)  # SUCCESS, FAILED, IN_PROGRESS
    last_sync_message = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    updated_by_rel = relationship("User", foreign_keys=[updated_by])


class BackgroundTask(Base):
    """Background tasks stored in database for persistence across restarts."""
    __tablename__ = "background_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    task_type = Column(String(100), nullable=False, index=True)
    status = Column(Enum(BackgroundTaskStatusEnum), nullable=False, default=BackgroundTaskStatusEnum.PENDING, index=True)

    # Progress tracking
    progress = Column(Integer, default=0, nullable=False)
    total = Column(Integer, default=0, nullable=False)
    processed = Column(Integer, default=0, nullable=False)
    message = Column(Text, nullable=True)

    # Result/Error
    result = Column(Text, nullable=True)  # JSON serialized
    error = Column(Text, nullable=True)

    # Extra data (JSON serialized)
    extra_data = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # User who started the task
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_rel = relationship("User")

    __table_args__ = (
        Index('ix_background_tasks_status_created', 'status', 'created_at'),
    )
