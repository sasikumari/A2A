"""
Shared LLM client for Product Builder agents.
Uses the vLLM endpoint at http://183.82.7.228:9535/v1
"""
import requests
import json
import re
import os
import time
from typing import Optional, Tuple

from llm_config import auth_headers, chat_completions_url, load_project_env, model_name

load_project_env()

LLM_URL = chat_completions_url(default="http://183.82.7.228:9535/v1")
LLM_MODEL = model_name(default="/model")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "180"))


def chat(
    system: str,
    user: str,
    temperature: float = 0.3,
    max_tokens: int = 8192,
    retries: int = 2,
) -> Tuple[str, str]:
    """
    Call the LLM. Returns (thinking_text, answer_text).
    thinking_text is extracted from <think>...</think> tags if present.
    """
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = requests.post(LLM_URL, json=payload, headers=auth_headers(), timeout=LLM_TIMEOUT)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]

            # Extract thinking
            think_match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
            thinking = think_match.group(1).strip() if think_match else ""
            answer = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

            return thinking, answer
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(2 ** attempt)

    print(f"[LLM] All retries exhausted. Last error: {last_err}")
    return "", ""


def extract_json(text: str) -> dict:
    """Best-effort JSON extractor from LLM output."""
    if not text:
        return {}
    t = text.strip()
    t = re.sub(r"```(?:json)?\n?", "", t).replace("```", "").strip()
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(t[start : end + 1])
    except Exception:
        return {}


def extract_json_array(text: str) -> list:
    """Best-effort JSON array extractor from LLM output."""
    if not text:
        return []
    t = text.strip()
    t = re.sub(r"```(?:json)?\n?", "", t).replace("```", "").strip()
    start = t.find("[")
    end = t.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        return json.loads(t[start : end + 1])
    except Exception:
        return []
