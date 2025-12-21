# Система фоновых задач

## Обзор

Реализована полнофункциональная система фоновых задач для асинхронной обработки больших объёмов данных с real-time обновлениями через WebSocket.

## Архитектура

### Backend компоненты

#### 1. BackgroundTaskManager (`app/services/background_tasks.py`)
Singleton менеджер для управления фоновыми задачами:

```python
from app.services.background_tasks import task_manager

# Создание задачи
task_id = task_manager.create_task(
    task_type="my_task",
    total=100,
    metadata={"user_id": 123}
)

# Обновление прогресса
task_manager.update_progress(
    task_id,
    processed=50,
    message="Обработано 50 элементов"
)

# Завершение
task_manager.complete_task(task_id, result={"success": True})
```

**Методы:**
- `create_task()` - создать новую задачу
- `update_progress()` - обновить прогресс
- `start_task()` - пометить как запущенную
- `complete_task()` - пометить как завершённую
- `fail_task()` - пометить как провалившуюся
- `cancel_task()` - отменить задачу
- `subscribe()` / `unsubscribe()` - подписка на обновления

#### 2. AsyncSyncService (`app/services/async_sync_service.py`)
Сервис для асинхронной синхронизации с 1С:

```python
from app.services.async_sync_service import AsyncSyncService

# Запуск синхронизации транзакций
task_id = AsyncSyncService.start_bank_transactions_sync(
    date_from=date(2025, 1, 1),
    date_to=date(2025, 12, 31),
    auto_classify=True,
    user_id=1
)

# Запуск синхронизации контрагентов
task_id = AsyncSyncService.start_contractors_sync(user_id=1)
```

**Особенности:**
- Периодические commit'ы каждые 100 записей
- Обработка ошибок с rollback
- Yield каждые 50 записей для возможности отмены
- Детальное отслеживание прогресса

#### 3. API Endpoints

**Tasks API** (`/api/v1/tasks`)
```bash
# Получить статус задачи
GET /api/v1/tasks/{task_id}

# Список всех задач
GET /api/v1/tasks?task_type=sync_bank_transactions&limit=20

# Отменить задачу
POST /api/v1/tasks/{task_id}/cancel

# Очистка старых задач (admin only)
POST /api/v1/tasks/cleanup?max_age_hours=24
```

**Async Sync API** (`/api/v1/sync-1c`)
```bash
# Асинхронная синхронизация транзакций
POST /api/v1/sync-1c/bank-transactions/sync-async
{
  "date_from": "2025-01-01",
  "date_to": "2025-12-31",
  "auto_classify": true
}

# Асинхронная синхронизация контрагентов
POST /api/v1/sync-1c/contractors/sync-async
```

**WebSocket API** (`/api/v1/ws`)
```javascript
// Подключение к обновлениям конкретной задачи
ws://localhost:8001/api/v1/ws/tasks/{task_id}

// Подключение ко всем задачам
ws://localhost:8001/api/v1/ws/tasks
```

### Frontend компоненты

#### 1. tasks.ts API
```typescript
import {
  getTaskStatus,
  listTasks,
  cancelTask,
  startAsyncBankTransactionsSync,
  TaskWebSocket
} from '@/api/tasks';

// Получить статус
const task = await getTaskStatus(taskId);

// Список задач
const { tasks, total } = await listTasks('sync_bank_transactions', 20);

// WebSocket подключение
const ws = new TaskWebSocket(
  taskId,
  (task) => console.log('Update:', task),
  (error) => console.error('Error:', error)
);
ws.connect();
```

#### 2. TaskProgress компонент
```tsx
import TaskProgress from '@/components/TaskProgress';

<TaskProgress
  taskId={taskId}
  title="Синхронизация транзакций"
  visible={showProgress}
  onClose={() => setShowProgress(false)}
  onComplete={(task) => console.log('Done!', task)}
  useWebSocket={true}
/>
```

**Функции:**
- Показывает прогресс бар
- WebSocket + polling fallback
- Отображение статуса (pending/running/completed/failed/cancelled)
- Кнопка отмены для запущенных задач
- Отображение ошибок и результатов

#### 3. SyncModal компонент
```tsx
import SyncModal from '@/components/SyncModal';

<SyncModal
  visible={showSyncModal}
  onClose={() => setShowSyncModal(false)}
  onSyncComplete={() => {
    message.success('Синхронизация завершена!');
    refetchData();
  }}
/>
```

**Вкладки:**
- **Транзакции** - синхронизация банковских операций
  - Выбор периода
  - Автоматическая классификация
- **Контрагенты** - синхронизация справочника

## Использование

### 1. Запуск асинхронной синхронизации

**Backend:**
```python
from app.services.async_sync_service import AsyncSyncService

task_id = AsyncSyncService.start_bank_transactions_sync(
    date_from=date(2025, 11, 1),
    date_to=date(2025, 11, 30),
    auto_classify=True
)
```

**Frontend:**
```typescript
import { startAsyncBankTransactionsSync } from '@/api/tasks';

const response = await startAsyncBankTransactionsSync({
  date_from: '2025-11-01',
  date_to: '2025-11-30',
  auto_classify: true
});

console.log('Task started:', response.task_id);
```

### 2. Отслеживание прогресса

**Через WebSocket:**
```typescript
import { TaskWebSocket } from '@/api/tasks';

const ws = new TaskWebSocket(
  taskId,
  (task) => {
    console.log(`Progress: ${task.progress}%`);
    console.log(`Message: ${task.message}`);

    if (task.status === 'completed') {
      console.log('Result:', task.result);
    }
  }
);
ws.connect();
```

**Через polling:**
```typescript
import { getTaskStatus } from '@/api/tasks';

const interval = setInterval(async () => {
  const task = await getTaskStatus(taskId);

  if (['completed', 'failed', 'cancelled'].includes(task.status)) {
    clearInterval(interval);
  }
}, 2000);
```

### 3. Создание собственной фоновой задачи

**Backend:**
```python
from app.services.background_tasks import task_manager

class MyService:
    @classmethod
    def start_my_task(cls, user_id: int) -> str:
        task_id = task_manager.create_task(
            task_type="my_custom_task",
            total=1000,
            metadata={"user_id": user_id}
        )

        task_manager.run_async_task(
            task_id,
            cls._process_my_task
        )

        return task_id

    @classmethod
    async def _process_my_task(cls, task_id: str) -> dict:
        # Ваша логика
        for i in range(1000):
            # Обработка
            await process_item(i)

            # Обновление прогресса
            task_manager.update_progress(
                task_id,
                i + 1,
                message=f"Processed {i + 1}/1000"
            )

            # Yield для отмены
            if i % 50 == 0:
                await asyncio.sleep(0.01)

        return {"processed": 1000}
```

## Тестирование

Запустите тестовый скрипт:
```bash
cd backend
python test_background_tasks.py
```

Тесты проверяют:
- ✓ Успешное выполнение задач
- ✓ Обработку ошибок
- ✓ Отмену задач
- ✓ Систему подписок
- ✓ Список задач

## Производительность

### Оптимизации:
- **Batch commits:** Commit каждые 100 записей вместо одной большой транзакции
- **Async/await:** Полностью асинхронная обработка
- **Yield points:** Периодические await для корректной отмены
- **WebSocket:** Real-time обновления без постоянного polling
- **Fallback polling:** Автоматический переход на polling при проблемах с WebSocket

### Масштабирование:
- Singleton BackgroundTaskManager (thread-safe)
- In-memory хранение задач (для production рекомендуется Redis)
- Cleanup старых задач для экономии памяти
- Множественные WebSocket подключения к одной задаче

## Безопасность

### Контроль доступа:
- Только ADMIN и MANAGER могут запускать синхронизацию
- Только ADMIN может выполнять cleanup
- Все пользователи видят свои задачи

### Обработка ошибок:
- Rollback при ошибках commit
- Graceful handling WebSocket disconnect
- Логирование всех ошибок
- Task status = FAILED при exception

## Мониторинг

### Логи:
```python
# INFO логи
- Task created
- Task started
- Task completed
- Progress updates (optional)

# ERROR логи
- Task failed
- Commit errors
- WebSocket errors
```

### Метрики задач:
```python
task_info = {
    "task_id": "uuid",
    "status": "running",
    "progress": 75,
    "total": 100,
    "processed": 75,
    "message": "Processing...",
    "created_at": "2025-12-21T12:00:00",
    "started_at": "2025-12-21T12:00:05",
    "completed_at": null,
    "result": null,
    "error": null
}
```

## Roadmap

### Будущие улучшения:
- [ ] Redis backend для персистентного хранения
- [ ] Rate limiting для WebSocket подключений
- [ ] Приоритизация задач
- [ ] Scheduled tasks (cron-like)
- [ ] Task retries с exponential backoff
- [ ] Metrics dashboard (Grafana)
- [ ] Email notifications при завершении

## Примеры использования

### Пример 1: Массовый импорт из 1С
```python
# Запуск
task_id = AsyncSyncService.start_bank_transactions_sync(
    date_from=date(2024, 1, 1),
    date_to=date(2024, 12, 31),
    auto_classify=True
)

# Результат
# - Загружено: 5000 документов
# - Создано: 4800 записей
# - Обновлено: 200 записей
# - Пропущено: 0
# - Время: ~2 минуты
```

### Пример 2: Отслеживание через UI
```tsx
function SyncPage() {
  const [taskId, setTaskId] = useState<string | null>(null);

  const handleStartSync = async () => {
    const response = await startAsyncBankTransactionsSync({
      date_from: '2025-01-01',
      date_to: '2025-12-31'
    });
    setTaskId(response.task_id);
  };

  return (
    <>
      <Button onClick={handleStartSync}>
        Запустить синхронизацию
      </Button>

      {taskId && (
        <TaskProgress
          taskId={taskId}
          visible={true}
          onComplete={() => message.success('Готово!')}
        />
      )}
    </>
  );
}
```

## Поддержка

Для вопросов и предложений создавайте issue в репозитории проекта.
