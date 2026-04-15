# fallback/Titanium Standard templates

FALLBACK_CANVAS = {
    "featureName": "UPI Feature",
    "buildTitle": "Build Framework for UPI Feature",
    "overallStatus": "ongoing",
    "approved": False,
    "rbiGuidelines": (
        "RBI Master Direction 12032 (Digital Payment Security Controls): "
        "MFA mandatory for all payment initiations, TLS 1.3+ required for API, "
        "DSC validation for mandate-based payments (OC 228), and real-time fraud monitoring.\n\n"
        "RBI Notification 1888 (UPI Interoperability): Full KYC for transactions >₹10,000, "
        "T+1 grievance redressal via UDIR, and category-specific volume limits.\n\n"
        "NPCI OC 228 (UPI Reserve Pay): Secure fund blocking with mandatory customer lifecycle "
        "notifications and daily MIS reporting to NPCI by 07:00 IST."
    ),
    "ecosystemChallenges": (
        "Payer Apps: SDK versioning complexity with 15+ active versions (backward compatibility required).\n\n"
        "Issuer Banks: Core banking upgrades for real-time block accounting; 12-16 week integration cycle.\n\n"
        "Merchants: High checkout dropout risks; requirement for robust webhook reliability at peak load.\n\n"
        "Regulatory: Awaiting final guidelines on AI-triggered payment liability (Expected Q2 2026)."
    ),
    "sections": [
        {
            "id": 1,
            "title": "Feature",
            "status": "on-track",
            "approved": False,
            "content": (
                "Feature Strategy:\n"
                "This next-generation UPI capability enables seamless, secure, and intelligent fund transfers. "
                "It extends the NPCI ecosystem with enhanced interoperability and automation for high-frequency use cases.\n\n"
                "Customer Journey: Customer initiates → Authenticates (PIN/Biometric) → Multi-party Routing → "
                "Real-time Settlement → Instant Push Notification (<5s)."
            ),
        },
        {
            "id": 2,
            "title": "Need",
            "status": "on-track",
            "approved": False,
            "content": (
                "Business Case:\n"
                "Current UPI friction for complex or recurring workflows leads to 18% cart abandonment. "
                "Phase 2 addresses this by moving from single-event auth to context-aware, AI-assisted orchestration.\n\n"
                "Strategic Alignment: Directly supports NPCI's vision for 1 billion daily transactions and "
                "RBI's Payments Vision 2025 goals."
            ),
        },
        {
            "id": 6,
            "title": "Product Operating",
            "status": "ongoing",
            "approved": False,
            "content": (
                "3 Success KPIs:\n"
                "1. ADOPTION: 5+ anchor merchants live within 6 months.\n"
                "2. SCALE: 10M+ transactions/month within 12 months.\n"
                "3. QUALITY: Success rate >94%; T+1 dispute resolution (UDIR)."
            ),
        },
        {
            "id": 10,
            "title": "Compliance",
            "status": "on-track",
            "approved": False,
            "content": (
                "Compliance Checklist:\n"
                "✓ Multi-factor authentication (RBI 12032)\n"
                "✓ End-to-end encryption TLS 1.3\n"
                "✓ Audit trails with 5-year retention\n"
                "✓ Data residency (India-only storage per IT Act 2000)\n"
                "✓ Privacy compliance (DPDP Act 2023)"
            ),
        },
    ],
}


def generate_fallback_documents(canvas: dict) -> list:
    feature = canvas.get("featureName", "UPI Feature")
    date_str = datetime.now().strftime("%d/%m/%Y")
    sections = {s["id"]: s for s in canvas.get("sections", [])}

    def sec(id_: int) -> str:
        return sections.get(id_, {}).get("content", "Standard NPCI Protocol Implementation.")

    # Generate 11-Point Canonical Product Note
    product_note_content = f"""# {feature} — 11-Point Canonical Product Note
**Version:** 1.0 (PROVISIONED) | **Date:** {date_str} | **NPCI | CONFIDENTIAL**

---

## 1. Executive Summary
{feature} represents the next evolution of UPI orchestration, aimed at reducing checkout friction and improving transaction reliability for the Indian digital economy.

## 2. Feature Description
{sec(1)}

## 3. Business Need
{sec(2)}

## 4. Market View
The ecosystem anticipated response includes high adoption from Payer Apps (PhonePe, GPay) and anchor merchants seeking reduced abandonment rates.

## 5. Scalability
Demand anchors include Quick Commerce and Mobility. Scalability target: 500M+ potential users with specific focus on high-frequency transaction corridors.

## 6. Validation
MVP Status: Integrated with NPCI UAT Sandbox. Success KPIs: Block conversion >85%, Checkout time <12s.

## 7. Product Operating
{sec(6)}

## 8. Product Comms
Full documentation pack including Operational Circular (OC), TSD, FAQs, and Video Script have been provisioned for ecosystem distribution.

## 9. Pricing
Monetization via tiered interchange/switch fees (0.25-0.40%). Standard CASA transactions remain Zero MDR per government mandate.

## 10. Potential Risks
| Risk Area | Severity | Mitigation Strategy |
|-----------|----------|---------------------|
| Fraud | High | DSC Validation & AI Scoring |
| Infosec | High | TLS 1.3 & PII Tokenization |
| Regulatory | Medium | Proactive RBI Sandbox alignment |

## 11. Must-Have Compliances
{sec(10)}

---
*Generated by Titan Orchestration Engine — NPCI Compliance Group*"""

    return [
        {
            "id": "product-doc",
            "title": "Product Note",
            "icon": "📋",
            "approved": False,
            "lastEdited": date_str,
            "content": product_note_content,
        },
        {
            "id": "circular",
            "title": "Operational Circular",
            "icon": "📜",
            "approved": False,
            "lastEdited": date_str,
            "content": f"""NATIONAL PAYMENTS CORPORATION OF INDIA
UNIFIED PAYMENTS INTERFACE

**OPERATIONAL CIRCULAR — NPCI TITANIUM STANDARD**
OC No.: NPCI/2026-27/UPI/{feature[:3].upper()}001 | Date: {date_str}

**SUBJECT: Implementation Guidelines for {feature}**

---

**To,**
All UPI Member Banks,
All Third-Party Application Providers (TPAPs),
All Payment Service Providers (PSPs)

**1. BACKGROUND**
In alignment with RBI's Payments Vision 2025, NPCI is launching {feature} to enhance transaction automation and security.

**2. KEY FEATURES**
The implementation enables smarter authentication and real-time reconciliation per Titanium standards.

**3. COMPLIANCE CHECKLIST**
- ✓ Security: RBI Master Direction 12032 adherence.
- ✓ Notifications: Mandatory for all lifecycle events (Create, Execute, Revoke).
- ✓ Reporting: Daily MIS submission to NPCI by 07:00 IST.

**4. TIMELINE**
- Sandbox Availability: T+15 days
- Full Production Go-Live: T+90 days

**For National Payments Corporation of India,**
[Chief Product Officer] | [Chief Operating Officer]

---
*DRAFT — PROVISIONED BY TITAN SYSTEM*""",
        },
        {
            "id": "faqs",
            "title": "FAQs",
            "icon": "❓",
            "approved": False,
            "lastEdited": date_str,
            "content": f"# {feature} — FAQ Repository\n**Audience: Customers, Merchants, Banks**\n\n**Q1: Is {feature} secure?**\nA: Yes, it employs NPCI's multi-layered security framework including MFA and real-time fraud scoring.\n\n**Q2: How do I enable this?**\nA: This feature is auto-enabled for all users on the latest version of their UPI application.",
        },
        {
            "id": "video-script",
            "title": "Product Video Script",
            "icon": "🎬",
            "approved": False,
            "lastEdited": date_str,
            "content": f"# Video Script: {feature}\n**Format: 90-second animated explainer**\n\n[Scene 1] Hook showing current payment friction.\n[Scene 2] Reveal {feature} as the solution.\n[Scene 3] Call to Action: 'Experience the future with NPCI.'",
        },
        {
            "id": "rbi-summary",
            "title": "RBI Guidelines Summary",
            "icon": "🏛️",
            "approved": False,
            "lastEdited": date_str,
            "content": f"# Regulatory Compliance Mapping: {feature}\n\n| Feature Requirement | RBI Clause | Status |\n|---------------------|------------|--------|\n| MFA | RBI 12032 | ✅ COMPLIANT |\n| Data Residency | IT Act 2000 | ✅ COMPLIANT |\n| Privacy | DPDP 2023 | ✅ COMPLIANT |",
        },
        {
            "id": "test-cases",
            "title": "Test Cases",
            "icon": "🧪",
            "approved": False,
            "lastEdited": date_str,
            "content": f"# Ecosystem Test Bed: {feature}\n\n| TC ID | Scenario | Expected Result |\n|-------|----------|-----------------|\n| TC_01 | Happy Path Transaction | Success, status=COMPLETED |\n| TC_02 | Insufficient Funds | Error U71 |\n| TC_03 | Invalid VSA/VPA | Reject transaction |",
        },
        {
            "id": "product-deck",
            "title": "Product Deck",
            "icon": "📊",
            "approved": False,
            "lastEdited": date_str,
            "content": f"# {feature} — Formal Presentation\n\n## Slide 1: {feature}\nNPCI Strategy | Confidential\n\n## Slide 2: Market Opportunity\nAddressable market: 1B daily transactions.\n\n## Slide 3: Resilience & Compliance\nBuilt on NPCI's Titanium Standard architecture.",
        },
    ]
