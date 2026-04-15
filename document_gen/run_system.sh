#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# consolidated project root (upi_hackathon_titans)
PROJ_ROOT="$SCRIPT_DIR"
# embedded docgen root
DOCGEN_ROOT="$PROJ_ROOT/docgen"

# Set PYTHONPATH to the project root
export PYTHONPATH="$PROJ_ROOT:$SCRIPT_DIR:$PYTHONPATH"

echo "Starting NPCI AI Agent Orchestrator System..."
echo "Project Root: $PROJ_ROOT"

# ── Choose the Python interpreter for the product-builder backend ────────────
# Preference order:
#   1. claudedocuer .venv  — has fastapi + uvicorn already
#   2. Any local venv with a working bin/python3
#   3. System python3
PB_PYTHON=""
for candidate in \
    "$DOCGEN_ROOT/.venv/bin/python3" \
    "$SCRIPT_DIR/.venv/bin/python3" \
    "$SCRIPT_DIR/venv/bin/python3"; do
    if [ -f "$candidate" ] && [ -x "$candidate" ] && "$candidate" -c "import fastapi, uvicorn" 2>/dev/null; then
        PB_PYTHON="$candidate"
        break
    fi
done

if [ -z "$PB_PYTHON" ]; then
    # Last resort: install into a fresh venv alongside this script
    echo "  No suitable venv found — creating $SCRIPT_DIR/pb_venv for product-builder backend..."
    python3 -m venv "$SCRIPT_DIR/pb_venv"
    "$SCRIPT_DIR/pb_venv/bin/pip" install -q fastapi uvicorn[standard] requests python-multipart pyjwt
    PB_PYTHON="$SCRIPT_DIR/pb_venv/bin/python3"
fi
echo "  Product Builder Python: $PB_PYTHON"

# ── Start the product-builder backend (port 8001) ────────────────────────────
echo "Starting Product Builder Backend on 8001..."
export PB_BACKEND_DIR="$PROJ_ROOT/product-builder/backend"

export FIGMA_PAT="figd_EHwP2y-EFdz17techTtdxEIQkLwYhw9F2vjQ2Ggj"
export FIGMA_TEAM_ID="1620687652014041325"

cd "$PB_BACKEND_DIR" && "$PB_PYTHON" main.py > "$SCRIPT_DIR/pb_backend.log" 2>&1 &
PB_PID=$!
cd "$SCRIPT_DIR"
echo "  PB backend PID: $PB_PID  (log: $SCRIPT_DIR/pb_backend.log)"

# ── Wait until the backend is actually accepting connections ─────────────────
echo "Waiting for Product Builder backend (port 8001)..."
for i in $(seq 1 30); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        --connect-timeout 1 --max-time 2 \
        http://localhost:8001/health 2>/dev/null)
    if [ "$STATUS" = "200" ]; then
        echo "  Backend ready after ${i}s."
        break
    fi
    if [ "$i" = "30" ]; then
        echo "  Warning: backend did not respond in 30s — proceeding."
        echo "  Last few lines of pb_backend.log:"
        tail -5 "$SCRIPT_DIR/pb_backend.log" 2>/dev/null || true
    fi
    sleep 1
done

# ── Start the UPI orchestrator (uses the upi .venv which has flask/qdrant) ───
# The upi .venv has no real python binary (created on Windows), so use the
# same claudedocuer/system python3 which has all the heavy deps already.
UPI_PYTHON=""
for candidate in \
    "$DOCGEN_ROOT/.venv/bin/python3" \
    "python3"; do
    if [ "$candidate" = "python3" ] || ([ -f "$candidate" ] && [ -x "$candidate" ]); then
        UPI_PYTHON="$candidate"
        break
    fi
done

# Make sure the UPI packages are importable by adding .venv site-packages to path
UPI_SITE="$SCRIPT_DIR/.venv/lib/python3.10/site-packages"
if [ -d "$UPI_SITE" ]; then
    export PYTHONPATH="$UPI_SITE:$PYTHONPATH"
fi

echo "  UPI Orchestrator Python: $UPI_PYTHON"
echo ""

# Run the application
"$UPI_PYTHON" -u api/app.py
