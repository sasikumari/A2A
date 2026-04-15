"""
Clarify Agent: Evaluates initial feature prompts for strategic alignment and completeness.
Decides if the AI has sufficient context for the 10-section NPCI Product Canvas
and engages the user in a directed dialogue to resolve essential ambiguities.
"""
import re
import json
from .llm import chat
from utils.context_loader import get_relevant_previous_products

SYSTEM = """You are a senior NPCI product manager reviewing a new UPI feature proposal.

Your job: Evaluate whether the feature description has enough information to build a 
comprehensive 10-section Product Build Canvas (like an internal NPCI product brief).

The 10 sections need:
1. Feature — clear user-facing explanation (layman language)
2. Need — why build this, differentiation (incremental vs exponential), UX delta, cannibalization
3. Market view — merchant/bank/PSP ecosystem response, effort required, regulatory view
4. Scalability — demand anchors (target merchants), supply anchors (banks/PSPs), impact numbers
5. Validation — MVP plan, what data/insights it generates
6. Product Operating — KPIs, grievance mechanism, Day 0 automation
7. Product Comms — demo, FAQs, circular, product doc
8. Pricing — revenue model, market willingness to pay
9. Potential risks — fraud, infosec, second-order effects
10. Compliance — specific OCs and regulatory requirements

Return ONLY valid JSON. No markdown.
"""

def evaluate(prompt: str, feature_name: str) -> dict:
    """
    Evaluates prompt completeness for the 10-section NPCI Product Canvas using LLM.
    """
    from .llm import chat

    user_msg = f"""Feature Name: {feature_name}
Feature Prompt: {prompt}

Evaluate whether the above feature prompt has sufficient context to populate all 10 sections of the NPCI Product Build Canvas.

Return a JSON object with these exact keys:
- "confident": boolean (true if the prompt is complete enough to proceed directly to canvas generation)
- "vision_proposal": string (a one-line vision statement for this feature)
- "questions": array of objects, each with: "id" (string), "question" (string), "reason" (string), "placeholder" (string)
- "missing_areas": array of strings naming sections that need more detail
- "summary": string (brief evaluation summary)

Only ask questions if truly necessary — if the prompt is sufficiently detailed (>80 words with clear user, usecase, and ecosystem context), return confident=true with empty questions array.

Return ONLY valid JSON, no markdown."""

    print(f"[ClarifyAgent] Evaluating prompt for '{feature_name}' ({len(prompt)} chars)...")
    try:
        _, answer = chat(SYSTEM, user_msg)
        match = re.search(r'\{[\s\S]*\}', answer)
        if match:
            res_json = json.loads(match.group())
            res_json.setdefault("confident", True)
            res_json.setdefault("questions", [])
            res_json.setdefault("missing_areas", [])
            res_json.setdefault("summary", f"Evaluation complete for {feature_name}.")
            res_json.setdefault("vision_proposal", f"Titan-Grade Vision for {feature_name}")
            print(f"[ClarifyAgent] Result: confident={res_json.get('confident')}, questions={len(res_json.get('questions', []))}")
            return res_json
    except Exception as exc:
        print(f"[ClarifyAgent] LLM evaluation error: {exc}")

    # Fast fallback: skip clarification if prompt is sufficiently detailed
    is_confident = len(prompt.strip()) > 80
    return {
        "confident": is_confident,
        "vision_proposal": f"Titan-Grade Vision for {feature_name}",
        "questions": [] if is_confident else [{
            "id": "q1",
            "question": "Who are the primary ecosystem participants for this feature?",
            "reason": "Market view identification",
            "placeholder": "e.g. Banks and PSPs"
        }],
        "missing_areas": [] if is_confident else ["Market view"],
        "summary": "Direct evaluation based on prompt length.",
    }
