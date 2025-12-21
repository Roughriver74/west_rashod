"""Bank transactions API endpoints - core module."""
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, extract

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
    CategorySuggestion, BankTransactionList, BankTransactionAnalytics,
    BankTransactionKPIs, MonthlyFlowData, DailyFlowData, CategoryBreakdown,
    CounterpartyBreakdown, ProcessingFunnelData, ProcessingFunnelStage,
    AIPerformanceData, ConfidenceBracket, LowConfidenceItem,
    RegularPaymentPattern, RegularPaymentPatternList
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
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get transaction statistics."""
    query = db.query(BankTransaction).filter(BankTransaction.is_active == True)

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


# ==================== Analytics ====================

@router.get("/analytics", response_model=BankTransactionAnalytics)
def get_analytics(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    transaction_type: Optional[BankTransactionTypeEnum] = None,
    category_id: Optional[int] = None,
    compare_previous_period: bool = Query(True, description="Include comparison with previous period"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive analytics for bank transactions."""
    MONTH_NAMES_RU = [
        '', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]

    # Base query
    query = db.query(BankTransaction).filter(BankTransaction.is_active == True)

    # Apply date filters
    if year and month:
        query = query.filter(
            extract('year', BankTransaction.transaction_date) == year,
            extract('month', BankTransaction.transaction_date) == month
        )
    elif year:
        query = query.filter(extract('year', BankTransaction.transaction_date) == year)

    if date_from:
        query = query.filter(BankTransaction.transaction_date >= date_from)
    if date_to:
        query = query.filter(BankTransaction.transaction_date <= date_to)

    if transaction_type:
        query = query.filter(BankTransaction.transaction_type == transaction_type)
    if category_id:
        query = query.filter(BankTransaction.category_id == category_id)

    # Get all matching transactions
    transactions = query.all()
    total_count = len(transactions)

    # ====== KPIs Calculation ======
    debit_transactions = [t for t in transactions if t.transaction_type == BankTransactionTypeEnum.DEBIT]
    credit_transactions = [t for t in transactions if t.transaction_type == BankTransactionTypeEnum.CREDIT]

    total_debit = sum(t.amount for t in debit_transactions) if debit_transactions else Decimal(0)
    total_credit = sum(t.amount for t in credit_transactions) if credit_transactions else Decimal(0)
    net_flow = total_credit - total_debit

    # Status counts
    status_counts = {}
    for status_enum in BankTransactionStatusEnum:
        status_counts[status_enum.value] = len([t for t in transactions if t.status == status_enum])

    # AI metrics
    categorized_transactions = [t for t in transactions if t.category_id is not None]
    auto_categorized = [t for t in categorized_transactions if t.category_confidence and float(t.category_confidence) >= 0.9]
    regular_payments = [t for t in transactions if t.is_regular_payment]

    avg_confidence = None
    if categorized_transactions:
        confidences = [float(t.category_confidence) for t in categorized_transactions if t.category_confidence]
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)

    # Previous period comparison
    debit_change_percent = None
    credit_change_percent = None
    net_flow_change_percent = None
    transactions_change = None

    if compare_previous_period and date_from and date_to:
        period_days = (date_to - date_from).days + 1
        prev_date_from = date_from - timedelta(days=period_days)
        prev_date_to = date_from - timedelta(days=1)

        prev_query = db.query(BankTransaction).filter(
            BankTransaction.is_active == True,
            BankTransaction.transaction_date >= prev_date_from,
            BankTransaction.transaction_date <= prev_date_to
        )

        prev_transactions = prev_query.all()
        prev_debit = sum(t.amount for t in prev_transactions if t.transaction_type == BankTransactionTypeEnum.DEBIT)
        prev_credit = sum(t.amount for t in prev_transactions if t.transaction_type == BankTransactionTypeEnum.CREDIT)
        prev_net_flow = prev_credit - prev_debit

        if prev_debit > 0:
            debit_change_percent = float((total_debit - prev_debit) / prev_debit * 100)
        if prev_credit > 0:
            credit_change_percent = float((total_credit - prev_credit) / prev_credit * 100)
        if prev_net_flow != 0:
            net_flow_change_percent = float((net_flow - prev_net_flow) / abs(prev_net_flow) * 100)
        transactions_change = total_count - len(prev_transactions)

    kpis = BankTransactionKPIs(
        total_debit_amount=total_debit,
        total_credit_amount=total_credit,
        net_flow=net_flow,
        total_transactions=total_count,
        debit_change_percent=debit_change_percent,
        credit_change_percent=credit_change_percent,
        net_flow_change_percent=net_flow_change_percent,
        transactions_change=transactions_change,
        new_count=status_counts.get(BankTransactionStatusEnum.NEW.value, 0),
        categorized_count=status_counts.get(BankTransactionStatusEnum.CATEGORIZED.value, 0),
        approved_count=status_counts.get(BankTransactionStatusEnum.APPROVED.value, 0),
        needs_review_count=status_counts.get(BankTransactionStatusEnum.NEEDS_REVIEW.value, 0),
        ignored_count=status_counts.get(BankTransactionStatusEnum.IGNORED.value, 0),
        new_percent=float(status_counts.get(BankTransactionStatusEnum.NEW.value, 0) / total_count * 100) if total_count > 0 else 0,
        categorized_percent=float(status_counts.get(BankTransactionStatusEnum.CATEGORIZED.value, 0) / total_count * 100) if total_count > 0 else 0,
        approved_percent=float(status_counts.get(BankTransactionStatusEnum.APPROVED.value, 0) / total_count * 100) if total_count > 0 else 0,
        needs_review_percent=float(status_counts.get(BankTransactionStatusEnum.NEEDS_REVIEW.value, 0) / total_count * 100) if total_count > 0 else 0,
        ignored_percent=float(status_counts.get(BankTransactionStatusEnum.IGNORED.value, 0) / total_count * 100) if total_count > 0 else 0,
        avg_category_confidence=avg_confidence,
        auto_categorized_count=len(auto_categorized),
        auto_categorized_percent=float(len(auto_categorized) / total_count * 100) if total_count > 0 else 0,
        regular_payments_count=len(regular_payments),
        regular_payments_percent=float(len(regular_payments) / total_count * 100) if total_count > 0 else 0,
    )

    # ====== Monthly Flow Data ======
    monthly_dict = defaultdict(lambda: {'debit': Decimal(0), 'credit': Decimal(0), 'count': 0, 'confidences': []})

    for t in transactions:
        key = (t.transaction_date.year, t.transaction_date.month)
        if t.transaction_type == BankTransactionTypeEnum.DEBIT:
            monthly_dict[key]['debit'] += t.amount
        else:
            monthly_dict[key]['credit'] += t.amount
        monthly_dict[key]['count'] += 1
        if t.category_confidence:
            monthly_dict[key]['confidences'].append(float(t.category_confidence))

    monthly_flow = []
    for (year_val, month_val), data in sorted(monthly_dict.items()):
        avg_conf = None
        if data['confidences']:
            avg_conf = sum(data['confidences']) / len(data['confidences'])

        monthly_flow.append(MonthlyFlowData(
            year=year_val,
            month=month_val,
            month_name=f"{MONTH_NAMES_RU[month_val]} {year_val}",
            debit_amount=data['debit'],
            credit_amount=data['credit'],
            net_flow=data['credit'] - data['debit'],
            transaction_count=data['count'],
            avg_confidence=avg_conf
        ))

    # ====== Daily Flow Data ======
    daily_dict = defaultdict(lambda: {'debit': Decimal(0), 'credit': Decimal(0), 'count': 0})

    for t in transactions:
        if t.transaction_type == BankTransactionTypeEnum.DEBIT:
            daily_dict[t.transaction_date]['debit'] += t.amount
        else:
            daily_dict[t.transaction_date]['credit'] += t.amount
        daily_dict[t.transaction_date]['count'] += 1

    daily_flow = []
    for day_key, values in sorted(daily_dict.items()):
        daily_flow.append(DailyFlowData(
            date=day_key,
            debit_amount=values['debit'],
            credit_amount=values['credit'],
            net_flow=values['credit'] - values['debit'],
            transaction_count=values['count'],
        ))

    # ====== Category Breakdown ======
    category_dict = defaultdict(lambda: {'count': 0, 'total': Decimal(0), 'confidences': [], 'type': None, 'name': ''})

    for t in transactions:
        if t.category_id:
            category_dict[t.category_id]['count'] += 1
            category_dict[t.category_id]['total'] += t.amount
            if t.category_confidence:
                category_dict[t.category_id]['confidences'].append(float(t.category_confidence))
            if t.category_rel:
                category_dict[t.category_id]['name'] = t.category_rel.name
                category_dict[t.category_id]['type'] = t.category_rel.type.value if t.category_rel.type else None

    total_categorized_amount = sum(d['total'] for d in category_dict.values())

    top_categories = []
    for cat_id, data in sorted(category_dict.items(), key=lambda x: x[1]['total'], reverse=True)[:10]:
        avg_conf = sum(data['confidences']) / len(data['confidences']) if data['confidences'] else None
        top_categories.append(CategoryBreakdown(
            category_id=cat_id,
            category_name=data['name'],
            category_type=data['type'],
            transaction_count=data['count'],
            total_amount=data['total'],
            avg_amount=data['total'] / data['count'] if data['count'] > 0 else Decimal(0),
            avg_confidence=avg_conf,
            percent_of_total=float(data['total'] / total_categorized_amount * 100) if total_categorized_amount > 0 else 0
        ))

    # Category type distribution
    category_type_distribution = []

    # ====== Counterparty Breakdown ======
    counterparty_dict = defaultdict(lambda: {
        'count': 0, 'total': Decimal(0), 'first_date': None, 'last_date': None, 'is_regular': False, 'name': ''
    })

    for t in transactions:
        if t.counterparty_inn:
            key = t.counterparty_inn
            counterparty_dict[key]['count'] += 1
            counterparty_dict[key]['total'] += t.amount
            counterparty_dict[key]['name'] = t.counterparty_name or 'Unknown'
            if counterparty_dict[key]['first_date'] is None or t.transaction_date < counterparty_dict[key]['first_date']:
                counterparty_dict[key]['first_date'] = t.transaction_date
            if counterparty_dict[key]['last_date'] is None or t.transaction_date > counterparty_dict[key]['last_date']:
                counterparty_dict[key]['last_date'] = t.transaction_date
            if t.is_regular_payment:
                counterparty_dict[key]['is_regular'] = True

    top_counterparties = []
    for cp_inn, data in sorted(counterparty_dict.items(), key=lambda x: x[1]['total'], reverse=True)[:20]:
        top_counterparties.append(CounterpartyBreakdown(
            counterparty_inn=cp_inn,
            counterparty_name=data['name'],
            transaction_count=data['count'],
            total_amount=data['total'],
            avg_amount=data['total'] / data['count'] if data['count'] > 0 else Decimal(0),
            first_transaction_date=data['first_date'] or date.today(),
            last_transaction_date=data['last_date'] or date.today(),
            is_regular=data['is_regular']
        ))

    # ====== Processing Funnel ======
    funnel_stages = []
    for status_enum in BankTransactionStatusEnum:
        count = status_counts.get(status_enum.value, 0)
        amount = sum(t.amount for t in transactions if t.status == status_enum)

        funnel_stages.append(ProcessingFunnelStage(
            status=status_enum.value,
            count=count,
            amount=amount,
            percent_of_total=float(count / total_count * 100) if total_count > 0 else 0
        ))

    approved_count = status_counts.get(BankTransactionStatusEnum.APPROVED.value, 0)
    processing_funnel = ProcessingFunnelData(
        stages=funnel_stages,
        total_count=total_count,
        conversion_rate_to_approved=float(approved_count / total_count * 100) if total_count > 0 else 0
    )

    # ====== AI Performance ======
    confidence_brackets = [
        ('High (≥90%)', 0.9, 1.0),
        ('Medium (70-90%)', 0.7, 0.9),
        ('Low (50-70%)', 0.5, 0.7),
        ('Very Low (<50%)', 0.0, 0.5),
    ]

    confidence_distribution = []
    for bracket_name, min_conf, max_conf in confidence_brackets:
        bracket_transactions = [
            t for t in categorized_transactions
            if t.category_confidence and min_conf <= float(t.category_confidence) < max_conf
        ]
        count = len(bracket_transactions)
        amount = sum(t.amount for t in bracket_transactions)

        confidence_distribution.append(ConfidenceBracket(
            bracket=bracket_name,
            min_confidence=min_conf,
            max_confidence=max_conf,
            count=count,
            total_amount=amount,
            percent_of_total=float(count / len(categorized_transactions) * 100) if categorized_transactions else 0
        ))

    high_confidence_count = len([t for t in categorized_transactions if t.category_confidence and float(t.category_confidence) >= 0.9])
    low_confidence_count = len([t for t in categorized_transactions if t.category_confidence and float(t.category_confidence) < 0.7])

    ai_performance = AIPerformanceData(
        confidence_distribution=confidence_distribution,
        avg_confidence=avg_confidence or 0.0,
        high_confidence_count=high_confidence_count,
        high_confidence_percent=float(high_confidence_count / len(categorized_transactions) * 100) if categorized_transactions else 0,
        low_confidence_count=low_confidence_count,
        low_confidence_percent=float(low_confidence_count / len(categorized_transactions) * 100) if categorized_transactions else 0
    )

    # ====== Low Confidence Items ======
    low_confidence_items = []
    for t in [t for t in transactions if t.category_confidence and float(t.category_confidence) < 0.7][:50]:
        low_confidence_items.append(LowConfidenceItem(
            transaction_id=t.id,
            transaction_date=t.transaction_date,
            counterparty_name=t.counterparty_name or 'Unknown',
            amount=t.amount,
            payment_purpose=t.payment_purpose,
            suggested_category_name=t.suggested_category_rel.name if t.suggested_category_rel else None,
            category_confidence=float(t.category_confidence),
            status=t.status.value
        ))

    return BankTransactionAnalytics(
        kpis=kpis,
        monthly_flow=monthly_flow,
        daily_flow=daily_flow,
        top_categories=top_categories,
        category_type_distribution=category_type_distribution,
        top_counterparties=top_counterparties,
        processing_funnel=processing_funnel,
        ai_performance=ai_performance,
        low_confidence_items=low_confidence_items
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


@router.post("/bulk-delete")
def bulk_delete_transactions(
    transaction_ids: List[int],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Bulk delete transactions (ADMIN and MANAGER only)."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMIN and MANAGER can bulk delete transactions"
        )

    # Get transactions
    transactions = db.query(BankTransaction).filter(
        BankTransaction.id.in_(transaction_ids)
    ).all()

    if not transactions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transactions found"
        )

    # Soft delete all
    deleted_count = 0
    for tx in transactions:
        tx.is_active = False
        deleted_count += 1

    db.commit()

    return {"message": f"Successfully deleted {deleted_count} transactions", "deleted": deleted_count}


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
        user_id=current_user.id
    )

    return BankTransactionImportResult(**result)


# ==================== Regular Patterns ====================

@router.get("/regular-patterns", response_model=RegularPaymentPatternList)
def get_regular_patterns(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get detected regular payment patterns."""
    from app.services.transaction_classifier import RegularPaymentDetector

    detector = RegularPaymentDetector(db)
    raw_patterns = detector.detect_patterns()

    # Convert to schema
    patterns = [RegularPaymentPattern(**p) for p in raw_patterns]

    monthly_count = len([p for p in patterns if p.is_monthly])
    quarterly_count = len([p for p in patterns if p.is_quarterly])
    other_count = len(patterns) - monthly_count - quarterly_count

    return RegularPaymentPatternList(
        patterns=patterns,
        total_count=len(patterns),
        monthly_count=monthly_count,
        quarterly_count=quarterly_count,
        other_count=other_count
    )


@router.post("/mark-regular-payments")
def mark_regular_payments(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark transactions as regular payments based on detected patterns."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMIN and MANAGER can mark regular payments"
        )

    from app.services.transaction_classifier import RegularPaymentDetector

    detector = RegularPaymentDetector(db)
    marked_count = detector.mark_regular_payments()

    return {"message": f"Marked {marked_count} transactions as regular payments", "marked_count": marked_count}


# ==================== Expense Linking ====================

@router.get("/{transaction_id}/matching-expenses")
def get_matching_expenses(
    transaction_id: int,
    threshold: float = Query(30.0, description="Minimum matching score"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get matching expense suggestions for a transaction."""
    from app.services.expense_matching import ExpenseMatchingService

    transaction = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id,
        BankTransaction.is_active == True
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    matching_service = ExpenseMatchingService(db)
    suggestions = matching_service.find_matching_expenses(transaction, threshold=threshold)

    return suggestions


@router.put("/{transaction_id}/link")
def link_to_expense(
    transaction_id: int,
    expense_id: int = Query(..., description="Expense ID to link to"),
    notes: Optional[str] = Query(None, description="Optional notes"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Link transaction to an expense."""
    from app.services.expense_matching import ExpenseMatchingService

    transaction = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id,
        BankTransaction.is_active == True
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    if transaction.expense_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction is already linked to an expense"
        )

    matching_service = ExpenseMatchingService(db)

    try:
        matching_service.link_transaction_to_expense(transaction_id, expense_id)

        if notes:
            transaction.notes = notes
            db.commit()

        return {"message": "Transaction linked successfully", "expense_id": expense_id}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{transaction_id}/unlink")
def unlink_from_expense(
    transaction_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Unlink transaction from expense."""
    from app.db.models import Expense, ExpenseStatusEnum
    from decimal import Decimal

    transaction = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id,
        BankTransaction.is_active == True
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    if not transaction.expense_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction is not linked to any expense"
        )

    # Get expense and update paid amount
    expense = db.query(Expense).filter(Expense.id == transaction.expense_id).first()
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

    # Unlink transaction
    old_expense_id = transaction.expense_id
    transaction.expense_id = None
    transaction.matching_score = None
    transaction.status = BankTransactionStatusEnum.CATEGORIZED

    db.commit()

    return {"message": "Transaction unlinked successfully", "old_expense_id": old_expense_id}


@router.post("/bulk-link")
def bulk_link_to_expenses(
    links: List[dict],  # [{"transaction_id": 1, "expense_id": 10}, ...]
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Bulk link transactions to expenses."""
    from app.services.expense_matching import ExpenseMatchingService

    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMIN and MANAGER can bulk link"
        )

    matching_service = ExpenseMatchingService(db)

    linked_count = 0
    errors = []

    for link in links:
        transaction_id = link.get("transaction_id")
        expense_id = link.get("expense_id")

        if not transaction_id or not expense_id:
            errors.append({"link": link, "error": "Missing transaction_id or expense_id"})
            continue

        try:
            matching_service.link_transaction_to_expense(transaction_id, expense_id)
            linked_count += 1
        except ValueError as e:
            errors.append({"transaction_id": transaction_id, "expense_id": expense_id, "error": str(e)})

    return {
        "success": len(errors) == 0,
        "linked_count": linked_count,
        "errors": errors
    }


@router.post("/auto-match")
def auto_match_transactions(
    threshold: float = Query(70.0, description="Minimum matching score for auto-matching"),
    limit: int = Query(100, description="Maximum number of transactions to process"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Automatically match unlinked transactions to expenses."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMIN and MANAGER can run auto-matching"
        )

    from app.services.expense_matching import ExpenseMatchingService

    matching_service = ExpenseMatchingService(db)
    matched = matching_service.auto_match_transactions(threshold=threshold, limit=limit)

    return {
        "message": f"Auto-matched {len(matched)} transactions",
        "matched_count": len(matched),
        "matches": matched
    }
