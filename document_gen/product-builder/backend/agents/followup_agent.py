"""
Followup Agent — handles follow-up chat messages and updates canvas sections.
"""
from .llm import chat, extract_json

SYSTEM = """You are a senior NPCI product strategist and UPI expert with deep knowledge of RBI regulations.
You are assisting a PM reviewing a Product Build Canvas for a UPI feature.

Your job:
- Answer follow-up questions with expert, specific, actionable insight
- When asked to update/improve a section: generate production-quality content (min 400 chars)
- Reference specific RBI notifications (12032 §4, 1888, OC 228), real ecosystem players, real numbers
- Never give generic advice — always tie your response specifically to the feature being built
- Return only valid JSON
"""


class FollowupAgent:
    def respond(self, user_text: str, canvas: dict) -> dict:
        """
        Returns:
          {
            "text": str,           # assistant response text
            "updated_section": dict | None,  # updated canvas section if any
            "thinking": str
          }
        """
        feature_name = canvas.get("featureName", "UPI Feature")
        sections_summary = "\n".join(
            f"Section {s['id']} ({s['title']}): {s['content'][:150]}..."
            for s in canvas.get("sections", [])[:10]
        )

        user_prompt = f"""
Feature: {feature_name}

Current Canvas Sections (summary):
{sections_summary}

User's follow-up question/request: "{user_text}"

Instructions:
1. Provide a helpful, expert response (2-4 sentences).
2. If the user asks to update or improve a specific section, also return the updated section JSON.
3. Return JSON in this format:
{{
  "response_text": "Your expert response here",
  "update_section_id": <number or null>,
  "updated_content": "New content for that section, or null if no update"
}}
"""
        thinking, answer = chat(SYSTEM, user_prompt, temperature=0.4, max_tokens=2048)
        parsed = extract_json(answer)

        text = parsed.get("response_text") or self._smart_fallback(user_text, feature_name)
        updated_section = None
        sec_id = parsed.get("update_section_id")
        new_content = parsed.get("updated_content")

        if sec_id and new_content:
            for sec in canvas.get("sections", []):
                if sec.get("id") == int(sec_id):
                    updated_section = {**sec, "content": new_content}
                    break

        return {
            "text": text,
            "updated_section": updated_section,
            "thinking": thinking,
        }

    def _smart_fallback(self, user_text: str, feature_name: str) -> str:
        lower = user_text.lower()
        if any(k in lower for k in ["pric", "revenue", "monetis"]):
            return f"For **{feature_name}**, a phased pricing model works best: Year 1 volume-led (zero MDR for CASA), Year 2 tiered for AI-triggered transactions, Year 3 full analytics API licensing. RBI MDR exemption clarity is an open item."
        if any(k in lower for k in ["risk", "fraud", "security"]):
            return f"Key risks for **{feature_name}**: misuse via rogue merchants, PII exposure, and core banking latency. Mitigations include DSC validation, TLS 1.3+, human-in-loop for AI payments >₹500, and real-time fraud scoring per RBI 12032."
        if any(k in lower for k in ["complian", "rbi", "regul"]):
            return f"**{feature_name}** must comply with RBI 12032 (MFA, TLS 1.3+, audit trails), Notification 1888 (KYC, grievance T+1), NPCI OC 228 (block limits, merchant eligibility), and DPDP Act 2023 (consent, data residency)."
        if any(k in lower for k in ["market", "scale", "merchant"]):
            return f"Scale anchors for **{feature_name}**: demand from quick commerce (Zomato, Blinkit — 40%), mobility (Uber, Ola — 25%), subscriptions (20%), B2B/MSME (15%). Supply via PhonePe (48% share), GPay (37%), and top CASA issuers (SBI, HDFC)."
        return f"Good point on **{feature_name}**. The canvas sections most relevant here are **Need** (#2) and **Product Operating** (#6). Would you like me to update a specific section with more detail?"
