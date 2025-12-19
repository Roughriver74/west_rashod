"""Organization API endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Organization, User, UserRoleEnum
from app.schemas.organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse
)
from app.utils.auth import get_current_active_user

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("/", response_model=List[OrganizationResponse])
def get_organizations(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all organizations."""
    query = db.query(Organization)

    if is_active is not None:
        query = query.filter(Organization.is_active == is_active)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Organization.name.ilike(search_term)) |
            (Organization.inn.ilike(search_term)) |
            (Organization.short_name.ilike(search_term))
        )

    return query.offset(skip).limit(limit).all()


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get organization by ID."""
    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    return organization


@router.post("/", response_model=OrganizationResponse)
def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new organization."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can create organizations"
        )

    organization = Organization(**org_data.model_dump())
    db.add(organization)
    db.commit()
    db.refresh(organization)

    return organization


@router.put("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: int,
    org_update: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update organization."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can update organizations"
        )

    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    update_data = org_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(organization, field, value)

    db.commit()
    db.refresh(organization)

    return organization


@router.delete("/{organization_id}")
def delete_organization(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Deactivate organization."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can delete organizations"
        )

    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    organization.is_active = False
    db.commit()

    return {"message": "Organization deactivated"}
