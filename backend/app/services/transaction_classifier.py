"""
AI-powered Transaction Classifier
Automatically suggests categories for bank transactions based on payment purpose and counterparty
"""
from typing import Optional, Tuple, List, Dict
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core import constants
from app.db.models import (
    BankTransaction,
    BudgetCategory,
    ExpenseTypeEnum,
)
from app.services.business_operation_mapper import BusinessOperationMapper


class TransactionClassifier:
    """
    AI-powered classifier for bank transactions
    Uses rule-based system with keyword matching and historical data
    Can be enhanced with ML model in the future
    """

    # Keyword mapping for Russian categories (OPEX)
    OPEX_KEYWORDS = {
        'Аренда помещений': [
            'аренда', 'арендная плата', 'арендные платежи', 'rent', 'rental',
            'помещение', 'офис', 'склад', 'площадь', 'наем помещения'
        ],
        'Услуги связи': [
            'связь', 'интернет', 'телефон', 'мобильная связь', 'телеком',
            'internet', 'telephone', 'mobile', 'сотовая', 'телефония',
            'домен', 'хостинг', 'vpn', 'мтс', 'билайн', 'мегафон', 'теле2'
        ],
        'Канцтовары': [
            'канцтовары', 'канцелярия', 'бумага', 'ручки', 'папки',
            'stationery', 'office supplies', 'офисные принадлежности', 'канцелярские товары'
        ],
        'Коммунальные услуги': [
            'коммунальные', 'электроэнергия', 'электричество', 'вода', 'отопление',
            'utilities', 'electricity', 'water', 'heating', 'свет', 'газ', 'жкх', 'жку'
        ],
        'Программное обеспечение': [
            'по ', 'программное обеспечение', 'лицензия', 'software', 'license',
            'subscription', 'подписка', 'saas', 'облако', 'cloud', 'microsoft',
            'adobe', '1с', 'лицензионное', 'антивирус', 'программы'
        ],
        'Реклама и маркетинг': [
            'реклама', 'маркетинг', 'продвижение', 'advertising', 'marketing',
            'seo', 'контекстная реклама', 'яндекс директ', 'google ads', 'промо',
            'рекламная кампания', 'баннер', 'таргетинг'
        ],
        'Транспортные расходы': [
            'транспорт', 'бензин', 'топливо', 'гсм', 'парковка', 'такси',
            'transport', 'fuel', 'parking', 'taxi', 'uber', 'яндекс такси',
            'авто', 'машина', 'перевозка', 'доставка', 'логистика'
        ],
        'Командировочные расходы': [
            'командировка', 'командировочные', 'бизнес-поездка', 'служебная поездка',
            'business trip', 'travel', 'гостиница', 'отель', 'hotel', 'авиабилет',
            'билет', 'проезд', 'проживание', 'суточные', 'per diem'
        ],
        'Обучение персонала': [
            'обучение', 'тренинг', 'курсы', 'семинар', 'training', 'education',
            'повышение квалификации', 'образование', 'конференция', 'вебинар'
        ],
        'Банковские услуги': [
            'комиссия банка', 'банковская комиссия', 'рко', 'обслуживание счета',
            'bank commission', 'bank fee', 'эквайринг', 'услуги банка', 'банк',
            'комиссия за', 'списание комис', 'плата за обслуживание'
        ],
        'Юридические услуги': [
            'юридические услуги', 'юрист', 'адвокат', 'legal services',
            'нотариус', 'правовые услуги', 'юридическое сопровождение'
        ],
        'Бухгалтерские услуги': [
            'бухгалтерские услуги', 'бухгалтер', 'accounting', '1с обслуживание',
            'отчетность', 'аудит', 'учет', 'бухгалтерия'
        ],
        'Хозяйственные расходы': [
            'хозтовары', 'хозяйственные', 'уборка', 'чистящие средства',
            'моющие средства', 'хозинвентарь', 'расходные материалы'
        ],
    }

    # CAPEX keywords
    CAPEX_KEYWORDS = {
        'Оборудование': [
            'оборудование', 'станок', 'машина', 'equipment', 'hardware',
            'сервер', 'компьютер', 'ноутбук', 'принтер', 'мебель'
        ],
        'Программное обеспечение (CAPEX)': [
            'внедрение', 'разработка по', 'erp', 'crm система',
            'implementation', 'development'
        ],
    }

    # Tax and Payroll keywords
    TAX_KEYWORDS = {
        'Налоги': [
            'налог', 'ндс', 'налог на прибыль', 'tax', 'усн', 'енвд',
            'пени', 'штраф', 'налоговая', 'инспекция', 'фнс'
        ],
        'НДФЛ': [
            'ндфл', 'налог на доходы', 'подоходный налог', 'income tax',
            'налог с зарплаты', 'удержание ндфл'
        ],
        'Страховые взносы': [
            'страховые взносы', 'пфр', 'фсс', 'ффомс', 'пенсионный фонд',
            'social security', 'pension', 'страхование', 'взносы',
            'обязательное страхование', 'соц. страх'
        ],
    }

    # Payroll keywords
    PAYROLL_KEYWORDS = {
        'Зарплата': [
            'зарплата', 'заработная плата', 'оплата труда', 'salary', 'wages',
            'выплата зарплаты', 'фот', 'вознаграждение', 'выплата сотруднику',
            'перечисление зарплаты', 'оклад', 'премия', 'компенсация'
        ],
    }

    # Revenue keywords (доходы) - CREDIT transactions
    REVENUE_KEYWORDS = {
        'Покупатели (приход)': [
            'покупатель', 'customer', 'client', 'клиент',
            'оплата счету по заказу', 'оплата счета', 'оплата по счету',
            'payment for invoice', 'invoice payment', 'order payment',
            'оплата за товар', 'оплата заказа', 'платеж от клиента',
            'поступление от покупателя', 'выручка', 'revenue', 'sales',
            'оплата заказа', 'оплата товара', 'предоплата', 'аванс',
            'поступление', 'приход', 'дохода', 'получение', 'возврат'
        ],
    }

    # Supplier/Vendor keywords (расходы) - DEBIT transactions
    SUPPLIER_KEYWORDS = {
        'Поставщики (расход)': [
            'поставщик', 'supplier', 'vendor', 'продавец',
            'оплата поставщику', 'оплата товара', 'закупка',
            'приобретение', 'покупка', 'оплата за товар',
            'payment to supplier', 'purchase', 'procurement'
        ],
    }

    def __init__(self, db: Session, department_id: Optional[int] = None):
        self.db = db
        self.department_id = department_id

        # Initialize Business Operation Mapper (highest priority)
        self.business_operation_mapper = BusinessOperationMapper(db)

        # Load categories from 1C (database) if department_id is provided
        self._1c_category_cache = {}
        if department_id:
            self._load_1c_categories(department_id)

    def _load_1c_categories(self, department_id: int):
        """
        Load budget categories from database (synced from 1C)
        and build keyword mapping
        """
        # Get all active categories with 1C integration
        categories = self.db.query(BudgetCategory).filter(
            BudgetCategory.department_id == department_id,
            BudgetCategory.is_active == True,
            BudgetCategory.external_id_1c.isnot(None),
            BudgetCategory.is_folder == False  # Only items, not folders
        ).all()

        # Build keyword mapping
        for category in categories:
            # Use category name as primary keyword
            name = category.name.lower()

            # Build keywords from category name
            keywords = [name]

            # Add variations
            # Remove common prefixes/suffixes
            if name.startswith('#'):
                keywords.append(name[1:])

            # Add words from name
            words = name.split()
            if len(words) > 1:
                keywords.extend(words)

            # Store in cache
            self._1c_category_cache[category.id] = {
                'id': category.id,
                'name': category.name,
                'type': category.type,
                'keywords': keywords
            }

        print(f"Loaded {len(self._1c_category_cache)} categories from 1C for department {department_id}")

    def _match_1c_categories(self, text_lower: str) -> Optional[Tuple[int, float, List[str]]]:
        """
        Match text against 1C categories keywords

        Returns:
            (category_id, confidence, matched_keywords) or None
        """
        best_match = None
        best_score = 0
        best_keywords = []

        for cat_id, cat_data in self._1c_category_cache.items():
            matched_keywords = []
            score = 0

            for keyword in cat_data['keywords']:
                keyword_lower = keyword.lower()

                # Exact word match (highest score)
                if f" {keyword_lower} " in f" {text_lower} ":
                    matched_keywords.append(keyword)
                    score += constants.AI_KEYWORD_EXACT_SCORE
                # Starts with keyword
                elif text_lower.startswith(keyword_lower):
                    matched_keywords.append(keyword)
                    score += constants.AI_KEYWORD_START_SCORE
                # Contains keyword
                elif keyword_lower in text_lower:
                    matched_keywords.append(keyword)
                    score += constants.AI_KEYWORD_CONTAINS_SCORE

            # Consider match if at least one keyword matched
            if score > 0 and score > best_score:
                best_score = score
                best_match = cat_id
                best_keywords = matched_keywords

        if best_match and best_score >= constants.AI_MIN_SCORE_THRESHOLD:
            # Calculate confidence (0.0 - 1.0)
            # Score of 10 = 0.9 confidence, 5 = 0.7, etc.
            confidence = min(
                constants.AI_CONFIDENCE_MIN_BASE + (best_score / constants.AI_SCORE_TO_CONFIDENCE_DIVISOR),
                constants.AI_CONFIDENCE_MAX_CAP
            )

            return (best_match, confidence, best_keywords)

        return None

    def classify(
        self,
        payment_purpose: Optional[str],
        counterparty_name: Optional[str],
        counterparty_inn: Optional[str],
        amount: Decimal,
        department_id: int,
        transaction_type: Optional[str] = None,
        business_operation: Optional[str] = None
    ) -> Tuple[Optional[int], float, str]:
        """
        Classify transaction and return (category_id, confidence, reasoning)

        Args:
            payment_purpose: Payment description text
            counterparty_name: Counterparty name
            counterparty_inn: Counterparty INN
            amount: Transaction amount
            department_id: Department ID
            transaction_type: DEBIT (expense) or CREDIT (income)
            business_operation: ХозяйственнаяОперация from 1C (highest priority)

        Returns:
            - category_id: Suggested category ID or None
            - confidence: Confidence score 0.0-1.0
            - reasoning: Human-readable explanation
        """
        # 0. Check business_operation first (HIGHEST PRIORITY - hard mapping from 1C)
        if business_operation:
            category_id = self.business_operation_mapper.get_category_by_business_operation(
                business_operation,
                department_id
            )
            if category_id:
                confidence = self.business_operation_mapper.get_confidence_for_mapping(business_operation, department_id)
                return category_id, confidence, f"Жёсткий маппинг по ХозяйственнаяОперация из 1С: '{business_operation}'"

        # 1. Check historical data (high confidence)
        historical = self._get_historical_category(counterparty_inn, department_id)
        if historical:
            return historical['category_id'], constants.AI_HISTORICAL_CONFIDENCE, f"Исторические данные: контрагент всегда относится к категории '{historical['category_name']}' ({historical['count']} транзакций)"

        # 2. Analyze payment purpose text (with transaction type context)
        if payment_purpose:
            text_based = self._analyze_text(payment_purpose, department_id, transaction_type)
            if text_based:
                return text_based

        # 3. Analyze counterparty name
        if counterparty_name:
            name_based = self._analyze_text(counterparty_name, department_id, transaction_type)
            if name_based:
                category_id, confidence, reasoning = name_based
                return category_id, confidence * constants.AI_NAME_BASED_CONFIDENCE_MULTIPLIER, f"По имени контрагента: {reasoning}"

        # 4. Fallback to default categories based on transaction type
        if transaction_type:
            default_category = self._get_default_category_by_type(transaction_type, department_id)
            if default_category:
                category_id, category_name = default_category
                if transaction_type == 'CREDIT':
                    return category_id, constants.AI_DEFAULT_CREDIT_CONFIDENCE, f"Доход от покупателя (по умолчанию для CREDIT)"
                else:
                    return category_id, constants.AI_DEFAULT_DEBIT_CONFIDENCE, f"Расход на поставщика (по умолчанию для DEBIT)"

        # No match found
        return None, 0.0, "Не удалось автоматически определить категорию"

    def _get_historical_category(
        self,
        counterparty_inn: Optional[str],
        department_id: int
    ) -> Optional[Dict]:
        """
        Get most common category for this counterparty from historical data
        """
        if not counterparty_inn:
            return None

        # Find most common category for this INN
        result = self.db.query(
            BankTransaction.category_id,
            BudgetCategory.name,
            func.count(BankTransaction.id).label('count')
        ).join(
            BudgetCategory,
            BankTransaction.category_id == BudgetCategory.id
        ).filter(
            BankTransaction.counterparty_inn == counterparty_inn,
            BankTransaction.department_id == department_id,
            BankTransaction.category_id.isnot(None),
            BankTransaction.is_active == True
        ).group_by(
            BankTransaction.category_id,
            BudgetCategory.name
        ).order_by(
            func.count(BankTransaction.id).desc()
        ).first()

        if result and result.count >= constants.AI_MIN_HISTORICAL_TRANSACTIONS:
            return {
                'category_id': result.category_id,
                'category_name': result.name,
                'count': result.count
            }

        return None

    def _analyze_text(
        self,
        text: str,
        department_id: int,
        transaction_type: Optional[str] = None
    ) -> Optional[Tuple[int, float, str]]:
        """
        Analyze text and match against keyword dictionaries

        Args:
            text: Text to analyze
            department_id: Department ID
            transaction_type: DEBIT or CREDIT (prioritizes relevant keywords)

        Returns (category_id, confidence, reasoning)
        """
        text_lower = text.lower()

        # PRIORITY 1: Check 1C categories first (if loaded)
        if self._1c_category_cache:
            match_1c = self._match_1c_categories(text_lower)
            if match_1c:
                category_id, confidence, matched_keywords = match_1c
                category_name = self._1c_category_cache[category_id]['name']
                return (
                    category_id,
                    confidence,
                    f"Категория из 1С: '{category_name}' (ключевые слова: {', '.join(matched_keywords[:3])})"
                )

        # PRIORITY 2: Check hardcoded keywords
        # Build keyword groups based on transaction type
        if transaction_type == 'CREDIT':
            # For CREDIT (income), prioritize revenue keywords
            all_keywords = {
                **self.REVENUE_KEYWORDS,
                **self.OPEX_KEYWORDS,
                **self.CAPEX_KEYWORDS,
                **self.TAX_KEYWORDS,
                **self.PAYROLL_KEYWORDS,
                **self.SUPPLIER_KEYWORDS
            }
        elif transaction_type == 'DEBIT':
            # For DEBIT (expense), prioritize supplier and expense keywords
            all_keywords = {
                **self.SUPPLIER_KEYWORDS,
                **self.OPEX_KEYWORDS,
                **self.CAPEX_KEYWORDS,
                **self.TAX_KEYWORDS,
                **self.PAYROLL_KEYWORDS,
                **self.REVENUE_KEYWORDS
            }
        else:
            # No transaction type specified, use all equally
            all_keywords = {
                **self.OPEX_KEYWORDS,
                **self.CAPEX_KEYWORDS,
                **self.TAX_KEYWORDS,
                **self.PAYROLL_KEYWORDS,
                **self.REVENUE_KEYWORDS,
                **self.SUPPLIER_KEYWORDS
            }

        matches = []
        for category_pattern, keywords in all_keywords.items():
            match_count = 0
            matched_keywords = []

            for keyword in keywords:
                if keyword.lower() in text_lower:
                    match_count += 1
                    matched_keywords.append(keyword)

            if match_count > 0:
                # Calculate confidence based on number of matches
                base_confidence = min(
                    constants.AI_CONFIDENCE_MIN_BASE + (match_count * constants.AI_MATCH_COUNT_MULTIPLIER),
                    constants.AI_CONFIDENCE_MAX_CAP
                )

                # Boost confidence if category matches transaction type
                if transaction_type == 'CREDIT' and category_pattern in self.REVENUE_KEYWORDS:
                    base_confidence = min(base_confidence + constants.AI_CREDIT_TYPE_BOOST, constants.AI_CONFIDENCE_MAX_CAP)
                elif transaction_type == 'DEBIT' and category_pattern in self.SUPPLIER_KEYWORDS:
                    base_confidence = min(base_confidence + constants.AI_DEBIT_TYPE_BOOST, constants.AI_CONFIDENCE_MAX_CAP)

                matches.append({
                    'pattern': category_pattern,
                    'count': match_count,
                    'confidence': base_confidence,
                    'keywords': matched_keywords
                })

        if not matches:
            return None

        # Sort by match count and confidence
        matches.sort(key=lambda x: (x['count'], x['confidence']), reverse=True)
        best_match = matches[0]

        # Find category in database by exact name match first
        category = self.db.query(BudgetCategory).filter(
            BudgetCategory.department_id == department_id,
            BudgetCategory.name == best_match['pattern'],
            BudgetCategory.is_active == True
        ).first()

        if not category:
            # Try partial match
            category = self.db.query(BudgetCategory).filter(
                BudgetCategory.department_id == department_id,
                BudgetCategory.name.ilike(f"%{best_match['pattern']}%"),
                BudgetCategory.is_active == True
            ).first()

        if not category:
            # Try to find by keyword match in category name
            categories = self.db.query(BudgetCategory).filter(
                BudgetCategory.department_id == department_id,
                BudgetCategory.is_active == True
            ).all()

            # Find best match
            for cat in categories:
                if any(kw.lower() in cat.name.lower() for kw in best_match['keywords']):
                    category = cat
                    break

        if category:
            reasoning = f"Найдены ключевые слова: {', '.join(best_match['keywords'][:3])}"
            return category.id, best_match['confidence'], reasoning

        return None

    def _get_default_category_by_type(
        self,
        transaction_type: str,
        department_id: int
    ) -> Optional[Tuple[int, str]]:
        """
        Get default category based on transaction type

        Args:
            transaction_type: DEBIT or CREDIT
            department_id: Department ID

        Returns:
            Tuple of (category_id, category_name) or None
        """
        if transaction_type == 'CREDIT':
            # For income, use "Покупатели (приход)"
            category_name = 'Покупатели (приход)'
        elif transaction_type == 'DEBIT':
            # For expenses, use "Поставщики (расход)"
            category_name = 'Поставщики (расход)'
        else:
            return None

        category = self.db.query(BudgetCategory).filter(
            BudgetCategory.department_id == department_id,
            BudgetCategory.name == category_name,
            BudgetCategory.is_active == True
        ).first()

        if category:
            return category.id, category.name

        return None

    def get_category_suggestions(
        self,
        payment_purpose: Optional[str],
        counterparty_name: Optional[str],
        counterparty_inn: Optional[str],
        amount: Decimal,
        department_id: int,
        transaction_type: Optional[str] = None,
        top_n: int = 3
    ) -> List[Dict]:
        """
        Get multiple category suggestions with explanations

        Args:
            payment_purpose: Payment description text
            counterparty_name: Counterparty name
            counterparty_inn: Counterparty INN
            amount: Transaction amount
            department_id: Department ID
            transaction_type: DEBIT or CREDIT
            top_n: Maximum number of suggestions to return

        Returns:
            List of suggestions with category_id, category_name, confidence, reasoning
        """
        suggestions = []

        # Historical data
        historical = self._get_historical_category(counterparty_inn, department_id)
        if historical:
            suggestions.append({
                'category_id': historical['category_id'],
                'category_name': historical['category_name'],
                'confidence': 0.95,
                'reasoning': [f"Исторические данные ({historical['count']} транзакций)"]
            })

        # Text analysis
        if payment_purpose:
            text_result = self._analyze_text(payment_purpose, department_id, transaction_type)
            if text_result:
                cat_id, conf, reason = text_result
                cat = self.db.query(BudgetCategory).filter(BudgetCategory.id == cat_id).first()
                if cat:
                    suggestions.append({
                        'category_id': cat_id,
                        'category_name': cat.name,
                        'confidence': conf,
                        'reasoning': [reason]
                    })

        # Default category based on transaction type
        if transaction_type and len(suggestions) < top_n:
            default_cat = self._get_default_category_by_type(transaction_type, department_id)
            if default_cat:
                cat_id, cat_name = default_cat
                # Only add if not already in suggestions
                if not any(s['category_id'] == cat_id for s in suggestions):
                    if transaction_type == 'CREDIT':
                        suggestions.append({
                            'category_id': cat_id,
                            'category_name': cat_name,
                            'confidence': 0.6,
                            'reasoning': ['Категория по умолчанию для доходов']
                        })
                    else:
                        suggestions.append({
                            'category_id': cat_id,
                            'category_name': cat_name,
                            'confidence': 0.5,
                            'reasoning': ['Категория по умолчанию для расходов']
                        })

        # Deduplicate by category_id
        seen = set()
        unique_suggestions = []
        for sugg in suggestions:
            if sugg['category_id'] not in seen:
                seen.add(sugg['category_id'])
                unique_suggestions.append(sugg)

        # Sort by confidence
        unique_suggestions.sort(key=lambda x: x['confidence'], reverse=True)

        return unique_suggestions[:top_n]


class RegularPaymentDetector:
    """
    Detect regular payments (subscriptions, rent, utilities, etc.)
    """

    def __init__(self, db: Session):
        self.db = db

    def detect_patterns(self, department_id: int) -> List[Dict]:
        """
        Detect regular payment patterns for a department
        Returns list of patterns with frequency and last payment date
        """
        # Find transactions with same counterparty_inn that occur regularly
        from datetime import datetime, timedelta

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
            BankTransaction.department_id == department_id,
            BankTransaction.counterparty_inn.isnot(None),
            BankTransaction.is_active == True,
            BankTransaction.transaction_type == 'DEBIT'
        ).group_by(
            BankTransaction.counterparty_inn,
            BankTransaction.counterparty_name,
            BankTransaction.category_id
        ).having(
            func.count(BankTransaction.id) >= 3  # At least 3 transactions
        ).all()

        for group in transactions_by_inn:
            # Get all transaction dates for this INN
            dates = self.db.query(BankTransaction.transaction_date).filter(
                BankTransaction.counterparty_inn == group.counterparty_inn,
                BankTransaction.department_id == department_id,
                BankTransaction.is_active == True
            ).order_by(BankTransaction.transaction_date).all()

            if len(dates) < 3:
                continue

            # Calculate average days between payments
            date_list = [d.transaction_date for d in dates]
            intervals = []
            for i in range(1, len(date_list)):
                delta = (date_list[i] - date_list[i-1]).days
                intervals.append(delta)

            avg_interval = sum(intervals) / len(intervals)
            interval_std = (sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)) ** 0.5

            # If interval is consistent (low variance), it's a regular payment
            if interval_std < avg_interval * constants.REGULAR_PAYMENT_PATTERN_THRESHOLD:
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
                    'is_monthly': 25 <= avg_interval <= 35,  # ~monthly
                    'is_quarterly': 85 <= avg_interval <= 95,  # ~quarterly
                })

        return patterns

    def mark_regular_payments(self, department_id: int) -> int:
        """
        Mark transactions as regular payments based on detected patterns
        Returns number of transactions marked
        """
        patterns = self.detect_patterns(department_id)
        marked_count = 0

        for pattern in patterns:
            # Mark all transactions from this counterparty as regular
            updated = self.db.query(BankTransaction).filter(
                BankTransaction.counterparty_inn == pattern['counterparty_inn'],
                BankTransaction.department_id == department_id,
                BankTransaction.is_active == True
            ).update({
                'is_regular_payment': True
            })

            marked_count += updated

        self.db.commit()
        return marked_count
