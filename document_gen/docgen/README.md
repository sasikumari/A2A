# DocGen AI

AI-powered document generator that creates professional Word documents (.docx) with UML diagrams, styled tables, and structured content — all running **locally** via Ollama.

## Stack

| Layer | Tech |
|-------|------|
| Web framework | FastAPI |
| Agentic pipeline | LangGraph (StateGraph) |
| LLM | Ollama (`llama3.1:8b` default, configurable) |
| LLM integration | LangChain + langchain-ollama |
| Vector store | ChromaDB (persistent) |
| Document generation | python-docx |
| Diagram rendering | Pillow (no external services) |

## Prerequisites

1. **Python 3.11+**
2. **Ollama** running locally: https://ollama.com
3. Pull the default model:
   ```bash
   ollama pull llama3.1:8b
   ```

## Quick Start

```bash
# 1. Clone / navigate to project
cd docgen_app

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start Ollama (separate terminal)
ollama serve

# 5. Run the app
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

## Docker Compose

```bash
docker compose up --build
```

Ollama is included as a service. After startup, pull the model inside the container:

```bash
docker compose exec ollama ollama pull llama3.1:8b
```

## Configuration

All settings live in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `llama3.1:8b` | Any Ollama model (mistral, codellama, gemma2…) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `TEMPERATURE` | `0.3` | LLM temperature |
| `TOP_K_RESULTS` | `8` | RAG retrieval chunks |
| `CHUNK_SIZE` | `1500` | Text splitter chunk size |
| `CHUNK_OVERLAP` | `200` | Text splitter overlap |

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/generate` | Start document generation |
| `GET` | `/api/jobs/{job_id}` | Poll job status |
| `GET` | `/api/download/{job_id}` | Download generated .docx |
| `POST` | `/api/rag/upload` | Upload file for RAG ingestion |
| `GET` | `/api/rag/collections` | List ChromaDB collections |
| `DELETE` | `/api/rag/collections/{name}` | Delete a collection |
| `GET` | `/api/rag/search` | Search RAG knowledge base |
| `GET` | `/api/health` | Health check |

### Generate request body

```json
{
  "prompt": "Create a BRD for a user authentication system with SSO...",
  "doc_type": "BRD",
  "collection_name": "default",
  "include_diagrams": true,
  "additional_context": "Must support SAML 2.0 and OAuth 2.0"
}
```

## Pipeline

```
retrieve_context → plan_document → generate_diagrams → write_content → assemble_document
                        ↓ (on any error)
                   handle_error → END
```

1. **retrieve_context** — queries ChromaDB with derived queries, populates RAG context
2. **plan_document** — LLM generates a JSON document plan (title, subtitle, sections)
3. **generate_diagrams** — LLM specifies diagram data; Pillow renders PNG files
4. **write_content** — LLM writes structured content for each section
5. **assemble_document** — python-docx assembles cover page, TOC, headings, tables, images

## Diagram Types

- **Sequence** — actors, lifelines, labeled arrows, self-calls
- **Flowchart** — start/end/process/decision nodes with color coding
- **Activity/Swimlane** — lane columns with positioned activity boxes

## Production Notes

- **Job store**: Currently in-memory (`dict`). For production, replace with Redis or a database.
- **CORS**: Open for all origins in dev. Lock down `allow_origins` for production.
- **Ollama JSON mode**: `format="json"` is set on the LLM for all structured generation nodes — required for reliable JSON output from local models.
- **ChromaDB**: Data persists in `./vectorstore/`. Back this up in production.
- **File storage**: Uploaded files go to `./uploads/`, generated docs to `./outputs/`.

## Model Alternatives

```bash
ollama pull mistral
ollama pull codellama
ollama pull gemma2
```

Then update `MODEL_NAME` in `.env`.
