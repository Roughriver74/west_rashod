"""
API endpoints for Fin Receipts (Поступления).
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
from app.modules.fin.models import FinReceipt, FinBankAccount, FinContract
from app.modules.fin.schemas import FinReceiptList

router = APIRouter()


@router.get("/", response_model=FinReceiptList)
def get_receipts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=10000000, description="Number of records to return"),
    organizations: Optional[str] = Query(None, description="Filter by organizations (comma-separated)"),
    payers: Optional[str] = Query(None, description="Filter by payers (comma-separated)"),
    date_from: Optional[str] = Query(None, description="Filter by document date from (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter by document date to (YYYY-MM-DD)"),
    contracts: Optional[str] = Query(None, description="Filter by contract numbers (comma-separated)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get paginated list of fin receipts with optional filters."""
    query = db.query(FinReceipt)

    # Filter by organizations
    if organizations:
        org_list = [o.strip() for o in organizations.split(",") if o.strip()]
        if org_list:
            org_ids = db.query(Organization.id).filter(Organization.name.in_(org_list)).all()
            org_ids = [o[0] for o in org_ids]
            if org_ids:
                query = query.filter(FinReceipt.organization_id.in_(org_ids))

    # Filter by payers
    if payers:
        payer_list = [p.strip() for p in payers.split(",") if p.strip()]
        if payer_list:
            query = query.filter(FinReceipt.payer.in_(payer_list))

    # Filter by contracts
    if contracts:
        contract_list = [c.strip() for c in contracts.split(",") if c.strip()]
        if contract_list:
            contract_ids = db.query(FinContract.id).filter(
                FinContract.contract_number.in_(contract_list)
            ).all()
            contract_ids = [c[0] for c in contract_ids]
            if contract_ids:
                query = query.filter(FinReceipt.contract_id.in_(contract_ids))

    # Filter by date range
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(FinReceipt.document_date >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(FinReceipt.document_date <= date_to_obj)
        except ValueError:
            pass

    # Get total count
    total = query.count()

    # Get paginated results
    receipts = query.order_by(FinReceipt.document_date.desc()).offset(skip).limit(limit).all()

    # Build response
    items = []
    for receipt in receipts:
        items.append({
            "id": receipt.id,
            "operation_id": receipt.operation_id,
            "organization": receipt.org.name if receipt.org else None,
            "organization_id": receipt.organization_id,
            "operation_type": receipt.operation_type,
            "bank_account": receipt.bank.account_number if receipt.bank else None,
            "bank_account_id": receipt.bank_account_id,
            "accounting_account": receipt.accounting_account,
            "document_number": receipt.document_number,
            "document_date": receipt.document_date,
            "payer": receipt.payer,
            "payer_account": receipt.payer_account,
            "settlement_account": receipt.settlement_account,
            "contract_number": receipt.contract.contract_number if receipt.contract else None,
            "contract_id": receipt.contract_id,
            "contract_date": receipt.contract_date,
            "currency": receipt.currency,
            "amount": float(receipt.amount) if receipt.amount else 0,
            "commission": float(receipt.commission) if receipt.commission else 0,
            "payment_purpose": receipt.payment_purpose,
            "responsible_person": receipt.responsible_person,
            "comment": receipt.comment,
            "created_at": receipt.created_at,
            "updated_at": receipt.updated_at
        })

    return {"total": total, "items": items}


@router.get("/summary")
def get_receipts_summary(
    organizations: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get summary statistics for fin receipts."""
    query = db.query(FinReceipt)

    # Apply filters
    if organizations:
        org_list = [o.strip() for o in organizations.split(",") if o.strip()]
        if org_list:
            org_ids = db.query(Organization.id).filter(Organization.name.in_(org_list)).all()
            org_ids = [o[0] for o in org_ids]
            if org_ids:
                query = query.filter(FinReceipt.organization_id.in_(org_ids))

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(FinReceipt.document_date >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(FinReceipt.document_date <= date_to_obj)
        except ValueError:
            pass

    # Get count and sum
    total_count = query.count()
    total_amount = db.query(func.sum(FinReceipt.amount)).filter(
        FinReceipt.id.in_(query.with_entities(FinReceipt.id))
    ).scalar() or 0

    return {
        "total_records": total_count,
        "total_amount": float(total_amount)
    }


@router.get("/{receipt_id}")
def get_receipt(
    receipt_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get single fin receipt by ID."""
    receipt = db.query(FinReceipt).filter(FinReceipt.id == receipt_id).first()

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    return {
        "id": receipt.id,
        "operation_id": receipt.operation_id,
        "organization": receipt.org.name if receipt.org else None,
        "organization_id": receipt.organization_id,
        "operation_type": receipt.operation_type,
        "bank_account": receipt.bank.account_number if receipt.bank else None,
        "bank_account_id": receipt.bank_account_id,
        "accounting_account": receipt.accounting_account,
        "document_number": receipt.document_number,
        "document_date": receipt.document_date,
        "payer": receipt.payer,
        "payer_account": receipt.payer_account,
        "settlement_account": receipt.settlement_account,
        "contract_number": receipt.contract.contract_number if receipt.contract else None,
        "contract_id": receipt.contract_id,
        "contract_date": receipt.contract_date,
        "currency": receipt.currency,
        "amount": float(receipt.amount) if receipt.amount else 0,
        "commission": float(receipt.commission) if receipt.commission else 0,
        "payment_purpose": receipt.payment_purpose,
        "responsible_person": receipt.responsible_person,
        "comment": receipt.comment,
        "created_at": receipt.created_at,
        "updated_at": receipt.updated_at
    }
