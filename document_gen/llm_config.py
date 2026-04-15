from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
ROOT_ENV = PROJECT_ROOT / ".env"


def load_project_env() -> None:
    if ROOT_ENV.exists():
        load_dotenv(ROOT_ENV, override=False)


def _normalize_base_url(url: str) -> str:
    value = (url or "").strip().rstrip("/")
    if not value:
        return ""
    if value.endswith("/chat/completions"):
        return value[: -len("/chat/completions")]
    if value.endswith("/embeddings"):
        return value[: -len("/embeddings")]
    return value


def openai_compat_base_url(default: str = "") -> str:
    load_project_env()
    value = (
        os.getenv("OPENAI_COMPAT_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("LLM_BASE_URL")
        or default
    )
    value = _normalize_base_url(value)
    if value and not value.endswith("/v1"):
        value = f"{value}/v1"
    return value


def chat_completions_url(default: str = "") -> str:
    load_project_env()
    explicit = (os.getenv("LLM_API_URL") or "").strip()
    if explicit:
        return explicit
    base = openai_compat_base_url(default=default)
    return f"{base}/chat/completions" if base else ""


def embeddings_url(default: str = "") -> str:
    load_project_env()
    explicit = (os.getenv("OPENAI_COMPAT_EMBEDDING_URL") or os.getenv("LLM_EMBEDDING_URL") or "").strip()
    if explicit:
        return explicit
    base = openai_compat_base_url(default=default)
    return f"{base}/embeddings" if base else ""


def model_name(default: str = "") -> str:
    load_project_env()
    return (
        os.getenv("OPENAI_COMPAT_MODEL")
        or os.getenv("OPENAI_MODEL_NAME")
        or os.getenv("LLM_MODEL")
        or default
    )


def embedding_model_name(default: str = "") -> str:
    load_project_env()
    return (
        os.getenv("OPENAI_COMPAT_EMBEDDING_MODEL")
        or os.getenv("LLM_EMBEDDING_MODEL")
        or model_name(default=default)
        or default
    )


def api_key(default: str = "none") -> str:
    load_project_env()
    return (
        os.getenv("OPENAI_COMPAT_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("LLM_API_KEY")
        or default
    )


def auth_headers(default_api_key: str = "none") -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key(default=default_api_key)}",
    }
