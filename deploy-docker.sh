#!/bin/bash

# Docker-based деплой West Поток
# Использует docker-compose.prod.yml для продакшн среды

set -e  # Остановка при ошибке

SERVER="192.168.45.98"
SERVER_USER="root"
APP_DIR="/opt/west_rashod"
BACKUP_DIR="/opt/backups/west_rashod"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="deploy_${TIMESTAMP}.log"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для логирования
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

show_error() {
    log "${RED}ОШИБКА: $1${NC}"
}

show_warning() {
    log "${YELLOW}ПРЕДУПРЕЖДЕНИЕ: $1${NC}"
}

show_success() {
    log "${GREEN}$1${NC}"
}

show_info() {
    log "${BLUE}$1${NC}"
}

# Функция для проверки доступности сервера
check_server_connectivity() {
    log "Проверка доступности сервера..."
    if ! ssh -o ConnectTimeout=10 $SERVER_USER@$SERVER "echo 'OK'" > /dev/null 2>&1; then
        show_error "Не удается подключиться к серверу $SERVER"
        exit 1
    fi
    show_success "Сервер доступен"
}

# Функция для проверки Docker на сервере
check_docker() {
    log "Проверка Docker на сервере..."
    if ! ssh $SERVER_USER@$SERVER "docker --version" > /dev/null 2>&1; then
        show_error "Docker не установлен на сервере"
        exit 1
    fi
    if ! ssh $SERVER_USER@$SERVER "docker compose version" > /dev/null 2>&1; then
        show_error "Docker Compose не установлен на сервере"
        exit 1
    fi
    show_success "Docker и Docker Compose доступны"
}

# Функция для показа логов контейнеров
show_container_logs() {
    local service=$1
    log ""
    log "Последние 30 строк логов $service:"
    log "========================================"
    ssh $SERVER_USER@$SERVER "cd $APP_DIR && docker compose -f docker-compose.prod.yml logs --tail=30 $service" 2>&1 | tee -a "$LOG_FILE"
    log "========================================"
}

# Функция для отката
rollback() {
    show_warning "Выполняю откат к предыдущей версии..."

    if ssh $SERVER_USER@$SERVER "[ -f $BACKUP_DIR/west_rashod_$TIMESTAMP.tar.gz ]"; then
        ssh $SERVER_USER@$SERVER "
            cd $APP_DIR && \
            docker compose -f docker-compose.prod.yml down && \
            tar -xzf $BACKUP_DIR/west_rashod_$TIMESTAMP.tar.gz --strip-components=1 && \
            docker compose -f docker-compose.prod.yml up -d --build
        " 2>&1 | tee -a "$LOG_FILE"
        show_warning "Откат выполнен"
    else
        show_error "Бекап не найден, откат невозможен"
    fi
}

log ""
log "========================================"
log " ДЕПЛОЙ WEST ПОТОК (Docker)"
log "========================================"
log "Время: $(date)"
log "Сервер: $SERVER"
log "Лог: $LOG_FILE"
log ""

# Проверки
check_server_connectivity
check_docker

# 1. Создать директории на сервере
log ""
show_info "[1/9] Создание директорий..."
ssh $SERVER_USER@$SERVER "mkdir -p $APP_DIR $BACKUP_DIR" 2>&1 | tee -a "$LOG_FILE"
show_success "Директории созданы"

# 2. Создать бекап текущей версии (если существует)
log ""
show_info "[2/9] Создание бекапа..."
if ssh $SERVER_USER@$SERVER "[ -d $APP_DIR/backend ]"; then
    ssh $SERVER_USER@$SERVER "
        cd $APP_DIR && \
        tar -czf $BACKUP_DIR/west_rashod_$TIMESTAMP.tar.gz \
            --exclude='*.pyc' \
            --exclude='__pycache__' \
            --exclude='node_modules' \
            --exclude='.env' \
            --exclude='*.log' \
            backend frontend docker-compose.prod.yml deployment 2>/dev/null || true
    " 2>&1 | tee -a "$LOG_FILE"
    show_success "Бекап создан: west_rashod_$TIMESTAMP.tar.gz"
else
    show_warning "Предыдущая версия не найдена, бекап пропущен"
fi

# 3. Синхронизировать backend код
log ""
show_info "[3/9] Синхронизация backend..."
rsync -av --delete \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='venv' \
    --exclude='logs' \
    --exclude='.env' \
    --exclude='*.log' \
    backend/ $SERVER_USER@$SERVER:$APP_DIR/backend/ 2>&1 | tee -a "$LOG_FILE"
show_success "Backend синхронизирован"

# 4. Синхронизировать frontend код
log ""
show_info "[4/9] Синхронизация frontend..."
rsync -av --delete \
    --exclude='node_modules' \
    --exclude='dist' \
    --exclude='.env' \
    frontend/ $SERVER_USER@$SERVER:$APP_DIR/frontend/ 2>&1 | tee -a "$LOG_FILE"
show_success "Frontend синхронизирован"

# 5. Синхронизировать конфигурацию деплоя
log ""
show_info "[5/9] Синхронизация конфигурации..."
rsync -av \
    docker-compose.prod.yml \
    $SERVER_USER@$SERVER:$APP_DIR/ 2>&1 | tee -a "$LOG_FILE"
rsync -av --delete \
    deployment/ $SERVER_USER@$SERVER:$APP_DIR/deployment/ 2>&1 | tee -a "$LOG_FILE"

# Создать директорию ssl если не существует
ssh $SERVER_USER@$SERVER "mkdir -p $APP_DIR/deployment/nginx/ssl" 2>&1 | tee -a "$LOG_FILE"
show_success "Конфигурация синхронизирована"

# 6. Обновить .env.prod с правильным VITE_API_URL
log ""
show_info "[6/9] Настройка переменных окружения..."

# Проверяем и обновляем .env.prod на сервере
ssh $SERVER_USER@$SERVER "
    # Создаем .env.prod если не существует
    if [ ! -f $APP_DIR/deployment/.env.prod ]; then
        cat > $APP_DIR/deployment/.env.prod << 'EOF'
# Database Configuration
POSTGRES_USER=rashod_user
POSTGRES_PASSWORD=rashod_pass_secure_2024
POSTGRES_DB=west_rashod_db

# Application Settings
DEBUG=False
SECRET_KEY=west-potok-super-secret-key-production-2024-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=720

# API URLs - Frontend использует этот URL для API запросов
VITE_API_URL=http://192.168.45.98

# CORS Origins
CORS_ORIGINS=[\"http://192.168.45.98\",\"http://192.168.45.98:80\",\"http://192.168.45.98:8005\",\"http://localhost:5178\"]

# 1C OData Integration
ODATA_1C_URL=http://10.10.100.77/trade/odata/standard.odata
ODATA_1C_USERNAME=odata.user
ODATA_1C_PASSWORD=ak228Hu2hbs28
ODATA_1C_CUSTOM_AUTH_TOKEN=

# OData Timeouts
ODATA_REQUEST_TIMEOUT=60
ODATA_CONNECTION_TIMEOUT=10
ODATA_GET_REQUEST_TIMEOUT=30

# Batch Settings
SYNC_BATCH_SIZE=100

# Redis
USE_REDIS=true
REDIS_HOST=redis
REDIS_PORT=6379
EOF
    fi
" 2>&1 | tee -a "$LOG_FILE"
show_success "Переменные окружения настроены"

# 7. Остановить текущие контейнеры и пересобрать
log ""
show_info "[7/9] Пересборка и запуск контейнеров..."

ssh $SERVER_USER@$SERVER "
    cd $APP_DIR && \
    docker compose -f docker-compose.prod.yml down --remove-orphans && \
    docker compose -f docker-compose.prod.yml build --no-cache && \
    docker compose -f docker-compose.prod.yml up -d
" 2>&1 | tee -a "$LOG_FILE"

show_success "Контейнеры запущены"

# 8. Ожидание запуска
log ""
show_info "[8/9] Ожидание запуска сервисов (30 сек)..."
sleep 30

# 9. Проверка статуса
log ""
show_info "[9/9] Проверка статуса сервисов..."

# Проверяем статус контейнеров
CONTAINERS_STATUS=$(ssh $SERVER_USER@$SERVER "cd $APP_DIR && docker compose -f docker-compose.prod.yml ps --format 'table {{.Name}}\t{{.Status}}'")
log "$CONTAINERS_STATUS"

# Проверяем что все контейнеры запущены
RUNNING_COUNT=$(ssh $SERVER_USER@$SERVER "cd $APP_DIR && docker compose -f docker-compose.prod.yml ps --status running -q | wc -l")
EXPECTED_COUNT=5  # db, redis, backend, frontend, nginx

if [ "$RUNNING_COUNT" -lt "$EXPECTED_COUNT" ]; then
    show_error "Не все контейнеры запущены ($RUNNING_COUNT из $EXPECTED_COUNT)"
    show_container_logs "backend"

    read -p "Выполнить откат? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rollback
    fi
    exit 1
fi

show_success "Все $RUNNING_COUNT контейнеров запущены"

# Проверка API
log ""
log "Проверка API..."
API_RESPONSE=$(ssh $SERVER_USER@$SERVER "curl -s -o /dev/null -w '%{http_code}' http://localhost/api/v1/health" 2>/dev/null || echo "000")

if [ "$API_RESPONSE" = "200" ]; then
    show_success "API отвечает корректно (HTTP $API_RESPONSE)"
else
    show_warning "API вернул HTTP $API_RESPONSE (может быть нормально если health endpoint не настроен)"

    # Пробуем другие эндпоинты
    API_DOCS=$(ssh $SERVER_USER@$SERVER "curl -s -o /dev/null -w '%{http_code}' http://localhost/docs" 2>/dev/null || echo "000")
    if [ "$API_DOCS" = "200" ]; then
        show_success "API документация доступна (/docs)"
    fi
fi

# Проверка frontend
log ""
log "Проверка Frontend..."
FRONTEND_RESPONSE=$(ssh $SERVER_USER@$SERVER "curl -s -o /dev/null -w '%{http_code}' http://localhost/" 2>/dev/null || echo "000")

if [ "$FRONTEND_RESPONSE" = "200" ]; then
    show_success "Frontend отвечает корректно (HTTP $FRONTEND_RESPONSE)"
else
    show_warning "Frontend вернул HTTP $FRONTEND_RESPONSE"
    show_container_logs "frontend"
fi

# Итог
log ""
log "========================================"
log " ДЕПЛОЙ ЗАВЕРШЕН"
log "========================================"
show_success "URL: http://$SERVER"
log "Логин: admin / admin"
log "Лог деплоя: $LOG_FILE"
log ""
log "Полезные команды:"
log "  Логи backend:  ssh $SERVER_USER@$SERVER 'cd $APP_DIR && docker compose -f docker-compose.prod.yml logs -f backend'"
log "  Логи nginx:    ssh $SERVER_USER@$SERVER 'cd $APP_DIR && docker compose -f docker-compose.prod.yml logs -f nginx'"
log "  Статус:        ssh $SERVER_USER@$SERVER 'cd $APP_DIR && docker compose -f docker-compose.prod.yml ps'"
log "  Перезапуск:    ssh $SERVER_USER@$SERVER 'cd $APP_DIR && docker compose -f docker-compose.prod.yml restart'"
log ""
log "Бекапы:"
ssh $SERVER_USER@$SERVER "ls -lh $BACKUP_DIR | tail -5" 2>/dev/null | tee -a "$LOG_FILE"
log ""
