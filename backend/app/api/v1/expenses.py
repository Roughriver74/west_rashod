"""Expenses API endpoints."""
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from app.db.session import get_db
from app.db.models import (
    Expense, BankTransaction, BudgetCategory, Organization, Contractor,
    User, UserRoleEnum, ExpenseStatusEnum, ExpensePriorityEnum
)
from app.schemas.expense import (
    ExpenseCreate, ExpenseUpdate, ExpenseResponse,
    ExpenseStats, ExpenseList, ExpenseApproval,
    MatchingSuggestion
)
from app.utils.auth import get_current_active_user

router = APIRouter(prefix="/expenses", tags=["Expenses"])


def generate_expense_number(db: Session) -> str:
    """Generate unique expense number."""
    year = datetime.now().year
    prefix = f"EXP-{year}-"

    # Get max number for this year
    last_expense = db.query(Expense).filter(
        Expense.number.like(f"{prefix}%")
    ).order_by(Expense.id.desc()).first()

    if last_expense:
        try:
            last_num = int(last_expense.number.replace(prefix, ""))
            new_num = last_num + 1
        except ValueError:
            new_num = 1
    else:
        new_num = 1

    return f"{prefix}{new_num:05d}"


# ==================== List & Stats ====================

@router.get("/", response_model=List[ExpenseResponse])
def get_expenses(
    skip: int = 0,
    limit: int = 100,
    status: Optional[ExpenseStatusEnum] = None,
    priority: Optional[ExpensePriorityEnum] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    contractor_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get expenses with filters."""
    query = db.query(Expense).options(
        joinedload(Expense.category_rel),
        joinedload(Expense.organization_rel),
        joinedload(Expense.contractor_rel),
        joinedload(Expense.requested_by_rel),
        joinedload(Expense.approved_by_rel)
    ).filter(Expense.is_active == True)

    if status:
        query = query.filter(Expense.status == status)
    if priority:
        query = query.filter(Expense.priority == priority)
    if date_from:
        query = query.filter(Expense.request_date >= date_from)
    if date_to:
        query = query.filter(Expense.request_date <= date_to)
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    if organization_id:
        query = query.filter(Expense.organization_id == organization_id)
    if contractor_id:
        query = query.filter(Expense.contractor_id == contractor_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Expense.number.ilike(search_term),
                Expense.title.ilike(search_term),
                Expense.contractor_name.ilike(search_term),
                Expense.contractor_inn.ilike(search_term),
                Expense.payment_purpose.ilike(search_term)
            )
        )

    expenses = query.order_by(
        Expense.request_date.desc(),
        Expense.id.desc()
    ).offset(skip).limit(limit).all()

    result = []
    for exp in expenses:
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

        result.append(ExpenseResponse(**exp_dict))

    return result


@router.get("/stats", response_model=ExpenseStats)
def get_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get expense statistics."""
    query = db.query(Expense).filter(Expense.is_active == True)

    if date_from:
        query = query.filter(Expense.request_date >= date_from)
    if date_to:
        query = query.filter(Expense.request_date <= date_to)

    total = query.count()

    status_counts = {}
    for status_enum in ExpenseStatusEnum:
        status_counts[status_enum.value] = query.filter(
            Expense.status == status_enum
        ).count()

    # Calculate totals
    total_amount = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
        Expense.is_active == True
    ).scalar() or Decimal("0")

    total_paid = db.query(func.coalesce(func.sum(Expense.amount_paid), 0)).filter(
        Expense.is_active == True
    ).scalar() or Decimal("0")

    pending_amount = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
        Expense.is_active == True,
        Expense.status.in_([ExpenseStatusEnum.PENDING, ExpenseStatusEnum.APPROVED])
    ).scalar() or Decimal("0")

    return ExpenseStats(
        total=total,
        draft=status_counts.get(ExpenseStatusEnum.DRAFT.value, 0),
        pending=status_counts.get(ExpenseStatusEnum.PENDING.value, 0),
        approved=status_counts.get(ExpenseStatusEnum.APPROVED.value, 0),
        rejected=status_counts.get(ExpenseStatusEnum.REJECTED.value, 0),
        paid=status_counts.get(ExpenseStatusEnum.PAID.value, 0),
        partially_paid=status_counts.get(ExpenseStatusEnum.PARTIALLY_PAID.value, 0),
        cancelled=status_counts.get(ExpenseStatusEnum.CANCELLED.value, 0),
        total_amount=total_amount,
        total_paid=total_paid,
        total_pending=pending_amount
    )


# ==================== CRUD ====================

@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    expense_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get single expense."""
    expense = db.query(Expense).options(
        joinedload(Expense.category_rel),
        joinedload(Expense.organization_rel),
        joinedload(Expense.contractor_rel),
        joinedload(Expense.requested_by_rel),
        joinedload(Expense.approved_by_rel)
    ).filter(
        Expense.id == expense_id,
        Expense.is_active == True
    ).first()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    # Calculate linked transactions
    linked = db.query(
        func.count(BankTransaction.id),
        func.coalesce(func.sum(BankTransaction.amount), 0)
    ).filter(
        BankTransaction.expense_id == expense.id,
        BankTransaction.is_active == True
    ).first()

    exp_dict = ExpenseResponse.model_validate(expense).model_dump()
    exp_dict['category_name'] = expense.category_rel.name if expense.category_rel else None
    exp_dict['organization_name'] = expense.organization_rel.name if expense.organization_rel else None
    exp_dict['requested_by_name'] = expense.requested_by_rel.full_name if expense.requested_by_rel else None
    exp_dict['approved_by_name'] = expense.approved_by_rel.full_name if expense.approved_by_rel else None
    exp_dict['remaining_amount'] = expense.amount - expense.amount_paid
    exp_dict['linked_transactions_count'] = linked[0] or 0
    exp_dict['linked_transactions_amount'] = linked[1] or Decimal("0")

    return ExpenseResponse(**exp_dict)


@router.post("/", response_model=ExpenseResponse)
def create_expense(
    expense_data: ExpenseCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new expense."""
    expense_dict = expense_data.model_dump()
    expense_dict['number'] = generate_expense_number(db)
    expense_dict['requested_by'] = current_user.id

    expense = Expense(**expense_dict)
    db.add(expense)
    db.commit()
    db.refresh(expense)

    return expense


@router.put("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: int,
    expense_update: ExpenseUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update expense."""
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.is_active == True
    ).first()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    # Only allow updates if not paid
    if expense.status in [ExpenseStatusEnum.PAID]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update paid expense"
        )

    update_data = expense_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(expense, field, value)

    db.commit()
    db.refresh(expense)

    return expense


@router.delete("/{expense_id}")
def delete_expense(
    expense_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Soft delete expense."""
    expense = db.query(Expense).filter(
        Expense.id == expense_id
    ).first()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    # Check permissions
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        if expense.requested_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete expense created by another user"
            )

    expense.is_active = False
    db.commit()

    return {"message": "Expense deleted"}


# ==================== Approval Workflow ====================

@router.post("/{expense_id}/submit")
def submit_for_approval(
    expense_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Submit expense for approval."""
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.is_active == True
    ).first()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    if expense.status != ExpenseStatusEnum.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft expenses can be submitted"
        )

    expense.status = ExpenseStatusEnum.PENDING
    db.commit()

    return {"message": "Expense submitted for approval"}


@router.post("/{expense_id}/approve", response_model=ExpenseResponse)
def approve_expense(
    expense_id: int,
    approval_data: ExpenseApproval,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Approve or reject expense."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER, UserRoleEnum.FOUNDER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can approve expenses"
        )

    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.is_active == True
    ).first()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    if expense.status != ExpenseStatusEnum.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending expenses can be approved/rejected"
        )

    if approval_data.action == "approve":
        expense.status = ExpenseStatusEnum.APPROVED
        expense.approved_by = current_user.id
        expense.approved_at = datetime.utcnow()
    elif approval_data.action == "reject":
        expense.status = ExpenseStatusEnum.REJECTED
        expense.rejection_reason = approval_data.rejection_reason
        expense.approved_by = current_user.id
        expense.approved_at = datetime.utcnow()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Use 'approve' or 'reject'"
        )

    db.commit()
    db.refresh(expense)

    return expense


# ==================== Linked Transactions ====================

@router.get("/{expense_id}/transactions")
def get_linked_transactions(
    expense_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get transactions linked to expense."""
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.is_active == True
    ).first()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    transactions = db.query(BankTransaction).filter(
        BankTransaction.expense_id == expense_id,
        BankTransaction.is_active == True
    ).order_by(BankTransaction.transaction_date.desc()).all()

    return transactions


@router.post("/{expense_id}/unlink/{transaction_id}")
def unlink_transaction(
    expense_id: int,
    transaction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Unlink transaction from expense."""
    transaction = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id,
        BankTransaction.expense_id == expense_id,
        BankTransaction.is_active == True
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found or not linked to this expense"
        )

    # Unlink
    transaction.expense_id = None
    transaction.matching_score = None

    # Update expense paid amount
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if expense:
        expense.amount_paid = (expense.amount_paid or Decimal("0")) - transaction.amount
        if expense.amount_paid < 0:
            expense.amount_paid = Decimal("0")

        # Update status
        if expense.amount_paid >= expense.amount:
            expense.status = ExpenseStatusEnum.PAID
        elif expense.amount_paid > 0:
            expense.status = ExpenseStatusEnum.PARTIALLY_PAID
        elif expense.status in [ExpenseStatusEnum.PAID, ExpenseStatusEnum.PARTIALLY_PAID]:
            expense.status = ExpenseStatusEnum.APPROVED

    db.commit()

    return {"message": "Transaction unlinked"}
