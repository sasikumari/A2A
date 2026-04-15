"""
Clarification Skills — Thought Alignment and Vision Proposal.
"""

from . import Skill, SkillResult

class ClarifyIntentSkill(Skill):
    name = "clarify_intent"
    description = (
        "Reconcile a user's prompt with NPCI Titanium standards and past product context. "
        "Generates a 'Vision Proposal' and 2-3 targeted clarification questions for the Product Manager."
    )
    parameters = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
            "context": {"type": "string", "description": "Context of previous products, BRDs, or RBI guidelines."},
        },
        "required": ["prompt"],
    }

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def execute(self, prompt: str, context: str = "", **_) -> SkillResult:
        system = """You are a Senior NPCI Agentic Architect. 
Your goal is to deeply understand the PM's vision for a new UPI feature and identify ambiguities.

STRICT RESPONSE FORMAT:
Return a JSON object:
{
  "vision_proposal": "A 2-sentence summary of the understood product vision.",
  "clarification_questions": [
    "Question 1: Specific architectural or business logic ambiguity.",
    "Question 2: Specific NPCI/RBI compliance ambiguity.",
    "Question 3: (Optional) User experience edge case."
  ],
  "context_relevancy": "How this relates to past products (e.g. UPI Lite, AutoPay)."
}
"""
        user_input = f"PM Prompt: {prompt}\n\nHistorical/Regulatory Context: {context}"
        response = self.llm_client.query(user_input, system=system)
        
        # SkillResult handles the structured output
        return SkillResult(success=True, output=response)
