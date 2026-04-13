"""
Change Orchestration Platform — FastAPI Backend
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from rag.ingest import ingest_pipeline
from rag.retriever import HybridRetriever
from agents.rag_client import init_rag_client
from routers import session, requirement, research, canvas, rag, history

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ------------------------------------------------------------------ #
    # Startup: build / load RAG indexes and initialize the RAG client
    # ------------------------------------------------------------------ #
    logger.info("Starting RAG ingestion pipeline...")
    try:
        vector_store, bm25, bm25_chunks = ingest_pipeline(
            documents_dir=config.DOCUMENTS_DIR,
            force=False,
        )
        retriever = HybridRetriever(vector_store, bm25, bm25_chunks)
        init_rag_client(retriever)
        logger.info("RAG client ready.")
    except Exception as e:
        logger.error(f"RAG initialization failed: {e}. Continuing without local RAG.")

    yield

    # ------------------------------------------------------------------ #
    # Shutdown (add cleanup if needed)
    # ------------------------------------------------------------------ #
    logger.info("Shutting down.")


app = FastAPI(
    title="Change Orchestration Platform",
    description="AI-driven Product Canvas generation via multi-agent pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(session.router)
app.include_router(requirement.router)
app.include_router(research.router)
app.include_router(canvas.router)
app.include_router(rag.router)
app.include_router(history.router)


@app.get("/health")
async def health():
    return {"status": "ok", "rag_mode": config.RAG_MODE, "model": config.MODEL_NAME}
