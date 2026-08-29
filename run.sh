#!/bin/bash
# Parallel development runner for GTO Poker Trainer
# Starts: PostgreSQL, Redis, Backend API, Frontend, Training Worker

set -e

cd /home/tuanlinh/poker

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     GTO Poker Trainer - Parallel Development Runner      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"

# Kill existing processes on ports
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    pkill -f "uvicorn.*gto.api.main" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    pkill -f "gto.worker.main" 2>/dev/null || true
    pkill -f "celery.*worker" 2>/dev/null || true
    docker compose down 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM

# Start Docker services (PostgreSQL + Redis)
echo -e "${BLUE}[1/5] Starting PostgreSQL & Redis...${NC}"
docker compose up -d postgres redis 2>/dev/null || {
    cat > docker-compose.yml << 'EOF'
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: gto_trainer
      POSTGRES_USER: gto
      POSTGRES_PASSWORD: gto_dev_password
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U gto"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: [redis_data:/data]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  postgres_data:
  redis_data:
EOF
    docker compose up -d
}

# Wait for services
echo -e "${BLUE}[2/5] Waiting for services...${NC}"
until docker compose exec -T postgres pg_isready -U gto >/dev/null 2>&1; do sleep 1; done
until docker compose exec -T redis redis-cli ping >/dev/null 2>&1; do sleep 1; done
echo -e "${GREEN}✓ Services ready${NC}"

# Setup database
echo -e "${BLUE}[3/5] Setting up database...${NC}"
.venv/bin/python -c "
import asyncio
from gto.db import init_db
asyncio.run(init_db())
print('Database initialized')
" 2>/dev/null || echo "DB init skipped (may already exist)"

# Activate venv
source .venv/bin/activate
export PYTHONPATH=/home/tuanlinh/poker:$PYTHONPATH
export DATABASE_URL=postgresql+asyncpg://gto:gto_dev_password@localhost:5432/gto_trainer
export REDIS_URL=redis://localhost:6379/0
export SECRET_KEY=dev-secret-change-in-production
export API_HOST=0.0.0.0
export API_PORT=8000
export FRONTEND_URL=http://localhost:3000

# Start Backend API
echo -e "${BLUE}[4/5] Starting Backend API (port 8000)...${NC}"
.venv/bin/python -m uvicorn gto.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir gto > logs/api.log 2>&1 &
API_PID=$!
sleep 3

# Check API health
for i in {1..10}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend API running on http://localhost:8000${NC}"
        break
    fi
    sleep 1
done

# Start Celery Worker (for training jobs)
echo -e "${BLUE}[5/5] Starting Training Worker...${NC}"
.venv/bin/python -m celery -A gto.worker.celery_app worker --loglevel=info --concurrency=2 > logs/worker.log 2>&1 &
WORKER_PID=$!
sleep 2
echo -e "${GREEN}✓ Training worker started${NC}"

# Start Frontend
echo -e "${BLUE}Starting Frontend (port 3000)...${NC}"
cd frontend
export PATH=/tmp/node-v20.15.0-linux-x64/bin:$PATH
npm install --prefer-offline 2>/dev/null || npm install
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo -e "\n${GREEN}══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}All services running!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════${NC}"
echo -e "  ${BLUE}Frontend:${NC}     http://localhost:3000"
echo -e "  ${BLUE}Backend API:${NC}  http://localhost:8000"
echo -e "  ${BLUE}API Docs:${NC}     http://localhost:8000/docs"
echo -e "  ${BLUE}PostgreSQL:${NC}   localhost:5432"
echo -e "  ${BLUE}Redis:${NC}        localhost:6379"
echo -e "\n${YELLOW}Logs:${NC} tail -f logs/*.log"
echo -e "${YELLOW}Stop:${NC}  Ctrl+C"
echo -e "${GREEN}══════════════════════════════════════════════════════════${NC}\n"

# Keep running
wait $API_PID $WORKER_PID $FRONTEND_PID