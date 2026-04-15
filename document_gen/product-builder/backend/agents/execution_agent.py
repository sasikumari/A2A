"""
Execution Agent — generates a development execution plan from an approved canvas using the Skill-Directed Orchestrator.
"""
from .llm import chat, extract_json

SYSTEM = """You are a senior software architect and tech lead specializing in UPI payment systems at NPCI.
You design production-ready implementation plans for UPI features, covering backend APIs, services, 
database schemas, UI components, jobs, and tests.
Every implementation item must be specific to the actual feature being built — no generic placeholders.
"""

class ExecutionAgent:
    def generate(self, canvas: dict, feedback: str = None, messages: list = None) -> dict:
        """Generate the technical orchestration plan through a Skill-Directed handshake."""
        from upi_hackathon_titans.agents.skill_planner import SkillPlanner
        from upi_hackathon_titans.agents.skills.registry import get_universal_registry
        
        # Wrapper to match Skill interface
        class SkillLLM:
            def query(self, prompt: str):
                _, ans = chat("", prompt)
                return ans
        
        llm_client = SkillLLM()
        registry = get_universal_registry(llm_client)
        planner = SkillPlanner(llm_client, registry)
        
        feature = canvas.get("featureName", "UPI Feature")
        
        # 1. PLAN the technical orchestration
        print(f"[ExecutionAgent] Orchestrating Skill Plan for {feature}...")
        intent = f"Generate technical items and perform A2A Sync for {feature}. Context: {feedback or 'Initial setup'}"
        plan = planner.plan(intent, context={"canvas": canvas})
        
        # 2. EXECUTE the A2A Sync Handshake Skill
        sync_skill = registry.get("sync_intent")
        sync_result = sync_skill.execute(
            feature_name=feature,
            tsd="Titan-III Technical Specification",
            participants=["ICICI Bank Agent", "PhonePe PSP Agent", "NPCI Switch Agent"]
        )
        
        # 3. GENERATE final items list (Powering the UI)
        user_prompt = f"""
Current Product: {feature}
A2A HANDSHAKE STATUS: {sync_result.output}
FEEDBACK: {feedback or "None"}

TASK: Return a JSON technical plan (14 items). 
Item 3 MUST be the 'Bank Participant Handshake' reflecting the Status above.

JSON Format:
{{
  "message": "Orchestration plan prepared for {feature}.",
  "items": [...]
}}
"""
        _, answer = chat(SYSTEM, user_prompt, temperature=0.3)
        data = extract_json(answer)
        
        fallback_items = self._fallback(canvas)
        brd_item = next(i for i in fallback_items if i["id"] == "brd")
        tsd_item = next(i for i in fallback_items if i["id"] == "tsd")
        
        if data and "items" in data:
            # Ensure "brd" and "tsd" exist for the frontend tabs
            if not any(i.get("id") == "brd" for i in data["items"]):
                data["items"].insert(0, brd_item)
            if not any(i.get("id") == "tsd" for i in data["items"]):
                data["items"].insert(1, tsd_item)
            return data

        return {
            "message": f"Orchestrated plan for {feature}.",
            "items": fallback_items
        }

    def _fallback(self, canvas: dict) -> list:
        feature = canvas.get("featureName", "UPI Feature")
        sections = {s["id"]: s for s in canvas.get("sections", [])}
        def sec(id_: int) -> str: return sections.get(id_, {}).get("content", "")
        
        slug = feature.lower().replace(" ", "_")[:20]
        return [
            {
                "id": "brd", 
                "file": "Business Requirements Document", 
                "change": f"# BRD: {feature}\n{sec(1)}", 
                "type": "add", 
                "status": "pending"
            },
            {
                "id": "tsd", 
                "file": "Technical Specification Document", 
                "change": f"# TSD: {feature}\n{sec(10)}", 
                "type": "add", 
                "status": "pending"
            },
            {
                "id": "a2a",
                "file": "Bank Participant Handshake (ICICI Bank)",
                "change": f"Handshake established with ICICI Bank node for {feature} intent sharing.",
                "type": "add",
                "status": "pending"
            },
            {"id": "e1", "file": f"src/api/upi/{slug}/create.ts", "change": f"Endpoint for {feature}", "type": "add", "status": "pending"},
            {"id": "e2", "file": "src/services/ledger.ts", "change": "Sync logic", "type": "modify", "status": "pending"},
            {"id": "e3", "file": "tests/integration.ts", "change": "Tests", "type": "add", "status": "pending"}
        ]
