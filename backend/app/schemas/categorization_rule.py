"""Pydantic schemas for categorization rules."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, validator

from app.db.models import CategorizationRuleTypeEnum


class CategorizationRuleBase(BaseModel):
    """Base schema for categorization rules."""
    rule_type: CategorizationRuleTypeEnum
    counterparty_inn: Optional[str] = None
    counterparty_name: Optional[str] = None
    business_operation: Optional[str] = None
    keyword: Optional[str] = None
    category_id: int
    priority: int = 10
    confidence: Decimal = Decimal("0.95")
    is_active: bool = True
    notes: Optional[str] = None

    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1."""
        if v < 0 or v > 1:
            raise ValueError('Confidence must be between 0 and 1')
        return v

    @validator('priority')
    def validate_priority(cls, v):
        """Ensure priority is positive."""
        if v < 0:
            raise ValueError('Priority must be non-negative')
        return v


class CategorizationRuleCreate(CategorizationRuleBase):
    """Schema for creating a categorization rule."""
    pass


class CategorizationRuleUpdate(BaseModel):
    """Schema for updating a categorization rule."""
    rule_type: Optional[CategorizationRuleTypeEnum] = None
    counterparty_inn: Optional[str] = None
    counterparty_name: Optional[str] = None
    business_operation: Optional[str] = None
    keyword: Optional[str] = None
    category_id: Optional[int] = None
    priority: Optional[int] = None
    confidence: Optional[Decimal] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1."""
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Confidence must be between 0 and 1')
        return v

    @validator('priority')
    def validate_priority(cls, v):
        """Ensure priority is positive."""
        if v is not None and v < 0:
            raise ValueError('Priority must be non-negative')
        return v


class CategorizationRule(CategorizationRuleBase):
    """Schema for categorization rule response."""
    id: int
    category_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None

    class Config:
        from_attributes = True
