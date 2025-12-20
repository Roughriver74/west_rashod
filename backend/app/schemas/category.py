"""Budget category schemas."""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.db.models import ExpenseTypeEnum


class CategoryBase(BaseModel):
    """Base category schema."""
    name: str
    type: ExpenseTypeEnum
    description: Optional[str] = None
    parent_id: Optional[int] = None
    code_1c: Optional[str] = None
    is_folder: bool = False
    order_index: Optional[int] = None
    is_active: bool = True


class CategoryCreate(CategoryBase):
    """Create category schema."""
    pass


class CategoryUpdate(BaseModel):
    """Update category schema."""
    name: Optional[str] = None
    type: Optional[ExpenseTypeEnum] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    code_1c: Optional[str] = None
    is_folder: Optional[bool] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryInDB(CategoryBase):
    """Category in database."""
    id: int
    external_id_1c: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CategoryResponse(CategoryInDB):
    """Category response."""
    pass


class CategoryTree(CategoryResponse):
    """Category with children for tree structure."""
    children: List["CategoryTree"] = []


CategoryTree.model_rebuild()
