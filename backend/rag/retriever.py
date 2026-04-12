"""
Hybrid RAG retriever: Dense (ChromaDB) + Sparse (BM25) fused via Reciprocal Rank Fusion.
Optional cross-encoder reranking step.
"""
import logging
from typing import Optional

from langchain_community.vectorstores import Chroma
from rank_bm25 import BM25Okapi

import config

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    dense_results: list,   # list of (doc, score) from ChromaDB
    sparse_results: list,  # list of (doc, bm25_score) from BM25
    k: int = 60,
) -> list:
    """
    Merge dense and sparse results using RRF.
    Returns sorted list of (doc, rrf_score).
    """
    doc_scores: dict[str, float] = {}
    doc_map: dict[str, object] = {}

    def _id(doc) -> str:
        # Use page_content as unique key (good enough for local RAG)
        return doc.page_content[:200]

    # Dense ranks
    for rank, (doc, _score) in enumerate(dense_results):
        doc_id = _id(doc)
        doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1 / (k + rank + 1)
        doc_map[doc_id] = doc

    # Sparse ranks
    for rank, (doc, _score) in enumerate(sparse_results):
        doc_id = _id(doc)
        doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1 / (k + rank + 1)
        doc_map[doc_id] = doc

    sorted_ids = sorted(doc_scores, key=lambda x: doc_scores[x], reverse=True)
    return [(doc_map[doc_id], doc_scores[doc_id]) for doc_id in sorted_ids]


class HybridRetriever:
    def __init__(self, vector_store: Chroma, bm25: BM25Okapi, bm25_chunks: list):
        self.vector_store = vector_store
        self.bm25 = bm25
        self.bm25_chunks = bm25_chunks

    def _dense_search(self, query: str, top_k: int, knowledge_type: Optional[str] = None) -> list:
        filter_dict = {"knowledge_type": knowledge_type} if knowledge_type else None
        results = self.vector_store.similarity_search_with_score(
            query,
            k=top_k,
            filter=filter_dict,
        )
        return results  # list of (Document, float)

    def _sparse_search(self, query: str, top_k: int, knowledge_type: Optional[str] = None) -> list:
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)

        # Pair with chunks and optionally filter by knowledge type
        paired = list(zip(scores, self.bm25_chunks))
        if knowledge_type:
            paired = [(s, d) for s, d in paired if d.metadata.get("knowledge_type") == knowledge_type]

        paired.sort(key=lambda x: x[0], reverse=True)
        top = paired[:top_k]
        return [(doc, score) for score, doc in top]

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        knowledge_type: Optional[str] = None,
    ) -> list[dict]:
        """
        Hybrid retrieve. Returns list of dicts with content, metadata, score.
        """
        dense_k = config.DENSE_TOP_K
        sparse_k = config.BM25_TOP_K
        final_k = top_k or config.FINAL_TOP_K

        dense_results = self._dense_search(query, dense_k, knowledge_type)
        sparse_results = self._sparse_search(query, sparse_k, knowledge_type)

        fused = reciprocal_rank_fusion(dense_results, sparse_results)
        top_results = fused[:final_k]

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": round(score, 4),
            }
            for doc, score in top_results
        ]

    def build_context_string(self, results: list[dict]) -> str:
        """Format retrieved chunks into a context string for LLM prompts."""
        parts = []
        for i, r in enumerate(results, 1):
            source = r["metadata"].get("source_file", "unknown")
            kt = r["metadata"].get("knowledge_type", "")
            parts.append(f"[{i}] Source: {source} ({kt})\n{r['content']}")
        return "\n\n---\n\n".join(parts)
