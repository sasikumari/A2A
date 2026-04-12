from fastapi import APIRouter
from schemas.models import RAGQueryRequest, RAGQueryResponse
from agents.rag_client import query_rag

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(req: RAGQueryRequest):
    result = await query_rag(
        query=req.query,
        context=req.context,
        top_k=req.top_k or 6,
        knowledge_type=req.knowledge_type,
    )
    return RAGQueryResponse(
        results=result["results"],
        enriched_context=result["enriched_context"],
    )
