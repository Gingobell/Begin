#!/usr/bin/env bash
# ─────────────────────────────────────────────────────
# FortuneDiary — local dev launcher
# Starts backend (FastAPI) + frontend (Next.js) together.
# Press Ctrl+C to stop both.
# ─────────────────────────────────────────────────────
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting FortuneDiary local dev...${NC}"
echo ""

# ── Check backend .env ───────────────────────────────
if [ ! -f "$ROOT_DIR/backend/.env" ]; then
  echo -e "${YELLOW}⚠️  backend/.env not found! Copy backend/.env.example and fill in your keys.${NC}"
  exit 1
fi

# ── Setup Python virtual environment ─────────────────
if [ ! -d "$ROOT_DIR/backend/.venv" ]; then
  echo -e "${BLUE}🐍 Creating Python virtual environment...${NC}"
  
  # Try Python 3.13 first, fallback to 3.12, then 3.11
  if command -v python3.13 &> /dev/null; then
    PYTHON_CMD="python3.13"
    echo -e "${GREEN}✓ Using Python 3.13${NC}"
  elif command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
    echo -e "${GREEN}✓ Using Python 3.12${NC}"
  elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    echo -e "${GREEN}✓ Using Python 3.11${NC}"
  else
    echo -e "${YELLOW}⚠️  Python 3.11+ not found! Please install Python 3.12 or 3.13:${NC}"
    echo -e "${YELLOW}   brew install python@3.13${NC}"
    exit 1
  fi
  
  (cd "$ROOT_DIR/backend" && $PYTHON_CMD -m venv .venv)
  echo -e "${GREEN}✓ Virtual environment created${NC}"
  
  # Install dependencies
  echo -e "${BLUE}📦 Installing backend dependencies...${NC}"
  (
    cd "$ROOT_DIR/backend"
    source .venv/bin/activate
    pip install --upgrade pip --quiet
    pip install -e . --quiet
  )
  echo -e "${GREEN}✓ Dependencies installed${NC}"
  echo ""
fi

# ── Install frontend deps if needed ──────────────────
if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo -e "${BLUE}📦 Installing frontend deps...${NC}"
  (cd "$ROOT_DIR/frontend" && npm install)
  echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
  echo ""
fi

# ── Start backend ────────────────────────────────────
echo -e "${GREEN}▶ Backend → http://localhost:8000${NC}"
(
  cd "$ROOT_DIR/backend"
  # Activate virtual environment
  source .venv/bin/activate
  # Load .env for the backend process
  set -a; source .env; set +a
  uvicorn app.main:app --reload --port 8000 --timeout-keep-alive 300
) &
BACKEND_PID=$!

# ── Start frontend ───────────────────────────────────
echo -e "${GREEN}▶ Frontend → http://localhost:3000${NC}"
(
  cd "$ROOT_DIR/frontend"
  npm run dev
) &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}✅ Both running. Press Ctrl+C to stop.${NC}"
echo ""

# ── Cleanup on exit ──────────────────────────────────
cleanup() {
  echo ""
  echo -e "${YELLOW}🛑 Shutting down...${NC}"
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
  echo -e "${GREEN}👋 Done.${NC}"
}
trap cleanup EXIT INT TERM

wait
