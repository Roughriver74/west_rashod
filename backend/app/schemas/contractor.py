"""Contractor schemas."""
from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class ContractorBase(BaseModel):
    """Base contractor schema."""
    name: str
    short_name: Optional[str] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    contact_info: Optional[str] = None
    department_id: int
    is_active: bool = True


class ContractorCreate(ContractorBase):
    """Create contractor schema."""
    pass


class ContractorUpdate(BaseModel):
    """Update contractor schema."""
    name: Optional[str] = None
    short_name: Optional[str] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    contact_info: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None


class ContractorInDB(ContractorBase):
    """Contractor in database."""
    id: int
    external_id_1c: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ContractorResponse(ContractorInDB):
    """Contractor response."""
    pass
