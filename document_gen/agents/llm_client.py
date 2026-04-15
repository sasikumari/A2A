import requests
import json
import re
import os
from typing import List

from llm_config import auth_headers, chat_completions_url, load_project_env, model_name

load_project_env()

class LLMClient:
    _default_api_url = "http://183.82.7.228:9532/v1/chat/completions"
    _default_model = "/model"

    def __init__(self, api_url=None, model=None):
        self.api_url = api_url or chat_completions_url(default=self._default_api_url) or self._default_api_url
        self.model = model_name(default=model or self._default_model) or self._default_model
        self.headers = auth_headers()
        self.use_fallback_on_failure = os.getenv("USE_LLM_FALLBACK", "0").strip().lower() in ("1", "true", "yes")

    def generate_code_update(self, spec_change_description, current_code, file_path, file_type="python", brd="", tsd="", error_context=None, force_full_file: bool = False):
        """
        Generates updated code based on the spec change description.
        If error_context is provided, it asks the LLM to fix the error.
        """
        prompt = f"""
You are an expert software engineer for an NPCI UPI Agent Orchestrator. 
Apply the requested spec change to the following file.

CONTEXT:
Business Requirements (BRD): 
{brd or "See spec change request."}

Technical Specification (TSD):
{tsd or "See spec change request."}

File: {os.path.basename(file_path)}
Current Content:
```{file_type}
{current_code}
```

Spec Change Request: {spec_change_description}

NPCI Technical Standards:
1. XML Namespaces MUST be preserved (targetNamespace="http://npci.org/upi/schema/").
2. Transaction Amounts MUST use attributes: `<Amount value="100.00" curr="INR"/>`. Do NOT use text content within `<Amount>`.
3. Amounts MUST be decimal strings with exactly two decimal places (e.g., "500.00").
4. In XSDs, use xs:decimal for amount value attributes, NOT xs:integer.
5. CRITICAL XSD RULE: NEVER add xs:maxInclusive or xs:minInclusive to AmountValueType in upi_pay_request.xsd.
   Amount limits are BUSINESS RULES enforced in Python (switch/upi_switch.py constants P2P_LIMIT, MAX_TXN_AMOUNT).
   Adding maxInclusive to the XSD will fail the Phase 1 compatibility check and be rejected.
6. CRITICAL XSD RULE: Never make Payee>Amount required. It MUST stay minOccurs="0".
7. CRITICAL XSD RULE: Preserve the xs:sequence order in ReqPay:
   Head → Txn → purpose(opt) → purposeCode(opt) → Payer → Payees → RiskScore(opt) → HighValue(opt) → extensions
8. For LIMIT CHANGES: Only change switch/upi_switch.py (P2P_LIMIT / MAX_TXN_AMOUNT constants). Do NOT touch the XSD.
9. CRITICAL: Do NOT truncate. You MUST return the COMPLETE file every time.
"""
        if error_context:
            prompt += f"""
IMPORTANT: The previous attempt failed with the following verification or syntax error:
{error_context}

You MUST fix this issue in your new change.
"""

        if force_full_file:
            # Recovery mode: require full file only (no surgical patches, no truncation).
            prompt += f"""
Return ONLY the COMPLETE updated file content, inside a single fenced code block. The output MUST contain the entire file from start to end.
```{file_type}
<entire updated file here - same length or longer than the original, never shorter>
```

Do NOT truncate. Do NOT include SEARCH/REPLACE blocks, <<<< / ==== / >>>>, or any prose.
"""
        else:
            # Normal mode: prefer safe full‑file updates, but allow surgical
            # SEARCH/REPLACE blocks when the model is absolutely certain.
            prompt += f"""
You have two options for returning the updated code:

OPTION A (preferred, safest):
- Return the COMPLETE updated file content only, inside a single fenced code block:
```{file_type}
<entire updated file here>
```
- Do NOT include any commentary or explanation outside the code block.

OPTION B (advanced, only if 100% sure):
- Return one or more SEARCH/REPLACE blocks in this exact format:

<<<< SEARCH
<exact lines from the CURRENT file to replace>
====
<new lines that should replace them>
>>>>

Rules for OPTION B:
1. The SEARCH block MUST match the existing code EXACTLY, including indentation and spacing.
2. Use SEARCH/REPLACE only when you are absolutely certain of an exact match.
3. Do NOT mix commentary or markdown around the blocks.

If you are not absolutely sure the SEARCH text matches the current file, use OPTION A and return the full updated file instead.
"""
        
        # Use high max_tokens so large files (e.g. 40KB+ handlers) are not truncated
        max_tokens = min(65536, max(16384, len(current_code) // 2 + 4096))
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful coding assistant. Output only code. Never truncate; always return the complete file."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens
        }

        retry_count = 0
        max_retries = 3
        backoff = 2

        while retry_count < max_retries:
            try:
                print(f"[LLMClient] Sending request to {self.api_url} (Attempt {retry_count+1})...")
                response = requests.post(self.api_url, json=payload, headers=self.headers, timeout=300) 
                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Strip <think> tags if present
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                
                # Parse SEARCH/REPLACE blocks
                if not force_full_file and "<<<< SEARCH" in content:
                    # In normal mode we hand raw blocks to BaseAgent, which
                    # will apply them surgically. In force_full_file mode we
                    # intentionally ignore these markers and instead fall
                    # through to the full‑file extraction logic below.
                    return content # Return raw blocks to be handled by BaseAgent
                
                # Extract code block more robustly
                code_match = re.search(r"```(?:\w+)?\n?(.*?)```", content, re.DOTALL)
                if code_match:
                    code = code_match.group(1).strip()
                else:
                    code = content.replace("```", "").strip()
                
                return code

            except Exception as e:
                print(f"[LLMClient] Error: {e}. Retrying in {backoff}s...")
                import time
                time.sleep(backoff)
                retry_count += 1
                backoff *= 2

        print("[LLMClient] Max retries exceeded. Returning None.")
        if self.use_fallback_on_failure:
            print("[LLMClient] USE_LLM_FALLBACK=1: Returning current code unchanged so execution can complete.")
            return current_code
        return None

    def _fallback_generate(self, current_code, file_type):
        # Simple mock fallback for the demo
        if file_type == "xml":
            if "<aiAgent>" not in current_code:
                return current_code.replace("</ReqPay>", "    <aiAgent>true</aiAgent>\n</ReqPay>")
        elif file_type == "python":
            if "ai_agent" not in current_code:
                return current_code.replace("return True", "print('AI Agent: True')\n    return True")
        return current_code

    def query(self, prompt: str, system: str = "", max_tokens: int = 4096) -> str:
        """
        Generic LLM query. Returns the raw text response.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        else:
            messages.append({"role": "system", "content": "You are a helpful assistant. Output valid JSON when requested."})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }

        try:
            response = requests.post(self.api_url, json=payload, headers=self.headers, timeout=300)
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            return content
        except Exception as e:
            print(f"[LLMClient] Query Error: {e}")
            return "{}"

    def plan_with_skills(
        self,
        intent: str,
        tool_specs: list[dict],
        context: str = "",
        max_tokens: int = 4096,
    ) -> str:
        """
        Ask the LLM to produce a skill call plan given an intent and available tools.
        Returns raw JSON string of the plan array.

        tool_specs: list of tool spec dicts from SkillRegistry.to_tool_specs()
        """
        tools_json = json.dumps(tool_specs, indent=2)
        system = (
            "You are an expert agentic orchestrator. "
            "Given an intent and available skills, output a JSON array of skill calls. "
            "Each call: {\"step\": N, \"skill\": \"name\", \"args\": {...}, \"reason\": \"...\"}. "
            "Return ONLY the JSON array. No prose, no markdown fences."
        )
        prompt = (
            f"AVAILABLE SKILLS:\n{tools_json}\n\n"
            + (f"CONTEXT:\n{context}\n\n" if context else "")
            + f"INTENT: {intent}\n\n"
            "Return the skill call plan as a JSON array:"
        )

        return self.query(prompt, system=system, max_tokens=max_tokens)
