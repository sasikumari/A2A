import json

class ProductKitAgent:
    """
    Role: Generate all required product artefacts (PRD, Video Script, Deck Outline, Checklist).
    """
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def generate_kit(self, canvas: dict, prototype: dict) -> dict:
        system = """You are the Product Kit Agent for NPCI.
Based on the approved Product Canvas and Prototype, generate the following assets.

Return ONLY JSON matching exactly:
{
  "prd": "Markdown formatted Product Requirements Document...",
  "video_script": "Explainer video script for the PM to present...",
  "pitch_deck": [
    {"slide": 1, "title": "...", "points": ["..."]}
  ],
  "regulatory_checklist": ["Item 1 (Pass/Fail criteria)..."]
}
"""
        payload = json.dumps({
            "canvas": canvas,
            "prototype": prototype
        })
        
        response = self.llm_client.query(payload, system=system, max_tokens=2500)
        try:
            start = response.find('{')
            end = response.rfind('}')
            return json.loads(response[start:end + 1])
        except Exception:
            return {
                "prd": "Failed to generate PRD.",
                "video_script": "",
                "pitch_deck": [],
                "regulatory_checklist": []
            }
