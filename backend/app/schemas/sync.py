"""Sync schemas for 1C integration."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime, date


class Sync1CRequest(BaseModel):
    """Request for 1C sync."""
    date_from: Optional[str] = None  # Accept string, parse to date
    date_to: Optional[str] = None
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
