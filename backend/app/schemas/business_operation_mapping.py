"""Business operation mapping schemas."""
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal


class BusinessOperationMappingBase(BaseModel):
    """Base mapping schema."""
    business_operation: str
    category_id: Optional[int] = None
    priority: int = 10
    confidence: Decimal = Decimal("0.98")
    notes: Optional[str] = None
    is_active: bool = True


class BusinessOperationMappingCreate(BusinessOperationMappingBase):
    """Create mapping schema."""
    pass


class BusinessOperationMappingUpdate(BaseModel):
    """Update mapping schema."""
    business_operation: Optional[str] = None
    category_id: Optional[int] = None
    priority: Optional[int] = None
    confidence: Optional[Decimal] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class BusinessOperationMappingInDB(BusinessOperationMappingBase):
    """Mapping in database."""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


class BusinessOperationMappingResponse(BusinessOperationMappingInDB):
    """Mapping response with category name."""
    category_name: Optional[str] = None
