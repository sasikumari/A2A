#!/usr/bin/env bash
# ============================================================
# start_all.sh  —  Start the full A2A + DocGen integrated stack
# ============================================================
# Services:
#   1. A2A Backend   (FastAPI)  → http://localhost:8000
#   2. DocGen Service(FastAPI)  → http://localhost:8001
#   3. Frontend      (Vite)     → http://localhost:5173
# ============================================================

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "========================================"
echo "  NPCI AgentHub — Full Stack Launcher   "
echo "========================================"
echo ""

# ── 1. A2A Backend ──────────────────────────────────────────
echo "[1/3] Starting A2A Backend on :8000 ..."
(
  cd "$ROOT/backend"
  [ -f ".venv/bin/activate" ] && source .venv/bin/activate
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
) &
BACKEND_PID=$!
echo "  PID $BACKEND_PID"

# ── 2. DocGen Service ────────────────────────────────────────
echo "[2/3] Starting DocGen Service on :8001 ..."
(
  cd "$ROOT/document_gen/docgen"
  [ -f ".venv/bin/activate" ] && source .venv/bin/activate
  uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
) &
DOCGEN_PID=$!
echo "  PID $DOCGEN_PID"

# ── 3. Frontend ──────────────────────────────────────────────
echo "[3/3] Starting Frontend (Vite) on :5173 ..."
(
  cd "$ROOT/frontend"
  npm run dev
) &
FRONTEND_PID=$!
echo "  PID $FRONTEND_PID"

echo ""
echo "All services started."
echo ""
echo "  A2A Backend  → http://localhost:8000"
echo "  DocGen       → http://localhost:8001"
echo "  Frontend     → http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all services."

# Wait and handle Ctrl+C
trap "kill $BACKEND_PID $DOCGEN_PID $FRONTEND_PID 2>/dev/null; echo 'All services stopped.'" INT
wait
