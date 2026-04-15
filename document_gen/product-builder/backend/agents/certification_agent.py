"""
Certification Agent — automates the NPCI/RBI certification board review using the Skill-Directed Orchestrator.
Gates deployment based on participant readiness and ecosystem test results.
"""
from datetime import datetime
from .llm import chat, extract_json

SYSTEM = """You are the NPCI Certification Board and Regulatory Compliance Auditor.
Your goal is to evaluate if a new UPI feature is ready for MAINNET deployment using the Titan-III Framework.
"""

class CertificationAgent:
    def certify(self, feature_name: str, canvas: dict, change_manifest: dict, test_results: list) -> dict:
        """
        Run the certification workflow through the Skill-Directed Orchestrator.
        """
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
        
        feature = feature_name or canvas.get("featureName", "UPI Feature")
        
        # 1. PLAN the certification audit
        print(f"[CertificationAgent] Orchestrating Certification Plan for {feature}...")
        intent = f"Perform a 3-pillar (Technical, Security, Compliance) audit for {feature}. Evaluate test results and technical synchronization."
        plan = planner.plan(intent, context={"canvas": canvas, "test_results": test_results})
        
        # 2. EXECUTE the Certification Pillar Skill (Evaluating the technical pillar)
        cert_skill = registry.get("certify_pillar")
        test_summary = "\n".join([f"- {r.get('agent')}: {r.get('status')}" for r in test_results])
        
        result = cert_skill.execute(
            feature_name=feature,
            tsd="Titan-III Technical Specification Document",
            test_results=test_summary,
            pillar="TECHNICAL"
        )
        
        # 3. GENERATE final certification report
        user_prompt = f"""
NPCI CERTIFICATION REQUEST for: {feature}
TECHNICAL AUDIT RESULT: {result.output}

TASK: Generate a final JSON certification report.
Return ONLY JSON:
{{
  "feature": "{feature}",
  "decision": "Approved | Rejected | Needs Improvement",
  "confidence_score": 0.0-1.0,
  "certificate_id": "NPCI-CERT-2026-XXXX",
  "audit_trail": [
     "Infrastructure check: ...",
     "Regulation check: ...",
     "Security check: ..."
  ],
  "concerns": ["..."],
  "next_steps": ["..."]
}}
"""
        thinking, answer = chat(SYSTEM, user_prompt, temperature=0.2)
        report = extract_json(answer)

        if not report:
            report = {
                "feature": feature,
                "decision": "Rejected",
                "confidence_score": 0.0,
                "certificate_id": "REJECTED-FAIL-PARSE",
                "audit_trail": ["Agentic skill-based report generation failed to parse."],
                "concerns": ["LLM output was not valid JSON."],
                "next_steps": ["Retry certification with the Skill Orchestrator."]
            }

        return {
            "report": report,
            "thinking": thinking,
            "timestamp": datetime.now().isoformat()
        }

    def _summarize_canvas(self, canvas: dict) -> str:
        lines = [f"Feature: {canvas.get('featureName', 'UPI Feature')}"]
        for sec in canvas.get("sections", []):
            if sec['title'] in ["Compliance", "Potential Risks", "Validation"]:
                lines.append(f"- {sec['title']}: {sec['content'][:200]}...")
        return "\n".join(lines)
