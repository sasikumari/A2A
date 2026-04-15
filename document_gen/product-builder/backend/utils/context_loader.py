"""
Context Loader: Facilities access to the NPCI regulatory knowledge base and
historical transaction context for agentic reasoning and technical synthesis.
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Any

# Path to the consolidated Titans repo root
TITANS_REPO_PATH = str(Path(__file__).resolve().parents[3])

def load_product_context() -> str:
    """
    Reads FEATURES_AND_FLOWS.md and other key documents from the Titans repo
    to build a comprehensive context for the agents.
    """
    context_parts = []
    
    # 1. Load Main Features & Flows
    features_path = os.path.join(TITANS_REPO_PATH, "FEATURES_AND_FLOWS.md")
    if os.path.exists(features_path):
        with open(features_path, "r") as f:
            content = f.read()
            # Extract only the key sections to keep context manageable
            context_parts.append("### EXISTING UPI FEATURES & FLOWS (REAL SYSTEM)\n" + content[:5000])

    # 2. Add any additional vision documents from the root if they exist
    # (Optional: can be expanded to PDF extraction if needed)
    
    # 3. Load input/output samples if possible
    samples_dir = os.path.join(TITANS_REPO_PATH, "Input-Output sample")
    if os.path.exists(samples_dir):
        context_parts.append("\n### ACTUAL XML TRANSACTION SAMPLES")
        for filename in os.listdir(samples_dir)[:3]:
            if filename.endswith(".xml") or filename.endswith(".json"):
                with open(os.path.join(samples_dir, filename), "r") as f:
                    context_parts.append(f"File: {filename}\n```\n{f.read()[:500]}\n```")

    return "\n\n".join(context_parts)

def get_relevant_previous_products(query: str) -> str:
    """
    Simple keyword-based retrieval of relevant sections from the context.
    """
    context = load_product_context()
    # For now, just return the whole context if it's not too large, 
    # or implement a simple chunk search.
    return context[:8000] # LLM context window safety
