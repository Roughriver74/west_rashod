"""Analytics API endpoints for payment calendar."""
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from calendar import monthrange

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, extract

from app.db.session import get_db
from app.db.models import Expense, ExpenseStatusEnum, User, BankTransaction
from app.schemas.analytics import PaymentCalendarDay, PaymentsByDay
from app.schemas.expense import ExpenseResponse
from app.utils.auth import get_current_active_user

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/payment-calendar", response_model=List[PaymentCalendarDay])
def get_payment_calendar(
    year: int = Query(..., description="Year for calendar"),
    month: int = Query(..., ge=1, le=12, description="Month for calendar (1-12)"),
    category_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get payment calendar for a specific month.

    Returns daily summary of paid and planned expenses.
    """
    # Validate month/year
    if year < 2000 or year > 2100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Year must be between 2000 and 2100"
        )

    # Calculate date range for the month
    days_in_month = monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, days_in_month)

    # Build base query for expenses in this month
    base_query = db.query(Expense).filter(
        Expense.is_active == True,
        Expense.payment_date.isnot(None),
        Expense.payment_date >= start_date,
        Expense.payment_date <= end_date
    )

    # Apply filters
    if category_id:
        base_query = base_query.filter(Expense.category_id == category_id)
    if organization_id:
        base_query = base_query.filter(Expense.organization_id == organization_id)

    # Query for PAID expenses grouped by payment_date
    paid_by_date = db.query(
        Expense.payment_date,
        func.count(Expense.id).label('count'),
        func.sum(Expense.amount).label('total')
    ).filter(
        Expense.is_active == True,
        Expense.status == ExpenseStatusEnum.PAID,
        Expense.payment_date >= start_date,
        Expense.payment_date <= end_date
    )

    if category_id:
        paid_by_date = paid_by_date.filter(Expense.category_id == category_id)
    if organization_id:
        paid_by_date = paid_by_date.filter(Expense.organization_id == organization_id)

    paid_by_date = paid_by_date.group_by(Expense.payment_date).all()

    # Query for PENDING expenses grouped by payment_date (planned)
    planned_by_date = db.query(
        Expense.payment_date,
        func.count(Expense.id).label('count'),
        func.sum(Expense.amount).label('total')
    ).filter(
        Expense.is_active == True,
        Expense.status == ExpenseStatusEnum.PENDING,
        Expense.payment_date >= start_date,
        Expense.payment_date <= end_date
    )

    if category_id:
        planned_by_date = planned_by_date.filter(Expense.category_id == category_id)
    if organization_id:
        planned_by_date = planned_by_date.filter(Expense.organization_id == organization_id)

    planned_by_date = planned_by_date.group_by(Expense.payment_date).all()

    # Build result dictionary
    result_dict = {}

    # Add paid expenses
    for payment_date, count, total in paid_by_date:
        if payment_date not in result_dict:
            result_dict[payment_date] = {
                'date': payment_date,
                'total_amount': Decimal("0"),
                'payment_count': 0,
                'planned_amount': Decimal("0"),
                'planned_count': 0
            }
        result_dict[payment_date]['total_amount'] = total or Decimal("0")
        result_dict[payment_date]['payment_count'] = count or 0

    # Add planned expenses
    for payment_date, count, total in planned_by_date:
        if payment_date not in result_dict:
            result_dict[payment_date] = {
                'date': payment_date,
                'total_amount': Decimal("0"),
                'payment_count': 0,
                'planned_amount': Decimal("0"),
                'planned_count': 0
            }
        result_dict[payment_date]['planned_amount'] = total or Decimal("0")
        result_dict[payment_date]['planned_count'] = count or 0

    # Convert to list and sort by date
    result = [PaymentCalendarDay(**day_data) for day_data in result_dict.values()]
    result.sort(key=lambda x: x.date)

    return result


@router.get("/payment-calendar/{target_date}", response_model=PaymentsByDay)
def get_payments_by_day(
    target_date: date,
    category_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed list of payments for a specific day.

    Returns paid and planned expenses separated.
    """
    # Build base query
    base_query = db.query(Expense).options(
        joinedload(Expense.category_rel),
        joinedload(Expense.organization_rel),
        joinedload(Expense.contractor_rel),
        joinedload(Expense.requested_by_rel),
        joinedload(Expense.approved_by_rel)
    ).filter(
        Expense.is_active == True,
        Expense.payment_date == target_date
    )

    # Apply filters
    if category_id:
        base_query = base_query.filter(Expense.category_id == category_id)
    if organization_id:
        base_query = base_query.filter(Expense.organization_id == organization_id)

    # Get PAID expenses
    paid_expenses_query = base_query.filter(
        Expense.status == ExpenseStatusEnum.PAID
    ).order_by(Expense.id.desc())

    paid_expenses = paid_expenses_query.all()

    # Get PENDING expenses (planned)
    planned_expenses_query = base_query.filter(
        Expense.status == ExpenseStatusEnum.PENDING
    ).order_by(Expense.id.desc())

    planned_expenses = planned_expenses_query.all()

    # Build response with related data
    def build_expense_response(exp: Expense) -> ExpenseResponse:
        """Helper to build expense response with relations."""
        # Calculate linked transactions
        linked = db.query(
            func.count(BankTransaction.id),
            func.coalesce(func.sum(BankTransaction.amount), 0)
        ).filter(
            BankTransaction.expense_id == exp.id,
            BankTransaction.is_active == True
        ).first()

        exp_dict = ExpenseResponse.model_validate(exp).model_dump()
        exp_dict['category_name'] = exp.category_rel.name if exp.category_rel else None
        exp_dict['organization_name'] = exp.organization_rel.name if exp.organization_rel else None
        exp_dict['requested_by_name'] = exp.requested_by_rel.full_name if exp.requested_by_rel else None
        exp_dict['approved_by_name'] = exp.approved_by_rel.full_name if exp.approved_by_rel else None
        exp_dict['remaining_amount'] = exp.amount - exp.amount_paid
        exp_dict['linked_transactions_count'] = linked[0] or 0
        exp_dict['linked_transactions_amount'] = linked[1] or Decimal("0")

        return ExpenseResponse(**exp_dict)

    paid_list = [build_expense_response(exp) for exp in paid_expenses]
    planned_list = [build_expense_response(exp) for exp in planned_expenses]

    # Calculate totals
    total_paid = sum([exp.amount for exp in paid_expenses], Decimal("0"))
    total_planned = sum([exp.amount for exp in planned_expenses], Decimal("0"))

    return PaymentsByDay(
        date=target_date,
        paid=paid_list,
        planned=planned_list,
        total_paid_amount=total_paid,
        total_planned_amount=total_planned
    )
