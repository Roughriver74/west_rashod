# Инструкция по деплою West Rashod

Полное руководство по развертыванию приложения West Rashod на production сервере.

## Содержание

1. [Требования к серверу](#требования-к-серверу)
2. [Быстрый деплой](#быстрый-деплой)
3. [Подробная инструкция](#подробная-инструкция)
4. [Настройка конфигурации](#настройка-конфигурации)
5. [Управление приложением](#управление-приложением)
6. [Мониторинг и логи](#мониторинг-и-логи)
7. [Обновление](#обновление)
8. [Troubleshooting](#troubleshooting)

---

## Требования к серверу

### Минимальные требования

- **ОС**: Ubuntu 20.04/22.04 или Debian 11+
- **CPU**: 2 ядра
- **RAM**: 4 GB
- **Диск**: 20 GB свободного места
- **Сеть**: Доступ к 1С серверу (10.10.100.77)

### Необходимое ПО

- Docker 24.0+
- Docker Compose 2.0+
- Git
- SSH доступ с правами root или sudo

### Порты

Должны быть открыты следующие порты:

- **80** - HTTP (Nginx)
- **443** - HTTPS (опционально)
- **8005** - Backend API (прямой доступ)
- **5178** - Frontend (прямой доступ)
- **54330** - PostgreSQL (опционально, для внешних подключений)
- **6382** - Redis (опционально)

---

## Быстрый деплой

### 1. Проверка сервера

```bash
# Сделать скрипты исполняемыми
chmod +x deploy.sh deployment/check-server.sh

# Проверить готовность сервера
./deployment/check-server.sh 192.168.45.98
```

### 2. Настройка конфигурации

```bash
# Скопировать пример конфигурации
cp deployment/.env.prod.example deployment/.env.prod

# Отредактировать конфигурацию
nano deployment/.env.prod
```

**Обязательно изменить:**
- `POSTGRES_PASSWORD` - пароль базы данных
- `SECRET_KEY` - секретный ключ приложения (минимум 32 символа)
- `VITE_API_URL` - если IP сервера отличается от 192.168.45.98

### 3. Запуск деплоя

```bash
# Полный деплой
./deploy.sh 192.168.45.98

# Деплой с опциями
./deploy.sh 192.168.45.98 --skip-checks  # Пропустить проверки
./deploy.sh 192.168.45.98 --force-rebuild  # Пересобрать образы
```

### 4. Проверка

После деплоя приложение будет доступно:

- **Frontend**: http://192.168.45.98
- **Backend API**: http://192.168.45.98:8005/docs
- **Логин**: admin / admin

---

## Подробная инструкция

### Шаг 1: Подготовка локальной машины

```bash
# Убедитесь что установлены зависимости
which ssh rsync git

# Клонировать репозиторий (если еще не сделано)
git clone <repo_url>
cd west_rashod
```

### Шаг 2: Настройка SSH доступа

```bash
# Проверить SSH соединение
ssh root@192.168.45.98

# Если нужно, настроить SSH ключ
ssh-copy-id root@192.168.45.98
```

### Шаг 3: Проверка сервера

Скрипт `check-server.sh` проверяет:

- SSH соединение
- Системную информацию (ОС, RAM, диск)
- Наличие Docker и Docker Compose
- Доступность портов
- Сетевую конфигурацию
- Доступ к 1С серверу

```bash
./deployment/check-server.sh 192.168.45.98
```

### Шаг 4: Подготовка конфигурации

#### 4.1. Создание .env.prod

```bash
cp deployment/.env.prod.example deployment/.env.prod
nano deployment/.env.prod
```

#### 4.2. Важные настройки

```bash
# База данных
POSTGRES_USER=rashod_user
POSTGRES_PASSWORD=your_strong_password_123  # ИЗМЕНИТЬ!
POSTGRES_DB=west_rashod_db

# Безопасность
SECRET_KEY=your-very-long-secret-key-min-32-chars-123456  # ИЗМЕНИТЬ!
DEBUG=False

# API URL (замените IP если нужно)
VITE_API_URL=http://192.168.45.98:8005

# CORS (добавьте нужные домены)
CORS_ORIGINS=["http://192.168.45.98","http://192.168.45.98:80"]

# 1C OData (оставьте как есть или измените)
ODATA_1C_URL=http://10.10.100.77/trade/odata/standard.odata
ODATA_1C_USERNAME=odata.user
ODATA_1C_PASSWORD=ak228Hu2hbs28
```

### Шаг 5: Запуск деплоя

```bash
# Запустить деплой
./deploy.sh 192.168.45.98
```

Скрипт выполнит:

1. ✓ Проверку локальных зависимостей
2. ✓ Проверку сервера
3. ✓ Подготовку конфигурационных файлов
4. ✓ Создание бэкапа (если приложение уже установлено)
5. ✓ Загрузку кода на сервер
6. ✓ Установку Docker (если не установлен)
7. ✓ Сборку и запуск контейнеров
8. ✓ Проверку работоспособности
9. ✓ Вывод логов и информации

### Шаг 6: Проверка после деплоя

```bash
# Проверить статус контейнеров
ssh root@192.168.45.98 'cd /opt/west_rashod && docker compose -f docker-compose.prod.yml ps'

# Проверить логи
ssh root@192.168.45.98 'cd /opt/west_rashod && docker compose -f docker-compose.prod.yml logs -f'

# Проверить доступность
curl http://192.168.45.98/health
curl http://192.168.45.98:8005/api/v1/health
```

---

## Настройка конфигурации

### Структура файлов конфигурации

```
deployment/
├── .env.prod              # Главный конфигурационный файл
├── .env.prod.example      # Пример конфигурации
├── nginx/
│   ├── nginx.conf         # Главная конфигурация Nginx
│   └── conf.d/
│       └── west_rashod.conf  # Виртуальный хост
└── systemd/
    └── west_rashod_backend.service  # Systemd сервис (альтернатива Docker)
```

### Настройка доступа по имени хоста

Если хотите использовать имя вместо IP:

#### На сервере (192.168.45.98)

```bash
# Установить hostname
hostnamectl set-hostname west-rashod

# Проверить
hostname
```

#### На клиентских машинах

**Windows:**

Добавить в `C:\Windows\System32\drivers\etc\hosts`:

```
192.168.45.98 west-rashod.local
```

**Linux/macOS:**

Добавить в `/etc/hosts`:

```
192.168.45.98 west-rashod.local
```

После этого приложение будет доступно по адресу:

- http://west-rashod.local

#### Обновление Nginx конфигурации

```bash
# На сервере отредактировать
nano /opt/west_rashod/deployment/nginx/conf.d/west_rashod.conf

# Изменить строку
server_name west-rashod.local 192.168.45.98 localhost;

# Перезапустить nginx
cd /opt/west_rashod
docker compose -f docker-compose.prod.yml restart nginx
```

### Настройка HTTPS (опционально)

Для HTTPS потребуется SSL сертификат. Для локальной сети можно использовать самоподписанный:

```bash
# На сервере
mkdir -p /opt/west_rashod/deployment/nginx/ssl

# Создать самоподписанный сертификат
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /opt/west_rashod/deployment/nginx/ssl/key.pem \
  -out /opt/west_rashod/deployment/nginx/ssl/cert.pem \
  -subj "/CN=192.168.45.98"

# Раскомментировать HTTPS блок в nginx конфигурации
nano /opt/west_rashod/deployment/nginx/conf.d/west_rashod.conf
```

---

## Управление приложением

### Основные команды Docker Compose

```bash
# Подключиться к серверу
ssh root@192.168.45.98
cd /opt/west_rashod

# Просмотр статуса
docker compose -f docker-compose.prod.yml ps

# Просмотр логов
docker compose -f docker-compose.prod.yml logs -f

# Просмотр логов конкретного сервиса
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend

# Рестарт всех сервисов
docker compose -f docker-compose.prod.yml restart

# Рестарт конкретного сервиса
docker compose -f docker-compose.prod.yml restart backend

# Остановка
docker compose -f docker-compose.prod.yml stop

# Запуск
docker compose -f docker-compose.prod.yml start

# Полная остановка и удаление контейнеров
docker compose -f docker-compose.prod.yml down

# Полная остановка с удалением volumes (УДАЛИТ БАЗУ ДАННЫХ!)
docker compose -f docker-compose.prod.yml down -v
```

### Выполнение команд внутри контейнеров

```bash
# Подключиться к backend контейнеру
docker exec -it west_rashod_prod_backend bash

# Выполнить миграции
docker exec -it west_rashod_prod_backend alembic upgrade head

# Подключиться к базе данных
docker exec -it west_rashod_prod_db psql -U rashod_user -d west_rashod_db

# Создать бэкап базы данных
docker exec west_rashod_prod_db pg_dump -U rashod_user west_rashod_db > backup.sql

# Восстановить базу данных из бэкапа
cat backup.sql | docker exec -i west_rashod_prod_db psql -U rashod_user west_rashod_db
```

---

## Мониторинг и логи

### Просмотр логов

```bash
# Все логи
docker compose -f docker-compose.prod.yml logs -f

# Логи backend
docker compose -f docker-compose.prod.yml logs -f backend

# Логи за последний час
docker compose -f docker-compose.prod.yml logs --since 1h

# Последние 100 строк
docker compose -f docker-compose.prod.yml logs --tail=100
```

### Мониторинг ресурсов

```bash
# Использование ресурсов контейнерами
docker stats

# Информация о конкретном контейнере
docker inspect west_rashod_prod_backend

# Список всех контейнеров
docker ps -a

# Использование диска
docker system df

# Очистка неиспользуемых образов
docker system prune -a
```

### Healthcheck

```bash
# Проверка backend
curl http://192.168.45.98:8005/api/v1/health

# Проверка frontend
curl http://192.168.45.98/health

# Проверка базы данных
docker exec west_rashod_prod_db pg_isready -U rashod_user
```

---

## Обновление

### Простое обновление

```bash
# На локальной машине
git pull origin main
./deploy.sh 192.168.45.98
```

### Обновление с пересборкой образов

```bash
./deploy.sh 192.168.45.98 --force-rebuild
```

### Ручное обновление

```bash
# На сервере
ssh root@192.168.45.98
cd /opt/west_rashod

# Остановить контейнеры
docker compose -f docker-compose.prod.yml down

# Обновить код (через git или rsync)
git pull origin main

# Пересобрать и запустить
docker compose -f docker-compose.prod.yml up -d --build
```

### Откат к предыдущей версии

```bash
# На сервере
ssh root@192.168.45.98

# Найти бэкап
ls -la /opt/ | grep west_rashod_backup

# Остановить текущую версию
cd /opt/west_rashod
docker compose -f docker-compose.prod.yml down

# Восстановить из бэкапа
cd /opt
mv west_rashod west_rashod_failed
cp -r west_rashod_backup_20240123_120000 west_rashod

# Запустить
cd /opt/west_rashod
docker compose -f docker-compose.prod.yml up -d
```

---

## Troubleshooting

### Проблема: Контейнеры не запускаются

```bash
# Проверить логи
docker compose -f docker-compose.prod.yml logs

# Проверить статус
docker compose -f docker-compose.prod.yml ps

# Пересоздать контейнеры
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

### Проблема: База данных недоступна

```bash
# Проверить статус PostgreSQL
docker exec west_rashod_prod_db pg_isready -U rashod_user

# Проверить логи
docker logs west_rashod_prod_db

# Перезапустить базу данных
docker compose -f docker-compose.prod.yml restart db
```

### Проблема: Frontend не загружается

```bash
# Проверить логи Nginx
docker logs west_rashod_prod_nginx

# Проверить конфигурацию Nginx
docker exec west_rashod_prod_nginx nginx -t

# Перезапустить Nginx
docker compose -f docker-compose.prod.yml restart nginx
```

### Проблема: Backend возвращает 500 ошибку

```bash
# Проверить логи backend
docker logs west_rashod_prod_backend

# Проверить переменные окружения
docker exec west_rashod_prod_backend env | grep DATABASE_URL

# Выполнить миграции
docker exec west_rashod_prod_backend alembic upgrade head
```

### Проблема: Нет доступа к 1С

```bash
# Проверить сетевую доступность из контейнера
docker exec west_rashod_prod_backend ping -c 3 10.10.100.77

# Проверить доступность OData endpoint
docker exec west_rashod_prod_backend curl -v http://10.10.100.77/trade/odata/standard.odata
```

### Проблема: Недостаточно места на диске

```bash
# Проверить использование диска
df -h

# Очистить неиспользуемые Docker образы
docker system prune -a

# Удалить старые логи
docker compose -f docker-compose.prod.yml logs --since 0s > /dev/null
```

### Проблема: Приложение работает медленно

```bash
# Проверить использование ресурсов
docker stats

# Увеличить количество workers в backend
# Редактировать docker-compose.prod.yml:
# command: >
#   sh -c "alembic upgrade head &&
#          python scripts/create_admin.py || true &&
#          uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 8"

# Перезапустить
docker compose -f docker-compose.prod.yml restart backend
```

---

## Безопасность

### Рекомендации по безопасности

1. **Измените пароли по умолчанию**
   - Пароль базы данных
   - SECRET_KEY
   - Пароль администратора (admin/admin)

2. **Настройте firewall**

```bash
# Установить UFW
apt-get install ufw

# Разрешить SSH
ufw allow 22/tcp

# Разрешить HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Включить firewall
ufw enable
```

3. **Регулярно делайте бэкапы**

```bash
# Создать скрипт для автоматического бэкапа
nano /opt/backup_west_rashod.sh

#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/west_rashod"
mkdir -p $BACKUP_DIR
cd /opt/west_rashod
docker exec west_rashod_prod_db pg_dump -U rashod_user west_rashod_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Удалять бэкапы старше 30 дней
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

# Добавить в cron
crontab -e
# 0 2 * * * /opt/backup_west_rashod.sh
```

4. **Мониторинг логов**

Регулярно проверяйте логи на наличие подозрительной активности.

---

## Дополнительная информация

### Структура приложения на сервере

```
/opt/west_rashod/
├── backend/              # Backend код
├── frontend/             # Frontend код
├── deployment/           # Конфигурационные файлы
├── docker-compose.prod.yml
└── postgres_data/        # База данных (volume)
```

### Полезные ссылки

- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)

---

## Поддержка

При возникновении проблем:

1. Проверьте логи: `docker compose -f docker-compose.prod.yml logs`
2. Проверьте статус: `docker compose -f docker-compose.prod.yml ps`
3. Проверьте документацию в разделе [Troubleshooting](#troubleshooting)
4. Обратитесь к администратору системы

---

**Версия документа**: 1.0
**Дата**: 2025-12-23
