# Анализ недостающего функционала банковских транзакций

**Сравнение:** west_buget_it (оригинал) vs west_rashod (новый проект)

---

## Краткое резюме

Новый проект (west_rashod) имеет **~30-40% функционала** от оригинального проекта. Это упрощённая версия, сфокусированная на базовом управлении транзакциями и AI-классификации.

---

## 1. ОТСУТСТВУЮЩИЕ API ЭНДПОИНТЫ

### 1.1 Связывание с расходами (Expense Linking)

| Эндпоинт | Описание | Приоритет |
|----------|----------|-----------|
| `PUT /bank-transactions/{id}/link` | Привязка транзакции к заявке на расход | Высокий |
| `GET /bank-transactions/{id}/matching-expenses` | Поиск подходящих расходов по сумме/дате | Высокий |
| `POST /bulk-link-transactions` | Массовая привязка транзакций | Средний |

**Оригинальный функционал:**
```python
class MatchingSuggestion(BaseModel):
    expense_id: int
    expense_number: str
    expense_amount: Decimal
    expense_date: date
    matching_score: float  # Алгоритм сопоставления
    match_reasons: List[str]  # Причины совпадения
```

### 1.2 OData интеграция с 1С (Фоновые задачи)

| Эндпоинт | Описание | Приоритет |
|----------|----------|-----------|
| `POST /odata/test-connection` | Тест подключения к 1С OData | Средний |
| `POST /odata/sync` | Запуск фоновой синхронизации | Высокий |
| `GET /odata/sync/status/{task_id}` | Статус фоновой задачи | Высокий |

**Что есть сейчас:**
- Синхронный импорт через `/sync-1c/bank-transactions/sync`

**Что нужно добавить:**
- Асинхронная обработка для больших объёмов данных
- Отслеживание прогресса импорта
- Возможность отмены задачи

### 1.3 Расширенная фильтрация

| Параметр | Описание | Статус |
|----------|----------|--------|
| `account_number` | Фильтр по номеру счёта | Отсутствует |
| `account_is_null` | Транзакции без номера счёта | Отсутствует |
| `has_expense` | Привязанные к расходам | Отсутствует |

### 1.4 Регулярные платежи

| Эндпоинт | Описание | Приоритет |
|----------|----------|-----------|
| `GET /regular-patterns` | Обнаружение паттернов (подписки, аренда) | Средний |

**Функционал в оригинале:**
```python
class RegularPaymentPattern(BaseModel):
    counterparty_inn: Optional[str]
    counterparty_name: Optional[str]
    category_id: int
    avg_amount: Decimal
    frequency_days: int  # Периодичность
    last_payment_date: date
    transaction_count: int
    next_expected_date: Optional[date]  # Прогноз следующего
```

---

## 2. ОТСУТСТВУЮЩИЕ СХЕМЫ ДАННЫХ

### 2.1 Pydantic схемы (Backend)

```python
# === СВЯЗЫВАНИЕ С РАСХОДАМИ ===
class BankTransactionLink(BaseModel):
    expense_id: int
    notes: Optional[str] = None

class MatchingSuggestion(BaseModel):
    expense_id: int
    expense_number: str
    expense_amount: Decimal
    expense_date: date
    expense_category_id: Optional[int]
    expense_contractor_name: Optional[str]
    matching_score: float
    match_reasons: List[str]

class BulkLinkRequest(BaseModel):
    links: List[dict]  # [{"transaction_id": 1, "expense_id": 10}, ...]

# === РЕГУЛЯРНЫЕ ПЛАТЕЖИ ===
class RegularPaymentPattern(BaseModel):
    id: int
    counterparty_inn: Optional[str]
    counterparty_name: Optional[str]
    category_id: int
    category_name: str
    avg_amount: Decimal
    frequency_days: int
    last_payment_date: date
    transaction_count: int

class RegularPaymentSummary(BaseModel):
    counterparty_inn: Optional[str]
    counterparty_name: str
    category_name: str
    avg_amount: Decimal
    amount_variance: Decimal
    payment_count: int
    avg_days_between: Optional[float]
    last_payment_date: date
    next_expected_date: Optional[date]

# === РАСШИРЕННАЯ АНАЛИТИКА ===
class RegionalData(BaseModel):
    region: str  # MOSCOW/SPB/REGIONS/FOREIGN
    transaction_count: int
    total_amount: Decimal
    percent_of_total: float

class SourceDistribution(BaseModel):
    payment_source: str  # BANK or CASH
    year: int
    month: int
    month_name: str
    transaction_count: int
    total_amount: Decimal

class ActivityHeatmapPoint(BaseModel):
    day_of_week: int  # 0=Monday ... 6=Sunday
    hour: int
    transaction_count: int
    total_amount: Decimal
    avg_amount: Decimal

class StatusTimelinePoint(BaseModel):
    date: date
    new_count: int
    categorized_count: int
    matched_count: int
    approved_count: int
    needs_review_count: int
    ignored_count: int

class ConfidenceScatterPoint(BaseModel):
    transaction_id: int
    transaction_date: date
    counterparty_name: Optional[str]
    amount: Decimal
    category_confidence: Optional[float]
    status: str
    transaction_type: BankTransactionTypeEnum
    is_regular_payment: bool

class ExhibitionData(BaseModel):
    transaction_id: int
    transaction_date: date
    exhibition: str  # Название выставки/мероприятия
    counterparty_name: str
    amount: Decimal
    category_name: Optional[str]
```

### 2.2 TypeScript типы (Frontend)

```typescript
// === СВЯЗЫВАНИЕ С РАСХОДАМИ ===
interface MatchingSuggestion {
  expense_id: number
  expense_number: string
  expense_amount: number
  expense_date: string
  expense_category_id: number | null
  expense_contractor_name: string | null
  matching_score: number
  match_reasons: string[]
}

// === РЕГУЛЯРНЫЕ ПЛАТЕЖИ ===
interface RegularPaymentPattern {
  id: number
  counterparty_inn: string | null
  counterparty_name: string | null
  category_id: number
  category_name: string
  avg_amount: number
  frequency_days: number
  last_payment_date: string
  transaction_count: number
}

// === РАСШИРЕННАЯ АНАЛИТИКА ===
interface RegionalData {
  region: 'MOSCOW' | 'SPB' | 'REGIONS' | 'FOREIGN'
  transaction_count: number
  total_amount: number
  percent_of_total: number
}

interface ActivityHeatmapPoint {
  day_of_week: number
  hour: number
  transaction_count: number
  total_amount: number
  avg_amount: number
}

interface StatusTimelinePoint {
  date: string
  new_count: number
  categorized_count: number
  matched_count: number
  approved_count: number
  needs_review_count: number
  ignored_count: number
}
```

---

## 3. ОТСУТСТВУЮЩИЕ FRONTEND КОМПОНЕНТЫ

### 3.1 Страница аналитики (BankTransactionsAnalyticsPage.tsx)

**Полностью отсутствует страница с:**
- 12+ графиками и диаграммами
- Фильтрами по дате, региону, статусу, типу
- Выбор года/месяца/квартала
- Сравнение с предыдущим периодом
- Экспорт данных

### 3.2 Отсутствующие компоненты графиков

| Компонент | Описание | Библиотека |
|-----------|----------|------------|
| `CashFlowChart.tsx` | График денежного потока (приход/расход) | recharts |
| `DailyFlowChart.tsx` | Ежедневный поток транзакций | recharts |
| `ActivityHeatmapChart.tsx` | Тепловая карта активности (по часам/дням) | recharts |
| `StatusTimelineChart.tsx` | Изменение статусов во времени | recharts |
| `CategoryBreakdownChart.tsx` | Круговая диаграмма по категориям | recharts |
| `CounterpartyAnalysisChart.tsx` | Топ контрагентов (бар-чарт) | recharts |
| `RegionalDistributionChart.tsx` | Распределение по регионам | recharts |
| `ProcessingEfficiencyChart.tsx` | Воронка обработки | recharts |
| `ConfidenceScatterChart.tsx` | Scatter plot: сумма vs уверенность AI | recharts |

### 3.3 Отсутствующие панели

| Компонент | Описание |
|-----------|----------|
| `BankTransactionsKPICards.tsx` | KPI карточки с метриками |
| `TransactionInsightsPanel.tsx` | AI-инсайты и рекомендации |
| `RegularPaymentsInsights.tsx` | Панель регулярных платежей |
| `ExhibitionSpendingInsights.tsx` | Расходы по мероприятиям |
| `ColumnMappingModal.tsx` | Модалка маппинга колонок при импорте |

---

## 4. ОТСУТСТВУЮЩИЕ ПОЛЯ В МОДЕЛИ ДАННЫХ

### 4.1 Таблица bank_transactions

```python
# ОТСУТСТВУЕТ в новом проекте:

# Связь с расходами
expense_id = Column(Integer, ForeignKey('expenses.id'))
suggested_expense_id = Column(Integer, ForeignKey('expenses.id'))
matching_score = Column(Numeric(5, 2))  # Оценка сопоставления 0-100

# Периоды принятия расхода
expense_acceptance_month = Column(Integer)
expense_acceptance_year = Column(Integer)
```

### 4.2 Отношения (Relationships)

```python
# ОТСУТСТВУЕТ в новом проекте:
expense_rel = relationship("Expense", foreign_keys=[expense_id])
suggested_expense_rel = relationship("Expense", foreign_keys=[suggested_expense_id])
```

---

## 5. ОТСУТСТВУЮЩИЕ СЕРВИСЫ

### 5.1 ExpenseMatchingService

```python
class ExpenseMatchingService:
    """Сервис сопоставления транзакций с расходами"""

    def find_matching_expenses(
        self,
        transaction: BankTransaction,
        threshold: float = 0.5
    ) -> List[MatchingSuggestion]:
        """Найти подходящие расходы для транзакции"""
        pass

    def calculate_matching_score(
        self,
        transaction: BankTransaction,
        expense: Expense
    ) -> Tuple[float, List[str]]:
        """Рассчитать оценку сопоставления"""
        # Критерии:
        # - Совпадение суммы (±5%)
        # - Совпадение даты (±7 дней)
        # - Совпадение контрагента
        # - Совпадение назначения платежа
        pass
```

### 5.2 RegularPaymentDetector

```python
class RegularPaymentDetector:
    """Детектор регулярных платежей"""

    def detect_patterns(
        self,
        min_occurrences: int = 3,
        max_variance: float = 0.2
    ) -> List[RegularPaymentPattern]:
        """
        Обнаружить паттерны регулярных платежей:
        - Подписки
        - Арендные платежи
        - Зарплатные выплаты
        """
        pass

    def predict_next_payment(
        self,
        pattern: RegularPaymentPattern
    ) -> Optional[date]:
        """Предсказать дату следующего платежа"""
        pass
```

### 5.3 BackgroundTaskManager

```python
class BackgroundTaskManager:
    """Менеджер фоновых задач для OData синхронизации"""

    def start_sync_task(
        self,
        date_from: date,
        date_to: date,
        auto_classify: bool
    ) -> str:
        """Запустить задачу синхронизации, вернуть task_id"""
        pass

    def get_task_status(self, task_id: str) -> dict:
        """Получить статус задачи"""
        return {
            "task_id": task_id,
            "status": "running|completed|failed",
            "progress": 75,
            "total_records": 1000,
            "processed_records": 750,
            "errors": []
        }

    def cancel_task(self, task_id: str) -> bool:
        """Отменить задачу"""
        pass
```

---

## 6. ТАБЛИЦА ПРИОРИТЕТОВ РЕАЛИЗАЦИИ

| Функционал | Приоритет | Сложность | Время (дни) |
|------------|-----------|-----------|-------------|
| Страница аналитики | Высокий | Высокая | 3-5 |
| Регулярные платежи | Средний | Средняя | 2-3 |
| Связывание с расходами | Высокий | Высокая | 3-4 |
| Фоновые задачи OData | Средний | Высокая | 2-3 |
| Расширенная фильтрация | Низкий | Низкая | 1 |
| Компоненты графиков | Средний | Средняя | 2-3 |
| KPI карточки | Низкий | Низкая | 0.5 |

---

## 7. РЕКОМЕНДУЕМЫЙ ПОРЯДОК РЕАЛИЗАЦИИ

### Фаза 1: Базовая аналитика (1-2 дня)
1. ✅ Добавить эндпоинт `/analytics` (УЖЕ СДЕЛАНО)
2. ✅ Добавить KPI карточки на страницу транзакций (УЖЕ СДЕЛАНО)
3. Создать отдельную страницу аналитики

### Фаза 2: Графики и визуализация (2-3 дня)
1. Установить recharts: `npm install recharts`
2. Создать компоненты графиков:
   - CashFlowChart
   - CategoryBreakdownChart
   - ProcessingEfficiencyChart

### Фаза 3: Расширенная функциональность (3-5 дней)
1. Добавить модель Expense (если нет)
2. Реализовать ExpenseMatchingService
3. Добавить эндпоинты связывания
4. Реализовать RegularPaymentDetector

### Фаза 4: Фоновые задачи (2-3 дня)
1. Добавить Celery или asyncio для фоновых задач
2. Реализовать BackgroundTaskManager
3. Добавить эндпоинты статуса задач
4. Добавить WebSocket для real-time обновлений

---

## 8. ТЕХНИЧЕСКИЙ ДОЛГ

### Критический:
- [ ] Отсутствует expense_id в модели BankTransaction
- [ ] Нет связи транзакций с заявками на расходы

### Высокий:
- [ ] Нет фоновой обработки для больших импортов
- [ ] Отсутствует детектор регулярных платежей

### Средний:
- [ ] Нет страницы аналитики
- [ ] Отсутствуют графики

### Низкий:
- [ ] Расширенная фильтрация
- [ ] Экспорт данных

---

## ИТОГО

**Реализовано:** ~35%
**Осталось:** ~65%

**Основные пробелы:**
1. Связь с расходами (expenses)
2. Детальная аналитика и графики
3. Регулярные платежи
4. Фоновая обработка

**Рекомендация:** Сначала реализовать страницу аналитики и графики, так как backend уже готов.
