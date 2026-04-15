#!/bin/bash
cd "$(dirname "$0")"
# Activate claudedocuer venv so all pipeline dependencies (langchain, langgraph, etc.) are available
DOCGEN_ROOT="$(cd ../../docgen && pwd)"
PROJECT_ROOT="$(cd ../.. && pwd)"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
source "$DOCGEN_ROOT/.venv/bin/activate"
echo "Starting Product Builder Backend on port 8001 (venv: $DOCGEN_ROOT/.venv)..."
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
