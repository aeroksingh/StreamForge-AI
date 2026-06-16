#!/bin/bash

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_DIR="/run/media/ashutosh/in use/003_myprojects/streamforge ai/youtube-downloader"

echo -e "${GREEN}"
echo "  ____  _                       "
echo " / ___|| |_ _ __ ___  __ _ _ __ "
echo " \___ \| __| '__/ _ \/ _\` | '__|"
echo "  ___) | |_| | |  __/ (_| | |   "
echo " |____/ \__|_|  \___|\__,_|_|   "
echo "        StreamForge AI           "
echo -e "${NC}"

# ── Step 1: Docker ────────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/4] Starting Docker containers...${NC}"
cd "$PROJECT_DIR"
sudo docker compose up -d

# Wait for PostgreSQL to be ready
echo "      Waiting for PostgreSQL..."
until sudo docker exec youtube-downloader-postgres-1 pg_isready -U admin -d ytdownloader &>/dev/null; do
  sleep 1
done
echo -e "${GREEN}      ✓ Docker ready${NC}"

# ── Step 2: Python FastAPI ────────────────────────────────────────────────────
echo -e "${YELLOW}[2/4] Starting Python FastAPI service...${NC}"
cd "$PROJECT_DIR/python-service"
source venv/bin/activate
python3 -m uvicorn app.main:app --port 8001 &
FASTAPI_PID=$!
sleep 2
echo -e "${GREEN}      ✓ FastAPI running on :8001 (PID $FASTAPI_PID)${NC}"

# ── Step 3: Python Redis Worker ───────────────────────────────────────────────
echo -e "${YELLOW}[3/4] Starting Redis worker...${NC}"
python3 redis_worker.py &
WORKER_PID=$!
sleep 1
echo -e "${GREEN}      ✓ Worker running (PID $WORKER_PID)${NC}"

# ── Step 4: Spring Boot ───────────────────────────────────────────────────────
echo -e "${YELLOW}[4/4] Starting Spring Boot...${NC}"
cd "$PROJECT_DIR/spring-backend/backend"
./mvnw spring-boot:run &
SPRING_PID=$!

# Wait for Spring Boot to be ready
echo "      Waiting for Spring Boot..."
until curl -s http://localhost:8080/api/health &>/dev/null; do
  sleep 2
done
echo -e "${GREEN}      ✓ Spring Boot running on :8080 (PID $SPRING_PID)${NC}"

# ── All ready ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✓ StreamForge AI is running!           ${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Python API  → http://localhost:8001"
echo "  Spring Boot → http://localhost:8080"
echo "  API Docs    → http://localhost:8001/docs"
echo ""
echo -e "${YELLOW}  Press Ctrl+C to stop everything${NC}"
echo ""

# ── Cleanup on exit ───────────────────────────────────────────────────────────
cleanup() {
  echo ""
  echo -e "${RED}Stopping all services...${NC}"
  kill $FASTAPI_PID $WORKER_PID $SPRING_PID 2>/dev/null
  sudo docker compose -f "$PROJECT_DIR/docker-compose.yml" stop
  echo -e "${GREEN}All stopped. Bye!${NC}"
  exit 0
}

trap cleanup SIGINT SIGTERM

# Keep script running
wait
