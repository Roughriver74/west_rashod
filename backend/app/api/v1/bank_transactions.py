"""Bank transactions API endpoints - core module."""
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from app.db.session import get_db
from app.db.models import (
    BankTransaction, BudgetCategory, Organization, User, UserRoleEnum,
    BankTransactionTypeEnum, BankTransactionStatusEnum
)
from app.schemas.bank_transaction import (
    BankTransactionCreate, BankTransactionUpdate, BankTransactionResponse,
    BankTransactionCategorize, BankTransactionBulkCategorize,
    BankTransactionBulkStatusUpdate, BankTransactionStats,
    BankTransactionImportResult, BankTransactionImportPreview,
    CategorySuggestion
)
from app.utils.auth import get_current_active_user
from app.services.transaction_classifier import TransactionClassifier
from app.services.bank_transaction_import import BankTransactionImporter

router = APIRouter(prefix="/bank-transactions", tags=["Bank Transactions"])


# ==================== List & Stats ====================

@router.get("/", response_model=List[BankTransactionResponse])
def get_bank_transactions(
    skip: int = 0,
    limit: int = 100,
    department_id: Optional[int] = None,
    status: Optional[BankTransactionStatusEnum] = None,
    transaction_type: Optional[BankTransactionTypeEnum] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    only_unprocessed: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get bank transactions with filters."""
    query = db.query(BankTransaction).options(
        joinedload(BankTransaction.category_rel),
        joinedload(BankTransaction.organization_rel),
        joinedload(BankTransaction.suggested_category_rel)
    ).filter(BankTransaction.is_active == True)

    # Department filter
    if current_user.role == UserRoleEnum.USER:
        query = query.filter(BankTransaction.department_id == current_user.department_id)
    elif department_id:
        query = query.filter(BankTransaction.department_id == department_id)

    # Status filter
    if status:
        query = query.filter(BankTransaction.status == status)

    # Type filter
    if transaction_type:
        query = query.filter(BankTransaction.transaction_type == transaction_type)

    # Date range
    if date_from:
        query = query.filter(BankTransaction.transaction_date >= date_from)
    if date_to:
        query = query.filter(BankTransaction.transaction_date <= date_to)

    # Category filter
    if category_id:
        query = query.filter(BankTransaction.category_id == category_id)

    # Organization filter
    if organization_id:
        query = query.filter(BankTransaction.organization_id == organization_id)

    # Unprocessed only
    if only_unprocessed:
        query = query.filter(BankTransaction.status.in_([
            BankTransactionStatusEnum.NEW,
            BankTransactionStatusEnum.NEEDS_REVIEW
        ]))

    # Search
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                BankTransaction.counterparty_name.ilike(search_term),
                BankTransaction.counterparty_inn.ilike(search_term),
                BankTransaction.payment_purpose.ilike(search_term),
                BankTransaction.document_number.ilike(search_term)
            )
        )

    # Order and paginate
    transactions = query.order_by(
        BankTransaction.transaction_date.desc(),
        BankTransaction.id.desc()
    ).offset(skip).limit(limit).all()

    # Add related names
    result = []
    for t in transactions:
        t_dict = BankTransactionResponse.model_validate(t).model_dump()
        t_dict['category_name'] = t.category_rel.name if t.category_rel else None
        t_dict['organization_name'] = t.organization_rel.name if t.organization_rel else None
        t_dict['suggested_category_name'] = t.suggested_category_rel.name if t.suggested_category_rel else None
        result.append(BankTransactionResponse(**t_dict))

    return result


@router.get("/stats", response_model=BankTransactionStats)
def get_stats(
    department_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get transaction statistics."""
    query = db.query(BankTransaction).filter(BankTransaction.is_active == True)

    # Department filter
    if current_user.role == UserRoleEnum.USER:
        query = query.filter(BankTransaction.department_id == current_user.department_id)
    elif department_id:
        query = query.filter(BankTransaction.department_id == department_id)

    # Date range
    if date_from:
        query = query.filter(BankTransaction.transaction_date >= date_from)
    if date_to:
        query = query.filter(BankTransaction.transaction_date <= date_to)

    # Get counts by status
    total = query.count()
    new = query.filter(BankTransaction.status == BankTransactionStatusEnum.NEW).count()
    categorized = query.filter(BankTransaction.status == BankTransactionStatusEnum.CATEGORIZED).count()
    approved = query.filter(BankTransaction.status == BankTransactionStatusEnum.APPROVED).count()
    needs_review = query.filter(BankTransaction.status == BankTransactionStatusEnum.NEEDS_REVIEW).count()
    ignored = query.filter(BankTransaction.status == BankTransactionStatusEnum.IGNORED).count()

    # Get totals by type
    total_debit = db.query(func.coalesce(func.sum(BankTransaction.amount), 0)).filter(
        BankTransaction.is_active == True,
        BankTransaction.transaction_type == BankTransactionTypeEnum.DEBIT
    ).scalar() or Decimal("0")

    total_credit = db.query(func.coalesce(func.sum(BankTransaction.amount), 0)).filter(
        BankTransaction.is_active == True,
        BankTransaction.transaction_type == BankTransactionTypeEnum.CREDIT
    ).scalar() or Decimal("0")

    return BankTransactionStats(
        total=total,
        new=new,
        categorized=categorized,
        approved=approved,
        needs_review=needs_review,
        ignored=ignored,
        total_debit=total_debit,
        total_credit=total_credit
    )


# ==================== CRUD ====================

@router.get("/{transaction_id}", response_model=BankTransactionResponse)
def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get single transaction."""
    transaction = db.query(BankTransaction).options(
        joinedload(BankTransaction.category_rel),
        joinedload(BankTransaction.organization_rel),
        joinedload(BankTransaction.suggested_category_rel)
    ).filter(
        BankTransaction.id == transaction_id,
        BankTransaction.is_active == True
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    t_dict = BankTransactionResponse.model_validate(transaction).model_dump()
    t_dict['category_name'] = transaction.category_rel.name if transaction.category_rel else None
    t_dict['organization_name'] = transaction.organization_rel.name if transaction.organization_rel else None
    t_dict['suggested_category_name'] = transaction.suggested_category_rel.name if transaction.suggested_category_rel else None

    return BankTransactionResponse(**t_dict)


@router.post("/", response_model=BankTransactionResponse)
def create_transaction(
    transaction_data: BankTransactionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new transaction."""
    transaction = BankTransaction(**transaction_data.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction


@router.put("/{transaction_id}", response_model=BankTransactionResponse)
def update_transaction(
    transaction_id: int,
    transaction_update: BankTransactionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update transaction."""
    transaction = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id,
        BankTransaction.is_active == True
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    update_data = transaction_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transaction, field, value)

    db.commit()
    db.refresh(transaction)

    return transaction


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Soft delete transaction."""
    transaction = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    transaction.is_active = False
    db.commit()

    return {"message": "Transaction deleted"}


# ==================== Categorization ====================

@router.put("/{transaction_id}/categorize", response_model=BankTransactionResponse)
def categorize_transaction(
    transaction_id: int,
    categorize_data: BankTransactionCategorize,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Assign category to transaction."""
    transaction = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id,
        BankTransaction.is_active == True
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    # Verify category exists
    category = db.query(BudgetCategory).filter(
        BudgetCategory.id == categorize_data.category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found"
        )

    transaction.category_id = categorize_data.category_id
    transaction.status = BankTransactionStatusEnum.CATEGORIZED
    transaction.reviewed_by = current_user.id
    transaction.reviewed_at = datetime.utcnow()

    if categorize_data.notes:
        transaction.notes = categorize_data.notes

    db.commit()
    db.refresh(transaction)

    return transaction


@router.post("/bulk-categorize")
def bulk_categorize(
    bulk_data: BankTransactionBulkCategorize,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Bulk assign category to multiple transactions."""
    # Verify category exists
    category = db.query(BudgetCategory).filter(
        BudgetCategory.id == bulk_data.category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found"
        )

    updated = db.query(BankTransaction).filter(
        BankTransaction.id.in_(bulk_data.transaction_ids),
        BankTransaction.is_active == True
    ).update({
        BankTransaction.category_id: bulk_data.category_id,
        BankTransaction.status: BankTransactionStatusEnum.CATEGORIZED,
        BankTransaction.reviewed_by: current_user.id,
        BankTransaction.reviewed_at: datetime.utcnow()
    }, synchronize_session=False)

    db.commit()

    return {"message": f"Updated {updated} transactions"}


@router.post("/bulk-status-update")
def bulk_status_update(
    bulk_data: BankTransactionBulkStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Bulk update status of multiple transactions."""
    updated = db.query(BankTransaction).filter(
        BankTransaction.id.in_(bulk_data.transaction_ids),
        BankTransaction.is_active == True
    ).update({
        BankTransaction.status: bulk_data.status,
        BankTransaction.reviewed_by: current_user.id,
        BankTransaction.reviewed_at: datetime.utcnow()
    }, synchronize_session=False)

    db.commit()

    return {"message": f"Updated {updated} transactions"}


# ==================== AI Classification ====================

@router.get("/{transaction_id}/category-suggestions", response_model=List[CategorySuggestion])
def get_category_suggestions(
    transaction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get AI category suggestions for transaction."""
    transaction = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id,
        BankTransaction.is_active == True
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    classifier = TransactionClassifier(db)

    suggestions = classifier.get_suggestions(
        payment_purpose=transaction.payment_purpose,
        counterparty_name=transaction.counterparty_name,
        counterparty_inn=transaction.counterparty_inn,
        amount=float(transaction.amount) if transaction.amount else None,
        department_id=transaction.department_id,
        business_operation=transaction.business_operation,
        transaction_type=transaction.transaction_type.value if transaction.transaction_type else None,
        limit=5
    )

    result = []
    for s in suggestions:
        category = db.query(BudgetCategory).filter(BudgetCategory.id == s['category_id']).first()
        if category:
            result.append(CategorySuggestion(
                category_id=s['category_id'],
                category_name=category.name,
                confidence=s['confidence'],
                reasoning=s.get('reasoning')
            ))

    return result


@router.post("/{transaction_id}/apply-ai-suggestion", response_model=BankTransactionResponse)
def apply_ai_suggestion(
    transaction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Apply AI suggested category to transaction."""
    transaction = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id,
        BankTransaction.is_active == True
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    if not transaction.suggested_category_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No AI suggestion available"
        )

    transaction.category_id = transaction.suggested_category_id
    transaction.status = BankTransactionStatusEnum.CATEGORIZED
    transaction.reviewed_by = current_user.id
    transaction.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(transaction)

    return transaction


# ==================== Excel Import ====================

@router.post("/import/preview", response_model=BankTransactionImportPreview)
async def preview_import(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Preview Excel file before import."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Excel files (.xlsx, .xls) are supported"
        )

    content = await file.read()
    importer = BankTransactionImporter(db)
    result = importer.preview_import(content, file.filename)

    return BankTransactionImportPreview(**result)


@router.post("/import", response_model=BankTransactionImportResult)
async def import_from_excel(
    file: UploadFile = File(...),
    department_id: int = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Import transactions from Excel file."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Excel files (.xlsx, .xls) are supported"
        )

    content = await file.read()
    importer = BankTransactionImporter(db)
    result = importer.import_from_excel(
        file_content=content,
        filename=file.filename,
        department_id=department_id,
        user_id=current_user.id
    )

    return BankTransactionImportResult(**result)


# ==================== Regular Patterns ====================

@router.get("/regular-patterns")
def get_regular_patterns(
    department_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detected regular payment patterns."""
    from app.services.transaction_classifier import RegularPaymentDetector

    dept_id = department_id
    if current_user.role == UserRoleEnum.USER:
        dept_id = current_user.department_id

    detector = RegularPaymentDetector(db, dept_id)
    patterns = detector.detect_patterns()

    return patterns
