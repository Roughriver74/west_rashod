# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Язык / Language

**Всегда отвечай на русском языке.**

Все ответы, описания задач, комментарии к коммитам и коммуникации с пользователем должны быть на русском языке.

**Правила:**
- Используй русский язык по умолчанию
- Код и названия переменных остаются на английском языке
- Комментарии к коду могут быть на русском языке
- Сообщения коммитов на русском языке

---

## Обзор проекта

**West Поток** (West Potok) - микросервис для учёта и анализа банковских операций с интеграцией 1С через OData.

**Основные возможности:**
- Импорт и синхронизация банковских транзакций из 1С
- Автоматическая AI-классификация транзакций по категориям
- Аналитика и визуализация денежных потоков
- Система фоновых задач с WebSocket отслеживанием прогресса
- Управление бюджетными категориями, контрагентами, организациями

**Технологический стек:**
- Backend: FastAPI + SQLAlchemy + PostgreSQL + Alembic
- Frontend: React + TypeScript + Vite + Ant Design + Recharts
- Интеграция: 1C OData API
- Задачи: AsyncIO-based background tasks с WebSocket

---

## Команды разработки

### Быстрый запуск (рекомендуется)

```bash
# Запустить все компоненты
./start-dev.sh

# Запустить отдельные сервисы
./start-dev.sh db        # Только PostgreSQL
./start-dev.sh backend   # Только Backend
./start-dev.sh frontend  # Только Frontend

# Утилиты
./start-dev.sh stop      # Остановить все сервисы
./start-dev.sh reset     # Сбросить базу данных
```

### Backend

```bash
cd backend

# Установка зависимостей
pip install -r requirements.txt

# Запуск сервера разработки (порт 8001)
uvicorn app.main:app --reload --port 8001

# Миграции
alembic revision --autogenerate -m "описание изменений"
alembic upgrade head
alembic downgrade -1

# Создание администратора (admin:admin)
python scripts/create_admin.py

# Тестирование фоновых задач
python test_background_tasks.py
```

**API документация:** http://localhost:8001/docs

### Frontend

```bash
cd frontend

# Установка зависимостей
npm install

# Запуск dev сервера (порт 5173)
npm run dev

# Сборка production
npm run build

# Линтинг
npm run lint

# Предпросмотр production сборки
npm preview
```

**Frontend URL:** http://localhost:5173

### Тестирование и отладка

```bash
# Backend логи в реальном времени
tail -f backend/logs/app.log

# Поиск ошибок
grep ERROR backend/logs/app.log

# Backend тесты
cd backend
pytest

# Проверка WebSocket соединения (требует wscat)
npm install -g wscat
wscat -c "ws://localhost:8001/api/v1/ws/tasks/{task_id}"
```

---

## Архитектура проекта

### Backend: Многослойная архитектура

```
backend/app/
├── api/v1/              # FastAPI роутеры (endpoints)
│   ├── auth.py          # JWT аутентификация
│   ├── bank_transactions.py   # Главный endpoint для транзакций
│   ├── sync_1c.py       # Синхронизация с 1С
│   ├── tasks.py         # API для фоновых задач
│   ├── websocket.py     # WebSocket для real-time обновлений
│   └── ...
├── services/            # Бизнес-логика
│   ├── odata_1c_client.py     # OData клиент для 1С
│   ├── bank_transaction_1c_import.py  # Импорт из 1С
│   ├── transaction_classifier.py      # AI классификатор
│   ├── async_sync_service.py          # Async синхронизация
│   ├── background_tasks.py            # Менеджер фоновых задач
│   └── ...
├── db/                  # Слой данных
│   ├── models.py        # SQLAlchemy модели
│   └── session.py       # Database session
├── schemas/             # Pydantic схемы (валидация)
├── core/                # Конфигурация приложения
│   ├── config.py        # Settings (env vars)
│   └── constants.py     # Константы
└── utils/               # Утилиты
    └── auth.py          # JWT helpers
```

### Frontend: Component-based архитектура

```
frontend/src/
├── pages/               # Страницы приложения
│   ├── BankTransactionsPage.tsx      # Главная страница транзакций
│   ├── BankTransactionsAnalyticsPage.tsx  # Аналитика
│   ├── DashboardPage.tsx             # Dashboard
│   ├── Sync1CPage.tsx                # Интерфейс синхронизации
│   └── ...
├── components/          # Переиспользуемые компоненты
│   ├── bank/            # Специфичные компоненты для транзакций
│   │   ├── CashFlowChart.tsx         # График денежного потока
│   │   ├── CategoryBreakdownChart.tsx # Разбивка по категориям
│   │   ├── RegularPaymentsInsights.tsx # Анализ регулярных платежей
│   │   └── ...
│   ├── SyncModal.tsx    # Модалка синхронизации
│   └── TaskProgress.tsx # Отслеживание прогресса задач
├── api/                 # API клиенты (axios)
│   ├── bankTransactions.ts
│   ├── tasks.ts         # API для фоновых задач
│   └── ...
├── types/               # TypeScript типы
├── contexts/            # React contexts (AuthContext)
└── utils/               # Вспомогательные функции
```

### База данных: 8 основных таблиц

**Справочники (синхронизируются с 1С):**
- `organizations` - Организации
- `contractors` - Контрагенты
- `categories` - Бюджетные категории

**Транзакции:**
- `bank_transactions` - Банковские операции (главная таблица)
- `expenses` - Заявки на расход (для связывания с транзакциями)

**Классификация:**
- `business_operation_mappings` - Маппинг бизнес-операций 1С на категории
- `categorization_patterns` - Правила автоматической категоризации

**Пользователи:**
- `users` - Пользователи системы (JWT auth)

---

## Ключевые концепции

### 1. Интеграция с 1С через OData

Все запросы к 1С идут через `odata_1c_client.py`:

```python
# Конфигурация в app/core/config.py
ODATA_1C_URL = "http://10.10.100.77/trade/odata/standard.odata"
ODATA_1C_USERNAME = "odata.user"
ODATA_1C_PASSWORD = "ak228Hu2hbs28"
```

**Основные endpoints 1С:**
- `/Catalog_ОрганизацииОрганизации` - организации
- `/Catalog_Контрагенты` - контрагенты
- `/Catalog_СтатьиБюджета` - категории бюджета
- `/Document_ПоступлениеНаРасчетныйСчет` - поступления
- `/Document_СписаниеСРасчетногоСчета` - списания
- `/Catalog_ХозяйственныеОперации` - бизнес-операции

**Важно:** OData фильтры используют синтаксис `$filter`, `$select`, `$top`, `$skip`.

### 2. Система фоновых задач

Backend использует AsyncIO-based систему фоновых задач (не Celery) с WebSocket для real-time отслеживания:

**Запуск задачи:**
```python
from app.services.async_sync_service import AsyncSyncService

task_id = AsyncSyncService.start_bank_transactions_sync(
    date_from=date(2025, 1, 1),
    date_to=date(2025, 12, 31),
    auto_classify=True,
    user_id=1
)
```

**Отслеживание через WebSocket:**
```javascript
const ws = new WebSocket(`ws://localhost:8001/api/v1/ws/tasks/${taskId}`);
ws.onmessage = (event) => {
  const task = JSON.parse(event.data);
  console.log(`${task.progress}%: ${task.message}`);
};
```

**Fallback на polling:** Если WebSocket недоступен, используется HTTP polling через `/api/v1/tasks/{task_id}`.

### 3. AI Классификация транзакций

`transaction_classifier.py` использует keyword-based подход для автоматической категоризации:

1. **Анализ назначения платежа и контрагента**
2. **Поиск ключевых слов** (настраиваются в категориях)
3. **Присвоение confidence score** (0-100)
4. **Статус:** `CATEGORIZED` (>70%), `NEEDS_REVIEW` (<70%)

**Улучшение классификации:**
- Добавить ключевые слова в категории через UI
- Использовать "Categorization Patterns" для точных правил
- Обучать на исторических данных (mapping table)

### 4. Статусы обработки транзакций

Жизненный цикл транзакции:

```
NEW → CATEGORIZED → APPROVED
  ↓          ↓
  → NEEDS_REVIEW → APPROVED
  ↓
  → IGNORED
```

- `NEW` - импортирована, не обработана
- `CATEGORIZED` - автоматически категоризирована (confidence > 70%)
- `NEEDS_REVIEW` - требует ручной проверки (confidence < 70%)
- `APPROVED` - проверена и подтверждена
- `IGNORED` - игнорируется (служебные операции)

### 5. Порты сервисов (непопулярные для избежания конфликтов)

| Сервис     | Порт  | URL |
|------------|-------|-----|
| PostgreSQL | 54330 | localhost:54330 |
| Backend    | 8005  | http://localhost:8005 |
| Frontend   | 5178  | http://localhost:5178 |
| Redis      | 6382  | localhost:6382 (опционально) |

**Примечание:** Порт backend в `main.py` указан как 8001, но `start-dev.sh` использует порт 8005. **Актуальный порт: 8005**.

---

## Типичные задачи разработки

### Добавление нового endpoint

1. Создать Pydantic схемы в `backend/app/schemas/`
2. Добавить модель в `backend/app/db/models.py` (если нужна новая таблица)
3. Создать миграцию: `alembic revision --autogenerate -m "описание"`
4. Создать роутер в `backend/app/api/v1/`
5. Подключить роутер в `backend/app/main.py`
6. Создать API клиент в `frontend/src/api/`
7. Использовать в компонентах через TanStack Query

### Добавление нового графика аналитики

1. Создать компонент в `frontend/src/components/bank/`
2. Использовать recharts для визуализации
3. Получать данные через `useBankTransactionAnalytics()` hook
4. При необходимости добавить новый endpoint аналитики

### Изменение логики классификации

1. Редактировать `backend/app/services/transaction_classifier.py`
2. Тестировать на реальных данных
3. Настроить ключевые слова категорий через UI
4. Использовать `business_operation_mappings` для точных правил

### Работа с фоновыми задачами

1. Использовать `AsyncSyncService` для длительных операций
2. Возвращать `task_id` клиенту
3. Отслеживать через WebSocket или polling
4. Обрабатывать статусы: `pending`, `running`, `completed`, `failed`

---

## Важные файлы и соглашения

### Конфигурация

- `backend/app/core/config.py` - все настройки приложения (через env vars)
- `backend/.env` - локальные переменные окружения
- `frontend/.env` - настройки frontend (VITE_API_URL)

### База данных

- Все изменения через миграции Alembic
- SQLAlchemy модели используют `declarative_base()`
- Индексы на часто используемые поля (date, contractor_id, category_id)
- Использовать `Decimal` для денежных сумм

### API

- Префикс: `/api/v1/`
- Аутентификация: JWT Bearer token
- Пагинация: `skip` и `limit` параметры
- Сортировка: параметр `order_by`
- Фильтрация: query параметры специфичные для endpoint

### Frontend

- TypeScript strict mode
- React Query для кэширования API запросов
- Ant Design компоненты для UI
- Recharts для графиков
- Day.js для работы с датами

### Логирование

- Backend: Python `logging` модуль
- Логи в консоль и файл `backend/logs/app.log`
- Уровни: DEBUG, INFO, WARNING, ERROR
- Контекст задач в логах для отладки

---

## Ссылки на документацию

- [QUICK_START.md](QUICK_START.md) - руководство по быстрому старту
- [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) - план разработки и TODO
- [BACKGROUND_TASKS_README.md](BACKGROUND_TASKS_README.md) - полная документация фоновых задач
- [PHASE_4_SUMMARY.md](PHASE_4_SUMMARY.md) - сводка изменений фазы 4
- API docs (runtime): http://localhost:8001/docs

---

## Готовые компоненты для копирования

При создании нового микросервиса можно использовать готовые компоненты:

**Из `west_buget_it/frontend/src/components/bank/`:**
- Все компоненты графиков аналитики (CashFlowChart, CategoryBreakdownChart и др.)
- TransactionInsightsPanel - панель инсайтов
- BankTransactionsKPICards - карточки метрик

**Команды для копирования уже настроены:**
```bash
cp /Users/evgenijsikunov/projects/west/west_buget_it/frontend/src/components/bank/*.tsx .
```
