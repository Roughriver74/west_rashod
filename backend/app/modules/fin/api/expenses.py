"""
API endpoints for Fin Expenses (Списания).
Adapted from west_fin for synchronous SQLAlchemy.
"""
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.utils.auth import get_current_active_user
from app.db.models import User, Organization
from app.modules.fin.models import FinExpense, FinExpenseDetail, FinBankAccount, FinContract
from app.modules.fin.schemas import FinExpenseList

router = APIRouter()


@router.get("/", response_model=FinExpenseList)
def get_expenses(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=10000000, description="Number of records to return"),
    organizations: Optional[str] = Query(None, description="Filter by organizations (comma-separated)"),
    recipients: Optional[str] = Query(None, description="Filter by recipients (comma-separated)"),
    date_from: Optional[str] = Query(None, description="Filter by document date from (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter by document date to (YYYY-MM-DD)"),
    contracts: Optional[str] = Query(None, description="Filter by contract numbers (comma-separated)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get paginated list of fin expenses with optional filters."""
    query = db.query(FinExpense)

    # Filter by organizations
    if organizations:
        org_list = [o.strip() for o in organizations.split(",") if o.strip()]
        if org_list:
            org_ids = db.query(Organization.id).filter(Organization.name.in_(org_list)).all()
            org_ids = [o[0] for o in org_ids]
            if org_ids:
                query = query.filter(FinExpense.organization_id.in_(org_ids))

    # Filter by recipients
    if recipients:
        recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]
        if recipient_list:
            query = query.filter(FinExpense.recipient.in_(recipient_list))

    # Filter by contracts
    if contracts:
        contract_list = [c.strip() for c in contracts.split(",") if c.strip()]
        if contract_list:
            contract_ids = db.query(FinContract.id).filter(
                FinContract.contract_number.in_(contract_list)
            ).all()
            contract_ids = [c[0] for c in contract_ids]
            if contract_ids:
                query = query.filter(FinExpense.contract_id.in_(contract_ids))

    # Filter by date range
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(FinExpense.document_date >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(FinExpense.document_date <= date_to_obj)
        except ValueError:
            pass

    # Get total count
    total = query.count()

    # Get paginated results
    expenses = query.order_by(FinExpense.document_date.desc()).offset(skip).limit(limit).all()

    # Build response
    items = []
    for expense in expenses:
        items.append({
            "id": expense.id,
            "operation_id": expense.operation_id,
            "organization": expense.org.name if expense.org else None,
            "organization_id": expense.organization_id,
            "operation_type": expense.operation_type,
            "bank_account": expense.bank.account_number if expense.bank else None,
            "bank_account_id": expense.bank_account_id,
            "accounting_account": expense.accounting_account,
            "document_number": expense.document_number,
            "document_date": expense.document_date,
            "recipient": expense.recipient,
            "recipient_account": expense.recipient_account,
            "debit_account": expense.debit_account,
            "contract_number": expense.contract.contract_number if expense.contract else None,
            "contract_id": expense.contract_id,
            "contract_date": expense.contract_date,
            "currency": expense.currency,
            "amount": float(expense.amount) if expense.amount else 0,
            "expense_article": expense.expense_article,
            "payment_purpose": expense.payment_purpose,
            "responsible_person": expense.responsible_person,
            "comment": expense.comment,
            "tax_period": expense.tax_period,
            "unconfirmed_by_bank": expense.unconfirmed_by_bank,
            "created_at": expense.created_at,
            "updated_at": expense.updated_at
        })

    return {"total": total, "items": items}


@router.get("/summary")
def get_expenses_summary(
    organizations: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get summary statistics for fin expenses."""
    query = db.query(FinExpense)

    # Apply filters
    if organizations:
        org_list = [o.strip() for o in organizations.split(",") if o.strip()]
        if org_list:
            org_ids = db.query(Organization.id).filter(Organization.name.in_(org_list)).all()
            org_ids = [o[0] for o in org_ids]
            if org_ids:
                query = query.filter(FinExpense.organization_id.in_(org_ids))

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(FinExpense.document_date >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(FinExpense.document_date <= date_to_obj)
        except ValueError:
            pass

    # Get count and sum
    total_count = query.count()
    total_amount = db.query(func.sum(FinExpense.amount)).filter(
        FinExpense.id.in_(query.with_entities(FinExpense.id))
    ).scalar() or 0

    return {
        "total_records": total_count,
        "total_amount": float(total_amount)
    }


@router.get("/details/all")
def get_all_expense_details(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(200000, ge=1, le=500000, description="Number of records to return"),
    date_from: Optional[str] = Query(None, description="Filter by document date from (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter by document date to (YYYY-MM-DD)"),
    organizations: Optional[str] = Query(None, description="Filter by organizations (comma-separated names)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all expense details with payment_type for credit calculations."""
    query = db.query(FinExpenseDetail).join(
        FinExpense, FinExpenseDetail.expense_operation_id == FinExpense.operation_id
    )

    # Apply organization filter
    if organizations:
        org_list = [o.strip() for o in organizations.split(",") if o.strip()]
        if org_list:
            org_ids = db.query(Organization.id).filter(Organization.name.in_(org_list)).all()
            org_ids = [o[0] for o in org_ids]
            if org_ids:
                query = query.filter(FinExpense.organization_id.in_(org_ids))

    # Apply date filters
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(FinExpense.document_date >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(FinExpense.document_date <= date_to_obj)
        except ValueError:
            pass

    # Get total count
    total = query.count()

    # Get paginated results
    details = query.offset(skip).limit(limit).all()

    items = []
    for detail in details:
        items.append({
            "id": detail.id,
            "expense_operation_id": detail.expense_operation_id,
            "contract_number": detail.contract_number,
            "repayment_type": detail.repayment_type,
            "settlement_account": detail.settlement_account,
            "advance_account": detail.advance_account,
            "payment_type": detail.payment_type,
            "payment_amount": float(detail.payment_amount) if detail.payment_amount else 0,
            "settlement_rate": float(detail.settlement_rate) if detail.settlement_rate else 1,
            "settlement_amount": float(detail.settlement_amount) if detail.settlement_amount else 0,
            "vat_amount": float(detail.vat_amount) if detail.vat_amount else 0,
            "expense_amount": float(detail.expense_amount) if detail.expense_amount else 0,
            "vat_in_expense": float(detail.vat_in_expense) if detail.vat_in_expense else 0,
        })

    return {"total": total, "items": items}


@router.get("/{expense_id}")
def get_expense(
    expense_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get single fin expense by ID with details."""
    expense = db.query(FinExpense).filter(FinExpense.id == expense_id).first()

    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Get expense details
    details = db.query(FinExpenseDetail).filter(
        FinExpenseDetail.expense_operation_id == expense.operation_id
    ).all()

    details_list = []
    for detail in details:
        details_list.append({
            "id": detail.id,
            "contract_number": detail.contract_number,
            "repayment_type": detail.repayment_type,
            "settlement_account": detail.settlement_account,
            "advance_account": detail.advance_account,
            "payment_type": detail.payment_type,
            "payment_amount": float(detail.payment_amount) if detail.payment_amount else 0,
            "settlement_rate": float(detail.settlement_rate) if detail.settlement_rate else 1,
            "settlement_amount": float(detail.settlement_amount) if detail.settlement_amount else 0,
            "vat_amount": float(detail.vat_amount) if detail.vat_amount else 0,
            "expense_amount": float(detail.expense_amount) if detail.expense_amount else 0,
            "vat_in_expense": float(detail.vat_in_expense) if detail.vat_in_expense else 0,
        })

    return {
        "id": expense.id,
        "operation_id": expense.operation_id,
        "organization": expense.org.name if expense.org else None,
        "organization_id": expense.organization_id,
        "operation_type": expense.operation_type,
        "bank_account": expense.bank.account_number if expense.bank else None,
        "bank_account_id": expense.bank_account_id,
        "accounting_account": expense.accounting_account,
        "document_number": expense.document_number,
        "document_date": expense.document_date,
        "recipient": expense.recipient,
        "recipient_account": expense.recipient_account,
        "debit_account": expense.debit_account,
        "contract_number": expense.contract.contract_number if expense.contract else None,
        "contract_id": expense.contract_id,
        "contract_date": expense.contract_date,
        "currency": expense.currency,
        "amount": float(expense.amount) if expense.amount else 0,
        "expense_article": expense.expense_article,
        "payment_purpose": expense.payment_purpose,
        "responsible_person": expense.responsible_person,
        "comment": expense.comment,
        "tax_period": expense.tax_period,
        "unconfirmed_by_bank": expense.unconfirmed_by_bank,
        "created_at": expense.created_at,
        "updated_at": expense.updated_at,
        "details": details_list
    }
