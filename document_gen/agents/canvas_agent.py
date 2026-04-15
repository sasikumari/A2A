import json
import time

class CanvasAgent:
    """
    Role: Generate a structured product canvas on a fixed template.
    Template fields:
      - Problem statement, Target segment, User journey,
        Market context, Regulatory considerations, Success metrics,
        Competitive landscape
    """
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def generate_canvas(self, prompt: str, context_notes: str = "") -> dict:
        system = """You are the Product Canvas Agent for NPCI.
Generate a structured JSON product canvas based on the approved PM prompt.

Return ONLY JSON matching exactly:
{
  "problem_statement": "...",
  "target_segment": "...",
  "user_journey": ["Step 1", "Step 2"],
  "market_context": "...",
  "regulatory_considerations": "...",
  "success_metrics": ["Metric 1"],
  "competitive_landscape": "..."
}
"""
        full_prompt = f"Context: {context_notes}\n\nPM Proposal: {prompt}"
        response = self.llm_client.query(full_prompt, system=system, max_tokens=1500)
        
        try:
            start = response.find('{')
            end = response.rfind('}')
            return json.loads(response[start:end + 1])
        except Exception:
            return {
                "error": "Failed to generate structured canvas",
                "raw_response": response
            }
