#!/bin/bash
# Скрипт автоматического деплоя West Rashod на production сервер
# Usage: ./deploy.sh <server_ip> [options]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Параметры
SERVER_IP="${1:-192.168.45.98}"
SERVER_USER="root"
SERVER_PATH="/opt/west_rashod"
PROJECT_NAME="west_rashod"

# Опции
SKIP_CHECKS=false
SKIP_BACKUP=false
FORCE_REBUILD=false

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  West Rashod - Деплой${NC}"
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

show_help() {
    cat << EOF
West Rashod - Скрипт деплоя

Usage: $0 <server_ip> [options]

Параметры:
  server_ip              IP адрес сервера (по умолчанию: 192.168.45.98)

Опции:
  --skip-checks          Пропустить проверки сервера
  --skip-backup          Пропустить создание бэкапа
  --force-rebuild        Принудительная пересборка образов
  -h, --help             Показать эту справку

Примеры:
  $0 192.168.45.98
  $0 192.168.45.98 --skip-checks
  $0 192.168.45.98 --force-rebuild

EOF
    exit 0
}

# Парсинг аргументов
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-checks)
            SKIP_CHECKS=true
            shift
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --force-rebuild)
            FORCE_REBUILD=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            if [[ -z "$SERVER_IP" || "$SERVER_IP" == --* ]]; then
                SERVER_IP="$1"
            fi
            shift
            ;;
    esac
done

# 1. Проверка локальных зависимостей
check_local_requirements() {
    echo -e "\n${BLUE}1. Проверка локальных зависимостей${NC}"

    if ! command -v ssh &> /dev/null; then
        print_error "SSH не установлен"
        exit 1
    fi
    print_status "SSH доступен"

    if ! command -v rsync &> /dev/null; then
        print_error "rsync не установлен"
        print_info "Установите: brew install rsync (macOS) или apt-get install rsync (Linux)"
        exit 1
    fi
    print_status "rsync доступен"

    if ! command -v git &> /dev/null; then
        print_error "Git не установлен"
        exit 1
    fi
    print_status "Git доступен"
}

# 2. Проверка сервера
check_server() {
    if [ "$SKIP_CHECKS" = true ]; then
        print_warning "Проверка сервера пропущена (--skip-checks)"
        return 0
    fi

    echo -e "\n${BLUE}2. Проверка сервера${NC}"

    if [ -f "deployment/check-server.sh" ]; then
        chmod +x deployment/check-server.sh
        print_info "Запуск проверки сервера..."
        ./deployment/check-server.sh "$SERVER_IP"
    else
        print_warning "Скрипт проверки сервера не найден, пропуск..."
    fi
}

# 3. Подготовка .env файлов
prepare_env_files() {
    echo -e "\n${BLUE}3. Подготовка конфигурационных файлов${NC}"

    if [ ! -f "deployment/.env.prod" ]; then
        if [ -f "deployment/.env.prod.example" ]; then
            print_warning ".env.prod не найден, копирую из .env.prod.example"
            cp deployment/.env.prod.example deployment/.env.prod

            print_warning "ВАЖНО: Отредактируйте deployment/.env.prod перед деплоем!"
            print_info "Необходимо изменить:"
            print_info "  - POSTGRES_PASSWORD"
            print_info "  - SECRET_KEY"
            print_info "  - VITE_API_URL (если нужен другой IP)"

            read -p "Продолжить деплой? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_info "Деплой отменен"
                exit 1
            fi
        else
            print_error ".env.prod и .env.prod.example не найдены"
            exit 1
        fi
    else
        print_status ".env.prod найден"
    fi
}

# 4. Создание бэкапа на сервере
create_backup() {
    if [ "$SKIP_BACKUP" = true ]; then
        print_warning "Создание бэкапа пропущено (--skip-backup)"
        return 0
    fi

    echo -e "\n${BLUE}4. Создание бэкапа${NC}"

    if ssh ${SERVER_USER}@${SERVER_IP} "[ -d ${SERVER_PATH} ]" 2>/dev/null; then
        BACKUP_DIR="${SERVER_PATH}_backup_$(date +%Y%m%d_%H%M%S)"

        print_info "Создание бэкапа в $BACKUP_DIR..."

        ssh ${SERVER_USER}@${SERVER_IP} << EOF
            # Остановить текущие контейнеры
            cd ${SERVER_PATH} && docker compose -f docker-compose.prod.yml down || true

            # Создать бэкап базы данных
            if [ -d "${SERVER_PATH}/postgres_data" ]; then
                mkdir -p ${BACKUP_DIR}
                docker run --rm -v ${SERVER_PATH}/postgres_data:/data -v ${BACKUP_DIR}:/backup alpine tar czf /backup/postgres_data.tar.gz -C /data .
            fi

            # Копировать текущий код
            cp -r ${SERVER_PATH} ${BACKUP_DIR}/code

            echo "Бэкап создан: ${BACKUP_DIR}"
EOF
        print_status "Бэкап создан на сервере"
    else
        print_info "Директория проекта не найдена, бэкап не требуется"
    fi
}

# 5. Загрузка кода на сервер
upload_code() {
    echo -e "\n${BLUE}5. Загрузка кода на сервер${NC}"

    # Создать директорию на сервере
    ssh ${SERVER_USER}@${SERVER_IP} "mkdir -p ${SERVER_PATH}"

    # Список исключений для rsync
    cat > /tmp/rsync_exclude.txt << EOF
.git
.gitignore
.venv
venv
__pycache__
*.pyc
*.pyo
*.pyd
.Python
node_modules
.DS_Store
.env
.env.local
backend/logs/*.log
frontend/dist
frontend/.vite
.worktrees
*.swp
*.swo
*~
.vscode
.idea
EOF

    print_info "Синхронизация файлов с сервером..."

    rsync -avz --delete \
        --exclude-from=/tmp/rsync_exclude.txt \
        --progress \
        ./ ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/

    rm /tmp/rsync_exclude.txt

    print_status "Код загружен на сервер"
}

# 6. Установка Docker на сервере (если нужно)
install_docker() {
    echo -e "\n${BLUE}6. Проверка Docker на сервере${NC}"

    if ssh ${SERVER_USER}@${SERVER_IP} "command -v docker" &> /dev/null; then
        print_status "Docker уже установлен"
    else
        print_warning "Docker не установлен, устанавливаю..."

        ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
            # Установка Docker
            curl -fsSL https://get.docker.com -o get-docker.sh
            sh get-docker.sh
            rm get-docker.sh

            # Установка Docker Compose plugin
            apt-get update
            apt-get install -y docker-compose-plugin

            # Запуск Docker
            systemctl enable docker
            systemctl start docker

            echo "Docker установлен успешно"
EOF
        print_status "Docker установлен"
    fi
}

# 7. Сборка и запуск контейнеров
deploy_containers() {
    echo -e "\n${BLUE}7. Сборка и запуск контейнеров${NC}"

    BUILD_FLAG=""
    if [ "$FORCE_REBUILD" = true ]; then
        BUILD_FLAG="--build"
        print_info "Принудительная пересборка образов..."
    fi

    ssh ${SERVER_USER}@${SERVER_IP} << EOF
        cd ${SERVER_PATH}

        # Остановить и удалить старые контейнеры
        docker compose -f docker-compose.prod.yml down

        # Собрать и запустить новые контейнеры
        docker compose -f docker-compose.prod.yml up -d ${BUILD_FLAG}

        # Подождать запуска
        echo "Ожидание запуска контейнеров..."
        sleep 10

        # Проверить статус
        docker compose -f docker-compose.prod.yml ps
EOF

    print_status "Контейнеры запущены"
}

# 8. Проверка здоровья приложения
check_health() {
    echo -e "\n${BLUE}8. Проверка работоспособности${NC}"

    print_info "Ожидание инициализации приложения (30 секунд)..."
    sleep 30

    # Проверка backend
    if curl -f -s "http://${SERVER_IP}:8005/api/v1/health" &> /dev/null; then
        print_status "Backend доступен"
    else
        print_warning "Backend может быть недоступен, проверьте логи"
    fi

    # Проверка frontend через nginx
    if curl -f -s "http://${SERVER_IP}/health" &> /dev/null; then
        print_status "Frontend доступен"
    else
        print_warning "Frontend может быть недоступен"
    fi

    # Проверка базы данных
    if ssh ${SERVER_USER}@${SERVER_IP} "docker exec west_rashod_prod_db pg_isready -U rashod_user" &> /dev/null; then
        print_status "База данных работает"
    else
        print_warning "База данных может быть недоступна"
    fi
}

# 9. Показать логи
show_logs() {
    echo -e "\n${BLUE}9. Последние логи${NC}"

    ssh ${SERVER_USER}@${SERVER_IP} << EOF
        cd ${SERVER_PATH}
        docker compose -f docker-compose.prod.yml logs --tail=50
EOF
}

# 10. Финальная информация
show_summary() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}  Деплой завершен${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
    echo -e "${GREEN}Приложение доступно по адресам:${NC}"
    echo -e "  Frontend: ${BLUE}http://${SERVER_IP}${NC}"
    echo -e "  Backend API: ${BLUE}http://${SERVER_IP}:8005/docs${NC}"
    echo -e "  Прямой доступ к frontend: ${BLUE}http://${SERVER_IP}:5178${NC}"
    echo ""
    echo -e "${YELLOW}Логин по умолчанию:${NC} admin / admin"
    echo ""
    echo -e "${YELLOW}Полезные команды:${NC}"
    echo -e "  Логи: ssh ${SERVER_USER}@${SERVER_IP} 'cd ${SERVER_PATH} && docker compose -f docker-compose.prod.yml logs -f'"
    echo -e "  Рестарт: ssh ${SERVER_USER}@${SERVER_IP} 'cd ${SERVER_PATH} && docker compose -f docker-compose.prod.yml restart'"
    echo -e "  Остановка: ssh ${SERVER_USER}@${SERVER_IP} 'cd ${SERVER_PATH} && docker compose -f docker-compose.prod.yml down'"
    echo -e "  Обновление: ./deploy.sh ${SERVER_IP}"
    echo ""
}

# Главная функция
main() {
    print_header

    check_local_requirements
    check_server
    prepare_env_files
    create_backup
    upload_code
    install_docker
    deploy_containers
    check_health
    show_logs
    show_summary
}

# Запуск
main
