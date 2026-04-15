import json

class PrototypeAgent:
    """
    Role: Create clickable UI flow and interaction model from the canvas.
    Output: Low-fidelity wireframes + user flow diagrams
    """
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def generate_flow_diagram(self, canvas: dict) -> dict:
        system = """You are the Prototype Agent for NPCI.
Based on the approved Product Canvas, generate a mermaid.js user flow diagram for the application.

Return ONLY JSON:
{
  "mermaid": "graph TD\\nA --> B...",
  "mockup_screens": [
    {"screen_name": "Home", "elements": ["Button A"]}
  ]
}
"""
        response = self.llm_client.query(json.dumps(canvas), system=system, max_tokens=1500)
        try:
            start = response.find('{')
            end = response.rfind('}')
            return json.loads(response[start:end + 1])
        except Exception:
            return {
                "mermaid": "graph TD\nError --> ParsingFailed",
                "mockup_screens": []
            }
