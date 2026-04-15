"""
ReasoningAgent — skill-based intent analysis with PM Clarification Loop and RAG.
"""

from __future__ import annotations
import json
import re
import uuid
import time
from .skills import SkillRegistry
from .skills.code_skills import AnalyzeImpactSkill, SearchCodebaseSkill
from .skills.file_skills import ListFilesSkill
from .skills.spec_skills import GenerateCanonicalSpecSkill
from .skill_planner import SkillPlanner
import sys
import os

from llm_config import auth_headers, chat_completions_url, load_project_env, model_name

load_project_env()

# Append paths temporarily if needed to import infrastructure
try:
    from infrastructure.doc_store import DocumentStore
except ImportError:
    # Handle if run differently
    DocumentStore = None

DEFAULT_FILE_MAP = {
    "switch": ["switch/upi_switch.py"],
    "payer_psp": ["psps/payer_psp.py", "psps/payer_psp_handler.py"],
    "payee_psp": ["psps/payee_psp.py", "psps/payee_psp_handler.py"],
    "remitter_bank": ["banks/remitter_bank.py", "banks/remitter_bank_handler.py"],
    "beneficiary_bank": ["banks/beneficiary_bank.py", "banks/beneficiary_bank_handler.py"],
    "xml_schema": ["api/schemas/upi_pay_request.xsd"],
}

class ReasoningAgent:
    def __init__(self, llm_client):
        """
        Initialize the ReasoningAgent with an LLM client, a RAG-based DocumentStore, 
        and a local SkillRegistry.
        """
        self.llm_client = llm_client
        # Connect to Qdrant-backed DocumentStore for regulatory RAG
        self.doc_store = DocumentStore(use_memory=False) if DocumentStore else None

        # Register core analysis and generation skills
        self.registry = SkillRegistry()
        self.registry.register(AnalyzeImpactSkill(llm_client))
        self.registry.register(SearchCodebaseSkill())
        self.registry.register(ListFilesSkill())
        self.registry.register(GenerateCanonicalSpecSkill(llm_client))

        # The SkillPlanner decomposes user requirements into specific, tool-driven tasks
        self.planner = SkillPlanner(llm_client, self.registry)

    def clarify_prompt(self, prompt: str, conversation_history: list = None) -> dict:
        """
        Phase 1: PM Clarification Loop
        -----------------------------
        1. Queries the DocStore (RAG) for relevant NPCI circulars.
        2. Engages in a multi-turn dialogue with the PM to refine the intent.
        3. Returns a JSON payload indicating whether clarification is needed or 
           if the agent is confident enough to proceed to Canvas generation.
        """
        conversation_history = conversation_history or []
        is_first_turn = len([m for m in conversation_history if m.get('role') == 'user']) == 0

        rag_context = ""
        rag_score = 0
        if self.doc_store:
            results = self.doc_store.query(prompt, threshold=0.85)
            if results:
                rag_context = "\n".join([r['text'] for r in results])
                rag_score = sum(r['score'] for r in results) / len(results)

        system = f"""You are the NPCI Agentic Architect — a senior product advisor specialized in UPI and NPCI payment ecosystem.

Your job: Analyze the PM's UPI feature request and ask 2-3 targeted clarifying questions so the Product Canvas can be built accurately.

The 10-section NPCI Product Canvas needs:
1. Feature — clear layman explanation
2. Need — differentiation, UX delta, cannibalization risk
3. Market view — merchant/bank/PSP readiness, regulatory view
4. Scalability — demand/supply anchors, impact numbers
5. Validation — MVP plan, success metrics
6. Operating KPIs — grievance mechanism, Day 0 automation
7. Product Comms — demo, FAQs, operating circular
8. Pricing — revenue model
9. Risks — fraud, infosec, second-order effects
10. Compliance — specific NPCI OCs, RBI Master Directions

RAG CONTEXT: {rag_context if rag_context else 'No exact regulatory matches. Apply general UPI/RBI bounds.'}
RAG Confidence: {rag_score:.2f}

IMPORTANT: {"This is the FIRST message. You MUST ask 2-3 clarifying questions regardless of how detailed the prompt is. Always ask." if is_first_turn else "The user has already responded. Review their answers and ask follow-up questions if needed, or confirm you have enough context."}

Return ONLY valid JSON:
{{
  "needs_clarification": true/false,
  "clarification_questions": ["Question 1", "Question 2", "Question 3"],
  "message_to_pm": "Your friendly analysis message to the PM.",
  "rag_confidence": {rag_score:.2f}
}}"""

        # Build messages with full conversation history for multi-turn
        messages = [{"role": "system", "content": system}]
        messages.append({"role": "user", "content": f"Feature Request: {prompt}"})

        # Inject conversation history
        for turn in conversation_history:
            role = turn.get('role', 'user')
            content = turn.get('content', '')
            if content:
                messages.append({"role": role, "content": content})

        # Direct LLM call with full message list
        import requests as _req
        import os as _os
        api_url = getattr(self.llm_client, "api_url", None) or chat_completions_url(default="http://183.82.7.228:9532/v1/chat/completions")
        model = getattr(self.llm_client, "model", None) or model_name(default="/model")

        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 1024,
            }
            resp = _req.post(
                api_url,
                json=payload,
                headers=getattr(self.llm_client, "headers", auth_headers()),
                timeout=60,
            )
            resp.raise_for_status()
            response = resp.json()["choices"][0]["message"]["content"]
            import re as _re
            response = _re.sub(r"<think>.*?</think>", "", response, flags=_re.DOTALL).strip()
        except Exception as e:
            print(f"[ReasoningAgent] LLM call failed: {e}")
            response = ""

        try:
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                result = json.loads(response[start:end + 1])
                # Force questions on first turn if LLM forgot
                if is_first_turn and not result.get('clarification_questions'):
                    result['clarification_questions'] = [
                        "What are the transaction limits (per-transaction and daily cap)?",
                        "Who are the primary ecosystem participants — which banks, PSPs, or merchant segments?",
                        "What specific fraud guardrails or NPCI circulars must this feature comply with?"
                    ]
                    result['needs_clarification'] = True
                return result
        except Exception:
            pass

        # Fallback with domain questions
        return {
            "needs_clarification": True,
            "clarification_questions": [
                "What are the transaction limits (per-transaction and daily cap)?",
                "Who are the primary ecosystem participants — banks, PSPs, merchant segments?",
                "What specific fraud controls or NPCI circulars must this comply with?"
            ],
            "rag_confidence": rag_score,
            "message_to_pm": "I've reviewed your feature brief. A few details will help me build a precise Product Canvas."
        }


    def analyze_prompt(self, prompt: str) -> dict:
        """
        Phase 2 Transition: Analyze a PM/OC request and return a structured change plan (TSD/Manifest gen).
        Maintains backward compatibility with original pipeline.
        """
        print(f"[ReasoningAgent] Analyzing prompt via skills: {prompt[:80]}")

        impact_skill = self.registry.get("analyze_impact")
        impact_result = impact_skill.execute(
            request=prompt,
            file_map=DEFAULT_FILE_MAP,
        )

        if not impact_result.success:
            return self._fallback_plan(prompt)

        plan = impact_result.output
        if not isinstance(plan, dict):
            return self._fallback_plan(prompt)

        feature_name = plan.get("description", prompt[:40])
        spec_skill = self.registry.get("generate_canonical_spec")
        spec_result = spec_skill.execute(feature_name=feature_name, prompt=prompt)
        
        canonical_note = spec_result.output if spec_result.success else "Canonical Note generation failed."

        files_to_change = plan.get("files_to_change", [])
        change_plan = plan.get("change_plan") or plan.get("plan", [])
        version = plan.get("version", "1.x")
        description = plan.get("description", prompt[:80])
        verification_payload = plan.get("verification_payload", "")

        return {
            "version": version,
            "description": description,
            "files_to_change": files_to_change,
            "plan": change_plan if isinstance(change_plan, list) else [str(change_plan)],
            "impact_analysis": {
                "technical_components": files_to_change,
                "business_value": plan.get("risk_reason", ""),
                "risk_assessment": f"{plan.get('risk_level', 'Medium')} — {plan.get('risk_reason', '')}",
                "compliance_check": plan.get("compliance_notes", "Aligns with RBI/NPCI guidelines."),
                "canonical_product_note": canonical_note,
            },
            "verification_payload": verification_payload,
            "change_manifest": plan.get("change_manifest", {}),
            "skill_plan_available": True,
            "raw_analysis": plan,
        }

    def _fallback_plan(self, prompt: str) -> dict:
        print("[ReasoningAgent] Using monolithic fallback prompt.")
        system_prompt = """You are a Senior NPCI Senior Product Steering Committee Member and Lead Technical Architect.
Analyze the user's request for a TITANIUM specification change and return a JSON plan.

FILE MAP:
• Amount/P2P limits → switch/upi_switch.py
• Auth/PIN → psps/payer_psp.py + psps/payer_psp_handler.py
• Payee credit → psps/payee_psp.py + psps/payee_psp_handler.py
• Debit/balance → banks/remitter_bank.py + banks/remitter_bank_handler.py
• Beneficiary credit → banks/beneficiary_bank.py
• XML structure → api/schemas/upi_pay_request.xsd

Return ONLY valid JSON:
{
  "version": "1.x",
  "description": "Formal NPCI Header",
  "impact_analysis": {
    "technical_components": ["files to change"],
    "business_value": "Formal NPCI Business Case Summary",
    "risk_assessment": "High/Medium/Low — Detailed risk reasons",
    "compliance_check": "11-Point Canonical alignment check",
    "canonical_product_note": "A summary of the 11 sections"
  },
  "plan": ["1. Change in file X: [Specific Technical Detail]", "2. Change in file Y: [Specific Technical Detail]"],
  "verification_payload": "<?xml ...valid ReqPay XML...>"
}"""
        full_prompt = f"{system_prompt}\n\nUser Request: {prompt}"
        response = self.llm_client.query(full_prompt)
        response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()

        try:
            start = response.find('{')
            end = response.rfind('}')
            return json.loads(response[start:end + 1])
        except Exception as e:
            return {
                "version": "1.x",
                "description": "Failed to parse plan",
                "impact_analysis": {"technical_components": ["Unknown"]},
                "plan": ["Manual intervention required."],
            }
