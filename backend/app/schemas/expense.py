"""Expense schemas."""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, date
from decimal import Decimal

from app.db.models import ExpenseStatusEnum, ExpensePriorityEnum, ExpenseTypeEnum


class ExpenseBase(BaseModel):
    """Base expense schema."""
    title: str
    description: Optional[str] = None
    amount: Decimal
    currency: str = "RUB"
    request_date: date
    due_date: Optional[date] = None

    # Classification
    category_id: Optional[int] = None
    expense_type: Optional[ExpenseTypeEnum] = None

    # Counterparty
    contractor_id: Optional[int] = None
    contractor_name: Optional[str] = None
    contractor_inn: Optional[str] = None

    # Organization
    organization_id: Optional[int] = None

    # Priority
    priority: ExpensePriorityEnum = ExpensePriorityEnum.NORMAL

    # Documents
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    contract_number: Optional[str] = None

    # Additional
    notes: Optional[str] = None
    payment_purpose: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    """Create expense schema."""
    pass


class ExpenseUpdate(BaseModel):
    """Update expense schema."""
    title: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    request_date: Optional[date] = None
    due_date: Optional[date] = None
    payment_date: Optional[date] = None
    category_id: Optional[int] = None
    expense_type: Optional[ExpenseTypeEnum] = None
    contractor_id: Optional[int] = None
    contractor_name: Optional[str] = None
    contractor_inn: Optional[str] = None
    organization_id: Optional[int] = None
    status: Optional[ExpenseStatusEnum] = None
    priority: Optional[ExpensePriorityEnum] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    contract_number: Optional[str] = None
    notes: Optional[str] = None
    payment_purpose: Optional[str] = None


class ExpenseInDB(ExpenseBase):
    """Expense in database."""
    id: int
    number: str
    amount_paid: Decimal = Decimal("0")
    payment_date: Optional[date] = None
    status: ExpenseStatusEnum = ExpenseStatusEnum.DRAFT
    requested_by: Optional[int] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    external_id_1c: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExpenseResponse(ExpenseInDB):
    """Expense response with related data."""
    category_name: Optional[str] = None
    organization_name: Optional[str] = None
    requested_by_name: Optional[str] = None
    approved_by_name: Optional[str] = None
    remaining_amount: Optional[Decimal] = None
    linked_transactions_count: int = 0
    linked_transactions_amount: Decimal = Decimal("0")


class ExpenseStats(BaseModel):
    """Expense statistics."""
    total: int = 0
    draft: int = 0
    pending: int = 0
    approved: int = 0
    rejected: int = 0
    paid: int = 0
    partially_paid: int = 0
    cancelled: int = 0
    total_amount: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")
    total_pending: Decimal = Decimal("0")


class ExpenseList(BaseModel):
    """List of expenses with pagination."""
    total: int
    items: List[ExpenseResponse]
    page: int
    page_size: int
    pages: int


# ==================== Expense Matching ====================

class MatchingSuggestion(BaseModel):
    """Expense matching suggestion for bank transaction."""
    expense_id: int
    expense_number: str
    expense_title: str
    expense_amount: Decimal
    expense_date: date
    expense_category_id: Optional[int] = None
    expense_category_name: Optional[str] = None
    expense_contractor_name: Optional[str] = None
    expense_contractor_inn: Optional[str] = None
    expense_status: str
    remaining_amount: Decimal
    matching_score: float  # 0.0 - 100.0
    match_reasons: List[str]


class BankTransactionLink(BaseModel):
    """Link bank transaction to expense."""
    expense_id: int
    notes: Optional[str] = None


class BulkLinkRequest(BaseModel):
    """Bulk link transactions to expenses."""
    links: List[dict]  # [{"transaction_id": 1, "expense_id": 10}, ...]


class BulkLinkResponse(BaseModel):
    """Bulk link response."""
    success: bool
    linked_count: int
    errors: List[dict] = []


# ==================== Expense Approval ====================

class ExpenseApproval(BaseModel):
    """Approve or reject expense."""
    action: str  # "approve" or "reject"
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None
