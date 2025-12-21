"""
Categorization patterns API endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db.session import get_db
from app.db.models import BankTransaction, BudgetCategory, BankTransactionStatusEnum
from app.api.v1.auth import get_current_active_user
from app.db.models import User

router = APIRouter(prefix="/categorization-patterns", tags=["categorization-patterns"])


@router.get("/counterparties")
def get_counterparty_patterns(
    limit: int = 50,
    min_transactions: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get categorization patterns by counterparty."""

    # Group transactions by counterparty and category
    patterns = (
        db.query(
            BankTransaction.counterparty_inn,
            BankTransaction.counterparty_name,
            BankTransaction.category_id,
            BudgetCategory.name.label("category_name"),
            func.count(BankTransaction.id).label("transaction_count"),
            func.avg(BankTransaction.amount).label("avg_amount"),
            func.avg(BankTransaction.category_confidence).label("confidence_estimate"),
        )
        .join(BudgetCategory, BankTransaction.category_id == BudgetCategory.id, isouter=True)
        .filter(BankTransaction.is_active == True)
        .filter(BankTransaction.category_id.isnot(None))
        .group_by(
            BankTransaction.counterparty_inn,
            BankTransaction.counterparty_name,
            BankTransaction.category_id,
            BudgetCategory.name,
        )
        .having(func.count(BankTransaction.id) >= min_transactions)
        .order_by(desc("transaction_count"))
        .limit(limit)
        .all()
    )

    return [
        {
            "counterparty_inn": p.counterparty_inn,
            "counterparty_name": p.counterparty_name,
            "category_id": p.category_id,
            "category_name": p.category_name,
            "transaction_count": p.transaction_count,
            "avg_amount": float(p.avg_amount) if p.avg_amount else 0,
            "confidence_estimate": float(p.confidence_estimate) if p.confidence_estimate else 0.5,
        }
        for p in patterns
    ]


@router.get("/business-operations")
def get_business_operation_patterns(
    limit: int = 50,
    min_transactions: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get categorization patterns by business operation."""

    # Group transactions by business operation and category
    patterns = (
        db.query(
            BankTransaction.business_operation,
            BankTransaction.category_id,
            BudgetCategory.name.label("category_name"),
            func.count(BankTransaction.id).label("transaction_count"),
            func.avg(BankTransaction.category_confidence).label("confidence_estimate"),
        )
        .join(BudgetCategory, BankTransaction.category_id == BudgetCategory.id, isouter=True)
        .filter(BankTransaction.is_active == True)
        .filter(BankTransaction.business_operation.isnot(None))
        .filter(BankTransaction.category_id.isnot(None))
        .group_by(
            BankTransaction.business_operation,
            BankTransaction.category_id,
            BudgetCategory.name,
        )
        .having(func.count(BankTransaction.id) >= min_transactions)
        .order_by(desc("transaction_count"))
        .limit(limit)
        .all()
    )

    return [
        {
            "business_operation": p.business_operation,
            "category_id": p.category_id,
            "category_name": p.category_name,
            "transaction_count": p.transaction_count,
            "confidence_estimate": float(p.confidence_estimate) if p.confidence_estimate else 0.5,
        }
        for p in patterns
    ]


@router.get("/stats")
def get_categorization_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get categorization statistics."""

    total = db.query(func.count(BankTransaction.id)).filter(BankTransaction.is_active == True).scalar()

    auto_categorized = (
        db.query(func.count(BankTransaction.id))
        .filter(BankTransaction.is_active == True)
        .filter(BankTransaction.category_id.isnot(None))
        .filter(BankTransaction.category_confidence.isnot(None))
        .scalar()
    )

    needs_review = (
        db.query(func.count(BankTransaction.id))
        .filter(BankTransaction.is_active == True)
        .filter(BankTransaction.status == BankTransactionStatusEnum.NEEDS_REVIEW)
        .scalar()
    )

    manual_categorized = (
        db.query(func.count(BankTransaction.id))
        .filter(BankTransaction.is_active == True)
        .filter(BankTransaction.category_id.isnot(None))
        .filter(BankTransaction.category_confidence.is_(None))
        .scalar()
    )

    avg_confidence = (
        db.query(func.avg(BankTransaction.category_confidence))
        .filter(BankTransaction.is_active == True)
        .filter(BankTransaction.category_confidence.isnot(None))
        .scalar()
    )

    high_confidence = (
        db.query(func.count(BankTransaction.id))
        .filter(BankTransaction.is_active == True)
        .filter(BankTransaction.category_confidence >= 0.8)
        .scalar()
    )

    medium_confidence = (
        db.query(func.count(BankTransaction.id))
        .filter(BankTransaction.is_active == True)
        .filter(BankTransaction.category_confidence >= 0.5)
        .filter(BankTransaction.category_confidence < 0.8)
        .scalar()
    )

    low_confidence = (
        db.query(func.count(BankTransaction.id))
        .filter(BankTransaction.is_active == True)
        .filter(BankTransaction.category_confidence < 0.5)
        .scalar()
    )

    return {
        "total_transactions": total or 0,
        "auto_categorized": auto_categorized or 0,
        "needs_review": needs_review or 0,
        "manual_categorized": manual_categorized or 0,
        "avg_confidence": float(avg_confidence) if avg_confidence else None,
        "high_confidence_count": high_confidence or 0,
        "medium_confidence_count": medium_confidence or 0,
        "low_confidence_count": low_confidence or 0,
    }


@router.get("/rules")
def get_categorization_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get categorization rules (placeholder for future implementation)."""
    # TODO: Implement categorization rules table and CRUD
    return []


@router.post("/rules")
def create_categorization_rule(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create categorization rule (placeholder for future implementation)."""
    # TODO: Implement categorization rules table and CRUD
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Categorization rules feature is not yet implemented"
    )


@router.put("/rules/{rule_id}")
def update_categorization_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update categorization rule (placeholder for future implementation)."""
    # TODO: Implement categorization rules table and CRUD
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Categorization rules feature is not yet implemented"
    )


@router.delete("/rules/{rule_id}")
def delete_categorization_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete categorization rule (placeholder for future implementation)."""
    # TODO: Implement categorization rules table and CRUD
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Categorization rules feature is not yet implemented"
    )


@router.post("/rules/bulk-activate")
def bulk_activate_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Bulk activate rules (placeholder for future implementation)."""
    # TODO: Implement categorization rules table and CRUD
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Categorization rules feature is not yet implemented"
    )


@router.post("/rules/bulk-deactivate")
def bulk_deactivate_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Bulk deactivate rules (placeholder for future implementation)."""
    # TODO: Implement categorization rules table and CRUD
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Categorization rules feature is not yet implemented"
    )
