"""Budget category API endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import BudgetCategory, User, UserRoleEnum, ExpenseTypeEnum
from app.schemas.category import (
    CategoryCreate, CategoryUpdate, CategoryResponse, CategoryTree
)
from app.utils.auth import get_current_active_user

router = APIRouter(prefix="/categories", tags=["Budget Categories"])


@router.get("/", response_model=List[CategoryResponse])
def get_categories(
    skip: int = 0,
    limit: int = 200,
    department_id: Optional[int] = None,
    type: Optional[ExpenseTypeEnum] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all budget categories."""
    query = db.query(BudgetCategory)

    if department_id:
        query = query.filter(BudgetCategory.department_id == department_id)

    if type:
        query = query.filter(BudgetCategory.type == type)

    if is_active is not None:
        query = query.filter(BudgetCategory.is_active == is_active)

    if search:
        query = query.filter(BudgetCategory.name.ilike(f"%{search}%"))

    return query.order_by(BudgetCategory.order_index, BudgetCategory.name).offset(skip).limit(limit).all()


@router.get("/tree", response_model=List[CategoryTree])
def get_category_tree(
    department_id: Optional[int] = None,
    type: Optional[ExpenseTypeEnum] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get categories as tree structure."""
    query = db.query(BudgetCategory).filter(BudgetCategory.is_active == True)

    if department_id:
        query = query.filter(BudgetCategory.department_id == department_id)

    if type:
        query = query.filter(BudgetCategory.type == type)

    categories = query.order_by(BudgetCategory.order_index, BudgetCategory.name).all()

    # Build tree
    cat_dict = {c.id: CategoryTree.model_validate(c) for c in categories}
    roots = []

    for cat in categories:
        cat_tree = cat_dict[cat.id]
        if cat.parent_id and cat.parent_id in cat_dict:
            cat_dict[cat.parent_id].children.append(cat_tree)
        else:
            roots.append(cat_tree)

    return roots


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get category by ID."""
    category = db.query(BudgetCategory).filter(BudgetCategory.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category


@router.post("/", response_model=CategoryResponse)
def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new category."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can create categories"
        )

    category = BudgetCategory(**category_data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)

    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update category."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can update categories"
        )

    category = db.query(BudgetCategory).filter(BudgetCategory.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    update_data = category_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)

    return category


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Deactivate category."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can delete categories"
        )

    category = db.query(BudgetCategory).filter(BudgetCategory.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    category.is_active = False
    db.commit()

    return {"message": "Category deactivated"}
