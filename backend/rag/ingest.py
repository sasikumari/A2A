"""
Document ingestion pipeline.
Loads all documents from /documents, chunks them, embeds into ChromaDB,
and builds a BM25 index for hybrid retrieval.
"""
import os
import pickle
import logging
from pathlib import Path
from typing import Optional

from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredExcelLoader,
    TextLoader,
    UnstructuredXMLLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from rank_bm25 import BM25Okapi

import config

logger = logging.getLogger(__name__)

# Paths
BM25_INDEX_PATH = Path(config.CHROMA_PERSIST_DIR) / "bm25_index.pkl"
BM25_DOCS_PATH = Path(config.CHROMA_PERSIST_DIR) / "bm25_docs.pkl"

# File extension → loader mapping
LOADER_MAP = {
    ".pdf": PyPDFLoader,
    ".xlsx": UnstructuredExcelLoader,
    ".xsd": UnstructuredXMLLoader,
    ".txt": TextLoader,
}

# Files with no extension treated as text
NO_EXT_AS_TEXT = True


def _get_loader(file_path: Path):
    ext = file_path.suffix.lower()
    if ext in LOADER_MAP:
        return LOADER_MAP[ext](str(file_path))
    if NO_EXT_AS_TEXT and ext == "":
        return TextLoader(str(file_path), encoding="utf-8", autodetect_encoding=True)
    return None


def load_documents(documents_dir: str) -> list:
    docs_dir = Path(documents_dir)
    if not docs_dir.exists():
        raise FileNotFoundError(f"Documents directory not found: {docs_dir.resolve()}")

    all_docs = []
    for file_path in docs_dir.iterdir():
        if file_path.is_file():
            loader = _get_loader(file_path)
            if loader is None:
                logger.warning(f"No loader for: {file_path.name} — skipping")
                continue
            try:
                docs = loader.load()
                # Tag each doc with source metadata
                for doc in docs:
                    doc.metadata["source_file"] = file_path.name
                    doc.metadata["knowledge_type"] = _classify(file_path.name)
                all_docs.extend(docs)
                logger.info(f"Loaded {len(docs)} chunks from {file_path.name}")
            except Exception as e:
                logger.warning(f"Failed to load {file_path.name}: {e}")

    logger.info(f"Total documents loaded: {len(all_docs)}")
    return all_docs


def _classify(filename: str) -> str:
    """Tag each document with one of the 4 knowledge types."""
    fn = filename.lower()
    if "product deck" in fn or "canvas" in fn:
        return "product_canvas"
    if "oc-no" in fn or "rbi" in fn or "compliance" in fn or "circular" in fn:
        return "rbi_guidelines"
    if "tsd" in fn or "guidelines" in fn or "testcase" in fn:
        return "product_documents"
    if "upi" in fn or "qr" in fn or "xsd" in fn or fn.startswith("req"):
        return "upi_codebase"
    return "general"


def chunk_documents(docs: list, chunk_size: int = 800, chunk_overlap: int = 150) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    logger.info(f"Total chunks after splitting: {len(chunks)}")
    return chunks


def build_vector_store(chunks: list) -> Chroma:
    embeddings = OpenAIEmbeddings(
        model=config.EMBEDDING_MODEL,
        openai_api_key=config.OPENAI_API_KEY,
    )
    Path(config.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=config.CHROMA_COLLECTION,
        persist_directory=config.CHROMA_PERSIST_DIR,
    )
    logger.info("ChromaDB vector store built and persisted.")
    return vector_store


def build_bm25_index(chunks: list):
    """Build and persist BM25 index from chunk texts."""
    tokenized = [chunk.page_content.lower().split() for chunk in chunks]
    bm25 = BM25Okapi(tokenized)
    # Save index and raw chunks for later retrieval
    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump(bm25, f)
    with open(BM25_DOCS_PATH, "wb") as f:
        pickle.dump(chunks, f)
    logger.info(f"BM25 index saved to {BM25_INDEX_PATH}")
    return bm25, chunks


def load_bm25_index():
    with open(BM25_INDEX_PATH, "rb") as f:
        bm25 = pickle.load(f)
    with open(BM25_DOCS_PATH, "rb") as f:
        chunks = pickle.load(f)
    return bm25, chunks


def load_vector_store() -> Chroma:
    embeddings = OpenAIEmbeddings(
        model=config.EMBEDDING_MODEL,
        openai_api_key=config.OPENAI_API_KEY,
    )
    return Chroma(
        collection_name=config.CHROMA_COLLECTION,
        embedding_function=embeddings,
        persist_directory=config.CHROMA_PERSIST_DIR,
    )


def ingest_pipeline(documents_dir: Optional[str] = None, force: bool = False):
    """
    Full ingest pipeline. Skips if indexes already exist unless force=True.
    Returns (vector_store, bm25, bm25_chunks).
    """
    docs_dir = documents_dir or config.DOCUMENTS_DIR
    index_exists = BM25_INDEX_PATH.exists() and Path(config.CHROMA_PERSIST_DIR).exists()

    if index_exists and not force:
        logger.info("Indexes found — loading existing indexes.")
        vector_store = load_vector_store()
        bm25, bm25_chunks = load_bm25_index()
        return vector_store, bm25, bm25_chunks

    logger.info("Building indexes from scratch...")
    docs = load_documents(docs_dir)
    chunks = chunk_documents(docs)
    vector_store = build_vector_store(chunks)
    bm25, bm25_chunks = build_bm25_index(chunks)
    return vector_store, bm25, bm25_chunks
