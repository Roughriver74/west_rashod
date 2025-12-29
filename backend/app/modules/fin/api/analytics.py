"""
Analytics API endpoints for Fin module.
Provides aggregated data for charts and reports.
"""
from typing import Optional, List
from datetime import date, datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, or_, case
from pydantic import BaseModel

from app.db.session import get_db
from app.utils.auth import get_current_active_user
from app.db.models import User, Organization
from app.modules.fin.models import FinReceipt, FinExpense, FinContract, FinExpenseDetail, FinManualAdjustment
from app.modules.fin.schemas import (
    FinContractsSummaryRecord,
    FinContractsSummaryPagination,
    FinContractsSummaryResponse,
)

router = APIRouter()

# === Helpers ===

def parse_csv_list(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v and v.strip()]


# === Helper functions for real principal/interest calculation ===

def get_principal_interest_from_details(
    db: Session,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    org_ids: Optional[List[int]] = None,
    contract_number: Optional[str] = None,
) -> tuple[float, float]:
    """
    Calculate real principal and interest amounts from FinExpenseDetail.
    Uses payment_type field: 'Погашение долга' for principal, 'Уплата процентов' for interest.
    Returns (principal, interest) tuple.
    """
    # Build base query joining expense details with expenses
    principal_query = db.query(func.coalesce(func.sum(FinExpenseDetail.payment_amount), 0))
    interest_query = db.query(func.coalesce(func.sum(FinExpenseDetail.payment_amount), 0))

    # Join with FinExpense to apply date and org filters
    principal_query = principal_query.join(
        FinExpense, FinExpenseDetail.expense_operation_id == FinExpense.operation_id
    )
    interest_query = interest_query.join(
        FinExpense, FinExpenseDetail.expense_operation_id == FinExpense.operation_id
    )

    # Filter by payment type
    principal_query = principal_query.filter(
        FinExpenseDetail.payment_type.ilike('%погашение долга%')
    )
    interest_query = interest_query.filter(
        FinExpenseDetail.payment_type.ilike('%уплата процентов%')
    )

    # Apply date filters
    if date_from:
        principal_query = principal_query.filter(FinExpense.document_date >= date_from)
        interest_query = interest_query.filter(FinExpense.document_date >= date_from)

    if date_to:
        principal_query = principal_query.filter(FinExpense.document_date <= date_to)
        interest_query = interest_query.filter(FinExpense.document_date <= date_to)

    # Apply organization filter
    if org_ids:
        principal_query = principal_query.filter(FinExpense.organization_id.in_(org_ids))
        interest_query = interest_query.filter(FinExpense.organization_id.in_(org_ids))

    # Apply contract filter
    if contract_number:
        principal_query = principal_query.filter(FinExpenseDetail.contract_number == contract_number)
        interest_query = interest_query.filter(FinExpenseDetail.contract_number == contract_number)

    principal = float(principal_query.scalar() or 0)
    interest = float(interest_query.scalar() or 0)

    return principal, interest


def get_principal_interest_by_month(
    db: Session,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    year: Optional[int] = None,
    org_ids: Optional[List[int]] = None,
) -> dict:
    """
    Get principal and interest amounts grouped by month.
    Returns dict with month as key and (principal, interest) tuple as value.
    """
    # Query for principal by month
    principal_query = db.query(
        func.to_char(FinExpense.document_date, 'YYYY-MM').label('month'),
        func.coalesce(func.sum(FinExpenseDetail.payment_amount), 0).label('amount')
    ).join(
        FinExpense, FinExpenseDetail.expense_operation_id == FinExpense.operation_id
    ).filter(
        FinExpenseDetail.payment_type.ilike('%погашение долга%')
    ).group_by(func.to_char(FinExpense.document_date, 'YYYY-MM'))

    interest_query = db.query(
        func.to_char(FinExpense.document_date, 'YYYY-MM').label('month'),
        func.coalesce(func.sum(FinExpenseDetail.payment_amount), 0).label('amount')
    ).join(
        FinExpense, FinExpenseDetail.expense_operation_id == FinExpense.operation_id
    ).filter(
        FinExpenseDetail.payment_type.ilike('%уплата процентов%')
    ).group_by(func.to_char(FinExpense.document_date, 'YYYY-MM'))

    # Apply date filters
    if date_from:
        principal_query = principal_query.filter(FinExpense.document_date >= date_from)
        interest_query = interest_query.filter(FinExpense.document_date >= date_from)
    if date_to:
        principal_query = principal_query.filter(FinExpense.document_date <= date_to)
        interest_query = interest_query.filter(FinExpense.document_date <= date_to)
    if year:
        principal_query = principal_query.filter(extract('year', FinExpense.document_date) == year)
        interest_query = interest_query.filter(extract('year', FinExpense.document_date) == year)
    if org_ids:
        principal_query = principal_query.filter(FinExpense.organization_id.in_(org_ids))
        interest_query = interest_query.filter(FinExpense.organization_id.in_(org_ids))

    principal_map = {row.month: float(row.amount) for row in principal_query.all()}
    interest_map = {row.month: float(row.amount) for row in interest_query.all()}

    # Combine into result dict
    all_months = set(principal_map.keys()) | set(interest_map.keys())
    result = {}
    for month in all_months:
        result[month] = (principal_map.get(month, 0), interest_map.get(month, 0))

    return result


def get_principal_interest_by_org(
    db: Session,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    org_ids: Optional[List[int]] = None,
) -> dict:
    """
    Get principal and interest amounts grouped by organization.
    Returns dict with org_id as key and (principal, interest) tuple as value.
    """
    principal_query = db.query(
        FinExpense.organization_id.label('org_id'),
        func.coalesce(func.sum(FinExpenseDetail.payment_amount), 0).label('amount')
    ).join(
        FinExpense, FinExpenseDetail.expense_operation_id == FinExpense.operation_id
    ).filter(
        FinExpenseDetail.payment_type.ilike('%погашение долга%')
    ).group_by(FinExpense.organization_id)

    interest_query = db.query(
        FinExpense.organization_id.label('org_id'),
        func.coalesce(func.sum(FinExpenseDetail.payment_amount), 0).label('amount')
    ).join(
        FinExpense, FinExpenseDetail.expense_operation_id == FinExpense.operation_id
    ).filter(
        FinExpenseDetail.payment_type.ilike('%уплата процентов%')
    ).group_by(FinExpense.organization_id)

    if date_from:
        principal_query = principal_query.filter(FinExpense.document_date >= date_from)
        interest_query = interest_query.filter(FinExpense.document_date >= date_from)
    if date_to:
        principal_query = principal_query.filter(FinExpense.document_date <= date_to)
        interest_query = interest_query.filter(FinExpense.document_date <= date_to)
    if org_ids:
        principal_query = principal_query.filter(FinExpense.organization_id.in_(org_ids))
        interest_query = interest_query.filter(FinExpense.organization_id.in_(org_ids))

    principal_map = {row.org_id: float(row.amount) for row in principal_query.all()}
    interest_map = {row.org_id: float(row.amount) for row in interest_query.all()}

    all_orgs = set(principal_map.keys()) | set(interest_map.keys())
    result = {}
    for org_id in all_orgs:
        if org_id:
            result[org_id] = (principal_map.get(org_id, 0), interest_map.get(org_id, 0))

    return result


def get_principal_interest_by_contract(
    db: Session,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    org_ids: Optional[List[int]] = None,
    payer_list: Optional[List[str]] = None,
    excluded_payer_list: Optional[List[str]] = None,
    contract_list: Optional[List[str]] = None,
) -> dict:
    """
    Get principal and interest amounts grouped by contract number.
    Returns dict with contract_number as key and (principal, interest) tuple as value.
    """
    principal_query = db.query(
        FinExpenseDetail.contract_number.label('contract'),
        func.coalesce(func.sum(FinExpenseDetail.payment_amount), 0).label('amount')
    ).join(
        FinExpense, FinExpenseDetail.expense_operation_id == FinExpense.operation_id
    ).filter(
        FinExpenseDetail.payment_type.ilike('%погашение долга%'),
        FinExpenseDetail.contract_number.isnot(None)
    ).group_by(FinExpenseDetail.contract_number)

    interest_query = db.query(
        FinExpenseDetail.contract_number.label('contract'),
        func.coalesce(func.sum(FinExpenseDetail.payment_amount), 0).label('amount')
    ).join(
        FinExpense, FinExpenseDetail.expense_operation_id == FinExpense.operation_id
    ).filter(
        FinExpenseDetail.payment_type.ilike('%уплата процентов%'),
        FinExpenseDetail.contract_number.isnot(None)
    ).group_by(FinExpenseDetail.contract_number)

    if date_from:
        principal_query = principal_query.filter(FinExpense.document_date >= date_from)
        interest_query = interest_query.filter(FinExpense.document_date >= date_from)
    if date_to:
        principal_query = principal_query.filter(FinExpense.document_date <= date_to)
        interest_query = interest_query.filter(FinExpense.document_date <= date_to)

    # Apply organization filter
    if org_ids:
        principal_query = principal_query.filter(FinExpense.organization_id.in_(org_ids))
        interest_query = interest_query.filter(FinExpense.organization_id.in_(org_ids))

    # Apply payer filters
    if payer_list:
        principal_query = principal_query.filter(FinExpense.recipient.in_(payer_list))
        interest_query = interest_query.filter(FinExpense.recipient.in_(payer_list))

    if excluded_payer_list:
        principal_query = principal_query.filter(~FinExpense.recipient.in_(excluded_payer_list))
        interest_query = interest_query.filter(~FinExpense.recipient.in_(excluded_payer_list))

    # Apply contract filter
    if contract_list:
        principal_query = principal_query.filter(FinExpenseDetail.contract_number.in_(contract_list))
        interest_query = interest_query.filter(FinExpenseDetail.contract_number.in_(contract_list))

    principal_map = {row.contract: float(row.amount) for row in principal_query.all()}
    interest_map = {row.contract: float(row.amount) for row in interest_query.all()}

    all_contracts = set(principal_map.keys()) | set(interest_map.keys())
    result = {}
    for contract in all_contracts:
        if contract:
            result[contract] = (principal_map.get(contract, 0), interest_map.get(contract, 0))

    return result


class FinSummary(BaseModel):
    """Summary statistics for fin module"""
    total_receipts: float
    total_expenses: float
    balance: float
    receipts_count: int
    expenses_count: int
    contracts_count: int
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class MonthlyCashFlow(BaseModel):
    """Monthly cash flow data"""
    month: str
    inflow: float
    outflow: float
    net: float
    cumulative: float


class OrganizationStats(BaseModel):
    """Organization statistics"""
    organization_id: int
    organization_name: str
    total_receipts: float
    total_expenses: float
    balance: float
    receipts_count: int
    expenses_count: int


@router.get("/summary", response_model=FinSummary)
def get_fin_summary(
    date_from: Optional[date] = Query(None, description="Start date filter"),
    date_to: Optional[date] = Query(None, description="End date filter"),
    organization_id: Optional[int] = Query(None, description="Organization filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get summary statistics for fin module.
    """
    # Receipts query
    receipts_query = db.query(
        func.coalesce(func.sum(FinReceipt.amount), 0).label("total"),
        func.count(FinReceipt.id).label("count")
    )

    # Expenses query
    expenses_query = db.query(
        func.coalesce(func.sum(FinExpense.amount), 0).label("total"),
        func.count(FinExpense.id).label("count")
    )

    # Apply date filters
    if date_from:
        receipts_query = receipts_query.filter(FinReceipt.document_date >= date_from)
        expenses_query = expenses_query.filter(FinExpense.document_date >= date_from)

    if date_to:
        receipts_query = receipts_query.filter(FinReceipt.document_date <= date_to)
        expenses_query = expenses_query.filter(FinExpense.document_date <= date_to)

    # Apply organization filter
    if organization_id:
        receipts_query = receipts_query.filter(FinReceipt.organization_id == organization_id)
        expenses_query = expenses_query.filter(FinExpense.organization_id == organization_id)

    receipts_result = receipts_query.first()
    expenses_result = expenses_query.first()

    total_receipts = float(receipts_result.total) if receipts_result else 0
    total_expenses = float(expenses_result.total) if expenses_result else 0

    # Count contracts
    contracts_count = db.query(func.count(FinContract.id)).scalar() or 0

    return FinSummary(
        total_receipts=total_receipts,
        total_expenses=total_expenses,
        balance=total_receipts - total_expenses,
        receipts_count=receipts_result.count if receipts_result else 0,
        expenses_count=expenses_result.count if expenses_result else 0,
        contracts_count=contracts_count,
        period_start=date_from,
        period_end=date_to,
    )


# === Credit Balances Endpoint ===

class CreditBalancesResponse(BaseModel):
    opening_balance: float
    period_received: float
    period_principal_paid: float
    period_interest_paid: float
    closing_balance: float
    total_debt: float


@router.get("/credit-balances", response_model=CreditBalancesResponse)
def get_credit_balances(
    date_from: Optional[date] = Query(None, description="Start date filter"),
    date_to: Optional[date] = Query(None, description="End date filter"),
    organizations: Optional[str] = Query(None, description="Organization names (comma-separated)"),
    payers: Optional[str] = Query(None, description="Payers (comma-separated)"),
    excluded_payers: Optional[str] = Query(None, description="Payers to exclude (comma-separated)"),
    contracts: Optional[str] = Query(None, description="Contract numbers (comma-separated)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get credit balances including opening balance, period activity, and closing balance.
    Opening balance is calculated from all operations BEFORE date_from.
    """
    # Parse organization filter
    org_ids = []
    if organizations:
        org_list = [o.strip() for o in organizations.split(",") if o.strip()]
        if org_list:
            org_ids = [o[0] for o in db.query(Organization.id).filter(Organization.name.in_(org_list)).all()]

    payer_list = parse_csv_list(payers)
    excluded_payer_list = parse_csv_list(excluded_payers)
    contract_list = parse_csv_list(contracts)

    def manual_contract_filter(query):
        """Apply contract filter for manual adjustments by number or linked contract_id."""
        if not contract_list:
            return query
        return query.outerjoin(
            FinContract, FinManualAdjustment.contract_id == FinContract.id
        ).filter(
            or_(
                FinContract.contract_number.in_(contract_list),
                FinManualAdjustment.contract_number.in_(contract_list)
            )
        )

    # === Calculate OPENING BALANCE (all operations before date_from) ===
    prior_receipts = 0.0
    prior_principal = 0.0
    prior_manual_receipts = 0.0
    prior_manual_principal = 0.0

    if date_from:
        # Prior receipts (credit money received before period)
        prior_receipts_query = db.query(func.coalesce(func.sum(FinReceipt.amount), 0))
        prior_receipts_query = prior_receipts_query.filter(FinReceipt.document_date < date_from)
        if org_ids:
            prior_receipts_query = prior_receipts_query.filter(FinReceipt.organization_id.in_(org_ids))
        if payer_list:
            prior_receipts_query = prior_receipts_query.filter(FinReceipt.payer.in_(payer_list))
        if excluded_payer_list:
            prior_receipts_query = prior_receipts_query.filter(~FinReceipt.payer.in_(excluded_payer_list))
        if contract_list:
            prior_receipts_query = prior_receipts_query.join(
                FinContract, FinReceipt.contract_id == FinContract.id, isouter=True
            ).filter(FinContract.contract_number.in_(contract_list))
        prior_receipts = float(prior_receipts_query.scalar() or 0)

        # Prior manual receipts
        manual_receipts_query = db.query(func.coalesce(func.sum(FinManualAdjustment.amount), 0)).filter(
            FinManualAdjustment.adjustment_type == 'receipt',
            FinManualAdjustment.document_date < date_from
        )
        if org_ids:
            manual_receipts_query = manual_receipts_query.filter(FinManualAdjustment.organization_id.in_(org_ids))
        if payer_list:
            manual_receipts_query = manual_receipts_query.filter(FinManualAdjustment.counterparty.in_(payer_list))
        if excluded_payer_list:
            manual_receipts_query = manual_receipts_query.filter(~FinManualAdjustment.counterparty.in_(excluded_payer_list))
        manual_receipts_query = manual_contract_filter(manual_receipts_query)
        prior_manual_receipts = float(manual_receipts_query.scalar() or 0)

        # Prior principal paid (debt repayment before period)
        prior_principal_query = db.query(func.coalesce(func.sum(FinExpenseDetail.payment_amount), 0))
        prior_principal_query = prior_principal_query.join(
            FinExpense, FinExpenseDetail.expense_operation_id == FinExpense.operation_id
        )
        prior_principal_query = prior_principal_query.filter(
            FinExpenseDetail.payment_type.ilike('%погашение долга%'),
            FinExpense.document_date < date_from
        )
        if org_ids:
            prior_principal_query = prior_principal_query.filter(FinExpense.organization_id.in_(org_ids))
        if payer_list:
            prior_principal_query = prior_principal_query.filter(FinExpense.recipient.in_(payer_list))
        if excluded_payer_list:
            prior_principal_query = prior_principal_query.filter(~FinExpense.recipient.in_(excluded_payer_list))
        if contract_list:
            prior_principal_query = prior_principal_query.filter(
                FinExpenseDetail.contract_number.in_(contract_list)
            )
        prior_principal = float(prior_principal_query.scalar() or 0)

        # Prior manual principal
        manual_principal_query = db.query(func.coalesce(func.sum(FinManualAdjustment.amount), 0)).filter(
            FinManualAdjustment.adjustment_type == 'expense',
            FinManualAdjustment.payment_type.ilike('%погашение долга%'),
            FinManualAdjustment.document_date < date_from
        )
        if org_ids:
            manual_principal_query = manual_principal_query.filter(FinManualAdjustment.organization_id.in_(org_ids))
        if payer_list:
            manual_principal_query = manual_principal_query.filter(FinManualAdjustment.counterparty.in_(payer_list))
        if excluded_payer_list:
            manual_principal_query = manual_principal_query.filter(~FinManualAdjustment.counterparty.in_(excluded_payer_list))
        manual_principal_query = manual_contract_filter(manual_principal_query)
        prior_manual_principal = float(manual_principal_query.scalar() or 0)

    opening_balance = prior_receipts + prior_manual_receipts - prior_principal - prior_manual_principal

    # === Calculate PERIOD ACTIVITY ===
    # Period receipts
    period_receipts_query = db.query(func.coalesce(func.sum(FinReceipt.amount), 0))
    if date_from:
        period_receipts_query = period_receipts_query.filter(FinReceipt.document_date >= date_from)
    if date_to:
        period_receipts_query = period_receipts_query.filter(FinReceipt.document_date <= date_to)
    if org_ids:
        period_receipts_query = period_receipts_query.filter(FinReceipt.organization_id.in_(org_ids))
    if payer_list:
        period_receipts_query = period_receipts_query.filter(FinReceipt.payer.in_(payer_list))
    if excluded_payer_list:
        period_receipts_query = period_receipts_query.filter(~FinReceipt.payer.in_(excluded_payer_list))
    if contract_list:
        period_receipts_query = period_receipts_query.join(
            FinContract, FinReceipt.contract_id == FinContract.id, isouter=True
        ).filter(FinContract.contract_number.in_(contract_list))
    period_received = float(period_receipts_query.scalar() or 0)

    # Period principal paid
    period_principal_query = db.query(func.coalesce(func.sum(FinExpenseDetail.payment_amount), 0))
    period_principal_query = period_principal_query.join(
        FinExpense, FinExpenseDetail.expense_operation_id == FinExpense.operation_id
    )
    period_principal_query = period_principal_query.filter(
        FinExpenseDetail.payment_type.ilike('%погашение долга%')
    )
    if date_from:
        period_principal_query = period_principal_query.filter(FinExpense.document_date >= date_from)
    if date_to:
        period_principal_query = period_principal_query.filter(FinExpense.document_date <= date_to)
    if org_ids:
        period_principal_query = period_principal_query.filter(FinExpense.organization_id.in_(org_ids))
    if payer_list:
        period_principal_query = period_principal_query.filter(FinExpense.recipient.in_(payer_list))
    if excluded_payer_list:
        period_principal_query = period_principal_query.filter(~FinExpense.recipient.in_(excluded_payer_list))
    if contract_list:
        period_principal_query = period_principal_query.filter(
            FinExpenseDetail.contract_number.in_(contract_list)
        )
    period_principal_paid = float(period_principal_query.scalar() or 0)

    # Period manual principal
    manual_principal_period_query = db.query(func.coalesce(func.sum(FinManualAdjustment.amount), 0)).filter(
        FinManualAdjustment.adjustment_type == 'expense',
        FinManualAdjustment.payment_type.ilike('%погашение долга%')
    )
    if date_from:
        manual_principal_period_query = manual_principal_period_query.filter(FinManualAdjustment.document_date >= date_from)
    if date_to:
        manual_principal_period_query = manual_principal_period_query.filter(FinManualAdjustment.document_date <= date_to)
    if org_ids:
        manual_principal_period_query = manual_principal_period_query.filter(FinManualAdjustment.organization_id.in_(org_ids))
    if payer_list:
        manual_principal_period_query = manual_principal_period_query.filter(FinManualAdjustment.counterparty.in_(payer_list))
    if excluded_payer_list:
        manual_principal_period_query = manual_principal_period_query.filter(~FinManualAdjustment.counterparty.in_(excluded_payer_list))
    manual_principal_period_query = manual_contract_filter(manual_principal_period_query)
    manual_principal_paid = float(manual_principal_period_query.scalar() or 0)

    # Period interest paid
    period_interest_query = db.query(func.coalesce(func.sum(FinExpenseDetail.payment_amount), 0))
    period_interest_query = period_interest_query.join(
        FinExpense, FinExpenseDetail.expense_operation_id == FinExpense.operation_id
    )
    period_interest_query = period_interest_query.filter(
        FinExpenseDetail.payment_type.ilike('%уплата процентов%')
    )
    if date_from:
        period_interest_query = period_interest_query.filter(FinExpense.document_date >= date_from)
    if date_to:
        period_interest_query = period_interest_query.filter(FinExpense.document_date <= date_to)
    if org_ids:
        period_interest_query = period_interest_query.filter(FinExpense.organization_id.in_(org_ids))
    if payer_list:
        period_interest_query = period_interest_query.filter(FinExpense.recipient.in_(payer_list))
    if excluded_payer_list:
        period_interest_query = period_interest_query.filter(~FinExpense.recipient.in_(excluded_payer_list))
    if contract_list:
        period_interest_query = period_interest_query.filter(
            FinExpenseDetail.contract_number.in_(contract_list)
        )
    period_interest_paid = float(period_interest_query.scalar() or 0)

    # Period manual interest
    manual_interest_period_query = db.query(func.coalesce(func.sum(FinManualAdjustment.amount), 0)).filter(
        FinManualAdjustment.adjustment_type == 'expense',
        FinManualAdjustment.payment_type.ilike('%уплата процентов%')
    )
    if date_from:
        manual_interest_period_query = manual_interest_period_query.filter(FinManualAdjustment.document_date >= date_from)
    if date_to:
        manual_interest_period_query = manual_interest_period_query.filter(FinManualAdjustment.document_date <= date_to)
    if org_ids:
        manual_interest_period_query = manual_interest_period_query.filter(FinManualAdjustment.organization_id.in_(org_ids))
    if payer_list:
        manual_interest_period_query = manual_interest_period_query.filter(FinManualAdjustment.counterparty.in_(payer_list))
    if excluded_payer_list:
        manual_interest_period_query = manual_interest_period_query.filter(~FinManualAdjustment.counterparty.in_(excluded_payer_list))
    manual_interest_period_query = manual_contract_filter(manual_interest_period_query)
    manual_interest_paid = float(manual_interest_period_query.scalar() or 0)

    # Period receipts from manual adjustments (calculate once cleanly)
    manual_receipts_period_query = db.query(func.coalesce(func.sum(FinManualAdjustment.amount), 0)).filter(
        FinManualAdjustment.adjustment_type == 'receipt'
    )
    if date_from:
        manual_receipts_period_query = manual_receipts_period_query.filter(FinManualAdjustment.document_date >= date_from)
    if date_to:
        manual_receipts_period_query = manual_receipts_period_query.filter(FinManualAdjustment.document_date <= date_to)
    if org_ids:
        manual_receipts_period_query = manual_receipts_period_query.filter(FinManualAdjustment.organization_id.in_(org_ids))
    if payer_list:
        manual_receipts_period_query = manual_receipts_period_query.filter(FinManualAdjustment.counterparty.in_(payer_list))
    if excluded_payer_list:
        manual_receipts_period_query = manual_receipts_period_query.filter(~FinManualAdjustment.counterparty.in_(excluded_payer_list))
    manual_receipts_period_query = manual_contract_filter(manual_receipts_period_query)
    manual_period_received = float(manual_receipts_period_query.scalar() or 0)

    # === Calculate CLOSING BALANCE ===
    total_period_received = period_received + manual_period_received

    total_period_principal = period_principal_paid + manual_principal_paid
    total_period_interest = period_interest_paid + manual_interest_paid

    closing_balance = opening_balance + total_period_received - total_period_principal

    return CreditBalancesResponse(
        opening_balance=opening_balance,
        period_received=total_period_received,
        period_principal_paid=total_period_principal,
        period_interest_paid=total_period_interest,
        closing_balance=closing_balance,
        total_debt=closing_balance,
    )


@router.get("/monthly-cashflow", response_model=List[MonthlyCashFlow])
def get_monthly_cashflow(
    date_from: Optional[date] = Query(None, description="Start date filter"),
    date_to: Optional[date] = Query(None, description="End date filter"),
    organization_id: Optional[int] = Query(None, description="Organization filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get monthly cash flow data for charts.
    """
    # Base queries with month extraction
    receipts_query = db.query(
        func.to_char(FinReceipt.document_date, 'YYYY-MM').label("month"),
        func.sum(FinReceipt.amount).label("inflow")
    ).group_by(
        func.to_char(FinReceipt.document_date, 'YYYY-MM')
    )

    expenses_query = db.query(
        func.to_char(FinExpense.document_date, 'YYYY-MM').label("month"),
        func.sum(FinExpense.amount).label("outflow")
    ).group_by(
        func.to_char(FinExpense.document_date, 'YYYY-MM')
    )

    # Apply date filters
    if date_from:
        receipts_query = receipts_query.filter(FinReceipt.document_date >= date_from)
        expenses_query = expenses_query.filter(FinExpense.document_date >= date_from)

    if date_to:
        receipts_query = receipts_query.filter(FinReceipt.document_date <= date_to)
        expenses_query = expenses_query.filter(FinExpense.document_date <= date_to)

    # Apply organization filter
    if organization_id:
        receipts_query = receipts_query.filter(FinReceipt.organization_id == organization_id)
        expenses_query = expenses_query.filter(FinExpense.organization_id == organization_id)

    # Execute queries
    receipts_data = {r.month: float(r.inflow) for r in receipts_query.all()}
    expenses_data = {e.month: float(e.outflow) for e in expenses_query.all()}

    # Merge months
    all_months = sorted(set(receipts_data.keys()) | set(expenses_data.keys()))

    # Build result with cumulative
    result = []
    cumulative = 0

    for month in all_months:
        inflow = receipts_data.get(month, 0)
        outflow = expenses_data.get(month, 0)
        net = inflow - outflow
        cumulative += net

        result.append(MonthlyCashFlow(
            month=month,
            inflow=inflow,
            outflow=outflow,
            net=net,
            cumulative=cumulative,
        ))

    return result


@router.get("/by-organization", response_model=List[OrganizationStats])
def get_stats_by_organization(
    date_from: Optional[date] = Query(None, description="Start date filter"),
    date_to: Optional[date] = Query(None, description="End date filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get statistics grouped by organization.
    """
    # Receipts by organization
    receipts_query = db.query(
        FinReceipt.organization_id,
        func.sum(FinReceipt.amount).label("total"),
        func.count(FinReceipt.id).label("count")
    ).filter(
        FinReceipt.organization_id.isnot(None)
    ).group_by(
        FinReceipt.organization_id
    )

    # Expenses by organization
    expenses_query = db.query(
        FinExpense.organization_id,
        func.sum(FinExpense.amount).label("total"),
        func.count(FinExpense.id).label("count")
    ).filter(
        FinExpense.organization_id.isnot(None)
    ).group_by(
        FinExpense.organization_id
    )

    # Apply date filters
    if date_from:
        receipts_query = receipts_query.filter(FinReceipt.document_date >= date_from)
        expenses_query = expenses_query.filter(FinExpense.document_date >= date_from)

    if date_to:
        receipts_query = receipts_query.filter(FinReceipt.document_date <= date_to)
        expenses_query = expenses_query.filter(FinExpense.document_date <= date_to)

    # Execute and build maps
    receipts_map = {r.organization_id: {"total": float(r.total), "count": r.count}
                    for r in receipts_query.all()}
    expenses_map = {e.organization_id: {"total": float(e.total), "count": e.count}
                    for e in expenses_query.all()}

    # Get all organization IDs
    all_org_ids = set(receipts_map.keys()) | set(expenses_map.keys())

    # Fetch organization names
    orgs = db.query(Organization).filter(Organization.id.in_(all_org_ids)).all()
    org_names = {org.id: org.name for org in orgs}

    # Build result
    result = []
    for org_id in all_org_ids:
        receipts = receipts_map.get(org_id, {"total": 0, "count": 0})
        expenses = expenses_map.get(org_id, {"total": 0, "count": 0})

        result.append(OrganizationStats(
            organization_id=org_id,
            organization_name=org_names.get(org_id, f"Org #{org_id}"),
            total_receipts=receipts["total"],
            total_expenses=expenses["total"],
            balance=receipts["total"] - expenses["total"],
            receipts_count=receipts["count"],
            expenses_count=expenses["count"],
        ))

    # Sort by total receipts descending
    result.sort(key=lambda x: x.total_receipts, reverse=True)

    return result


@router.get("/top-payers")
def get_top_payers(
    limit: int = Query(10, ge=1, le=10000000),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get top payers by total receipts.
    """
    query = db.query(
        FinReceipt.payer,
        func.sum(FinReceipt.amount).label("total"),
        func.count(FinReceipt.id).label("count")
    ).filter(
        FinReceipt.payer.isnot(None),
        FinReceipt.payer != ""
    ).group_by(
        FinReceipt.payer
    )

    if date_from:
        query = query.filter(FinReceipt.document_date >= date_from)
    if date_to:
        query = query.filter(FinReceipt.document_date <= date_to)

    query = query.order_by(func.sum(FinReceipt.amount).desc()).limit(limit)

    result = []
    for row in query.all():
        result.append({
            "payer": row.payer,
            "total": float(row.total),
            "count": row.count,
        })

    return result


@router.get("/top-recipients")
def get_top_recipients(
    limit: int = Query(10, ge=1, le=10000000),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get top recipients by total expenses.
    """
    query = db.query(
        FinExpense.recipient,
        func.sum(FinExpense.amount).label("total"),
        func.count(FinExpense.id).label("count")
    ).filter(
        FinExpense.recipient.isnot(None),
        FinExpense.recipient != ""
    ).group_by(
        FinExpense.recipient
    )

    if date_from:
        query = query.filter(FinExpense.document_date >= date_from)
    if date_to:
        query = query.filter(FinExpense.document_date <= date_to)

    query = query.order_by(func.sum(FinExpense.amount).desc()).limit(limit)

    result = []
    for row in query.all():
        result.append({
            "recipient": row.recipient,
            "total": float(row.total),
            "count": row.count,
        })

    return result


# === KPI Metrics ===

class KPIMetrics(BaseModel):
    """KPI metrics for dashboard"""
    repaymentVelocity: float
    paymentEfficiency: float
    avgInterestRate: float
    debtRatio: float
    activeContracts: int
    totalContracts: int
    totalReceived: float
    totalExpenses: float
    principalPaid: float
    interestPaid: float


@router.get("/kpi", response_model=KPIMetrics)
def get_kpi_metrics(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    organizations: Optional[str] = Query(None, description="Comma-separated org names"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get KPI metrics for the dashboard.
    """
    # Parse organization filter by name
    org_ids = []
    if organizations:
        org_list = [o.strip() for o in organizations.split(",") if o.strip()]
        if org_list:
            org_ids = [o[0] for o in db.query(Organization.id).filter(Organization.name.in_(org_list)).all()]

    # Base queries
    receipts_query = db.query(func.sum(FinReceipt.amount).label("total"))
    expenses_query = db.query(func.sum(FinExpense.amount).label("total"))
    contracts_query = db.query(FinContract)

    # Apply date filters
    if date_from:
        receipts_query = receipts_query.filter(FinReceipt.document_date >= date_from)
        expenses_query = expenses_query.filter(FinExpense.document_date >= date_from)

    if date_to:
        receipts_query = receipts_query.filter(FinReceipt.document_date <= date_to)
        expenses_query = expenses_query.filter(FinExpense.document_date <= date_to)

    # Apply organization filters
    if org_ids:
        receipts_query = receipts_query.filter(FinReceipt.organization_id.in_(org_ids))
        expenses_query = expenses_query.filter(FinExpense.organization_id.in_(org_ids))

    # Get totals
    total_received = float(receipts_query.scalar() or 0)
    total_expenses = float(expenses_query.scalar() or 0)

    # Count contracts
    total_contracts = contracts_query.count()
    active_contracts = contracts_query.filter(FinContract.is_active == True).count()

    # Calculate real principal and interest from FinExpenseDetail
    principal_paid, interest_paid = get_principal_interest_from_details(
        db, date_from, date_to, org_ids
    )

    # Calculate ratios
    repayment_velocity = (principal_paid / total_received * 100) if total_received > 0 else 0
    payment_efficiency = (principal_paid / total_expenses * 100) if total_expenses > 0 else 0
    avg_interest_rate = (interest_paid / principal_paid * 100) if principal_paid > 0 else 0
    debt_ratio = ((total_received - principal_paid) / total_received * 100) if total_received > 0 else 0

    return KPIMetrics(
        repaymentVelocity=round(repayment_velocity, 2),
        paymentEfficiency=round(payment_efficiency, 2),
        avgInterestRate=round(avg_interest_rate, 2),
        debtRatio=round(debt_ratio, 2),
        activeContracts=active_contracts,
        totalContracts=total_contracts,
        totalReceived=total_received,
        totalExpenses=total_expenses,
        principalPaid=principal_paid,
        interestPaid=interest_paid,
    )


# === Turnover Balance ===

class TurnoverBalanceRow(BaseModel):
    """Turnover balance row"""
    account: str
    counterparty: Optional[str] = None
    parentCounterparty: Optional[str] = None
    inn: Optional[str] = None
    contract: Optional[str] = None
    balanceStartDebit: float
    balanceStartCredit: float
    turnoverDebit: float
    turnoverCredit: float
    balanceEndDebit: float
    balanceEndCredit: float
    level: int


@router.get("/turnover-balance", response_model=List[TurnoverBalanceRow])
def get_turnover_balance(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    organizations: Optional[str] = Query(None),
    payers: Optional[str] = Query(None),
    excluded_payers: Optional[str] = Query(None),
    contracts: Optional[str] = Query(None),
    account_number: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get turnover balance sheet (Оборотно-сальдовая ведомость).
    Groups data by accounting account, counterparty, and contract.
    """
    # Parse organization filter by name
    org_ids = []
    if organizations:
        org_list = [o.strip() for o in organizations.split(",") if o.strip()]
        if org_list:
            org_ids = [o[0] for o in db.query(Organization.id).filter(Organization.name.in_(org_list)).all()]

    # Parse payers filter
    payer_list = parse_csv_list(payers)

    # Parse excluded payers
    excluded_payer_list = parse_csv_list(excluded_payers)

    # Parse contracts filter
    contract_list = parse_csv_list(contracts)

    # Get receipts grouped by counterparty and contract
    receipts_query = db.query(
        FinReceipt.payer.label("counterparty"),
        FinContract.contract_number.label("contract"),
        func.sum(FinReceipt.amount).label("amount")
    ).outerjoin(
        FinContract, FinReceipt.contract_id == FinContract.id
    ).filter(
        FinReceipt.payer.isnot(None)
    ).group_by(
        FinReceipt.payer, FinContract.contract_number
    )

    # Get expenses grouped by counterparty and contract
    expenses_query = db.query(
        FinExpense.recipient.label("counterparty"),
        FinContract.contract_number.label("contract"),
        func.sum(FinExpense.amount).label("amount")
    ).outerjoin(
        FinContract, FinExpense.contract_id == FinContract.id
    ).filter(
        FinExpense.recipient.isnot(None)
    ).group_by(
        FinExpense.recipient, FinContract.contract_number
    )

    # Apply filters
    if date_from:
        receipts_query = receipts_query.filter(FinReceipt.document_date >= date_from)
        expenses_query = expenses_query.filter(FinExpense.document_date >= date_from)

    if date_to:
        receipts_query = receipts_query.filter(FinReceipt.document_date <= date_to)
        expenses_query = expenses_query.filter(FinExpense.document_date <= date_to)

    if org_ids:
        receipts_query = receipts_query.filter(FinReceipt.organization_id.in_(org_ids))
        expenses_query = expenses_query.filter(FinExpense.organization_id.in_(org_ids))

    if payer_list:
        receipts_query = receipts_query.filter(FinReceipt.payer.in_(payer_list))
        expenses_query = expenses_query.filter(FinExpense.recipient.in_(payer_list))

    if excluded_payer_list:
        receipts_query = receipts_query.filter(~FinReceipt.payer.in_(excluded_payer_list))
        expenses_query = expenses_query.filter(~FinExpense.recipient.in_(excluded_payer_list))

    if contract_list:
        receipts_query = receipts_query.filter(FinContract.contract_number.in_(contract_list))
        expenses_query = expenses_query.filter(FinContract.contract_number.in_(contract_list))

    # Execute queries
    receipts_data = receipts_query.all()
    expenses_data = expenses_query.all()

    # Build hierarchical structure
    accounts_data = {}
    default_account = account_number or "67"

    # Process receipts (credits)
    for row in receipts_data:
        counterparty = row.counterparty or "Без контрагента"
        contract = row.contract or ""
        amount = float(row.amount or 0)

        if default_account not in accounts_data:
            accounts_data[default_account] = {"counterparties": {}}

        if counterparty not in accounts_data[default_account]["counterparties"]:
            accounts_data[default_account]["counterparties"][counterparty] = {"contracts": {}, "totals": {"credit": 0, "debit": 0}}

        accounts_data[default_account]["counterparties"][counterparty]["totals"]["credit"] += amount

        if contract:
            if contract not in accounts_data[default_account]["counterparties"][counterparty]["contracts"]:
                accounts_data[default_account]["counterparties"][counterparty]["contracts"][contract] = {"credit": 0, "debit": 0}
            accounts_data[default_account]["counterparties"][counterparty]["contracts"][contract]["credit"] += amount

    # Process expenses (debits)
    for row in expenses_data:
        counterparty = row.counterparty or "Без контрагента"
        contract = row.contract or ""
        amount = float(row.amount or 0)

        if default_account not in accounts_data:
            accounts_data[default_account] = {"counterparties": {}}

        if counterparty not in accounts_data[default_account]["counterparties"]:
            accounts_data[default_account]["counterparties"][counterparty] = {"contracts": {}, "totals": {"credit": 0, "debit": 0}}

        accounts_data[default_account]["counterparties"][counterparty]["totals"]["debit"] += amount

        if contract:
            if contract not in accounts_data[default_account]["counterparties"][counterparty]["contracts"]:
                accounts_data[default_account]["counterparties"][counterparty]["contracts"][contract] = {"credit": 0, "debit": 0}
            accounts_data[default_account]["counterparties"][counterparty]["contracts"][contract]["debit"] += amount

    # Flatten to rows
    result = []
    for account, acc_data in sorted(accounts_data.items()):
        total_credit = 0
        total_debit = 0

        for counterparty, cp_data in acc_data["counterparties"].items():
            total_credit += cp_data["totals"]["credit"]
            total_debit += cp_data["totals"]["debit"]

        # Account level row
        balance = total_credit - total_debit
        result.append(TurnoverBalanceRow(
            account=account,
            balanceStartDebit=0,
            balanceStartCredit=0,
            turnoverDebit=total_debit,
            turnoverCredit=total_credit,
            balanceEndDebit=abs(balance) if balance < 0 else 0,
            balanceEndCredit=balance if balance > 0 else 0,
            level=0,
        ))

        # Counterparty level rows
        for counterparty, cp_data in sorted(acc_data["counterparties"].items()):
            cp_balance = cp_data["totals"]["credit"] - cp_data["totals"]["debit"]
            result.append(TurnoverBalanceRow(
                account=account,
                counterparty=counterparty,
                balanceStartDebit=0,
                balanceStartCredit=0,
                turnoverDebit=cp_data["totals"]["debit"],
                turnoverCredit=cp_data["totals"]["credit"],
                balanceEndDebit=abs(cp_balance) if cp_balance < 0 else 0,
                balanceEndCredit=cp_balance if cp_balance > 0 else 0,
                level=1,
            ))

            # Contract level rows
            for contract, ct_data in sorted(cp_data["contracts"].items()):
                ct_balance = ct_data["credit"] - ct_data["debit"]
                result.append(TurnoverBalanceRow(
                    account=account,
                    counterparty=counterparty,
                    parentCounterparty=counterparty,
                    contract=contract,
                    balanceStartDebit=0,
                    balanceStartCredit=0,
                    turnoverDebit=ct_data["debit"],
                    turnoverCredit=ct_data["credit"],
                    balanceEndDebit=abs(ct_balance) if ct_balance < 0 else 0,
                    balanceEndCredit=ct_balance if ct_balance > 0 else 0,
                    level=2,
                ))

    return result


# === Organization Efficiency ===

class OrgEfficiencyMetric(BaseModel):
    """Organization efficiency metric"""
    id: int
    name: str
    totalPaid: float
    principal: float
    interest: float
    received: float
    efficiency: float
    debtRatio: float
    operationsCount: int


@router.get("/org-efficiency", response_model=List[OrgEfficiencyMetric])
def get_org_efficiency(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    organizations: Optional[str] = Query(None, description="Comma-separated org names"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get efficiency metrics by organization.
    """
    # Parse organization filter by name
    org_ids = []
    if organizations:
        org_list = [o.strip() for o in organizations.split(",") if o.strip()]
        if org_list:
            org_ids = [o[0] for o in db.query(Organization.id).filter(Organization.name.in_(org_list)).all()]

    # Receipts by organization
    receipts_query = db.query(
        FinReceipt.organization_id,
        func.sum(FinReceipt.amount).label("received"),
        func.count(FinReceipt.id).label("count")
    ).filter(
        FinReceipt.organization_id.isnot(None)
    ).group_by(FinReceipt.organization_id)

    # Expenses by organization
    expenses_query = db.query(
        FinExpense.organization_id,
        func.sum(FinExpense.amount).label("paid"),
        func.count(FinExpense.id).label("count")
    ).filter(
        FinExpense.organization_id.isnot(None)
    ).group_by(FinExpense.organization_id)

    # Apply filters
    if date_from:
        receipts_query = receipts_query.filter(FinReceipt.document_date >= date_from)
        expenses_query = expenses_query.filter(FinExpense.document_date >= date_from)

    if date_to:
        receipts_query = receipts_query.filter(FinReceipt.document_date <= date_to)
        expenses_query = expenses_query.filter(FinExpense.document_date <= date_to)

    if org_ids:
        receipts_query = receipts_query.filter(FinReceipt.organization_id.in_(org_ids))
        expenses_query = expenses_query.filter(FinExpense.organization_id.in_(org_ids))

    receipts_map = {r.organization_id: {"received": float(r.received), "count": r.count} for r in receipts_query.all()}
    expenses_map = {e.organization_id: {"paid": float(e.paid), "count": e.count} for e in expenses_query.all()}

    # Get all org IDs
    all_org_ids = set(receipts_map.keys()) | set(expenses_map.keys())

    # Get org names
    orgs = db.query(Organization).filter(Organization.id.in_(all_org_ids)).all()
    org_names = {org.id: org.name for org in orgs}

    # Get real principal/interest by organization
    org_payments = get_principal_interest_by_org(db, date_from, date_to, org_ids if org_ids else None)

    result = []
    for org_id in all_org_ids:
        receipts = receipts_map.get(org_id, {"received": 0, "count": 0})
        expenses = expenses_map.get(org_id, {"paid": 0, "count": 0})

        total_paid = expenses["paid"]
        received = receipts["received"]
        operations_count = receipts["count"] + expenses["count"]

        # Get real principal and interest from FinExpenseDetail
        principal, interest = org_payments.get(org_id, (0, 0))

        efficiency = (principal / total_paid * 100) if total_paid > 0 else 0
        debt_ratio = ((received - principal) / received * 100) if received > 0 else 0

        result.append(OrgEfficiencyMetric(
            id=org_id,
            name=org_names.get(org_id, f"Org #{org_id}"),
            totalPaid=total_paid,
            principal=principal,
            interest=interest,
            received=received,
            efficiency=round(efficiency, 2),
            debtRatio=round(debt_ratio, 2),
            operationsCount=operations_count,
        ))

    # Sort by total paid descending
    result.sort(key=lambda x: x.totalPaid, reverse=True)

    return result


# === Monthly Efficiency ===

class MonthlyEfficiency(BaseModel):
    """Monthly efficiency data"""
    month: str
    principal: float
    interest: float
    total: float
    efficiency: float


@router.get("/monthly-efficiency", response_model=List[MonthlyEfficiency])
def get_monthly_efficiency(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    year: Optional[int] = Query(None),
    organizations: Optional[str] = Query(None, description="Comma-separated org names"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get monthly payment efficiency (principal vs interest).
    Uses real data from FinExpenseDetail.payment_type.
    """
    # Parse organization filter by name
    org_ids = []
    if organizations:
        org_list = [o.strip() for o in organizations.split(",") if o.strip()]
        if org_list:
            org_ids = [o[0] for o in db.query(Organization.id).filter(Organization.name.in_(org_list)).all()]

    # Get real principal/interest by month from FinExpenseDetail
    monthly_payments = get_principal_interest_by_month(db, date_from, date_to, year, org_ids if org_ids else None)

    result = []
    for month in sorted(monthly_payments.keys()):
        principal, interest = monthly_payments[month]
        total = principal + interest
        efficiency = (principal / total * 100) if total > 0 else 0

        result.append(MonthlyEfficiency(
            month=month,
            principal=principal,
            interest=interest,
            total=total,
            efficiency=round(efficiency, 2),
        ))

    return result


# === Contracts Summary ===

@router.get("/contracts-summary", response_model=FinContractsSummaryResponse)
def get_contracts_summary(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    organizations: Optional[str] = Query(None),
    payers: Optional[str] = Query(None),
    excluded_payers: Optional[str] = Query(None),
    contracts: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=10000000),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get contracts summary with pagination.
    """
    # Parse organization filter by name
    org_ids = []
    if organizations:
        org_list = [o.strip() for o in organizations.split(",") if o.strip()]
        if org_list:
            org_ids = [o[0] for o in db.query(Organization.id).filter(Organization.name.in_(org_list)).all()]

    payer_list = parse_csv_list(payers)
    excluded_payer_list = parse_csv_list(excluded_payers)
    contract_list = parse_csv_list(contracts)

    # Receipts grouped by contract (via contract_id -> contract_number)
    contract_expr = FinContract.contract_number
    receipts_query = db.query(
        contract_expr.label("contract"),
        func.sum(FinReceipt.amount).label("received"),
        func.min(FinReceipt.document_date).label("first_receipt")
    ).outerjoin(
        FinContract, FinReceipt.contract_id == FinContract.id
    ).filter(
        contract_expr.isnot(None)
    ).group_by(
        contract_expr
    )

    # Apply filters to receipts
    if date_from:
        receipts_query = receipts_query.filter(FinReceipt.document_date >= date_from)
    if date_to:
        receipts_query = receipts_query.filter(FinReceipt.document_date <= date_to)
    if org_ids:
        receipts_query = receipts_query.filter(FinReceipt.organization_id.in_(org_ids))
    if payer_list:
        receipts_query = receipts_query.filter(FinReceipt.payer.in_(payer_list))
    if excluded_payer_list:
        receipts_query = receipts_query.filter(~FinReceipt.payer.in_(excluded_payer_list))
    if contract_list:
        receipts_query = receipts_query.filter(contract_expr.in_(contract_list))

    receipts_map = {
        row.contract: {
            "received": float(row.received or 0),
            "first_receipt": row.first_receipt.isoformat() if row.first_receipt else None,
        }
        for row in receipts_query.all()
        if row.contract
    }

    # Manual receipts grouped by contract
    manual_contract_expr = func.coalesce(FinManualAdjustment.contract_number, FinContract.contract_number)
    manual_receipts_query = db.query(
        manual_contract_expr.label("contract"),
        func.coalesce(func.sum(FinManualAdjustment.amount), 0).label("received")
    ).outerjoin(
        FinContract, FinManualAdjustment.contract_id == FinContract.id
    ).filter(
        FinManualAdjustment.adjustment_type == 'receipt',
        manual_contract_expr.isnot(None)
    ).group_by(
        manual_contract_expr
    )

    if date_from:
        manual_receipts_query = manual_receipts_query.filter(FinManualAdjustment.document_date >= date_from)
    if date_to:
        manual_receipts_query = manual_receipts_query.filter(FinManualAdjustment.document_date <= date_to)
    if org_ids:
        manual_receipts_query = manual_receipts_query.filter(FinManualAdjustment.organization_id.in_(org_ids))
    if payer_list:
        manual_receipts_query = manual_receipts_query.filter(FinManualAdjustment.counterparty.in_(payer_list))
    if excluded_payer_list:
        manual_receipts_query = manual_receipts_query.filter(~FinManualAdjustment.counterparty.in_(excluded_payer_list))
    if contract_list:
        manual_receipts_query = manual_receipts_query.filter(
            or_(
                FinManualAdjustment.contract_number.in_(contract_list),
                FinContract.contract_number.in_(contract_list)
            )
        )

    manual_receipts_map = {
        row.contract: float(row.received or 0)
        for row in manual_receipts_query.all()
        if row.contract
    }

    # Opening balances require prior receipts/principal if date_from is set
    prior_receipts_map = {}
    manual_prior_receipts_map = {}
    prior_principal_map = {}
    manual_prior_principal_map = {}

    if date_from:
        # Receipts before period
        prior_receipts_query = db.query(
            contract_expr.label("contract"),
            func.coalesce(func.sum(FinReceipt.amount), 0).label("received")
        ).outerjoin(
            FinContract, FinReceipt.contract_id == FinContract.id
        ).filter(
            contract_expr.isnot(None),
            FinReceipt.document_date < date_from
        ).group_by(contract_expr)

        if org_ids:
            prior_receipts_query = prior_receipts_query.filter(FinReceipt.organization_id.in_(org_ids))
        if payer_list:
            prior_receipts_query = prior_receipts_query.filter(FinReceipt.payer.in_(payer_list))
        if excluded_payer_list:
            prior_receipts_query = prior_receipts_query.filter(~FinReceipt.payer.in_(excluded_payer_list))
        if contract_list:
            prior_receipts_query = prior_receipts_query.filter(contract_expr.in_(contract_list))

        prior_receipts_map = {
            row.contract: float(row.received or 0)
            for row in prior_receipts_query.all()
            if row.contract
        }

        # Manual receipts before period
        manual_prior_receipts_query = db.query(
            manual_contract_expr.label("contract"),
            func.coalesce(func.sum(FinManualAdjustment.amount), 0).label("received")
        ).outerjoin(
            FinContract, FinManualAdjustment.contract_id == FinContract.id
        ).filter(
            manual_contract_expr.isnot(None),
            FinManualAdjustment.adjustment_type == 'receipt',
            FinManualAdjustment.document_date < date_from
        ).group_by(manual_contract_expr)

        if org_ids:
            manual_prior_receipts_query = manual_prior_receipts_query.filter(FinManualAdjustment.organization_id.in_(org_ids))
        if payer_list:
            manual_prior_receipts_query = manual_prior_receipts_query.filter(FinManualAdjustment.counterparty.in_(payer_list))
        if excluded_payer_list:
            manual_prior_receipts_query = manual_prior_receipts_query.filter(~FinManualAdjustment.counterparty.in_(excluded_payer_list))
        if contract_list:
            manual_prior_receipts_query = manual_prior_receipts_query.filter(
                or_(
                    FinManualAdjustment.contract_number.in_(contract_list),
                    FinContract.contract_number.in_(contract_list)
                )
            )

        manual_prior_receipts_map = {
            row.contract: float(row.received or 0)
            for row in manual_prior_receipts_query.all()
            if row.contract
        }

        # Principal repayments before period (from FinExpenseDetail)
        prior_principal_query = db.query(
            FinExpenseDetail.contract_number.label('contract'),
            func.coalesce(func.sum(FinExpenseDetail.payment_amount), 0).label('amount')
        ).join(
            FinExpense, FinExpenseDetail.expense_operation_id == FinExpense.operation_id
        ).filter(
            FinExpenseDetail.payment_type.ilike('%погашение долга%'),
            FinExpense.document_date < date_from,
            FinExpenseDetail.contract_number.isnot(None)
        ).group_by(FinExpenseDetail.contract_number)

        if org_ids:
            prior_principal_query = prior_principal_query.filter(FinExpense.organization_id.in_(org_ids))
        if payer_list:
            prior_principal_query = prior_principal_query.filter(FinExpense.recipient.in_(payer_list))
        if excluded_payer_list:
            prior_principal_query = prior_principal_query.filter(~FinExpense.recipient.in_(excluded_payer_list))
        if contract_list:
            prior_principal_query = prior_principal_query.filter(FinExpenseDetail.contract_number.in_(contract_list))

        prior_principal_map = {
            row.contract: float(row.amount or 0)
            for row in prior_principal_query.all()
            if row.contract
        }

        # Manual principal before period
        manual_prior_principal_query = db.query(
            manual_contract_expr.label("contract"),
            func.coalesce(func.sum(FinManualAdjustment.amount), 0).label("amount")
        ).outerjoin(
            FinContract, FinManualAdjustment.contract_id == FinContract.id
        ).filter(
            manual_contract_expr.isnot(None),
            FinManualAdjustment.adjustment_type == 'expense',
            FinManualAdjustment.payment_type.ilike('%погашение долга%'),
            FinManualAdjustment.document_date < date_from
        ).group_by(manual_contract_expr)

        if org_ids:
            manual_prior_principal_query = manual_prior_principal_query.filter(FinManualAdjustment.organization_id.in_(org_ids))
        if payer_list:
            manual_prior_principal_query = manual_prior_principal_query.filter(FinManualAdjustment.counterparty.in_(payer_list))
        if excluded_payer_list:
            manual_prior_principal_query = manual_prior_principal_query.filter(~FinManualAdjustment.counterparty.in_(excluded_payer_list))
        if contract_list:
            manual_prior_principal_query = manual_prior_principal_query.filter(
                or_(
                    FinManualAdjustment.contract_number.in_(contract_list),
                    FinContract.contract_number.in_(contract_list)
                )
            )

        manual_prior_principal_map = {
            row.contract: float(row.amount or 0)
            for row in manual_prior_principal_query.all()
            if row.contract
        }

    # Get expenses grouped by contract
    query = db.query(
        FinContract.id.label("contract_id"),
        FinContract.contract_number,
        Organization.name.label("organization"),
        func.coalesce(FinExpense.recipient, '').label("payer"),
        func.sum(FinExpense.amount).label("total_paid"),
        func.count(FinExpense.id).label("operations_count"),
        func.max(FinExpense.document_date).label("last_payment")
    ).join(
        FinExpense, FinExpense.contract_id == FinContract.id
    ).outerjoin(
        Organization, FinExpense.organization_id == Organization.id
    ).group_by(
        FinContract.id, FinContract.contract_number, Organization.name, FinExpense.recipient
    )

    if date_from:
        query = query.filter(FinExpense.document_date >= date_from)
    if date_to:
        query = query.filter(FinExpense.document_date <= date_to)
    if org_ids:
        query = query.filter(FinExpense.organization_id.in_(org_ids))
    if search:
        query = query.filter(FinContract.contract_number.ilike(f"%{search}%"))
    if payer_list:
        query = query.filter(FinExpense.recipient.in_(payer_list))
    if excluded_payer_list:
        query = query.filter(~FinExpense.recipient.in_(excluded_payer_list))
    if contract_list:
        query = query.filter(FinContract.contract_number.in_(contract_list))

    # Get total count
    count_query = query.subquery()
    total = db.query(func.count()).select_from(count_query).scalar() or 0

    # Apply pagination
    query = query.order_by(func.sum(FinExpense.amount).desc())
    skip = (page - 1) * limit
    rows = query.offset(skip).limit(limit).all()

    # Get real principal/interest by contract from FinExpenseDetail
    contract_payments = get_principal_interest_by_contract(
        db,
        date_from,
        date_to,
        org_ids if org_ids else None,
        payer_list if payer_list else None,
        excluded_payer_list if excluded_payer_list else None,
        contract_list if contract_list else None,
    )

    # Manual adjustments for period grouped by contract
    manual_expenses_query = db.query(
        manual_contract_expr.label("contract"),
        func.coalesce(
            func.sum(
                case(
                    (FinManualAdjustment.payment_type.ilike('%погашение долга%'), FinManualAdjustment.amount),
                    else_=0
                )
            ), 0
        ).label("principal"),
        func.coalesce(
            func.sum(
                case(
                    (FinManualAdjustment.payment_type.ilike('%уплата процентов%'), FinManualAdjustment.amount),
                    else_=0
                )
            ), 0
        ).label("interest"),
        func.count().label("count")
    ).outerjoin(
        FinContract, FinManualAdjustment.contract_id == FinContract.id
    ).filter(
        manual_contract_expr.isnot(None),
        FinManualAdjustment.adjustment_type == 'expense'
    ).group_by(manual_contract_expr)

    if date_from:
        manual_expenses_query = manual_expenses_query.filter(FinManualAdjustment.document_date >= date_from)
    if date_to:
        manual_expenses_query = manual_expenses_query.filter(FinManualAdjustment.document_date <= date_to)
    if org_ids:
        manual_expenses_query = manual_expenses_query.filter(FinManualAdjustment.organization_id.in_(org_ids))
    if payer_list:
        manual_expenses_query = manual_expenses_query.filter(FinManualAdjustment.counterparty.in_(payer_list))
    if excluded_payer_list:
        manual_expenses_query = manual_expenses_query.filter(~FinManualAdjustment.counterparty.in_(excluded_payer_list))
    if contract_list:
        manual_expenses_query = manual_expenses_query.filter(
            or_(
                FinManualAdjustment.contract_number.in_(contract_list),
                FinContract.contract_number.in_(contract_list)
            )
        )

    manual_principal_map = {}
    manual_interest_map = {}
    manual_expense_count_map = {}
    for row in manual_expenses_query.all():
        if not row.contract:
            continue
        manual_principal_map[row.contract] = float(row.principal or 0)
        manual_interest_map[row.contract] = float(row.interest or 0)
        manual_expense_count_map[row.contract] = int(row.count or 0)

    data = []
    for row in rows:
        contract_num = row.contract_number or ""
        contract_id = int(row.contract_id) if row.contract_id else 0

        total_paid = float(row.total_paid or 0)

        # Real principal and interest from details + manual adjustments
        principal, interest = contract_payments.get(contract_num, (0, 0))
        manual_principal = manual_principal_map.get(contract_num, 0.0)
        manual_interest = manual_interest_map.get(contract_num, 0.0)
        principal_total = principal + manual_principal
        interest_total = interest + manual_interest

        receipt_info = receipts_map.get(contract_num)
        received = receipt_info["received"] if receipt_info else 0.0
        manual_received = manual_receipts_map.get(contract_num, 0.0)
        received_total = received + manual_received

        first_receipt = receipt_info["first_receipt"] if receipt_info else None

        # Opening balance if period is limited
        opening_balance = 0.0
        if date_from:
            opening_receipts = prior_receipts_map.get(contract_num, 0.0) + manual_prior_receipts_map.get(contract_num, 0.0)
            opening_principal = prior_principal_map.get(contract_num, 0.0) + manual_prior_principal_map.get(contract_num, 0.0)
            opening_balance = opening_receipts - opening_principal

        balance = opening_balance + received_total - principal_total
        paid_percent = (principal_total / received_total * 100) if received_total > 0 else 0

        # Include manual expense adjustments into totals/operations count
        total_paid_with_manual = total_paid + manual_principal + manual_interest
        operations_count = (row.operations_count or 0) + manual_expense_count_map.get(contract_num, 0)

        data.append(FinContractsSummaryRecord(
            contractId=contract_id,
            contractNumber=contract_num,
            organization=row.organization or "Не указано",
            payer=row.payer or "",
            totalPaid=total_paid_with_manual,
            principal=principal_total,
            interest=interest_total,
            totalReceived=received_total,
            balance=balance,
            paidPercent=round(paid_percent, 2),
            operationsCount=operations_count,
            lastPayment=row.last_payment.isoformat() if row.last_payment else None,
            firstReceipt=first_receipt,
        ))

    pages = (total + limit - 1) // limit if limit > 0 else 1

    return FinContractsSummaryResponse(
        data=data,
        pagination=FinContractsSummaryPagination(
            page=page,
            limit=limit,
            total=total,
            pages=pages,
        )
    )


# === Payments by Date (for Calendar) ===

@router.get("/payments-by-date")
def get_payments_by_date(
    date_from: date = Query(..., description="Start date"),
    date_to: date = Query(..., description="End date"),
    organizations: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get payments grouped by date for calendar view.
    """
    # Parse organization filter by name
    org_ids = []
    if organizations:
        org_list = [o.strip() for o in organizations.split(",") if o.strip()]
        if org_list:
            org_ids = [o[0] for o in db.query(Organization.id).filter(Organization.name.in_(org_list)).all()]

    # Get expenses grouped by date
    query = db.query(
        FinExpense.document_date.label("date"),
        func.count(FinExpense.id).label("count"),
        func.sum(FinExpense.amount).label("total")
    ).filter(
        FinExpense.document_date >= date_from,
        FinExpense.document_date <= date_to,
        FinExpense.document_date.isnot(None)
    ).group_by(
        FinExpense.document_date
    ).order_by(
        FinExpense.document_date
    )

    if org_ids:
        query = query.filter(FinExpense.organization_id.in_(org_ids))

    result = []
    for row in query.all():
        # Get individual expenses for this date
        expenses_query = db.query(FinExpense).filter(
            FinExpense.document_date == row.date
        )
        if org_ids:
            expenses_query = expenses_query.filter(FinExpense.organization_id.in_(org_ids))

        expenses = []
        for exp in expenses_query.limit(10).all():  # Limit to 10 per date
            expenses.append({
                "id": exp.id,
                "document_date": exp.document_date.isoformat() if exp.document_date else None,
                "amount": float(exp.amount or 0),
                "organization": exp.org.name if exp.org else None,
                "contract_number": exp.contract.contract_number if exp.contract else None,
            })

        result.append({
            "date": row.date.isoformat() if row.date else None,
            "count": row.count,
            "total": float(row.total or 0),
            "expenses": expenses,
        })

    return result


# === Contract Operations (for Contract Details Page) ===

@router.get("/contract-operations/{contract_number}")
def get_contract_operations(
    contract_number: str,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all operations (receipts and expenses) for a specific contract.
    Calculates opening balance, principal paid, interest paid, and closing balance.
    """
    from urllib.parse import unquote
    from app.modules.fin.models import FinExpenseDetail

    # Decode contract number
    decoded_contract = unquote(contract_number)

    def classify_payment(payment_type: Optional[str]) -> str:
        """Map payment type to principal/interest buckets."""
        if not payment_type:
            return "other"
        pt = payment_type.lower()
        if 'процент' in pt:
            return "interest"
        if 'долг' in pt:
            return "principal"
        return "other"

    # Find contract
    contract = db.query(FinContract).filter(
        FinContract.contract_number == decoded_contract
    ).first()

    if not contract:
        # Try partial match
        contract = db.query(FinContract).filter(
            FinContract.contract_number.ilike(f"%{decoded_contract}%")
        ).first()

    # Get organization from contract or first related expense
    organization_name = None
    if contract:
        # Get from first expense
        first_expense = db.query(FinExpense).filter(
            FinExpense.contract_id == contract.id
        ).first()
        if first_expense and first_expense.org:
            organization_name = first_expense.org.name

    # Get receipts for this contract (using contract_id, not contract_number)
    receipts_query = db.query(FinReceipt)
    if contract:
        receipts_query = receipts_query.filter(FinReceipt.contract_id == contract.id)
    else:
        # If no contract found, return empty list for receipts
        receipts_query = receipts_query.filter(FinReceipt.id == -1)  # No match

    if date_from:
        receipts_query = receipts_query.filter(FinReceipt.document_date >= date_from)
    if date_to:
        receipts_query = receipts_query.filter(FinReceipt.document_date <= date_to)

    receipts = receipts_query.order_by(FinReceipt.document_date.desc()).all()

    # Get expenses for this contract
    expenses_query = db.query(FinExpense)
    if contract:
        expenses_query = expenses_query.filter(FinExpense.contract_id == contract.id)
    else:
        # If no contract found, return empty list
        expenses_query = expenses_query.filter(FinExpense.id == -1)  # No match

    if date_from:
        expenses_query = expenses_query.filter(FinExpense.document_date >= date_from)
    if date_to:
        expenses_query = expenses_query.filter(FinExpense.document_date <= date_to)

    expenses = expenses_query.order_by(FinExpense.document_date.desc()).all()

    # Manual adjustments for this contract (by id or number)
    manual_query = db.query(FinManualAdjustment)
    if contract:
        manual_query = manual_query.filter(FinManualAdjustment.contract_id == contract.id)
    else:
        manual_query = manual_query.filter(FinManualAdjustment.contract_number == decoded_contract)

    if date_from:
        manual_query = manual_query.filter(FinManualAdjustment.document_date >= date_from)
    if date_to:
        manual_query = manual_query.filter(FinManualAdjustment.document_date <= date_to)

    manual_adjustments = manual_query.order_by(FinManualAdjustment.document_date.desc()).all()

    manual_receipts_sum = 0.0
    manual_principal_sum = 0.0
    manual_interest_sum = 0.0
    for adj in manual_adjustments:
        amount = float(adj.amount or 0)
        if adj.adjustment_type == 'receipt':
            manual_receipts_sum += amount
        else:
            bucket = classify_payment(adj.payment_type)
            if bucket == "principal":
                manual_principal_sum += amount
            elif bucket == "interest":
                manual_interest_sum += amount

    # Get expense operation IDs for detail lookup
    expense_operation_ids = [e.operation_id for e in expenses]

    # Get expense details for calculating principal and interest
    # Filter by contract_number in FinExpenseDetail for accurate calculation
    details_query = db.query(FinExpenseDetail).filter(
        FinExpenseDetail.expense_operation_id.in_(expense_operation_ids)
    )
    # Filter details by contract_number to get only payments for this contract
    details_query = details_query.filter(FinExpenseDetail.contract_number == decoded_contract)
    details = details_query.all() if expense_operation_ids else []

    # Calculate principal and interest from details
    total_principal = 0.0
    total_interest = 0.0
    for detail in details:
        amount = float(detail.payment_amount or 0)
        if detail.payment_type and 'долг' in detail.payment_type.lower():
            total_principal += amount
        elif detail.payment_type and 'процент' in detail.payment_type.lower():
            total_interest += amount

    # Calculate totals
    total_received = sum(float(r.amount or 0) for r in receipts) + manual_receipts_sum
    total_principal += manual_principal_sum
    total_interest += manual_interest_sum
    # Total paid is sum of principal + interest for this specific contract
    total_paid = total_principal + total_interest

    # Calculate opening balance (all operations before date_from)
    opening_balance = 0.0
    if date_from:
        # Prior receipts using contract_id
        prior_receipts = 0.0
        if contract:
            prior_receipts = db.query(func.sum(FinReceipt.amount)).filter(
                FinReceipt.contract_id == contract.id,
                FinReceipt.document_date < date_from
            ).scalar() or 0

        # Prior principal payments
        prior_principal = 0.0
        if contract:
            prior_expense_ops = db.query(FinExpense.operation_id).filter(
                FinExpense.contract_id == contract.id,
                FinExpense.document_date < date_from
            ).all()
            prior_op_ids = [op[0] for op in prior_expense_ops]

            prior_principal = db.query(func.sum(FinExpenseDetail.payment_amount)).filter(
                FinExpenseDetail.expense_operation_id.in_(prior_op_ids),
                FinExpenseDetail.payment_type.ilike('%погашение долга%'),
                FinExpenseDetail.contract_number == decoded_contract
            ).scalar() or 0 if prior_op_ids else 0

        prior_manual_receipts = db.query(func.sum(FinManualAdjustment.amount)).filter(
            (FinManualAdjustment.contract_id == contract.id) if contract else (FinManualAdjustment.contract_number == decoded_contract),
            FinManualAdjustment.adjustment_type == 'receipt',
            FinManualAdjustment.document_date < date_from
        ).scalar() or 0

        prior_manual_principal = db.query(func.sum(FinManualAdjustment.amount)).filter(
            (FinManualAdjustment.contract_id == contract.id) if contract else (FinManualAdjustment.contract_number == decoded_contract),
            FinManualAdjustment.adjustment_type == 'expense',
            FinManualAdjustment.payment_type.ilike('%погашение долга%'),
            FinManualAdjustment.document_date < date_from
        ).scalar() or 0

        opening_balance = float(prior_receipts) + float(prior_manual_receipts) - float(prior_principal) - float(prior_manual_principal)

    # Closing balance = opening + received - principal paid
    closing_balance = opening_balance + total_received - total_principal

    # Build operations list (combine receipts and expenses, sorted by date)
    operations = []

    for receipt in receipts:
        operations.append({
            "id": receipt.id,
            "type": "receipt",
            "operation_id": receipt.operation_id,
            "document_date": receipt.document_date.isoformat() if receipt.document_date else None,
            "document_number": receipt.document_number,
            "amount": float(receipt.amount or 0),
            "principal": 0,
            "interest": 0,
            "payer": receipt.payer,
            "payment_purpose": receipt.payment_purpose,
            "organization": receipt.org.name if receipt.org else None,
        })

    for adj in manual_adjustments:
        adj_amount = float(adj.amount or 0)
        bucket = classify_payment(adj.payment_type)
        is_receipt = adj.adjustment_type == 'receipt'

        operations.append({
            "id": -adj.id,
            "type": "receipt" if is_receipt else "expense",
            "operation_id": None,
            "document_date": adj.document_date.isoformat() if adj.document_date else None,
            "document_number": adj.document_number,
            "amount": adj_amount,
            "principal": adj_amount if (not is_receipt and bucket == "principal") else 0,
            "interest": adj_amount if (not is_receipt and bucket == "interest") else 0,
            "payer": adj.counterparty if is_receipt else None,
            "recipient": None if is_receipt else adj.counterparty,
            "payment_purpose": adj.description or adj.comment or "Корректировка",
            "organization": organization_name,
        })

    for expense in expenses:
        # Get details for this expense (already filtered by contract_number)
        exp_details = [d for d in details if d.expense_operation_id == expense.operation_id]

        # Only include expense if it has details for this contract
        if not exp_details:
            continue

        exp_principal = sum(
            float(d.payment_amount or 0)
            for d in exp_details
            if d.payment_type and 'долг' in d.payment_type.lower()
        )
        exp_interest = sum(
            float(d.payment_amount or 0)
            for d in exp_details
            if d.payment_type and 'процент' in d.payment_type.lower()
        )

        # Use the sum of detail amounts as the operation amount for this contract
        exp_amount = exp_principal + exp_interest

        operations.append({
            "id": expense.id,
            "type": "expense",
            "operation_id": expense.operation_id,
            "document_date": expense.document_date.isoformat() if expense.document_date else None,
            "document_number": expense.document_number,
            "amount": exp_amount,  # Amount specific to this contract
            "principal": exp_principal,
            "interest": exp_interest,
            "recipient": expense.recipient,
            "payment_purpose": expense.payment_purpose,
            "organization": expense.org.name if expense.org else None,
        })

    # Sort by date (newest first)
    operations.sort(key=lambda x: x["document_date"] or "", reverse=True)

    # Calculate actual counts after filtering
    receipts_in_operations = len([op for op in operations if op["type"] == "receipt"])
    expenses_in_operations = len([op for op in operations if op["type"] == "expense"])

    return {
        "contract_number": decoded_contract,
        "organization": organization_name,
        "summary": {
            "opening_balance": opening_balance,
            "total_received": total_received,
            "total_paid": total_paid,
            "principal_paid": total_principal,
            "interest_paid": total_interest,
            "closing_balance": closing_balance,
        },
        "statistics": {
            "receipts_count": receipts_in_operations,
            "expenses_count": expenses_in_operations,
            "total_operations": len(operations),
        },
        "operations": operations,
    }


@router.get("/contract-operations-by-id")
def get_contract_operations_by_id(
    contract_id: int = Query(..., description="Contract ID"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all operations (receipts and expenses) for a specific contract by ID.
    This is an alternative to get_contract_operations that avoids URL encoding issues
    with contract numbers containing special characters like slashes.
    """
    from app.modules.fin.models import FinExpenseDetail

    # Find contract by ID
    contract = db.query(FinContract).filter(FinContract.id == contract_id).first()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    decoded_contract = contract.contract_number

    def classify_payment(payment_type: Optional[str]) -> str:
        """Map payment_type text to principal/interest/other bucket."""
        if not payment_type:
            return "other"
        pt = payment_type.lower()
        if 'процент' in pt:
            return "interest"
        if 'долг' in pt:
            return "principal"
        return "other"

    # Get organization from contract or first related expense
    organization_name = None
    # Get from first expense
    first_expense = db.query(FinExpense).filter(
        FinExpense.contract_id == contract.id
    ).first()
    if first_expense and first_expense.org:
        organization_name = first_expense.org.name

    # Get receipts for this contract
    receipts_query = db.query(FinReceipt).filter(FinReceipt.contract_id == contract.id)
    if date_from:
        receipts_query = receipts_query.filter(FinReceipt.document_date >= date_from)
    if date_to:
        receipts_query = receipts_query.filter(FinReceipt.document_date <= date_to)
    receipts = receipts_query.order_by(FinReceipt.document_date.desc()).all()

    # Get expenses for this contract
    expenses_query = db.query(FinExpense).filter(FinExpense.contract_id == contract.id)
    if date_from:
        expenses_query = expenses_query.filter(FinExpense.document_date >= date_from)
    if date_to:
        expenses_query = expenses_query.filter(FinExpense.document_date <= date_to)
    expenses = expenses_query.order_by(FinExpense.document_date.desc()).all()

    # Manual adjustments for this contract
    manual_query = db.query(FinManualAdjustment).filter(FinManualAdjustment.contract_id == contract.id)
    if date_from:
        manual_query = manual_query.filter(FinManualAdjustment.document_date >= date_from)
    if date_to:
        manual_query = manual_query.filter(FinManualAdjustment.document_date <= date_to)
    manual_adjustments = manual_query.order_by(FinManualAdjustment.document_date.desc()).all()

    manual_receipts_sum = 0.0
    manual_principal_sum = 0.0
    manual_interest_sum = 0.0

    for adj in manual_adjustments:
        amount = float(adj.amount or 0)
        if adj.adjustment_type == 'receipt':
            manual_receipts_sum += amount
        else:
            bucket = classify_payment(adj.payment_type)
            if bucket == "principal":
                manual_principal_sum += amount
            elif bucket == "interest":
                manual_interest_sum += amount

    # Get expense operation IDs for detail lookup
    expense_operation_ids = [e.operation_id for e in expenses]

    # Get expense details for calculating principal and interest
    details_query = db.query(FinExpenseDetail).filter(
        FinExpenseDetail.expense_operation_id.in_(expense_operation_ids),
        FinExpenseDetail.contract_number == decoded_contract
    )
    details = details_query.all() if expense_operation_ids else []

    # Calculate principal and interest from details
    total_principal = 0.0
    total_interest = 0.0
    for detail in details:
        amount = float(detail.payment_amount or 0)
        if detail.payment_type and 'долга' in detail.payment_type.lower():
            total_principal += amount
        elif detail.payment_type and 'процент' in detail.payment_type.lower():
            total_interest += amount

    # Calculate totals
    total_received = sum(float(r.amount or 0) for r in receipts) + manual_receipts_sum
    total_principal += manual_principal_sum
    total_interest += manual_interest_sum
    total_paid = total_principal + total_interest

    # Opening balance calculation
    receipts_before = 0.0
    principal_before = 0.0
    manual_principal_before = 0.0
    manual_receipts_before = 0.0

    if date_from:
        receipts_before_query = db.query(func.sum(FinReceipt.amount)).filter(
            FinReceipt.contract_id == contract.id,
            FinReceipt.document_date < date_from
        )
        receipts_before = receipts_before_query.scalar() or 0

        details_before_query = db.query(
            func.sum(FinExpenseDetail.payment_amount)
        ).join(
            FinExpense, FinExpenseDetail.expense_operation_id == FinExpense.operation_id
        ).filter(
            FinExpense.contract_id == contract.id,
            FinExpenseDetail.contract_number == decoded_contract,
            FinExpenseDetail.payment_type.ilike('%погашение долга%'),
            FinExpense.document_date < date_from
        )
        principal_before = details_before_query.scalar() or 0

        manual_before_query = db.query(func.sum(FinManualAdjustment.amount)).filter(
            FinManualAdjustment.contract_id == contract.id,
            FinManualAdjustment.adjustment_type == 'expense',
            FinManualAdjustment.payment_type.ilike('%погашение долга%'),
            FinManualAdjustment.document_date < date_from
        )
        manual_principal_before = manual_before_query.scalar() or 0

        manual_receipts_before = db.query(func.sum(FinManualAdjustment.amount)).filter(
            FinManualAdjustment.contract_id == contract.id,
            FinManualAdjustment.adjustment_type == 'receipt',
            FinManualAdjustment.document_date < date_from
        ).scalar() or 0

    opening_balance = float(receipts_before) + float(manual_receipts_before) - float(principal_before) - float(manual_principal_before)
    closing_balance = opening_balance + total_received - total_principal

    # Combine receipts and expenses into operations list
    operations = []
    for receipt in receipts:
        operations.append({
            "id": receipt.id,
            "type": "receipt",
            "document_date": receipt.document_date.isoformat() if receipt.document_date else None,
            "document_number": receipt.document_number,
            "counterparty": receipt.payer,
            "payer": receipt.payer,
            "amount": float(receipt.amount or 0),
            "payment_purpose": receipt.payment_purpose,
            "organization": receipt.org.name if receipt.org else None,
        })

    for adj in manual_adjustments:
        adj_amount = float(adj.amount or 0)
        payment_bucket = classify_payment(adj.payment_type)
        is_receipt = adj.adjustment_type == 'receipt'

        operations.append({
            "id": -adj.id,  # keep unique and non-conflicting with DB ids
            "type": "receipt" if is_receipt else "expense",
            "document_date": adj.document_date.isoformat() if adj.document_date else None,
            "document_number": adj.document_number,
            "counterparty": adj.counterparty,
            "payer": adj.counterparty if is_receipt else None,
            "recipient": None if is_receipt else adj.counterparty,
            "amount": adj_amount,
            "principal": adj_amount if (not is_receipt and payment_bucket == "principal") else 0,
            "interest": adj_amount if (not is_receipt and payment_bucket == "interest") else 0,
            "payment_purpose": adj.description or adj.comment or "Корректировка",
            "organization": organization_name,
        })

    for expense in expenses:
        exp_details = [d for d in details if d.expense_operation_id == expense.operation_id]
        exp_principal = sum(
            float(d.payment_amount or 0)
            for d in exp_details
            if d.payment_type and 'долг' in d.payment_type.lower()
        )
        exp_interest = sum(
            float(d.payment_amount or 0)
            for d in exp_details
            if d.payment_type and 'процент' in d.payment_type.lower()
        )
        exp_amount = exp_principal + exp_interest if exp_details else float(expense.amount or 0)

        operations.append({
            "id": expense.id,
            "type": "expense",
            "document_date": expense.document_date.isoformat() if expense.document_date else None,
            "document_number": expense.document_number,
            "counterparty": expense.recipient,
            "recipient": expense.recipient,
            "amount": exp_amount,
            "principal": exp_principal,
            "interest": exp_interest,
            "payment_purpose": expense.payment_purpose,
            "organization": expense.org.name if expense.org else None,
        })

    # Sort by date (newest first)
    operations.sort(key=lambda x: x["document_date"] or "", reverse=True)

    # Calculate actual counts after filtering
    receipts_in_operations = len([op for op in operations if op["type"] == "receipt"])
    expenses_in_operations = len([op for op in operations if op["type"] == "expense"])

    return {
        "contract_number": decoded_contract,
        "organization": organization_name,
        "summary": {
            "opening_balance": opening_balance,
            "total_received": total_received,
            "total_paid": total_paid,
            "principal_paid": total_principal,
            "interest_paid": total_interest,
            "closing_balance": closing_balance,
        },
        "statistics": {
            "receipts_count": receipts_in_operations,
            "expenses_count": expenses_in_operations,
            "total_operations": len(operations),
        },
        "operations": operations,
    }
