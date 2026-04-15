# ============================================================
# start_all.ps1  —  Start the full A2A + DocGen integrated stack
# ============================================================
# Services started:
#   1. A2A Backend   (FastAPI)  — http://localhost:8000
#   2. DocGen Service(FastAPI)  — http://localhost:8001
#   3. Frontend      (Vite)     — http://localhost:5173
# ============================================================

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND_DIR  = Join-Path $ROOT "backend"
$DOCGEN_DIR   = Join-Path $ROOT "document_gen\docgen"
$FRONTEND_DIR = Join-Path $ROOT "frontend"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NPCI AgentHub — Full Stack Launcher   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. A2A Backend ──────────────────────────────────────────
Write-Host "[1/3] Starting A2A Backend on :8000 ..." -ForegroundColor Yellow
$backendProc = Start-Process powershell -ArgumentList `
  "-NoExit", "-Command", `
  "cd '$BACKEND_DIR'; if (Test-Path '.venv\Scripts\Activate.ps1') { . .venv\Scripts\Activate.ps1 }; uvicorn main:app --host 0.0.0.0 --port 8000 --reload" `
  -PassThru
Write-Host "  PID $($backendProc.Id)" -ForegroundColor Green

# ── 2. DocGen Service ────────────────────────────────────────
Write-Host "[2/3] Starting DocGen Service on :8001 ..." -ForegroundColor Yellow
$docgenProc = Start-Process powershell -ArgumentList `
  "-NoExit", "-Command", `
  "cd '$DOCGEN_DIR'; if (Test-Path '.venv\Scripts\Activate.ps1') { . .venv\Scripts\Activate.ps1 }; uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload" `
  -PassThru
Write-Host "  PID $($docgenProc.Id)" -ForegroundColor Green

# ── 3. Frontend ──────────────────────────────────────────────
Write-Host "[3/3] Starting Frontend (Vite) on :5173 ..." -ForegroundColor Yellow
$frontendProc = Start-Process powershell -ArgumentList `
  "-NoExit", "-Command", `
  "cd '$FRONTEND_DIR'; npm run dev" `
  -PassThru
Write-Host "  PID $($frontendProc.Id)" -ForegroundColor Green

Write-Host ""
Write-Host "All services started." -ForegroundColor Green
Write-Host ""
Write-Host "  A2A Backend  → http://localhost:8000" -ForegroundColor Cyan
Write-Host "  DocGen       → http://localhost:8001" -ForegroundColor Cyan
Write-Host "  Frontend     → http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Close the individual terminal windows to stop each service." -ForegroundColor Gray
