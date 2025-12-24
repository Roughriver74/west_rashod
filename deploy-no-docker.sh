#!/bin/bash
# Автоматическая установка West Rashod без Docker
# Работает в любом окружении, включая Proxmox LXC

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVER_IP="${1:-192.168.45.98}"
SERVER_USER="root"
PROJECT_DIR="/opt/west_rashod"
APP_USER="west_rashod"

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  West Rashod - Деплой без Docker${NC}"
    echo -e "${BLUE}  Сервер: $SERVER_IP${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
}

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# 1. Установить зависимости
install_dependencies() {
    echo -e "\n${BLUE}1. Установка зависимостей на сервере${NC}"

    ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
export DEBIAN_FRONTEND=noninteractive

# Обновить систему
apt-get update

# Установить PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "Установка PostgreSQL..."
    apt-get install -y postgresql postgresql-contrib
fi

# Установить Nginx
if ! command -v nginx &> /dev/null; then
    echo "Установка Nginx..."
    apt-get install -y nginx
fi

# Установить Redis
if ! command -v redis-cli &> /dev/null; then
    echo "Установка Redis..."
    apt-get install -y redis-server
fi

# Установить Python
if ! command -v python3 &> /dev/null; then
    echo "Установка Python..."
    apt-get install -y python3 python3-pip python3-venv
fi

# Установить Node.js
if ! command -v node &> /dev/null; then
    echo "Установка Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y nodejs
fi

# Установить build tools
apt-get install -y build-essential libpq-dev curl

echo "Все зависимости установлены"
EOF

    print_status "Зависимости установлены"
}

# 2. Настроить PostgreSQL
setup_database() {
    echo -e "\n${BLUE}2. Настройка PostgreSQL${NC}"

    # Генерировать случайный пароль если не задан
    if [ -z "$DB_PASSWORD" ]; then
        DB_PASSWORD=$(openssl rand -base64 16)
        print_info "Сгенерирован пароль БД: $DB_PASSWORD"
    fi

    ssh ${SERVER_USER}@${SERVER_IP} << EOF
sudo -u postgres psql << 'PSQL'
-- Удалить базу и пользователя если существуют
DROP DATABASE IF EXISTS west_rashod_db;
DROP USER IF EXISTS rashod_user;

-- Создать новую базу и пользователя
CREATE DATABASE west_rashod_db;
CREATE USER rashod_user WITH PASSWORD '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON DATABASE west_rashod_db TO rashod_user;
ALTER DATABASE west_rashod_db OWNER TO rashod_user;
\c west_rashod_db
GRANT ALL ON SCHEMA public TO rashod_user;
PSQL
EOF

    # Сохранить пароль локально
    echo "$DB_PASSWORD" > /tmp/db_password.txt
    print_status "База данных настроена"
}

# 3. Создать пользователя приложения
create_app_user() {
    echo -e "\n${BLUE}3. Создание пользователя приложения${NC}"

    ssh ${SERVER_USER}@${SERVER_IP} << EOF
if ! id -u ${APP_USER} &> /dev/null; then
    useradd -m -s /bin/bash ${APP_USER}
    echo "Пользователь ${APP_USER} создан"
else
    echo "Пользователь ${APP_USER} уже существует"
fi
EOF

    print_status "Пользователь приложения готов"
}

# 4. Загрузить код
upload_code() {
    echo -e "\n${BLUE}4. Загрузка кода на сервер${NC}"

    # Создать директорию
    ssh ${SERVER_USER}@${SERVER_IP} "mkdir -p ${PROJECT_DIR}"

    # Синхронизировать код
    rsync -av --delete \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='logs/*.log' \
        --exclude='frontend/dist' \
        ./ ${SERVER_USER}@${SERVER_IP}:${PROJECT_DIR}/

    # Установить владельца
    ssh ${SERVER_USER}@${SERVER_IP} "chown -R ${APP_USER}:${APP_USER} ${PROJECT_DIR}"

    print_status "Код загружен"
}

# 5. Настроить Backend
setup_backend() {
    echo -e "\n${BLUE}5. Настройка Backend${NC}"

    DB_PASSWORD=$(cat /tmp/db_password.txt)
    SECRET_KEY=$(openssl rand -base64 32)

    ssh ${SERVER_USER}@${SERVER_IP} << EOF
cd ${PROJECT_DIR}/backend

# Создать venv
sudo -u ${APP_USER} python3 -m venv venv

# Установить зависимости
sudo -u ${APP_USER} bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"

# Создать .env
cat > .env << 'ENVFILE'
DATABASE_URL=postgresql://rashod_user:${DB_PASSWORD}@localhost:5432/west_rashod_db
DEBUG=False
SECRET_KEY=${SECRET_KEY}
CORS_ORIGINS=["http://192.168.45.98","http://192.168.45.98:8005","http://west-rashod.local"]
ODATA_1C_URL=http://10.10.100.77/trade/odata/standard.odata
ODATA_1C_USERNAME=odata.user
ODATA_1C_PASSWORD=ak228Hu2hbs28
USE_REDIS=true
REDIS_HOST=localhost
REDIS_PORT=6379
ENVFILE

chown ${APP_USER}:${APP_USER} .env

# Выполнить миграции
sudo -u ${APP_USER} bash -c "source venv/bin/activate && alembic upgrade head"

# Создать администратора
sudo -u ${APP_USER} bash -c "source venv/bin/activate && python scripts/create_admin.py" || true
EOF

    print_status "Backend настроен"
}

# 6. Собрать Frontend
build_frontend() {
    echo -e "\n${BLUE}6. Сборка Frontend${NC}"

    ssh ${SERVER_USER}@${SERVER_IP} << EOF
cd ${PROJECT_DIR}/frontend

# Создать .env для сборки
cat > .env << 'ENVFILE'
VITE_API_URL=http://192.168.45.98:8005
ENVFILE

# Установить зависимости
sudo -u ${APP_USER} npm install

# Собрать
sudo -u ${APP_USER} npm run build

echo "Frontend собран в dist/"
EOF

    print_status "Frontend собран"
}

# 7. Создать systemd сервис
create_systemd_service() {
    echo -e "\n${BLUE}7. Создание systemd сервиса${NC}"

    ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
# Создать директорию для логов
mkdir -p /var/log/west_rashod
chown west_rashod:west_rashod /var/log/west_rashod

# Создать systemd сервис
cat > /etc/systemd/system/west-rashod-backend.service << 'SERVICE'
[Unit]
Description=West Rashod Backend API
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

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
SERVICE

# Reload systemd
systemctl daemon-reload

# Включить и запустить
systemctl enable west-rashod-backend
systemctl restart west-rashod-backend

# Подождать запуска
sleep 3

# Проверить статус
systemctl status west-rashod-backend --no-pager
EOF

    print_status "Systemd сервис создан и запущен"
}

# 8. Настроить Nginx
setup_nginx() {
    echo -e "\n${BLUE}8. Настройка Nginx${NC}"

    ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
# Скопировать frontend в www
rm -rf /var/www/west_rashod
mkdir -p /var/www/west_rashod
cp -r /opt/west_rashod/frontend/dist/* /var/www/west_rashod/
chown -R www-data:www-data /var/www/west_rashod

# Создать конфигурацию
cat > /etc/nginx/sites-available/west-rashod << 'NGINX'
server {
    listen 80;
    server_name 192.168.45.98 west-rashod.local localhost _;

    # Логи
    access_log /var/log/nginx/west_rashod_access.log;
    error_log /var/log/nginx/west_rashod_error.log;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Frontend
    location / {
        root /var/www/west_rashod;
        index index.html;
        try_files $uri $uri/ /index.html;

        # Cache static
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

    # WebSocket
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
NGINX

# Включить сайт
ln -sf /etc/nginx/sites-available/west-rashod /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Проверить конфигурацию
nginx -t

# Перезапустить
systemctl restart nginx
EOF

    print_status "Nginx настроен"
}

# 9. Проверка
check_health() {
    echo -e "\n${BLUE}9. Проверка работоспособности${NC}"

    sleep 5

    # Backend
    if curl -f -s "http://${SERVER_IP}:8005/api/v1/health" &> /dev/null; then
        print_status "Backend работает: http://${SERVER_IP}:8005"
    else
        print_warning "Backend может быть недоступен"
    fi

    # Frontend через Nginx
    if curl -f -s "http://${SERVER_IP}/" &> /dev/null; then
        print_status "Frontend работает: http://${SERVER_IP}"
    else
        print_warning "Frontend может быть недоступен"
    fi
}

# 10. Показать итоговую информацию
show_summary() {
    DB_PASSWORD=$(cat /tmp/db_password.txt)

    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}  Деплой завершен!${NC}"
    echo -e "${BLUE}================================${NC}"
    echo -e ""
    echo -e "${GREEN}Приложение доступно:${NC}"
    echo -e "  Frontend: ${BLUE}http://${SERVER_IP}${NC}"
    echo -e "  Backend API: ${BLUE}http://${SERVER_IP}:8005/docs${NC}"
    echo -e "  API через Nginx: ${BLUE}http://${SERVER_IP}/docs${NC}"
    echo -e ""
    echo -e "${YELLOW}Логин:${NC} admin / admin"
    echo -e ""
    echo -e "${YELLOW}Пароль БД сохранен в:${NC} /tmp/db_password.txt"
    echo -e "  Пароль: ${DB_PASSWORD}"
    echo -e ""
    echo -e "${YELLOW}Управление:${NC}"
    echo -e "  Статус backend: systemctl status west-rashod-backend"
    echo -e "  Рестарт backend: systemctl restart west-rashod-backend"
    echo -e "  Логи backend: tail -f /var/log/west_rashod/backend.log"
    echo -e "  Логи nginx: tail -f /var/log/nginx/west_rashod_access.log"
    echo -e ""
    echo -e "${YELLOW}Обновление:${NC}"
    echo -e "  ./deploy-no-docker.sh ${SERVER_IP}"
    echo -e ""

    # Очистить временный файл
    rm -f /tmp/db_password.txt
}

# Главная функция
main() {
    print_header

    install_dependencies
    setup_database
    create_app_user
    upload_code
    setup_backend
    build_frontend
    create_systemd_service
    setup_nginx
    check_health
    show_summary
}

# Запуск
main
