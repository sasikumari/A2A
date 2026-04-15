import os
import requests
import json
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from llm_config import auth_headers, embedding_model_name, embeddings_url, load_project_env

load_project_env()

class DocumentStore:
    def __init__(self, use_memory=False):
        if use_memory:
            self.client = QdrantClient(":memory:")
        else:
            self.client = QdrantClient(path="qdrant_data")
        
        # We assume the same vLLM endpoint format, but targeting /embeddings
        # Fallback dummy embedding mode if API unreachable
        self.vllm_api_url = embeddings_url(default="http://183.82.7.228:9532/v1")
        self.model = embedding_model_name(default="/model")
        self.vector_size = 1024 # Standard fallback, but will adjust based on first embedding if possible
        
    def _get_embedding(self, text):
        payload = {
            "model": self.model,
            "input": [text]
        }
        try:
            response = requests.post(self.vllm_api_url, json=payload, headers=auth_headers(), timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data["data"][0]["embedding"]
        except Exception as e:
            print(f"[DocumentStore] Failed to fetch embedding from vLLM: {e}")
        
        # Fallback to a dummy random embedding vector if vLLM fails
        return [0.01] * self.vector_size

    def initialize_collection(self, collection_name="npci_circulars"):
        if not self.client.collection_exists(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
            )

    def ingest_document(self, doc_id, text, metadata, collection_name="npci_circulars"):
        self.initialize_collection(collection_name)
        embedding = self._get_embedding(text)
        
        # Update vector size config dynamically if it changes
        if len(embedding) != self.vector_size:
            print(f"[DocumentStore] Warning: Embedding size mismatch. Expected {self.vector_size}, got {len(embedding)}")
        
        point = PointStruct(
            id=doc_id,
            vector=embedding,
            payload={"text": text, **metadata}
        )
        self.client.upsert(
            collection_name=collection_name,
            points=[point]
        )
        print(f"Ingested document {doc_id} into {collection_name}")

    def query(self, text, collection_name="npci_circulars", limit=3, threshold=0.85):
        if not self.client.collection_exists(collection_name):
            return []
            
        query_vector = self._get_embedding(text)
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=threshold
        )
        
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "text": hit.payload.get("text", ""),
                "metadata": hit.payload
            }
            for hit in results
        ]
