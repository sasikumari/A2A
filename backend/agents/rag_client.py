"""
RAG Client Agent.
Abstracts whether retrieval is local (HybridRetriever) or remote (POST /rag/query).
All agents call this module — never hit ChromaDB/BM25 directly.
"""
import logging
import httpx
from typing import Optional

import config

logger = logging.getLogger(__name__)

# These are set at app startup via init_rag_client()
_retriever = None


def init_rag_client(retriever):
    """Called once at FastAPI startup with the HybridRetriever instance."""
    global _retriever
    _retriever = retriever
    logger.info(f"RAG client initialized in '{config.RAG_MODE}' mode")


async def query_rag(
    query: str,
    context: Optional[str] = None,
    top_k: int = 6,
    knowledge_type: Optional[str] = None,
) -> dict:
    """
    Unified RAG query interface.
    Returns: {"results": [...], "enriched_context": "..."}
    """
    if config.RAG_MODE == "remote":
        return await _remote_query(query, context, top_k, knowledge_type)
    return _local_query(query, top_k, knowledge_type)


def _local_query(query: str, top_k: int, knowledge_type: Optional[str]) -> dict:
    if _retriever is None:
        raise RuntimeError("RAG client not initialized. Call init_rag_client() at startup.")
    results = _retriever.retrieve(query, top_k=top_k, knowledge_type=knowledge_type)
    enriched_context = _retriever.build_context_string(results)
    return {"results": results, "enriched_context": enriched_context}


async def _remote_query(
    query: str,
    context: Optional[str],
    top_k: int,
    knowledge_type: Optional[str],
) -> dict:
    payload = {"query": query, "context": context, "top_k": top_k, "knowledge_type": knowledge_type}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(config.RAG_ENDPOINT, json=payload)
        resp.raise_for_status()
        return resp.json()
