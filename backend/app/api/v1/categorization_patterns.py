"""
Categorization patterns API endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db.session import get_db
from app.db.models import (
    BankTransaction, BudgetCategory, BankTransactionStatusEnum,
    CategorizationRule, User, CategorizationRuleTypeEnum
)
from app.api.v1.auth import get_current_active_user
from app.schemas.categorization_rule import (
    CategorizationRule as CategorizationRuleSchema,
    CategorizationRuleCreate,
    CategorizationRuleUpdate,
)

router = APIRouter(prefix="/categorization-patterns", tags=["categorization-patterns"])


@router.get("/counterparties")
def get_counterparty_patterns(
    limit: int = 500,
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
    limit: int = 200,
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


@router.get("/payment-purpose-keywords")
def get_payment_purpose_keyword_patterns(
    limit: int = 500,
    min_transactions: int = 3,
    min_keyword_length: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get categorization patterns by payment purpose keywords.

    Analyzes payment_purpose field to extract common keywords and their associated categories.
    This helps identify which keywords are frequently used in categorized transactions.
    """

    # Get all categorized transactions with payment_purpose
    transactions = (
        db.query(
            BankTransaction.payment_purpose,
            BankTransaction.category_id,
            BudgetCategory.name.label("category_name"),
            BankTransaction.category_confidence,
        )
        .join(BudgetCategory, BankTransaction.category_id == BudgetCategory.id)
        .filter(BankTransaction.is_active == True)
        .filter(BankTransaction.payment_purpose.isnot(None))
        .filter(BankTransaction.category_id.isnot(None))
        .all()
    )

    # Extract keywords and group by category
    keyword_patterns = {}

    for transaction in transactions:
        if not transaction.payment_purpose:
            continue

        # Extract words from payment purpose (normalize to lowercase)
        words = transaction.payment_purpose.lower().split()

        # Filter words: length >= min_keyword_length, skip numbers
        keywords = [
            word.strip('.,;:()[]{}"\'-')
            for word in words
            if len(word) >= min_keyword_length and not word.isdigit()
        ]

        # Group by keyword and category
        for keyword in keywords:
            if not keyword:
                continue

            key = (keyword, transaction.category_id, transaction.category_name)

            if key not in keyword_patterns:
                keyword_patterns[key] = {
                    "keyword": keyword,
                    "category_id": transaction.category_id,
                    "category_name": transaction.category_name,
                    "transaction_count": 0,
                    "confidence_sum": 0.0,
                }

            keyword_patterns[key]["transaction_count"] += 1
            if transaction.category_confidence:
                keyword_patterns[key]["confidence_sum"] += float(transaction.category_confidence)

    # Convert to list and filter by min_transactions
    patterns = [
        {
            "keyword": p["keyword"],
            "category_id": p["category_id"],
            "category_name": p["category_name"],
            "transaction_count": p["transaction_count"],
            "confidence_estimate": (
                p["confidence_sum"] / p["transaction_count"]
                if p["transaction_count"] > 0
                else 0.5
            ),
        }
        for p in keyword_patterns.values()
        if p["transaction_count"] >= min_transactions
    ]

    # Sort by transaction count (descending) and limit
    patterns.sort(key=lambda x: x["transaction_count"], reverse=True)

    return patterns[:limit]


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


@router.get("/rules", response_model=List[CategorizationRuleSchema])
def get_categorization_rules(
    rule_type: Optional[CategorizationRuleTypeEnum] = None,
    is_active: Optional[bool] = None,
    limit: int = 500,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get categorization rules with optional filtering."""
    query = db.query(CategorizationRule)

    # Apply filters
    if rule_type:
        query = query.filter(CategorizationRule.rule_type == rule_type)
    if is_active is not None:
        query = query.filter(CategorizationRule.is_active == is_active)

    # Order by priority (higher first) and then by created date
    query = query.order_by(desc(CategorizationRule.priority), desc(CategorizationRule.created_at))

    # Apply limit
    rules = query.limit(limit).all()

    # Enrich with category names
    result = []
    for rule in rules:
        rule_dict = {
            "id": rule.id,
            "rule_type": rule.rule_type,
            "counterparty_inn": rule.counterparty_inn,
            "counterparty_name": rule.counterparty_name,
            "business_operation": rule.business_operation,
            "keyword": rule.keyword,
            "category_id": rule.category_id,
            "category_name": rule.category_rel.name if rule.category_rel else None,
            "priority": rule.priority,
            "confidence": rule.confidence,
            "is_active": rule.is_active,
            "notes": rule.notes,
            "created_at": rule.created_at,
            "updated_at": rule.updated_at,
            "created_by": rule.created_by,
        }
        result.append(rule_dict)

    return result


@router.post("/rules", response_model=CategorizationRuleSchema, status_code=status.HTTP_201_CREATED)
def create_categorization_rule(
    rule_data: CategorizationRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new categorization rule."""
    # Validate that the category exists
    category = db.query(BudgetCategory).filter(BudgetCategory.id == rule_data.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with id {rule_data.category_id} not found"
        )

    # Create the rule
    db_rule = CategorizationRule(
        **rule_data.dict(),
        created_by=current_user.id
    )

    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)

    # Return with category name
    return {
        "id": db_rule.id,
        "rule_type": db_rule.rule_type,
        "counterparty_inn": db_rule.counterparty_inn,
        "counterparty_name": db_rule.counterparty_name,
        "business_operation": db_rule.business_operation,
        "keyword": db_rule.keyword,
        "category_id": db_rule.category_id,
        "category_name": category.name,
        "priority": db_rule.priority,
        "confidence": db_rule.confidence,
        "is_active": db_rule.is_active,
        "notes": db_rule.notes,
        "created_at": db_rule.created_at,
        "updated_at": db_rule.updated_at,
        "created_by": db_rule.created_by,
    }


@router.put("/rules/{rule_id}", response_model=CategorizationRuleSchema)
def update_categorization_rule(
    rule_id: int,
    rule_data: CategorizationRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update an existing categorization rule."""
    # Find the rule
    db_rule = db.query(CategorizationRule).filter(CategorizationRule.id == rule_id).first()
    if not db_rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with id {rule_id} not found"
        )

    # If updating category, validate it exists
    if rule_data.category_id is not None:
        category = db.query(BudgetCategory).filter(BudgetCategory.id == rule_data.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {rule_data.category_id} not found"
            )

    # Update the rule
    update_data = rule_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_rule, field, value)

    db.commit()
    db.refresh(db_rule)

    # Return with category name
    return {
        "id": db_rule.id,
        "rule_type": db_rule.rule_type,
        "counterparty_inn": db_rule.counterparty_inn,
        "counterparty_name": db_rule.counterparty_name,
        "business_operation": db_rule.business_operation,
        "keyword": db_rule.keyword,
        "category_id": db_rule.category_id,
        "category_name": db_rule.category_rel.name if db_rule.category_rel else None,
        "priority": db_rule.priority,
        "confidence": db_rule.confidence,
        "is_active": db_rule.is_active,
        "notes": db_rule.notes,
        "created_at": db_rule.created_at,
        "updated_at": db_rule.updated_at,
        "created_by": db_rule.created_by,
    }


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_categorization_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a categorization rule permanently."""
    # Find the rule
    db_rule = db.query(CategorizationRule).filter(CategorizationRule.id == rule_id).first()
    if not db_rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with id {rule_id} not found"
        )

    # Delete the rule
    db.delete(db_rule)
    db.commit()

    return None


@router.post("/rules/bulk-activate", status_code=status.HTTP_200_OK)
def bulk_activate_rules(
    rule_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Bulk activate categorization rules."""
    if not rule_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rule IDs provided"
        )

    # Update all rules
    updated_count = (
        db.query(CategorizationRule)
        .filter(CategorizationRule.id.in_(rule_ids))
        .update({"is_active": True}, synchronize_session=False)
    )

    db.commit()

    return {"updated_count": updated_count}


@router.post("/rules/bulk-deactivate", status_code=status.HTTP_200_OK)
def bulk_deactivate_rules(
    rule_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Bulk deactivate categorization rules."""
    if not rule_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rule IDs provided"
        )

    # Update all rules
    updated_count = (
        db.query(CategorizationRule)
        .filter(CategorizationRule.id.in_(rule_ids))
        .update({"is_active": False}, synchronize_session=False)
    )

    db.commit()

    return {"updated_count": updated_count}
