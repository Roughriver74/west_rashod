"""
Transaction Classifier - Rule-based only

Классифицирует транзакции ТОЛЬКО по существующим правилам:
1. BusinessOperationMapping - маппинг ХозяйственнаяОперация из 1С
2. CategorizationRule - правила по ИНН, имени контрагента, ключевым словам
3. Исторические данные - если контрагент с таким ИНН уже категоризировался

Если правила нет - транзакция остаётся без категории (status = NEW)
"""
from typing import Optional, Tuple, List, Dict
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import (
    BankTransaction,
    BudgetCategory,
    BusinessOperationMapping,
    CategorizationRule,
    CategorizationRuleTypeEnum,
)


class TransactionClassifier:
    """
    Rule-based classifier for bank transactions.

    Uses ONLY existing rules from database:
    - BusinessOperationMapping (from 1C)
    - CategorizationRule (user-defined)
    - Historical data (same counterparty INN)

    If no rule matches - returns None (transaction stays uncategorized)
    """

    # Minimum transactions for historical matching
    MIN_HISTORICAL_TRANSACTIONS = 3

    # Confidence levels
    CONFIDENCE_BUSINESS_OP = 0.98  # BusinessOperationMapping
    CONFIDENCE_BANK_COMMISSION = 0.80  # Bank commission detection (low to prevent auto-apply)
    CONFIDENCE_RULE_INN = 0.95     # CategorizationRule by INN
    CONFIDENCE_RULE_NAME = 0.90   # CategorizationRule by name
    CONFIDENCE_RULE_KEYWORD = 0.85  # CategorizationRule by keyword
    CONFIDENCE_HISTORICAL = 0.92   # Historical data

    # Keywords for detecting bank commissions (lowercase)
    BANK_COMMISSION_KEYWORDS = [
        'комисс',  # Комиссия, комисс
        'плата за',  # Плата за обслуживание
        'commission',
        'fee',
        'sms',  # СМС-уведомления
        'обслуживание счета',
        'обслуживание карты',
    ]

    def __init__(self, db: Session):
        self.db = db
        # Кэшируем все правила категоризации при инициализации
        self._rules_cache = self._load_rules_cache()

    def _load_rules_cache(self) -> Dict[str, List]:
        """
        Загружает все активные правила категоризации в память для быстрого доступа.
        Это значительно ускоряет классификацию, избегая повторных SQL-запросов.
        """
        cache = {
            'business_operations': {},  # Dict[business_operation, rule]
            'inn': {},                   # Dict[inn, rule]
            'names': [],                 # List[rule] - для частичного совпадения
            'keywords': [],              # List[rule] - для поиска по ключевым словам
        }

        try:
            # Загружаем все активные правила одним запросом
            all_rules = self.db.query(CategorizationRule).filter(
                CategorizationRule.is_active == True,
                CategorizationRule.category_id.isnot(None)
            ).order_by(CategorizationRule.priority.desc()).all()

            for rule in all_rules:
                if rule.rule_type == CategorizationRuleTypeEnum.BUSINESS_OPERATION and rule.business_operation:
                    # Для бизнес-операций берем правило с наивысшим приоритетом
                    if rule.business_operation not in cache['business_operations']:
                        cache['business_operations'][rule.business_operation] = rule

                elif rule.rule_type == CategorizationRuleTypeEnum.COUNTERPARTY_INN and rule.counterparty_inn:
                    # Для ИНН берем правило с наивысшим приоритетом
                    if rule.counterparty_inn not in cache['inn']:
                        cache['inn'][rule.counterparty_inn] = rule

                elif rule.rule_type == CategorizationRuleTypeEnum.COUNTERPARTY_NAME and rule.counterparty_name:
                    cache['names'].append(rule)

                elif rule.rule_type == CategorizationRuleTypeEnum.KEYWORD and rule.keyword:
                    cache['keywords'].append(rule)

            # Также загружаем BusinessOperationMapping одним запросом
            mappings = self.db.query(BusinessOperationMapping).filter(
                BusinessOperationMapping.is_active == True,
                BusinessOperationMapping.category_id.isnot(None)
            ).all()

            cache['business_operation_mappings'] = {
                m.business_operation: m for m in mappings
            }

        except Exception as e:
            # Если не удалось загрузить кэш, логируем ошибку
            # но не падаем - методы смогут работать без кэша
            print(f"Warning: Failed to load rules cache: {e}")

        return cache

    def classify(
        self,
        payment_purpose: Optional[str],
        counterparty_name: Optional[str],
        counterparty_inn: Optional[str],
        amount: Decimal,
        transaction_type: Optional[str] = None,
        business_operation: Optional[str] = None
    ) -> Tuple[Optional[int], float, str, bool]:
        """
        Classify transaction using existing rules and AI heuristics.

        Args:
            payment_purpose: Payment description text
            counterparty_name: Counterparty name
            counterparty_inn: Counterparty INN
            amount: Transaction amount
            transaction_type: DEBIT (expense) or CREDIT (income)
            business_operation: ХозяйственнаяОперация from 1C

        Returns:
            - category_id: Category ID or None if no rule matches
            - confidence: Confidence score 0.0-1.0
            - reasoning: Human-readable explanation
            - is_rule_based: True if categorized by explicit rule (auto-apply),
                            False if by AI heuristics (suggestion only)
        """
        # 1. BusinessOperationMapping (highest priority - from 1C) - RULE
        if business_operation:
            result = self._match_business_operation(business_operation)
            if result:
                return result

        # 2. PRIORITY: Check for bank commissions (before other rules!) - AI HEURISTIC
        # Bank commissions should NOT use historical data from the same bank INN
        if payment_purpose:
            result = self._detect_bank_commission(payment_purpose)
            if result:
                return result

        # 3. CategorizationRule by INN (exact match) - RULE
        if counterparty_inn:
            result = self._match_rule_by_inn(counterparty_inn)
            if result:
                return result

        # 4. CategorizationRule by counterparty name - RULE
        if counterparty_name:
            result = self._match_rule_by_name(counterparty_name)
            if result:
                return result

        # 5. CategorizationRule by keyword in payment purpose - RULE
        if payment_purpose:
            result = self._match_rule_by_keyword(payment_purpose)
            if result:
                return result

        # 6. Historical data - same INN was categorized before - AI HEURISTIC
        # Now runs AFTER commission check to avoid false matches
        if counterparty_inn:
            result = self._match_historical(counterparty_inn, transaction_type)
            if result:
                return result

        # No rule matched - return None (transaction stays uncategorized)
        return None, 0.0, "Нет подходящего правила категоризации", False

    def _match_business_operation(
        self,
        business_operation: str
    ) -> Optional[Tuple[int, float, str, bool]]:
        """Match by BusinessOperationMapping (ХозяйственнаяОперация from 1C) - RULE"""
        # Проверяем кэш BusinessOperationMapping
        mapping = self._rules_cache.get('business_operation_mappings', {}).get(business_operation)

        if mapping and mapping.category_id:
            confidence = float(mapping.confidence) if mapping.confidence else self.CONFIDENCE_BUSINESS_OP
            return (
                mapping.category_id,
                confidence,
                f"Маппинг ХозяйственнаяОперация: '{business_operation}'",
                True  # is_rule_based
            )

        # Если не нашли в BusinessOperationMapping, проверяем CategorizationRule из кэша
        rule = self._rules_cache.get('business_operations', {}).get(business_operation)

        if rule and rule.category_id:
            confidence = float(rule.confidence) if rule.confidence else self.CONFIDENCE_BUSINESS_OP
            return (
                rule.category_id,
                confidence,
                f"Правило по бизнес-операции: '{business_operation}'",
                True  # is_rule_based
            )

        return None

    def _match_rule_by_inn(
        self,
        counterparty_inn: str
    ) -> Optional[Tuple[int, float, str, bool]]:
        """Match by CategorizationRule with INN - RULE"""
        # Ищем в кэше (уже отсортированы по приоритету)
        rule = self._rules_cache.get('inn', {}).get(counterparty_inn)

        if rule:
            confidence = float(rule.confidence) if rule.confidence else self.CONFIDENCE_RULE_INN
            return (
                rule.category_id,
                confidence,
                f"Правило по ИНН контрагента: {counterparty_inn}",
                True  # is_rule_based
            )
        return None

    def _match_rule_by_name(
        self,
        counterparty_name: str
    ) -> Optional[Tuple[int, float, str, bool]]:
        """Match by CategorizationRule with counterparty name (partial match) - RULE"""
        name_lower = counterparty_name.lower()

        # Используем кэш (правила уже отсортированы по приоритету)
        rules = self._rules_cache.get('names', [])

        for rule in rules:
            rule_name = rule.counterparty_name.lower()
            # Check if rule name is contained in counterparty name or vice versa
            if rule_name in name_lower or name_lower in rule_name:
                confidence = float(rule.confidence) if rule.confidence else self.CONFIDENCE_RULE_NAME
                return (
                    rule.category_id,
                    confidence,
                    f"Правило по имени контрагента: '{rule.counterparty_name}'",
                    True  # is_rule_based
                )
        return None

    def _match_rule_by_keyword(
        self,
        payment_purpose: str
    ) -> Optional[Tuple[int, float, str, bool]]:
        """Match by CategorizationRule with keyword in payment purpose - RULE"""
        purpose_lower = payment_purpose.lower()

        # Используем кэш (правила уже отсортированы по приоритету)
        rules = self._rules_cache.get('keywords', [])

        for rule in rules:
            keyword = rule.keyword.lower()
            if keyword in purpose_lower:
                confidence = float(rule.confidence) if rule.confidence else self.CONFIDENCE_RULE_KEYWORD
                return (
                    rule.category_id,
                    confidence,
                    f"Правило по ключевому слову: '{rule.keyword}'",
                    True  # is_rule_based
                )
        return None

    def _detect_bank_commission(
        self,
        payment_purpose: str
    ) -> Optional[Tuple[int, float, str, bool]]:
        """
        Detect bank commissions by keywords in payment purpose - AI HEURISTIC.
        Returns None (no category) with low confidence to prevent auto-categorization.
        This ensures bank commissions are flagged for manual review.
        """
        purpose_lower = payment_purpose.lower()

        for keyword in self.BANK_COMMISSION_KEYWORDS:
            if keyword in purpose_lower:
                # Return None as category_id but with specific reasoning
                # This will cause transaction to stay as NEW/NEEDS_REVIEW
                # and NOT use historical data
                return (
                    None,
                    self.CONFIDENCE_BANK_COMMISSION,
                    f"Обнаружена банковская комиссия (ключевое слово: '{keyword}'). Требует ручной категоризации.",
                    False  # is_rule_based = False (AI heuristic)
                )
        return None

    def _match_historical(
        self,
        counterparty_inn: str,
        transaction_type: Optional[str] = None
    ) -> Optional[Tuple[int, float, str, bool]]:
        """
        Match by historical data - same INN was categorized before - AI HEURISTIC.
        Now also considers transaction_type to avoid mismatches
        (e.g., bank commissions vs payments from the same bank).
        """
        # Build query with optional transaction_type filter
        query = self.db.query(
            BankTransaction.category_id,
            BudgetCategory.name,
            func.count(BankTransaction.id).label('count')
        ).join(
            BudgetCategory,
            BankTransaction.category_id == BudgetCategory.id
        ).filter(
            BankTransaction.counterparty_inn == counterparty_inn,
            BankTransaction.category_id.isnot(None),
            BankTransaction.is_active == True,
            # Only use approved or manually categorized transactions
            BankTransaction.status.in_(['APPROVED', 'CATEGORIZED'])
        )

        # IMPORTANT: Filter by transaction_type if provided
        # This prevents mixing DEBIT (expenses) and CREDIT (income) categories
        if transaction_type:
            query = query.filter(BankTransaction.transaction_type == transaction_type)

        result = query.group_by(
            BankTransaction.category_id,
            BudgetCategory.name
        ).order_by(
            func.count(BankTransaction.id).desc()
        ).first()

        if result and result.count >= self.MIN_HISTORICAL_TRANSACTIONS:
            type_note = f" (тип: {transaction_type})" if transaction_type else ""
            return (
                result.category_id,
                self.CONFIDENCE_HISTORICAL,
                f"Исторические данные: ИНН {counterparty_inn}{type_note} → '{result.name}' ({result.count} транзакций)",
                False  # is_rule_based = False (AI heuristic)
            )
        return None

    def get_category_suggestions(
        self,
        payment_purpose: Optional[str],
        counterparty_name: Optional[str],
        counterparty_inn: Optional[str],
        amount: Decimal,
        transaction_type: Optional[str] = None,
        top_n: int = 3
    ) -> List[Dict]:
        """
        Get category suggestions (for UI dropdown).
        Returns suggestions based on existing rules only.
        """
        suggestions = []

        # Historical data (now considers transaction_type for better accuracy)
        if counterparty_inn:
            hist = self._match_historical(counterparty_inn, transaction_type)
            if hist:
                cat_id, conf, reason = hist
                cat = self.db.query(BudgetCategory).filter(BudgetCategory.id == cat_id).first()
                if cat:
                    suggestions.append({
                        'category_id': cat_id,
                        'category_name': cat.name,
                        'confidence': conf,
                        'reasoning': [reason]
                    })

        # Deduplicate and limit
        seen = set()
        unique = []
        for s in suggestions:
            if s['category_id'] not in seen:
                seen.add(s['category_id'])
                unique.append(s)

        return unique[:top_n]


class RegularPaymentDetector:
    """Detect regular payments (subscriptions, rent, etc.)"""

    def __init__(self, db: Session):
        self.db = db

    def detect_patterns(self) -> List[Dict]:
        """Detect regular payment patterns"""
        patterns = []

        # Group by counterparty INN
        transactions_by_inn = self.db.query(
            BankTransaction.counterparty_inn,
            BankTransaction.counterparty_name,
            BankTransaction.category_id,
            func.count(BankTransaction.id).label('count'),
            func.avg(BankTransaction.amount).label('avg_amount'),
            func.max(BankTransaction.transaction_date).label('last_date')
        ).filter(
            BankTransaction.counterparty_inn.isnot(None),
            BankTransaction.is_active == True,
            BankTransaction.transaction_type == 'DEBIT'
        ).group_by(
            BankTransaction.counterparty_inn,
            BankTransaction.counterparty_name,
            BankTransaction.category_id
        ).having(
            func.count(BankTransaction.id) >= 3
        ).all()

        for group in transactions_by_inn:
            dates = self.db.query(BankTransaction.transaction_date).filter(
                BankTransaction.counterparty_inn == group.counterparty_inn,
                BankTransaction.is_active == True
            ).order_by(BankTransaction.transaction_date).all()

            if len(dates) < 3:
                continue

            date_list = [d.transaction_date for d in dates]
            intervals = []
            for i in range(1, len(date_list)):
                delta = (date_list[i] - date_list[i-1]).days
                intervals.append(delta)

            avg_interval = sum(intervals) / len(intervals)
            interval_std = (sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)) ** 0.5

            # If interval is consistent (low variance), it's a regular payment
            if interval_std < avg_interval * 0.3:
                category = None
                if group.category_id:
                    category = self.db.query(BudgetCategory).filter(
                        BudgetCategory.id == group.category_id
                    ).first()

                patterns.append({
                    'counterparty_inn': group.counterparty_inn,
                    'counterparty_name': group.counterparty_name,
                    'category_id': group.category_id,
                    'category_name': category.name if category else None,
                    'avg_amount': float(group.avg_amount),
                    'frequency_days': int(avg_interval),
                    'last_payment_date': group.last_date.isoformat(),
                    'transaction_count': group.count,
                    'is_monthly': 25 <= avg_interval <= 35,
                    'is_quarterly': 85 <= avg_interval <= 95,
                })

        return patterns

    def mark_regular_payments(self) -> int:
        """Mark transactions as regular payments"""
        patterns = self.detect_patterns()
        marked_count = 0

        for pattern in patterns:
            updated = self.db.query(BankTransaction).filter(
                BankTransaction.counterparty_inn == pattern['counterparty_inn'],
                BankTransaction.is_active == True
            ).update({'is_regular_payment': True})
            marked_count += updated

        self.db.commit()
        return marked_count
