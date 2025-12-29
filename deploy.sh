#!/bin/bash

set -e

SERVER="root@192.168.45.98"
PROJECT_NAME="west-rashod"
REMOTE_DIR="/opt/$PROJECT_NAME"
BACKUP_DIR="/opt/${PROJECT_NAME}-backups"

echo "=== Deploying West Поток to $SERVER ==="

# Проверка наличия .env.production
if [ ! -f ".env.production" ]; then
    echo "Error: .env.production file not found!"
    echo "Please create .env.production from deployment/.env.prod"
    exit 1
fi

# Создание бэкапа БД перед деплоем
echo ""
echo "[1/8] Creating database backup..."
ssh $SERVER "mkdir -p $BACKUP_DIR"
BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql.gz"
ssh $SERVER "cd $REMOTE_DIR && docker compose exec -T db pg_dump -U rashod_user west_rashod_db 2>/dev/null | gzip > $BACKUP_DIR/$BACKUP_FILE || echo 'No existing database to backup'"
echo "Backup saved to $BACKUP_DIR/$BACKUP_FILE"

# Копирование конфигов на сервер
echo ""
echo "[2/8] Copying configs to server..."
ssh $SERVER "mkdir -p $REMOTE_DIR/nginx"
scp docker-compose.prod.yml $SERVER:$REMOTE_DIR/docker-compose.yml
scp .env.production $SERVER:$REMOTE_DIR/.env
scp -r nginx/* $SERVER:$REMOTE_DIR/nginx/

# Сборка образов локально
echo ""
echo "[3/8] Building backend image locally..."
docker buildx build --platform linux/amd64 \
    -f ./backend/Dockerfile.production \
    -t ${PROJECT_NAME}-backend:latest \
    ./backend --load

echo ""
echo "[4/8] Building frontend image locally..."
docker buildx build --platform linux/amd64 \
    --build-arg VITE_API_URL=http://192.168.45.98 \
    -f ./frontend/Dockerfile.prod \
    -t ${PROJECT_NAME}-frontend:latest \
    ./frontend --load

# Загрузка образов на сервер
echo ""
echo "[5/8] Uploading backend image to server..."
docker save ${PROJECT_NAME}-backend:latest | gzip | \
    ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=3 $SERVER "gunzip | docker load"

echo ""
echo "[6/8] Uploading frontend image to server..."
docker save ${PROJECT_NAME}-frontend:latest | gzip | \
    ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=3 $SERVER "gunzip | docker load"

# Остановка старых сервисов
echo ""
echo "[7/8] Stopping old services..."
ssh $SERVER "cd $REMOTE_DIR && docker compose stop backend frontend nginx 2>/dev/null || true"

# Запуск сервисов
echo ""
echo "[8/8] Starting services..."
ssh $SERVER "cd $REMOTE_DIR && docker compose pull db redis nginx && docker compose up -d"

# Ожидание PostgreSQL
echo ""
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if ssh $SERVER "cd $REMOTE_DIR && docker compose exec -T db pg_isready -U rashod_user" 2>/dev/null; then
        echo "PostgreSQL is ready"
        break
    fi
    echo "Waiting for PostgreSQL... ($i/30)"
    sleep 2
done

# Ожидание backend
echo ""
echo "Waiting for backend to start..."
sleep 10

# Проверка логов
echo ""
echo "Checking backend logs..."
ssh $SERVER "cd $REMOTE_DIR && docker compose logs backend --tail 30"

# Статус сервисов
echo ""
echo "=== Service Status ==="
ssh $SERVER "cd $REMOTE_DIR && docker compose ps"

# Очистка
echo ""
echo "Cleaning up old images..."
ssh $SERVER "docker image prune -f"

echo ""
echo "=== Deployment completed! ==="
echo "Frontend: http://192.168.45.98"
echo "Backend API: http://192.168.45.98/api"
echo "API Docs: http://192.168.45.98/docs"
echo ""
echo "Login: admin / admin"
echo ""
echo "Database backup: $BACKUP_DIR/$BACKUP_FILE"
echo ""
echo "Useful commands:"
echo "  Logs: ssh $SERVER 'cd $REMOTE_DIR && docker compose logs -f'"
echo "  Status: ssh $SERVER 'cd $REMOTE_DIR && docker compose ps'"
echo "  Restart: ssh $SERVER 'cd $REMOTE_DIR && docker compose restart'"
