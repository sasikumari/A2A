#!/bin/bash

PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOCGEN_ROOT="$PROJECT_ROOT/docgen"

echo "================================================"
echo "🚀 NPCI Hackathon Titans - Setup & Run Script 🚀"
echo "================================================"
echo "Project root: $PROJECT_ROOT"

find_or_create_venv() {
    local dir="$1"
    local label="$2"
    for candidate in "$dir/.venv" "$dir/venv"; do
        if [ -f "$candidate/bin/activate" ]; then
            echo "$candidate"
            return
        fi
    done
    echo "  Creating new virtual environment in $dir/.venv for $label..." >&2
    python3 -m venv "$dir/.venv"
    echo "$dir/.venv"
}

echo -e "\n[1/3] Preparing embedded DocGen runtime..."
cd "$DOCGEN_ROOT"
DOCGEN_VENV="$(find_or_create_venv "$DOCGEN_ROOT" "claudedocuer")"
source "$DOCGEN_VENV/bin/activate"
echo "  Installing docgen dependencies (quiet)..."
pip install -q -r requirements.txt 2>&1 | tail -2
deactivate

echo -e "\n[2/3] Setting up and starting Node.js Frontend (port 5173)..."
cd "$PROJECT_ROOT/product-builder"
if [ ! -d "node_modules" ]; then
    echo "  Installing npm dependencies (this may take a minute)..."
    npm install
else
    echo "  node_modules found, skipping npm install."
fi
nohup npm run dev -- --host 127.0.0.1 --port 5173 > "$PROJECT_ROOT/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID  (log: $PROJECT_ROOT/frontend.log)"

echo -e "\n[3/3] Setting up Python environment for UPI orchestrator..."
cd "$PROJECT_ROOT"
UPI_VENV="$(find_or_create_venv "$PROJECT_ROOT" "upi-orchestrator")"
echo "  Activating virtual environment: $UPI_VENV"
source "$UPI_VENV/bin/activate"
echo "  Installing Python packages..."
pip install -q -r requirements.txt 2>&1 | tail -2

echo ""
echo "================================================"
echo "✅ Services starting up:"
echo ""
echo "🌐 Frontend Dashboard:       http://127.0.0.1:5173"
echo "🌐 Product Builder API:      http://localhost:8001"
echo "🌐 UPI Agent Orchestrator:   http://localhost:5000"
echo ""
echo "Logs:"
echo "  PB backend:     $PROJECT_ROOT/pb_backend.log"
echo "  Frontend:       $PROJECT_ROOT/frontend.log"
echo ""
echo "Optional standalone DocGen API:"
echo "  cd $DOCGEN_ROOT"
echo "  source .venv/bin/activate"
echo "  python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "================================================"
echo ""
echo "Press Ctrl+C to stop all services."

trap "echo -e '\nShutting down...'; kill $FRONTEND_PID 2>/dev/null; pkill -P $$; exit" SIGINT SIGTERM

exec bash "$PROJECT_ROOT/run_system.sh"
