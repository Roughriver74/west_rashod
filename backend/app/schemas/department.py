"""Department schemas."""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class DepartmentBase(BaseModel):
    """Base department schema."""
    name: str
    code: str
    description: Optional[str] = None
    region: Optional[str] = None
    parent_id: Optional[int] = None
    organization_id: Optional[int] = None
    is_active: bool = True


class DepartmentCreate(DepartmentBase):
    """Create department schema."""
    pass


class DepartmentUpdate(BaseModel):
    """Update department schema."""
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    region: Optional[str] = None
    parent_id: Optional[int] = None
    organization_id: Optional[int] = None
    is_active: Optional[bool] = None


class DepartmentInDB(DepartmentBase):
    """Department in database."""
    id: int
    hierarchy_path: str = ""
    hierarchy_level: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DepartmentResponse(DepartmentInDB):
    """Department response."""
    pass


class DepartmentTree(DepartmentResponse):
    """Department with children for tree structure."""
    children: List["DepartmentTree"] = []


DepartmentTree.model_rebuild()
