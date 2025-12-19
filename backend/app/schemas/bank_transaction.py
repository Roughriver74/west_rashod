"""Bank transaction schemas."""
from typing import Optional, List, Any, Dict
from pydantic import BaseModel
from datetime import datetime, date
from decimal import Decimal

from app.db.models import (
    BankTransactionTypeEnum,
    BankTransactionStatusEnum,
    PaymentSourceEnum,
    RegionEnum,
    DocumentTypeEnum,
)


class BankTransactionBase(BaseModel):
    """Base bank transaction schema."""
    transaction_date: date
    amount: Decimal
    transaction_type: BankTransactionTypeEnum = BankTransactionTypeEnum.DEBIT

    # Counterparty
    counterparty_name: Optional[str] = None
    counterparty_inn: Optional[str] = None
    counterparty_kpp: Optional[str] = None
    counterparty_account: Optional[str] = None
    counterparty_bank: Optional[str] = None
    counterparty_bik: Optional[str] = None

    # Payment details
    payment_purpose: Optional[str] = None
    business_operation: Optional[str] = None
    payment_source: PaymentSourceEnum = PaymentSourceEnum.BANK

    # Our organization
    organization_id: Optional[int] = None
    account_number: Optional[str] = None

    # Document
    document_number: Optional[str] = None
    document_date: Optional[date] = None

    # Classification
    category_id: Optional[int] = None

    # Status
    status: BankTransactionStatusEnum = BankTransactionStatusEnum.NEW

    # Additional
    notes: Optional[str] = None
    region: Optional[RegionEnum] = None
    exhibition: Optional[str] = None
    document_type: Optional[DocumentTypeEnum] = None

    # Currency breakdown
    amount_rub_credit: Optional[Decimal] = None
    amount_eur_credit: Optional[Decimal] = None
    amount_rub_debit: Optional[Decimal] = None
    amount_eur_debit: Optional[Decimal] = None

    # Time periods
    transaction_month: Optional[int] = None
    transaction_year: Optional[int] = None
    expense_acceptance_month: Optional[int] = None
    expense_acceptance_year: Optional[int] = None

    department_id: int


class BankTransactionCreate(BankTransactionBase):
    """Create bank transaction schema."""
    pass


class BankTransactionUpdate(BaseModel):
    """Update bank transaction schema."""
    transaction_date: Optional[date] = None
    amount: Optional[Decimal] = None
    transaction_type: Optional[BankTransactionTypeEnum] = None
    counterparty_name: Optional[str] = None
    counterparty_inn: Optional[str] = None
    counterparty_kpp: Optional[str] = None
    counterparty_account: Optional[str] = None
    counterparty_bank: Optional[str] = None
    counterparty_bik: Optional[str] = None
    payment_purpose: Optional[str] = None
    business_operation: Optional[str] = None
    payment_source: Optional[PaymentSourceEnum] = None
    organization_id: Optional[int] = None
    account_number: Optional[str] = None
    document_number: Optional[str] = None
    document_date: Optional[date] = None
    category_id: Optional[int] = None
    status: Optional[BankTransactionStatusEnum] = None
    notes: Optional[str] = None
    region: Optional[RegionEnum] = None
    exhibition: Optional[str] = None
    document_type: Optional[DocumentTypeEnum] = None
    amount_rub_credit: Optional[Decimal] = None
    amount_eur_credit: Optional[Decimal] = None
    amount_rub_debit: Optional[Decimal] = None
    amount_eur_debit: Optional[Decimal] = None
    transaction_month: Optional[int] = None
    transaction_year: Optional[int] = None
    expense_acceptance_month: Optional[int] = None
    expense_acceptance_year: Optional[int] = None
    is_active: Optional[bool] = None


class BankTransactionCategorize(BaseModel):
    """Categorize transaction schema."""
    category_id: int
    notes: Optional[str] = None


class BankTransactionBulkCategorize(BaseModel):
    """Bulk categorize transactions schema."""
    transaction_ids: List[int]
    category_id: int


class BankTransactionBulkStatusUpdate(BaseModel):
    """Bulk status update schema."""
    transaction_ids: List[int]
    status: BankTransactionStatusEnum


class BankTransactionInDB(BankTransactionBase):
    """Bank transaction in database."""
    id: int
    category_confidence: Optional[float] = None
    suggested_category_id: Optional[int] = None
    is_regular_payment: bool = False
    regular_payment_pattern_id: Optional[int] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    import_source: Optional[str] = None
    import_file_name: Optional[str] = None
    imported_at: Optional[datetime] = None
    external_id_1c: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BankTransactionResponse(BankTransactionInDB):
    """Bank transaction response with related data."""
    category_name: Optional[str] = None
    organization_name: Optional[str] = None
    suggested_category_name: Optional[str] = None


class BankTransactionStats(BaseModel):
    """Bank transaction statistics."""
    total: int = 0
    new: int = 0
    categorized: int = 0
    approved: int = 0
    needs_review: int = 0
    ignored: int = 0
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")


class BankTransactionImportResult(BaseModel):
    """Import result schema."""
    success: bool
    imported: int = 0
    skipped: int = 0
    total_rows: int = 0
    errors: List[Dict[str, Any]] = []
    error: Optional[str] = None


class BankTransactionImportPreview(BaseModel):
    """Import preview schema."""
    success: bool
    columns: List[str] = []
    detected_mapping: Dict[str, str] = {}
    sample_data: List[Dict[str, Any]] = []
    total_rows: int = 0
    required_fields: Dict[str, str] = {}
    error: Optional[str] = None


class CategorySuggestion(BaseModel):
    """Category suggestion from AI."""
    category_id: int
    category_name: str
    confidence: float
    reasoning: Optional[str] = None
