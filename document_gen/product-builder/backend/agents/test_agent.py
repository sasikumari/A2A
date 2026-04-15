"""
Test Agent — generates UPI XML test cases from a natural language prompt.
"""
from .llm import chat
import re

SYSTEM = """You are the NPCI Lead Quality Engineer and Test Orchestrator. 
Your goal is to distribute feature-specific unit tests and integration scenarios to all participating agents (Bank, PSP, Switch).

A2A VERIFICATION FLOW:
1. DISTRIBUTE: Send relevant unit tests to the ICICI Bank Agent and PhonePe Agent.
2. EXECUTE: The agents execute the tests in their sandboxes.
3. ACKNOWLEDGE: The agents post a success token or failure detail back to the NPCI Orchestrator.

Ensure every test covers both happy paths and edge cases (e.g. invalid signing, balance insufficient).
Return ONLY the XML content for the ReqPay/RespPay. No markdown, no prose.
"""

class TestAgent:
    def generate_xml(self, prompt, canvas):
        if not isinstance(canvas, dict):
            canvas = {}
        feature_name = canvas.get("featureName", "UPI Feature")
        sections = canvas.get("sections", [])
        feature_desc = ""
        if isinstance(sections, list) and len(sections) > 0:
            feature_desc = sections[0].get("content", "")
        
        user_prompt = f"Generate a valid UPI XML (ReqPay) for the following test scenario.\n\nFEATURE: {feature_name}\nDESCRIPTION: {feature_desc}\n\nSCENARIO PROMPT: {prompt}\n\nReturn ONLY the raw XML. No markdown code blocks, just the XML content string."
        
        thinking, answer = chat(SYSTEM, user_prompt, temperature=0.3, max_tokens=2000)
        
        # Clean up the output in case the LLM included markdown blocks
        xml = self._clean_xml(answer)
        return xml

    def _clean_xml(self, text):
        # Remove markdown code blocks if present
        text = re.sub(r"```xml", "", text)
        text = re.sub(r"```", "", text)
        return text.strip()
