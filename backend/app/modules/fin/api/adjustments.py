"""
API endpoints for manual adjustments (Ручные корректировки)
CRUD operations for adjustments that are NOT deleted during FTP import
"""
import logging
from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel

from app.db.session import get_db
from app.utils.auth import get_current_active_user
from app.db.models import User
from app.modules.fin.models import FinManualAdjustment, FinContract
from app.services.cache import cache

router = APIRouter()
logger = logging.getLogger(__name__)


# === Pydantic Schemas ===

class ManualAdjustmentBase(BaseModel):
    adjustment_date: date
    counterparty: Optional[str] = None
    contract_number: Optional[str] = None
    adjustment_type: str  # 'principal' | 'interest' | 'other'
    amount: float
    description: Optional[str] = None


class ManualAdjustmentCreate(ManualAdjustmentBase):
    pass


class ManualAdjustmentUpdate(BaseModel):
    adjustment_date: Optional[date] = None
    counterparty: Optional[str] = None
    contract_number: Optional[str] = None
    adjustment_type: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None


class ManualAdjustmentResponse(BaseModel):
    id: int
    adjustment_date: date
    counterparty: Optional[str] = None
    contract_number: Optional[str] = None
    adjustment_type: str
    amount: float
    description: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ManualAdjustmentListResponse(BaseModel):
    total: int
    items: List[ManualAdjustmentResponse]


# === Endpoints ===

@router.get("/", response_model=ManualAdjustmentListResponse)
def get_adjustments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000000),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    adjustment_type: Optional[str] = Query(None, description="Filter by type: principal, interest, other"),
    counterparty: Optional[str] = Query(None, description="Filter by counterparty"),
    contract_number: Optional[str] = Query(None, description="Filter by contract number"),
    search: Optional[str] = Query(None, description="Search in description, counterparty"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get list of manual adjustments with filtering and pagination."""
    query = db.query(FinManualAdjustment)

    # Apply filters
    if adjustment_type:
        # Map frontend types to backend
        type_mapping = {
            'principal': 'expense',
            'interest': 'expense',
            'other': 'expense',
        }
        backend_type = type_mapping.get(adjustment_type, adjustment_type)
        query = query.filter(FinManualAdjustment.adjustment_type == backend_type)

        # Also filter by payment_type for expenses
        if adjustment_type == 'principal':
            query = query.filter(FinManualAdjustment.payment_type == 'Погашение долга')
        elif adjustment_type == 'interest':
            query = query.filter(FinManualAdjustment.payment_type == 'Уплата процентов')

    if counterparty:
        query = query.filter(FinManualAdjustment.counterparty.ilike(f"%{counterparty}%"))

    if contract_number:
        query = query.filter(FinManualAdjustment.contract_number.ilike(f"%{contract_number}%"))

    if date_from:
        try:
            from datetime import datetime
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(FinManualAdjustment.document_date >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            from datetime import datetime
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(FinManualAdjustment.document_date <= date_to_obj)
        except ValueError:
            pass

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                FinManualAdjustment.description.ilike(pattern),
                FinManualAdjustment.counterparty.ilike(pattern),
                FinManualAdjustment.comment.ilike(pattern),
                FinManualAdjustment.contract_number.ilike(pattern),
            )
        )

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    adjustments = query.order_by(
        FinManualAdjustment.document_date.desc(),
        FinManualAdjustment.id.desc()
    ).offset(skip).limit(limit).all()

    # Convert to response format
    items = []
    for adj in adjustments:
        # Map backend type to frontend type
        frontend_type = adj.adjustment_type
        if adj.adjustment_type == 'expense':
            if adj.payment_type == 'Погашение долга':
                frontend_type = 'principal'
            elif adj.payment_type == 'Уплата процентов':
                frontend_type = 'interest'
            else:
                frontend_type = 'other'
        elif adj.adjustment_type == 'receipt':
            frontend_type = 'principal'  # Receipts are usually principal

        items.append(ManualAdjustmentResponse(
            id=adj.id,
            adjustment_date=adj.document_date,
            counterparty=adj.counterparty,
            contract_number=adj.contract_number,
            adjustment_type=frontend_type,
            amount=float(adj.amount or 0),
            description=adj.description,
            created_by=adj.created_by,
            created_at=adj.created_at.isoformat() if adj.created_at else None,
        ))

    return ManualAdjustmentListResponse(total=total, items=items)


@router.get("/{adjustment_id}", response_model=ManualAdjustmentResponse)
def get_adjustment(
    adjustment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a single manual adjustment by ID."""
    adjustment = db.query(FinManualAdjustment).filter(
        FinManualAdjustment.id == adjustment_id
    ).first()

    if not adjustment:
        raise HTTPException(status_code=404, detail="Adjustment not found")

    # Map backend type to frontend type
    frontend_type = adjustment.adjustment_type
    if adjustment.adjustment_type == 'expense':
        if adjustment.payment_type == 'Погашение долга':
            frontend_type = 'principal'
        elif adjustment.payment_type == 'Уплата процентов':
            frontend_type = 'interest'
        else:
            frontend_type = 'other'
    elif adjustment.adjustment_type == 'receipt':
        frontend_type = 'principal'

    return ManualAdjustmentResponse(
        id=adjustment.id,
        adjustment_date=adjustment.document_date,
        counterparty=adjustment.counterparty,
        contract_number=adjustment.contract_number,
        adjustment_type=frontend_type,
        amount=float(adjustment.amount or 0),
        description=adjustment.description,
        created_by=adjustment.created_by,
        created_at=adjustment.created_at.isoformat() if adjustment.created_at else None,
    )


@router.post("/", response_model=ManualAdjustmentResponse)
def create_adjustment(
    data: ManualAdjustmentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new manual adjustment."""
    # Map frontend type to backend
    backend_type = 'expense'
    payment_type = None

    if data.adjustment_type == 'principal':
        backend_type = 'expense'
        payment_type = 'Погашение долга'
    elif data.adjustment_type == 'interest':
        backend_type = 'expense'
        payment_type = 'Уплата процентов'
    elif data.adjustment_type == 'other':
        backend_type = 'expense'
        payment_type = 'Прочее'
    elif data.adjustment_type == 'receipt':
        backend_type = 'receipt'
        payment_type = None

    # Find contract if contract_number provided
    contract_id = None
    if data.contract_number:
        # Trim whitespace
        contract_number_clean = data.contract_number.strip()

        # Try exact match first
        contract = db.query(FinContract).filter(
            FinContract.contract_number == contract_number_clean
        ).first()

        if contract:
            contract_id = contract.id
            logger.info(f"Found contract (exact match): id={contract_id}, number={contract_number_clean}")
        else:
            # Try case-insensitive and whitespace-tolerant match
            contract = db.query(FinContract).filter(
                func.trim(FinContract.contract_number) == contract_number_clean
            ).first()

            if contract:
                contract_id = contract.id
                logger.info(f"Found contract (trimmed match): id={contract_id}, number={contract_number_clean}")
            else:
                logger.warning(
                    f"Contract not found for number: '{contract_number_clean}'. "
                    f"Adjustment will be created with contract_number but without contract_id."
                )

    adjustment = FinManualAdjustment(
        contract_id=contract_id,
        contract_number=data.contract_number,
        adjustment_type=backend_type,
        payment_type=payment_type,
        amount=data.amount,
        document_date=data.adjustment_date,
        counterparty=data.counterparty,
        description=data.description,
        created_by=current_user.username if current_user else None,
    )

    db.add(adjustment)
    db.commit()
    db.refresh(adjustment)

    logger.info(
        f"Created manual adjustment: id={adjustment.id}, contract_id={adjustment.contract_id}, "
        f"contract_number={adjustment.contract_number}, type={adjustment.adjustment_type}, "
        f"payment_type={adjustment.payment_type}, amount={adjustment.amount}"
    )

    # Очистить кэш аналитики после создания корректировки
    cache.clear_pattern("fin:*")

    return ManualAdjustmentResponse(
        id=adjustment.id,
        adjustment_date=adjustment.document_date,
        counterparty=adjustment.counterparty,
        contract_number=adjustment.contract_number,
        adjustment_type=data.adjustment_type,
        amount=float(adjustment.amount or 0),
        description=adjustment.description,
        created_by=adjustment.created_by,
        created_at=adjustment.created_at.isoformat() if adjustment.created_at else None,
    )


@router.put("/{adjustment_id}", response_model=ManualAdjustmentResponse)
def update_adjustment(
    adjustment_id: int,
    data: ManualAdjustmentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update an existing manual adjustment."""
    adjustment = db.query(FinManualAdjustment).filter(
        FinManualAdjustment.id == adjustment_id
    ).first()

    if not adjustment:
        raise HTTPException(status_code=404, detail="Adjustment not found")

    # Update fields
    if data.adjustment_date is not None:
        adjustment.document_date = data.adjustment_date

    if data.counterparty is not None:
        adjustment.counterparty = data.counterparty

    if data.contract_number is not None:
        adjustment.contract_number = data.contract_number
        # Update contract_id if contract found
        contract = db.query(FinContract).filter(
            FinContract.contract_number == data.contract_number
        ).first()
        adjustment.contract_id = contract.id if contract else None

    if data.amount is not None:
        adjustment.amount = data.amount

    if data.description is not None:
        adjustment.description = data.description

    if data.adjustment_type is not None:
        # Map frontend type to backend
        if data.adjustment_type == 'principal':
            adjustment.adjustment_type = 'expense'
            adjustment.payment_type = 'Погашение долга'
        elif data.adjustment_type == 'interest':
            adjustment.adjustment_type = 'expense'
            adjustment.payment_type = 'Уплата процентов'
        elif data.adjustment_type == 'other':
            adjustment.adjustment_type = 'expense'
            adjustment.payment_type = 'Прочее'
        elif data.adjustment_type == 'receipt':
            adjustment.adjustment_type = 'receipt'
            adjustment.payment_type = None

    db.commit()
    db.refresh(adjustment)

    logger.info(f"Updated manual adjustment: id={adjustment.id}")

    # Очистить кэш аналитики после обновления корректировки
    cache.clear_pattern("fin:*")

    # Map backend type to frontend type for response
    frontend_type = adjustment.adjustment_type
    if adjustment.adjustment_type == 'expense':
        if adjustment.payment_type == 'Погашение долга':
            frontend_type = 'principal'
        elif adjustment.payment_type == 'Уплата процентов':
            frontend_type = 'interest'
        else:
            frontend_type = 'other'
    elif adjustment.adjustment_type == 'receipt':
        frontend_type = 'principal'

    return ManualAdjustmentResponse(
        id=adjustment.id,
        adjustment_date=adjustment.document_date,
        counterparty=adjustment.counterparty,
        contract_number=adjustment.contract_number,
        adjustment_type=frontend_type,
        amount=float(adjustment.amount or 0),
        description=adjustment.description,
        created_by=adjustment.created_by,
        created_at=adjustment.created_at.isoformat() if adjustment.created_at else None,
    )


@router.delete("/{adjustment_id}")
def delete_adjustment(
    adjustment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a manual adjustment."""
    adjustment = db.query(FinManualAdjustment).filter(
        FinManualAdjustment.id == adjustment_id
    ).first()

    if not adjustment:
        raise HTTPException(status_code=404, detail="Adjustment not found")

    db.delete(adjustment)
    db.commit()

    logger.info(f"Deleted manual adjustment: id={adjustment_id}")

    # Очистить кэш аналитики после удаления корректировки
    cache.clear_pattern("fin:*")

    return {"message": "Adjustment deleted successfully", "id": adjustment_id}
