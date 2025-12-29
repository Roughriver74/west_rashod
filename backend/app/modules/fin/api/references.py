"""
API endpoints for Fin References (Справочники).
Bank accounts, contracts, excluded payers.
"""
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.utils.auth import get_current_active_user
from app.db.models import User, Organization
from app.modules.fin.models import (
    FinBankAccount, FinContract, FinReceipt, FinExpense,
    FinExcludedPayer
)
from pydantic import BaseModel

router = APIRouter()


# === Bank Accounts ===

@router.get("/bank-accounts")
def get_bank_accounts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000000),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get list of fin bank accounts."""
    query = db.query(FinBankAccount)

    if is_active is not None:
        query = query.filter(FinBankAccount.is_active == is_active)

    total = query.count()
    accounts = query.offset(skip).limit(limit).all()

    items = []
    for acc in accounts:
        items.append({
            "id": acc.id,
            "account_number": acc.account_number,
            "bank_name": acc.bank_name,
            "is_active": acc.is_active,
            "created_at": acc.created_at,
            "updated_at": acc.updated_at
        })

    return {"total": total, "items": items}


# === Contracts ===

@router.get("/contracts")
def get_contracts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000000),
    is_active: Optional[bool] = Query(None),
    contract_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by contract number"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get list of fin contracts."""
    query = db.query(FinContract)

    if is_active is not None:
        query = query.filter(FinContract.is_active == is_active)

    if contract_type:
        query = query.filter(FinContract.contract_type == contract_type)

    if search:
        query = query.filter(FinContract.contract_number.ilike(f"%{search}%"))

    total = query.count()
    contracts = query.order_by(FinContract.contract_date.desc().nulls_last()).offset(skip).limit(limit).all()

    items = []
    for c in contracts:
        items.append({
            "id": c.id,
            "contract_number": c.contract_number,
            "contract_date": c.contract_date,
            "contract_type": c.contract_type,
            "counterparty": c.counterparty,
            "is_active": c.is_active,
            "created_at": c.created_at,
            "updated_at": c.updated_at
        })

    return {"total": total, "items": items}


@router.get("/contracts/{contract_id}")
def get_contract_by_id(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a single contract by ID."""
    contract = db.query(FinContract).filter(FinContract.id == contract_id).first()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    return {
        "id": contract.id,
        "contract_number": contract.contract_number,
        "contract_date": contract.contract_date,
        "contract_type": contract.contract_type,
        "counterparty": contract.counterparty,
        "is_active": contract.is_active,
        "created_at": contract.created_at,
        "updated_at": contract.updated_at
    }


@router.get("/contracts/{contract_id}/operations")
def get_contract_operations(
    contract_id: int,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all operations (receipts and expenses) for a contract."""
    contract = db.query(FinContract).filter(FinContract.id == contract_id).first()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Get receipts
    receipts_query = db.query(FinReceipt).filter(FinReceipt.contract_id == contract_id)
    expenses_query = db.query(FinExpense).filter(FinExpense.contract_id == contract_id)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            receipts_query = receipts_query.filter(FinReceipt.document_date >= date_from_obj)
            expenses_query = expenses_query.filter(FinExpense.document_date >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            receipts_query = receipts_query.filter(FinReceipt.document_date <= date_to_obj)
            expenses_query = expenses_query.filter(FinExpense.document_date <= date_to_obj)
        except ValueError:
            pass

    receipts = receipts_query.order_by(FinReceipt.document_date.desc()).all()
    expenses = expenses_query.order_by(FinExpense.document_date.desc()).all()

    # Calculate totals
    total_receipts = sum(float(r.amount or 0) for r in receipts)
    total_expenses = sum(float(e.amount or 0) for e in expenses)

    return {
        "contract": {
            "id": contract.id,
            "contract_number": contract.contract_number,
            "contract_date": contract.contract_date,
            "contract_type": contract.contract_type,
            "counterparty": contract.counterparty
        },
        "summary": {
            "total_receipts": total_receipts,
            "total_expenses": total_expenses,
            "balance": total_receipts - total_expenses,
            "receipts_count": len(receipts),
            "expenses_count": len(expenses)
        },
        "receipts": [
            {
                "id": r.id,
                "document_date": r.document_date,
                "document_number": r.document_number,
                "payer": r.payer,
                "amount": float(r.amount or 0),
                "payment_purpose": r.payment_purpose
            }
            for r in receipts
        ],
        "expenses": [
            {
                "id": e.id,
                "document_date": e.document_date,
                "document_number": e.document_number,
                "recipient": e.recipient,
                "amount": float(e.amount or 0),
                "payment_purpose": e.payment_purpose
            }
            for e in expenses
        ]
    }


# === Excluded Payers ===

class ExcludedPayerCreate(BaseModel):
    payer_name: str


@router.get("/excluded-payers")
def get_excluded_payers(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get list of excluded payers."""
    payers = db.query(FinExcludedPayer).order_by(FinExcludedPayer.payer_name).all()

    return {
        "total": len(payers),
        "items": [
            {"id": p.id, "payer_name": p.payer_name, "created_at": p.created_at}
            for p in payers
        ]
    }


@router.post("/excluded-payers")
def add_excluded_payer(
    data: ExcludedPayerCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a payer to excluded list."""
    existing = db.query(FinExcludedPayer).filter(
        FinExcludedPayer.payer_name == data.payer_name
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Payer already in excluded list")

    payer = FinExcludedPayer(payer_name=data.payer_name)
    db.add(payer)
    db.commit()

    return {"id": payer.id, "payer_name": payer.payer_name, "created_at": payer.created_at}


@router.delete("/excluded-payers/{payer_id}")
def remove_excluded_payer(
    payer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove a payer from excluded list."""
    payer = db.query(FinExcludedPayer).filter(FinExcludedPayer.id == payer_id).first()

    if not payer:
        raise HTTPException(status_code=404, detail="Excluded payer not found")

    db.delete(payer)
    db.commit()

    return {"message": "Excluded payer removed successfully"}


# === Organizations (from main table) ===

@router.get("/organizations")
def get_organizations(
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get list of organizations (from main organizations table)."""
    query = db.query(Organization)

    if is_active is not None:
        query = query.filter(Organization.is_active == is_active)

    if search:
        query = query.filter(Organization.name.ilike(f"%{search}%"))

    orgs = query.order_by(Organization.name).limit(100000).all()

    return {
        "total": len(orgs),
        "items": [
            {"id": o.id, "name": o.name, "is_active": o.is_active}
            for o in orgs
        ]
    }


# === Unique Payers ===

@router.get("/payers")
def get_unique_payers(
    search: Optional[str] = Query(None, description="Search payer name"),
    limit: int = Query(100, ge=1, le=10000000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get list of unique payers from receipts."""
    query = db.query(FinReceipt.payer).filter(FinReceipt.payer.isnot(None)).distinct()

    if search:
        query = query.filter(FinReceipt.payer.ilike(f"%{search}%"))

    payers = query.limit(limit).all()

    return {
        "total": len(payers),
        "items": [p[0] for p in payers if p[0]]
    }


# === Unique Recipients ===

@router.get("/recipients")
def get_unique_recipients(
    search: Optional[str] = Query(None, description="Search recipient name"),
    limit: int = Query(100, ge=1, le=10000000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get list of unique recipients from expenses."""
    query = db.query(FinExpense.recipient).filter(FinExpense.recipient.isnot(None)).distinct()

    if search:
        query = query.filter(FinExpense.recipient.ilike(f"%{search}%"))

    recipients = query.limit(limit).all()

    return {
        "total": len(recipients),
        "items": [r[0] for r in recipients if r[0]]
    }
