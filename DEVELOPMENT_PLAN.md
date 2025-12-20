# West Rashod - План разработки

## Описание проекта

**West Rashod** - независимый микросервис для учёта банковских операций, извлечённый из монолита `west_buget_it`.

### Ключевые решения

- ✅ Собственная БД + синхронизация с 1С для справочников
- ✅ Собственная JWT аутентификация (Users, Departments, Roles)
- ✅ Полная интеграция 1С OData для банковских операций
- ❌ **БЕЗ Expenses matching** - связывание с заявками отключено

### Порты (непопулярные, для избежания конфликтов)

| Сервис     | Порт  |
|------------|-------|
| PostgreSQL | 54330 |
| Backend    | 8005  |
| Frontend   | 5178  |
| Redis      | 6382  |

---

## Текущее состояние

### ✅ Завершено

1. **Backend инфраструктура**
   - FastAPI приложение с роутерами
   - SQLAlchemy модели (8 таблиц)
   - Alembic миграции
   - JWT аутентификация (bcrypt)
   - Docker Compose конфигурация

2. **Сервисы 1С интеграции**
   - `odata_1c_client.py` - OData клиент
   - `bank_transaction_1c_import.py` - импорт транзакций
   - `transaction_classifier.py` - AI классификация
   - `business_operation_mapper.py` - маппинг операций

3. **API Endpoints**
   - `/api/v1/auth/` - аутентификация
   - `/api/v1/bank-transactions/` - CRUD транзакций + аналитика
   - `/api/v1/categories/` - категории бюджета
   - `/api/v1/organizations/` - организации
   - `/api/v1/contractors/` - контрагенты
   - `/api/v1/business-operation-mappings/` - маппинги
   - `/api/v1/sync-1c/` - синхронизация с 1С

4. **Frontend**
   - React + TypeScript + Vite
   - Ant Design UI
   - TanStack React Query
   - Все основные страницы созданы

5. **Аналитика и отчёты (NEW)**
   - Dashboard с интерактивными графиками (recharts)
   - Графики денежного потока по месяцам (столбцы/линии/области)
   - Круговая диаграмма топ категорий
   - Статистика по статусам обработки
   - Метрики AI классификации
   - Топ контрагентов по сумме
   - Выбор периода для анализа

6. **Страница контрагентов (NEW)**
   - Полный CRUD для контрагентов
   - Поиск по названию и ИНН
   - Фильтрация по активности
   - Детальный просмотр информации

7. **Экспорт данных (NEW)**
   - Экспорт транзакций в Excel
   - Экспорт выбранных или всех записей
   - Полная информация с форматированием

### ⚠️ Требует доработки

1. **Тестирование синхронизации 1С**
   - Проверить подключение к 1С
   - Тест импорта транзакций
   - Тест синхронизации справочников

2. **Frontend доработки**
   - Проверить все страницы
   - Исправить TypeScript ошибки (если есть)
   - Добавить обработку ошибок

3. **Безопасность**
   - Изменить SECRET_KEY для production
   - Настроить HTTPS
   - Проверить CORS настройки

---

## Структура проекта

```
west_rashod/
├── backend/
│   ├── app/
│   │   ├── api/v1/           # API роутеры
│   │   ├── core/             # Конфигурация
│   │   ├── db/               # Модели и сессия
│   │   ├── schemas/          # Pydantic схемы
│   │   ├── services/         # Бизнес-логика
│   │   └── utils/            # Утилиты (auth)
│   ├── alembic/              # Миграции
│   ├── scripts/              # Скрипты
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── api/              # API клиент
│   │   ├── components/       # React компоненты
│   │   ├── contexts/         # React контексты
│   │   ├── pages/            # Страницы
│   │   └── types/            # TypeScript типы
│   ├── package.json
│   ├── vite.config.ts
│   └── .env
├── docker-compose.yml
├── .gitignore
└── DEVELOPMENT_PLAN.md
```

---

## Следующие шаги (TODO)

### Высокий приоритет

1. [ ] **Тестирование 1С интеграции**
   - Проверить подключение к OData
   - Выполнить тестовую синхронизацию
   - Проверить маппинг полей

2. [ ] **Доработка импорта Excel**
   - Проверить работу импорта банковских выписок
   - Добавить валидацию файлов

3. [ ] **AI классификация**
   - Настроить ключевые слова для категорий
   - Тестировать автоклассификацию

### Средний приоритет

4. [x] **Аналитика и отчёты** ✅
   - Dashboard со статистикой
   - Графики по категориям (recharts)
   - Экспорт в Excel

5. [ ] **Регулярные платежи**
   - Детектор регулярных платежей
   - Автоматическая категоризация

6. [ ] **Уведомления**
   - Email уведомления
   - Telegram бот (опционально)

### Низкий приоритет

7. [ ] **Производительность**
   - Кеширование (Redis)
   - Пагинация для больших списков
   - Оптимизация запросов

8. [ ] **CI/CD**
   - GitHub Actions
   - Автоматический деплой
   - Тесты

---

## Как запустить

### Быстрый старт (рекомендуется)

```bash
# Запустить всё одной командой
./start-dev.sh

# Или отдельные компоненты:
./start-dev.sh db        # Только PostgreSQL
./start-dev.sh backend   # Только Backend
./start-dev.sh frontend  # Только Frontend
./start-dev.sh stop      # Остановить всё
./start-dev.sh reset     # Сбросить базу данных
```

### Ручной запуск

```bash
# 1. Запустить PostgreSQL
cd west_rashod
docker compose up -d db

# 2. Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python scripts/create_admin.py  # admin:admin
uvicorn app.main:app --reload --port 8005

# 3. Frontend
cd frontend
npm install
npm run dev
```

### Доступ

- Frontend: http://localhost:5178
- Backend API: http://localhost:8005/docs
- Логин: admin / admin

### Docker (production)

```bash
docker compose up -d
```

---

## Полезные команды

```bash
# Миграции
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Тесты
pytest

# Линтинг
cd frontend && npm run lint

# Создать админа
python scripts/create_admin.py
```

---

## Контакты и репозиторий

- **GitHub**: https://github.com/Roughriver74/west_rashod.git
- **Основной проект**: west_buget_it

---

*Последнее обновление: 2025-12-20*
