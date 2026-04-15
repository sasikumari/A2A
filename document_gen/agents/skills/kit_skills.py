"""
Universal Product Kit Skills — Grouping 7 professional documents.
"""

from . import Skill, SkillResult

class GenerateProductKitSkill(Skill):
    name = "generate_product_kit"
    description = (
        "Generate a full professional suite (7 items) for a UPI product launch. "
        "Includes: Product Note, Circular, FAQs, PPT Deck (Template), Video Script, RBI Compliance Guidelines, and Standardized UAT Cases."
    )
    parameters = {
        "type": "object",
        "properties": {
            "feature_name": {"type": "string"},
            "canvas": {"type": "object", "description": "The approved 10-section canvas JSON."},
        },
        "required": ["feature_name", "canvas"],
    }

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def execute(self, feature_name: str, canvas: dict, **_) -> SkillResult:
        system = """You are a Lead NPCI Product Strategist. 
Generate a professional Launch Kit for: {feature_name}.

OUTPUT SECTIONS:
1. PRODUCT_NOTE: One-page executive summary.
2. CIRCULAR: Official NPCI notification to all banks.
3. FAQ: Top 10 public questions.
4. DECK_STRUCTURE: 5-slide PPT outline (Title, Problem, UPI-AI solution, Flow, Adoption).
5. VIDEO_SCRIPT: 60-second marketing narration script.
6. RBI_GUIDELINES: List of 5 critical regulatory compliance pillars.
7. TEST_STRATEGY: Formal ecosystem-wide UAT checklist.
"""
        user_input = f"Canvas Data: {canvas}"
        response = self.llm_client.query(user_input, system=system)
        
        return SkillResult(success=True, output=response)
