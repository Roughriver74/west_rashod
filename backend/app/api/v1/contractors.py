"""Contractor API endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Contractor, User, UserRoleEnum
from app.schemas.contractor import (
    ContractorCreate, ContractorUpdate, ContractorResponse
)
from app.utils.auth import get_current_active_user

router = APIRouter(prefix="/contractors", tags=["Contractors"])


@router.get("/", response_model=List[ContractorResponse])
def get_contractors(
    skip: int = 0,
    limit: int = 100,
    department_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all contractors."""
    query = db.query(Contractor)

    # Filter by department
    if current_user.role == UserRoleEnum.USER:
        query = query.filter(Contractor.department_id == current_user.department_id)
    elif department_id:
        query = query.filter(Contractor.department_id == department_id)

    if is_active is not None:
        query = query.filter(Contractor.is_active == is_active)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Contractor.name.ilike(search_term)) |
            (Contractor.inn.ilike(search_term)) |
            (Contractor.short_name.ilike(search_term))
        )

    return query.offset(skip).limit(limit).all()


@router.get("/{contractor_id}", response_model=ContractorResponse)
def get_contractor(
    contractor_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get contractor by ID."""
    contractor = db.query(Contractor).filter(Contractor.id == contractor_id).first()
    if not contractor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contractor not found"
        )
    return contractor


@router.post("/", response_model=ContractorResponse)
def create_contractor(
    contractor_data: ContractorCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new contractor."""
    contractor = Contractor(**contractor_data.model_dump())
    db.add(contractor)
    db.commit()
    db.refresh(contractor)

    return contractor


@router.put("/{contractor_id}", response_model=ContractorResponse)
def update_contractor(
    contractor_id: int,
    contractor_update: ContractorUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update contractor."""
    contractor = db.query(Contractor).filter(Contractor.id == contractor_id).first()
    if not contractor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contractor not found"
        )

    update_data = contractor_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contractor, field, value)

    db.commit()
    db.refresh(contractor)

    return contractor


@router.delete("/{contractor_id}")
def delete_contractor(
    contractor_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Deactivate contractor."""
    contractor = db.query(Contractor).filter(Contractor.id == contractor_id).first()
    if not contractor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contractor not found"
        )

    contractor.is_active = False
    db.commit()

    return {"message": "Contractor deactivated"}
