#!/bin/bash

# Безопасный скрипт деплоя West Rashod
# Создает бекап и проверяет работоспособность после деплоя

set -e  # Остановка при ошибке

SERVER="192.168.45.98"
SERVER_USER="root"
APP_DIR="/opt/west_rashod"
BACKUP_DIR="/opt/backups/west_rashod"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🚀 Начало безопасного деплоя West Rashod..."
echo "📅 Время: $(date)"
echo "🖥️  Сервер: $SERVER"
echo ""

# 1. Создать директорию для бекапов
echo "📦 Создание директории для бекапов..."
ssh $SERVER_USER@$SERVER "mkdir -p $BACKUP_DIR"

# 2. Создать бекап текущей версии
echo "💾 Создание бекапа текущей версии..."
ssh $SERVER_USER@$SERVER "
cd $APP_DIR && \
tar -czf $BACKUP_DIR/west_rashod_$TIMESTAMP.tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='logs' \
  --exclude='node_modules' \
  backend/app frontend/src frontend/package.json frontend/vite.config.ts
"
echo "✅ Бекап создан: $BACKUP_DIR/west_rashod_$TIMESTAMP.tar.gz"

# 3. Синхронизировать backend код
echo ""
echo "📤 Синхронизация backend кода..."
rsync -av --delete \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='venv' \
  --exclude='logs' \
  --exclude='.env' \
  backend/app/ $SERVER_USER@$SERVER:$APP_DIR/backend/app/

# 4. Синхронизировать frontend код
echo "📤 Синхронизация frontend исходников..."
rsync -av \
  --exclude='node_modules' \
  --exclude='dist' \
  frontend/src/ $SERVER_USER@$SERVER:$APP_DIR/frontend/src/

rsync -av \
  frontend/package.json \
  frontend/vite.config.ts \
  frontend/index.html \
  $SERVER_USER@$SERVER:$APP_DIR/frontend/

# 5. Обновить .env.production для frontend
echo "⚙️  Обновление конфигурации frontend..."
ssh $SERVER_USER@$SERVER "cat > $APP_DIR/frontend/.env.production << 'EOF'
VITE_API_URL=http://$SERVER
EOF
"

# 6. Собрать frontend
echo "🔨 Сборка frontend..."
ssh $SERVER_USER@$SERVER "cd $APP_DIR/frontend && npm run build"

# 7. Обновить frontend на продакшене
echo "📦 Обновление frontend на продакшене..."
ssh $SERVER_USER@$SERVER "
rm -rf /var/www/west_rashod/* && \
cp -r $APP_DIR/frontend/dist/* /var/www/west_rashod/ && \
chown -R www-data:www-data /var/www/west_rashod
"

# 8. Исправить права доступа backend
echo "🔐 Исправление прав доступа backend..."
ssh $SERVER_USER@$SERVER "chown -R west_rashod:west_rashod $APP_DIR/backend/app"

# 9. Перезапустить backend
echo "🔄 Перезапуск backend..."
ssh $SERVER_USER@$SERVER "systemctl restart west-rashod-backend.service"

# 10. Подождать запуска
echo "⏳ Ожидание запуска сервиса (10 сек)..."
sleep 10

# 11. Проверить статус backend
echo ""
echo "🔍 Проверка статуса backend..."
if ssh $SERVER_USER@$SERVER "systemctl is-active --quiet west-rashod-backend.service"; then
    echo "✅ Backend запущен"
else
    echo "❌ ОШИБКА: Backend не запустился!"
    echo "🔙 Откат к предыдущей версии..."

    # Откат
    ssh $SERVER_USER@$SERVER "
    cd $APP_DIR && \
    tar -xzf $BACKUP_DIR/west_rashod_$TIMESTAMP.tar.gz && \
    chown -R west_rashod:west_rashod $APP_DIR/backend/app && \
    systemctl restart west-rashod-backend.service
    "

    echo "⚠️  Откат выполнен. Проверьте логи."
    exit 1
fi

# 12. Проверить API
echo "🔍 Проверка API..."
API_RESPONSE=$(ssh $SERVER_USER@$SERVER "curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8005/api/v1/auth/login -H 'Content-Type: application/x-www-form-urlencoded' -d 'username=admin&password=admin'")

if [ "$API_RESPONSE" = "200" ]; then
    echo "✅ API отвечает корректно (HTTP $API_RESPONSE)"
else
    echo "❌ ОШИБКА: API не отвечает! HTTP код: $API_RESPONSE"
    echo "⚠️  Backend запущен, но API не работает. Проверьте логи вручную."
    exit 1
fi

# 13. Проверить логи на ошибки
echo "🔍 Проверка логов на ошибки..."
ERROR_COUNT=$(ssh $SERVER_USER@$SERVER "journalctl -u west-rashod-backend.service --since '2 minutes ago' --no-pager | grep -i 'error' | wc -l" || echo "0")

if [ "$ERROR_COUNT" -gt "0" ]; then
    echo "⚠️  Найдено $ERROR_COUNT ошибок в логах. Проверьте:"
    echo "   ssh $SERVER_USER@$SERVER 'journalctl -u west-rashod-backend.service -n 50'"
else
    echo "✅ Ошибок в логах не найдено"
fi

# 14. Перезагрузить nginx
echo "🔄 Перезагрузка nginx..."
ssh $SERVER_USER@$SERVER "systemctl reload nginx"

# 15. Финальная проверка
echo ""
echo "🎯 Финальная проверка всех сервисов..."
ssh $SERVER_USER@$SERVER "
systemctl is-active --quiet nginx && echo '✅ Nginx: running' || echo '❌ Nginx: stopped'
systemctl is-active --quiet west-rashod-backend.service && echo '✅ Backend: running' || echo '❌ Backend: stopped'
systemctl is-active --quiet postgresql && echo '✅ PostgreSQL: running' || echo '❌ PostgreSQL: stopped'
systemctl is-active --quiet redis && echo '✅ Redis: running' || echo '❌ Redis: stopped'
"

echo ""
echo "🎉 Деплой успешно завершен!"
echo "📍 URL: http://$SERVER"
echo "🔐 Логин: admin / admin"
echo ""
echo "📋 Доступные бекапы:"
ssh $SERVER_USER@$SERVER "ls -lh $BACKUP_DIR | tail -5"
echo ""
echo "💡 Для отката к предыдущей версии:"
echo "   ssh $SERVER_USER@$SERVER 'cd $APP_DIR && tar -xzf $BACKUP_DIR/west_rashod_$TIMESTAMP.tar.gz && systemctl restart west-rashod-backend.service'"
