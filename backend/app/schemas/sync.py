"""Sync schemas for 1C integration."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime, date


class Sync1CRequest(BaseModel):
    """Request for 1C sync."""
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    department_id: int
    auto_classify: bool = True


class Sync1CResult(BaseModel):
    """Result of 1C sync."""
    success: bool
    message: str
    statistics: Dict[str, Any] = {}
    errors: List[str] = []


class Sync1CConnectionTest(BaseModel):
    """Connection test result."""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
