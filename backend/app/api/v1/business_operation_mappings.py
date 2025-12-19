"""Business operation mapping API endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.db.models import BusinessOperationMapping, BudgetCategory, User, UserRoleEnum
from app.schemas.business_operation_mapping import (
    BusinessOperationMappingCreate, BusinessOperationMappingUpdate,
    BusinessOperationMappingResponse
)
from app.utils.auth import get_current_active_user

router = APIRouter(prefix="/business-operation-mappings", tags=["Business Operation Mappings"])


@router.get("/", response_model=List[BusinessOperationMappingResponse])
def get_mappings(
    skip: int = 0,
    limit: int = 100,
    department_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all business operation mappings."""
    query = db.query(BusinessOperationMapping).options(
        joinedload(BusinessOperationMapping.category_rel)
    )

    # Filter by department
    if current_user.role == UserRoleEnum.USER:
        query = query.filter(BusinessOperationMapping.department_id == current_user.department_id)
    elif department_id:
        query = query.filter(BusinessOperationMapping.department_id == department_id)

    if is_active is not None:
        query = query.filter(BusinessOperationMapping.is_active == is_active)

    if search:
        query = query.filter(BusinessOperationMapping.business_operation.ilike(f"%{search}%"))

    mappings = query.order_by(BusinessOperationMapping.priority.desc()).offset(skip).limit(limit).all()

    # Add category name
    result = []
    for m in mappings:
        m_dict = BusinessOperationMappingResponse.model_validate(m).model_dump()
        m_dict['category_name'] = m.category_rel.name if m.category_rel else None
        result.append(BusinessOperationMappingResponse(**m_dict))

    return result


@router.get("/stats")
def get_mapping_stats(
    department_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get mapping statistics."""
    query = db.query(BusinessOperationMapping)

    if current_user.role == UserRoleEnum.USER:
        query = query.filter(BusinessOperationMapping.department_id == current_user.department_id)
    elif department_id:
        query = query.filter(BusinessOperationMapping.department_id == department_id)

    total = query.count()
    active = query.filter(BusinessOperationMapping.is_active == True).count()
    inactive = query.filter(BusinessOperationMapping.is_active == False).count()

    return {
        "total": total,
        "active": active,
        "inactive": inactive
    }


@router.get("/{mapping_id}", response_model=BusinessOperationMappingResponse)
def get_mapping(
    mapping_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get mapping by ID."""
    mapping = db.query(BusinessOperationMapping).options(
        joinedload(BusinessOperationMapping.category_rel)
    ).filter(BusinessOperationMapping.id == mapping_id).first()

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found"
        )

    m_dict = BusinessOperationMappingResponse.model_validate(mapping).model_dump()
    m_dict['category_name'] = mapping.category_rel.name if mapping.category_rel else None

    return BusinessOperationMappingResponse(**m_dict)


@router.post("/", response_model=BusinessOperationMappingResponse)
def create_mapping(
    mapping_data: BusinessOperationMappingCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new mapping."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can create mappings"
        )

    # Verify category exists if provided
    if mapping_data.category_id:
        category = db.query(BudgetCategory).filter(
            BudgetCategory.id == mapping_data.category_id
        ).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found"
            )

    mapping = BusinessOperationMapping(
        **mapping_data.model_dump(),
        created_by=current_user.id
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)

    return mapping


@router.put("/{mapping_id}", response_model=BusinessOperationMappingResponse)
def update_mapping(
    mapping_id: int,
    mapping_update: BusinessOperationMappingUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update mapping."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can update mappings"
        )

    mapping = db.query(BusinessOperationMapping).filter(
        BusinessOperationMapping.id == mapping_id
    ).first()

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found"
        )

    update_data = mapping_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(mapping, field, value)

    db.commit()
    db.refresh(mapping)

    return mapping


@router.delete("/{mapping_id}")
def delete_mapping(
    mapping_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete mapping."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can delete mappings"
        )

    mapping = db.query(BusinessOperationMapping).filter(
        BusinessOperationMapping.id == mapping_id
    ).first()

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found"
        )

    db.delete(mapping)
    db.commit()

    return {"message": "Mapping deleted"}


@router.post("/bulk-activate")
def bulk_activate(
    mapping_ids: List[int],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Activate multiple mappings."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can modify mappings"
        )

    updated = db.query(BusinessOperationMapping).filter(
        BusinessOperationMapping.id.in_(mapping_ids)
    ).update({BusinessOperationMapping.is_active: True}, synchronize_session=False)

    db.commit()

    return {"message": f"Activated {updated} mappings"}


@router.post("/bulk-deactivate")
def bulk_deactivate(
    mapping_ids: List[int],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Deactivate multiple mappings."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can modify mappings"
        )

    updated = db.query(BusinessOperationMapping).filter(
        BusinessOperationMapping.id.in_(mapping_ids)
    ).update({BusinessOperationMapping.is_active: False}, synchronize_session=False)

    db.commit()

    return {"message": f"Deactivated {updated} mappings"}


@router.post("/bulk-delete")
def bulk_delete(
    mapping_ids: List[int],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete multiple mappings."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can delete mappings"
        )

    deleted = db.query(BusinessOperationMapping).filter(
        BusinessOperationMapping.id.in_(mapping_ids)
    ).delete(synchronize_session=False)

    db.commit()

    return {"message": f"Deleted {deleted} mappings"}
