# 🚀 Quick Start - Система фоновых задач

## Проверка работоспособности

### 1. Тест системы фоновых задач
```bash
cd backend
python test_background_tasks.py
```

Ожидаемый результат: `All tests passed! ✓`

### 2. Запуск backend
```bash
cd backend
uvicorn app.main:app --reload --port 8001
```

API доступен по адресу: http://localhost:8001
Документация: http://localhost:8001/docs

### 3. Запуск frontend
```bash
cd frontend
npm run dev
```

Приложение доступно по адресу: http://localhost:5173

---

## Быстрый тест через API

### 1. Получить токен
```bash
curl -X POST "http://localhost:8001/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"
```

### 2. Запустить async синхронизацию
```bash
curl -X POST "http://localhost:8001/api/v1/sync-1c/bank-transactions/sync-async" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date_from": "2025-11-01",
    "date_to": "2025-11-30",
    "auto_classify": true
  }'
```

Ответ:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "Sync started. Track progress at /api/v1/tasks/123e..."
}
```

### 3. Проверить статус
```bash
curl "http://localhost:8001/api/v1/tasks/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Ответ:
```json
{
  "task_id": "123e...",
  "status": "running",
  "progress": 45,
  "total": 1000,
  "processed": 450,
  "message": "Обработано 450 из 1000 (220 создано, 230 обновлено)"
}
```

### 4. WebSocket подключение
```javascript
const ws = new WebSocket('ws://localhost:8001/api/v1/ws/tasks/123e...');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data.data.progress + '%');
};

// Keep alive
setInterval(() => ws.send('ping'), 30000);
```

---

## Использование в UI

### 1. Открыть модалку синхронизации
```tsx
import { SyncModal } from '@/components/SyncModal';

<Button onClick={() => setShowSync(true)}>
  Синхронизация 1С
</Button>

<SyncModal
  visible={showSync}
  onClose={() => setShowSync(false)}
  onSyncComplete={() => {
    message.success('Синхронизация завершена!');
    refetch();
  }}
/>
```

### 2. Отслеживание прогресса
```tsx
import { TaskProgress } from '@/components/TaskProgress';

<TaskProgress
  taskId={taskId}
  title="Импорт транзакций"
  visible={showProgress}
  onClose={() => setShowProgress(false)}
  onComplete={(task) => {
    console.log('Результат:', task.result);
  }}
  useWebSocket={true}
/>
```

---

## Примеры использования API

### Python (backend)
```python
from app.services.async_sync_service import AsyncSyncService
from datetime import date

# Запуск синхронизации
task_id = AsyncSyncService.start_bank_transactions_sync(
    date_from=date(2025, 1, 1),
    date_to=date(2025, 12, 31),
    auto_classify=True,
    user_id=1
)

print(f"Task ID: {task_id}")
```

### TypeScript (frontend)
```typescript
import { startAsyncBankTransactionsSync, TaskWebSocket } from '@/api/tasks';

// Запуск
const { task_id } = await startAsyncBankTransactionsSync({
  date_from: '2025-01-01',
  date_to: '2025-12-31',
  auto_classify: true
});

// WebSocket отслеживание
const ws = new TaskWebSocket(
  task_id,
  (task) => {
    console.log(`${task.progress}%: ${task.message}`);

    if (task.status === 'completed') {
      console.log('Done!', task.result);
    }
  }
);

ws.connect();
```

---

## Отладка

### Просмотр логов backend
```bash
# Логи в реальном времени
tail -f backend/logs/app.log

# Поиск ошибок
grep ERROR backend/logs/app.log

# Логи конкретной задачи
grep "Task 123e4567" backend/logs/app.log
```

### Проверка WebSocket
```bash
# Установить wscat
npm install -g wscat

# Подключиться
wscat -c "ws://localhost:8001/api/v1/ws/tasks/123e..."

# Отправить ping
> ping
< pong
```

### Список всех задач
```bash
curl "http://localhost:8001/api/v1/tasks?limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Troubleshooting

### Ошибка: "Task not found"
- Проверьте task_id
- Возможно, задача была удалена cleanup'ом

### WebSocket не подключается
- Проверьте CORS настройки
- Проверьте URL (ws:// или wss://)
- Fallback на polling активируется автоматически

### Долгие транзакции
- Увеличьте batch size в async_sync_service.py
- Проверьте индексы в БД
- Мониторьте PostgreSQL slow queries

### Память растёт
- Запустите cleanup: `POST /api/v1/tasks/cleanup`
- Настройте автоматический cleanup (cron)

---

## Production checklist

- [ ] Настроить Redis для хранения задач
- [ ] Добавить мониторинг (Grafana)
- [ ] Настроить логирование в файл
- [ ] Включить SSL для WebSocket (wss://)
- [ ] Настроить rate limiting
- [ ] Добавить health checks
- [ ] Настроить автоматический cleanup
- [ ] Бэкап задач в БД (опционально)

---

## Документация

- **Полное руководство:** [BACKGROUND_TASKS_README.md](BACKGROUND_TASKS_README.md)
- **Сводка изменений:** [PHASE_4_SUMMARY.md](PHASE_4_SUMMARY.md)
- **Исправления:** [FIXES_APPLIED.md](FIXES_APPLIED.md)
- **API docs:** http://localhost:8001/docs (после запуска)

---

**Готово! 🎉**
