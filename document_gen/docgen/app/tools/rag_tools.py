"""RAG tools for UPI knowledge base and UPI code repository retrieval.

These functions serve two purposes:
  1. Called directly by the pipeline's retrieve_context node
  2. Usable as tool nodes in a parent LangGraph workflow

Collections:
  UPI_KNOWLEDGE_COLLECTION = "upi_knowledge"  — NPCI docs, TSDs, BRDs, circulars
  UPI_CODE_COLLECTION       = "upi_code"       — Source files, XSD schemas, API specs
"""
from __future__ import annotations

import ast
import logging
import textwrap
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

UPI_KNOWLEDGE_COLLECTION = "upi_knowledge"
UPI_CODE_COLLECTION = "upi_code"

# ---------------------------------------------------------------------------
# Public retrieval functions (used by pipeline and parent LangGraph workflows)
# ---------------------------------------------------------------------------

def retrieve_upi_knowledge(query: str, top_k: int = 5) -> str:
    """Search the UPI knowledge base (NPCI docs, specs, circulars).
    Returns formatted string of top-K relevant passages, empty string if nothing found.
    """
    from app.rag.engine import retrieve_hybrid
    chunks = retrieve_hybrid(query, collection_name=UPI_KNOWLEDGE_COLLECTION, top_k=top_k)
    if not chunks:
        return ""
    return "\n\n---\n\n".join(chunks[:top_k])


def retrieve_upi_code(query: str, top_k: int = 5) -> str:
    """Search the UPI code repository (Python/Java source, XSD schemas, API contracts).
    Returns formatted string of top-K relevant code/schema passages.
    """
    from app.rag.engine import retrieve_hybrid
    chunks = retrieve_hybrid(query, collection_name=UPI_CODE_COLLECTION, top_k=top_k)
    if not chunks:
        return ""
    return "\n\n---\n\n".join(chunks[:top_k])


# ---------------------------------------------------------------------------
# Code-aware ingestion
# ---------------------------------------------------------------------------

def ingest_code_file(file_path: str) -> int:
    """Ingest a source code file into upi_code collection with smart chunking.

    Strategy by file type:
      .py          → AST-based chunking at function/class boundaries
      .java        → Heuristic class/method boundary chunking
      .xsd / .xml  → Element-definition chunking (top-level element blocks)
      other        → Recursive character chunking (512-token chunks)

    Returns number of chunks added.
    """
    from app.rag.engine import ingest_text

    path = Path(file_path)
    if not path.exists():
        logger.warning("[ingest_code_file] File not found: %s", file_path)
        return 0

    suffix = path.suffix.lower()
    raw = path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".py":
        chunks = _chunk_python(raw, str(path))
    elif suffix == ".java":
        chunks = _chunk_java(raw, str(path))
    elif suffix in (".xsd", ".xml"):
        chunks = _chunk_xml(raw, str(path))
    else:
        # Generic fallback — 800 char chunks with 100 char overlap
        size, overlap = 800, 100
        chunks = [raw[i: i + size] for i in range(0, len(raw), size - overlap) if raw[i: i + size].strip()]

    added = 0
    for chunk in chunks:
        if chunk.strip():
            n = ingest_text(chunk, collection_name=UPI_CODE_COLLECTION, source=str(path))
            added += n
    logger.info("[ingest_code_file] %s → %d chunks → upi_code", path.name, added)
    return added


def _chunk_python(source: str, filepath: str) -> list[str]:
    """Extract function and class bodies from a Python file using the AST."""
    chunks: list[str] = []
    lines = source.splitlines(keepends=True)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Fallback to raw chunking
        return [source[i: i + 800] for i in range(0, len(source), 700) if source[i: i + 800].strip()]

    # Collect top-level and nested class/function defs with their line ranges
    nodes: list[tuple[str, int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            end_line = getattr(node, "end_lineno", None)
            if end_line:
                nodes.append((node.name, node.lineno, end_line))

    # Sort by start line, take non-overlapping regions
    nodes.sort(key=lambda x: x[0])
    for name, start, end in nodes:
        body = "".join(lines[start - 1: end])
        header = f"# File: {filepath} | def/class: {name}\n"
        chunks.append(header + body)

    if not chunks:
        chunks = [source[i: i + 800] for i in range(0, len(source), 700) if source[i: i + 800].strip()]
    return chunks


def _chunk_java(source: str, filepath: str) -> list[str]:
    """Heuristic chunking for Java — split at class/method boundaries."""
    import re
    # Split on public/protected/private class/method declarations
    pattern = re.compile(
        r"(?=(?:public|protected|private|static|final|abstract)\s+(?:class|interface|enum|void|[A-Z]\w+))"
    )
    parts = pattern.split(source)
    chunks = []
    buffer = ""
    for part in parts:
        if len(buffer) + len(part) > 1000:
            if buffer.strip():
                chunks.append(f"// File: {filepath}\n{buffer}")
            buffer = part
        else:
            buffer += part
    if buffer.strip():
        chunks.append(f"// File: {filepath}\n{buffer}")
    return chunks or [source[i: i + 800] for i in range(0, len(source), 700)]


def _chunk_xml(source: str, filepath: str) -> list[str]:
    """Chunk XSD/XML by top-level element definitions."""
    import re
    # Match xs:element, xs:complexType, xs:simpleType blocks
    pattern = re.compile(
        r"(<xs:(?:element|complexType|simpleType)[^>]*>.*?</xs:(?:element|complexType|simpleType)>)",
        re.DOTALL,
    )
    matches = pattern.findall(source)
    if matches:
        return [f"<!-- File: {filepath} -->\n{m}" for m in matches]
    # Fallback: 800-char chunks
    return [source[i: i + 800] for i in range(0, len(source), 700) if source[i: i + 800].strip()]
