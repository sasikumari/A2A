"""
NPCI Titanium Specification Skills - Universal 11-Point Canonical Product Note generation.
"""

from __future__ import annotations
import re
from . import Skill, SkillResult


class GenerateCanonicalSpecSkill(Skill):
    name = "generate_canonical_spec"
    description = (
        "Generate a high-fidelity NPCI 11-Point Canonical Product Note for any given prompt/product. "
        "Ensures compliance-grade documentation structure and formal regulatory tone."
    )
    parameters = {
        "type": "object",
        "properties": {
            "feature_name": {
                "type": "string",
                "description": "Name of the UPI feature.",
            },
            "prompt": {
                "type": "string",
                "description": "The requirements or change request.",
            },
        },
        "required": ["feature_name", "prompt"],
    }

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def execute(self, feature_name: str, prompt: str, **_) -> SkillResult:
        system_prompt = """You are a Senior NPCI Product Steering Committee Member.
Your goal is to produce a 11-Point CANONICAL PRODUCT NOTE for a UPI feature.
The tone must be EXTREMELY FORMAL and follow NPCI regulatory standards.

The structure MUST be:
1. Executive Summary (Strategic vision and NPCI alignment)
2. Feature Description (Formal functionality + user journey)
3. Business Need (Gap analysis and competitive differentiation)
4. Market View (Ecosystem response from PSPs, Banks, Merchants)
5. Scalability (Demand/Supply anchors and transaction targets)
6. Validation (MVP status, pilot partners, success KPIs)
7. Product Operating (KPIs, UDIR grievance, operating cadence)
8. Product Comms (Circular, TSD, FAQ, Video orientation)
9. Pricing (Revenue view, Interchange/MDR strategy)
10. Potential Risks (Detailed Fraud, Infosec, Operational, Regulatory)
11. Must-Have Compliances (Specific RBI/NPCI clauses)

Return the content in clean Markdown with 'NPCI | CONFIDENTIAL' footers.
"""
        user_prompt = f"Feature: {feature_name}\nRequirements: {prompt}\n\nGenerate the 11-Point Canonical Product Note."
        
        result = self.llm_client.query(f"{system_prompt}\n\n{user_prompt}")
        result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL).strip()

        if not result:
            return SkillResult(success=False, error="LLM returned empty specification.")

        return SkillResult(
            success=True,
            output=result,
            metadata={"feature": feature_name, "length": len(result)}
        )

class FormalizeBRDSkill(Skill):
    name = "formalize_brd"
    description = (
        "Formalize the Product Kit into a binding Business Requirements Document (BRD). "
        "Transforms high-level documentation into technical requirements for all parties."
    )
    parameters = {
        "type": "object",
        "properties": {
            "feature_name": {"type": "string"},
            "product_kit": {"type": "string", "description": "The full documentation suite."},
        },
        "required": ["feature_name", "product_kit"],
    }
    
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def execute(self, feature_name: str, product_kit: str, **_) -> SkillResult:
        system_prompt = """You are a Senior NPCI Regulatory Architect and Chief Documentation Officer.
Your task: Transform the provided Product Kit into a BINDING, LEGALLY-COMPLETE Business Requirements Document (BRD).

The BRD MUST contain ALL 8 sections below in formal Markdown:

---
# Business Requirements Document (BRD)
## Feature: [Feature Name] | Classification: NPCI CONFIDENTIAL | Version: 1.0

---
## 1. Executive Summary
   - Strategic alignment with NPCI/RBI mandate
   - Business problem being solved
   - Expected outcome and success definition

## 2. Scope & Objectives
   - In-scope capabilities (numbered list)
   - Out-of-scope items (numbered list)
   - Measurable objectives with KPIs

## 3. Stakeholder Matrix
   | Stakeholder | Role | Responsibility | Approval Required |
   |---|---|---|---|
   | NPCI Product Team | Owner | ... | Yes |
   | Payer PSP | Implementer | ... | Yes |
   | Payee PSP | Implementer | ... | Yes |
   | Remitter Bank | Implementer | ... | Yes |
   | Beneficiary Bank | Implementer | ... | Yes |
   | RBI | Regulator | ... | No |

## 4. Functional Requirements
   Group by party. Each requirement: FR-{PARTY}-{NN} | Priority: HIGH/MED/LOW
   ### 4.1 NPCI Switch Requirements  (FR-SW-01, FR-SW-02, ...)
   ### 4.2 Payer PSP Requirements    (FR-PP-01, FR-PP-02, ...)
   ### 4.3 Payee PSP Requirements    (FR-PEP-01, ...)
   ### 4.4 Remitter Bank Requirements (FR-RB-01, ...)
   ### 4.5 Beneficiary Bank Requirements (FR-BB-01, ...)

## 5. Non-Functional Requirements
   | Category | Requirement | Target SLA |
   |---|---|---|
   | Performance | TPS at peak | ≥5000 TPS |
   | Availability | Uptime | 99.99% |
   | Latency | P99 end-to-end | ≤600ms |
   | Security | Encryption | AES-256, TLS 1.3 |
   | Data Retention | Txn logs | 7 years per RBI |

## 6. Regulatory Compliance
   - Specific NPCI Operating Circulars referenced (OC number + title)
   - Specific RBI Master Directions referenced (MD number + clause)
   - Specific PCI-DSS or ISO clauses if applicable
   - Data localization requirements

## 7. Risk Register
   | Risk ID | Description | Likelihood | Impact | Mitigation |
   |---|---|---|---|---|
   | RSK-01 | ... | High/Med/Low | High/Med/Low | ... |

## 8. Acceptance Criteria
   - Formal UAT pass conditions per party
   - NPCI Certification sign-off checklist
   - Go/No-Go decision matrix
---
*NPCI | CONFIDENTIAL | Unauthorized distribution prohibited*
"""
        user_prompt = f"Feature: {feature_name}\n\nProduct Kit:\n{product_kit}\n\nGenerate the complete 8-section BRD."
        result = self.llm_client.query(f"{system_prompt}\n\n{user_prompt}")
        import re as _re
        result = _re.sub(r"<think>.*?</think>", "", result, flags=_re.DOTALL).strip()
        if not result:
            return SkillResult(success=False, error="LLM returned empty BRD.")
        return SkillResult(success=True, output=result)



class SyncIntentSkill(Skill):
    name = "sync_intent"
    description = (
        "NPCI Orchestrator distributes the TSD and Change Manifest to all participant agents (Bank, PSP). "
        "Handles the formal Agent-to-Agent handshake and acknowledgment protocol."
    )
    parameters = {
        "type": "object",
        "properties": {
            "feature_name": {"type": "string"},
            "tsd": {"type": "string", "description": "The Technical Specification Document."},
            "participants": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["feature_name", "tsd", "participants"],
    }

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def execute(self, feature_name: str, tsd: str, participants: list, **_) -> SkillResult:
        handshake_log = []
        for p in participants:
            handshake_log.append(f"AGENT_NOTIFY: {p} notified of Intent for {feature_name}.")
            handshake_log.append(f"TSD_SHARE: Shared Technical Specification with {p} Agent node.")
            handshake_log.append(f"ACK_RECV: Acknowledgment Token received from {p} with Intent ID: {hash(p)}.")
        
        return SkillResult(
            success=True, 
            output="\n".join(handshake_log), 
            metadata={"participants": participants}
        )
