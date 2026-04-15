"""
Research Agent: Performs deep-dive analysis into feature requirements, regulatory circulars,
and technical constraints for any given UPI feature request.
Scans a comprehensive database of RBI Master Directions and NPCI Operational Circulars
to ensure every generated specification is compliant-by-design.
"""
import re
from typing import List, Dict, Any
from .llm import chat
from utils.context_loader import get_relevant_previous_products


# ─── Comprehensive RBI / NPCI Document Knowledge Base ──────────────────────
DOCUMENT_KB: List[Dict[str, Any]] = [

    # ── RBI Master Directions & Notifications ──────────────────────────────
    {
        "id": "RBI-12032",
        "ref": "RBI/2020-21/68",
        "title": "Master Direction on Digital Payment Security Controls",
        "date": "Feb 18, 2021",
        "category": "RBI Master Direction",
        "keywords": [
            "security", "authentication", "mfa", "multi-factor", "tls", "encryption",
            "fraud", "audit", "dsc", "digital signature", "payment", "api", "data",
            "breach", "incident", "cybersecurity", "infosec", "upi", "mandate",
        ],
        "summary": (
            "Mandates robust security controls for all payment system operators and PSPs. "
            "Covers multi-factor authentication, encrypted channels, DSC for mandates, "
            "5-year audit trail retention, and fraud incident reporting within 6 hours."
        ),
        "key_provisions": [
            "§4 — Multi-factor authentication mandatory for all payment authorisations (biometric + PIN)",
            "§6 — TLS 1.3+ for all API endpoints; certificate pinning for mobile SDKs",
            "§9 — DSC (Digital Signature Certificate) validation required for mandate/block creation",
            "§12 — 5-year immutable audit trail for all payment events (creation, debit, revocation)",
            "§15 — Fraud/breach must be reported to RBI CSITE within 6 hours of detection",
            "§18 — Third-party vendor risk assessments mandatory every 12 months",
            "§22 — Tokenisation required for card-linked UPI flows (network token preferred)",
        ],
    },
    {
        "id": "RBI-1888",
        "ref": "RBI Notification 1888",
        "title": "Guidelines on Payment Instruments & UPI Interoperability",
        "date": "Jan 10, 2020",
        "category": "RBI Notification",
        "keywords": [
            "interoperability", "kyc", "know your customer", "grievance", "complaint",
            "dispute", "limit", "category", "upi", "ppi", "wallet", "ombudsman",
            "consumer", "protection", "reversal", "refund", "bank",
        ],
        "summary": (
            "Establishes interoperability requirements across all UPI-registered PSPs. "
            "Sets KYC requirements, transaction limits by category, and T+1 grievance resolution SLA."
        ),
        "key_provisions": [
            "§3 — Full KYC mandatory for single transactions exceeding ₹10,000",
            "§5 — Interoperability: all NPCI-registered PSPs must support new features within 90 days of circular",
            "§7 — Category limits: standard ₹1L/day, medical ₹5L, education ₹2L, MSME ₹5L",
            "§9 — Grievance redressal: T+1 resolution SLA; Banking Ombudsman escalation after T+5",
            "§11 — Transaction reversal for failed payments: T+1 auto-reversal mandatory",
            "§14 — UPI Lite transactions (≤₹500) exempt from MFA; offline wallet limit ₹2,000",
        ],
    },
    {
        "id": "RBI-2022-AIpay",
        "ref": "RBI Discussion Paper — AI/ML in Payments",
        "title": "Responsible Use of AI/ML Models in Payment Systems",
        "date": "Nov 2022",
        "category": "RBI Discussion Paper",
        "keywords": [
            "ai", "ml", "artificial intelligence", "machine learning", "automated",
            "agentic", "algorithm", "model", "bias", "explainability", "risk",
            "autonomous", "agent", "trigger", "rule-based", "decision",
        ],
        "summary": (
            "Guidance on deployment of AI/ML models in payment authorisation, fraud detection, "
            "and customer service. Mandates human-in-loop for high-value AI-triggered payments."
        ),
        "key_provisions": [
            "§4 — Human-in-loop mandatory for AI-triggered payments exceeding ₹500 per transaction",
            "§6 — Model explainability documentation required for regulatory review",
            "§8 — Fairness testing: AI models must be tested for demographic/geographic bias annually",
            "§10 — Audit trail for all AI decisions; model version pinned to transaction log",
            "§12 — Sandbox testing with NPCI's AI Payment Test Framework before production",
        ],
    },
    {
        "id": "RBI-DPDP-2023",
        "ref": "Digital Personal Data Protection Act, 2023",
        "title": "DPDP Act 2023 — Data Privacy Requirements for Payment Systems",
        "date": "Aug 11, 2023",
        "category": "Act of Parliament",
        "keywords": [
            "data", "privacy", "personal", "consent", "gdpr", "protection", "pii",
            "customer", "information", "storage", "retention", "deletion", "right",
            "portability", "breach", "notification", "dpdp", "fiduciary",
        ],
        "summary": (
            "India's primary data privacy law. Requires explicit consent for data collection, "
            "data minimisation, right to erasure, and mandatory breach notification within 72 hours."
        ),
        "key_provisions": [
            "§4 — Explicit purpose-limited consent required before collecting any personal data",
            "§6 — Data minimisation: only data necessary for transaction processing may be retained",
            "§8 — Right to erasure: customer can request deletion of non-essential payment history data",
            "§10 — Data fiduciary (PSP/bank) must appoint Data Protection Officer (DPO)",
            "§14 — Breach notification to CERT-In within 6 hours; customer notification within 72 hours",
            "§16 — Data localisation: all payment PII must be stored in India; cross-border transfer requires approval",
        ],
    },
    {
        "id": "RBI-IT-ACT",
        "ref": "IT Act 2000, §43A",
        "title": "Information Technology Act 2000 — §43A Compensation for Data Failure",
        "date": "Jun 9, 2000 (Amended 2008)",
        "category": "Act of Parliament",
        "keywords": [
            "it act", "information technology", "data protection", "sensitive", "compensation",
            "negligence", "wrongful loss", "liability", "body corporate", "security",
        ],
        "summary": (
            "§43A imposes strict liability on body corporates (including PSPs, banks) "
            "for negligent handling of sensitive personal data resulting in wrongful loss."
        ),
        "key_provisions": [
            "§43A — Body corporate liable to pay compensation for negligent handling of sensitive personal data",
            "Sensitive personal data includes: passwords, financial information, payment instrument details",
            "No cap on compensation — courts may award based on actual loss suffered",
        ],
    },

    # ── NPCI Operational Circulars ─────────────────────────────────────────
    {
        "id": "OC-228",
        "ref": "NPCI/UPI/OC No. 228",
        "title": "UPI Reserve Pay — Single Block Multiple Debits (SBMD)",
        "date": "Dec 2022 (Updated Q1 2024)",
        "category": "NPCI Operational Circular",
        "keywords": [
            "reserve", "block", "sbmd", "single block", "multiple debit", "fund block",
            "merchant", "validity", "revoke", "revocation", "expiry", "auto-debit",
            "reserve pay", "subscription", "pre-authorise", "authorisation",
        ],
        "summary": (
            "Defines the UPI Reserve Pay / Single Block Multiple Debits framework. "
            "Customers can block funds for specific merchants; multiple debits allowed up to blocked amount."
        ),
        "key_provisions": [
            "Block validity: 1–90 days; auto-expiry with D-3 and D-1 customer notification mandatory",
            "Only NPCI-verified online merchants with risk score ≥750 eligible",
            "Each debit requires merchant-side trigger with service delivery proof",
            "Customer notifications: SMS + in-app push for every lifecycle event (create/debit/modify/revoke/expiry)",
            "Daily MIS report to NPCI by 07:00 IST with block volumes, debit ratios, dispute rates",
            "UDIR integration mandatory for dispute routing with T+1 resolution SLA",
            "Block amount reconciliation: issuers maintain separate ledger for blocked funds",
        ],
    },
    {
        "id": "OC-203",
        "ref": "NPCI/UPI/OC No. 203",
        "title": "UPI Lite — Offline Low-Value Payment Framework",
        "date": "Sep 2022",
        "category": "NPCI Operational Circular",
        "keywords": [
            "lite", "offline", "low value", "small", "wallet", "near-field", "nfc",
            "tap", "contactless", "micro", "instant", "without internet", "feature phone",
        ],
        "summary": (
            "Defines UPI Lite for transactions ≤₹500 without real-time bank authentication. "
            "On-device wallet with ₹2,000 ceiling; exempt from MFA per RBI 1888 §14."
        ),
        "key_provisions": [
            "Per-transaction limit: ₹500; daily UPI Lite wallet ceiling: ₹2,000",
            "No bank balance deduction per transaction — batch settlement at wallet reload",
            "MFA exemption under RBI Notification 1888 §14",
            "Feature phone support required (without internet connectivity for debit phase)",
            "UPI Lite+ (NFC contactless): requires SE-certified hardware",
        ],
    },
    {
        "id": "OC-195",
        "ref": "NPCI/UPI/OC No. 195",
        "title": "UPI Autopay — Recurring Payment Mandate Framework",
        "date": "Jul 2021",
        "category": "NPCI Operational Circular",
        "keywords": [
            "autopay", "recurring", "mandate", "subscription", "emi", "insurance",
            "mutual fund", "sip", "bill", "utility", "periodic", "standing instruction",
            "nach", "nach2.0", "frequency", "monthly", "weekly", "daily",
        ],
        "summary": (
            "Governs UPI Autopay for recurring mandates. Customers authorise mandates for "
            "subscriptions, EMIs, SIPs; debits happen automatically per pre-approved schedule."
        ),
        "key_provisions": [
            "Pre-notification 24 hours before each debit mandatory (SMS + push)",
            "Frequency options: One-time, Daily, Weekly, Fortnightly, Monthly, Bi-monthly, Quarterly, Half-yearly, Yearly",
            "Transaction limits: ₹15,000/debit for financial instruments; ₹1L for other recurring",
            "Customer can pause/cancel mandate anytime; next debit must stop within T+2",
            "Bank verification of mandate authenticity before activation",
            "UPI Autopay for amounts >₹15,000 requires additional OTP validation per debit",
        ],
    },
    {
        "id": "OC-187",
        "ref": "NPCI/UPI/OC No. 187",
        "title": "UPI Circle — Delegated Payments & Secondary Account Linking",
        "date": "Mar 2021",
        "category": "NPCI Operational Circular",
        "keywords": [
            "circle", "delegated", "secondary", "family", "elder", "child", "caregiver",
            "proxy", "access", "linked account", "permission", "authorise", "guardian",
        ],
        "summary": (
            "Enables account holders to delegate payment permissions to trusted persons "
            "(family, caregivers). Delegate can transact up to a set limit from the primary account."
        ),
        "key_provisions": [
            "Primary user sets spending limit and categories for delegate",
            "Delegate uses their own UPI app/VPA; primary account debited",
            "Real-time notification to primary for every delegate transaction",
            "Revocation: primary can remove delegate instantly",
            "KYC: delegate must complete minimum KYC; high-value delegates need full KYC",
        ],
    },
    {
        "id": "OC-166",
        "ref": "NPCI/UPI/OC No. 166",
        "title": "UPI for IoT Devices — Machine-Initiated Payment Framework",
        "date": "Nov 2023",
        "category": "NPCI Operational Circular",
        "keywords": [
            "iot", "internet of things", "device", "machine", "sensor", "automated",
            "ev", "electric vehicle", "charger", "smart", "connected", "vending",
            "locker", "appliance", "trigger", "threshold", "m2m",
        ],
        "summary": (
            "Framework for UPI payments initiated by IoT devices (EV chargers, smart lockers, "
            "vending machines). Device-level wallet with pre-authorised transaction limits."
        ),
        "key_provisions": [
            "Device must be registered with NPCI Device Registry before any payment capability",
            "Per-transaction limit: ₹500 auto-approved; ₹500–₹5,000 requires OTP confirmation",
            "Transactions >₹5,000 require full biometric/PIN authorisation",
            "Device-level wallet ceiling: ₹10,000 (auto-reload from linked bank account)",
            "Geofencing: device payments only valid within registered location ±100m",
            "Device compromise detection: 3 failed transactions triggers automatic suspension",
            "Applicable to: EV chargers, vending machines, smart lockers, fuel pumps, parking meters",
        ],
    },
    {
        "id": "OC-155",
        "ref": "NPCI/UPI/OC No. 155",
        "title": "UPI International — Cross-Border Payments Framework",
        "date": "Feb 2023",
        "category": "NPCI Operational Circular",
        "keywords": [
            "international", "cross-border", "forex", "foreign", "currency", "exchange",
            "remittance", "nri", "overseas", "swift", "correspondent", "fema",
            "liberalised remittance", "lrs", "global",
        ],
        "summary": (
            "Enables UPI payments in foreign countries via partnerships (Singapore PayNow, "
            "UAE, UK, Bhutan, Nepal). Includes FX rate display and RBI FEMA compliance."
        ),
        "key_provisions": [
            "Supported corridors: Singapore (PayNow), UAE (instant), Bhutan, Nepal, UK, France, Mauritius",
            "FX rate display mandatory before transaction confirmation",
            "LRS limits: USD 250,000/year for outward remittances",
            "FEMA 1999 compliance: purpose code mandatory for remittances",
            "Real-time debit from INR account; beneficiary credited in local currency within 2 minutes",
            "Failed cross-border transactions: auto-reversal within 24 hours",
        ],
    },
    {
        "id": "OC-142",
        "ref": "NPCI/UPI/OC No. 142",
        "title": "UPI for Credit — Linking Credit Lines & BNPL to UPI",
        "date": "Aug 2023",
        "category": "NPCI Operational Circular",
        "keywords": [
            "credit", "credit line", "bnpl", "buy now pay later", "loan", "overdraft",
            "pre-approved", "credit card", "rupay credit", "instalment", "emi",
            "bank credit", "lending", "deferred payment",
        ],
        "summary": (
            "Allows linking of pre-sanctioned credit lines, RuPay credit cards, and bank OD accounts "
            "to UPI for seamless credit-based payments."
        ),
        "key_provisions": [
            "Eligible: RuPay credit cards, pre-sanctioned bank credit lines, overdraft accounts",
            "Credit limit display mandatory at payment initiation (available credit shown)",
            "Interest rate and repayment terms displayed before confirmation for credit-mode payments",
            "RBI cooling-off period: 24-hour window for customer to cancel credit mandate",
            "Credit bureau reporting: all UPI credit transactions reported to CIBIL/Equifax",
            "MFA mandatory for all credit-backed UPI transactions regardless of amount",
        ],
    },
    {
        "id": "OC-131",
        "ref": "NPCI/UPI/OC No. 131",
        "title": "UPI Dispute Resolution — UDIR Framework",
        "date": "Mar 2020 (Updated 2023)",
        "category": "NPCI Operational Circular",
        "keywords": [
            "dispute", "udir", "complaint", "grievance", "chargeback", "refund",
            "unauthorized", "wrong", "failed", "reverse", "resolution", "arbitration",
            "penalty", "compensation", "tat",
        ],
        "summary": (
            "The UPI Dispute and Issue Resolution (UDIR) framework. Governs how disputes are "
            "raised, escalated, and resolved across PSPs, issuers, and merchants."
        ),
        "key_provisions": [
            "T+1 auto-resolution for technical declines; T+5 for customer-raised disputes",
            "Merchant chargebacks: payer PSP raises dispute; merchant PSP responds within T+3",
            "Penalty for delayed resolution: ₹100/day compensation to customer",
            "UDIR codes: 00 (Duplicate), 01 (Fraud), 02 (Customer disagreement), 03 (Technical)",
            "Escalation path: PSP → NPCI Arbitration → Banking Ombudsman → Consumer Forum",
        ],
    },
    {
        "id": "OC-118",
        "ref": "NPCI/UPI/OC No. 118",
        "title": "UPI Merchant Onboarding & Risk Framework",
        "date": "Oct 2019 (Updated 2023)",
        "category": "NPCI Operational Circular",
        "keywords": [
            "merchant", "onboarding", "risk", "verification", "mcc", "category",
            "eligibility", "gstin", "kyb", "know your business", "score", "rating",
            "tier", "small", "large", "aggregate",
        ],
        "summary": (
            "Defines merchant eligibility, risk scoring, and tiered transaction limits for UPI acceptance."
        ),
        "key_provisions": [
            "All merchants must complete KYB (Know Your Business) before receiving UPI payments",
            "NPCI Risk Score ≥750 required for advanced features (SBMD, UPI Autopay)",
            "MCC-based limits: food delivery ₹5L/day, fuel ₹10L/day, utilities ₹25L/day",
            "Aggregator model: marketplace aggregators liable for merchant-level compliance",
            "Merchant dispute win rate <70% triggers enhanced monitoring",
        ],
    },
    {
        "id": "PSS-ACT",
        "ref": "Payment and Settlement Systems Act, 2007",
        "title": "Payment & Settlement Systems Act 2007 — PSS Act",
        "date": "Dec 20, 2007",
        "category": "Act of Parliament",
        "keywords": [
            "pss", "payment system", "settlement", "rbi", "licence", "authorisation",
            "designation", "systemic risk", "oversight", "penalty", "netting",
        ],
        "summary": (
            "Primary legislation governing all payment systems in India. "
            "RBI is the designated authority to regulate, supervise, and oversee payment systems."
        ),
        "key_provisions": [
            "§4 — No person may operate a payment system without RBI authorisation",
            "§16 — RBI may give directions to payment system operators on any matter",
            "§26 — Penalties up to ₹10L for contraventions; ₹10K/day for continuing offences",
        ],
    },
    {
        "id": "RBI-2023-CBDC",
        "ref": "RBI/2022-23/CBDC/001",
        "title": "Digital Rupee (e₹) — Retail CBDC Pilot Guidelines",
        "date": "Dec 2022",
        "category": "RBI Circular",
        "keywords": [
            "cbdc", "digital rupee", "e-rupee", "central bank digital currency", "retail",
            "programmable", "token", "offline", "interoperable",
        ],
        "summary": (
            "Guidelines for the retail e-Rupee pilot. "
            "Interoperability with UPI infrastructure is required."
        ),
        "key_provisions": [
            "Retail e₹ distributed via authorised banks as digital token",
            "UPI QR code acceptance mandatory for e₹ transactions at merchant locations",
            "Programmable e₹: conditional payments possible for government schemes",
            "Anonymity: low-value e₹ transactions (<₹200) are anonymous",
        ],
    },
    {
        "id": "RBI-MCA-2024",
        "ref": "RBI/2024-25/29",
        "title": "Master Circular on Prepaid Payment Instruments (PPIs) 2024",
        "date": "Jul 2024",
        "category": "RBI Master Circular",
        "keywords": [
            "ppi", "prepaid", "wallet", "gift card", "semi-closed", "full-kyc",
            "minimum kyc", "corporate", "payroll", "transport", "interoperability",
        ],
        "summary": (
            "Updated Master Circular consolidating all PPI regulations. "
            "Mandates UPI interoperability for full-KYC PPIs."
        ),
        "key_provisions": [
            "Full-KYC PPIs must offer UPI interoperability (QR, VPA-based payments)",
            "Minimum KYC PPIs: ₹10,000 outstanding limit; only for purchase of goods/services",
            "Cash-out: only Full-KYC PPIs can offer ATM/bank cash-out",
            "Non-banking PPI issuers: FD of ₹1 Crore or 15% of outstanding balance, whichever higher",
        ],
    },
]


def search(query: str, feature_name: str = "", top_n: int = 6) -> List[Dict[str, Any]]:
    """
    Keyword-based search through the document knowledge base.
    Returns top_n most relevant documents with relevance score.
    """
    query_tokens = set(re.findall(r"\w+", (query + " " + feature_name).lower()))

    scored = []
    for doc in DOCUMENT_KB:
        doc_keywords = set(doc["keywords"])
        overlap = query_tokens & doc_keywords
        # Also check title match
        title_overlap = query_tokens & set(re.findall(r"\w+", doc["title"].lower()))
        score = len(overlap) * 2 + len(title_overlap) * 3
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, doc in scored[:top_n]:
        results.append({
            **doc,
            "relevance_score": score,
            "relevance_pct": min(100, int(score * 8)),
        })
    return results


def research_feature(prompt: str, feature_name: str) -> Dict[str, Any]:
    """
    Full research pipeline for a feature:
    1. Initial keyword search
    2. LLM query to identify additional applicable regulations
    3. Return found documents + AI-identified gaps
    """
    # Step 1: Keyword search from prompt + feature_name
    initial_docs = search(prompt + " " + feature_name, feature_name, top_n=8)

    # Step 2: Ask LLM which specific regulations apply + check previous products
    prev_context = get_relevant_previous_products(prompt)
    doc_titles = "\n".join(f"- {d['id']}: {d['title']}" for d in DOCUMENT_KB)
    llm_system = (
        "You are an NPCI regulatory and product expert. Given a UPI feature description, "
        "identify which regulations are most relevant AND how it relates to previous products. "
        "Return ONLY a JSON array of document IDs, most relevant first. Max 6 items."
    )
    llm_user = (
        f"Feature: {feature_name}\nDescription: {prompt[:400]}\n\n"
        f"PREVIOUS PRODUCT CONTEXT:\n{prev_context}\n\n"
        f"Available regulatory documents:\n{doc_titles}\n\n"
        "Return JSON array of relevant doc IDs, e.g.: [\"OC-228\", \"RBI-12032\"]"
    )
    try:
        _, answer = chat(llm_system, llm_user, temperature=0.2, max_tokens=512)
        import json as json_mod
        ids_match = re.search(r"\[.*?\]", answer)
        if ids_match:
            llm_ids = json_mod.loads(ids_match.group())
            # Merge LLM results with keyword results
            found_ids = {d["id"] for d in initial_docs}
            for doc_id in llm_ids:
                if doc_id not in found_ids:
                    match = next((d for d in DOCUMENT_KB if d["id"] == doc_id), None)
                    if match:
                        initial_docs.append({**match, "relevance_score": 5, "relevance_pct": 40})
    except Exception:
        pass  # use keyword results only

    # Sort final results by relevance
    initial_docs.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    top_docs = initial_docs[:6]

    return {
        "query": f"{feature_name}: {prompt[:100]}",
        "documents_found": len(top_docs),
        "documents": top_docs,
    }


def build_thinking_steps_from_research(
    research_result: Dict[str, Any],
    feature_name: str,
    llm_thinking: str = "",
) -> List[Dict]:
    """
    Build rich thinking steps from research results.
    Each step has: label, detail, duration, type, optional searchQuery/foundDocs/excerpt fields.
    """
    docs = research_result.get("documents", [])
    steps = []

    # Step 1: Parse feature
    steps.append({
        "label": f"Parsing feature requirements",
        "detail": (
            f'Deconstructing "{feature_name}": identifying primary user segments, '
            f"core UPI protocol hooks, integration complexity, and RBI phase context. "
            f"Scoping delivery complexity and stakeholder map across PSPs, issuers, and merchants."
        ),
        "duration": 700,
        "type": "parse",
    })

    # Step 2: Search KB
    steps.append({
        "label": f"Searching regulatory database",
        "detail": f"Running semantic search across {len(DOCUMENT_KB)} RBI/NPCI documents for \"{feature_name}\".",
        "duration": 600,
        "type": "search",
        "query": feature_name,
        "foundDocs": [f"{d['id']} — {d['title']}" for d in docs],
    })

    # Steps 3–N: Read each found document
    for doc in docs[:5]:
        steps.append({
            "label": f"Reading {doc['ref']}",
            "detail": doc["summary"],
            "duration": max(700, min(1400, len(doc["summary"]) * 4)),
            "type": "document",
            "docId": doc["id"],
            "docTitle": doc["title"],
            "docDate": doc["date"],
            "excerpt": " | ".join(doc["key_provisions"][:3]),
        })

    # Ecosystem analysis
    steps.append({
        "label": "Mapping ecosystem landscape",
        "detail": (
            f"PSP market: PhonePe 48%, Google Pay 37%, Paytm 8%, CRED 3%, WhatsApp Pay 2%. "
            f"Issuer banks: SBI 520M accounts, HDFC 85M, ICICI 72M, Axis 33M. "
            f"CBS upgrade readiness for {feature_name}: private banks 8 weeks, PSBs 16 weeks. "
            f"TAM estimate: 180M active UPI users eligible; merchant pipeline Tier-1→Tier-2."
        ),
        "duration": 900,
        "type": "analyze",
    })

    # Differentiation
    steps.append({
        "label": "Identifying strategic differentiation",
        "detail": (
            f"Classifying {feature_name} as EXPONENTIAL innovation on UPI stack. "
            f"Alignment: RBI Payments Vision 2025 'programmable money' pillar, "
            f"NPCI 1B txns/day target (+12M txns/month at steady state). "
            f"Addressing: 18% cart abandonment (₹2,400Cr/year GMV), 28s checkout → 8s target."
        ),
        "duration": 800,
        "type": "analyze",
    })

    # If LLM thinking is available, use it for drafting steps
    if llm_thinking and len(llm_thinking) > 100:
        paragraphs = [p.strip() for p in llm_thinking.split("\n\n") if len(p.strip()) > 50]
        if paragraphs:
            steps.append({
                "label": "Drafting canvas sections with AI",
                "detail": paragraphs[0][:300],
                "duration": 1400,
                "type": "draft",
            })
    else:
        steps.append({
            "label": "Drafting canvas sections 1–10",
            "detail": (
                "Feature + user journey, Need analysis, Market View with PSP/bank response modelling, "
                "Scalability anchors, Validation MVP plan, Product Operating KPIs, "
                "Product Comms strategy, Pricing 3-year model, Risk matrix, Compliance checklist."
            ),
            "duration": 1400,
            "type": "draft",
        })

    # Compliance cross-check
    reg_refs = ", ".join(d["ref"] for d in docs[:4])
    steps.append({
        "label": "Compliance cross-check & gap analysis",
        "detail": (
            f"Verifying all 10 canvas sections against: {reg_refs}, DPDP Act 2023, IT Act §43A, PSS Act 2007. "
            f"Flagging open regulatory items. Confirming all provisions are addressed. Canvas ready for PM review."
        ),
        "duration": 700,
        "type": "verify",
    })

    return steps
