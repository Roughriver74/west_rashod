# Деплой West Rashod без Docker

Инструкция по установке приложения напрямую на сервер без использования Docker.

## Преимущества

- ✅ Работает в любом окружении (включая Proxmox LXC)
- ✅ Меньше overhead
- ✅ Проще отладка
- ✅ Прямой доступ к логам

## Требования

- Ubuntu 22.04 или новее
- Python 3.10+
- Node.js 18+
- PostgreSQL 15
- Nginx
- Redis (опционально)

---

## Быстрая установка

### 1. Установить зависимости

```bash
# Обновить систему
apt-get update && apt-get upgrade -y

# Установить PostgreSQL
apt-get install -y postgresql postgresql-contrib

# Установить Nginx
apt-get install -y nginx

# Установить Redis (опционально)
apt-get install -y redis-server

# Установить Python и pip
apt-get install -y python3 python3-pip python3-venv

# Установить Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs

# Установить build tools
apt-get install -y build-essential libpq-dev
```

### 2. Настроить PostgreSQL

```bash
# Переключиться на пользователя postgres
sudo -u postgres psql

-- В psql:
CREATE DATABASE west_rashod_db;
CREATE USER rashod_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE west_rashod_db TO rashod_user;
\q
```

### 3. Создать пользователя приложения

```bash
# Создать пользователя
useradd -m -s /bin/bash west_rashod
```

### 4. Загрузить код приложения

```bash
# Создать директорию
mkdir -p /opt/west_rashod
cd /opt/west_rashod

# Скопировать с локальной машины (с вашего компьютера):
rsync -av --exclude='.git' --exclude='node_modules' --exclude='venv' \
  /Users/evgenijsikunov/projects/west/west_rashod/ \
  root@192.168.45.98:/opt/west_rashod/

# Установить владельца
chown -R west_rashod:west_rashod /opt/west_rashod
```

### 5. Настроить Backend

```bash
cd /opt/west_rashod/backend

# Создать виртуальное окружение
sudo -u west_rashod python3 -m venv venv

# Активировать venv
sudo -u west_rashod bash -c "source venv/bin/activate && pip install -r requirements.txt"

# Создать .env файл
cat > .env << EOF
DATABASE_URL=postgresql://rashod_user:your_secure_password_here@localhost:5432/west_rashod_db
DEBUG=False
SECRET_KEY=your-very-long-secret-key-min-32-chars-123456
CORS_ORIGINS=["http://192.168.45.98","http://192.168.45.98:8005"]
ODATA_1C_URL=http://10.10.100.77/trade/odata/standard.odata
ODATA_1C_USERNAME=odata.user
ODATA_1C_PASSWORD=ak228Hu2hbs28
USE_REDIS=true
REDIS_HOST=localhost
REDIS_PORT=6379
EOF

chown west_rashod:west_rashod .env

# Выполнить миграции
sudo -u west_rashod bash -c "cd /opt/west_rashod/backend && source venv/bin/activate && alembic upgrade head"

# Создать администратора
sudo -u west_rashod bash -c "cd /opt/west_rashod/backend && source venv/bin/activate && python scripts/create_admin.py"
```

### 6. Настроить Frontend

```bash
cd /opt/west_rashod/frontend

# Создать .env для сборки
cat > .env << EOF
VITE_API_URL=http://192.168.45.98:8005
EOF

# Установить зависимости и собрать
sudo -u west_rashod npm install
sudo -u west_rashod npm run build

# Результат сборки в frontend/dist
```

### 7. Создать systemd сервис для Backend

```bash
cat > /etc/systemd/system/west-rashod-backend.service << 'EOF'
[Unit]
Description=West Rashod Backend API
After=network.target postgresql.service redis.service
Wants=postgresql.service

[Service]
Type=simple
User=west_rashod
Group=west_rashod
WorkingDirectory=/opt/west_rashod/backend
Environment="PATH=/opt/west_rashod/backend/venv/bin"
EnvironmentFile=/opt/west_rashod/backend/.env

ExecStart=/opt/west_rashod/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8005 --workers 4

Restart=always
RestartSec=10

StandardOutput=append:/var/log/west_rashod/backend.log
StandardError=append:/var/log/west_rashod/backend_error.log

[Install]
WantedBy=multi-user.target
EOF

# Создать директорию для логов
mkdir -p /var/log/west_rashod
chown west_rashod:west_rashod /var/log/west_rashod

# Включить и запустить
systemctl daemon-reload
systemctl enable west-rashod-backend
systemctl start west-rashod-backend

# Проверить статус
systemctl status west-rashod-backend
```

### 8. Настроить Nginx

```bash
# Скопировать собранный frontend
rm -rf /var/www/west_rashod
mkdir -p /var/www/west_rashod
cp -r /opt/west_rashod/frontend/dist/* /var/www/west_rashod/
chown -R www-data:www-data /var/www/west_rashod

# Создать конфигурацию Nginx
cat > /etc/nginx/sites-available/west-rashod << 'EOF'
server {
    listen 80;
    server_name 192.168.45.98 west-rashod.local localhost _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Frontend
    location / {
        root /var/www/west_rashod;
        index index.html;
        try_files $uri $uri/ /index.html;

        # Cache static assets
        location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket для задач
    location /api/v1/ws/ {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }

    # API docs
    location /docs {
        proxy_pass http://127.0.0.1:8005;
        proxy_set_header Host $host;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8005;
        proxy_set_header Host $host;
    }
}
EOF

# Включить сайт
ln -sf /etc/nginx/sites-available/west-rashod /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Проверить конфигурацию
nginx -t

# Перезапустить Nginx
systemctl restart nginx
```

### 9. Проверка

```bash
# Проверить backend
curl http://localhost:8005/api/v1/health

# Проверить frontend
curl http://localhost/

# Проверить логи backend
tail -f /var/log/west_rashod/backend.log

# Проверить логи nginx
tail -f /var/log/nginx/access.log
```

---

## Управление

### Backend

```bash
# Статус
systemctl status west-rashod-backend

# Рестарт
systemctl restart west-rashod-backend

# Логи
journalctl -u west-rashod-backend -f
# или
tail -f /var/log/west_rashod/backend.log

# Остановка
systemctl stop west-rashod-backend
```

### Frontend/Nginx

```bash
# Рестарт Nginx
systemctl restart nginx

# Логи
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Обновление frontend
cd /opt/west_rashod/frontend
sudo -u west_rashod npm run build
rm -rf /var/www/west_rashod/*
cp -r dist/* /var/www/west_rashod/
chown -R www-data:www-data /var/www/west_rashod
```

---

## Обновление приложения

### 1. Загрузить новый код

```bash
# С локальной машины
rsync -av --exclude='.git' --exclude='node_modules' --exclude='venv' \
  /Users/evgenijsikunov/projects/west/west_rashod/ \
  root@192.168.45.98:/opt/west_rashod/

chown -R west_rashod:west_rashod /opt/west_rashod
```

### 2. Обновить backend

```bash
cd /opt/west_rashod/backend

# Обновить зависимости
sudo -u west_rashod bash -c "source venv/bin/activate && pip install -r requirements.txt"

# Выполнить миграции
sudo -u west_rashod bash -c "source venv/bin/activate && alembic upgrade head"

# Рестарт
systemctl restart west-rashod-backend
```

### 3. Обновить frontend

```bash
cd /opt/west_rashod/frontend

# Установить зависимости
sudo -u west_rashod npm install

# Собрать
sudo -u west_rashod npm run build

# Обновить файлы
rm -rf /var/www/west_rashod/*
cp -r dist/* /var/www/west_rashod/
chown -R www-data:www-data /var/www/west_rashod
```

---

## Бэкап

### База данных

```bash
# Создать бэкап
sudo -u postgres pg_dump west_rashod_db > /backup/west_rashod_$(date +%Y%m%d_%H%M%S).sql

# Восстановить
sudo -u postgres psql west_rashod_db < /backup/west_rashod_20251223_120000.sql
```

### Приложение

```bash
# Бэкап
tar -czf /backup/west_rashod_code_$(date +%Y%m%d_%H%M%S).tar.gz /opt/west_rashod
```

---

## Автоматический скрипт установки

```bash
# Скачать и запустить
curl -o install.sh https://raw.githubusercontent.com/.../install_no_docker.sh
chmod +x install.sh
./install.sh
```

---

## Доступ к приложению

- **Frontend**: http://192.168.45.98
- **Backend API**: http://192.168.45.98/api/v1/
- **API docs**: http://192.168.45.98/docs
- **Прямой доступ к backend**: http://192.168.45.98:8005/docs
- **Логин**: admin / admin

---

## Troubleshooting

### Backend не запускается

```bash
# Проверить логи
journalctl -u west-rashod-backend -n 100

# Проверить порт
ss -tulpn | grep 8005

# Проверить БД
sudo -u postgres psql -c "\l" | grep west_rashod
```

### Frontend не загружается

```bash
# Проверить nginx
nginx -t
systemctl status nginx

# Проверить файлы
ls -la /var/www/west_rashod/

# Проверить логи
tail -f /var/log/nginx/error.log
```

---

Это полное решение без Docker, которое гарантированно работает в любом окружении!
