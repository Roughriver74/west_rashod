# Быстрый старт деплоя West Rashod

## Результаты проверки сервера (192.168.45.98)

✅ **Сервер готов к деплою!**

### Что установлено:
- ✅ Ubuntu 22.04.5 LTS
- ✅ Docker 29.1.3 с Docker Compose v5.0.0
- ✅ Git 2.34.1
- ✅ Python 3.10.12
- ✅ Node.js v24.12.0
- ✅ UFW firewall (порты 80, 443, 22 открыты)
- ✅ 34GB свободного места на диске
- ✅ 4GB RAM (используется только 135MB)

### Что нужно сделать:

⚠️ **Nginx не установлен** (но это не проблема - мы используем Nginx в Docker)
⚠️ **1С сервер (10.10.100.77) недоступен с сервера** (проверьте сетевую связность)

---

## Шаги для деплоя

### 1. Настройте конфигурацию

```bash
# Скопируйте пример конфигурации
cp deployment/.env.prod.example deployment/.env.prod

# Отредактируйте .env.prod
nano deployment/.env.prod
```

**Обязательно измените:**
- `POSTGRES_PASSWORD` - надежный пароль для БД
- `SECRET_KEY` - секретный ключ (минимум 32 символа)
- `VITE_API_URL=http://192.168.45.98:8005` (IP уже правильный)

### 2. Запустите деплой

```bash
# Полный деплой с проверками
./deploy.sh 192.168.45.98

# Или пропустить проверки (быстрее)
./deploy.sh 192.168.45.98 --skip-checks
```

### 3. Доступ к приложению

После деплоя приложение будет доступно:

- **Frontend**: http://192.168.45.98
- **Backend API**: http://192.168.45.98:8005/docs
- **Логин**: admin / admin

---

## Управление после деплоя

### Подключение к серверу

```bash
ssh root@192.168.45.98
cd /opt/west_rashod
```

### Просмотр статуса

```bash
docker compose -f docker-compose.prod.yml ps
```

### Просмотр логов

```bash
# Все логи
docker compose -f docker-compose.prod.yml logs -f

# Только backend
docker compose -f docker-compose.prod.yml logs -f backend
```

### Рестарт сервисов

```bash
# Все сервисы
docker compose -f docker-compose.prod.yml restart

# Только backend
docker compose -f docker-compose.prod.yml restart backend
```

### Остановка

```bash
docker compose -f docker-compose.prod.yml down
```

---

## Настройка доступа по имени

### На клиентских машинах

Добавьте в файл hosts:

**Windows**: `C:\Windows\System32\drivers\etc\hosts`
**Linux/macOS**: `/etc/hosts`

```
192.168.45.98 west-rashod.local
```

После этого приложение будет доступно по адресу: http://west-rashod.local

---

## Решение проблем

### 1С сервер недоступен

Если 1С сервер (10.10.100.77) недоступен с production сервера:

```bash
# На сервере проверьте доступность
ssh root@192.168.45.98
ping 10.10.100.77

# Проверьте из контейнера backend
docker exec west_rashod_prod_backend ping 10.10.100.77
```

Возможные причины:
- Сервер 1С выключен
- Файрвол блокирует доступ
- Маршрутизация между серверами не настроена

### Проблемы с портами

Если какой-то порт занят:

```bash
# Найти процесс
sudo lsof -i :80
sudo lsof -i :8005

# Остановить процесс
sudo kill <PID>
```

### Очистка Docker

Если нужно освободить место:

```bash
# Удалить неиспользуемые образы
docker system prune -a

# Просмотреть использование диска
docker system df
```

---

## Структура файлов деплоя

```
deployment/
├── README.md                    # Этот файл
├── check-server.sh              # Скрипт проверки сервера
├── .env.prod.example            # Пример конфигурации
├── .env.prod                    # Реальная конфигурация (не в git)
├── nginx/
│   ├── nginx.conf               # Главная конфигурация Nginx
│   └── conf.d/
│       └── west_rashod.conf     # Виртуальный хост
└── systemd/
    └── west_rashod_backend.service  # Systemd сервис (альтернатива Docker)
```

---

## Дополнительная информация

Полная документация: [DEPLOYMENT.md](../DEPLOYMENT.md)

Основная документация проекта: [CLAUDE.md](../CLAUDE.md)

---

**Важно**: После первого деплоя обязательно измените пароль администратора (admin/admin) через UI приложения!
