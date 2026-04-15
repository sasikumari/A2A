# NPCI Titans

NPCI Titans is a combined UPI ecosystem simulator and product engineering workspace.

It includes:

- a `Flask`-based UPI orchestrator and simulation engine
- a `React + FastAPI` product builder for canvas, documents, prototype, execution, and certification workflows
- an embedded `LangGraph` document generation engine in `docgen/`

The main user flow is:

1. enter a product idea
2. generate and refine a product canvas
3. generate BRD, TSD, Product Note, and Circular
4. preview, edit, and download documents
5. continue into prototype, execution, and certification flows

---

## Project Layout

```text
upi_hackathon_titans/
├── api/                     # Flask orchestrator on :5000
├── agents/                  # Reasoning / switch / participant agents
├── switch/                  # UPI switch, ledger, notification bus
├── banks/                   # simulated banks
├── psps/                    # simulated PSPs
├── infrastructure/          # Qdrant-backed doc store, signing, RBAC
├── storage/                 # SQLite helpers
├── product-builder/
│   ├── src/                 # React frontend
│   └── backend/             # FastAPI backend on :8001
├── docgen/                  # embedded document engine
├── setup_and_run.sh         # main launcher
└── run_system.sh            # starts PB backend + orchestrator
```

For a full architectural walkthrough, see:

- [PROJECT_ARCHITECTURE.md](/Users/nirbhaynikam/claudedocuer/upi_hackathon_titans/PROJECT_ARCHITECTURE.md)

---

## Services and Ports

| Service | Port | Required for normal Titans flow |
|---|---:|---|
| Frontend | `5173` | Yes |
| Product Builder backend | `8001` | Yes |
| UPI orchestrator | `5000` | Yes |
| Standalone DocGen API | `8000` | No |

Important:

- the Titans document flow uses `docgen` in-process through the Product Builder backend
- you do **not** need to run DocGen as a separate service for normal document generation from the UI

---

## Supported Setup Modes

## 1. Recommended

Use:

- macOS
- Linux
- Windows with native `PowerShell`

This project includes Unix-style launcher scripts for Linux/macOS, and now also includes a native Windows launcher.

## 2. Not Recommended

Running directly in `cmd.exe`.

Why:

- PowerShell is much more reliable than `cmd.exe` for virtual environments and long-running dev servers
- the Unix launchers are still `bash`-based, so Windows should use the dedicated Windows launcher
- native Windows works best when started through the files documented below

If you are on Windows, use `PowerShell` and `setup_and_run_windows.bat`.

---

## Prerequisites

Install these first:

- Python `3.10+`
- Node.js `18+`
- npm
- Git

Optional:

- LiteLLM or another OpenAI-compatible model gateway
- Ollama if you want local Ollama-based model serving

---

## LLM Configuration

The project can be pointed at an OpenAI-compatible endpoint through a shared root `.env`.

Start from:

- [`.env.example`](/Users/nirbhaynikam/claudedocuer/upi_hackathon_titans/.env.example)

If you are using your local LiteLLM test at `http://localhost:4000/v1`, create:

```bash
cp .env.example .env
```

Then set:

```env
OPENAI_COMPAT_BASE_URL=http://localhost:4000/v1
OPENAI_COMPAT_API_KEY=anything
OPENAI_COMPAT_MODEL=local-chat

LLM_API_URL=http://localhost:4000/v1/chat/completions
LLM_BASE_URL=http://localhost:4000
LLM_API_KEY=anything
LLM_MODEL=local-chat

LLM_PROVIDER=openai_compat
OPENAI_BASE_URL=http://localhost:4000/v1
OPENAI_API_KEY=anything
OPENAI_MODEL_NAME=local-chat
```

Notes:

- `docgen` can run in `openai_compat` mode
- if `langchain_openai` is not installed, the document pipeline now falls back to a built-in OpenAI-compatible adapter
- orchestrator-side retrieval may still require a working embedding endpoint if you want full RAG behavior

### LiteLLM Configuration

If you are using LiteLLM locally, this project treats it as an OpenAI-compatible gateway.

Your LiteLLM endpoint should respond to a request like:

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer anything" \
  -d '{
    "model": "local-chat",
    "messages": [
      {"role": "user", "content": "Say hello"}
    ]
  }'
```

If that works, configure [`.env`](/Users/nirbhaynikam/claudedocuer/upi_hackathon_titans/.env) like this:

```env
# Shared OpenAI-compatible gateway config
OPENAI_COMPAT_BASE_URL=http://localhost:4000/v1
OPENAI_COMPAT_API_KEY=anything
OPENAI_COMPAT_MODEL=local-chat

# Optional embeddings endpoint
OPENAI_COMPAT_EMBEDDING_URL=http://localhost:4000/v1/embeddings
OPENAI_COMPAT_EMBEDDING_MODEL=local-chat

# Backward-compatible aliases still used by some modules
LLM_API_URL=http://localhost:4000/v1/chat/completions
LLM_BASE_URL=http://localhost:4000
LLM_API_KEY=anything
LLM_MODEL=local-chat
LLM_TIMEOUT=180
LLM_EMBEDDING_URL=http://localhost:4000/v1/embeddings
LLM_EMBEDDING_MODEL=local-chat

# DocGen OpenAI-compatible mode
LLM_PROVIDER=openai_compat
OPENAI_BASE_URL=http://localhost:4000/v1
OPENAI_API_KEY=anything
OPENAI_MODEL_NAME=local-chat
```

What these values control:

- `OPENAI_COMPAT_*`: shared gateway config for modules using the common compatibility layer
- `LLM_*`: older orchestrator and Product Builder call paths that still read legacy names
- `OPENAI_*` plus `LLM_PROVIDER=openai_compat`: DocGen pipeline configuration

If you switch models later, you usually only need to change:

```env
OPENAI_COMPAT_BASE_URL=http://your-host:port/v1
OPENAI_COMPAT_API_KEY=your-key
OPENAI_COMPAT_MODEL=your-model-name

LLM_API_URL=http://your-host:port/v1/chat/completions
LLM_BASE_URL=http://your-host:port
LLM_API_KEY=your-key
LLM_MODEL=your-model-name

OPENAI_BASE_URL=http://your-host:port/v1
OPENAI_API_KEY=your-key
OPENAI_MODEL_NAME=your-model-name
```

If your LiteLLM server does not expose embeddings:

- document generation can still work
- orchestrator-side RAG and embedding-based retrieval may be limited
- in that case, point `OPENAI_COMPAT_EMBEDDING_URL` and `LLM_EMBEDDING_URL` to a separate embedding-capable endpoint later

### Quick LiteLLM Smoke Test

Before starting the full app, you can verify the configured gateway:

On Linux/macOS:

```bash
curl "$OPENAI_COMPAT_BASE_URL/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_COMPAT_API_KEY" \
  -d "{\"model\":\"$OPENAI_COMPAT_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}]}"
```

On Windows PowerShell:

```powershell
$envFile = Get-Content .env
$baseUrl = ($envFile | Where-Object { $_ -match '^OPENAI_COMPAT_BASE_URL=' }) -replace '^OPENAI_COMPAT_BASE_URL=', ''
$apiKey = ($envFile | Where-Object { $_ -match '^OPENAI_COMPAT_API_KEY=' }) -replace '^OPENAI_COMPAT_API_KEY=', ''
$model = ($envFile | Where-Object { $_ -match '^OPENAI_COMPAT_MODEL=' }) -replace '^OPENAI_COMPAT_MODEL=', ''

Invoke-RestMethod `
  -Uri "$baseUrl/chat/completions" `
  -Method Post `
  -Headers @{ Authorization = "Bearer $apiKey" } `
  -ContentType "application/json" `
  -Body (@{
    model = $model
    messages = @(@{ role = "user"; content = "ping" })
  } | ConvertTo-Json -Depth 4)
```

---

# Linux / macOS Setup

## Step 1: Clone the repo

```bash
git clone <your-repo-url>
cd upi_hackathon_titans
```

## Step 2: Create the root `.env`

```bash
cp .env.example .env
```

Edit `.env` for your LLM endpoint if needed.

## Step 3: Start the system

```bash
bash setup_and_run.sh
```

This will:

1. prepare the embedded `docgen` Python environment
2. start the frontend on `127.0.0.1:5173`
3. start the Product Builder backend on `8001`
4. start the UPI orchestrator on `5000`

## Step 4: Open the UI

Use:

- [http://127.0.0.1:5173](http://127.0.0.1:5173)

Prefer `127.0.0.1` over `localhost` if your machine/browser behaves differently with Vite binding.

## Step 5: Verify services

```bash
curl http://localhost:8001/health
curl http://localhost:5000/health
```

If you also started standalone DocGen:

```bash
curl http://localhost:8000/api/health
```

---

# Windows Setup

Use native `PowerShell`. You do not need WSL, Ubuntu, Git Bash, or any other Linux-style shell.

## Step 1: Install prerequisites

Install:

- Python `3.10+`
- Node.js `18+`
- npm
- Git

Recommended checks:

```powershell
py --version
node --version
npm --version
git --version
```

## Step 2: Clone the repo

```powershell
git clone <your-repo-url>
cd upi_hackathon_titans
```

## Step 3: Create `.env`

```powershell
Copy-Item .env.example .env
```

Edit it for your model endpoint.

## Step 4: Start the system

Use the native Windows launcher:

```powershell
.\setup_and_run_windows.bat
```

This launcher:

1. creates or reuses `.venv`
2. creates or reuses `docgen\.venv`
3. installs Python requirements
4. installs frontend dependencies if needed
5. starts the frontend on `127.0.0.1:5173`
6. starts the Product Builder backend on `8001`
7. starts the UPI orchestrator on `5000`

## Step 5: Open the app

Use:

- [http://127.0.0.1:5173](http://127.0.0.1:5173)

Prefer `127.0.0.1` over `localhost` on Windows too.

## Step 6: Verify services

```powershell
curl http://localhost:8001/health
curl http://localhost:5000/health
```

## Step 7: Manual fallback if you do not want the launcher

If you prefer to run services yourself in separate PowerShell terminals:

### Terminal 1: frontend

```powershell
cd product-builder
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

### Terminal 2: Product Builder backend

```powershell
py -3 -m venv docgen\.venv
.\docgen\.venv\Scripts\python.exe -m pip install -r docgen\requirements.txt
$env:PYTHONPATH = (Get-Location).Path
cd product-builder\backend
..\..\docgen\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Terminal 3: UPI orchestrator

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe -u api\app.py
```

---

## Optional: Standalone DocGen Service

Not required for the Titans UI flow, but available if you want direct DocGen API access.

```bash
cd docgen
source .venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Use this only if you explicitly need:

- direct DocGen APIs
- RAG upload/search through the DocGen FastAPI layer
- standalone bundle generation independent of Product Builder

---

## What `setup_and_run.sh` Actually Does

The startup sequence is:

1. prepare `docgen/.venv` and install `docgen/requirements.txt`
2. start frontend dev server
3. prepare root Python env
4. run `run_system.sh`
5. `run_system.sh` starts Product Builder backend and waits for `/health`
6. then starts the UPI orchestrator

This order is important and avoids earlier race conditions.

---

## Problems We Already Faced and How to Avoid Them

## 1. Mixed Windows and Unix virtual environments caused startup failures

Problem:

- Windows virtual environments use `Scripts\`
- Unix shell launchers expect `bin/activate`
- reusing the same environment across both styles causes startup confusion

What we changed:

- the launcher tries `.venv` and `venv`
- if no usable Unix venv exists, it creates one

What you should do:

- on Windows, use `setup_and_run_windows.bat`
- on Linux/macOS, use `bash setup_and_run.sh`
- do not reuse a Windows-created venv inside Unix shells, or a Unix-created venv inside PowerShell

## 2. Qdrant lock conflict on restart

Problem:

- the orchestrator uses local `qdrant_data/`
- only one process can hold that lock
- if an old orchestrator is still alive, startup fails with an `AlreadyLocked` / `Storage folder qdrant_data is already accessed` error

What you should do:

- stop old processes before restarting
- if you see this error, kill the old `api/app.py` process and start again

Windows tip:

```powershell
Get-Process python | Select-Object Id, ProcessName, Path
Stop-Process -Id <PID>
```

## 3. Frontend opens on `127.0.0.1` more reliably than `localhost`

Problem:

- some environments bind Vite differently

What you should do:

- use `http://127.0.0.1:5173`

## 4. DocGen is embedded, but its dependencies are still required

Problem:

- some users assume “not running standalone DocGen” means `docgen` deps are not needed
- that is incorrect

Why:

- Product Builder imports `docgen/app` directly in-process

What we changed:

- startup now prepares the embedded DocGen runtime first

What you should do on Windows:

```powershell
.\docgen\.venv\Scripts\python.exe -m pip install -r docgen\requirements.txt
```

## 5. `langchain_openai` missing in `openai_compat` mode

Problem:

- DocGen attempted to import `langchain_openai`
- environment didn’t have it

What we changed:

- the pipeline now falls back to a built-in OpenAI-compatible adapter if `langchain_openai` is unavailable

## 6. Product Builder backend startup depends on `docgen` env

Problem:

- manual starts from inside `product-builder/backend` could miss shared root config/helpers

What we changed:

- `product-builder/backend/start.sh` now exports `PYTHONPATH` with the repo root

## 7. Windows now has a native launcher

What we changed:

- added [setup_and_run_windows.ps1](/Users/nirbhaynikam/claudedocuer/upi_hackathon_titans/setup_and_run_windows.ps1)
- added [setup_and_run_windows.bat](/Users/nirbhaynikam/claudedocuer/upi_hackathon_titans/setup_and_run_windows.bat)

What you should do:

```powershell
.\setup_and_run_windows.bat
```

---

## Logs

Useful logs:

```bash
tail -f pb_backend.log
tail -f frontend.log
```

If running standalone DocGen:

```bash
tail -f docgen.log
```

---

## Common Commands

## Start everything

```bash
bash setup_and_run.sh
```

## Start only standalone DocGen

```bash
cd docgen
source .venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Health checks

```bash
curl http://localhost:8001/health
curl http://localhost:5000/health
curl http://localhost:8000/api/health
```

## Check local LiteLLM endpoint

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer anything" \
  -d '{
    "model": "local-chat",
    "messages": [{"role": "user", "content": "Say hello"}]
  }'
```

---

## Manual Development Notes

### Frontend

```bash
cd product-builder
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

### Product Builder backend

```bash
cd product-builder/backend
bash start.sh
```

### Orchestrator

```bash
python3 -u api/app.py
```

---

## GitHub Hygiene

Before publishing:

- keep `.env` out of Git
- keep `.venv/`, `venv/`, logs, DBs, vector stores, and generated outputs out of Git
- use `.env.example` for shared config shape

The repo already ignores the main local/runtime artifacts.

---

## Architecture Document

For a deeper technical walkthrough:

- [PROJECT_ARCHITECTURE.md](/Users/nirbhaynikam/claudedocuer/upi_hackathon_titans/PROJECT_ARCHITECTURE.md)
