import type { CanvasData, Document, PrototypeData, ExecutionItem } from '../types';
import { getCodePlan, getFilesTouched, getTotalLinesAffected, getLayerSummary } from './upiCodebaseMap';

export const RBI_GUIDELINES = {
  notification_12032: `Master Direction on Digital Payment Security Controls (RBI/2020-21/68, Feb 18, 2021):
• All payment system operators must implement robust security controls including multi-factor authentication, end-to-end encryption, and fraud monitoring systems.
• UPI transactions must comply with API security standards, rate limiting, and transaction monitoring thresholds.
• Banks and PSPs must maintain audit trails for all UPI operations including block creation, modification, execution, and revocation.
• Customer data protection: PII must be masked in logs; access to transaction data restricted on need-to-know basis.
• Incident response: Any breach or anomaly must be reported to RBI within stipulated timeframes.
• For block/mandate-based payments (like UPI Reserve Pay): Issuers must validate block authenticity using DSC, enforce block limits, and send customer notifications for every lifecycle event.`,

  notification_1888: `RBI Guidelines on Prepaid Payment Instruments and UPI Interoperability (Notification 1888):
• UPI-based payment instruments must ensure interoperability across all PSPs registered with NPCI.
• Consumer protection: Customers must receive transaction confirmations, dispute resolution pathways must be available within UPI framework.
• Know Your Customer (KYC): Full KYC mandatory for high-value UPI transactions; enhanced due diligence for corporate accounts.
• Limits: RBI prescribes per-transaction and daily limits for different UPI categories; medical and educational payments have enhanced limits.
• Grievance Redressal: All UPI complaints to be addressed within T+1; escalation to banking ombudsman available.
• For A2A payments: Payer and payee PSPs must validate counterparty credentials; reversals must be processed within defined timelines.`,

  sbmd_guidelines: `RBI Single Block Multiple Debits (SBMD / UPI Reserve Pay) Guidelines (Dec 2022 onwards):
• Customers can block funds in their bank account for specific merchants/purposes with single authorization.
• Multiple debits allowed up to the blocked amount; each debit requires merchant-side trigger with service delivery proof.
• Block duration limits apply as per issuer policy (typically 1-90 days); automatic expiry with customer notification.
• Customer consent: Explicit consent required at block creation; modification and revocation rights preserved.
• Merchant eligibility: Only NPCI-verified online merchants permitted; risk scoring applied.
• Reconciliation: Issuers must maintain real-time available balance considering blocked amounts; separate ledger for block accounting.
• Consumer safeguards: Service delivery verification before debit; dispute window for unauthorized debits; ODR (UDIR) integration mandatory.
• Regulatory reporting: Monthly MIS to NPCI on block volumes, debit ratios, dispute rates.`
};

export function generateCanvas(prompt: string, featureName: string): CanvasData {
  const name = featureName || extractFeatureName(prompt);
  
  return {
    featureName: name,
    buildTitle: `Build Framework for ${name}`,
    overallStatus: 'ongoing',
    approved: false,
    rbiGuidelines: `${RBI_GUIDELINES.notification_12032}\n\n${RBI_GUIDELINES.notification_1888}\n\n${RBI_GUIDELINES.sbmd_guidelines}`,
    ecosystemChallenges: generateEcosystemChallenges(prompt, name),
    sections: [
      {
        id: 1,
        title: 'Feature',
        status: 'on-track',
        approved: false,
        content: generateFeatureSection(prompt, name),
      },
      {
        id: 2,
        title: 'Need',
        status: 'on-track',
        approved: false,
        content: generateNeedSection(prompt, name),
      },
      {
        id: 3,
        title: 'Market View',
        status: 'open',
        approved: false,
        content: generateMarketViewSection(prompt, name),
      },
      {
        id: 4,
        title: 'Scalability',
        status: 'open',
        approved: false,
        content: generateScalabilitySection(prompt, name),
      },
      {
        id: 5,
        title: 'Validation',
        status: 'ongoing',
        approved: false,
        content: generateValidationSection(prompt, name),
      },
      {
        id: 6,
        title: 'Product Operating',
        status: 'ongoing',
        approved: false,
        content: generateProductOperatingSection(prompt, name),
      },
      {
        id: 7,
        title: 'Product Comms',
        status: 'open',
        approved: false,
        content: generateProductCommsSection(prompt, name),
      },
      {
        id: 8,
        title: 'Pricing',
        status: 'open',
        approved: false,
        content: generatePricingSection(prompt, name),
      },
      {
        id: 9,
        title: 'Potential Risks',
        status: 'ongoing',
        approved: false,
        content: generateRisksSection(prompt, name),
      },
      {
        id: 10,
        title: 'Compliance',
        status: 'on-track',
        approved: false,
        content: generateComplianceSection(prompt, name),
      },
    ],
  };
}

function extractFeatureName(prompt: string): string {
  const lower = prompt.toLowerCase();
  if (lower.includes('a2a')) return 'UPI A2A Payments Phase 2';
  if (lower.includes('biometric')) return 'UPI Biometric Payments Enhancement';
  if (lower.includes('iot') || lower.includes('device') || lower.includes('secondary')) return 'UPI for Secondary Devices — Phase 2';
  if (lower.includes('multi') && lower.includes('sign')) return 'UPI Multisignatory Payments Enhancement';
  if (lower.includes('reserve') || lower.includes('block')) return 'UPI Reserve Pay Enhancement';
  const words = prompt.split(' ').slice(0, 5).join(' ');
  return words.length > 3 ? words : 'New UPI Feature';
}

function generateFeatureSection(prompt: string, name: string): string {
  return `Explain the feature for a layman:
${name} is a next-generation UPI payment capability that enables seamless, secure, and intelligent fund transfers. Building on Phase 1 successes (Biometric payments, Multisignatory UPI, UPI ReservePay, UPI Circle for IoT), this phase extends the ecosystem with enhanced interoperability and automation.

Key user-facing benefit: Customers can complete complex payment workflows with fewer steps, greater security, and real-time confirmation — all within their existing UPI app.

User journey: Customer initiates → Authenticates → Confirms → Transacts → Gets instant confirmation, all in under 5 seconds.

Phase 2 context: ${prompt.slice(0, 250)}`;
}

function generateNeedSection(_prompt: string, _name: string): string {
  return `Why should we do this?
The Indian digital payments ecosystem has grown to 14+ billion UPI transactions/month. Phase 2 addresses the next frontier: higher automation, broader merchant coverage, and deeper financial inclusion.

Key gaps addressed:
• Current limitation: Phase 1 features have limited interoperability with emerging use cases (AI agents, IoT commerce, embedded finance)
• Customer pain: Multi-step authentication friction for recurring/predictable payments
• Merchant pain: High dropout rates during checkout; reconciliation complexity

Differentiation:
EXPONENTIAL improvement — moves from single-event authorization to context-aware, AI-assisted payment orchestration aligned with emerging RBI sandbox framework.

Strategic alignment: Directly supports NPCI's Digital India vision and RBI's Payments Vision 2025 goals for UPI transaction doubling.`;
}

function generateMarketViewSection(_p: string, _n: string): string {
  return `Ecosystem Anticipated Response:

Payer Apps (PhonePe, GPay, Paytm, CRED, WhatsApp Pay):
• Strong positive reception — reduces payment friction, improves NPS scores
• Will require SDK updates; 6-8 week integration timeline estimated
• Concern: Liability framework for automated/AI-triggered payments

Payee PSPs & Merchants:
• High demand from: Quick commerce (Zomato, Blinkit, Zepto), Mobility (Uber, Ola, DMRC), Subscriptions (Hotstar, Netflix IN)
• Concern: Technical complexity of webhook/callback reliability at scale
• Demand for sandbox environment before production rollout

Issuer Banks (HDFC, ICICI, SBI, Axis, BNPL providers):
• Cautious optimism — need clarity on block accounting, credit risk treatment
• Public sector banks require 12-16 weeks for core banking integration
• Credit line issuers see strong cross-sell opportunity

Regulator Signals:
• RBI Payments Vision 2025 explicitly supports programmable money and smart payments
• Guidelines expected on AI-triggered payment authorizations`;
}

function generateScalabilitySection(_prompt: string, _name: string): string {
  return `Market Anchors to Make It Big:

DEMAND SIDE:
• Food & Quick Commerce: Zomato (90M+ users), Swiggy, Blinkit, Zepto, Zepto Cafe — high-frequency, low-value transactions ideal for optimization
• Mobility: Uber, Ola, DMRC, BRTS — trip-based payment patterns benefit from block-debit model
• Subscriptions & OTT: Multi-plan management, household payment delegation
• B2B / MSME: Recurring supplier payments, GST-linked disbursements
• IoT Commerce: Smart appliances auto-replenishment (Phase 1 IoT Circle extension)

SUPPLY SIDE:
• Top Apps: PhonePe (48% market share), Google Pay (37%), Paytm, BHIM, Amazon Pay
• Top CASA Issuers: SBI (520M+ accounts), HDFC, ICICI, Axis, PNB, BOB
• Credit Line Issuers: HDFC Credit, ICICI Credit, Bajaj Finserv, Amazon Pay Later
• Neo Banks & Fintechs: Fi, Jupiter, Slice, Uni

SCALE TARGET: 500M+ potential users; ₹2L+ Cr monthly transaction value addressable market within 24 months`;
}

function generateValidationSection(_prompt: string, _name: string): string {
  return `Creating and Operating MVP:

MVP Status: Building on Phase 1 (GFF 2025 launch)
• Phase 1 features live: UPI ReservePay, Biometric UPI, Multisignatory UPI, UPI IoT Circle
• Phase 2 MVP: Enhanced orchestration layer with AI-assist triggers + expanded merchant categories
• Sandbox environment: Live on NPCI developer portal with 12 PSPs onboarded for testing

Pilot Partners: 3 anchor merchants (Zomato, Uber, one public utility), 2 issuer banks (HDFC, SBI)
Timeline: 8-week pilot → review → expand to 25 merchants → full rollout

Data Generated for Insights:
• Block creation-to-execution conversion rates (target: >85%)
• Checkout time reduction (baseline: 28s; target: <12s)
• False decline rate (target: <0.5%)
• Dispute/chargeback rates per merchant category
• Account type adoption mix (CASA vs Credit vs Prepaid)
• AI trigger accuracy for automated payments`;
}

function generateProductOperatingSection(_prompt: string, _name: string): string {
  return `3 Success KPIs:
1. ADOPTION: 5+ anchor merchants live (top food commerce + mobility + utility) within 6 months of launch
2. SCALE: 10M+ transactions/month within 12 months; top 5 issuer banks enabled within 3 months
3. QUALITY: Checkout success rate >94%; average transaction time <10 seconds; dispute rate <0.3%

Grievance Redressal (Trust):
• ODR (UDIR) integration: All disputes auto-routed with T+1 resolution SLA
• Dedicated PM hotline for anchor merchant issue escalation
• 24x7 ops monitoring: Real-time dashboard for transaction anomalies
• Customer notification: SMS + in-app push for every payment lifecycle event
• Reconciliation support: Automated daily MIS to issuers for block reconciliation
• Fraud response: Immediate block freeze on fraud signal; customer notification within 5 mins

Operating Cadence:
• Weekly: PSP adoption tracker + merchant feedback loop
• Monthly: NPCI executive review + RBI regulatory reporting
• Quarterly: Ecosystem health scorecard + roadmap recalibration`;
}

function generateProductCommsSection(_prompt: string, _name: string): string {
  return `Product Communications (External + Internal):

1. Product Demo: Polished end-to-end demo video (3-5 min) showcasing merchant + customer journeys
   → Available on NPCI website + shared with ecosystem partners

2. Product Video: 90-second explainer for general audience
   → Multi-language versions (Hindi, English, 6 regional languages)

3. Explanation Video by PM: Deep-dive technical walkthrough for PSP/bank integrators
   → Shared via NPCI developer portal + ecosystem newsletter

4. FAQs + Trained LLM:
   → 50+ FAQs covering customer, merchant, bank, and PSP perspectives
   → LLM trained on product documentation; deployed on NPCI website chatbot
   → Available at NPCI helpdesk for ecosystem queries

5. Circular (Operational Circular):
   → Draft circular to all UPI member banks and PSPs
   → Includes: Technical specs, compliance requirements, go-live checklist, support contacts
   → Timeline: 30 days before production launch

6. Product Document (Full Specs):
   → API documentation with sample requests/responses
   → Integration guide with test cases and UI/UX guidelines
   → Security requirements per RBI Master Direction 12032`;
}

function generatePricingSection(_prompt: string, _name: string): string {
  return `3-Year Pricing & Revenue View:

Current Pricing Framework:
• Existing UPI merchant discount rate (MDR) structure applies as baseline
• For Credit Account transactions: Interchange-based pricing (0.25-0.40% per transaction)
• For CASA transactions: Zero MDR (government mandate); ecosystem sustainability via switch fee

Phase 2 Incremental Revenue:
Year 1: Volume-led; focus on adoption over monetization. Est. ₹15-20 Cr switch fees
Year 2: Introduce tiered pricing for AI-triggered/high-value transactions. Est. ₹60-80 Cr
Year 3: Full product suite pricing including analytics APIs, fraud scores. Est. ₹150-200 Cr

Market Ability to Pay:
• LARGE MERCHANTS (Zomato, Uber): High WTP — operational savings (reduced cancellations, reconciliation automation) offset fees
• SMEs/MSMEs: Price-sensitive; require zero or low MDR for adoption; cross-subsidize via large merchant pricing
• Banks/Issuers: Revenue opportunity from credit penetration & float; positive NPV on integration investment

Open Items:
• CASA issuers requesting separate commercial framework for new capabilities
• Need RBI clarity on MDR exemptions for specific categories
• B2B pricing to be defined post-pilot data analysis`;
}

function generateRisksSection(_prompt: string, _name: string): string {
  return `Fraud & Abuse:
• Risk: Misuse of block payloads; rogue merchant creation of unauthorized blocks
• Mitigation: DSC validation for all block creation APIs; NPCI risk scoring for merchant onboarding; two-step customer authentication for high-value blocks (>₹10,000); real-time fraud model scoring on each debit trigger
• AI-Specific Risk: AI agents triggering payments without sufficient customer oversight
• Mitigation: "Human-in-loop" confirmation for AI-triggered payments above configurable threshold; audit trail for all AI-initiated transactions per RBI guidelines

Infosec & Privacy:
• Risk: PII exposure in transaction metadata; MITM attacks on API calls
• Mitigation: End-to-end encryption (TLS 1.3+); PII tokenization in all logs; access controls per RBI Master Direction 12032; penetration testing before each major release

Operational:
• Risk: Core banking system latency causing block reconciliation failures
• Mitigation: Async reconciliation with idempotency keys; automated retry with exponential backoff; real-time ops dashboard

Regulatory:
• Risk: RBI guideline changes on AI-triggered payments or block duration limits
• Mitigation: Active engagement with RBI payments policy team; modular architecture allowing rapid parameter changes without deployment

Adoption Risk:
• Risk: Low merchant uptake due to integration complexity
• Mitigation: Pre-built SDKs for top platforms; dedicated integration support team; sandbox-first approach; financial incentives for early adopters`;
}

function generateComplianceSection(_prompt: string, _name: string): string {
  return `Must-Have Compliances:

RBI Master Direction 12032 (Digital Payment Security Controls):
✓ Multi-factor authentication for all payment initiations
✓ End-to-end encryption for API communications
✓ Audit trails for all transaction lifecycle events
✓ Fraud monitoring and anomaly detection systems
✓ Incident reporting within stipulated RBI timelines

RBI Notification 1888 (Payment Instruments & Interoperability):
✓ Full KYC compliance for all participating accounts
✓ Grievance redressal pathway through UPI dispute framework
✓ Transaction limit adherence per RBI category guidelines
✓ Customer notification for all debits and block lifecycle events

NPCI Operational Circular (OC 228 — UPI Reserve Pay):
✓ Block and duration limits adherence as defined
✓ Mandatory customer notifications: Creation, execution, modification, revoke, expiry
✓ Merchant eligibility: Online-verified merchants only for block-based payments
✓ Reconciliation: Daily automated MIS to NPCI and issuer banks

Data Protection:
✓ Compliance with IT Act 2000 and DPDP Act 2023 (Digital Personal Data Protection)
✓ Data residency: All transaction data stored within India
✓ Consent management: Granular customer consent for AI-triggered payments
✓ Right to erasure implementation for personal data linked to expired mandates`;
}

function generateEcosystemChallenges(_prompt: string, _name: string): string {
  return `Payer Apps & Payee PSPs: Currently performing internal testing and integration for Credit line accounts, RCC accounts, and CASA before full rollout to customers across Android and iOS versions. SDK versioning complexity with 15+ active app versions in market requiring backward compatibility.

Issuer Banks: Core banking system upgrades required for real-time block accounting; public sector banks averaging 12-16 weeks for CBS integration. Float accounting treatment for blocked funds requires RBI clarification.

Merchant Integration: Large merchants have dedicated tech teams but mid-market merchants lack internal capability; need for plug-and-play payment gateway integration. Webhook reliability at peak load (sale events) remains a concern.

Regulatory Uncertainty: Awaiting final RBI guidelines on AI-triggered payment authorizations and liability framework for automated payments. Expected clarification in Q2 2026 sandbox framework release.`;
}

export function generateDocuments(canvas: CanvasData): Document[] {
  // Return standard NPCI-compliant product documentation

  return [
    {
      id: 'product-doc',
      title: 'Product Document',
      icon: '📋',
      approved: false,
      lastEdited: new Date().toLocaleDateString(),
      content: generateProductDoc(canvas),
    },
    {
      id: 'circular',
      title: 'Operational Circular',
      icon: '📜',
      approved: false,
      lastEdited: new Date().toLocaleDateString(),
      content: generateCircular(canvas),
    },
    {
      id: 'faqs',
      title: 'FAQs',
      icon: '❓',
      approved: false,
      lastEdited: new Date().toLocaleDateString(),
      content: generateFAQs(canvas),
    },
    {
      id: 'video-script',
      title: 'Product Video Script',
      icon: '🎬',
      approved: false,
      lastEdited: new Date().toLocaleDateString(),
      content: generateVideoScript(canvas),
    },
    {
      id: 'rbi-summary',
      title: 'RBI Guidelines Summary',
      icon: '🏛️',
      approved: false,
      lastEdited: new Date().toLocaleDateString(),
      content: generateRBISummary(canvas),
    },
    {
      id: 'test-cases',
      title: 'Test Cases',
      icon: '🧪',
      approved: false,
      lastEdited: new Date().toLocaleDateString(),
      content: generateTestCases(canvas),
    },
  ];
}

function generateProductDoc(canvas: CanvasData): string {
  return `# ${canvas.featureName} — Product Document
**Version:** 1.0 | **Date:** ${new Date().toLocaleDateString('en-IN')} | **Status:** Draft

---

## 1. Executive Summary
${canvas.sections[0].content.split('\n')[2] || 'This document provides comprehensive product specifications for ' + canvas.featureName + '.'}

## 2. Product Overview

### 2.1 Feature Description
${canvas.sections[0].content}

### 2.2 Business Need
${canvas.sections[1].content}

---

## 3. Technical Specifications

### 3.1 API Endpoints

**Create Block / Initiate Transaction**
\`\`\`
POST /api/v2/upi/transaction/create
Authorization: Bearer {token}
Content-Type: application/json

{
  "merchantId": "MERCH001",
  "customerId": "CUST123",
  "amount": 5000,
  "currency": "INR",
  "purpose": "PURCHASE",
  "validUpto": "2026-06-30",
  "authMode": "BIOMETRIC|PIN"
}
\`\`\`

**Execute / Debit**
\`\`\`
POST /api/v2/upi/transaction/execute
{
  "transactionId": "TXN20260323001",
  "amount": 1200,
  "triggerType": "MERCHANT|AI_AGENT",
  "serviceDeliveryProof": "ORDER_ID_XYZ"
}
\`\`\`

**Revoke**
\`\`\`
DELETE /api/v2/upi/transaction/{transactionId}
\`\`\`

### 3.2 Response Codes
| Code | Description |
|------|-------------|
| 00 | Success |
| U69 | Block limit exceeded |
| U70 | Block expired |
| U71 | Insufficient funds |
| U72 | Customer revoked |
| U73 | Merchant not authorized |

### 3.3 Security Requirements
- TLS 1.3+ for all API communications
- DSC validation for block creation
- HMAC-SHA256 request signing
- Rate limiting: 100 requests/min per merchant

---

## 4. User Journeys

### Journey 1: Customer Creates Block
1. Customer opens UPI app → Merchant payment screen
2. Selects "Reserve & Pay Later" option
3. Enters amount and validity period
4. Authenticates via PIN/Biometric
5. Block created → Customer receives SMS + push notification
6. Block ID shown to customer for reference

### Journey 2: Merchant Triggers Debit
1. Merchant backend receives service delivery confirmation
2. Calls UPI Execute API with transaction ID + delivery proof
3. NPCI validates block, balance, and merchant eligibility
4. Debit processed → Both parties notified in real-time
5. Available balance updated on customer app

### Journey 3: Customer Revokes Block
1. Customer views active blocks in UPI app
2. Selects block → Clicks "Revoke"
3. Confirms via PIN
4. Block released → Full amount restored to available balance
5. Merchant notified via webhook

---

## 5. UI/UX Guidelines

### Customer App
- New "Active Reserves" section in UPI app home screen
- Block creation flow: max 3 taps
- Visual indicator for blocked vs available balance
- Push notification design: Clear merchant name, amount, purpose

### Merchant Dashboard
- Real-time block status view
- One-click debit trigger with delivery proof attachment
- Daily reconciliation report download

---

## 6. Test Cases
See separate Test Cases document.

---

## 7. Compliance & Security
${canvas.sections[9].content}

---

## 8. Rollout Plan
**Phase A (Weeks 1-4):** Sandbox integration for anchor merchants
**Phase B (Weeks 5-8):** Controlled pilot (3 merchants, 2 banks)
**Phase C (Weeks 9-16):** Expanded pilot (25 merchants)
**Phase D (Week 17+):** Full production rollout

---

*Document Owner: Product Management, NPCI | Confidential*`;
}

function generateCircular(canvas: CanvasData): string {
  const dateStr = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' });
  return `NATIONAL PAYMENTS CORPORATION OF INDIA
UNIFIED PAYMENTS INTERFACE

OPERATIONAL CIRCULAR — DRAFT
OC No.: [TO BE ASSIGNED] | Date: ${dateStr}

SUBJECT: Implementation Guidelines for ${canvas.featureName}

---

To,
All UPI Member Banks,
All Third-Party Application Providers (TPAPs),
All Payment Service Providers (PSPs)

Dear Sir/Madam,

1. BACKGROUND

1.1 NPCI has been continuously enhancing the UPI ecosystem in alignment with RBI's Payments Vision 2025 and the Digital India initiative. Building on the successful launch of UPI ReservePay, Biometric Payments, Multisignatory UPI, and UPI Circle for IoT at GFF 2025, NPCI is pleased to announce Phase 2 enhancements under the ${canvas.featureName} framework.

1.2 This Operational Circular provides mandatory implementation guidelines for all ecosystem participants.

2. SCOPE

This circular is applicable to:
a) All UPI member banks (Payer PSPs and Payee PSPs)
b) Third-Party Application Providers (TPAPs) certified by NPCI
c) Payment aggregators and payment gateways integrated with UPI

3. KEY FEATURES

3.1 ${canvas.featureName} enables:
• Enhanced payment orchestration with AI-assist triggers
• Expanded block-based payment use cases
• Improved interoperability across payment instruments
• Real-time reconciliation and notification framework

4. COMPLIANCE REQUIREMENTS

4.1 Security: All participants must comply with RBI Master Direction on Digital Payment Security Controls (RBI/2020-21/68).

4.2 Customer Notifications: Mandatory notifications for all payment lifecycle events (creation, execution, modification, revocation, expiry) via SMS and in-app push.

4.3 Block Limits: As per schedule attached. Current limits applicable until further notice.

4.4 Merchant Eligibility: Only NPCI-approved online merchants permitted for block-based debit triggers.

4.5 Reconciliation: Daily automated MIS submission to NPCI by 07:00 IST.

5. IMPLEMENTATION TIMELINE

• Date of Circular: ${dateStr}
• Sandbox Availability: T+15 days
• Controlled Pilot: T+30 days
• Full Production: T+90 days

6. GO-LIVE CHECKLIST

☐ SDK integration and certification on NPCI UAT
☐ Security audit completion and certificate submission
☐ Customer notification template approval
☐ Reconciliation API integration
☐ Dispute management workflow testing
☐ Staff training completion certificate

7. SUPPORT

Technical Queries: upi-integration@npci.org.in
Operational Queries: upi-ops@npci.org.in
Emergency Escalation: NPCI Operations Center — 1800-XXX-XXXX

This circular supersedes any conflicting provisions in earlier circulars on related subjects.

For National Payments Corporation of India,

[Chief Product Officer]
[Chief Operating Officer]

---
*DRAFT — Subject to review and approval*`;
}

function generateFAQs(canvas: CanvasData): string {
  return `# ${canvas.featureName} — Frequently Asked Questions (FAQs)
**Version:** 1.0 | **Audience:** Customers, Merchants, Banks, PSPs

---

## FOR CUSTOMERS

**Q1. What is ${canvas.featureName}?**
A: ${canvas.featureName} is an enhanced UPI capability that allows you to make smarter, faster, and more secure payments. It builds on existing UPI features to provide seamless payment experiences for everyday transactions.

**Q2. Is my money safe?**
A: Absolutely. Your funds remain in your bank account until the actual payment is triggered. All transactions require your explicit authentication. NPCI's fraud monitoring systems protect every transaction 24/7.

**Q3. How do I enable this feature?**
A: Update your UPI app to the latest version. The feature will be available automatically for eligible transactions. No additional registration required.

**Q4. What if I want to cancel a pending transaction?**
A: You can revoke any pending payment from within your UPI app under "Active Payments" → Select payment → "Revoke". Funds are released immediately.

**Q5. Will I receive notifications?**
A: Yes. You will receive SMS and in-app notifications for every payment event: creation, execution, modification, and cancellation.

**Q6. What are the transaction limits?**
A: Standard UPI transaction limits apply. For enhanced features, limits are as per your bank's policy. Check with your bank for specific limits.

**Q7. What if there's a dispute?**
A: Raise a dispute through your UPI app or bank app. All disputes are processed through NPCI's UDIR (UPI Dispute & Issue Resolution) system with T+1 resolution SLA.

---

## FOR MERCHANTS

**Q8. How do I integrate ${canvas.featureName}?**
A: Download the latest NPCI UPI SDK from the developer portal (developer.npci.org.in). Integration guide, sample code, and sandbox credentials are available.

**Q9. What are the merchant eligibility criteria?**
A: NPCI-verified online merchants are eligible. You must complete NPCI's merchant onboarding process, including KYB (Know Your Business) verification.

**Q10. How quickly are payments settled?**
A: Standard UPI settlement timelines apply: T+1 for regular settlements. Real-time settlement available for eligible merchants.

**Q11. How do I handle reconciliation?**
A: NPCI provides automated daily reconciliation reports. API-based reconciliation is also available for real-time integration with your accounting systems.

**Q12. What happens if a customer revokes a payment?**
A: You will receive a webhook notification immediately upon revocation. Ensure your order management system handles revocation events gracefully.

---

## FOR BANKS & PSPS

**Q13. What technical changes are required?**
A: Core banking system integration for new transaction types, webhook endpoint implementation, and customer notification system updates. Full technical specs in the Integration Guide.

**Q14. What is the timeline for implementation?**
A: Sandbox: Available T+15 days from circular. Production: T+90 days (mandatory for all member banks).

**Q15. How are blocks accounted in available balance?**
A: Blocked amounts are deducted from available balance in real-time. Detailed accounting guidelines available in the technical annexure to this circular.

**Q16. What security certifications are required?**
A: ISO 27001, PCI-DSS (where applicable), and NPCI security audit completion. All as per RBI Master Direction 12032.

---

## TRAINED LLM INTEGRATION NOTE

*This FAQ document is used to train the NPCI UPI Assistant chatbot. The LLM is available at npci.org.in/upi-assistant and can answer questions about ${canvas.featureName} in real-time.*`;
}

function generateVideoScript(canvas: CanvasData): string {
  return `# ${canvas.featureName} — Product Video Script
**Duration:** 90 seconds | **Format:** Animated explainer | **Languages:** English + Hindi

---

## SCENE 1: HOOK (0-10 seconds)
[VISUAL: Split screen — frustrated customer at checkout vs. seamless payment]

NARRATOR (V.O.):
"Making payments in India has never been easier. But what if it could be even smarter?"

---

## SCENE 2: PROBLEM (10-25 seconds)
[VISUAL: Customer trying to pay, multiple steps, complexity shown]

NARRATOR (V.O.):
"Today, millions of Indians make dozens of digital payments every day. But complex transactions still require too many steps, too much time."

STATS ON SCREEN:
• 14+ billion UPI transactions per month
• Average checkout time: 28 seconds
• 18% cart abandonment during payment

---

## SCENE 3: SOLUTION INTRODUCTION (25-45 seconds)
[VISUAL: NPCI logo appears, UPI animation, feature name revealed]

NARRATOR (V.O.):
"Introducing ${canvas.featureName} — the next evolution of UPI payments. Powered by NPCI. Backed by the Reserve Bank of India."

[VISUAL: Key features appearing as icons]
✓ Smarter authentication
✓ Faster transactions
✓ Enhanced security
✓ Works with your existing UPI app

---

## SCENE 4: HOW IT WORKS (45-70 seconds)
[VISUAL: Animated user journey — 3 simple steps]

NARRATOR (V.O.):
"It's simple. Step 1: Open your UPI app and select your payment. Step 2: Authenticate once with your PIN or fingerprint. Step 3: Pay instantly — every time."

[VISUAL: Customer smiling, transaction complete in 3 seconds]

"Your money stays safe in your account until you choose to pay. Complete control. Zero friction."

---

## SCENE 5: USE CASES (70-80 seconds)
[VISUAL: Montage — ordering food, booking cab, shopping online, paying bills]

NARRATOR (V.O.):
"Use it for food delivery, mobility, subscriptions, shopping, and more. ${canvas.featureName} works wherever UPI is accepted."

---

## SCENE 6: CALL TO ACTION (80-90 seconds)
[VISUAL: NPCI logo, UPI logo, "Update your app today"]

NARRATOR (V.O.):
"Update your UPI app today and experience the future of payments. ${canvas.featureName} — by NPCI, for India."

[END CARD]
Website: npci.org.in | UPI Help: 1800-XXX-XXXX | @NPCI_NPCI

---

## PRODUCTION NOTES
- Animation style: Modern flat design, consistent with UPI brand guidelines
- Color palette: UPI indigo (#4F2D7F) + white + accent orange
- Music: Upbeat, modern, 90 BPM
- Languages: English master + Hindi voice-over + 6 regional language subtitles
- Delivery: MP4 (1080p + 4K), optimized for social media, YouTube, broadcast`;
}

function generateRBISummary(canvas: CanvasData): string {
  return `# RBI Guidelines Summary for ${canvas.featureName}
**Compiled:** ${new Date().toLocaleDateString('en-IN')} | **Confidential — Internal Use**

---

## 1. PRIMARY APPLICABLE GUIDELINES

### 1.1 Master Direction on Digital Payment Security Controls
**Reference:** RBI/2020-21/68, February 18, 2021 (Notification ID: 12032)

**Key Provisions Applicable to ${canvas.featureName}:**

**Security Architecture:**
• Multi-factor authentication (MFA) mandatory for payment initiation
• All APIs must use TLS 1.3 or higher
• Certificate-based authentication for server-to-server communications
• End-to-end encryption for customer data in transit and at rest

**Fraud Management:**
• Real-time fraud scoring on all transactions
• Velocity checks and behavioral analytics
• Immediate blocking capability for compromised credentials
• Mandatory fraud reporting to RBI within 6 hours of detection

**Audit & Compliance:**
• Complete audit trail for all transaction lifecycle events (minimum 5-year retention)
• Access controls with privilege separation
• Regular security assessments (minimum quarterly)
• Third-party security audit before major feature launches

**Customer Protection:**
• Customers must receive notifications for all debits
• Cooling-off period available for dispute filing
• Right to revoke mandates/blocks must be preserved at all times

---

### 1.2 Payment Instruments & UPI Interoperability
**Reference:** RBI Notification 1888

**Key Provisions:**
• All UPI features must maintain full interoperability across NPCI-registered PSPs
• KYC requirements: Full KYC for transactions above ₹10,000; enhanced due diligence for new merchant types
• Consumer grievance: 30-day resolution window; banking ombudsman escalation pathway
• Limit framework: Category-specific limits to be adhered to; any increase requires RBI approval

---

### 1.3 UPI Single Block Multiple Debits (SBMD)
**Reference:** RBI Press Release (December 2022) + NPCI OC 228

**Specific Provisions for Block-Based Payments:**
• Single authorization for multiple debits: Explicitly permitted
• Block duration: As per issuer policy; maximum duration per RBI guidelines
• Mandatory notifications: All lifecycle events (create, execute, modify, revoke, expire)
• Service delivery requirement: Debit to occur only post-service delivery confirmation
• Merchant restrictions: Online-verified merchants only; risk-based eligibility screening
• Consumer right: Unconditional right to revoke at any time before debit
• Dispute resolution: Special ODR pathway for block-based disputes

---

## 2. COMPLIANCE CHECKLIST

| Requirement | Regulatory Source | Status | Owner |
|------------|------------------|--------|-------|
| MFA implementation | RBI 12032 | ✅ In Design | Tech Lead |
| TLS 1.3 APIs | RBI 12032 | ✅ Done | Security |
| Customer notifications | NPCI OC 228 | 🔄 In Progress | Product |
| Block duration limits | NPCI OC 228 | ✅ Done | Product |
| Fraud monitoring | RBI 12032 | ✅ Done | Risk |
| KYC compliance | RBI 1888 | ✅ Done | Compliance |
| ODR integration | NPCI OC 228 | 🔄 In Progress | Ops |
| DPDP Act compliance | DPDP 2023 | 🔄 In Progress | Legal |
| Data residency (India) | IT Act 2000 | ✅ Done | Tech Lead |
| RBI audit trail | RBI 12032 | ✅ Done | Tech Lead |

---

## 3. OPEN REGULATORY ITEMS

1. **AI-Triggered Payments:** RBI yet to issue specific guidelines on AI agent-initiated UPI transactions. Recommend "human-in-loop" approach until guidelines issued (expected Q2 2026).

2. **Enhanced Limits for New Categories:** Awaiting RBI approval for higher per-transaction limits for specific B2B use cases.

3. **MDR Framework:** CASA MDR exemption applicability to new features requires RBI clarification.

---

## 4. REGULATORY ENGAGEMENT PLAN

• Q2 2026: Present feature design to RBI Payments Policy Department for pre-clearance
• Q3 2026: File formal approval request for any limit enhancements
• Ongoing: Monthly regulatory update calls with RBI DPSS (Department of Payment & Settlement Systems)

---

*Prepared by: Compliance Team, NPCI | Reviewed by: Legal Counsel | For internal circulation only*`;
}

function generateTestCases(canvas: CanvasData): string {
  return `# ${canvas.featureName} — Test Cases
**Version:** 1.0 | **Environment:** UAT → Production

---

## MODULE 1: TRANSACTION CREATION

| TC ID | Test Case | Input | Expected Output | Priority |
|-------|-----------|-------|-----------------|----------|
| TC_001 | Create transaction — happy path | Valid merchant, customer, amount | TXN_ID returned, status=ACTIVE | P0 |
| TC_002 | Create with insufficient funds | Amount > available balance | Error U71 — Insufficient funds | P0 |
| TC_003 | Create with expired customer VPA | Invalid VPA | Error U07 — Invalid VPA | P0 |

---

## MODULE 2: TRANSACTION EXECUTION (DEBIT)

| TC ID | Test Case | Input | Expected Output | Priority |
|-------|-----------|-------|-----------------|----------|
| TC_101 | Execute debit — full amount | Valid TXN_ID, full block amount | Debit success, TXN_STATUS=COMPLETED | P0 |
| TC_102 | Execute partial debit | Amount < block amount | Partial debit, remaining balance retained | P0 |
| TC_103 | Execute on revoked block | Revoked TXN_ID | Error U72 — Customer revoked | P0 |

---

## MODULE 3: REVOCATION

| TC ID | Test Case | Input | Expected Output | Priority |
|-------|-----------|-------|-----------------|----------|
| TC_201 | Customer revokes active block | Valid TXN_ID, customer auth | Success, funds restored | P0 |
| TC_202 | Revoke after partial debit | Partially debited block | Success, remaining amount restored | P0 |

---

## MODULE 4: NOTIFICATIONS

| TC ID | Test Case | Expected Notification | Channel | SLA |
|-------|-----------|--------------------|---------|-----|
| TC_301 | Block created | "₹X blocked for [Merchant] valid till [Date]" | SMS + Push | <5s |

---

## MODULE 5: SECURITY & FRAUD

| TC ID | Test Case | Expected Behavior | Priority |
|-------|-----------|------------------|----------|
| TC_401 | DSC validation failure | Reject block creation | P0 |

---

*Test execution by: QA Team + Security Team | Sign-off required before UAT → Production promotion*`;
}

/* ─── Technical Plan: BRD + TSD ───────────────────────────────────────────── */

export function generateBRD(canvas: CanvasData): string {
  const n = canvas.featureName;
  const date = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' });
  const sec = canvas.sections;
  const featureContent   = sec.find(s => s.title === 'Feature')?.content   || '';
  const needContent      = sec.find(s => s.title === 'Need')?.content      || '';
  const marketContent    = sec.find(s => s.title === 'Market View')?.content || '';
  const scaleContent     = sec.find(s => s.title === 'Scalability')?.content || '';
  const validContent     = sec.find(s => s.title === 'Validation')?.content  || '';
  const opsContent       = sec.find(s => s.title === 'Product Operating')?.content || '';
  const pricingContent   = sec.find(s => s.title === 'Pricing')?.content    || '';
  const complianceContent= sec.find(s => s.title === 'Compliance')?.content || '';

  // Codebase analysis
  const codePlan = getCodePlan(canvas);
  const filesTouched = getFilesTouched(codePlan);
  const totalLines = getTotalLinesAffected(codePlan);
  const layerSummary = getLayerSummary(codePlan);

  return `# Business Requirements Document (BRD)
## ${n}

**Document Version:** 1.0
**Status:** Draft — Pending PM Approval
**Date:** ${date}
**Prepared by:** NPCI Product Management
**Reviewed by:** [To be filled]
**Approved by:** [Pending]

---

## 1. EXECUTIVE SUMMARY

This Business Requirements Document captures the end-to-end business requirements for **${n}**. It establishes the business context, stakeholder needs, functional and non-functional requirements, and acceptance criteria required for successful delivery.

${featureContent.split('\n').slice(0, 6).join('\n')}

---

## 2. BUSINESS CONTEXT

### 2.1 Problem Statement

${needContent.split('\n').slice(0, 8).join('\n')}

### 2.2 Strategic Alignment

- **RBI Payments Vision 2025** — Explicitly supports programmable money and AI-assisted payment orchestration
- **NPCI Volume Target** — 1 billion UPI transactions/day by 2026
- **Digital India** — Financial inclusion and frictionless payment for all citizen segments

### 2.3 Business Objectives

| # | Objective | Success Metric | Target Date |
|---|-----------|---------------|-------------|
| BO-1 | Launch to market with anchor merchants | 5+ merchants live | 6 months from approval |
| BO-2 | Achieve transaction scale | 10M+ txns/month | 12 months from launch |
| BO-3 | Maintain quality | Checkout success >94% | Ongoing |
| BO-4 | Ensure compliance | Zero RBI findings | Ongoing |

---

## 3. STAKEHOLDERS

| Stakeholder | Role | Interest | Impact |
|-------------|------|----------|--------|
| NPCI Product Team | Owner | Feature design & delivery | High |
| RBI DPSS | Regulator | Compliance & consumer protection | High |
| Issuer Banks (SBI, HDFC, ICICI) | Technology partner | Balance management, KYC | High |
| PSP Apps (PhonePe, GPay, Paytm) | Distribution | SDK integration, UX | High |
| Merchants (Zomato, Uber) | Demand side | Revenue uplift, reduced abandonment | High |
| End Customers | Users | Ease of use, security | High |
| NPCI Operations | Support | System reliability, MIS reporting | Medium |

---

## 4. MARKET OPPORTUNITY

${marketContent.split('\n').slice(0, 12).join('\n')}

### 4.1 Scale Potential

${scaleContent.split('\n').slice(0, 10).join('\n')}

---

## 5. FUNCTIONAL REQUIREMENTS

### 5.1 Core Features (Must Have — P0)

| FR-ID | Requirement | Stakeholder | Priority |
|-------|-------------|-------------|----------|
| FR-001 | System must support single-authorization block creation via UPI | Customer, Issuer | P0 |
| FR-002 | Multiple partial debits up to blocked amount must be supported | Merchant, Issuer | P0 |
| FR-003 | Customer must be able to revoke blocks at any time pre-debit | Customer | P0 |
| FR-004 | Real-time customer notification for every lifecycle event | Customer, Regulator | P0 |
| FR-005 | Merchant eligibility verification before block acceptance | NPCI, Regulator | P0 |
| FR-006 | DSC validation on all block creation API calls | Security, Regulator | P0 |
| FR-007 | Block expiry with customer notification at T-3 days and expiry | Customer | P0 |
| FR-008 | UDIR dispute integration for unauthorized debits | Customer, Regulator | P0 |
| FR-009 | Daily MIS report generation and NPCI submission by 07:00 IST | Operations, Regulator | P0 |
| FR-010 | Full KYC check for transactions above ₹10,000 | Regulator (RBI 1888) | P0 |

### 5.2 Enhanced Features (Should Have — P1)

| FR-ID | Requirement | Stakeholder | Priority |
|-------|-------------|-------------|----------|
| FR-011 | AI-agent triggered debit with human-in-loop confirmation above threshold | Customer | P1 |
| FR-012 | Multi-language customer notifications (6 regional languages) | Customer | P1 |
| FR-013 | Merchant webhook for revocation and expiry events | Merchant | P1 |
| FR-014 | Real-time available balance reflecting blocked amounts | Customer | P1 |
| FR-015 | Analytics API for merchant-level block statistics | Merchant | P1 |

### 5.3 Future Features (Could Have — P2)

| FR-ID | Requirement | Description |
|-------|-------------|-------------|
| FR-016 | Biometric delegation | Allow delegated payment via biometric from linked accounts |
| FR-017 | Cross-border UPI | Extend block-based model to international UPI corridors |
| FR-018 | Credit line blocks | Block against credit line, not just CASA |

---

## 6. NON-FUNCTIONAL REQUIREMENTS

| NFR-ID | Category | Requirement | Target |
|--------|----------|-------------|--------|
| NFR-001 | Performance | Transaction processing latency | < 3 seconds end-to-end |
| NFR-002 | Availability | System uptime | 99.95% monthly |
| NFR-003 | Scalability | Peak transaction throughput | 10,000 TPS sustained |
| NFR-004 | Security | API authentication | TLS 1.3 + DSC + HMAC-SHA256 |
| NFR-005 | Reliability | Idempotency | Duplicate requests return same result |
| NFR-006 | Auditability | Transaction log retention | Minimum 5 years (RBI 12032) |
| NFR-007 | Privacy | PII handling | Masked in all logs; DPDP Act 2023 compliant |
| NFR-008 | Recoverability | RTO | < 15 minutes for critical paths |
| NFR-009 | Compliance | Fraud detection | Real-time scoring < 500ms |
| NFR-010 | Observability | Monitoring & alerting | 24x7 ops dashboard with anomaly alerts |

---

## 7. VALIDATION APPROACH (MVP & PILOT)

${validContent.split('\n').slice(0, 12).join('\n')}

---

## 8. BUSINESS OPERATING MODEL

${opsContent.split('\n').slice(0, 12).join('\n')}

---

## 9. COMMERCIAL MODEL

${pricingContent.split('\n').slice(0, 12).join('\n')}

---

## 10. COMPLIANCE & REGULATORY REQUIREMENTS

${complianceContent.split('\n').slice(0, 16).join('\n')}

---

## 11. ASSUMPTIONS & DEPENDENCIES

### Assumptions
- RBI does not issue contradictory guidelines before launch
- Top 5 issuer banks complete CBS integration within 16 weeks
- NPCI UAT environment available for PSP certification testing

### Dependencies
| Dependency | Owner | Status | Risk |
|------------|-------|--------|------|
| RBI guideline clarity on AI-triggered payments | RBI | Awaited | High |
| Issuer CBS upgrades | Banks | In Progress | Medium |
| PSP SDK certification | PSPs | Pending | Medium |
| NPCI UAT environment expansion | NPCI Tech | Planned | Low |

---

## 12. ACCEPTANCE CRITERIA

| AC-ID | Criterion | Test Method | Pass Condition |
|-------|-----------|-------------|----------------|
| AC-001 | Block creation completes successfully | Functional test TC_001 | HTTP 200 + TXN_ID returned |
| AC-002 | Partial debit works | Functional test TC_101/102 | Correct debit, balance updated |
| AC-003 | Revocation frees funds immediately | Functional test TC_201 | Balance restored within 5s |
| AC-004 | Notifications sent for all events | Integration test TC_301-305 | 100% delivery within SLA |
| AC-005 | Performance under load | Load test at 10,000 TPS | p95 latency < 3s |
| AC-006 | Security — no SQL injection | Security test TC_405 | Request rejected, alert raised |

---

## 12. CODEBASE IMPACT ANALYSIS — upi_hackathon_titans

> This section is auto-generated by analysing the existing UPI system codebase.

**Feature Type:** ${codePlan.featureType}

**Summary:** ${codePlan.summary}

### 12.1 Files Requiring Changes

| # | File | Layer | Change Type | Effort |
|---|------|-------|-------------|--------|
${codePlan.fileChanges.map((fc, i) => `| ${i + 1} | \`${fc.path}\` | ${fc.path.split('/')[0]} | ${fc.changeType} | ${fc.effort} |`).join('\n')}

**Total files touched:** ${filesTouched.length} | **Estimated lines changed:** ~${totalLines}
**Layer breakdown:** ${Object.entries(layerSummary).map(([l, n]) => `${l}: ${n}`).join(', ')}

### 12.2 New Files to Create

${codePlan.newFiles.length === 0 ? 'None required.' : codePlan.newFiles.map(nf => `- \`${nf.path}\` — ${nf.purpose}`).join('\n')}

### 12.3 New API Endpoints

${codePlan.newEndpoints.map(ep => `- ${ep}`).join('\n')}

### 12.4 Test Files

${codePlan.testFilePaths.map(tp => `- \`${tp}\``).join('\n')}

---

## 13. SIGN-OFF

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Chief Product Officer | | | |
| Chief Technology Officer | | | |
| Chief Risk Officer | | | |
| Chief Compliance Officer | | | |

---
*This document is confidential and intended for internal NPCI circulation only.*`;
}

export function generateTSD(canvas: CanvasData): string {
  const n = canvas.featureName;
  const date = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' });
  const codePlan = getCodePlan(canvas);
  const filesTouched = getFilesTouched(codePlan);

  return `# Technical Specification Document (TSD)
## ${n}

**Document Version:** 1.0
**Status:** Draft — Pending Architecture Review
**Date:** ${date}
**Prepared by:** NPCI Platform Engineering
**Architecture Lead:** [To be assigned]
**Security Review:** Pending

---

## 1. SYSTEM OVERVIEW

### 1.1 Architecture Pattern

\`\`\`
┌─────────────────────────────────────────────────────────┐
│                   CUSTOMER UPI APP                       │
│         (PhonePe / GPay / Paytm / BHIM)                 │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS / TLS 1.3
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  PAYER PSP LAYER                         │
│    • SDK integration  • Auth orchestration              │
│    • Customer UX      • Block management                │
└──────────────────────┬──────────────────────────────────┘
                       │ UPI XML over HTTPS (DSC-signed)
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   NPCI UPI SWITCH                        │
│   • Request routing   • Schema validation               │
│   • Block registry    • Fraud scoring                   │
│   • Idempotency mgr   • MIS aggregation                 │
└──────────────┬───────────────────────┬──────────────────┘
               │                       │
               ▼                       ▼
┌──────────────────────┐  ┌───────────────────────────────┐
│   ISSUER BANK CBS    │  │     PAYEE PSP / MERCHANT       │
│  • Block accounting  │  │  • Debit trigger API           │
│  • Balance updates   │  │  • Service delivery proof      │
│  • Customer notifs   │  │  • Reconciliation webhooks     │
└──────────────────────┘  └───────────────────────────────┘
\`\`\`

### 1.2 Technology Stack

| Component | Technology | Version | Notes |
|-----------|-----------|---------|-------|
| API Gateway | NPCI internal | v3.x | Rate limiting, auth |
| Core Switch | Java 17 + Spring Boot | 3.x | High-throughput processing |
| Block Registry | PostgreSQL 15 | Clustered | ACID compliance required |
| Notification Engine | Apache Kafka | 3.5 | Async event processing |
| Cache Layer | Redis Cluster | 7.x | Session + idempotency |
| Fraud Engine | Python 3.11 + ML model | — | Real-time scoring < 500ms |
| Monitoring | Prometheus + Grafana | — | 24x7 ops dashboard |
| Logging | ELK Stack | — | 5-year retention |

---

## 2. API SPECIFICATIONS

### 2.1 XML Schema — Block Creation (ReqPay with Block)

\`\`\`xml
<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqPay xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="2.0" ts="{ISO8601}" orgId="{PSP_ID}"
            msgId="{UNIQUE_MSG_ID}" prodType="UPI"/>
  <upi:Txn id="{TXN_ID}" type="BLOCK_DEBIT"
           note="{PURPOSE}" refUrl="{MERCHANT_REF}"/>
  <upi:Block amount="{BLOCK_AMOUNT}" validUpto="{EXPIRY_ISO}"
             purpose="{PURPOSE_CODE}" authMode="{PIN|BIOMETRIC}"/>
  <upi:Payer addr="{CUSTOMER_VPA}">
    <upi:Amount value="{BLOCK_AMOUNT}"/>
    <upi:Creds>
      <upi:Cred type="{AUTH_TYPE}">
        <upi:Data code="{AUTH_DATA}" ki="{KI_VALUE}"/>
      </upi:Cred>
    </upi:Creds>
  </upi:Payer>
  <upi:Payees>
    <upi:Payee addr="{MERCHANT_VPA}" amount="{BLOCK_AMOUNT}"/>
  </upi:Payees>
</upi:ReqPay>
\`\`\`

### 2.2 XML Schema — Execute Debit (ReqPay Debit Trigger)

\`\`\`xml
<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqDebit xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="2.0" ts="{ISO8601}" orgId="{MERCHANT_PSP}"
            msgId="{DEBIT_MSG_ID}" prodType="UPI"/>
  <upi:Txn id="{DEBIT_TXN_ID}" type="EXECUTE_DEBIT"
           blockRef="{ORIGINAL_BLOCK_TXN_ID}"/>
  <upi:Amount value="{DEBIT_AMOUNT}"/>
  <upi:ServiceProof orderId="{ORDER_ID}" deliveredAt="{ISO8601}"/>
</upi:ReqDebit>
\`\`\`

### 2.3 XML Schema — Revoke Block

\`\`\`xml
<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqRevoke xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="2.0" ts="{ISO8601}" orgId="{PSP_ID}"
            msgId="{REVOKE_MSG_ID}" prodType="UPI"/>
  <upi:Txn id="{ORIGINAL_BLOCK_TXN_ID}" type="REVOKE_BLOCK"/>
  <upi:Creds>
    <upi:Cred type="{AUTH_TYPE}">
      <upi:Data code="{AUTH_DATA}"/>
    </upi:Cred>
  </upi:Creds>
</upi:ReqRevoke>
\`\`\`

### 2.4 Response Codes

| Code | Meaning | HTTP | Recovery |
|------|---------|------|----------|
| 00 | SUCCESS | 200 | — |
| U06 | Transaction not permitted | 403 | Do not retry |
| U07 | Invalid VPA | 400 | Fix VPA, retry |
| U09 | Requested entity not available | 404 | Retry after delay |
| U16 | Risk threshold exceeded | 403 | Customer action needed |
| U69 | Block limit exceeded | 422 | Reduce amount |
| U70 | Block expired | 410 | Create new block |
| U71 | Insufficient funds | 422 | Customer action needed |
| U72 | Customer revoked | 410 | Do not retry |
| U73 | Merchant not authorized | 403 | Verify merchant eligibility |
| U90 | Internal system error | 500 | Retry with backoff |

---

## 3. DATA MODELS

### 3.1 Block Entity

\`\`\`sql
CREATE TABLE upi_blocks (
  block_id          VARCHAR(64)    PRIMARY KEY,
  txn_id            VARCHAR(64)    NOT NULL UNIQUE,
  customer_vpa      VARCHAR(100)   NOT NULL,
  merchant_vpa      VARCHAR(100)   NOT NULL,
  payer_psp_id      VARCHAR(20)    NOT NULL,
  payee_psp_id      VARCHAR(20)    NOT NULL,
  issuer_bank_code  VARCHAR(10)    NOT NULL,
  blocked_amount    DECIMAL(15,2)  NOT NULL CHECK(blocked_amount > 0),
  available_amount  DECIMAL(15,2)  NOT NULL,
  currency          CHAR(3)        NOT NULL DEFAULT 'INR',
  purpose_code      VARCHAR(20),
  auth_mode         VARCHAR(20)    NOT NULL,
  status            VARCHAR(20)    NOT NULL CHECK(status IN (
                      'ACTIVE','PARTIALLY_DEBITED','FULLY_DEBITED',
                      'REVOKED','EXPIRED','SUSPENDED')),
  valid_upto        TIMESTAMPTZ    NOT NULL,
  created_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  last_modified_at  TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  risk_score        SMALLINT,
  dsc_validated     BOOLEAN        NOT NULL DEFAULT FALSE,
  merchant_ref      TEXT,
  INDEX idx_customer_vpa (customer_vpa),
  INDEX idx_merchant_vpa (merchant_vpa),
  INDEX idx_status_expiry (status, valid_upto)
);
\`\`\`

### 3.2 Debit Transaction Entity

\`\`\`sql
CREATE TABLE upi_block_debits (
  debit_id          VARCHAR(64)    PRIMARY KEY,
  block_id          VARCHAR(64)    NOT NULL REFERENCES upi_blocks(block_id),
  debit_txn_id      VARCHAR(64)    NOT NULL UNIQUE,
  amount            DECIMAL(15,2)  NOT NULL CHECK(amount > 0),
  status            VARCHAR(20)    NOT NULL,
  service_proof     JSONB,
  trigger_type      VARCHAR(30)    NOT NULL CHECK(trigger_type IN (
                      'MERCHANT','AI_AGENT','SUBSCRIPTION','MANUAL')),
  created_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
  rrn               VARCHAR(20),
  INDEX idx_block_id (block_id)
);
\`\`\`

---

## 4. INTEGRATION FLOWS

### 4.1 Block Creation Flow (Sequence)

\`\`\`
Customer App → Payer PSP → NPCI Switch → Issuer Bank → NPCI Switch → Payer PSP → Customer App

1. Customer selects merchant + amount + validity
2. Payer PSP builds ReqPay (BLOCK_DEBIT) XML with DSC signature
3. NPCI Switch receives, validates schema + DSC
4. NPCI Switch → Fraud Engine: risk score request (< 500ms)
5. If risk OK: NPCI Switch → Issuer: block request
6. Issuer: validates balance, reserves funds, creates block record
7. Issuer → NPCI: RespPay SUCCESS + block_id
8. NPCI → Payer PSP → Customer: confirmation + block_id
9. NPCI → Notification Engine: async customer SMS + push notification
\`\`\`

### 4.2 Debit Execution Flow

\`\`\`
Merchant System → Payee PSP → NPCI Switch → Issuer Bank → NPCI Switch → Payee PSP → Merchant

1. Merchant triggers debit API after service delivery confirmation
2. Payee PSP builds ReqDebit XML with service proof
3. NPCI: validates block exists + is ACTIVE + amount ≤ remaining
4. NPCI → Issuer: debit instruction
5. Issuer: executes debit, updates available_amount, posts to CBS
6. Issuer → NPCI: debit confirmation + RRN
7. NPCI updates block status (PARTIALLY_DEBITED or FULLY_DEBITED)
8. Notification Engine: customer debit notification (< 5s SLA)
9. Merchant: receives webhook confirmation
\`\`\`

---

## 5. SECURITY ARCHITECTURE

### 5.1 Transport Security
- All external APIs: TLS 1.3 minimum; TLS 1.2 deprecated
- Certificate pinning for PSP app SDK communications
- mTLS for server-to-server (PSP ↔ NPCI ↔ Banks)

### 5.2 Request Authentication
\`\`\`
Request signing flow:
1. Build canonical request string (method + path + timestamp + body-hash)
2. Sign with RSA-2048 private key (PSP's registered key)
3. Attach as X-UPI-Signature header
4. NPCI validates against registered PSP public key
\`\`\`

### 5.3 Fraud Detection Architecture
\`\`\`
Transaction → Feature Extraction → ML Model → Risk Score
Features:
  - Velocity (txn count per customer/merchant in last 1h/24h)
  - Amount percentile vs historical
  - Device fingerprint match
  - Geographic anomaly
  - Merchant risk tier
  - Customer account age

Risk Score: 0–100
  0-30:  Auto-approve
  31-70: Apply friction (additional auth)
  71-90: Require OTP + biometric
  91+:   Decline + alert
\`\`\`

### 5.4 Data Privacy (DPDP Act 2023 Compliance)
- Customer VPA, account number, name: Tokenized in all logs
- PII accessible only to authorized roles with audit trail
- Data retention: Transaction data 5 years; PII masked after 2 years
- Right to erasure: Non-financial metadata deletable on request

---

## 6. DEPLOYMENT ARCHITECTURE

### 6.1 Infrastructure

\`\`\`
Production (Primary - Mumbai):
  ├── API Gateway Cluster (3 nodes, active-active)
  ├── UPI Switch Service (6 pods, auto-scaling 2-20)
  ├── Block Registry DB (Primary + 2 Read Replicas)
  ├── Fraud Engine (4 pods, GPU-enabled for ML inference)
  ├── Kafka Cluster (3 brokers, replication factor 3)
  ├── Redis Cluster (3 masters + 3 replicas)
  └── ELK Stack (log aggregation + search)

DR Site (Chennai):
  ├── Warm standby for all critical services
  ├── DB replication lag < 1 second
  └── RTO: 15 minutes | RPO: 30 seconds
\`\`\`

### 6.2 CI/CD Pipeline

\`\`\`
Git Push → CI Build (Maven) → Unit Tests → Integration Tests
→ Security Scan (SAST) → Docker Build → Push to Registry
→ Deploy to UAT → Functional Tests → Performance Tests
→ Security Audit Gate → Deploy to Production (blue-green)
\`\`\`

---

## 7. MONITORING & OBSERVABILITY

### 7.1 Key Metrics (SLOs)

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| API P99 latency | < 3s | > 5s |
| Transaction success rate | > 99.5% | < 99% |
| Block creation success | > 98% | < 97% |
| Notification delivery | > 99.9% | < 99% |
| Fraud model latency | < 500ms | > 1s |

### 7.2 Alerting Runbook
- **CRITICAL (PagerDuty immediate):** Success rate < 99% or API latency > 5s
- **HIGH (Slack + on-call):** Any single component error rate > 1%
- **MEDIUM (Slack):** Approaching capacity thresholds (>80% utilization)

---

## 8. MIGRATION & ROLLOUT PLAN

| Phase | Scope | Duration | Rollback Plan |
|-------|-------|----------|---------------|
| Alpha | NPCI internal sandbox | Week 1-2 | N/A (new env) |
| Beta | 3 pilot PSPs + 1 bank | Week 3-6 | Feature flag disable |
| Controlled | 10 PSPs + top 5 banks | Week 7-12 | Feature flag per PSP |
| GA | All certified PSPs | Week 13+ | Feature flag per PSP |

---

## 9. OPEN TECHNICAL ITEMS

| Item | Description | Owner | ETA |
|------|-------------|-------|-----|
| TSD-OI-1 | DSC key rotation mechanism | Security Arch | Week 3 |
| TSD-OI-2 | CBS integration spec for PSB banks | Bank Tech Leads | Week 4 |
| TSD-OI-3 | AI agent auth flow final design | Platform Arch | Week 5 |
| TSD-OI-4 | Fraud model training data pipeline | Data Science | Week 6 |

---

## 10. CODEBASE CHANGE SPECIFICATION — upi_hackathon_titans

> Auto-generated by analysing the current UPI system source code. Each entry maps to a specific file in the codebase.

**Existing System:** \`upi_hackathon_titans/\` — Python/Flask UPI simulation
**Feature Type:** ${codePlan.featureType}
**Total files touched:** ${filesTouched.length} | **~${getTotalLinesAffected(codePlan)} lines changed**

${codePlan.fileChanges.map((fc, idx) => `### 10.${idx + 1} \`${fc.path}\`

**Change:** ${fc.changeType === 'add' ? '➕ New additions' : fc.changeType === 'add-function' ? '➕ New functions' : '✏️ Modifications'}
**What:** ${fc.what}
**Why:** ${fc.why}

\`\`\`python
${fc.codeAfter}
\`\`\`
`).join('\n')}

### New Files to Create

${codePlan.newFiles.length === 0 ? 'None required for this feature.' : codePlan.newFiles.map(nf => `**\`${nf.path}\`** — ${nf.purpose}`).join('\n\n')}

### New API Endpoints

${codePlan.newEndpoints.map(ep => `- \`${ep}\``).join('\n')}

---

*Prepared by NPCI Platform Engineering | Confidential | Version 1.0 Draft*`;
}

export function generatePrototype(canvas: CanvasData): PrototypeData {
  const name = canvas.featureName;
  const nl = name.toLowerCase();
  const fullText = (name + ' ' + canvas.sections.map(s => s.content).join(' ')).toLowerCase();

  // Detect feature archetype
  const isReserve    = nl.includes('reserve') || nl.includes('block') || nl.includes('sbmd');
  const isAutopay    = nl.includes('autopay') || nl.includes('recurring') || nl.includes('mandate') || nl.includes('subscription');
  const isA2A        = nl.includes('a2a') || nl.includes('account to account') || nl.includes('peer');
  const isCredit     = nl.includes('credit') || nl.includes('loan') || nl.includes('bnpl') || nl.includes('buy now');
  const isIntl       = nl.includes('international') || nl.includes('cross border') || nl.includes('forex');
  const isOffline    = nl.includes('offline') || nl.includes('low connectivity') || nl.includes('no internet');

  const actionLabel  = isReserve ? 'Reserve' : isAutopay ? 'Mandate' : isA2A ? 'Transfer' : isCredit ? 'Credit Pay' : isOffline ? 'Offline Pay' : 'Payment';
  const itemLabel    = isReserve ? 'Reserves' : isAutopay ? 'Mandates' : isA2A ? 'Transfers' : 'Payments';
  const createLabel  = isReserve ? 'Create Reserve' : isAutopay ? 'Setup Mandate' : isA2A ? 'New Transfer' : isCredit ? 'Apply Credit' : isOffline ? 'Generate Token' : 'Pay Now';
  const confirmLabel = isReserve ? 'Reserve Created' : isAutopay ? 'Mandate Activated' : isCredit ? 'Credit Approved' : 'Payment Successful';

  const sampleItems  = isReserve
    ? [{ icon: '🍕', label: 'Zomato Food', sub: 'Expires 15 Apr', val: '₹2,000' }, { icon: '🚗', label: 'Uber Rides', sub: 'Expires 30 Apr', val: '₹3,000' }]
    : isAutopay
    ? [{ icon: '🎬', label: 'Netflix', sub: 'Next: 1 Apr', val: '₹649/mo' }, { icon: '💡', label: 'Electricity', sub: 'Next: 5 Apr', val: '₹1,200/mo' }]
    : isA2A
    ? [{ icon: '👤', label: 'Priya Sharma', sub: '2 days ago', val: '₹5,000' }, { icon: '🏢', label: 'Office Rent', sub: '1 Mar', val: '₹18,000' }]
    : isCredit
    ? [{ icon: '💳', label: 'HDFC Credit', sub: '₹38,000 available', val: '₹50,000' }, { icon: '🏦', label: 'Bajaj Finserv', sub: '₹25,000 available', val: '₹40,000' }]
    : isOffline
    ? [{ icon: '📴', label: 'Offline Token #1', sub: 'Valid: 24h', val: '₹500' }, { icon: '📴', label: 'Offline Token #2', sub: 'Valid: 12h', val: '₹200' }]
    : [{ icon: '💳', label: 'Last payment', sub: 'Merchant · 2d ago', val: '₹1,200' }, { icon: '📅', label: 'Scheduled', sub: 'Tomorrow · Utility', val: '₹500' }];

  const createFields = [
    isA2A ? 'Beneficiary account / VPA' : 'Payee / Merchant VPA',
    'Amount (₹)',
    isAutopay ? 'Frequency (Daily / Monthly)' : isReserve ? 'Validity period (7 / 15 / 30 days)' : 'Payment note',
    'Source bank account',
    ...(isReserve  ? ['Max debit cap per transaction', 'Merchant category'] : []),
    ...(isAutopay  ? ['Start date', 'End date / Max debits'] : []),
    ...(isCredit   ? ['Select credit line', 'Loan tenure', 'EMI amount preview'] : []),
    ...(isIntl     ? ['Currency selector', 'Live FX rate preview'] : []),
    ...(isOffline  ? ['Token validity (hours)', 'Max amount per token'] : []),
  ];

  // Build feature-specific extra screens
  const extraScreens: import('../types').PrototypeScreen[] = [];

  if (isReserve) {
    extraScreens.push({
      id: 'reserve_detail',
      title: 'Reserve Detail',
      description: 'View block details, partial debit history, and remaining balance',
      journeyStep: 5, journeyPhase: 'Manage',
      elements: ['Block ID / UPI Ref', 'Blocked amount vs remaining', 'Partial debit history', 'Merchant details', 'Validity countdown', 'Revoke / Modify buttons'],
      meta: { actionLabel, featureName: name },
    });
    extraScreens.push({
      id: 'reserve_merchant_debit',
      title: 'Merchant Debit Trigger',
      description: 'Merchant triggers partial debit against the block after service delivery',
      journeyStep: 6, journeyPhase: 'Confirm',
      elements: ['Service delivery proof', 'Debit amount (partial)', 'Block reference', 'Customer notification preview', 'Execute debit CTA'],
      meta: { actionLabel, featureName: name },
    });
  }

  if (isCredit) {
    extraScreens.push({
      id: 'credit_select',
      title: 'Select Credit Line',
      description: 'Choose from available credit lines for this payment',
      journeyStep: 2, journeyPhase: 'Select',
      elements: ['Available credit lines (bank-wise)', 'Credit limit & available balance', 'Interest rate / EMI preview', 'No-cost EMI offers', 'Proceed with selected line'],
      meta: { actionLabel, featureName: name },
    });
    extraScreens.push({
      id: 'credit_dashboard',
      title: 'Credit Dashboard',
      description: 'Overview of all credit line usage, EMIs, and repayment schedule',
      journeyStep: 7, journeyPhase: 'Manage',
      elements: ['Total credit utilization', 'Upcoming EMI payments', 'Credit score indicator', 'Repayment history', 'Pre-close EMI option'],
      meta: { actionLabel, featureName: name },
    });
  }

  if (isOffline) {
    extraScreens.push({
      id: 'offline_token_gen',
      title: 'Generate Offline Token',
      description: 'Create a pre-authorized payment token for offline use',
      journeyStep: 2, journeyPhase: 'Create',
      elements: ['Token amount (max ₹500)', 'Validity period', 'NFC / QR delivery method', 'Enter UPI PIN to authorize', 'Token stored securely on device'],
      meta: { actionLabel, featureName: name },
    });
    extraScreens.push({
      id: 'offline_pay',
      title: 'Tap to Pay (Offline)',
      description: 'Use stored token for NFC-based offline payment',
      journeyStep: 3, journeyPhase: 'Authenticate',
      elements: ['NFC scan animation', 'Token value deducted', 'Offline receipt generated', 'Will sync when online', 'Remaining token balance'],
      meta: { actionLabel, featureName: name },
    });
  }

  // Build user journey
  const journeySteps: import('../types').JourneyStep[] = [
    { step: 1, phase: 'Initiate', screen_id: 'home', actor: 'Customer', action: `Open UPI App — view ${itemLabel.toLowerCase()} dashboard`, what_happens_technically: 'App loads user profile, fetches active items from backend, renders dashboard', user_feeling: 'Confident — clear overview of financial state', pain_point_solved: 'No need to navigate multiple menus' },
    { step: 2, phase: 'Create', screen_id: 'create', actor: 'Customer', action: `${createLabel} — fill in details`, what_happens_technically: `Frontend validates inputs, prepares ${actionLabel} request payload`, user_feeling: 'Guided — clear form with smart defaults', pain_point_solved: 'Reduced form fields vs traditional banking' },
    { step: 3, phase: 'Authenticate', screen_id: 'auth', actor: 'Customer', action: 'Authenticate via UPI PIN or biometric', what_happens_technically: 'PIN encrypted with RSA-2048, sent to NPCI switch for validation at issuer bank', user_feeling: 'Secure — familiar UPI authentication', pain_point_solved: 'Single authentication step' },
    { step: 4, phase: 'Confirm', screen_id: 'confirm', actor: 'System', action: `${confirmLabel} — instant confirmation`, what_happens_technically: 'Switch processes transaction, credits/debits accounts, sends notifications via SMS + push', user_feeling: 'Satisfied — instant gratification', pain_point_solved: 'Real-time confirmation vs delayed banking' },
    { step: 5, phase: 'Manage', screen_id: 'manage', actor: 'Customer', action: `View and manage ${itemLabel.toLowerCase()}`, what_happens_technically: `Backend fetches all ${itemLabel.toLowerCase()} with status, limits, and history`, user_feeling: 'In control — full visibility', pain_point_solved: 'Centralized management' },
    { step: 6, phase: 'Resolve', screen_id: 'dispute', actor: 'Customer', action: 'Raise dispute if needed via UDIR', what_happens_technically: 'Dispute submitted to NPCI UDIR system, auto-routed to relevant bank', user_feeling: 'Protected — clear resolution pathway', pain_point_solved: 'T+1 resolution SLA' },
  ];

  return {
    status: 'pending',
    approved: false,
    feedback: '',
    figma_url: 'https://www.figma.com/',
    userJourney: {
      persona: { name: 'Rahul Mehta', context: `Tech-savvy professional using UPI for ${itemLabel.toLowerCase()}. Wants seamless, secure, and fast payment experiences.` },
      upi_flow_overview: `${name}: ${createLabel} → Authenticate → Confirm → Manage → Dispute (if needed)`,
      journey_steps: journeySteps,
    },
    screens: [
      {
        id: 'home', title: 'Home', journeyStep: 1, journeyPhase: 'Initiate',
        description: `${name} dashboard — balance and active ${itemLabel}`,
        elements: ['Account balance', `Active ${itemLabel}: ${sampleItems[0].label}, ${sampleItems[1].label}`, `Quick ${actionLabel} shortcut`, 'Recent transaction history', ...(isCredit ? ['Credit limit: ₹50,000 | Used: ₹12,000'] : []), ...(isOffline ? ['Offline tokens: 2 active'] : [])],
        meta: { sampleItems, actionLabel, itemLabel, createLabel, featureName: name },
      },
      ...extraScreens.filter(s => s.journeyStep === 2),
      {
        id: 'create', title: createLabel, journeyStep: extraScreens.filter(s => s.journeyStep === 2).length > 0 ? 3 : 2, journeyPhase: 'Create',
        description: `Initiate a new ${name} transaction with all required parameters`,
        elements: createFields,
        meta: { actionLabel, featureName: name },
      },
      {
        id: 'auth', title: 'Authenticate', journeyStep: 4, journeyPhase: 'Authenticate',
        description: `Secure UPI authentication before ${actionLabel.toLowerCase()} is created`,
        elements: [`${actionLabel} summary`, 'Fingerprint / Biometric', 'UPI PIN (fallback)', 'Encrypted channel indicator'],
        meta: { actionLabel, featureName: name },
      },
      {
        id: 'confirm', title: confirmLabel, journeyStep: 5, journeyPhase: 'Confirm',
        description: `${actionLabel} created and confirmation sent to registered mobile`,
        elements: ['Success animation', 'UPI Reference / RRN', isReserve ? 'Reserve valid until: 7 Apr 2026' : isAutopay ? 'Next debit date: 1 Apr 2026' : 'Receipt timestamp', 'Download / Share receipt', isReserve ? 'Revoke anytime option' : isAutopay ? 'Manage mandate' : 'Pay again shortcut'],
        meta: { actionLabel, featureName: name },
      },
      ...extraScreens.filter(s => s.journeyStep && s.journeyStep >= 5 && s.journeyStep <= 6 && s.id !== 'manage'),
      {
        id: 'manage', title: `My ${itemLabel}`, journeyStep: 7, journeyPhase: 'Manage',
        description: `View, pause, or revoke all your ${itemLabel.toLowerCase()}`,
        elements: [isReserve ? 'Active / Expired tabs' : isAutopay ? 'Active / Paused / Cancelled tabs' : 'Completed / Pending tabs', `${actionLabel} cards with usage bar`, isReserve ? 'Revoke / Modify' : isAutopay ? 'Pause / Cancel' : 'Repeat payment', 'Amount used vs total', 'Filter by date / merchant'],
        meta: { sampleItems, actionLabel, itemLabel, featureName: name },
      },
      ...extraScreens.filter(s => s.journeyStep && s.journeyStep > 6),
      {
        id: 'dispute', title: 'Raise Dispute', journeyStep: 8, journeyPhase: 'Resolve',
        description: 'UDIR-linked dispute resolution for unauthorized or incorrect debits',
        elements: [`Select ${actionLabel.toLowerCase()} / transaction`, 'Dispute reason: Not authorized / Wrong amount / Duplicate)', 'Supporting evidence upload', 'Submit via UDIR framework', 'Resolution in T+1 business day'],
        meta: { featureName: name },
      },
    ],
  };
}

export function generateExecutionItems(canvas: CanvasData): ExecutionItem[] {
  const codePlan = getCodePlan(canvas);
  const items: ExecutionItem[] = [
    {
      id: 'brd',
      file: 'Business Requirements Document',
      change: generateBRD(canvas),
      type: 'add',
      status: 'pending'
    },
    {
      id: 'tsd',
      file: 'Technical Specification Document',
      change: generateTSD(canvas),
      type: 'add',
      status: 'pending'
    }
  ];

  codePlan.fileChanges.forEach((fc, i) => {
    items.push({
      id: `e${i + 1}`,
      file: fc.path,
      change: fc.what,
      type: (fc.changeType === 'add' || fc.changeType === 'add-function') ? 'add' as const : 'modify' as const,
      status: 'pending' as const,
    });
  });

  codePlan.newFiles.forEach((nf, i) => {
    items.push({
      id: `enf${i + 1}`,
      file: nf.path,
      change: nf.purpose,
      type: 'add',
      status: 'pending',
    });
  });

  codePlan.testFilePaths.forEach((tp, i) => {
    items.push({
      id: `et${i + 1}`,
      file: tp,
      change: `Test suite: ${tp.replace('test_', '').replace('.py', '').replace(/_/g, ' ')}`,
      type: 'add',
      status: 'pending',
    });
  });
  return items;
}
