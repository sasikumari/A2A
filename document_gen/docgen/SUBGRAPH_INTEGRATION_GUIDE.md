# Subgraph Integration Guide

This guide explains how to embed the DocGen AI document generation pipeline as a reusable
LangGraph subgraph inside a parent agent or workflow.

---

## 1. Overview

### What is a LangGraph subgraph?

A LangGraph `StateGraph` is a compiled runnable — a `CompiledGraph` — that accepts a state
dict and returns an updated state dict. Any compiled graph can be passed directly as a
**node function** inside another `StateGraph`. The outer graph is called the **parent graph**;
the embedded graph is called the **subgraph**.

```
Parent StateGraph
  ├── node: my_other_node
  ├── node: docgen_subgraph   <── this is the compiled DocGen pipeline
  └── node: post_process_node
```

The subgraph runs its full six-node pipeline (retrieve → plan → diagrams → write → review →
assemble) as a single atomic node from the parent's perspective. Its internal nodes, edges,
and error routing are invisible to the parent.

### Why embed as a subgraph?

- **Reuse without duplication.** Any parent agent can generate BRD, TSD, Product Note, or
  Circular documents without reimplementing the pipeline.
- **State isolation.** The subgraph receives only the keys it needs. The parent maps its own
  richer state into the subgraph's input contract, then maps the outputs back.
- **Independent upgrades.** The DocGen pipeline can be updated (new LLMs, new blueprints,
  new validation rules) without touching the parent graph.
- **Parallel fan-out.** The parent can dispatch multiple `Send` messages to the subgraph
  simultaneously to generate all four document types concurrently.

---

## 2. State Contract

The pipeline state is a plain Python `dict`. The `GraphState` Pydantic model in
`app/models.py` documents the full schema; only a subset is required to start a run.

### Required input keys (must be provided by caller)

| Key | Type | Description |
|-----|------|-------------|
| `job_id` | `str` | Unique identifier for this generation job. Used for output path and artifact storage. |
| `prompt` | `str` | The natural-language description of what the document should contain. Minimum 10 characters. |
| `doc_type` | `str` | One of `"BRD"`, `"TSD"`, `"Product Note"`, `"Circular"`. Defaults to `"BRD"`. |

### Optional input keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `document_title` | `str` | `None` | Override the document title. Blueprint sets a default if absent. |
| `version_number` | `str` | `"1.0"` | Document version shown on cover page. |
| `classification` | `str` | `"Draft / Confidential"` | Classification label shown in footer. |
| `collection_name` | `str` | `"default"` | ChromaDB collection to query for RAG context. |
| `use_rag` | `bool` | `True` | Set `False` to skip RAG retrieval entirely. |
| `include_diagrams` | `bool` | `True` | Set `False` to skip diagram generation. |
| `audience` | `str` | `None` | Audience hint passed to the writer LLM. |
| `desired_outcome` | `str` | `None` | Desired outcome hint for the writer LLM. |
| `format_constraints` | `str` | `None` | Any formatting constraints for the writer LLM. |
| `organization_name` | `str` | `"NPCI"` | Organization name used in cover and Circular letterhead. |
| `reference_code` | `str` | `None` | OC reference code for Circular documents. |
| `issue_date` | `str` | today | Issue date string (e.g., `"10 April 2026"`). |
| `recipient_line` | `str` | `None` | Circular addressee line. |
| `subject_line` | `str` | `None` | Circular subject line. |
| `signatory_name` | `str` | `None` | Name of the approving signatory. |
| `signatory_title` | `str` | `None` | Title of the approving signatory. |
| `signatory_department` | `str` | `None` | Department of the approving signatory. |
| `additional_context` | `str` | `None` | Extra context appended to the planner prompt. |

### Output keys written by the pipeline

| Key | Type | Set by node | Description |
|-----|------|-------------|-------------|
| `rag_context` | `str` | `retrieve_context` | Concatenated RAG chunks passed to planner and writer. |
| `rag_chunks` | `list[str]` | `retrieve_context` | Individual retrieved chunks. |
| `document_plan` | `dict` | `plan_document` | Full `DocumentPlan` dict: title, sections, document_meta. |
| `diagram_specs` | `list[dict]` | `plan_document` | One entry per diagram to generate: `diagram_id`, `target_heading`, `diagram_type`, `description`. |
| `generated_diagrams` | `dict[str, str]` | `generate_diagrams` | Maps `diagram_id` → absolute PNG file path. |
| `generated_sections` | `list[dict]` | `write_content` | One `GeneratedContent` dict per section. |
| `output_path` | `str` | `assemble_doc` | Absolute path to the final `.docx` file. |
| `status` | `str` | all nodes | Last status: `"completed"` on success, `"failed"` on error. |
| `error` | `str \| None` | `handle_error` | Error message if the pipeline failed. |

---

## 3. Minimal Embedding Example

```python
"""parent_graph.py — minimal example embedding DocGen as a subgraph node."""
import uuid
from langgraph.graph import StateGraph, END
from app.agents.pipeline import build_pipeline


# Build the docgen subgraph once at module level (singleton).
_docgen = build_pipeline()


def my_pre_node(state: dict) -> dict:
    """Prepare the initial state before handing off to docgen."""
    state["job_id"] = str(uuid.uuid4())
    state["doc_type"] = "BRD"
    state["prompt"] = state["user_request"]
    state["use_rag"] = True
    state["include_diagrams"] = True
    state["collection_name"] = "default"
    return state


def my_post_node(state: dict) -> dict:
    """Do something with the generated document."""
    if state.get("status") == "completed":
        print(f"Document ready: {state['output_path']}")
    else:
        print(f"Generation failed: {state.get('error')}")
    return state


def build_parent_graph():
    graph = StateGraph(dict)

    graph.add_node("pre", my_pre_node)
    graph.add_node("docgen", _docgen)       # compiled subgraph used as a node
    graph.add_node("post", my_post_node)

    graph.set_entry_point("pre")
    graph.add_edge("pre", "docgen")
    graph.add_edge("docgen", "post")
    graph.add_edge("post", END)

    return graph.compile()


if __name__ == "__main__":
    parent = build_parent_graph()
    result = parent.invoke({"user_request": "Generate a BRD for UPI biometric authentication."})
    print("Final status:", result.get("status"))
    print("Output file:", result.get("output_path"))
```

---

## 4. State Mapping Example

If your parent graph uses different key names from the docgen contract, use input/output
transformer functions to remap keys before and after the subgraph call.

```python
"""state_mapping.py — mapping parent state keys to docgen state keys."""
import uuid
from langgraph.graph import StateGraph, END
from app.agents.pipeline import build_pipeline

_docgen = build_pipeline()


def map_to_docgen(state: dict) -> dict:
    """
    Map parent-graph keys to the docgen state contract.
    Returns a new dict — do not mutate the incoming state.
    """
    return {
        # Required keys
        "job_id": state.get("run_id") or str(uuid.uuid4()),
        "prompt": state["feature_description"],   # parent key → docgen key
        "doc_type": state.get("output_format", "TSD"),

        # Optional keys carried through
        "document_title": state.get("title"),
        "version_number": state.get("version", "1.0"),
        "classification": state.get("sensitivity", "Confidential"),
        "collection_name": state.get("kb_collection", "upi_knowledge"),
        "use_rag": state.get("enable_rag", True),
        "include_diagrams": state.get("with_diagrams", True),
        "organization_name": state.get("org", "NPCI"),

        # Pass through any keys the subgraph needs that are already present
        "rag_context": "",
        "rag_chunks": [],
        "document_plan": None,
        "diagram_specs": [],
        "generated_diagrams": {},
        "generated_sections": [],
        "output_path": None,
        "status": "pending",
        "error": None,
    }


def map_from_docgen(parent_state: dict, docgen_result: dict) -> dict:
    """
    Merge docgen output keys back into the parent state.
    Only copy keys the parent graph cares about.
    """
    return {
        **parent_state,
        "generated_doc_path": docgen_result.get("output_path"),
        "generation_status": docgen_result.get("status"),
        "generation_error": docgen_result.get("error"),
        "doc_plan": docgen_result.get("document_plan"),
    }


# ---------------------------------------------------------------------------
# Wrap the subgraph with the mapper
# ---------------------------------------------------------------------------

def docgen_with_mapping(state: dict) -> dict:
    docgen_input = map_to_docgen(state)
    docgen_output = _docgen.invoke(docgen_input)
    return map_from_docgen(state, docgen_output)


def build_parent():
    graph = StateGraph(dict)
    graph.add_node("prepare", lambda s: {**s, "feature_description": s["raw_input"]})
    graph.add_node("docgen", docgen_with_mapping)
    graph.add_node("notify", lambda s: {**s, "done": True})
    graph.set_entry_point("prepare")
    graph.add_edge("prepare", "docgen")
    graph.add_edge("docgen", "notify")
    graph.add_edge("notify", END)
    return graph.compile()
```

---

## 5. Using the RAG Tools Directly

The retrieval functions in `app/rag/engine.py` can be imported and used as LangChain tools
inside any parent agent without going through the full docgen pipeline.

```python
"""rag_tools.py — wrap DocGen RAG functions as LangChain tools."""
from langchain_core.tools import tool
from app.rag.engine import retrieve, retrieve_multi_query, ingest_file


@tool
def retrieve_upi_knowledge(query: str) -> str:
    """
    Search the UPI knowledge base (NPCI docs, circulars, product notes) for
    content relevant to the query. Returns the top matching passages as a
    single string block.
    """
    chunks, context = retrieve_multi_query(
        prompt=query,
        topic=" ".join(query.split()[:6]),
        collection_name="upi_knowledge",
    )
    return context if context else "No relevant content found."


@tool
def retrieve_upi_code(query: str) -> str:
    """
    Search the UPI source code collection for implementation examples,
    API handler patterns, or schema definitions relevant to the query.
    Returns matching code snippets as a single string block.
    """
    chunks, context = retrieve_multi_query(
        prompt=query,
        topic=" ".join(query.split()[:6]),
        collection_name="upi_code",
    )
    return context if context else "No relevant code found."


# ---------------------------------------------------------------------------
# Use in a ReAct agent
# ---------------------------------------------------------------------------

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from app.config import settings

llm = ChatOllama(model=settings.model_name, base_url=settings.ollama_base_url)
rag_agent = create_react_agent(llm, tools=[retrieve_upi_knowledge, retrieve_upi_code])

# Invoke:
# result = rag_agent.invoke({"messages": [("user", "What is the CL version for biometric UPI?")]})
```

To ingest new documents into a named collection:

```python
from app.rag.engine import ingest_file

# Add NPCI documentation to the knowledge collection
chunks_added = ingest_file("./docs/upi_biometric_spec.pdf", collection_name="upi_knowledge")
print(f"Ingested {chunks_added} chunks.")

# Add source code to the code collection
chunks_added = ingest_file("./src/payment_handler.py", collection_name="upi_code")
```

---

## 6. Adding DocGen as a Tool

Wrap `run_pipeline` as a LangChain `@tool` so any ReAct or tool-calling agent can invoke
document generation as a single tool call.

```python
"""docgen_tool.py — wrap the full pipeline as a @tool."""
import uuid
from langchain_core.tools import tool
from app.agents.pipeline import run_pipeline


@tool
def generate_document(
    prompt: str,
    doc_type: str = "BRD",
    collection_name: str = "default",
    include_diagrams: bool = True,
) -> str:
    """
    Generate a professional NPCI-standard document (.docx) from a natural-language
    description. Supported doc_type values: 'BRD', 'TSD', 'Product Note', 'Circular'.

    Returns the absolute path to the generated .docx file, or an error message.
    """
    job_id = str(uuid.uuid4())
    initial_state = {
        "job_id": job_id,
        "prompt": prompt,
        "doc_type": doc_type,
        "collection_name": collection_name,
        "use_rag": True,
        "include_diagrams": include_diagrams,
        "rag_context": "",
        "rag_chunks": [],
        "document_plan": None,
        "diagram_specs": [],
        "generated_diagrams": {},
        "generated_sections": [],
        "output_path": None,
        "status": "pending",
        "error": None,
    }
    result = run_pipeline(initial_state)
    if result.get("status") == "completed":
        return f"Document generated successfully: {result['output_path']}"
    return f"Document generation failed: {result.get('error', 'unknown error')}"


# ---------------------------------------------------------------------------
# Use inside a ReAct agent
# ---------------------------------------------------------------------------

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from app.config import settings

llm = ChatOllama(model=settings.model_name, base_url=settings.ollama_base_url)
agent = create_react_agent(llm, tools=[generate_document])

# Example invocation:
# result = agent.invoke({
#     "messages": [("user", "Generate a TSD for the UPI AutoPay mandate feature.")]
# })
```

---

## 7. Parallel Document Generation (Fan-Out with Send API)

Use LangGraph's `Send` API to fan out four independent docgen subgraph invocations in a
single parent node. All four documents generate concurrently; a fan-in node collects the
results.

```python
"""parallel_docgen.py — generate all 4 doc types in parallel using Send."""
import uuid
from typing import Annotated
from langgraph.graph import StateGraph, END
from langgraph.types import Send
from app.agents.pipeline import build_pipeline

_docgen = build_pipeline()

_DOC_TYPES = ["BRD", "TSD", "Product Note", "Circular"]


# ---------------------------------------------------------------------------
# Parent state schema
# ---------------------------------------------------------------------------

def _merge_results(existing: list, new: list) -> list:
    """Reducer that accumulates results from parallel branches."""
    return (existing or []) + (new or [])


class BundleState:
    prompt: str
    collection_name: str
    # Accumulated results from parallel branches (uses reducer)
    results: Annotated[list, _merge_results]


# ---------------------------------------------------------------------------
# Fan-out node: dispatch one Send per doc type
# ---------------------------------------------------------------------------

def fan_out(state: dict) -> list[Send]:
    """Return one Send message per document type."""
    sends = []
    for doc_type in _DOC_TYPES:
        child_state = {
            "job_id": str(uuid.uuid4()),
            "prompt": state["prompt"],
            "doc_type": doc_type,
            "collection_name": state.get("collection_name", "default"),
            "use_rag": True,
            "include_diagrams": doc_type != "Circular",
            "rag_context": "",
            "rag_chunks": [],
            "document_plan": None,
            "diagram_specs": [],
            "generated_diagrams": {},
            "generated_sections": [],
            "output_path": None,
            "status": "pending",
            "error": None,
        }
        sends.append(Send("docgen", child_state))
    return sends


# ---------------------------------------------------------------------------
# Fan-in node: collect results
# ---------------------------------------------------------------------------

def fan_in(state: dict) -> dict:
    """Summarise all generated documents."""
    results = state.get("results", [])
    completed = [r for r in results if r.get("status") == "completed"]
    failed = [r for r in results if r.get("status") != "completed"]
    print(f"Generated {len(completed)}/{len(_DOC_TYPES)} documents.")
    for r in completed:
        print(f"  {r.get('doc_type', '?')}: {r['output_path']}")
    for r in failed:
        print(f"  FAILED {r.get('doc_type', '?')}: {r.get('error')}")
    return {"summary": {"completed": len(completed), "failed": len(failed)}}


# ---------------------------------------------------------------------------
# Wrap docgen subgraph so its output can be collected into `results`
# ---------------------------------------------------------------------------

def docgen_node(state: dict) -> dict:
    """Run the docgen subgraph and return result in a list for the reducer."""
    result = _docgen.invoke(state)
    # Keep doc_type for the summary
    result["doc_type"] = state.get("doc_type", "Unknown")
    return {"results": [result]}


# ---------------------------------------------------------------------------
# Build parent graph
# ---------------------------------------------------------------------------

def build_bundle_graph():
    graph = StateGraph(dict)

    graph.add_node("fan_out_node", fan_out)
    graph.add_node("docgen", docgen_node)
    graph.add_node("fan_in_node", fan_in)

    graph.set_entry_point("fan_out_node")

    # fan_out returns Send objects — LangGraph routes each to "docgen"
    graph.add_conditional_edges("fan_out_node", lambda s: s, ["docgen"])
    graph.add_edge("docgen", "fan_in_node")
    graph.add_edge("fan_in_node", END)

    return graph.compile()


if __name__ == "__main__":
    bundle = build_bundle_graph()
    bundle.invoke({"prompt": "UPI biometric authentication via fingerprint at PoS terminals."})
```

---

## 8. Checkpoint and Resume

### Where artifacts are stored

Every pipeline run writes three JSON artifacts under `./outputs/{job_id}/`:

| File | Written by node | Contents |
|------|----------------|----------|
| `document_plan.json` | `plan_document` | Full `DocumentPlan` dict: title, sections, document_meta. |
| `generated_sections.json` | `write_content` | List of `GeneratedContent` dicts, one per section. |
| `review_report.json` | `review_document` | Validation errors and warnings. |
| `document.docx` | `assemble_doc` | Final assembled Word document. |
| `diagram_{id}_{hex}.png` | `generate_diagrams` | One PNG per generated diagram. |

The `job_id` is set by the caller in the initial state and is also used as the output
directory name: `{OUTPUT_DIR}/{job_id}/document.docx`.

### Resuming a partially completed run

If the pipeline fails at `write_content` or later, you can skip the retrieval and planning
stages by pre-populating the relevant state keys from the saved artifacts:

```python
import json
from pathlib import Path
from app.agents.pipeline import get_pipeline

job_id = "your-existing-job-id"
output_dir = Path(f"./outputs/{job_id}")

# Load previously saved plan
plan = json.loads((output_dir / "document_plan.json").read_text())

# Resume from write_content onward by pre-populating plan keys
resume_state = {
    "job_id": job_id,
    "prompt": "UPI biometric authentication",   # must be present
    "doc_type": plan.get("doc_type", "BRD"),
    "document_plan": plan,
    "diagram_specs": [],       # regenerate diagrams, or load from a prior run
    "generated_diagrams": {},
    "rag_context": "",
    "rag_chunks": [],
    "generated_sections": [],
    "output_path": None,
    "status": "pending",
    "error": None,
    "use_rag": False,          # skip RAG re-retrieval
    "include_diagrams": True,
    "collection_name": "default",
}

pipeline = get_pipeline()
result = pipeline.invoke(resume_state)
print(result["output_path"])
```

For full LangGraph checkpointing (persistence across process restarts), configure a
`SqliteSaver` or `PostgresSaver` when compiling the pipeline:

```python
from langgraph.checkpoint.sqlite import SqliteSaver
from app.agents.pipeline import build_pipeline

memory = SqliteSaver.from_conn_string("./checkpoints.db")
pipeline = build_pipeline().compile(checkpointer=memory)

# Invoke with a thread_id so LangGraph stores state per thread
result = pipeline.invoke(initial_state, config={"configurable": {"thread_id": job_id}})
```

---

## 9. Configuration

All configuration is loaded from `.env` via `app/config.py` (`pydantic-settings`). Set these
variables in the subgraph's runtime environment.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `MODEL_NAME` | `gpt-oss:120b-cloud` | Yes | Ollama model tag used for all LLM calls. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Yes | Base URL for the Ollama HTTP API. |
| `TEMPERATURE` | `0.3` | No | Generation temperature for the free-form writer LLM. Planner LLM always uses 0.0. |
| `OUTPUT_DIR` | `./outputs` | No | Directory where `{job_id}/document.docx` is written. |
| `VECTORSTORE_DIR` | `./vectorstore` | No | Path to the ChromaDB persistent storage. |
| `UPLOAD_DIR` | `./uploads` | No | Temporary directory for uploaded RAG files. |
| `CHUNK_SIZE` | `1500` | No | Token chunk size for the RAG text splitter. |
| `CHUNK_OVERLAP` | `200` | No | Overlap tokens between adjacent chunks. |
| `TOP_K_RESULTS` | `8` | No | Maximum number of RAG chunks to retrieve per query. |
| `RAG_DISTANCE_THRESHOLD` | `0.45` | No | Cosine distance cutoff for relevance filtering. |
| `RAG_MIN_TOKEN_OVERLAP` | `2` | No | Minimum shared tokens for a chunk to be considered relevant. |
| `DEFAULT_FONT` | `Calibri` | No | Font used throughout the generated document. |
| `DEFAULT_FONT_SIZE` | `11` | No | Base body font size in points. |

For a subgraph running inside a Docker container or a remote environment, map these as
environment variables rather than relying on a local `.env` file:

```bash
export MODEL_NAME=llama3.1:70b
export OLLAMA_BASE_URL=http://ollama-service:11434
export OUTPUT_DIR=/app/outputs
export VECTORSTORE_DIR=/app/vectorstore
```
