#!/bin/bash

# Скрипт для применения миграций БД на удаленном сервере West Rashod

SERVER="192.168.45.98"
SERVER_USER="root"
APP_DIR="/opt/west_rashod"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 Применение миграций БД West Rashod${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📅 Время: $(date)"
echo "🖥️  Сервер: $SERVER"
echo ""

# 1. Синхронизировать миграции
echo -e "${YELLOW}📦 Синхронизация файлов миграций...${NC}"
rsync -av backend/alembic/ $SERVER_USER@$SERVER:$APP_DIR/backend/alembic/

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Ошибка синхронизации миграций${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Файлы миграций синхронизированы${NC}"

# 2. Показать текущее состояние БД
echo ""
echo -e "${YELLOW}🔍 Текущее состояние БД:${NC}"
ssh $SERVER_USER@$SERVER "cd $APP_DIR/backend && source venv/bin/activate && alembic current"

# 3. Показать ожидающие миграции
echo ""
echo -e "${YELLOW}📋 Список миграций, которые будут применены:${NC}"
ssh $SERVER_USER@$SERVER "cd $APP_DIR/backend && source venv/bin/activate && alembic history"

# 4. Запросить подтверждение
echo ""
read -p "Применить миграции? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}⚠️  Операция отменена${NC}"
    exit 0
fi

# 5. Применить миграции
echo ""
echo -e "${YELLOW}🔄 Применение миграций...${NC}"
ssh $SERVER_USER@$SERVER "cd $APP_DIR/backend && source venv/bin/activate && alembic upgrade head"

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ ОШИБКА: Миграции не были применены!${NC}"
    echo ""
    echo -e "${YELLOW}🔧 Команды для отладки:${NC}"
    echo "   ssh $SERVER_USER@$SERVER 'cd $APP_DIR/backend && source venv/bin/activate && alembic current'"
    echo "   ssh $SERVER_USER@$SERVER 'cd $APP_DIR/backend && source venv/bin/activate && alembic history'"
    echo "   ssh $SERVER_USER@$SERVER 'psql -U rashod_user -d west_rashod_db -c \"SELECT * FROM alembic_version;\"'"
    exit 1
fi

# 6. Показать новое состояние
echo ""
echo -e "${GREEN}✅ Миграции применены успешно!${NC}"
echo ""
echo -e "${YELLOW}🔍 Новое состояние БД:${NC}"
ssh $SERVER_USER@$SERVER "cd $APP_DIR/backend && source venv/bin/activate && alembic current"

# 7. Перезапустить backend
echo ""
read -p "Перезапустить backend сервис? (yes/no): " RESTART

if [ "$RESTART" = "yes" ]; then
    echo -e "${YELLOW}🔄 Перезапуск backend...${NC}"
    ssh $SERVER_USER@$SERVER "systemctl restart west-rashod-backend.service"

    sleep 3

    if ssh $SERVER_USER@$SERVER "systemctl is-active --quiet west-rashod-backend.service"; then
        echo -e "${GREEN}✅ Backend успешно перезапущен${NC}"
    else
        echo -e "${RED}❌ Backend не запустился. Проверьте логи:${NC}"
        echo "   ssh $SERVER_USER@$SERVER 'journalctl -u west-rashod-backend.service -n 50'"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}🎉 Готово!${NC}"
echo ""
echo -e "${BLUE}💡 Полезные команды:${NC}"
echo "   Текущая версия БД: ssh $SERVER_USER@$SERVER 'cd $APP_DIR/backend && source venv/bin/activate && alembic current'"
echo "   История миграций:  ssh $SERVER_USER@$SERVER 'cd $APP_DIR/backend && source venv/bin/activate && alembic history'"
echo "   Откат на 1 шаг:    ssh $SERVER_USER@$SERVER 'cd $APP_DIR/backend && source venv/bin/activate && alembic downgrade -1'"
echo ""
