"""
Canvas Agent — generates a 10-section Product Build Canvas from a prompt.
Runs research first to find relevant regulations, then builds the canvas.
"""
import re
from .llm import chat, extract_json
from .fallbacks import FALLBACK_CANVAS
from .research_agent import research_feature, build_thinking_steps_from_research
from utils.context_loader import get_relevant_previous_products

SYSTEM = """You are a senior NPCI product strategist and UPI expert writing an internal product canvas.

Your job: Write a 10-section Product Build Canvas exactly as NPCI internal documents are structured.
The canvas is used by the NPCI review committee before approving any new UPI feature.

MANDATORY rules:
1. Return ONLY valid JSON — no markdown, no text outside JSON.
2. Every section must be DEEPLY specific to the feature — real numbers, real ecosystem players, real RBI section references.
3. NEVER use placeholder text like "[insert]" or "e.g." — all content is final-quality.
4. Name real PSPs (PhonePe 48%, Google Pay 37%, Paytm 8%), real banks (SBI, HDFC, ICICI, Axis), real merchants.
5. Reference specific RBI notifications (§4 of RBI 12032, OC 228, etc).
6. Content must read exactly like an NPCI internal product document — authoritative, specific, actionable.

FORMATTING RULES FOR SECTION CONTENT (critical — renderer depends on this):
- Use ALL-CAPS lines for major subsection headings (e.g. "WHY SHOULD WE DO THIS?", "DIFFERENTIATION")
- Use bullet points with "• " prefix for list items
- Use numbered items "1. ", "2. ", "3. " for ordered lists (KPIs, steps, etc.)
- Use "Key: Value" format for metrics, targets, and named items (e.g. "PhonePe: High effort — SDK update required")
- Bold key numbers/terms with **text** (e.g. "**₹2,400 Cr** annual opportunity")
- Separate major subsections with a blank line
- Do NOT write long unbroken paragraphs — use structure throughout
- Every data point should stand on its own line for readability
"""

# Exact 10-section format matching NPCI Canvas_ProductBuild document
CANVAS_SCHEMA = """{
  "featureName": "string",
  "buildTitle": "Build framework for [Feature Name]",
  "overallStatus": "ongoing",
  "approved": false,
  "rbiGuidelines": "string — specific RBI notifications (number, section) applicable to this feature",
  "ecosystemChallenges": "string — specific PSP/bank/merchant integration challenges with timelines",
  "sections": [
    {
      "id": 1,
      "title": "Feature",
      "status": "on-track",
      "approved": false,
      "content": "LAYMAN EXPLANATION\\n[1-2 plain English sentences]\\n\\nUSER JOURNEY\\n1. [Step 1 — user action]\\n2. [Step 2 — what happens]\\n3. [Step 3 — confirmation]\\n4. [Step 4 — outcome]\\n\\nKEY BENEFITS\\n• [Benefit 1 with specific number]\\n• [Benefit 2 with specific number]\\n• [Benefit 3 with specific number]"
    },
    {
      "id": 2,
      "title": "Need",
      "status": "on-track",
      "approved": false,
      "content": "WHY SHOULD WE DO THIS?\\n• [Gap 1 in current UPI ecosystem with specific stat]\\n• [Gap 2 — user pain point with data]\\n• [Gap 3 — market opportunity with ₹ figure]\\n\\nDIFFERENTIATION\\nType: [Incremental / Exponential]\\n• vs UPI Autopay: [how this is different]\\n• vs UPI Lite: [how this is different]\\n• Unique capability: [what no other payment product does]\\n\\nDELTA IN USER EXPERIENCE\\n• Before: [specific friction — e.g. 5 steps, 28 seconds, PIN required]\\n• After: [specific improvement — e.g. 1 tap, 8 seconds, biometric]\\n• Conversion lift: [expected improvement %]\\n\\nWHAT WILL IT CANNIBALIZE?\\n• [Payment method 1]: [complement or replace — why]\\n• [Payment method 2]: [complement or replace — why]\\n\\nWHAT IF WE DON'T BUILD THIS?\\n• [Risk 1 — market share / competitor]\\n• [Risk 2 — opportunity cost in ₹]\\n• [Risk 3 — strategic risk]"
    },
    {
      "id": 3,
      "title": "Market View",
      "status": "open",
      "approved": false,
      "content": "ECOSYSTEM ANTICIPATED RESPONSE\\nMerchants: [positive/neutral/concern + specific categories]\\nPhonePe (48%): [stance + specific effort required]\\nGoogle Pay (37%): [stance + specific effort required]\\nPaytm (8%): [stance + specific effort required]\\nIssuer Banks: [CBS changes + CASA vs Credit impact]\\n\\nECOSYSTEM COSTS\\nUPI Apps: [effort level] — [specific SDK/API changes]\\nIssuer Banks: [effort level] — [CBS modules affected]\\nMerchants: [effort level] — [integration method]\\n\\nANTICIPATED REGULATORY VIEW\\n• RBI stance: [approval type expected]\\n• Circular type: [OC / Master Direction / Notification]\\n• Engagement status: [pending / in-progress / approved]\\n• Key concern: [primary regulatory consideration]"
    },
    {
      "id": 4,
      "title": "Scalability",
      "status": "open",
      "approved": false,
      "content": "MARKET ANCHORS TO MAKE IT BIG\\n\\nDEMAND SIDE\\nMerchants: [Zomato, Swiggy, Uber — specific category names]\\nUsers: [target segment + estimated eligible count]\\nUse cases: [top 3 high-frequency scenarios]\\n\\nSUPPLY SIDE\\nPhonePe: [enablement plan + timeline]\\nGoogle Pay: [enablement plan + timeline]\\nPaytm: [enablement plan + timeline]\\nSBI: [issuer readiness + account types]\\nHDFC: [issuer readiness + account types]\\nICICI: [issuer readiness + account types]\\n\\nIMPACT OPPORTUNITY\\nTransaction volume: [target txns/month at steady state]\\nUser reach: [estimated addressable users]\\nCheckout improvement: [time reduction or conversion lift]\\nRevenue potential: **₹[amount]** annually"
    },
    {
      "id": 5,
      "title": "Validation",
      "status": "ongoing",
      "approved": false,
      "content": "CREATING AND OPERATING MVP\\nPilot partners: [3-4 specific merchant/PSP names]\\nScope: [specific features in MVP vs full build]\\nLaunch timeline: [Q/Year]\\nSuccess criteria:\\n• [Metric 1 with target value]\\n• [Metric 2 with target value]\\n• [Metric 3 with target value]\\n\\nDATA INSIGHTS GENERATED\\n• Conversion rate: [what we learn about payment conversion]\\n• User behaviour: [patterns around timing, device, account preference]\\n• Merchant segments: [which categories convert best]\\n• Dispute rate: [baseline measurement]\\n• Drop-off: [where users abandon]\\n\\nIMPACT ON SGF / FRM\\n• SGF: [Safeguard Fund applicability — new flow or excluded]\\n• FRM: [new fraud rules needed — specific vectors]"
    },
    {
      "id": 6,
      "title": "Product Operating",
      "status": "ongoing",
      "approved": false,
      "content": "3 SUCCESS KPIs\\n1. [KPI name]: [target value] by [date]\\n2. [KPI name]: [target value] by [date]\\n3. [KPI name]: [target value] by [date]\\n\\nGRIEVANCE REDRESSAL\\n• UDIR integration: [specific dispute categories handled]\\n• SLA: [resolution timeline]\\n• Reconciliation: [cross-party (merchant/PSP/bank) process]\\n• Escalation: [NPCI-level intervention triggers]\\n\\nDAY 0 AUTOMATION\\n• Dashboard: [key metrics monitored in real-time]\\n• Alerts: [specific thresholds for decline rate, error codes]\\n• Runbook: [first-response steps for common failure modes]\\n\\nIMPACT ON EXISTING INFRA\\nPurpose codes: [new codes required]\\nAPI changes: [specific APIs updated or new]\\nSystem load: [estimated additional TPS at peak]"
    },
    {
      "id": 7,
      "title": "Product Comms",
      "status": "open",
      "approved": false,
      "content": "DELIVERABLES\\n• Product demo: polished MVP demo video (3-5 min)\\n• Product video: ecosystem-facing explainer\\n• PM explanation video: internal technical walkthrough\\n• FAQs + LLM training: published on NPCI website, model fine-tuned on OC + specs\\n\\nCIRCULAR PLAN\\nExpected OC: [OC number range + issuance quarter]\\nRecipients: [PSPs / Banks / Merchants / All ecosystem]\\nContent: [key mandates, timelines, compliance items]\\n\\nPRODUCT DOCUMENTATION\\n• Technical specs + API reference\\n• UI/UX guidelines for PSP integration\\n• Test cases (happy path + edge cases)\\n• Certification checklist for go-live"
    },
    {
      "id": 8,
      "title": "Pricing",
      "status": "open",
      "approved": false,
      "content": "3-YEAR PRICING VIEW\\nModel: [MDR / flat fee / zero-charge + rationale]\\nYear 1: **₹[amount]** — [basis: X txns × Y fee]\\nYear 2: **₹[amount]** — [projected growth]\\nYear 3: **₹[amount]** — [steady-state revenue]\\n\\nMARKET ABILITY TO PAY\\n• Merchants: [willingness — high/medium/low + justification]\\n• PSPs: [commercial model — pass-through or absorb]\\n• Banks: [separate commercials needed for CASA vs Credit]\\n• Consumers: [zero-charge or merchant-funded — rationale]\\n\\nMARKET VIEW ON PRICING\\n• [Concern 1 from specific stakeholder]\\n• [Concern 2 from specific stakeholder]\\n• [Resolution approach]"
    },
    {
      "id": 9,
      "title": "Potential Risks",
      "status": "ongoing",
      "approved": false,
      "content": "FRAUD RISKS\\n• [Fraud vector 1]: [mechanism + specific mitigation]\\n• [Fraud vector 2]: [mechanism + specific mitigation]\\n• [Fraud vector 3]: [mechanism + specific mitigation]\\n\\nINFOSEC & DATA PRIVACY RISKS\\n• Authentication risk: [specific vulnerability + control]\\n• Data exposure: [what data is at risk + DPDP Act 2023 requirement]\\n• API security: [attack surface + mitigation]\\n\\nSECOND-ORDER EFFECTS\\n• [Ecosystem risk 1]: [distortion or competitive impact]\\n• [Ecosystem risk 2]: [concentration risk or market distortion]\\n• [Regulatory risk]: [potential backlash or rule change trigger]"
    },
    {
      "id": 10,
      "title": "Compliance",
      "status": "on-track",
      "approved": false,
      "content": "MUST-HAVE COMPLIANCES\\n[OC/RBI ref 1]: [exact mandate for this feature]\\n[OC/RBI ref 2]: [exact mandate for this feature]\\n[OC/RBI ref 3]: [exact mandate for this feature]\\n[OC/RBI ref 4]: [exact mandate for this feature]\\n\\nADHERENCE REQUIREMENTS\\n• Lifecycle notifications: [create / execute / modify / revoke / expire — all events]\\n• Block/amount limits: [specific limits per RBI/NPCI rules]\\n• UDIR integration: [dispute resolution SLA]\\n• MIS reporting: [frequency + deadline — e.g. daily by 07:00 IST]\\n• Audit trail: [retention period per RBI 12032]\\n• Merchant verification: [online-only or offline too]"
    }
  ]
}"""


class CanvasAgent:
    def generate(self, prompt: str, feature_name: str, clarification_qa: list = None) -> dict:
        """
        Generate the 10-section canvas.
        clarification_qa: list of {"question": str, "answer": str} from the clarification phase
        """
        # ── Step 1: Research relevant regulations ──────────────────────────
        research_result = research_feature(prompt, feature_name)
        found_docs = research_result.get("documents", [])

        # Build regulation context from found documents
        reg_context = "\n".join(
            f"• {d['ref']} ({d['date']}): {d['summary']}\n  Key: {'; '.join(d['key_provisions'][:3])}"
            for d in found_docs
        )

        # Load previous product context
        prev_context = get_relevant_previous_products(prompt)

        # Build clarification context
        qa_context = ""
        if clarification_qa:
            qa_context = "\n\nADDITIONAL CONTEXT FROM PM CLARIFICATIONS:\n" + "\n".join(
                f"Q: {qa['question']}\nA: {qa['answer']}"
                for qa in clarification_qa
            )

        # ── Step 2: Generate canvas with research context ──────────────────
        user_prompt = f"""Build a complete 10-section Product Build Canvas for this UPI feature.
Write exactly like an NPCI internal product document — authoritative, specific, no placeholders.

Feature Name: {feature_name}
Description: {prompt}{qa_context}

PREVIOUS PRODUCT CONTEXT (How this feature relates to existing UPI features):
{prev_context}

APPLICABLE REGULATIONS (use these exact references throughout):
{reg_context if reg_context else "Apply standard UPI regulatory framework (RBI 12032, 1888, OC 228)."}

Return ONLY valid JSON matching this exact schema — follow ALL subsection headings exactly:
{CANVAS_SCHEMA}

CRITICAL:
- Follow every subsection heading exactly (e.g. "WHY SHOULD WE DO THIS?", "DIFFERENTIATION", "DELTA IN USER EXPERIENCE", etc.)
- Reference specific regulation refs above (e.g. "{found_docs[0]['ref'] if found_docs else 'RBI 12032'}")
- Every section specific to "{feature_name}" — no generic UPI statements
- Compliance section must list the specific OC numbers found ({', '.join(d['id'] for d in found_docs[:4])})"""

        thinking, answer = chat(SYSTEM, user_prompt, temperature=0.4, max_tokens=12000)
        parsed = extract_json(answer)

        if not parsed or "sections" not in parsed or len(parsed.get("sections", [])) < 10:
            # Try to repair partial JSON or use fallback
            parsed = self._repair_or_fallback(parsed, feature_name, prompt)

        # Ensure required fields
        parsed.setdefault("featureName", feature_name)
        parsed.setdefault("buildTitle", f"Build Framework for {feature_name}")
        parsed.setdefault("overallStatus", "ongoing")
        parsed.setdefault("approved", False)
        parsed.setdefault("rbiGuidelines", self._default_rbi(feature_name))
        parsed.setdefault("ecosystemChallenges", self._default_ecosystem(feature_name))

        # Ensure all 10 sections exist
        existing_ids = {s.get("id") for s in parsed.get("sections", [])}
        fallback_sections = FALLBACK_CANVAS["sections"]
        sections = {s["id"]: s for s in parsed.get("sections", [])}
        for fb_sec in fallback_sections:
            if fb_sec["id"] not in existing_ids:
                # Customize fallback section for this feature
                sec = dict(fb_sec)
                sec["content"] = sec["content"].replace("UPI Reserve Pay Enhancement", feature_name)
                sections[sec["id"]] = sec
        parsed["sections"] = [sections[i] for i in sorted(sections.keys()) if i <= 10]

        return {
            "canvas": parsed,
            "thinking": thinking,
            "research": research_result,
        }

    def _repair_or_fallback(self, partial: dict, feature_name: str, prompt: str) -> dict:
        """Use fallback canvas and inject feature name."""
        fb = dict(FALLBACK_CANVAS)
        fb["featureName"] = feature_name
        fb["buildTitle"] = f"Build Framework for {feature_name}"
        # Merge any partial data
        if isinstance(partial, dict):
            for key in ["rbiGuidelines", "ecosystemChallenges"]:
                if partial.get(key):
                    fb[key] = partial[key]
            if partial.get("sections"):
                for sec in partial["sections"]:
                    if sec.get("id") and sec.get("content"):
                        for i, fb_sec in enumerate(fb["sections"]):
                            if fb_sec["id"] == sec["id"]:
                                fb["sections"][i]["content"] = sec["content"]
                                break
        # Inject prompt context into feature section
        if fb["sections"]:
            fb["sections"][0]["content"] = (
                fb["sections"][0]["content"] + f"\n\nContext: {prompt[:300]}"
            )
        return fb

    def _default_rbi(self, name: str) -> str:
        return (
            f"RBI Master Direction 12032 (Digital Payment Security Controls): "
            f"Multi-factor authentication, TLS 1.3+ APIs, 5-year audit trails, fraud reporting within 6 hours. "
            f"RBI Notification 1888 (UPI Interoperability): Full KYC for transactions >₹10K, T+1 grievance resolution, "
            f"interoperability across all NPCI-registered PSPs. "
            f"NPCI OC 228 (UPI Reserve Pay / SBMD): Block duration limits, mandatory notifications for all lifecycle events, "
            f"online-verified merchants only, daily MIS by 07:00 IST. "
            f"All applicable to {name}."
        )

    def _default_ecosystem(self, name: str) -> str:
        return (
            f"Payer Apps (PhonePe, GPay, Paytm): SDK updates required; 6-8 week integration timeline. "
            f"Liability framework for new payment flows needs clarity. "
            f"Issuer Banks (SBI, HDFC, ICICI, Axis): Core banking upgrades needed for new transaction types; "
            f"public sector banks averaging 12-16 weeks for CBS integration. "
            f"Merchants (Zomato, Uber, Blinkit): High demand but mid-market merchants need plug-and-play SDKs. "
            f"Regulatory: Awaiting RBI guidelines on AI-triggered payments (expected Q2 2026). "
            f"All relevant for {name}."
        )
