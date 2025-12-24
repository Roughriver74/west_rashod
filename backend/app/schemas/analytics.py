"""Analytics schemas for payment calendar."""
from typing import List, Optional
from pydantic import BaseModel
from datetime import date
from decimal import Decimal

from app.schemas.expense import ExpenseResponse


class PaymentCalendarDay(BaseModel):
    """Payment calendar day summary."""
    date: date
    total_amount: Decimal = Decimal("0")
    payment_count: int = 0
    planned_amount: Decimal = Decimal("0")
    planned_count: int = 0


class PaymentsByDay(BaseModel):
    """Detailed payments for a specific day."""
    date: date
    paid: List[ExpenseResponse] = []
    planned: List[ExpenseResponse] = []
    total_paid_amount: Decimal = Decimal("0")
    total_planned_amount: Decimal = Decimal("0")
