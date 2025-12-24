#!/bin/bash

# Безопасный скрипт деплоя West Поток
# Создает бекап и проверяет работоспособность после деплоя

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
NC='\033[0m' # No Color

# Функция для логирования
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Функция для отображения ошибок
show_error() {
    log "${RED}❌ ОШИБКА: $1${NC}"
}

# Функция для отображения предупреждений
show_warning() {
    log "${YELLOW}⚠️  ПРЕДУПРЕЖДЕНИЕ: $1${NC}"
}

# Функция для отображения успеха
show_success() {
    log "${GREEN}✅ $1${NC}"
}

# Функция для отображения последних логов backend
show_backend_logs() {
    log ""
    log "📋 Последние 30 строк логов backend:"
    log "════════════════════════════════════════"
    ssh $SERVER_USER@$SERVER "journalctl -u west-rashod-backend.service -n 30 --no-pager" 2>&1 | tee -a "$LOG_FILE"
    log "════════════════════════════════════════"
}

# Функция для отображения ошибок из логов
show_error_logs() {
    log ""
    log "🔍 Ошибки в логах backend (последние 5 минут):"
    log "════════════════════════════════════════"
    ssh $SERVER_USER@$SERVER "journalctl -u west-rashod-backend.service --since '5 minutes ago' --no-pager | grep -i 'error\|exception\|traceback' || echo 'Ошибок не найдено'" 2>&1 | tee -a "$LOG_FILE"
    log "════════════════════════════════════════"
}

# Функция для проверки доступности сервера
check_server_connectivity() {
    log "🔍 Проверка доступности сервера..."
    if ! ssh -o ConnectTimeout=10 $SERVER_USER@$SERVER "echo 'OK'" > /dev/null 2>&1; then
        show_error "Не удается подключиться к серверу $SERVER"
        log "💡 Проверьте:"
        log "   - Доступность сервера: ping $SERVER"
        log "   - SSH доступ: ssh $SERVER_USER@$SERVER"
        log "   - SSH ключи или пароль"
        exit 1
    fi
    show_success "Сервер доступен"
}

# Функция для проверки статуса сервиса
check_service_status() {
    local service=$1
    local description=$2

    if ssh $SERVER_USER@$SERVER "systemctl is-active --quiet $service"; then
        show_success "$description: работает"
        return 0
    else
        show_error "$description: не работает"
        return 1
    fi
}

log "🚀 Начало безопасного деплоя West Rashod..."
log "📅 Время: $(date)"
log "🖥️  Сервер: $SERVER"
log "📝 Лог файл: $LOG_FILE"
log ""

# Проверка доступности сервера
check_server_connectivity

# 1. Создать директорию для бекапов
log "📦 Создание директории для бекапов..."
if ssh $SERVER_USER@$SERVER "mkdir -p $BACKUP_DIR" 2>&1 | tee -a "$LOG_FILE"; then
    show_success "Директория бекапов создана"
else
    show_error "Не удалось создать директорию бекапов"
    exit 1
fi

# 2. Создать бекап текущей версии
log ""
log "💾 Создание бекапа текущей версии..."
if ssh $SERVER_USER@$SERVER "
cd $APP_DIR && \
tar -czf $BACKUP_DIR/west_rashod_$TIMESTAMP.tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='logs' \
  --exclude='node_modules' \
  backend/app frontend/src frontend/package.json frontend/vite.config.ts 2>&1
" 2>&1 | tee -a "$LOG_FILE"; then
    show_success "Бекап создан: $BACKUP_DIR/west_rashod_$TIMESTAMP.tar.gz"
else
    show_error "Не удалось создать бекап"
    exit 1
fi

# 3. Синхронизировать backend код
log ""
log "📤 Синхронизация backend кода..."
if rsync -av --delete \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='venv' \
  --exclude='logs' \
  --exclude='.env' \
  backend/app/ $SERVER_USER@$SERVER:$APP_DIR/backend/app/ 2>&1 | tee -a "$LOG_FILE"; then
    show_success "Backend код синхронизирован"
else
    show_error "Ошибка синхронизации backend кода"
    exit 1
fi

# 4. Синхронизировать frontend код
log ""
log "📤 Синхронизация frontend исходников..."
if rsync -av \
  --exclude='node_modules' \
  --exclude='dist' \
  frontend/src/ $SERVER_USER@$SERVER:$APP_DIR/frontend/src/ 2>&1 | tee -a "$LOG_FILE" && \
  rsync -av \
  frontend/package.json \
  frontend/vite.config.ts \
  frontend/index.html \
  $SERVER_USER@$SERVER:$APP_DIR/frontend/ 2>&1 | tee -a "$LOG_FILE"; then
    show_success "Frontend исходники синхронизированы"
else
    show_error "Ошибка синхронизации frontend исходников"
    exit 1
fi

# 5. Обновить конфигурацию
log ""
log "⚙️  Обновление конфигурации..."

# Frontend .env.production
if ssh $SERVER_USER@$SERVER "cat > $APP_DIR/frontend/.env.production << 'EOF'
VITE_API_URL=http://$SERVER
EOF
" 2>&1 | tee -a "$LOG_FILE"; then
    show_success "Frontend конфигурация обновлена"
else
    show_error "Ошибка обновления frontend конфигурации"
    exit 1
fi

# Backend .env (если не существует или нужно обновить)
log "⚙️  Проверка backend .env..."
ssh $SERVER_USER@$SERVER "
if [ ! -f $APP_DIR/backend/.env ] || ! grep -q 'client_encoding=utf8' $APP_DIR/backend/.env; then
    echo '⚙️  Обновление backend .env с UTF-8...'
    cat > $APP_DIR/backend/.env << 'ENVEOF'
DATABASE_URL=postgresql://rashod_user:rashod_pass_secure_2024@localhost:5432/west_rashod_db?client_encoding=utf8

# 1C OData API Configuration
ODATA_1C_URL=http://10.10.100.77/trade/odata/standard.odata
ODATA_1C_USERNAME=odata.user
ODATA_1C_PASSWORD=ak228Hu2hbs28

# JWT Configuration
SECRET_KEY=super-secret-key-for-jwt-rashod-2024
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200

# CORS
CORS_ORIGINS=http://localhost:5173,http://$SERVER

# Debug
DEBUG=False
ENVEOF
fi
" 2>&1 | tee -a "$LOG_FILE"
show_success "Backend конфигурация проверена/обновлена"

# 6. Собрать frontend
log ""
log "🔨 Сборка frontend..."
if ssh $SERVER_USER@$SERVER "cd $APP_DIR/frontend && npm run build 2>&1" 2>&1 | tee -a "$LOG_FILE"; then
    show_success "Frontend собран успешно"
else
    show_error "Ошибка сборки frontend"
    log "💡 Возможные причины:"
    log "   - Отсутствуют node_modules (выполните npm install на сервере)"
    log "   - Ошибки в TypeScript коде"
    log "   - Недостаточно памяти для сборки"
    exit 1
fi

# 7. Обновить frontend на продакшене
log ""
log "📦 Обновление frontend на продакшене..."
if ssh $SERVER_USER@$SERVER "
rm -rf /var/www/west_rashod/* && \
cp -r $APP_DIR/frontend/dist/* /var/www/west_rashod/ && \
chown -R www-data:www-data /var/www/west_rashod
" 2>&1 | tee -a "$LOG_FILE"; then
    show_success "Frontend развернут на продакшене"
else
    show_error "Ошибка развертывания frontend"
    exit 1
fi

# 8. Синхронизировать alembic миграции
log ""
log "📦 Синхронизация миграций Alembic..."
if rsync -av \
  backend/alembic/ $SERVER_USER@$SERVER:$APP_DIR/backend/alembic/ 2>&1 | tee -a "$LOG_FILE"; then
    show_success "Миграции синхронизированы"
else
    show_error "Ошибка синхронизации миграций"
    exit 1
fi

# 9. Применить миграции базы данных
log ""
log "🔄 Применение миграций базы данных..."
MIGRATION_OUTPUT=$(ssh $SERVER_USER@$SERVER "cd $APP_DIR/backend && source venv/bin/activate && alembic upgrade head 2>&1" | tee -a "$LOG_FILE")

if echo "$MIGRATION_OUTPUT" | grep -q "ERROR\|FAILED"; then
    show_error "Ошибка применения миграций!"
    log ""
    log "Вывод миграций:"
    log "════════════════════════════════════════"
    echo "$MIGRATION_OUTPUT" | tee -a "$LOG_FILE"
    log "════════════════════════════════════════"
    exit 1
elif echo "$MIGRATION_OUTPUT" | grep -q "Running upgrade"; then
    show_success "Миграции применены успешно"
    log "Применённые миграции:"
    echo "$MIGRATION_OUTPUT" | grep "Running upgrade" | tee -a "$LOG_FILE"
else
    show_success "База данных актуальна (нет новых миграций)"
fi

# 10. Исправить права доступа backend
log ""
log "🔐 Исправление прав доступа backend..."
if ssh $SERVER_USER@$SERVER "chown -R west_rashod:west_rashod $APP_DIR/backend" 2>&1 | tee -a "$LOG_FILE"; then
    show_success "Права доступа backend обновлены"
else
    show_warning "Ошибка обновления прав доступа (продолжаем...)"
fi

# 11. Перезапустить backend
log ""
log "🔄 Перезапуск backend..."
if ssh $SERVER_USER@$SERVER "systemctl restart west-rashod-backend.service" 2>&1 | tee -a "$LOG_FILE"; then
    show_success "Команда перезапуска выполнена"
else
    show_error "Ошибка выполнения команды перезапуска"
    show_backend_logs
    exit 1
fi

# 12. Подождать запуска
log ""
log "⏳ Ожидание запуска сервиса (10 сек)..."
sleep 10

# 13. Проверить статус backend
log ""
log "🔍 Проверка статуса backend..."
if ssh $SERVER_USER@$SERVER "systemctl is-active --quiet west-rashod-backend.service"; then
    show_success "Backend запущен"
else
    show_error "Backend не запустился!"
    show_backend_logs
    show_error_logs

    log ""
    log "🔙 Откат к предыдущей версии..."

    # Откат
    if ssh $SERVER_USER@$SERVER "
    cd $APP_DIR && \
    tar -xzf $BACKUP_DIR/west_rashod_$TIMESTAMP.tar.gz && \
    chown -R west_rashod:west_rashod $APP_DIR/backend/app && \
    systemctl restart west-rashod-backend.service
    " 2>&1 | tee -a "$LOG_FILE"; then
        show_warning "Откат выполнен. Проверьте логи выше."
    else
        show_error "КРИТИЧЕСКАЯ ОШИБКА: Откат не удался!"
        log "💡 Требуется ручное вмешательство:"
        log "   ssh $SERVER_USER@$SERVER"
        log "   cd $APP_DIR"
        log "   tar -xzf $BACKUP_DIR/west_rashod_$TIMESTAMP.tar.gz"
        log "   systemctl restart west-rashod-backend.service"
    fi
    exit 1
fi

# 14. Проверить API
log ""
log "🔍 Проверка API..."
API_RESPONSE=$(ssh $SERVER_USER@$SERVER "curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8005/api/v1/auth/login -H 'Content-Type: application/x-www-form-urlencoded' -d 'username=admin&password=admin'" 2>/dev/null)

if [ "$API_RESPONSE" = "200" ]; then
    show_success "API отвечает корректно (HTTP $API_RESPONSE)"
else
    show_error "API не отвечает! HTTP код: $API_RESPONSE"
    show_backend_logs
    show_error_logs
    log ""
    log "💡 Возможные причины:"
    log "   - Backend запустился, но падает при обработке запросов"
    log "   - Ошибка подключения к БД"
    log "   - Проблемы с зависимостями Python"
    log "   - Порт 8005 не слушается"
    log ""
    log "🔧 Команды для отладки:"
    log "   ssh $SERVER_USER@$SERVER 'journalctl -u west-rashod-backend.service -n 100'"
    log "   ssh $SERVER_USER@$SERVER 'systemctl status west-rashod-backend.service'"
    log "   ssh $SERVER_USER@$SERVER 'netstat -tulpn | grep 8005'"
    exit 1
fi

# 15. Проверить логи на ошибки
log ""
log "🔍 Проверка логов на ошибки..."
ERROR_COUNT=$(ssh $SERVER_USER@$SERVER "journalctl -u west-rashod-backend.service --since '2 minutes ago' --no-pager | grep -i 'error' | wc -l" 2>/dev/null || echo "0")

if [ "$ERROR_COUNT" -gt "0" ]; then
    show_warning "Найдено $ERROR_COUNT ошибок в логах"
    show_error_logs
else
    show_success "Ошибок в логах не найдено"
fi

# 16. Перезагрузить nginx
log ""
log "🔄 Перезагрузка nginx..."
if ssh $SERVER_USER@$SERVER "systemctl reload nginx" 2>&1 | tee -a "$LOG_FILE"; then
    show_success "Nginx перезагружен"
else
    show_warning "Ошибка перезагрузки nginx (не критично)"
fi

# 17. Финальная проверка
log ""
log "🎯 Финальная проверка всех сервисов..."
log "════════════════════════════════════════"

ALL_OK=true

if ! check_service_status "nginx" "Nginx"; then
    ALL_OK=false
fi

if ! check_service_status "west-rashod-backend.service" "Backend"; then
    ALL_OK=false
fi

if ! check_service_status "postgresql" "PostgreSQL"; then
    ALL_OK=false
fi

# Redis опционально
ssh $SERVER_USER@$SERVER "systemctl is-active --quiet redis" 2>/dev/null && show_success "Redis: работает" || show_warning "Redis: не работает (опционально)"

log "════════════════════════════════════════"

if [ "$ALL_OK" = false ]; then
    show_error "Некоторые сервисы не работают!"
    show_backend_logs
    exit 1
fi

log ""
log "${GREEN}🎉 Деплой успешно завершен!${NC}"
log "════════════════════════════════════════"
log "📍 URL: http://$SERVER"
log "🔐 Логин: admin / admin"
log "📝 Лог деплоя: $LOG_FILE"
log ""
log "📋 Доступные бекапы:"
ssh $SERVER_USER@$SERVER "ls -lh $BACKUP_DIR | tail -5" | tee -a "$LOG_FILE"
log ""
log "💡 Для отката к предыдущей версии:"
log "   ssh $SERVER_USER@$SERVER 'cd $APP_DIR && tar -xzf $BACKUP_DIR/west_rashod_$TIMESTAMP.tar.gz && systemctl restart west-rashod-backend.service'"
log ""
log "🔧 Полезные команды:"
log "   Просмотр логов: ssh $SERVER_USER@$SERVER 'journalctl -u west-rashod-backend.service -f'"
log "   Статус backend: ssh $SERVER_USER@$SERVER 'systemctl status west-rashod-backend.service'"
log "   Перезапуск: ssh $SERVER_USER@$SERVER 'systemctl restart west-rashod-backend.service'"
log ""
log "${GREEN}✨ Все проверки пройдены успешно!${NC}"
