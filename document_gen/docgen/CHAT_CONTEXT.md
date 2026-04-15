# Claude Code Session — Full Context
**Project:** claudedocuer + UPI Hackathon Titans Integration  
**Date:** 2026-04-11  
**Session file:** `ad060229-8513-4f79-8590-fd0a35bcad72`

---

## 1. Initial Request — Build DocGen AI

**User asked:** Build a complete, production-ready AI document generation tool called **DocGen AI** using:
- FastAPI backend
- LangGraph pipeline
- Ollama LLM (local)
- ChromaDB vector store (RAG)
- Python-docx for DOCX output

**What was built (`/Users/nirbhaynikam/claudedocuer/upi_hackathon_titans/docgen/`):**

```
docgen/
├── app/
│   ├── main.py              # FastAPI app, job store, all API endpoints
│   ├── config.py            # Pydantic settings (model, paths, RAG config)
│   ├── models.py            # All Pydantic models (DocumentPlan, GeneratedContent, etc.)
│   ├── document_guides.py   # Document blueprints per doc type (BRD, TSD, Circular, etc.)
│   ├── document_validator.py# Validation + repair of generated sections
│   ├── content_fallbacks.py # Fallback table data when LLM omits tables
│   ├── agents/
│   │   └── pipeline.py      # Full LangGraph pipeline (retrieve → plan → diagram → write → review → assemble)
│   ├── rag/
│   │   └── engine.py        # ChromaDB ingest, retrieval, chunking
│   └── tools/
│       ├── docx_builder.py  # DOCX assembly with styles, tables, diagrams
│       ├── document_editor.py # Section-level edit + re-assemble
│       └── rag_tools.py     # RAG tool wrappers for LangGraph nodes
├── requirements.txt
├── .env
└── outputs/                 # Generated documents stored here
```

**API Endpoints created:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/generate` | Start document generation job |
| GET | `/api/jobs/{job_id}` | Poll job status (0-100%) |
| GET | `/api/download/{job_id}` | Download completed DOCX |
| POST | `/api/edit/{job_id}` | Edit a specific section |
| GET | `/api/jobs/{job_id}/content` | Get document as markdown (new) |
| POST | `/api/generate/bundle` | Generate BRD+TSD+ProductNote+Circular in parallel |
| GET | `/api/bundles/{bundle_id}` | Poll bundle status |
| GET | `/api/bundles/{bundle_id}/download` | Download all as ZIP |
| POST | `/api/rag/upload` | Upload file to RAG collection |
| GET | `/api/rag/collections` | List RAG collections |
| GET | `/api/rag/search` | Search RAG collection |
| GET | `/api/health` | Health check |

---

## 2. Model Configuration

**User asked:** Where to change the model?

**Answer:** In `.env` at project root:
```env
MODEL_NAME=llama3.1:8b         # Change to any Ollama model
OLLAMA_BASE_URL=http://localhost:11434

# For OpenAI-compatible (vLLM/LiteLLM):
LLM_PROVIDER=openai_compat
OPENAI_BASE_URL=http://183.82.7.228:9535/v1
OPENAI_MODEL_NAME=/model
OPENAI_API_KEY=none
```

Also configurable in `app/config.py` via `Settings` class.

---

## 3. Prompt Architecture Refactor

**User's diagnosis:** Old prompts had too much mixed responsibility — anatomy, JSON schema, content, validation all in one prompt. Needed separation of concerns.

**Changes made to `pipeline.py`:**
- **Planner node**: Uses a dedicated system prompt focused only on document structure/outline
- **Writer node**: Uses a separate content-focused system prompt with section-specific instructions from `document_guides.py`
- **Reviewer node**: Independent validation pass
- **System vs User prompt separation**: Blueprint/rules in system prompt; actual content instruction in user prompt
- Added `content_instructions` and `prompt_instruction` per section in blueprints

---

## 4. Document Quality Improvements

**User provided:** Structural audit comparing agent-created TSD vs official NPCI TSD.

**Key gaps identified & fixed:**
1. BRD was including API specs (belongs in TSD) — fixed via blueprint section definitions
2. TSD was missing: Architecture diagrams, API specs table, sequence flows, error codes
3. Product Note missing 11-point NPCI canonical structure
4. Circular missing proper header/footer, reference codes

**Changes to `document_guides.py`:**
- BRD blueprint: Executive summary, business objectives, stakeholders, user stories, regulatory requirements, success metrics — NO API specs
- TSD blueprint: System architecture, API specs (tables), sequence diagrams, data models, error codes, deployment
- Product Note: Strict 11-point NPCI canonical structure
- Circular: Reference code, issue date, recipient line, subject, body, signatory block
- Each section got `validation_min_paragraphs`, `include_table`, `include_diagram` flags

**Changes to `models.py`:**
- Added `SectionPlan.validation_min_paragraphs`
- Added `SectionPlan.table_fallback_profile`
- Added `SectionPlan.validation_fill_numbered_items`
- Added `GenerateRequest` fields: `organization_name`, `reference_code`, `issue_date`, `recipient_line`, `subject_line`, `signatory_name/title/department`

---

## 5. Bundle Generation (All 4 Documents from One Prompt)

**User asked:** Make all four documents (BRD, TSD, Product Note, Circular) from the same prompt.

**Implemented:**
- `POST /api/generate/bundle` — takes single prompt, spawns 4 parallel `threading.Thread` jobs
- `BundleGenerateRequest` model with per-type title overrides
- `GET /api/bundles/{bundle_id}` — polls all 4 jobs, returns overall status
- `GET /api/bundles/{bundle_id}/download` — ZIP of all completed DOCXs
- UI updated to show bundle generation flow

---

## 6. Java Code Analysis for Better Diagrams

**User shared:** Java Spring AI document generation code with detailed phase-by-phase generation (Plan → Content → Diagrams → Assembly).

**Key insights extracted from Java code:**
- Java used dedicated `DiagramGenerationAgent` that generated Mermaid/PlantUML markup then rendered
- Each section had explicit diagram type (sequence, flowchart, activity/swimlane)
- Java code generated diagrams as PNG via external renderer, then embedded in DOCX
- Python implementation had diagram generation but was skipping it in practice

**Changes made:**
- Fixed `pipeline.py` diagram generation node to not be skipped
- Updated `document_guides.py` to explicitly mark which sections need `include_diagram: true` with `diagram_type` and `diagram_description`
- Fixed `docx_builder.py` to actually embed PNG diagrams in the Word document
- Added sequence, flowchart, and activity diagram renderers using `matplotlib` + `pillow`

---

## 7. Validation & Error Fixes

### Validation error: "Section must contain at least 2 substantive paragraphs"

**Fix in `document_validator.py`:**
- `_substantive_body_ok()` — allows structured content alone (table/list/code) to satisfy validation
- `repair_sections_for_validation()` — auto-injects fallback content when LLM omits sections
- `validation_min_paragraphs: 1` override for intro/cover sections
- Validation is **content-structure based** — NOT hardcoded for specific use cases

### JSON parsing error in TSD: "Expecting ',' delimiter"

**Fix in `pipeline.py`:**
- Multi-stage JSON recovery: strip markdown fences → fix trailing commas → extract largest valid JSON object
- Fallback to empty section rather than crashing entire pipeline
- Added `[JSON recovery]` logging for debugging

### Diagrams not appearing in documents

**Root cause:** Diagram generation was completing but `diagram_path` wasn't being threaded through to `docx_builder.py`.

**Fix:**
- `generated_diagrams` dict in state now keyed by `section_index`
- `assemble_document` node reads diagram paths and passes to DOCX builder
- DOCX builder inserts `InlineImage` for each diagram at correct section position

---

## 8. RAG Tools Added

**User requested:** Two dedicated RAG tools:
1. UPI Knowledge Base RAG (NPCI circulars, guidelines)
2. UPI Code RAG (codebase references)

**Implemented in `app/tools/rag_tools.py`:**
```python
def search_upi_knowledge(query: str, top_k: int = 8) -> str:
    """Search the UPI knowledge base collection."""
    return search_collection(query, collection_name=settings.upi_knowledge_collection, top_k=top_k)

def search_upi_code(query: str, top_k: int = 5) -> str:
    """Search the UPI codebase collection."""
    return search_collection(query, collection_name=settings.upi_code_collection, top_k=top_k)
```

**Added to `config.py`:**
```python
upi_knowledge_collection: str = Field(default="upi_knowledge")
upi_code_collection: str = Field(default="upi_code")
```

**Pipeline updated:** `retrieve_context` node now searches both collections and merges results.

---

## 9. Subgraph Integration Guide

**User requested:** Make claudedocuer embeddable as a LangGraph subgraph in another workflow.

**Created `SUBGRAPH_INTEGRATION_GUIDE.md`** covering:
- How to import `run_pipeline` as a callable
- State schema compatibility
- How to wire as a LangGraph subgraph node
- Input/output state mapping
- Example integration code

---

## 10. Document Edit Feature

**User requested:** Edit documents based on user input after generation.

**Implemented `app/tools/document_editor.py`:**
- `edit_document_section(job_id, section_heading, edit_instruction)` 
- Loads existing `generated_sections.json` from job output dir
- Finds section by heading, re-generates only that section using the edit instruction + original context
- Re-assembles full DOCX with edited section
- Saves as `document_edited.docx`

**API endpoint added to `main.py`:**
```
POST /api/edit/{job_id}
Body: { "section_heading": "...", "edit_instruction": "..." }
```

---

## 11. UPI Titans UI Integration

**User asked:** Integrate claudedocuer into the `upi_hackathon_titans/product-builder` UI, replacing the existing document generation flow.

### Project Structure
```
upi_hackathon_titans/
├── product-builder/              # React/Vite frontend + FastAPI backend
│   ├── src/
│   │   ├── components/
│   │   │   ├── DocumentsChatPage.tsx   # Chat UI for document generation
│   │   │   └── DocumentsView.tsx       # Document viewer/editor
│   │   ├── types.ts
│   │   └── utils/canvasGenerator.ts    # Local template-based fallback
│   └── backend/
│       ├── main.py                     # FastAPI on port 8001
│       └── agents/
│           └── document_agent.py       # ← REPLACED with claudedocuer integration
└── upi_hackathon_titans/         # UPI orchestrator (Flask on port 5000)
```

### Port Map
| Service | Port | Description |
|---------|------|-------------|
| claudedocuer | 8000 | Document generation API |
| product-builder backend | 8001 | Canvas/registry API |
| UPI orchestrator | 5000 | Agent A2A orchestration |
| Frontend (Vite) | 5173 | React UI |

### Changes Made

#### `product-builder/backend/agents/document_agent.py` (full rewrite)
Replaced skill-based generator with claudedocuer API calls:

```python
DOCGEN_BASE_URL = os.getenv("DOCGEN_BASE_URL", "http://localhost:8000")

class DocumentAgent:
    def generate(self, canvas, feedback=None):
        # 1. Convert canvas → prompt
        prompt = _canvas_to_prompt(canvas, feedback)
        # 2. Submit bundle to claudedocuer
        bundle_id = self._submit_bundle(prompt, feature)
        # 3. Poll until complete
        job_map = self._poll_bundle(bundle_id)
        # 4. Fetch markdown for each job
        documents = [self._build_document(dt, job, feature) for dt, job in job_map.items()]
        return documents
```

#### `app/main.py` (claudedocuer) — new endpoint added
```
GET /api/jobs/{job_id}/content
```
Reads `generated_sections.json` and returns full document as clean markdown.

#### `product-builder/backend/main.py`
- Updated `DownloadRequest` to accept optional `_docgen_job_id` / `_docgen_base_url`
- `/api/documents/download` now proxies DOCX download from claudedocuer when job ID present

#### `product-builder/src/types.ts`
```typescript
export interface Document {
  // ... existing fields
  _docgen_job_id?: string;
  _docgen_base_url?: string;
}
```

#### `product-builder/src/components/DocumentsView.tsx`
Updated `downloadDocx()` to pass claudedocuer job metadata:
```typescript
const body = { title: doc.title, content: doc.content };
if (doc._docgen_job_id) body._docgen_job_id = doc._docgen_job_id;
```

#### `product-builder/src/components/DocumentsChatPage.tsx`
Updated thinking step labels to reflect real claudedocuer pipeline stages (cosmetic only — the actual API call `apiGenerateDocuments` already hit `/api/documents/generate` which routes to `document_agent.py`).

#### `product-builder/backend/.env`
```env
DOCGEN_BASE_URL="http://localhost:8000"
DOCGEN_TIMEOUT="300"
DOCGEN_POLL_INTERVAL="3"
```

#### `product-builder/backend/agents/figma_agent.py`
Wrapped `mcp` imports in `try/except ImportError` — `mcp` package not installed was crashing the entire backend on startup.

---

## 12. Startup Script (`setup_and_run.sh`)

**Problem history:**
1. First version: double-started product-builder backend (conflict with `run_system.sh`)
2. Second version: `upi_hackathon_titans/venv` was Windows-created (no `bin/activate`) — crash
3. Third version: `curl` health check without `--connect-timeout` hung 60s per attempt
4. Current version: all fixed

**Final `setup_and_run.sh`:**
```bash
# 1. Start claudedocuer (port 8000) using claudedocuer's own .venv
# 2. Start frontend (port 5173) via npm
# 3. Activate upi orchestrator .venv (create fresh if Windows-created)
# 4. Call run_system.sh which: starts PB backend (8001) + waits for it + starts orchestrator (5000)
```

**`run_system.sh` key fixes:**
- Uses claudedocuer `.venv` Python (has fastapi+uvicorn) for the product-builder backend
- Health check loop with `--connect-timeout 1` (fast fail, not 60s hang)
- Adds UPI `.venv` site-packages to PYTHONPATH for orchestrator

---

## 13. Bug Fixes Chronology

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| `ModuleNotFoundError: mcp` | `figma_agent.py` imported `mcp` unconditionally | Wrapped in `try/except ImportError` |
| `Connection to localhost timed out` | product-builder backend never started (crashed on mcp import) | Fixed figma_agent + watchfiles auto-reloaded |
| `venv/bin/activate: No such file` | `upi_hackathon_titans/venv` created on Windows (has `Scripts/` not `bin/`) | `find_or_create_venv()` helper creates fresh Unix venv |
| `curl` health check hanging | No `--connect-timeout` — each attempt waited 60s | Added `--connect-timeout 1 --max-time 2` |
| PB backend using wrong Python | `bash run_system.sh` didn't inherit activated venv | Explicitly pass `$VENV_PYTHON` path |
| `ModuleNotFoundError: langchain.text_splitter` | LangChain reorganized — moved to `langchain_text_splitters` package | Changed import in `app/rag/engine.py` |

---

## 14. Current State (End of Session)

### What's working ✅
- **Product-builder backend (8001)**: fully up, all agents loading, registry working
- **UPI orchestrator (5000)**: all agents registered and authenticated
- **claudedocuer (8000)**: starts cleanly after `langchain.text_splitter` fix
- **Frontend (5173)**: running

### Document generation flow
```
User clicks "Generate Documents" in UI
  → DocumentsChatPage.tsx calls POST /api/documents/generate (port 8001)
  → DocumentAgent.generate() in product-builder backend
  → POST http://localhost:8000/api/generate/bundle  (claudedocuer)
  → claudedocuer runs: RAG retrieval → planning → writing → validation → DOCX assembly
  → Poll GET /api/bundles/{bundle_id} until complete
  → GET /api/jobs/{job_id}/content → markdown returned per doc type
  → Documents displayed in DocumentsView.tsx
  → .docx download proxied from claudedocuer
```

### Fallback chain (if claudedocuer unreachable)
```
document_agent.py → returns self._fallback_docs(canvas)  [python fallbacks]
  OR
DocumentsChatPage.tsx catch block → generateDocuments(canvas)  [JS template generator]
```

### To verify claudedocuer is being used
```bash
# After triggering document generation in the UI:
tail -f upi_hackathon_titans/pb_backend.log
# Should show: [DocumentAgent] Bundle submitted: <uuid>
# Should show: [DocumentAgent]   BRD              30%  Planning document structure

curl http://localhost:8000/api/health
# Should return: {"status":"ok","model_name":"gpt-oss:120b-cloud",...}
```

---

## 15. Key Files Reference

### claudedocuer (`/Users/nirbhaynikam/claudedocuer/`)
| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app + all endpoints + job store |
| `app/config.py` | All settings (model, paths, RAG, LLM provider) |
| `app/models.py` | All Pydantic models |
| `app/document_guides.py` | Per-doc-type blueprints (BRD/TSD/Circular/etc.) |
| `app/document_validator.py` | Content validation + auto-repair |
| `app/agents/pipeline.py` | LangGraph pipeline (6 nodes) |
| `app/rag/engine.py` | ChromaDB RAG engine |
| `app/tools/docx_builder.py` | DOCX assembly |
| `app/tools/document_editor.py` | Section-level edit |
| `app/tools/rag_tools.py` | UPI knowledge + code RAG tools |

### product-builder (`upi_hackathon_titans/product-builder/`)
| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI on port 8001, proxies docx download |
| `backend/agents/document_agent.py` | **Replaced** — now calls claudedocuer bundle API |
| `backend/agents/figma_agent.py` | Fixed — mcp import is now optional |
| `backend/.env` | Added DOCGEN_BASE_URL, DOCGEN_TIMEOUT |
| `src/types.ts` | Added `_docgen_job_id`, `_docgen_base_url` to Document |
| `src/components/DocumentsView.tsx` | Passes job metadata to download endpoint |
| `src/components/DocumentsChatPage.tsx` | Updated thinking step labels |

### Startup scripts
| File | Purpose |
|------|---------|
| `upi_hackathon_titans/setup_and_run.sh` | Starts all 4 services in correct order |
| `upi_hackathon_titans/run_system.sh` | Starts PB backend + waits + starts orchestrator |

---

## 16. LLM Provider Configuration

claudedocuer supports two LLM providers:

```env
# Option 1: Local Ollama
LLM_PROVIDER=ollama
MODEL_NAME=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434

# Option 2: vLLM / LiteLLM (OpenAI-compatible) — what's currently configured
LLM_PROVIDER=openai_compat
OPENAI_BASE_URL=http://183.82.7.228:9535/v1
OPENAI_MODEL_NAME=/model
OPENAI_API_KEY=none
```

The product-builder backend LLM is configured separately in `backend/agents/llm.py`:
```python
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://183.82.7.228:9535")
LLM_MODEL = os.getenv("LLM_MODEL", "/model")
```

---

## 17. Future Work (Discussed but Not Yet Done)

1. **RAG population**: Need to ingest actual NPCI circulars into `upi_knowledge` collection and UPI codebase into `upi_code` collection via `POST /api/rag/upload`
2. **Code RAG integration**: Someone else on team building this — will use existing RAG tools when ready
3. **Moving to company laptop**: Needs: Python 3.14, all deps installed, `.env` updated with correct vLLM endpoint
4. **Parallel section generation**: `MAX_PARALLEL_SECTIONS=3` config exists — needs testing at scale
