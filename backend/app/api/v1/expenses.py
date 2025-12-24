"""Expenses API endpoints."""
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

logger = logging.getLogger(__name__)

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

@router.get("/", response_model=ExpenseList)
def get_expenses(
    skip: int = 0,
    limit: int = 50,
    status: Optional[ExpenseStatusEnum] = None,
    priority: Optional[ExpensePriorityEnum] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    contractor_id: Optional[int] = None,
    subdivision: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get expenses with filters and pagination."""
    base_query = db.query(Expense).filter(Expense.is_active == True)

    # Filters
    if status:
        base_query = base_query.filter(Expense.status == status)
    if priority:
        base_query = base_query.filter(Expense.priority == priority)
    if date_from:
        base_query = base_query.filter(Expense.request_date >= date_from)
    if date_to:
        base_query = base_query.filter(Expense.request_date <= date_to)
    if category_id:
        base_query = base_query.filter(Expense.category_id == category_id)
    if organization_id:
        base_query = base_query.filter(Expense.organization_id == organization_id)
    if contractor_id:
        base_query = base_query.filter(Expense.contractor_id == contractor_id)
    if subdivision:
        base_query = base_query.filter(Expense.subdivision == subdivision)

    # Search (включая новые поля comment и requester)
    if search:
        search_term = f"%{search}%"
        base_query = base_query.filter(
            or_(
                Expense.number.ilike(search_term),
                Expense.title.ilike(search_term),
                Expense.contractor_name.ilike(search_term),
                Expense.contractor_inn.ilike(search_term),
                Expense.payment_purpose.ilike(search_term),
                Expense.comment.ilike(search_term),
                Expense.requester.ilike(search_term)
            )
        )

    # Get total count
    total = base_query.count()

    # Order and paginate with eager loading
    query = base_query.options(
        joinedload(Expense.category_rel),
        joinedload(Expense.organization_rel),
        joinedload(Expense.contractor_rel),
        joinedload(Expense.requested_by_rel),
        joinedload(Expense.approved_by_rel)
    ).order_by(
        Expense.request_date.desc(),
        Expense.id.desc()
    ).offset(skip).limit(limit)

    expenses = query.all()

    # Build response with related data
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

    # Calculate pagination info
    page = (skip // limit) + 1 if limit > 0 else 1
    pages = (total + limit - 1) // limit if limit > 0 else 1

    return ExpenseList(
        total=total,
        items=result,
        page=page,
        page_size=limit,
        pages=pages
    )


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
    """Delete expense permanently."""
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

    # Permanently delete from database
    db.delete(expense)
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


# ==================== Additional Endpoints ====================

@router.patch("/{expense_id}/status", response_model=ExpenseResponse)
def update_expense_status(
    expense_id: int,
    new_status: ExpenseStatusEnum,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update expense status."""
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.is_active == True
    ).first()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    # Validate status transition
    if new_status == ExpenseStatusEnum.PAID and expense.amount_paid < expense.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot mark as PAID: expense not fully paid"
        )

    expense.status = new_status
    expense.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(expense)

    return expense


@router.get("/export")
def export_expenses(
    status: Optional[ExpenseStatusEnum] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    category_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    contractor_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Export expenses to Excel."""
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Excel export requires openpyxl library"
        )

    # Build query with same filters as GET /
    query = db.query(Expense).filter(Expense.is_active == True)

    if status:
        query = query.filter(Expense.status == status)
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

    expenses = query.options(
        joinedload(Expense.category_rel),
        joinedload(Expense.organization_rel),
        joinedload(Expense.contractor_rel)
    ).order_by(Expense.request_date.desc()).all()

    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Заявки на расход"

    # Headers
    headers = [
        "№", "Номер", "Название", "Сумма", "Дата заявки", "Срок оплаты",
        "Дата платежа", "Статус", "Категория", "Организация", "Контрагент",
        "Заявитель", "Комментарий", "Оплачено", "Импорт из 1С"
    ]
    ws.append(headers)

    # Style headers
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    # Data rows
    for idx, exp in enumerate(expenses, start=1):
        ws.append([
            idx,
            exp.number or "",
            exp.title or "",
            float(exp.amount) if exp.amount else 0,
            exp.request_date.isoformat() if exp.request_date else "",
            exp.due_date.isoformat() if exp.due_date else "",
            exp.payment_date.isoformat() if exp.payment_date else "",
            exp.status.value if exp.status else "",
            exp.category_rel.name if exp.category_rel else "",
            exp.organization_rel.name if exp.organization_rel else "",
            exp.contractor_name or (exp.contractor_rel.name if exp.contractor_rel else ""),
            exp.requester or "",
            exp.comment or "",
            "Да" if exp.is_paid else "Нет",
            "Да" if exp.imported_from_1c else "Нет"
        ])

    # Auto-size columns
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width

    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"expenses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/bulk-delete")
def bulk_delete_expenses(
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    category_id: Optional[int] = Query(None),
    organization_id: Optional[int] = Query(None),
    contractor_id: Optional[int] = Query(None),
    subdivision: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Массовое удаление заявок по фильтру.
    ВАЖНО: Эта операция необратима! Данные будут удалены из базы данных навсегда.
    """
    logger.info(f"Bulk delete request - status: {status}, date_from: {date_from}, date_to: {date_to}, "
                f"category_id: {category_id}, org_id: {organization_id}, contractor_id: {contractor_id}, "
                f"subdivision: {subdivision}, search: {search}")

    status_filter = status

    query = db.query(Expense)

    # Применить все фильтры
    if status_filter:
        query = query.filter(Expense.status == status_filter)
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
    if subdivision:
        query = query.filter(Expense.subdivision == subdivision)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Expense.number.ilike(search_term),
                Expense.title.ilike(search_term),
                Expense.contractor_name.ilike(search_term),
                Expense.payment_purpose.ilike(search_term)
            )
        )

    # Подсчитать количество
    count = query.count()

    # Полностью удалить из базы данных
    query.delete(synchronize_session=False)
    db.commit()

    logger.info(f"Permanently deleted {count} expenses by user {current_user.id}")
    return {"message": f"Удалено заявок: {count}", "count": count}
