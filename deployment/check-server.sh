#!/bin/bash
# Скрипт проверки сервера перед деплоем
# Usage: ./check-server.sh <server_ip>

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVER_IP="${1:-192.168.45.98}"
SERVER_USER="root"

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Проверка сервера для деплоя${NC}"
    echo -e "${BLUE}  IP: $SERVER_IP${NC}"
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

check_ssh() {
    echo -e "\n${BLUE}1. Проверка SSH соединения${NC}"
    if ssh -o ConnectTimeout=5 -o BatchMode=yes ${SERVER_USER}@${SERVER_IP} exit 2>/dev/null; then
        print_status "SSH соединение установлено"
        return 0
    else
        print_error "SSH соединение не удалось"
        print_info "Попробуйте: ssh ${SERVER_USER}@${SERVER_IP}"
        exit 1
    fi
}

check_system() {
    echo -e "\n${BLUE}2. Проверка системной информации${NC}"

    OS_INFO=$(ssh ${SERVER_USER}@${SERVER_IP} "cat /etc/os-release 2>/dev/null | grep PRETTY_NAME" | cut -d'"' -f2)
    KERNEL=$(ssh ${SERVER_USER}@${SERVER_IP} "uname -r")
    ARCH=$(ssh ${SERVER_USER}@${SERVER_IP} "uname -m")

    print_info "ОС: ${OS_INFO}"
    print_info "Ядро: ${KERNEL}"
    print_info "Архитектура: ${ARCH}"

    # Проверка места на диске
    DISK_USAGE=$(ssh ${SERVER_USER}@${SERVER_IP} "df -h / | awk 'NR==2 {print \$5}'" | sed 's/%//')
    DISK_AVAIL=$(ssh ${SERVER_USER}@${SERVER_IP} "df -h / | awk 'NR==2 {print \$4}'")

    print_info "Использовано диска: ${DISK_USAGE}%"
    print_info "Доступно: ${DISK_AVAIL}"

    if [ "$DISK_USAGE" -gt 90 ]; then
        print_warning "Мало места на диске!"
    else
        print_status "Достаточно места на диске"
    fi

    # Проверка RAM
    RAM_TOTAL=$(ssh ${SERVER_USER}@${SERVER_IP} "free -h | awk 'NR==2 {print \$2}'")
    RAM_USED=$(ssh ${SERVER_USER}@${SERVER_IP} "free -h | awk 'NR==2 {print \$3}'")
    RAM_AVAIL=$(ssh ${SERVER_USER}@${SERVER_IP} "free -h | awk 'NR==2 {print \$7}'")

    print_info "RAM: $RAM_USED / $RAM_TOTAL используется, доступно: $RAM_AVAIL"
}

check_docker() {
    echo -e "\n${BLUE}3. Проверка Docker${NC}"

    if ssh ${SERVER_USER}@${SERVER_IP} "command -v docker" &> /dev/null; then
        DOCKER_VERSION=$(ssh ${SERVER_USER}@${SERVER_IP} "docker --version")
        print_status "Docker установлен: $DOCKER_VERSION"

        # Проверка Docker Compose
        if ssh ${SERVER_USER}@${SERVER_IP} "docker compose version" &> /dev/null; then
            COMPOSE_VERSION=$(ssh ${SERVER_USER}@${SERVER_IP} "docker compose version")
            print_status "Docker Compose установлен: $COMPOSE_VERSION"
        else
            print_warning "Docker Compose не установлен"
            print_info "Установка: sudo apt-get update && sudo apt-get install docker-compose-plugin"
        fi
    else
        print_error "Docker не установлен"
        print_info "Установка Docker:"
        print_info "  curl -fsSL https://get.docker.com -o get-docker.sh"
        print_info "  sudo sh get-docker.sh"
        print_info "  sudo usermod -aG docker \$USER"
    fi
}

check_nginx() {
    echo -e "\n${BLUE}4. Проверка Nginx${NC}"

    if ssh ${SERVER_USER}@${SERVER_IP} "command -v nginx" &> /dev/null; then
        NGINX_VERSION=$(ssh ${SERVER_USER}@${SERVER_IP} "nginx -v 2>&1")
        print_status "Nginx установлен: $NGINX_VERSION"

        # Проверка запущен ли nginx
        if ssh ${SERVER_USER}@${SERVER_IP} "systemctl is-active nginx" &> /dev/null; then
            print_status "Nginx запущен"
        else
            print_warning "Nginx не запущен"
        fi
    else
        print_warning "Nginx не установлен"
        print_info "Установка: sudo apt-get install nginx"
    fi
}

check_ports() {
    echo -e "\n${BLUE}5. Проверка портов${NC}"

    PORTS=(80 443 8005 5178)

    for port in "${PORTS[@]}"; do
        if ssh ${SERVER_USER}@${SERVER_IP} "ss -tulpn | grep :$port" &> /dev/null; then
            PROCESS=$(ssh ${SERVER_USER}@${SERVER_IP} "ss -tulpn | grep :$port | head -n1")
            print_warning "Порт $port занят: $PROCESS"
        else
            print_status "Порт $port свободен"
        fi
    done
}

check_firewall() {
    echo -e "\n${BLUE}6. Проверка Firewall${NC}"

    if ssh ${SERVER_USER}@${SERVER_IP} "command -v ufw" &> /dev/null; then
        UFW_STATUS=$(ssh ${SERVER_USER}@${SERVER_IP} "sudo ufw status" 2>&1)

        if echo "$UFW_STATUS" | grep -q "inactive"; then
            print_warning "UFW выключен"
            print_info "Рекомендуется включить: sudo ufw enable"
        else
            print_status "UFW активен"
            echo "$UFW_STATUS" | grep -E "(80|443|22)" | while read line; do
                print_info "$line"
            done
        fi
    else
        print_info "UFW не установлен (необязательно для локальной сети)"
    fi
}

check_git() {
    echo -e "\n${BLUE}7. Проверка Git${NC}"

    if ssh ${SERVER_USER}@${SERVER_IP} "command -v git" &> /dev/null; then
        GIT_VERSION=$(ssh ${SERVER_USER}@${SERVER_IP} "git --version")
        print_status "Git установлен: $GIT_VERSION"
    else
        print_warning "Git не установлен"
        print_info "Установка: sudo apt-get install git"
    fi
}

check_network() {
    echo -e "\n${BLUE}8. Проверка сетевой конфигурации${NC}"

    # Получить IP адреса
    IPS=$(ssh ${SERVER_USER}@${SERVER_IP} "hostname -I")
    print_info "IP адреса сервера: $IPS"

    # Hostname
    HOSTNAME=$(ssh ${SERVER_USER}@${SERVER_IP} "hostname")
    print_info "Hostname: $HOSTNAME"

    # Проверка доступа к 1С
    print_info "Проверка доступа к 1С (10.10.100.77)..."
    if ssh ${SERVER_USER}@${SERVER_IP} "ping -c 1 -W 2 10.10.100.77" &> /dev/null; then
        print_status "1С сервер доступен"
    else
        print_warning "1С сервер недоступен"
    fi
}

check_dependencies() {
    echo -e "\n${BLUE}9. Проверка дополнительных зависимостей${NC}"

    # Python
    if ssh ${SERVER_USER}@${SERVER_IP} "command -v python3" &> /dev/null; then
        PYTHON_VERSION=$(ssh ${SERVER_USER}@${SERVER_IP} "python3 --version")
        print_status "$PYTHON_VERSION установлен"
    else
        print_warning "Python3 не установлен"
    fi

    # Node.js
    if ssh ${SERVER_USER}@${SERVER_IP} "command -v node" &> /dev/null; then
        NODE_VERSION=$(ssh ${SERVER_USER}@${SERVER_IP} "node --version")
        print_status "Node.js $NODE_VERSION установлен"
    else
        print_info "Node.js не установлен (не обязательно при использовании Docker)"
    fi
}

show_summary() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}  Сводка${NC}"
    echo -e "${BLUE}================================${NC}"
    echo -e ""
    echo -e "Сервер готов к деплою, если все критические проверки пройдены."
    echo -e ""
    echo -e "${YELLOW}Следующие шаги:${NC}"
    echo -e "1. Если Docker не установлен - установите его"
    echo -e "2. Настройте .env файлы для production"
    echo -e "3. Запустите ./deploy.sh ${SERVER_IP} для деплоя"
    echo -e ""
}

# Main
print_header
check_ssh
check_system
check_docker
check_nginx
check_ports
check_firewall
check_git
check_network
check_dependencies
show_summary
