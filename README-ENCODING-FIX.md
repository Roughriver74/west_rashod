# Исправление проблемы кодировки UTF-8

## Проблема

При синхронизации с 1С возникала ошибка:
```
UnicodeEncodeError: 'ascii' codec can't encode characters in position 0-4: ordinal not in range(128)
```

## Причина

PostgreSQL база данных использовала кодировку `SQL_ASCII` вместо `UTF-8`, что не позволяло сохранять русские символы.

## Решение

### 1. Изменена кодировка базы данных

```sql
ALTER DATABASE west_rashod_db SET client_encoding TO 'UTF8';
```

### 2. Обновлен DATABASE_URL в .env

```bash
DATABASE_URL=postgresql://rashod_user:rashod_pass_secure_2024@localhost:5432/west_rashod_db?client_encoding=utf8
```

### 3. Добавлен параметр в SQLAlchemy

```python
engine = create_engine(
    settings.DATABASE_URL,
    ...
    connect_args={"client_encoding": "utf8"},
)
```

## Проверка

После применения исправлений:

```bash
# Проверить кодировку БД
PGPASSWORD=rashod_pass_secure_2024 psql -U rashod_user -d west_rashod_db -h localhost -c "SHOW client_encoding;"

# Должно вернуть: UTF8 или SQL_UTF8
```

## Деплой

Исправления применяются автоматически через `deploy-safe.sh`:

```bash
./deploy-safe.sh
```

## Статус

✅ Исправлено  
✅ Протестировано на продакшене  
✅ Синхронизация с 1С работает корректно
