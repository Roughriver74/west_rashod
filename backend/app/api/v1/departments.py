"""Department API endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Department, User, UserRoleEnum
from app.schemas.department import (
    DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentTree
)
from app.utils.auth import get_current_active_user

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("/", response_model=List[DepartmentResponse])
def get_departments(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all departments."""
    query = db.query(Department)

    if is_active is not None:
        query = query.filter(Department.is_active == is_active)

    return query.offset(skip).limit(limit).all()


@router.get("/tree", response_model=List[DepartmentTree])
def get_department_tree(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get departments as tree structure."""
    departments = db.query(Department).filter(Department.is_active == True).all()

    # Build tree
    dept_dict = {d.id: DepartmentTree.model_validate(d) for d in departments}
    roots = []

    for dept in departments:
        dept_tree = dept_dict[dept.id]
        if dept.parent_id and dept.parent_id in dept_dict:
            dept_dict[dept.parent_id].children.append(dept_tree)
        else:
            roots.append(dept_tree)

    return roots


@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department(
    department_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get department by ID."""
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    return department


@router.post("/", response_model=DepartmentResponse)
def create_department(
    department_data: DepartmentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new department (ADMIN only)."""
    if current_user.role != UserRoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create departments"
        )

    # Check unique code
    existing = db.query(Department).filter(Department.code == department_data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department code already exists"
        )

    department = Department(**department_data.model_dump())

    # Set hierarchy
    if department.parent_id:
        parent = db.query(Department).filter(Department.id == department.parent_id).first()
        if parent:
            department.hierarchy_path = f"{parent.hierarchy_path}{parent.id}/"
            department.hierarchy_level = parent.hierarchy_level + 1

    db.add(department)
    db.commit()
    db.refresh(department)

    return department


@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    department_update: DepartmentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update department (ADMIN only)."""
    if current_user.role != UserRoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update departments"
        )

    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    update_data = department_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(department, field, value)

    db.commit()
    db.refresh(department)

    return department


@router.delete("/{department_id}")
def delete_department(
    department_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Deactivate department (ADMIN only)."""
    if current_user.role != UserRoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete departments"
        )

    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    department.is_active = False
    db.commit()

    return {"message": "Department deactivated"}
