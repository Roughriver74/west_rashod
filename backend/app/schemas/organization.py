"""Organization schemas."""
from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class OrganizationBase(BaseModel):
    """Base organization schema."""
    name: str
    legal_name: Optional[str] = None
    full_name: Optional[str] = None
    short_name: Optional[str] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    ogrn: Optional[str] = None
    prefix: Optional[str] = None
    okpo: Optional[str] = None
    address: Optional[str] = None
    department_id: Optional[int] = None
    is_active: bool = True


class OrganizationCreate(OrganizationBase):
    """Create organization schema."""
    pass


class OrganizationUpdate(BaseModel):
    """Update organization schema."""
    name: Optional[str] = None
    legal_name: Optional[str] = None
    full_name: Optional[str] = None
    short_name: Optional[str] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    ogrn: Optional[str] = None
    prefix: Optional[str] = None
    okpo: Optional[str] = None
    address: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None


class OrganizationInDB(OrganizationBase):
    """Organization in database."""
    id: int
    external_id_1c: Optional[str] = None
    status_1c: Optional[str] = None
    synced_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrganizationResponse(OrganizationInDB):
    """Organization response."""
    pass
