#!/bin/bash
# West Rashod - Quick Development Start Script
# Usage: ./start-dev.sh [option]
# Options:
#   all       - Start everything (DB + Backend + Frontend)
#   db        - Start only PostgreSQL
#   backend   - Start only Backend (requires DB)
#   frontend  - Start only Frontend
#   stop      - Stop all Docker containers
#   reset     - Reset DB and restart
#   logs      - Show backend logs

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  West Rashod Development${NC}"
    echo -e "${BLUE}================================${NC}"
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

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        exit 1
    fi
}

check_node() {
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed"
        exit 1
    fi
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
}

start_db() {
    print_status "Starting PostgreSQL on port 54330..."
    cd "$PROJECT_DIR"
    docker compose up -d db

    # Wait for DB to be ready
    echo -n "Waiting for PostgreSQL..."
    for i in {1..30}; do
        if docker compose exec -T db pg_isready -U rashod_user -d west_rashod_db &> /dev/null; then
            echo ""
            print_status "PostgreSQL is ready!"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    echo ""
    print_error "PostgreSQL failed to start"
    exit 1
}

start_backend() {
    print_status "Starting Backend on port 8005..."
    cd "$BACKEND_DIR"

    # Create venv if not exists
    if [ ! -d "venv" ]; then
        print_warning "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    # Activate venv
    source venv/bin/activate

    # Install dependencies
    if [ ! -f "venv/.deps_installed" ]; then
        print_status "Installing Python dependencies..."
        pip install -r requirements.txt -q
        touch venv/.deps_installed
    fi

    # Run migrations
    print_status "Running database migrations..."
    alembic upgrade head 2>/dev/null || print_warning "Migrations may have failed, continuing..."

    # Check if admin exists
    python3 -c "
from app.db.session import SessionLocal
from app.db.models import User
db = SessionLocal()
admin = db.query(User).filter(User.username == 'admin').first()
if not admin:
    print('ADMIN_NEEDED')
db.close()
" 2>/dev/null | grep -q "ADMIN_NEEDED" && {
        print_status "Creating admin user (admin/admin)..."
        python3 scripts/create_admin.py 2>/dev/null || true
    }

    # Start uvicorn
    print_status "Starting uvicorn server..."
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8005
}

start_frontend() {
    print_status "Starting Frontend on port 5178..."
    cd "$FRONTEND_DIR"

    # Install npm dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_status "Installing npm dependencies..."
        npm install
    fi

    # Start Vite dev server
    npm run dev -- --port 5178 --host
}

start_all() {
    print_header
    check_docker
    check_python
    check_node

    # Start DB
    start_db

    # Start backend and frontend in parallel
    print_status "Starting Backend and Frontend..."

    # Create a trap to kill both processes on exit
    trap 'kill $(jobs -p) 2>/dev/null' EXIT

    # Start backend in background
    (cd "$BACKEND_DIR" && source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate && \
        pip install -r requirements.txt -q 2>/dev/null && \
        alembic upgrade head 2>/dev/null; \
        python3 scripts/create_admin.py 2>/dev/null; \
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8005) &
    BACKEND_PID=$!

    # Give backend time to start
    sleep 3

    # Start frontend in background
    (cd "$FRONTEND_DIR" && npm install 2>/dev/null && npm run dev -- --port 5178 --host) &
    FRONTEND_PID=$!

    print_status "Services starting..."
    echo ""
    echo -e "${GREEN}Access URLs:${NC}"
    echo -e "  Frontend: ${BLUE}http://localhost:5178${NC}"
    echo -e "  Backend API: ${BLUE}http://localhost:8005/docs${NC}"
    echo -e "  Login: ${YELLOW}admin / admin${NC}"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

    # Wait for both processes
    wait
}

stop_all() {
    print_status "Stopping all services..."
    cd "$PROJECT_DIR"
    docker compose down

    # Kill any running uvicorn or vite processes
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true

    print_status "All services stopped"
}

reset_db() {
    print_warning "Resetting database..."
    cd "$PROJECT_DIR"
    docker compose down -v
    start_db

    cd "$BACKEND_DIR"
    source venv/bin/activate
    alembic upgrade head
    python3 scripts/create_admin.py
    print_status "Database reset complete"
}

show_logs() {
    cd "$PROJECT_DIR"
    docker compose logs -f backend
}

# Main script
case "${1:-all}" in
    all)
        start_all
        ;;
    db)
        check_docker
        start_db
        ;;
    backend)
        check_python
        start_backend
        ;;
    frontend)
        check_node
        start_frontend
        ;;
    stop)
        stop_all
        ;;
    reset)
        check_docker
        reset_db
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "West Rashod Development Script"
        echo ""
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  all       - Start everything (default)"
        echo "  db        - Start only PostgreSQL"
        echo "  backend   - Start only Backend"
        echo "  frontend  - Start only Frontend"
        echo "  stop      - Stop all services"
        echo "  reset     - Reset database"
        echo "  logs      - Show Docker logs"
        ;;
esac
