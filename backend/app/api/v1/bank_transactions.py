"""Bank transactions API endpoints - core module."""
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, extract, case
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models import (
    BankTransaction, BudgetCategory, Organization, User, UserRoleEnum,
    BankTransactionTypeEnum, BankTransactionStatusEnum,
    CategorizationRule, CategorizationRuleTypeEnum
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
    ActivityHeatmapPoint, StatusTimelinePoint, ConfidenceScatterPoint,
    RegionalData, SourceDistribution, RegularPaymentSummary, ExhibitionData,
    RegularPaymentPattern, RegularPaymentPatternList,
    AccountGrouping, AccountGroupingList,
    RuleSuggestion, RuleSuggestionsResponse,
    CategorizationWithSuggestionsResponse, BulkCategorizationWithSuggestionsResponse,
    CreateRuleFromSuggestionRequest
)
from app.utils.auth import get_current_active_user
from app.services.transaction_classifier import TransactionClassifier
from app.services.bank_transaction_import import BankTransactionImporter

router = APIRouter(prefix="/bank-transactions", tags=["Bank Transactions"])


# ==================== Helper Functions ====================

def analyze_rule_suggestions(
    transactions: List[BankTransaction],
    category_id: int,
    db: Session
) -> RuleSuggestionsResponse:
    """
    Анализирует транзакции и возвращает предложения для создания правил.
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"🔍 Analyzing {len(transactions)} transactions for rule suggestions")

    # Получаем имя категории
    category = db.query(BudgetCategory).filter(BudgetCategory.id == category_id).first()
    category_name = category.name if category else "Неизвестная категория"

    suggestions_list = []

    # Собираем статистику по ИНН, названиям и операциям
    inn_counter = {}
    name_counter = {}
    operation_counter = {}

    for tx in transactions:
        if tx.counterparty_inn:
            inn_counter[tx.counterparty_inn] = inn_counter.get(tx.counterparty_inn, 0) + 1
        if tx.counterparty_name:
            name_counter[tx.counterparty_name] = name_counter.get(tx.counterparty_name, 0) + 1
        if tx.business_operation:
            operation_counter[tx.business_operation] = operation_counter.get(tx.business_operation, 0) + 1

    logger.info(f"📊 Stats: INNs={len(inn_counter)}, Names={len(name_counter)}, Operations={len(operation_counter)}")

    # Анализируем ИНН
    if inn_counter:
        most_common_inn = max(inn_counter.items(), key=lambda x: x[1])

        # Проверяем, нет ли уже такого правила
        existing_rule = db.query(CategorizationRule).filter(
            CategorizationRule.rule_type == CategorizationRuleTypeEnum.COUNTERPARTY_INN,
            CategorizationRule.counterparty_inn == most_common_inn[0],
            CategorizationRule.category_id == category_id,
            CategorizationRule.is_active == True
        ).first()

        # Найдём имя контрагента для этого ИНН
        counterparty_name = "Неизвестно"
        for tx in transactions:
            if tx.counterparty_inn == most_common_inn[0] and tx.counterparty_name:
                counterparty_name = tx.counterparty_name
                break

        # Считаем, сколько существующих транзакций без категории подходят под это правило
        matching_count = db.query(BankTransaction).filter(
            BankTransaction.is_active == True,
            BankTransaction.counterparty_inn == most_common_inn[0],
            or_(
                BankTransaction.category_id == None,
                BankTransaction.status == BankTransactionStatusEnum.NEEDS_REVIEW
            )
        ).count()

        suggestions_list.append(RuleSuggestion(
            rule_type="COUNTERPARTY_INN",
            match_value=most_common_inn[0],
            transaction_count=most_common_inn[1],
            description=f"По ИНН контрагента: {counterparty_name} ({most_common_inn[0]})",
            can_create=not existing_rule,
            matching_existing_count=matching_count
        ))

    # Анализируем название контрагента
    if name_counter:
        most_common_name = max(name_counter.items(), key=lambda x: x[1])

        existing_rule = db.query(CategorizationRule).filter(
            CategorizationRule.rule_type == CategorizationRuleTypeEnum.COUNTERPARTY_NAME,
            CategorizationRule.counterparty_name == most_common_name[0],
            CategorizationRule.category_id == category_id,
            CategorizationRule.is_active == True
        ).first()

        # Считаем подходящие транзакции
        matching_count = db.query(BankTransaction).filter(
            BankTransaction.is_active == True,
            BankTransaction.counterparty_name == most_common_name[0],
            or_(
                BankTransaction.category_id == None,
                BankTransaction.status == BankTransactionStatusEnum.NEEDS_REVIEW
            )
        ).count()

        suggestions_list.append(RuleSuggestion(
            rule_type="COUNTERPARTY_NAME",
            match_value=most_common_name[0],
            transaction_count=most_common_name[1],
            description=f"По названию контрагента: {most_common_name[0]}",
            can_create=not existing_rule,
            matching_existing_count=matching_count
        ))

    # Анализируем хозяйственную операцию
    if operation_counter:
        most_common_operation = max(operation_counter.items(), key=lambda x: x[1])

        existing_rule = db.query(CategorizationRule).filter(
            CategorizationRule.rule_type == CategorizationRuleTypeEnum.BUSINESS_OPERATION,
            CategorizationRule.business_operation == most_common_operation[0],
            CategorizationRule.category_id == category_id,
            CategorizationRule.is_active == True
        ).first()

        # Считаем подходящие транзакции
        matching_count = db.query(BankTransaction).filter(
            BankTransaction.is_active == True,
            BankTransaction.business_operation == most_common_operation[0],
            or_(
                BankTransaction.category_id == None,
                BankTransaction.status == BankTransactionStatusEnum.NEEDS_REVIEW
            )
        ).count()

        suggestions_list.append(RuleSuggestion(
            rule_type="BUSINESS_OPERATION",
            match_value=most_common_operation[0],
            transaction_count=most_common_operation[1],
            description=f"По хозяйственной операции: {most_common_operation[0]}",
            can_create=not existing_rule,
            matching_existing_count=matching_count
        ))

    # Анализируем ключевые слова из назначения платежа
    stop_words = {
        'для', 'при', 'или', 'без', 'под', 'над', 'перед', 'после',
        'через', 'между', 'среди', 'вместо', 'кроме', 'около', 'вдоль',
        'оплата', 'плата', 'платеж', 'счет', 'счёт', 'счету', 'договор',
        'договору', 'номер', 'дата', 'период', 'услуги', 'услуг',
        'работы', 'работ', 'товар', 'товара', 'товаров', 'включая',
        'также', 'всего', 'итого', 'сумма', 'сумму', 'рублей', 'рубль',
        'копеек', 'копейка', 'безналичный', 'наличный', 'перевод',
        'перечисление', 'возврат', 'аванс', 'предоплата', 'доплата',
        'числе', 'число', 'включительно',
    }

    keyword_counter = {}
    for tx in transactions:
        if tx.payment_purpose:
            words = tx.payment_purpose.lower().split()
            for word in words:
                clean_word = word.strip('.,;:!?()[]{}"\'-')
                if len(clean_word) >= 5 and clean_word not in stop_words:
                    keyword_counter[clean_word] = keyword_counter.get(clean_word, 0) + 1

    if keyword_counter:
        # Берём самое частое ключевое слово
        most_common_keyword = max(keyword_counter.items(), key=lambda x: x[1])

        # Проверяем только если слово встречается в большинстве транзакций (>50%)
        if most_common_keyword[1] >= len(transactions) * 0.5:
            existing_rule = db.query(CategorizationRule).filter(
                CategorizationRule.rule_type == CategorizationRuleTypeEnum.KEYWORD,
                CategorizationRule.keyword == most_common_keyword[0],
                CategorizationRule.category_id == category_id,
                CategorizationRule.is_active == True
            ).first()

            # Считаем подходящие транзакции (ищем ключевое слово в назначении платежа)
            matching_count = db.query(BankTransaction).filter(
                BankTransaction.is_active == True,
                BankTransaction.payment_purpose.ilike(f"%{most_common_keyword[0]}%"),
                or_(
                    BankTransaction.category_id == None,
                    BankTransaction.status == BankTransactionStatusEnum.NEEDS_REVIEW
                )
            ).count()

            suggestions_list.append(RuleSuggestion(
                rule_type="KEYWORD",
                match_value=most_common_keyword[0],
                transaction_count=most_common_keyword[1],
                description=f"По ключевому слову: '{most_common_keyword[0]}'",
                can_create=not existing_rule,
                matching_existing_count=matching_count
            ))

    result = RuleSuggestionsResponse(
        suggestions=suggestions_list,
        total_transactions=len(transactions),
        category_id=category_id,
        category_name=category_name
    )

    logger.info(f"✅ Generated {len(suggestions_list)} rule suggestions")
    for sugg in suggestions_list:
        logger.info(f"   - {sugg.rule_type}: {sugg.match_value} (can_create={sugg.can_create})")

    return result


def create_categorization_rule_from_suggestion(
    rule_type: CategorizationRuleTypeEnum,
    match_value: str,
    category_id: int,
    user_id: int,
    priority: int,
    confidence: float,
    db: Session
) -> CategorizationRule:
    """
    Создаёт правило категоризации на основе предложения пользователя.
    """
    rule_data = {
        "rule_type": rule_type,
        "category_id": category_id,
        "priority": priority,
        "confidence": confidence,
        "is_active": True,
        "notes": f"Создано при категоризации",
        "created_by": user_id
    }

    if rule_type == CategorizationRuleTypeEnum.COUNTERPARTY_INN:
        rule_data["counterparty_inn"] = match_value
    elif rule_type == CategorizationRuleTypeEnum.COUNTERPARTY_NAME:
        rule_data["counterparty_name"] = match_value
    elif rule_type == CategorizationRuleTypeEnum.BUSINESS_OPERATION:
        rule_data["business_operation"] = match_value
    elif rule_type == CategorizationRuleTypeEnum.KEYWORD:
        rule_data["keyword"] = match_value

    new_rule = CategorizationRule(**rule_data)
    db.add(new_rule)
    db.flush()
    return new_rule


# ==================== List & Stats ====================

@router.get("/", response_model=BankTransactionList)
def get_bank_transactions(
    skip: int = 0,
    limit: int = 100,
    status: Optional[BankTransactionStatusEnum] = None,
    transaction_type: Optional[BankTransactionTypeEnum] = None,
    payment_source: Optional[str] = None,
    account_number: Optional[str] = None,
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
    base_query = db.query(BankTransaction).filter(BankTransaction.is_active == True)

    # Status filter
    if status:
        base_query = base_query.filter(BankTransaction.status == status)

    # Type filter
    if transaction_type:
        base_query = base_query.filter(BankTransaction.transaction_type == transaction_type)

    # Payment source filter
    if payment_source:
        base_query = base_query.filter(BankTransaction.payment_source == payment_source)

    # Account number filter - special handling for "Не указан" (null accounts)
    if account_number:
        if account_number == "Не указан":
            base_query = base_query.filter(BankTransaction.account_number.is_(None))
        else:
            base_query = base_query.filter(BankTransaction.account_number == account_number)

    # Date range
    if date_from:
        base_query = base_query.filter(BankTransaction.transaction_date >= date_from)
    if date_to:
        base_query = base_query.filter(BankTransaction.transaction_date <= date_to)

    # Category filter - special handling for null (no category)
    if category_id is not None:
        if category_id == 0 or str(category_id).lower() == 'null':
            base_query = base_query.filter(BankTransaction.category_id.is_(None))
        else:
            base_query = base_query.filter(BankTransaction.category_id == category_id)

    # Organization filter
    if organization_id:
        base_query = base_query.filter(BankTransaction.organization_id == organization_id)

    # Unprocessed only
    if only_unprocessed:
        base_query = base_query.filter(BankTransaction.status.in_([
            BankTransactionStatusEnum.NEW,
            BankTransactionStatusEnum.NEEDS_REVIEW
        ]))

    # Search
    if search:
        search_term = f"%{search}%"
        base_query = base_query.filter(
            or_(
                BankTransaction.counterparty_name.ilike(search_term),
                BankTransaction.counterparty_inn.ilike(search_term),
                BankTransaction.payment_purpose.ilike(search_term),
                BankTransaction.document_number.ilike(search_term)
            )
        )

    # Get total count
    total = base_query.count()

    # Order and paginate
    query = base_query.options(
        joinedload(BankTransaction.category_rel),
        joinedload(BankTransaction.organization_rel),
        joinedload(BankTransaction.suggested_category_rel)
    ).order_by(
        BankTransaction.transaction_date.desc(),
        BankTransaction.id.desc()
    ).offset(skip).limit(limit)

    transactions = query.all()

    # Add related names
    result = []
    for t in transactions:
        t_dict = BankTransactionResponse.model_validate(t).model_dump()
        t_dict['category_name'] = t.category_rel.name if t.category_rel else None
        t_dict['organization_name'] = t.organization_rel.name if t.organization_rel else None
        t_dict['suggested_category_name'] = t.suggested_category_rel.name if t.suggested_category_rel else None
        result.append(BankTransactionResponse(**t_dict))

    # Calculate pagination info
    page = (skip // limit) + 1 if limit > 0 else 1
    pages = (total + limit - 1) // limit if limit > 0 else 1

    return BankTransactionList(
        total=total,
        items=result,
        page=page,
        page_size=limit,
        pages=pages
    )


@router.get("/stats", response_model=BankTransactionStats)
def get_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    transaction_type: Optional[BankTransactionTypeEnum] = None,
    payment_source: Optional[str] = None,
    account_number: Optional[str] = None,
    category_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    search: Optional[str] = None,
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

    # Transaction type filter
    if transaction_type:
        query = query.filter(BankTransaction.transaction_type == transaction_type)

    # Payment source filter
    if payment_source:
        query = query.filter(BankTransaction.payment_source == payment_source)

    # Account number filter - special handling for "Не указан" (null accounts)
    if account_number:
        if account_number == "Не указан":
            query = query.filter(BankTransaction.account_number.is_(None))
        else:
            query = query.filter(BankTransaction.account_number == account_number)

    # Category filter - special handling for null (no category)
    if category_id is not None:
        if category_id == 0 or str(category_id).lower() == 'null':
            query = query.filter(BankTransaction.category_id.is_(None))
        else:
            query = query.filter(BankTransaction.category_id == category_id)

    # Organization filter
    if organization_id:
        query = query.filter(BankTransaction.organization_id == organization_id)

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

    # Get counts by status
    total = query.count()
    new = query.filter(BankTransaction.status == BankTransactionStatusEnum.NEW).count()
    categorized = query.filter(BankTransaction.status == BankTransactionStatusEnum.CATEGORIZED).count()
    approved = query.filter(BankTransaction.status == BankTransactionStatusEnum.APPROVED).count()
    # needs_review включает как NEEDS_REVIEW, так и NEW статусы (все необработанные транзакции)
    needs_review = query.filter(
        BankTransaction.status.in_([
            BankTransactionStatusEnum.NEEDS_REVIEW,
            BankTransactionStatusEnum.NEW
        ])
    ).count()
    ignored = query.filter(BankTransaction.status == BankTransactionStatusEnum.IGNORED).count()

    # Get totals by type - use subquery for efficiency
    total_debit = query.filter(
        BankTransaction.transaction_type == BankTransactionTypeEnum.DEBIT
    ).with_entities(func.coalesce(func.sum(BankTransaction.amount), 0)).scalar() or Decimal("0")

    total_credit = query.filter(
        BankTransaction.transaction_type == BankTransactionTypeEnum.CREDIT
    ).with_entities(func.coalesce(func.sum(BankTransaction.amount), 0)).scalar() or Decimal("0")

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

    # Calculate needs_review as NEW + NEEDS_REVIEW (same logic as /stats endpoint)
    needs_review_count = (
        status_counts.get(BankTransactionStatusEnum.NEW.value, 0) +
        status_counts.get(BankTransactionStatusEnum.NEEDS_REVIEW.value, 0)
    )

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
        needs_review_count=needs_review_count,
        ignored_count=status_counts.get(BankTransactionStatusEnum.IGNORED.value, 0),
        new_percent=float(status_counts.get(BankTransactionStatusEnum.NEW.value, 0) / total_count * 100) if total_count > 0 else 0,
        categorized_percent=float(status_counts.get(BankTransactionStatusEnum.CATEGORIZED.value, 0) / total_count * 100) if total_count > 0 else 0,
        approved_percent=float(status_counts.get(BankTransactionStatusEnum.APPROVED.value, 0) / total_count * 100) if total_count > 0 else 0,
        needs_review_percent=float(needs_review_count / total_count * 100) if total_count > 0 else 0,
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
            first_transaction_date=data['first_date'] or datetime.now(),
            last_transaction_date=data['last_date'] or datetime.now(),
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

    # ====== Activity Heatmap (Day of Week × Hour) ======
    heatmap_dict = defaultdict(lambda: {'count': 0, 'total': Decimal(0)})
    for t in transactions:
        # Используем document_date (дата из 1С), если доступна, иначе transaction_date
        dt = t.document_date if t.document_date else t.transaction_date
        day_of_week = dt.weekday()  # 0=Monday, 6=Sunday
        hour = dt.hour
        key = (day_of_week, hour)
        heatmap_dict[key]['count'] += 1
        heatmap_dict[key]['total'] += t.amount

    activity_heatmap = []
    for (day, hour), data in sorted(heatmap_dict.items()):
        activity_heatmap.append(ActivityHeatmapPoint(
            day_of_week=day,
            hour=hour,
            transaction_count=data['count'],
            total_amount=data['total'],
            avg_amount=data['total'] / data['count'] if data['count'] > 0 else Decimal(0)
        ))

    # ====== Status Timeline ======
    timeline_dict = defaultdict(lambda: {
        'new': 0, 'categorized': 0, 'matched': 0, 'approved': 0, 'needs_review': 0, 'ignored': 0
    })
    for t in transactions:
        day_key = t.transaction_date
        if t.status == BankTransactionStatusEnum.NEW:
            timeline_dict[day_key]['new'] += 1
        elif t.status == BankTransactionStatusEnum.CATEGORIZED:
            timeline_dict[day_key]['categorized'] += 1
        elif t.status == BankTransactionStatusEnum.MATCHED:
            timeline_dict[day_key]['matched'] += 1
        elif t.status == BankTransactionStatusEnum.APPROVED:
            timeline_dict[day_key]['approved'] += 1
        elif t.status == BankTransactionStatusEnum.NEEDS_REVIEW:
            timeline_dict[day_key]['needs_review'] += 1
        elif t.status == BankTransactionStatusEnum.IGNORED:
            timeline_dict[day_key]['ignored'] += 1

    status_timeline = []
    for day_key, counts in sorted(timeline_dict.items()):
        status_timeline.append(StatusTimelinePoint(
            date=day_key,
            new_count=counts['new'],
            categorized_count=counts['categorized'],
            matched_count=counts['matched'],
            approved_count=counts['approved'],
            needs_review_count=counts['needs_review'],
            ignored_count=counts['ignored']
        ))

    # ====== Confidence Scatter (all categorized transactions) ======
    confidence_scatter = []
    for t in categorized_transactions[:500]:  # Limit to 500 points for performance
        confidence_scatter.append(ConfidenceScatterPoint(
            transaction_id=t.id,
            transaction_date=t.transaction_date,
            counterparty_name=t.counterparty_name,
            amount=t.amount,
            category_confidence=float(t.category_confidence) if t.category_confidence else None,
            status=t.status.value,
            transaction_type=t.transaction_type.value,
            is_regular_payment=t.is_regular_payment
        ))

    # ====== Regional Distribution ======
    region_dict = defaultdict(lambda: {'count': 0, 'total': Decimal(0)})
    total_with_region = 0
    for t in transactions:
        if t.region:
            region_dict[t.region.value]['count'] += 1
            region_dict[t.region.value]['total'] += t.amount
            total_with_region += 1

    regional_distribution = []
    for region_key, data in sorted(region_dict.items(), key=lambda x: x[1]['total'], reverse=True):
        regional_distribution.append(RegionalData(
            region=region_key,
            transaction_count=data['count'],
            total_amount=data['total'],
            avg_amount=data['total'] / data['count'] if data['count'] > 0 else Decimal(0),
            percent_of_total=float(data['count'] / total_with_region * 100) if total_with_region > 0 else 0
        ))

    # ====== Source Distribution ======
    source_dict = defaultdict(lambda: {'count': 0, 'total': Decimal(0)})
    for t in transactions:
        source_key = t.payment_source.value if t.payment_source else 'BANK'
        source_dict[source_key]['count'] += 1
        source_dict[source_key]['total'] += t.amount

    source_distribution = []
    for source_key, data in sorted(source_dict.items()):
        source_distribution.append(SourceDistribution(
            source=source_key,
            transaction_count=data['count'],
            total_amount=data['total'],
            percent_of_total=float(data['count'] / total_count * 100) if total_count > 0 else 0
        ))

    # ====== Regular Payments Summary ======
    regular_dict = defaultdict(lambda: {
        'count': 0, 'total': Decimal(0), 'first_date': None, 'last_date': None,
        'name': '', 'category_id': None, 'category_name': None
    })
    for t in regular_payments:
        key = t.counterparty_inn or t.counterparty_name or 'Unknown'
        regular_dict[key]['count'] += 1
        regular_dict[key]['total'] += t.amount
        regular_dict[key]['name'] = t.counterparty_name or 'Unknown'
        if t.category_id:
            regular_dict[key]['category_id'] = t.category_id
            regular_dict[key]['category_name'] = t.category_rel.name if t.category_rel else None
        if regular_dict[key]['first_date'] is None or t.transaction_date < regular_dict[key]['first_date']:
            regular_dict[key]['first_date'] = t.transaction_date
        if regular_dict[key]['last_date'] is None or t.transaction_date > regular_dict[key]['last_date']:
            regular_dict[key]['last_date'] = t.transaction_date

    regular_payments_summary = []
    for cp_key, data in sorted(regular_dict.items(), key=lambda x: x[1]['count'], reverse=True)[:20]:
        if data['first_date'] and data['last_date'] and data['count'] > 1:
            frequency_days = int((data['last_date'] - data['first_date']).days / (data['count'] - 1))
        else:
            frequency_days = 30

        is_monthly = 25 <= frequency_days <= 35
        is_quarterly = 85 <= frequency_days <= 95

        regular_payments_summary.append(RegularPaymentSummary(
            counterparty_inn=cp_key if len(cp_key) == 10 or len(cp_key) == 12 else None,
            counterparty_name=data['name'],
            category_id=data['category_id'],
            category_name=data['category_name'],
            avg_amount=data['total'] / data['count'] if data['count'] > 0 else Decimal(0),
            frequency_days=frequency_days,
            last_payment_date=data['last_date'] or date.today(),
            transaction_count=data['count'],
            is_monthly=is_monthly,
            is_quarterly=is_quarterly
        ))

    # ====== Exhibition Spending ======
    exhibition_dict = defaultdict(lambda: {
        'count': 0, 'total': Decimal(0), 'first_date': None, 'last_date': None
    })
    for t in transactions:
        if t.exhibition:
            exhibition_dict[t.exhibition]['count'] += 1
            exhibition_dict[t.exhibition]['total'] += t.amount
            if exhibition_dict[t.exhibition]['first_date'] is None or t.transaction_date < exhibition_dict[t.exhibition]['first_date']:
                exhibition_dict[t.exhibition]['first_date'] = t.transaction_date
            if exhibition_dict[t.exhibition]['last_date'] is None or t.transaction_date > exhibition_dict[t.exhibition]['last_date']:
                exhibition_dict[t.exhibition]['last_date'] = t.transaction_date

    exhibitions = []
    for exhibition_name, data in sorted(exhibition_dict.items(), key=lambda x: x[1]['total'], reverse=True):
        exhibitions.append(ExhibitionData(
            exhibition=exhibition_name,
            transaction_count=data['count'],
            total_amount=data['total'],
            avg_amount=data['total'] / data['count'] if data['count'] > 0 else Decimal(0),
            first_transaction_date=data['first_date'] or datetime.now(),
            last_transaction_date=data['last_date'] or datetime.now()
        ))

    return BankTransactionAnalytics(
        kpis=kpis,
        monthly_flow=monthly_flow,
        daily_flow=daily_flow,
        top_categories=top_categories,
        category_type_distribution=category_type_distribution,
        top_counterparties=top_counterparties,
        regional_distribution=regional_distribution,
        source_distribution=source_distribution,
        processing_funnel=processing_funnel,
        ai_performance=ai_performance,
        low_confidence_items=low_confidence_items,
        activity_heatmap=activity_heatmap,
        status_timeline=status_timeline,
        confidence_scatter=confidence_scatter,
        regular_payments=regular_payments_summary,
        exhibitions=exhibitions
    )


# ==================== Account Grouping ====================

@router.get("/account-grouping", response_model=AccountGroupingList)
def get_account_grouping(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get transactions grouped by account number."""

    # Parse enum values (handle empty strings)
    parsed_transaction_type = None
    parsed_status = None

    if transaction_type and transaction_type.strip():
        try:
            parsed_transaction_type = BankTransactionTypeEnum(transaction_type)
        except ValueError:
            pass

    if status and status.strip():
        try:
            parsed_status = BankTransactionStatusEnum(status)
        except ValueError:
            pass

    # Base query
    query = db.query(BankTransaction).filter(BankTransaction.is_active == True)

    # Apply filters
    if date_from:
        query = query.filter(BankTransaction.transaction_date >= date_from)
    if date_to:
        query = query.filter(BankTransaction.transaction_date <= date_to)
    if parsed_transaction_type:
        query = query.filter(BankTransaction.transaction_type == parsed_transaction_type)
    if parsed_status:
        query = query.filter(BankTransaction.status == parsed_status)

    # Group by account number, organization, and bank
    accounts_data = db.query(
        BankTransaction.account_number,
        BankTransaction.organization_id,
        BankTransaction.our_bank_name,
        BankTransaction.our_bank_bik,
        func.count(BankTransaction.id).label('total_count'),
        func.sum(
            case((BankTransaction.transaction_type == BankTransactionTypeEnum.CREDIT, 1), else_=0)
        ).label('credit_count'),
        func.sum(
            case((BankTransaction.transaction_type == BankTransactionTypeEnum.DEBIT, 1), else_=0)
        ).label('debit_count'),
        func.sum(
            case(
                (BankTransaction.transaction_type == BankTransactionTypeEnum.CREDIT, BankTransaction.amount),
                else_=0
            )
        ).label('total_credit_amount'),
        func.sum(
            case(
                (BankTransaction.transaction_type == BankTransactionTypeEnum.DEBIT, BankTransaction.amount),
                else_=0
            )
        ).label('total_debit_amount'),
        func.sum(
            case(
                (BankTransaction.status.in_([BankTransactionStatusEnum.NEW, BankTransactionStatusEnum.NEEDS_REVIEW]), 1),
                else_=0
            )
        ).label('needs_processing_count'),
        func.sum(
            case((BankTransaction.status == BankTransactionStatusEnum.APPROVED, 1), else_=0)
        ).label('approved_count'),
        func.max(BankTransaction.transaction_date).label('last_transaction_date')
    ).filter(
        BankTransaction.is_active == True
    )

    # Apply same filters to grouping query
    if date_from:
        accounts_data = accounts_data.filter(BankTransaction.transaction_date >= date_from)
    if date_to:
        accounts_data = accounts_data.filter(BankTransaction.transaction_date <= date_to)
    if parsed_transaction_type:
        accounts_data = accounts_data.filter(BankTransaction.transaction_type == parsed_transaction_type)
    if parsed_status:
        accounts_data = accounts_data.filter(BankTransaction.status == parsed_status)

    accounts_data = accounts_data.group_by(
        BankTransaction.account_number,
        BankTransaction.organization_id,
        BankTransaction.our_bank_name,
        BankTransaction.our_bank_bik
    ).order_by(func.max(BankTransaction.transaction_date).desc()).all()

    # Get organization names
    org_ids = [acc.organization_id for acc in accounts_data if acc.organization_id]
    orgs = {}
    if org_ids:
        org_list = db.query(Organization).filter(Organization.id.in_(org_ids)).all()
        orgs = {org.id: org.name for org in org_list}

    # Build result
    accounts = []
    for acc in accounts_data:
        accounts.append(AccountGrouping(
            account_number=acc.account_number or "Не указан",
            organization_id=acc.organization_id,
            organization_name=orgs.get(acc.organization_id) if acc.organization_id else None,
            our_bank_name=acc.our_bank_name,
            our_bank_bik=acc.our_bank_bik,
            total_count=acc.total_count or 0,
            credit_count=acc.credit_count or 0,
            debit_count=acc.debit_count or 0,
            total_credit_amount=acc.total_credit_amount or Decimal("0"),
            total_debit_amount=acc.total_debit_amount or Decimal("0"),
            balance=(acc.total_credit_amount or Decimal("0")) - (acc.total_debit_amount or Decimal("0")),
            needs_processing_count=acc.needs_processing_count or 0,
            approved_count=acc.approved_count or 0,
            last_transaction_date=acc.last_transaction_date
        ))

    return AccountGroupingList(
        accounts=accounts,
        total_accounts=len(accounts)
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
    """Hard delete transaction (physically removes from database)."""
    transaction = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    # Physical delete from database
    db.delete(transaction)
    db.commit()

    return {"message": "Transaction deleted"}


@router.post("/bulk-delete")
def bulk_delete_transactions(
    transaction_ids: List[int],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Bulk delete transactions - physically removes from database (ADMIN and MANAGER only)."""
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

    # Physical delete all
    deleted_count = 0
    for tx in transactions:
        db.delete(tx)
        deleted_count += 1

    db.commit()

    return {"message": f"Successfully deleted {deleted_count} transactions", "deleted": deleted_count}


@router.post("/delete-by-filter")
def delete_by_filter(
    status_filter: Optional[BankTransactionStatusEnum] = None,
    transaction_type: Optional[BankTransactionTypeEnum] = None,
    payment_source: Optional[str] = None,
    account_number: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete all transactions matching filters (ADMIN only)."""
    if current_user.role != UserRoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMIN can delete transactions by filter"
        )

    # Build query with filters
    query = db.query(BankTransaction).filter(BankTransaction.is_active == True)

    # Apply filters (same as get_bank_transactions)
    if status_filter:
        query = query.filter(BankTransaction.status == status_filter)

    if transaction_type:
        query = query.filter(BankTransaction.transaction_type == transaction_type)

    if payment_source:
        query = query.filter(BankTransaction.payment_source == payment_source)

    if account_number:
        if account_number == "Не указан":
            query = query.filter(BankTransaction.account_number.is_(None))
        else:
            query = query.filter(BankTransaction.account_number == account_number)

    if date_from:
        query = query.filter(BankTransaction.transaction_date >= date_from)
    if date_to:
        query = query.filter(BankTransaction.transaction_date <= date_to)

    if category_id is not None:
        if category_id == 0 or str(category_id).lower() == 'null':
            query = query.filter(BankTransaction.category_id.is_(None))
        else:
            query = query.filter(BankTransaction.category_id == category_id)

    if organization_id:
        query = query.filter(BankTransaction.organization_id == organization_id)

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

    # Get count before deletion
    total_count = query.count()

    if total_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transactions found matching the filters"
        )

    # Physical delete all matching transactions
    deleted_count = query.delete(synchronize_session=False)

    db.commit()

    return {
        "message": f"Successfully deleted {deleted_count} transactions",
        "deleted": deleted_count
    }


# ==================== Categorization ====================

@router.put("/{transaction_id}/categorize", response_model=CategorizationWithSuggestionsResponse)
def categorize_transaction(
    transaction_id: int,
    categorize_data: BankTransactionCategorize,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Assign category to transaction and return rule suggestions."""
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

    # Анализируем возможность создания правил
    rule_suggestions = analyze_rule_suggestions([transaction], categorize_data.category_id, db)

    # Формируем ответ с транзакцией
    t_dict = BankTransactionResponse.model_validate(transaction).model_dump()
    t_dict['category_name'] = category.name
    t_dict['organization_name'] = transaction.organization_rel.name if transaction.organization_rel else None
    t_dict['suggested_category_name'] = transaction.suggested_category_rel.name if transaction.suggested_category_rel else None

    return CategorizationWithSuggestionsResponse(
        transaction=BankTransactionResponse(**t_dict),
        rule_suggestions=rule_suggestions
    )


@router.post("/bulk-categorize", response_model=BulkCategorizationWithSuggestionsResponse)
def bulk_categorize(
    bulk_data: BankTransactionBulkCategorize,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Bulk assign category to multiple transactions and return rule suggestions."""
    # Verify category exists
    category = db.query(BudgetCategory).filter(
        BudgetCategory.id == bulk_data.category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found"
        )

    # Получаем все транзакции для обновления
    transactions = db.query(BankTransaction).filter(
        BankTransaction.id.in_(bulk_data.transaction_ids),
        BankTransaction.is_active == True
    ).all()

    updated_count = 0
    for transaction in transactions:
        transaction.category_id = bulk_data.category_id
        transaction.status = BankTransactionStatusEnum.CATEGORIZED
        transaction.reviewed_by = current_user.id
        transaction.reviewed_at = datetime.utcnow()
        updated_count += 1

    db.commit()

    # Анализируем возможность создания правил на основе всех транзакций
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"🔍 Bulk categorize: {updated_count} transactions categorized")
    rule_suggestions = analyze_rule_suggestions(transactions, bulk_data.category_id, db)

    response = BulkCategorizationWithSuggestionsResponse(
        updated_count=updated_count,
        message=f"Категоризировано {updated_count} операций",
        rule_suggestions=rule_suggestions
    )

    logger.info(f"📦 Returning response with {len(rule_suggestions.suggestions)} suggestions")

    return response


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


@router.post("/create-rule-from-suggestion")
def create_rule_from_suggestion(
    request: CreateRuleFromSuggestionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Создаёт правило категоризации на основе выбора пользователя.
    """
    # Проверяем, что категория существует
    category = db.query(BudgetCategory).filter(
        BudgetCategory.id == request.category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Категория с id {request.category_id} не найдена"
        )

    # Конвертируем строковый тип в enum
    try:
        rule_type_enum = CategorizationRuleTypeEnum(request.rule_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неверный тип правила: {request.rule_type}"
        )

    # Проверяем, нет ли уже такого правила
    existing_rule_query = db.query(CategorizationRule).filter(
        CategorizationRule.rule_type == rule_type_enum,
        CategorizationRule.category_id == request.category_id,
        CategorizationRule.is_active == True
    )

    if rule_type_enum == CategorizationRuleTypeEnum.COUNTERPARTY_INN:
        existing_rule_query = existing_rule_query.filter(
            CategorizationRule.counterparty_inn == request.match_value
        )
    elif rule_type_enum == CategorizationRuleTypeEnum.COUNTERPARTY_NAME:
        existing_rule_query = existing_rule_query.filter(
            CategorizationRule.counterparty_name == request.match_value
        )
    elif rule_type_enum == CategorizationRuleTypeEnum.BUSINESS_OPERATION:
        existing_rule_query = existing_rule_query.filter(
            CategorizationRule.business_operation == request.match_value
        )
    elif rule_type_enum == CategorizationRuleTypeEnum.KEYWORD:
        existing_rule_query = existing_rule_query.filter(
            CategorizationRule.keyword == request.match_value
        )

    existing_rule = existing_rule_query.first()
    if existing_rule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Такое правило уже существует"
        )

    # Создаём правило
    new_rule = create_categorization_rule_from_suggestion(
        rule_type=rule_type_enum,
        match_value=request.match_value,
        category_id=request.category_id,
        user_id=current_user.id,
        priority=request.priority,
        confidence=request.confidence,
        db=db
    )

    if request.notes:
        new_rule.notes = request.notes

    db.commit()
    db.refresh(new_rule)

    # Применяем правило к существующим транзакциям, если requested
    applied_count = 0
    if request.apply_to_existing:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 Applying rule to existing transactions...")

        # Формируем запрос для поиска подходящих транзакций
        matching_query = db.query(BankTransaction).filter(
            BankTransaction.is_active == True,
            # Только транзакции без категории или с низкой уверенностью
            or_(
                BankTransaction.category_id == None,
                BankTransaction.status == BankTransactionStatusEnum.NEEDS_REVIEW
            )
        )

        # Добавляем фильтр в зависимости от типа правила
        if rule_type_enum == CategorizationRuleTypeEnum.COUNTERPARTY_INN:
            matching_query = matching_query.filter(
                BankTransaction.counterparty_inn == request.match_value
            )
        elif rule_type_enum == CategorizationRuleTypeEnum.COUNTERPARTY_NAME:
            matching_query = matching_query.filter(
                BankTransaction.counterparty_name == request.match_value
            )
        elif rule_type_enum == CategorizationRuleTypeEnum.BUSINESS_OPERATION:
            matching_query = matching_query.filter(
                BankTransaction.business_operation == request.match_value
            )
        elif rule_type_enum == CategorizationRuleTypeEnum.KEYWORD:
            matching_query = matching_query.filter(
                BankTransaction.payment_purpose.ilike(f"%{request.match_value}%")
            )

        matching_transactions = matching_query.all()
        logger.info(f"📋 Found {len(matching_transactions)} matching transactions")

        # Применяем категорию
        for tx in matching_transactions:
            tx.category_id = request.category_id
            tx.status = BankTransactionStatusEnum.CATEGORIZED
            tx.category_confidence = request.confidence
            tx.reviewed_by = current_user.id
            tx.reviewed_at = datetime.utcnow()
            applied_count += 1

        db.commit()
        logger.info(f"✅ Applied category to {applied_count} transactions")

    return {
        "success": True,
        "message": f"Правило создано{' и применено к ' + str(applied_count) + ' операциям' if applied_count > 0 else ''}",
        "rule_id": new_rule.id,
        "rule_type": new_rule.rule_type.value,
        "category_name": category.name,
        "applied_count": applied_count
    }


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

    suggestions = classifier.get_category_suggestions(
        payment_purpose=transaction.payment_purpose,
        counterparty_name=transaction.counterparty_name,
        counterparty_inn=transaction.counterparty_inn,
        amount=float(transaction.amount) if transaction.amount else 0,
        transaction_type=transaction.transaction_type.value if transaction.transaction_type else None,
        top_n=5
    )

    result = []
    for s in suggestions:
        category = db.query(BudgetCategory).filter(BudgetCategory.id == s['category_id']).first()
        if category:
            # reasoning может быть списком - преобразуем в строку
            reasoning = s.get('reasoning')
            if isinstance(reasoning, list):
                reasoning = ', '.join(reasoning) if reasoning else None

            result.append(CategorySuggestion(
                category_id=s['category_id'],
                category_name=category.name,
                confidence=s['confidence'],
                reasoning=reasoning
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


# ==================== Similar Transactions ====================

@router.get("/{transaction_id}/similar", response_model=List[BankTransactionResponse])
def get_similar_transactions(
    transaction_id: int,
    similarity_threshold: float = Query(0.5, description="Similarity threshold (0-1)"),
    limit: int = Query(1000, description="Maximum number of similar transactions to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Find similar transactions based on counterparty, purpose, and amount."""
    # Get the source transaction
    source_transaction = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id,
        BankTransaction.is_active == True
    ).first()

    if not source_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    # Build query for similar transactions
    query = db.query(BankTransaction).options(
        joinedload(BankTransaction.category_rel),
        joinedload(BankTransaction.organization_rel),
        joinedload(BankTransaction.suggested_category_rel)
    ).filter(
        BankTransaction.is_active == True,
        BankTransaction.id != transaction_id,
        BankTransaction.category_id == None  # Только не категоризированные
    )

    # Стоп-слова и общие банковские термины, которые не следует использовать для поиска
    stop_words = {
        # Предлоги и союзы
        'для', 'при', 'или', 'без', 'под', 'над', 'перед', 'после',
        'через', 'между', 'среди', 'вместо', 'кроме', 'около', 'вдоль',
        # Общие банковские термины
        'оплата', 'плата', 'платеж', 'счет', 'счёт', 'счету', 'договор',
        'договору', 'номер', 'дата', 'период', 'услуги', 'услуг',
        'работы', 'работ', 'товар', 'товара', 'товаров', 'включая',
        'также', 'всего', 'итого', 'сумма', 'сумму', 'рублей', 'рубль',
        'копеек', 'копейка', 'безналичный', 'наличный', 'перевод',
        'перечисление', 'возврат', 'аванс', 'предоплата', 'доплата',
        'комиссия', 'комис', 'пополнение', 'списание', 'зачисление',
        # НДС и налоги
        'числе', 'число', 'включительно', 'облагается', 'ставка',
        # Документы
        'документ', 'основание', 'назначение', 'платежа',
        # Даты
        'январь', 'февраль', 'март', 'апрель', 'июнь', 'июль',
        'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь',
        # Банковские операции
        'операции', 'операция', 'банк', 'банка', 'расчетный', 'расчётный',
        'корреспондентский', 'транзакция', 'межбанк', 'межбанковский',
    }

    # Паттерны банковских комиссий и служебных операций для исключения
    commission_patterns = [
        'комис%',
        'пополнение по операции сбп%',
        'плата за пакет%',
        'плата за обслуживание%',
        'плата за предоставление услуги%',
        'плата за пополнение%',
        'погашение задолженности по договору%',
        'межбанки%',
        'sms-банк%',
        'sms банк%',
        'смс-банк%',
        'смс банк%',
    ]

    # Исключаем банковские комиссии из результатов поиска
    # Важно: учитываем NULL значения payment_purpose (они не должны исключаться)
    for pattern in commission_patterns:
        query = query.filter(
            or_(
                BankTransaction.payment_purpose.is_(None),
                ~BankTransaction.payment_purpose.ilike(pattern)
            )
        )

    # Стратегия поиска: объединяем контрагента, business_operation и ключевые слова через OR
    search_conditions = []

    # 1. Поиск по контрагенту (ИНН или имя)
    if source_transaction.counterparty_inn:
        # По ИНН - точное совпадение
        search_conditions.append(BankTransaction.counterparty_inn == source_transaction.counterparty_inn)

    if source_transaction.counterparty_name:
        # По имени - используем ilike для более мягкого поиска
        name_parts = source_transaction.counterparty_name.strip().split()
        if name_parts:
            # Точное совпадение по имени
            search_conditions.append(BankTransaction.counterparty_name.ilike(source_transaction.counterparty_name))
            # Поиск по фамилии (первое слово имени, если >= 3 символов)
            if len(name_parts[0]) >= 3:
                search_conditions.append(BankTransaction.counterparty_name.ilike(f"{name_parts[0]}%"))

    # 2. Поиск по business_operation (хозяйственной операции) - ВСЕГДА если есть
    if source_transaction.business_operation:
        search_conditions.append(BankTransaction.business_operation == source_transaction.business_operation)

    # 3. Поиск по ключевым словам из назначения платежа (если нет других критериев)
    if not search_conditions and source_transaction.payment_purpose:
        # Извлекаем значимые ключевые слова (минимум 5 символов, не стоп-слова)
        words = source_transaction.payment_purpose.lower().split()
        keywords = [
            word.strip('.,;:!?()[]{}"\'-')
            for word in words
            if len(word) >= 5 and word.lower().strip('.,;:!?()[]{}"\'-') not in stop_words
        ]

        # Берём только уникальные слова длиной >= 6 символов для более точного поиска
        significant_keywords = list(set([kw for kw in keywords if len(kw) >= 6]))[:3]

        if significant_keywords:
            # Создаём условие: все ключевые слова должны присутствовать
            keyword_conditions = [BankTransaction.payment_purpose.ilike(f"%{kw}%") for kw in significant_keywords]
            if keyword_conditions:
                search_conditions.append(and_(*keyword_conditions))

    # Применяем все условия через OR (любое совпадение)
    if search_conditions:
        query = query.filter(or_(*search_conditions))

    # Фильтр по типу транзакции
    query = query.filter(BankTransaction.transaction_type == source_transaction.transaction_type)

    # Order by date and limit
    similar_transactions = query.order_by(
        BankTransaction.transaction_date.desc()
    ).limit(limit).all()

    # Format response
    result = []
    for t in similar_transactions:
        t_dict = BankTransactionResponse.model_validate(t).model_dump()
        t_dict['category_name'] = t.category_rel.name if t.category_rel else None
        t_dict['organization_name'] = t.organization_rel.name if t.organization_rel else None
        t_dict['suggested_category_name'] = t.suggested_category_rel.name if t.suggested_category_rel else None
        result.append(BankTransactionResponse(**t_dict))

    return result


class ApplyCategoryToSimilarRequest(BaseModel):
    """Request to apply category to similar transactions."""
    category_id: int
    apply_to_transaction_ids: Optional[List[int]] = None


@router.post("/{transaction_id}/apply-category-to-similar")
def apply_category_to_similar(
    transaction_id: int,
    request: ApplyCategoryToSimilarRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Apply category to the transaction and optionally to similar transactions."""
    # Get the source transaction
    source_transaction = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id,
        BankTransaction.is_active == True
    ).first()

    if not source_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    # Verify category exists
    category = db.query(BudgetCategory).filter(
        BudgetCategory.id == request.category_id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found"
        )

    # Apply category to source transaction
    source_transaction.category_id = request.category_id
    source_transaction.status = BankTransactionStatusEnum.CATEGORIZED
    source_transaction.updated_at = datetime.utcnow()

    # Collect all transactions for rule analysis
    all_transactions = [source_transaction]

    # Apply to similar transactions if specified
    updated_count = 1
    if request.apply_to_transaction_ids:
        similar_txs = db.query(BankTransaction).filter(
            BankTransaction.id.in_(request.apply_to_transaction_ids),
            BankTransaction.is_active == True
        ).all()

        for tx in similar_txs:
            tx.category_id = request.category_id
            tx.status = BankTransactionStatusEnum.CATEGORIZED
            tx.updated_at = datetime.utcnow()
            updated_count += 1
            all_transactions.append(tx)

    db.commit()

    # Analyze rule suggestions based on ALL categorized transactions
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 Apply to similar: analyzing {len(all_transactions)} transactions for rule suggestions")

    rule_suggestions = analyze_rule_suggestions(all_transactions, request.category_id, db)

    return {
        "message": f"Категория применена к {updated_count} операциям",
        "updated_count": updated_count,
        "category_id": category.id,
        "category_name": category.name,
        "rule_suggestions": rule_suggestions
    }
