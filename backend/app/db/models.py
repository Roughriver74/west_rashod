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


# ============== MODELS ==============

class Department(Base):
    """Department model for multi-tenancy."""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Hierarchy
    parent_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    hierarchy_path = Column(String(1024), default="")
    hierarchy_level = Column(Integer, default=0)

    # Additional info
    region = Column(String(50), nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    parent = relationship("Department", remote_side=[id], backref="children")
    users = relationship("User", back_populates="department_rel")
    bank_transactions = relationship("BankTransaction", back_populates="department_rel")


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

    # Multi-tenancy
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)

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

    # Department (multi-tenancy)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)

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
    department_rel = relationship("Department", back_populates="users")
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

    # Multi-tenancy
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)

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

    # Composite index
    __table_args__ = (
        Index('idx_budget_category_dept_active', 'department_id', 'is_active'),
    )


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

    # Multi-tenancy
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Composite index
    __table_args__ = (
        Index('idx_contractor_dept_active', 'department_id', 'is_active'),
    )


class BankTransaction(Base):
    """Bank transaction model - main entity."""
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, index=True)

    # Basic transaction info
    transaction_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    transaction_type = Column(Enum(BankTransactionTypeEnum), nullable=False,
                             default=BankTransactionTypeEnum.DEBIT, index=True)

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

    # Document info
    document_number = Column(String(50), nullable=True, index=True)
    document_date = Column(Date, nullable=True)

    # AI Classification
    category_id = Column(Integer, ForeignKey("budget_categories.id"), nullable=True, index=True)
    category_confidence = Column(Numeric(5, 4), nullable=True)  # 0.0000 - 1.0000
    suggested_category_id = Column(Integer, ForeignKey("budget_categories.id"), nullable=True)

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

    # Multi-tenancy
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)

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
    department_rel = relationship("Department", back_populates="bank_transactions")
    organization_rel = relationship("Organization", back_populates="bank_transactions")
    category_rel = relationship("BudgetCategory", back_populates="bank_transactions",
                               foreign_keys=[category_id])
    suggested_category_rel = relationship("BudgetCategory", back_populates="suggested_transactions",
                                         foreign_keys=[suggested_category_id])
    reviewed_by_rel = relationship("User", back_populates="reviewed_transactions",
                                  foreign_keys=[reviewed_by])


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

    # Multi-tenancy
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    category_rel = relationship("BudgetCategory")
    department_rel = relationship("Department")
    created_by_user = relationship("User")

    # Unique constraint
    __table_args__ = (
        Index('ix_business_op_mapping_unique', 'business_operation', 'department_id', 'category_id', unique=True),
    )
