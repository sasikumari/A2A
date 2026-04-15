/**
 * IoT Payments Document Generator
 * Produces all 7 NPCI-standard IoT documents as markdown strings,
 * fitting the existing Document type used by DocumentsView.
 *
 * Reference: NPCI IoT TSD v1.6, Product Note v1.1, Circular, Product Deck,
 *            Canvas_ProductBuild IoT.docx, Testcases V1.4, Prototype Screens TV v1.0
 */

import type { CanvasData, Document } from '../types';

// ─── Device Detection ─────────────────────────────────────────────────────────

interface IoTContext {
  deviceType: string;
  deviceCategory: string;
  authMethod: string;
  primaryUseCase: string;
  deviceTag: string;
  capabilityFlags: string;
}

export function isIoTFeature(canvas: CanvasData): boolean {
  const text = (canvas.featureName + ' ' + canvas.sections.map(s => s.content).join(' ')).toLowerCase();
  return text.includes('iot') || text.includes('smart watch') || text.includes('smartwatch') ||
    text.includes('car dashboard') || text.includes('smart tv') || text.includes('television') ||
    text.includes('wearable') || text.includes('smart glasses') || text.includes('meta glasses') ||
    text.includes('smart ring') || text.includes('smart appliance') || text.includes('smart refrigerator') ||
    text.includes('connected car') || text.includes('ai agent') || text.includes('ai profile') ||
    text.includes('smart speaker') || text.includes('upi circle iot') || text.includes('delegate payment') ||
    text.includes('secondary device') || text.includes('device payment');
}

export function detectIoTContext(canvas: CanvasData): IoTContext {
  const text = (canvas.featureName + ' ' + canvas.sections.map(s => s.content).join(' ')).toLowerCase();

  if (text.includes('car') || text.includes('vehicle') || text.includes('automobile') || text.includes('dashboard')) {
    return { deviceType: 'Car Dashboard', deviceCategory: 'Type E', authMethod: 'Passcode / Biometric (fingerprint)', primaryUseCase: 'Fuel payments, toll payments, parking fees, EV charging', deviceTag: 'AUTOMOBILE', capabilityFlags: 'SCREEN:Y;NFC:N;VOICE:Y' };
  }
  if (text.includes('smart tv') || text.includes('television') || text.includes('tv') || text.includes('smart screen')) {
    return { deviceType: 'Smart TV', deviceCategory: 'Type C', authMethod: 'On-screen PIN / Passcode', primaryUseCase: 'Streaming subscriptions, in-app purchases, pay-per-view events', deviceTag: 'SMARTTV', capabilityFlags: 'SCREEN:Y;NFC:N;VOICE:N' };
  }
  if (text.includes('bike') || text.includes('motorcycle') || text.includes('two wheeler') || text.includes('scooter')) {
    return { deviceType: 'Connected Bike', deviceCategory: 'Type E', authMethod: 'Passcode / Biometric', primaryUseCase: 'Fuel checkout, EV battery swapping, toll payments', deviceTag: 'AUTOMOBILE', capabilityFlags: 'SCREEN:Y;NFC:N;VOICE:N' };
  }
  if (text.includes('smartwatch') || text.includes('smart watch') || text.includes('wearable')) {
    return { deviceType: 'Smartwatch', deviceCategory: 'Type A', authMethod: 'Passcode / NFC Tap', primaryUseCase: 'Retail purchases via NFC, transit fares, event tickets', deviceTag: 'WEARABLE', capabilityFlags: 'SCREEN:Y;NFC:Y;VOICE:N' };
  }
  if (text.includes('glasses') || text.includes('ar glasses') || text.includes('meta')) {
    return { deviceType: 'Smart Glasses', deviceCategory: 'Type D', authMethod: 'Voiceprint + Passphrase', primaryUseCase: 'Retail checkout via AR scan, event access, navigation fees', deviceTag: 'GLASSES', capabilityFlags: 'SCREEN:N;NFC:N;VOICE:Y' };
  }
  if (text.includes('smart ring') || text.includes('fitness band') || text.includes('band')) {
    return { deviceType: 'Smart Ring / Fitness Band', deviceCategory: 'Type B', authMethod: 'NFC Tap', primaryUseCase: 'Contactless POS payments, transit fare payment', deviceTag: 'WEARABLE', capabilityFlags: 'SCREEN:N;NFC:Y;VOICE:N' };
  }
  if (text.includes('refrigerator') || text.includes('appliance') || text.includes('vending')) {
    return { deviceType: 'Smart Appliance', deviceCategory: 'Type C', authMethod: 'App Passcode / Voice Confirmation', primaryUseCase: 'Grocery auto-replenishment, subscription renewals', deviceTag: 'APPLIANCE', capabilityFlags: 'SCREEN:Y;NFC:N;VOICE:N' };
  }
  if (text.includes('ai') || text.includes('software') || text.includes('agent') || text.includes('autonomous')) {
    return { deviceType: 'AI Software Agent', deviceCategory: 'Type D', authMethod: 'User-confirmed Mandate (pre-authorised)', primaryUseCase: 'Automated bill payments, scheduled transactions, smart reordering', deviceTag: 'SOFTWARE', capabilityFlags: 'SCREEN:N;NFC:N;VOICE:Y' };
  }
  // default IoT
  return { deviceType: 'IoT Device', deviceCategory: 'Type E', authMethod: 'Passcode / Biometric', primaryUseCase: 'Context-aware UPI payments from connected devices', deviceTag: 'IOT_DEVICE', capabilityFlags: 'SCREEN:Y;NFC:N;VOICE:N' };
}

const today = () => new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' });
const circularNo = () => `NPCI/UPI/OC/${new Date().getFullYear()}/${String(Math.floor(Math.random() * 800) + 100).padStart(3, '0')}`;

// ─── 1. Product Canvas ────────────────────────────────────────────────────────

function genCanvas(canvas: CanvasData, ctx: IoTContext): string {
  return `# Product Canvas — ${canvas.featureName}
**Version:** 1.0 | **Date:** ${today()} | **Status:** Draft | **Device:** ${ctx.deviceType} (${ctx.deviceCategory})

---

## 1. Feature
${canvas.featureName} enables UPI payments directly from **${ctx.deviceType}** using the UPI Circle Delegate Payments framework. Primary users authorize the device as a secondary payment entity, set spending limits, and the device transacts autonomously within those bounds without requiring the primary smartphone at payment time.

**Device Classification:** ${ctx.deviceCategory} — Capability flags: ${ctx.capabilityFlags}
**Authentication on device:** ${ctx.authMethod}
**Purpose Code:** H (IoT Delegate Payments)

---

## 2. Need / Problem Statement
Users relying on ${ctx.deviceType} for ${ctx.primaryUseCase} currently must interrupt the device experience to pull out a smartphone and complete a UPI transaction. This creates friction, payment abandonment, and degrades the native device experience. ${canvas.featureName} eliminates this by enabling UPI natively on the device.

---

## 3. Market View
- Rapidly growing ${ctx.deviceType} adoption in India across ${canvas.sections[2]?.content?.split('\n')[0] || 'urban and semi-urban segments'}
- 35M+ smartwatch users, 70M+ connected screens, 5M+ smart car dashboards (India, 2026)
- IoT payments globally projected at $30B+ by 2028; India poised for significant share via UPI
- UPI Circle framework already live — IoT extension is a natural next step for ecosystem expansion

---

## 4. Scalability
- Interoperable across all UPI-member PSPs (any PSP can become Secondary PSP)
- Device-agnostic: Same API framework works across all ${ctx.deviceCategory} devices via DeviceType tag = ${ctx.deviceTag}
- Monthly limit controls (max ₹15,000) + rolling 30-day logic prevent systemic risk
- NPCI switch handles cumulative limit enforcement — no per-PSP implementation needed

---

## 5. Validation
**Primary KPIs:**
| Metric | Target | Owner |
|--------|--------|-------|
| Device linking rate | 60% of eligible devices in 90 days | PSP |
| Transaction success rate | >98% | NPCI |
| Dispute rate | <0.1% | UDIR Dashboard |
| Monthly active devices | Per PSP target | Secondary PSP |
| Cooling period breach attempts | 0 | NPCI Switch |

---

## 6. Product Operating Model
- **Primary PSP**: Creates authorization; validates device on every transaction; handles dispute via UDIR
- **Secondary PSP**: Creates UPI ID for device; stores Device ID + App ID + Mobile; enforces cooling period
- **NPCI Switch**: Enforces cumulative ₹15,000/month limit; manages mandate lifecycle; routes transactions
- **Issuer Bank**: Processes mandates under purpose code H; resets monthly limits on anniversary date
- **OEM / Device Manufacturer**: Provides IoT Device App SDK; exposes Device ID; supports ${ctx.authMethod}

---

## 7. Product Comms
- NPCI Operational Circular to all UPI members upon launch
- PSP training kit with API specs, sandbox environment, and test vectors
- User communication: In-app prompts on primary UPI App to link eligible ${ctx.deviceType}
- Merchant enablement at ${ctx.primaryUseCase.split(',')[0]} touchpoints

---

## 8. Pricing
- No additional MDR for IoT delegate transactions — standard UPI MDR applies
- PSP SDK licensing: Free (as per NPCI policy for UPI ecosystem tools)
- Device OEM certification: Standard NPCI certification process (no fee)

---

## 9. Potential Risks

| Risk | Mitigation |
|------|-----------|
| Device theft → unauthorized payments | Instant delink via primary UPI App; auto-expiry on inactivity |
| Compromised device pairing | All pairing requires 2FA via primary app; tokens are session+device bound |
| Monthly limit gaming | Rolling 30-day window at NPCI switch; not calendar month |
| Cooling period bypass attempts | Enforced at both Secondary PSP and NPCI switch level |
| Voice spoofing (${ctx.deviceCategory === 'Type D' ? ctx.deviceType : 'voice-enabled devices'}) | Voiceprint + passphrase combination required |
| OEM non-compliance | NPCI certification mandatory before go-live |

---

## 10. Compliance
- Operates within extant RBI guidelines for delegate/mandate-based UPI payments
- Purpose Code H (IoT Delegate Payments) assigned by NPCI
- Device binding protocols mandatory per NPCI risk guidelines
- Cooling period (24 hours post-linking) per NPCI risk framework
- International transactions and collect requests restricted on secondary device UPI IDs
- All disputes via UDIR — existing resolution timelines apply
`;
}

// ─── 2. Operational Circular ──────────────────────────────────────────────────

function genCircular(canvas: CanvasData, ctx: IoTContext): string {
  return `# Operational Circular — ${canvas.featureName}

**Circular No.:** ${circularNo()}
**Date:** ${today()}
**Issued by:** National Payments Corporation of India (NPCI)

**To,**
All UPI Member Banks, Payment Service Providers, and Technology Service Providers

**Sub: Introduction of ${canvas.featureName} — ${ctx.deviceType} as Secondary Payment Entity under UPI Circle (Delegate Payments)**

---

Dear Sir / Madam,

## 1. Background

NPCI has been progressively enhancing the UPI Circle framework to enable trusted delegation of UPI payments to secondary entities under controlled conditions. In continuation of earlier circulars on UPI Circle and IoT device payments, this circular announces the introduction of **${canvas.featureName}**, enabling **${ctx.deviceType}** (Device Category: ${ctx.deviceCategory}) to initiate UPI transactions on behalf of the primary account holder.

This circular is effective from the date of issue and all UPI member banks and PSPs are required to comply by the timelines specified herein.

---

## 2. Feature Description

${canvas.featureName} operates under the **Full Delegation Approach** of UPI Circle:

**(a)** The primary user creates an authorization (mandate) for their ${ctx.deviceType} via their primary UPI App, setting a monthly spending limit.

**(b)** The ${ctx.deviceType} initiates UPI transactions autonomously, debited from the primary account holder's bank account.

**(c)** Purpose Code **'H'** (IoT Delegate Payments) is mandatory for all transactions under this feature.

**(d)** Authentication on the device is via **${ctx.authMethod}**.

**(e)** Primary user retains full control — can view, modify limits, or delink the device at any time from the primary UPI App.

---

## 3. Eligibility Criteria

| Entity | Eligibility Condition |
|--------|----------------------|
| Primary User | Active UPI account; KYC-compliant PSP; minimum one successful UPI transaction |
| ${ctx.deviceType} | Supports ${ctx.authMethod}; registered with Secondary PSP implementing UPI Circle SDK v2.37+ |
| Secondary PSP | NPCI-certified UPI member PSP with IoT Device SDK (v2.37+) |
| Issuer Bank | Supports mandate creation and processing for purpose code H under UPI v2.37+ |

---

## 4. Operational Guidelines

### 4.1 Device Registration & Linking
- The ${ctx.deviceType} captures the user's mobile number and device details (Device ID, App ID)
- UPI ID created for device post-OTP verification by Secondary PSP
- Linking initiated by scanning a QR displayed on the device via the primary UPI App
- Linking request expires after **30 minutes**

### 4.2 Authorization Creation
- Primary user sets monthly spending limit (maximum **₹15,000**) and validity (maximum 1 year)
- Mandate created with purpose code **'H'** at Issuer Bank
- Terms & Conditions acceptance mandatory on both primary UPI App and ${ctx.deviceType}

### 4.3 Transaction Processing
- Transactions initiated by ${ctx.deviceType} are processed via Full Delegation
- Device validation (Device ID + App ID + Mobile Number) is mandatory at every transaction
- Cumulative monthly limit enforced by NPCI switch on rolling 30-day basis

### 4.4 Limits & Controls
| Parameter | Value |
|-----------|-------|
| Maximum Monthly Limit | ₹15,000 |
| Cooling Period | 24 hours from device linking |
| Authorization Validity | As set by primary user (max 1 year) |
| Limit Reset | Same date monthly (rolls to 1st if date unavailable) |
| International Transactions | Not permitted |
| Collect Requests on Secondary UPI ID | Not permitted |

---

## 5. Roles & Responsibilities

### 5.1 Primary PSP
1. Shall ensure maximum prescribed limits for authorization creation and transactions
2. Shall validate Device ID, Secondary UPI ID, and available limit on every transaction
3. Shall decline transaction if amount exceeds available authorization limit for the month
4. Shall support UDIR/dispute mechanism from Primary UPI App
5. Shall enforce inter-PSP linking limits as per NPCI guidelines

### 5.2 Secondary PSP (${ctx.deviceType} App)
1. Shall create UPI ID post mobile number OTP verification (max 3 OTPs/day)
2. Shall store Device ID + App ID + Mobile Number for each registered device
3. Shall enforce cooling period (24 hours) — decline transactions within this window
4. Shall restrict collect requests and incoming mandate creation on secondary UPI IDs
5. Shall validate device details at every transaction

### 5.3 Issuer Bank
1. Shall allow authorization creation and transactions per prescribed limits
2. Shall store device details during authorization creation
3. Shall validate: monthly mandate limit, secondary UPI ID/device details, and digital signature
4. Shall reset monthly authorization limits on the anniversary date
5. Shall remove payee validation and PDN for purpose code = 'H'
6. Reconciliation per existing standard UPI process

---

## 6. Risk & Security Controls
- Device binding protocols mandatory for all ${ctx.deviceType} registrations
- Cooling period of 24 hours from device linking (transactions declined with error code U34)
- All pairing requires 2FA via primary UPI App
- Tokens are session-bound and device-bound (no replay attacks)
- Abnormal/excessive transaction patterns invoke PSP-level fraud checks
- Liability framework per RBI guidelines and NPCI UDIR guidelines

---

## 7. Compliance Timeline

| Milestone | Target | Responsible |
|-----------|--------|-------------|
| SDK integration & NPCI certification | T+60 days | Secondary PSPs / OEMs |
| Issuer bank mandate processing (purpose H) | T+60 days | Issuer Banks |
| UAT completion | T+75 days | All Members |
| Production Go-Live | T+90 days | NPCI + All Members |

---

## 8. Enclosures
1. ${canvas.featureName} — Product Note
2. TSD — API Specifications for ${canvas.featureName} (UPI IoT TSD v1.7)
3. Test Cases — ${canvas.featureName}

Members are requested to ensure compliance by the specified dates. Queries may be directed to **upi.iot@npci.org.in**.

Yours faithfully,

**[Authorized Signatory]**
National Payments Corporation of India, Mumbai
`;
}

// ─── 3. Product Note ──────────────────────────────────────────────────────────

function genProductNote(canvas: CanvasData, ctx: IoTContext): string {
  return `# Product Note — ${canvas.featureName}
**Version:** 1.1 | **Date:** ${today()} | **Classification:** NPCI Confidential

---

## 1. Introduction
This note describes **${canvas.featureName}** — a capability that enables users to delegate UPI payment initiation to their **${ctx.deviceType}** (${ctx.deviceCategory}) using the UPI Circle framework. By authorizing the ${ctx.deviceType} as a secondary entity, primary users can complete **${ctx.primaryUseCase.split(',')[0]}** without interrupting their device experience. The feature leverages NPCI's Full Delegation approach (purpose code 'H') and is interoperable across all UPI member PSPs.

---

## 2. About the Feature

${canvas.featureName} enables UPI payments directly from ${ctx.deviceType} by extending the primary user's payment capability to their device through a delegated authorization mechanism.

**User Journey Overview:** The primary user performs a one-time linking of their ${ctx.deviceType} through their UPI App, setting a monthly spending limit. Thereafter, the device can initiate UPI payments autonomously — authenticating via **${ctx.authMethod}** on the device — while all transactions are debited from the primary account holder's linked bank account.

The feature significantly reduces friction in **${ctx.primaryUseCase}** scenarios by eliminating the need to reach for a smartphone. It expands UPI's touchpoints to millions of ${ctx.deviceType} users and drives higher engagement with daily digital payments through seamless, contextual transactions.

---

## 3. Design Principles

1. **Interoperable:** Primary user and secondary ${ctx.deviceType} can function on any PSP/UPI App in the UPI ecosystem — no lock-in to a specific PSP.
2. **Authentication by Primary User:** Primary user explicitly authenticates to authorize the ${ctx.deviceType} with prescribed monthly limits — no implicit delegation.
3. **Controls with Primary User:** Primary user retains full control to modify limits, pause, or revoke authorization for the linked ${ctx.deviceType} at any time from the UPI App.
4. **Device Security:** Secondary entity authenticated with device binding protocols (Device ID + App ID + Mobile Number) ensuring tamper-proof, device-specific pairing.
5. **Visibility:** All transactions initiated by the ${ctx.deviceType} are visible to the Primary user in real-time via their UPI App transaction history.
6. **Device-Native Authentication:** ${ctx.authMethod} ensures authentication is natively supported on ${ctx.deviceType} — no smartphone required during payment.

---

## 4. Product Construct

This feature enables primary users to extend UPI payments through ${ctx.deviceType} in a trusted and secure manner. Primary user can link or delink the device at any point of time.

**Primary User** — Individual/Payer who authorizes delegation of payment to a ${ctx.deviceType} from their preferred UPI App.

**Secondary Device (${ctx.deviceType})** — Device through which UPI payments are made. Category: ${ctx.deviceCategory}. Capabilities: ${ctx.capabilityFlags}. Authentication: ${ctx.authMethod}.

**IoT Device App** — Application embedded in/installed on the ${ctx.deviceType} enabling registration, QR display for linking, and payment initiation.

**Secondary PSP** — Manages the ${ctx.deviceType}'s UPI ID and processes transactions on behalf of the device.

**Primary PSP** — Manages the primary user's UPI account, authorization limits, and validates every transaction from the device.

### 4.1 Device Category Matrix
| Device | Category | Screen | NFC | Voice | Approach |
|--------|----------|--------|-----|-------|----------|
| ${ctx.deviceType} | ${ctx.deviceCategory} | ${ctx.capabilityFlags.includes('SCREEN:Y') ? '✓' : '✗'} | ${ctx.capabilityFlags.includes('NFC:Y') ? '✓' : '✗'} | ${ctx.capabilityFlags.includes('VOICE:Y') ? '✓' : '✗'} | Full Delegation |
| Smartwatch | Type A | ✓ | ✓ | Optional | Full Delegation |
| Smart Ring | Type B | ✗ | ✓ | ✗ | Full Delegation (Lite) |
| Smart TV | Type C | ✓ | ✗ | ✗ | Full Delegation |
| Meta Glasses | Type D | ✗ | ✗ | ✓ | Lite Approach |
| Car Dashboard | Type E | ✓ | ✗ | ✓ | Full Delegation |

### 4.2 Use Cases
| Device | Use Case | Description |
|--------|----------|-------------|
${ctx.primaryUseCase.split(',').map(uc => `| ${ctx.deviceType} | ${uc.trim()} | Initiated directly from ${ctx.deviceType} via ${ctx.authMethod} |`).join('\n')}
| ${ctx.deviceType} | Subscription Renewal | Auto-renew recurring subscriptions using delegated mandate |
| ${ctx.deviceType} | Limit Management | Primary user modifies/pauses/revokes authorization from UPI App |
| ${ctx.deviceType} | Transaction History | View all device transactions in primary UPI App |

---

## 5. Journey

### 5.1 Registration / Onboarding

**On ${ctx.deviceType} (IoT Device App):**
1. User opens IoT Device App on ${ctx.deviceType}
2. Enters registered mobile number
3. IoT Device App triggers OTP for mobile verification (max 3 attempts/day)
4. Post-OTP: UPI ID created for device by Secondary PSP
5. Device stores: Device ID (OEM-provided) + App ID + Mobile Number
6. ${ctx.deviceType} generates and displays QR containing UPI ID + device details

**On Primary UPI App:**
1. Primary user → UPI App → 'Link New Device' / 'UPI Circle'
2. Scans QR displayed on ${ctx.deviceType}
3. App validates: Mobile number match + Device details match
4. Reviews linking details, sets monthly limit (max ₹15,000) and validity
5. Enters UPI PIN to authorize
6. Mandate created with purpose code 'H' at Issuer Bank

**Consent on ${ctx.deviceType}:**
1. Device receives linking notification
2. Terms & conditions displayed — mandatory acceptance
3. User accepts → UPI ID activated → success confirmation on both devices

> Linking request expires after **30 minutes**. Cooling period of **24 hours** applies post-linking.

### 5.2 Payments

**Initiation on ${ctx.deviceType}:**
1. User initiates ${ctx.primaryUseCase.split(',')[0]} on ${ctx.deviceType}
2. Device checks available authorization limit
3. If limit available → proceed to authentication
4. User authenticates via **${ctx.authMethod}**
5. Payment request sent to Secondary PSP

**Transaction Processing (Full Delegation):**
1. Secondary PSP → ReqDelegateAuth → NPCI → Primary PSP
2. Primary PSP validates: Device details + UPI ID + Monthly limit
3. If valid: ReqPay from Primary PSP → NPCI → Remitter Bank
4. Remitter Bank debits primary account → ARPC sent to NPCI
5. NPCI routes credit → Beneficiary Bank credits payee
6. Transaction confirmation: ${ctx.deviceType} + primary phone notification

**Decline Conditions:**
- Monthly limit exhausted (error code U32)
- Cooling period active within 24h of linking (U34)
- Device details mismatch (U37)
- Insufficient balance in primary account (U35)
- Linking request expired (U30)

### 5.3 Manage IoT Payments (Primary UPI App)

**From Primary UPI App → Settings → UPI Circle / Linked Devices:**
- View all linked ${ctx.deviceType}(s) with status and remaining limit
- Modify monthly spending limit (requires UPI PIN)
- View authorization expiry date
- Pause / resume device payments
- Delink ${ctx.deviceType} permanently (mandate revoked)
- View full transaction history for each linked device

### 5.4 Transaction History (Primary UPI App)

- All ${ctx.deviceType} transactions tagged with device identifier
- Filter by: Date range, Amount, Transaction type, Device name
- Transaction details: Amount, Payee, Merchant, Timestamp, Status, Reference ID, Purpose Code H
- Export: PDF/CSV of transaction history available

### 5.5 Dispute Journey (within Transaction History)

**Raising a Dispute:**
1. Primary user → Transaction History → Select transaction → 'Raise Dispute'
2. Select reason: Not authorized / Amount incorrect / Goods not received / Other
3. Submit → Dispute registered via UPI Help → UDIR flow initiated

**Resolution Timelines (per UDIR):**
- Acknowledgment: within 3 business days
- Resolution: within 30 calendar days
- Refund (if applicable): T+5 business days from resolution

> All disputes must be raised via Primary UPI App. ${ctx.deviceType} cannot raise disputes independently.

---

## 6. Roles & Responsibilities

### 6.1 PSP (Primary and Secondary)

**Primary PSP:**
1. Shall ensure maximum prescribed limits for authorization creation and transactions
2. Shall validate device details, Secondary UPI ID, and available limit on every transaction
3. Shall decline transaction if amount exceeds available authorization limit for the month
4. Shall support UDIR/dispute mechanism from Primary UPI App
5. Shall enforce intra-PSP linking limits per NPCI guidelines

**Secondary PSP (${ctx.deviceType} App):**
1. Shall create UPI ID post mobile number OTP verification
2. Shall trigger OTP (maximum 3 times/day) for mobile verification
3. Shall store Device ID + App ID + Mobile Number for each device
4. Shall enforce cooling period (24 hours post-linking) — decline transactions in window
5. Shall restrict collect requests and incoming mandate creation on secondary UPI IDs

### 6.2 IoT Device Software

The IoT Device App for ${ctx.deviceType} is the application layer interfacing between the hardware and UPI network:
1. Capture mobile number + device details → send to Secondary PSP for UPI ID creation
2. Display QR with UPI ID + device details for linking
3. Show available authorization limit before every payment
4. Allow payment only if limit is available
5. Implement **${ctx.authMethod}** for user identification
6. Display transaction confirmation and history
7. Accept/decline linking requests within 30-minute window
8. Enforce terms & conditions acceptance before linking

### 6.3 Issuer Bank
1. Allow authorization creation and transactions per maximum prescribed limits
2. Store device details during authorization creation
3. Validate: monthly mandate limit, secondary UPI ID/device details, digital signature
4. Reset monthly authorization limits on the anniversary date automatically
5. Remove payee validation and PDN for purpose code = 'H'
6. Reconciliation per existing standard UPI process

### 6.4 NPCI
1. Allow authorization creation and transactions per maximum prescribed limits
2. Enforce inter-PSP linking limits
3. Enforce cumulative ₹15,000/month limit per secondary user on rolling 30-day basis
4. Settlement and dispute management per UDIR guidelines

### 6.5 Payee / Beneficiary Bank
1. Process credits per standard UPI credit flow
2. Validate mandate and purpose code H for IoT payment credits
3. Support dispute resolution per UDIR guidelines

---

## 7. Dispute Management Mechanism

1. Dispute management is as per extant UPI UDIR guidelines
2. All complaints raised via UPI Help from the primary user's mobile device
3. ${ctx.deviceType} cannot raise disputes independently — disputes go through Primary UPI App only
4. For unauthorized transactions, primary user should immediately delink the ${ctx.deviceType}
5. **Liability framework:**
   - Primary user's PSP/Bank liability framework applies for standard disputes
   - Lost/stolen device post-linking: subject to RBI liability pass-on rules
   - Transactions within cooling period deemed fraudulent: Issuer bank liability

---

## 8. Edge Case Scenarios

| Scenario | Behavior | Error Code |
|----------|----------|-----------|
| Linking request expires (>30 min) | Error shown; user must regenerate QR from device | U30 |
| Mobile/device details mismatch at linking | Secondary PSP declines; linking rejected | U31 |
| Monthly limit exhausted | Transaction declined; remaining balance shown | U32 |
| Authorization limit exceeded per transaction | Transaction declined | U33 |
| Cooling period active (first 24h) | Transaction declined with cooling period message | U34 |
| Insufficient balance in primary account | Declined at Remitter Bank | U35 |
| Maximum linking limit reached | No additional devices can be linked | U36 |
| Device details mismatch during payment | Transaction declined by Secondary PSP | U37 |
| Device already registered (duplicate linking) | Secondary PSP rejects; UPI ID already exists | U38 |
| Network timeout at NPCI switch | Deemed pending; auto-resolved within 2h via reconciliation | — |
| Device delinked while transaction in-flight | In-flight transaction completes/pending; all subsequent declined | — |
| Primary user deletes UPI App | Existing authorizations remain valid; PSP must notify user | — |
| ${ctx.deviceType} offline/no connectivity | Transaction cannot be initiated; offline error shown on device | — |

---

## 9. Risk & Controls

| Risk Type | Description | Mitigation |
|-----------|-------------|-----------|
| Device theft/loss | Unauthorized payments via linked device | Instant delink via primary UPI App; auto-expiry on inactivity |
| Compromised pairing | Token replay from external device | Tokens are session-bound and device-bound |
| Spoofed QR/BLE linking | Spoofed device linking attempt | All pairing requires 2FA via primary UPI App |
| Voice spoofing | Mimicked commands on voice-enabled devices | Voiceprint + passphrase combination |
| Monthly limit gaming | Rolling window exploitation | Rolling 30-day window at NPCI switch (not calendar month) |
| Abnormal transaction patterns | Excessive/unusual frequency | PSP-level fraud detection; auto-flag and alert primary user |
| Liability pass-on | Unauthorized transaction liability | Defined framework per RBI circular + NPCI UDIR guidelines |

---

## 10. Reconciliation, Clearing & Settlement

Reconciliation for ${canvas.featureName} transactions follows the existing UPI process:

1. **URCS:** All ${ctx.deviceType} transactions processed through UPI Reconciliation and Clearing System (URCS) per extant guidelines
2. **Settlement:** Primary account holder's bank account debited; beneficiary's account credited; funds settled between banks during settlement windows per existing UPI settlement rails
3. **Mandate-Level Reconciliation:** Issuer bank maintains mandate-level records for all delegated authorizations under purpose code 'H'; monthly limit restoration automated on reset date
4. **Dispute Settlement:** Disputed transactions follow standard UDIR-linked resolution — refunds processed within T+5 business days of resolution
5. **No Infrastructure Change:** Existing UPI settlement rails unchanged; no new settlement infrastructure required
`;
}

// ─── 4. Prototype Screens Description ────────────────────────────────────────

function genPrototype(canvas: CanvasData, ctx: IoTContext): string {
  return `# Prototype Screens — ${canvas.featureName}
**Reference:** IoT — ${ctx.deviceType} Sample Journey v1.0 | **Date:** ${today()}

---

## Flow Overview

| Flow | Screens | Description |
|------|---------|-------------|
| Onboarding / Linking | 8 screens | Full linking journey: device registration → QR → primary app scan → limit setting → consent |
| Payment | 4 screens | Payment initiation → authentication → processing → success |
| Manage | 2 screens | View linked devices → modify limit / delink |
| Transaction History | 2 screens | History list → transaction detail |
| Dispute | 2 screens | Raise dispute → confirmation |

---

## Flow 1: Onboarding / Linking

### Screen 1.1 — ${ctx.deviceType}: Enter Mobile Number
\`\`\`
┌────────────────────────────┐
│  UPI Circle                │
│  Smarter Way to Pay        │
│                            │
│  Set up UPI payments on    │
│  your ${ctx.deviceType.padEnd(15)}│
│                            │
│  ┌──────────────────────┐  │
│  │ +91 9876543210       │  │
│  └──────────────────────┘  │
│  Make sure this number is  │
│  linked to UPI             │
│                            │
│  [   Get OTP →   ]         │
└────────────────────────────┘
\`\`\`
**Action:** User enters registered mobile number
**Validation:** Mobile must be registered with UPI

---

### Screen 1.2 — ${ctx.deviceType}: OTP Verification
\`\`\`
┌────────────────────────────┐
│  One Time Password         │
│                            │
│  Enter OTP received on     │
│  +91 98765 XXXXX           │
│                            │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ │
│  │●│ │●│ │●│ │●│ │●│ │●│ │
│  └──┘ └──┘ └──┘ └──┘ └──┘ └──┘ │
│                            │
│  Didn't receive? 01:23     │
│  [    Verify →    ]        │
└────────────────────────────┘
\`\`\`
**Action:** 6-digit OTP entry; resend after 2 minutes; max 3 attempts/day

---

### Screen 1.3 — ${ctx.deviceType}: QR Display for Linking
\`\`\`
┌────────────────────────────┐
│  Hello User!               │
│  Link your ${ctx.deviceType.substring(0, 12).padEnd(12)} │
│                            │
│  ┌──────────────────────┐  │
│  │  ▓▓▓  ░  ▓▓  ░  ▓▓▓ │  │
│  │  ░    ▓  ░░  ▓  ░   │  │
│  │  ▓▓▓  ░  ▓▓  ░  ▓▓▓ │  │
│  │  [QR CODE]           │  │
│  └──────────────────────┘  │
│  Scan from your UPI App    │
│  UPI ID: device.XX@iotpsp  │
│  Expires in: 29:45         │
└────────────────────────────┘
\`\`\`
**Action:** QR contains UPI ID + Device ID + App ID; expires in 30 minutes

---

### Screen 1.4 — Primary UPI App: Review Linking Request
\`\`\`
┌────────────────────────────┐
│  Link Device               │
│                            │
│  Device: ${ctx.deviceType.substring(0, 18).padEnd(18)} │
│  Device ID: XXXXXXXXXXXXXXX│
│  Mobile: +91 98765XXXXX    │
│  UPI ID: device.XX@iotpsp  │
│                            │
│  Linking to your           │
│  UPI account               │
│                            │
│  [ Proceed to Set Limits ] │
│  [ Cancel                ] │
└────────────────────────────┘
\`\`\`
**Validation:** Primary UPI App verifies mobile number match and device details

---

### Screen 1.5 — Primary UPI App: Set Spending Limits
\`\`\`
┌────────────────────────────┐
│  Set Usage Limits          │
│                            │
│  Monthly Limit             │
│  ┌──────────────────────┐  │
│  │ ₹ _____________      │  │
│  │ Max: ₹15,000         │  │
│  └──────────────────────┘  │
│                            │
│  Validity                  │
│  ┌──────────────────────┐  │
│  │ ▼ 6 Months           │  │
│  └──────────────────────┘  │
│                            │
│  [ Proceed to Authorize ]  │
└────────────────────────────┘
\`\`\`
**Note:** User can set any limit up to ₹15,000; default suggested: ₹5,000

---

### Screen 1.6 — Primary UPI App: Enter UPI PIN
\`\`\`
┌────────────────────────────┐
│  Authorize Device Linking  │
│                            │
│  Linking ${ctx.deviceType.substring(0, 15).padEnd(15)}│
│  Monthly limit: ₹5,000     │
│  Validity: 6 months        │
│                            │
│  Enter UPI PIN             │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ │
│  │●│ │●│ │●│ │●│ │●│ │●│ │
│  └──┘ └──┘ └──┘ └──┘ └──┘ └──┘ │
│                            │
│  [     Authorize     ]     │
└────────────────────────────┘
\`\`\`
**Security:** UPI PIN encrypts mandate creation request; sent to NPCI for processing

---

### Screen 1.7 — ${ctx.deviceType}: Accept Linking Consent
\`\`\`
┌────────────────────────────┐
│  Activate UPI Circle       │
│                            │
│  Linking Request Received  │
│                            │
│  ✓ Full control — set      │
│    limits & duration       │
│  ✓ One-time setup —        │
│    seamless recurring pay  │
│  ✓ Convenience — no QR     │
│    scan every time         │
│                            │
│  [  ✓ Accept Linking  ]    │
│  [  ✗ Decline         ]    │
└────────────────────────────┘
\`\`\`
**Time limit:** Must accept/decline within 30 minutes of linking request

---

### Screen 1.8 — Linking Successful
\`\`\`
┌────────────────────────────┐
│                            │
│     ✅ Device Linked!      │
│                            │
│  ${ctx.deviceType.substring(0, 20).padEnd(20)} │
│  is now enabled for UPI    │
│                            │
│  Monthly Limit: ₹5,000     │
│  Valid till: Jun 2026      │
│  UPI ID: device.XX@iotpsp  │
│                            │
│  [        Done        ]    │
└────────────────────────────┘
\`\`\`
**Post-linking:** 24-hour cooling period begins; transactions declined until period ends

---

## Flow 2: Payment

### Screen 2.1 — ${ctx.deviceType}: Initiate Payment
\`\`\`
┌────────────────────────────┐
│  ${ctx.primaryUseCase.split(',')[0].substring(0, 22).padEnd(22)} │
│                            │
│  Merchant: [Merchant Name] │
│  Amount: ₹ ___________     │
│                            │
│  Available: ₹4,750         │
│  (of ₹5,000 monthly limit) │
│                            │
│  [      Pay ₹ ___     ]    │
└────────────────────────────┘
\`\`\`

### Screen 2.2 — ${ctx.deviceType}: Authenticate
\`\`\`
┌────────────────────────────┐
│  Confirm Payment           │
│                            │
│  ₹250 → Merchant Name      │
│                            │
│  ${ctx.authMethod.substring(0, 25).padEnd(25)} │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐       │
│  │●│ │●│ │●│ │●│          │
│  └──┘ └──┘ └──┘ └──┘       │
│                            │
│  [   Confirm & Pay    ]    │
└────────────────────────────┘
\`\`\`

### Screen 2.3 — Processing
\`\`\`
┌────────────────────────────┐
│                            │
│     ⏳ Processing...       │
│                            │
│  Securely routing via UPI  │
│  ████████░░░░░░░           │
│                            │
│  Do not close this screen  │
└────────────────────────────┘
\`\`\`

### Screen 2.4 — Payment Success
\`\`\`
┌────────────────────────────┐
│                            │
│    ✅ Payment Successful   │
│                            │
│  ₹250 paid to              │
│  Merchant Name             │
│                            │
│  Txn ID: UPI1234567890     │
│  Remaining: ₹4,500         │
│                            │
│  [        Done        ]    │
└────────────────────────────┘
\`\`\`

---

## Flow 3: Manage IoT Payments (Primary UPI App)

### Screen 3.1 — Linked Devices Overview
\`\`\`
┌────────────────────────────┐
│  UPI Circle — My Devices   │
│                            │
│  📱 ${ctx.deviceType.substring(0, 18).padEnd(18)} │
│  Status: Active            │
│  This month: ₹250 of ₹5,000│
│  [   Manage Device    ]    │
│                            │
│  [ + Link New Device  ]    │
└────────────────────────────┘
\`\`\`

### Screen 3.2 — Device Management
\`\`\`
┌────────────────────────────┐
│  ${ctx.deviceType.substring(0, 20).padEnd(20)} │
│                            │
│  Monthly Limit:  ₹5,000    │
│  Remaining:      ₹4,750    │
│  Resets on:      25th      │
│  Expires:        Jun 2026  │
│  Status:         Active    │
│                            │
│  [✏️  Modify Limit    ]    │
│  [⏸️  Pause Payments  ]    │
│  [🔗  Delink Device   ]    │
└────────────────────────────┘
\`\`\`

---

## Flow 4: Transaction History

### Screen 4.1 — History List
\`\`\`
┌────────────────────────────┐
│  Transaction History       │
│  All │ IoT │ Other         │
│                            │
│  Today                     │
│  ✅ ₹250 → Merchant A      │
│  ${ctx.deviceType.substring(0, 12).padEnd(12)} | 3:45 PM │
│                            │
│  Yesterday                 │
│  ✅ ₹1,200 → Merchant B    │
│  ${ctx.deviceType.substring(0, 12).padEnd(12)} | 11:20 AM│
└────────────────────────────┘
\`\`\`

### Screen 4.2 — Transaction Detail
\`\`\`
┌────────────────────────────┐
│  Transaction Detail        │
│                            │
│  ✅ Payment Successful     │
│  ₹250                      │
│                            │
│  To:   Merchant Name       │
│  Via:  ${ctx.deviceType.substring(0, 18).padEnd(18)} │
│  Date: ${today().substring(0, 18).padEnd(18)} │
│  Txn:  UPI1234567890       │
│  Code: H (IoT Delegate)    │
│                            │
│  [🚨 Raise Dispute   ]     │
└────────────────────────────┘
\`\`\`

---

## Flow 5: Dispute Journey

### Screen 5.1 — Raise Dispute
\`\`\`
┌────────────────────────────┐
│  Raise a Complaint         │
│  ₹250 | ${today().substring(0, 10).padEnd(10)}       │
│                            │
│  ○ Not authorized by me    │
│  ○ Amount deducted, failed │
│  ○ Wrong amount charged    │
│  ○ Goods not received      │
│  ○ Other                   │
│                            │
│  [  Submit Complaint  ]    │
└────────────────────────────┘
\`\`\`

### Screen 5.2 — Dispute Confirmed
\`\`\`
┌────────────────────────────┐
│                            │
│  ✅ Complaint Registered   │
│                            │
│  ID: UDIR2025XXXXXXXXXX    │
│  Resolution: ~30 days      │
│  You'll be notified via    │
│  SMS & UPI App             │
│                            │
│  [  Track Status  ]        │
│  [     Done       ]        │
└────────────────────────────┘
\`\`\`

---

## Design Notes
- All screens build on base UPI screen patterns — no new design language needed
- ${ctx.deviceType} screens adapt based on capability flags: ${ctx.capabilityFlags}
- Authentication screen uses ${ctx.authMethod} as the primary method
- Error states (cooling period, limit exceeded, device mismatch) show clear error codes (U30–U38) with user-friendly messages
- QR screen must auto-refresh after expiry; do not allow scanning expired QR
`;
}

// ─── 5. Test Cases ────────────────────────────────────────────────────────────

function genTestCases(canvas: CanvasData, ctx: IoTContext): string {
  return `# Test Cases — ${canvas.featureName}
**Version:** 1.0 | **Date:** ${today()} | **Reference:** IOT_testcases_V1.4

---

## Test Case Summary
| Type | Count |
|------|-------|
| Happy Path | 4 |
| Negative | 4 |
| Edge Case | 2 |
| **Total** | **10** |

---

## Section 1: Linking / Registration

| TC ID | Test Scenario | Pre-Condition | Test Steps | Expected Result | Type | Priority |
|-------|--------------|---------------|------------|-----------------|------|----------|
| TC-LINK-001 | Successful device linking | ${ctx.deviceType} with IoT App installed; Active UPI account | 1. Open IoT App → enter mobile → complete OTP → display QR 2. Primary app scans QR 3. Set limit ₹5,000, validity 6 months 4. Enter UPI PIN 5. Accept consent on device | Device linked; UPI ID created; Mandate at issuer bank; Success on both devices | Happy Path | P1 |
| TC-LINK-002 | Linking request expiry (>30 min) | QR displayed on device | 1. Display QR 2. Wait 31 minutes 3. Attempt scan | Error U30; "Linking request expired"; User prompted to regenerate QR | Negative | P1 |
| TC-LINK-003 | Mobile number mismatch | Device registered with mobile A; primary account on mobile B | 1. Scan QR with mismatched mobile 2. Proceed with linking | Error U31; "Mobile number mismatch"; Linking rejected by Secondary PSP | Negative | P1 |
| TC-LINK-004 | Limit exceeds ₹15,000 | Primary UPI App at limit input screen | 1. Enter limit ₹16,000 2. Tap Proceed | Input rejected; "Maximum monthly limit is ₹15,000" | Negative | P1 |

---

## Section 2: Payments

| TC ID | Test Scenario | Pre-Condition | Test Steps | Expected Result | Type | Priority |
|-------|--------------|---------------|------------|-----------------|------|----------|
| TC-PAY-001 | Successful payment via ${ctx.deviceType} | Device linked; limit available; primary account has balance | 1. Initiate ${ctx.primaryUseCase.split(',')[0]} on device 2. Verify available limit shown 3. Authenticate via ${ctx.authMethod} 4. Confirm payment | Transaction processed; debited from primary account; Success notification on device + primary phone | Happy Path | P1 |
| TC-PAY-002 | Payment exceeds monthly limit | Limit = ₹5,000; ₹4,900 spent this month | 1. Attempt payment of ₹200 | Declined; Error U32; "Monthly limit exceeded" | Negative | P1 |
| TC-PAY-003 | Payment during cooling period | Device linked less than 24 hours ago | 1. Attempt payment immediately post-linking | Declined; Error U34; "Cooling period active — retry after 24h from linking" | Negative | P1 |
| TC-PAY-004 | Network timeout — deemed pending | Network failure after payment initiation | 1. Initiate payment 2. Simulate network drop at NPCI | Transaction in Pending state; auto-resolved within 2h via reconciliation | Edge Case | P1 |

---

## Section 3: Manage / Delink

| TC ID | Test Scenario | Pre-Condition | Test Steps | Expected Result | Type | Priority |
|-------|--------------|---------------|------------|-----------------|------|----------|
| TC-MGMT-001 | Modify monthly spending limit | ${ctx.deviceType} linked; primary UPI App open | 1. Navigate to Manage ${ctx.deviceType} 2. Tap Modify Limit 3. Change ₹5,000 → ₹8,000 4. Enter UPI PIN | Limit updated; Mandate modified at issuer bank; Both devices show new limit | Happy Path | P1 |

---

## Section 4: Dispute

| TC ID | Test Scenario | Pre-Condition | Test Steps | Expected Result | Type | Priority |
|-------|--------------|---------------|------------|-----------------|------|----------|
| TC-DISP-001 | Raise dispute for unauthorized transaction | Transaction in history; Primary UPI App | 1. Open transaction 2. Tap Raise Dispute 3. Select "Not authorized by me" 4. Submit | Complaint registered with UDIR reference; Acknowledgment in 3 business days; Resolution within 30 days | Happy Path | P1 |
`;
}

// ─── 6. TSD ───────────────────────────────────────────────────────────────────

function genTSD(canvas: CanvasData, ctx: IoTContext): string {
  return `# Technical Specification Document (TSD) — ${canvas.featureName}
**Version:** 1.7 | **Date:** ${today()} | **UPI Version:** 2.37+ | **Purpose Code:** H

---

## Preface
This document describes the technical changes in UPI for **${canvas.featureName}** — Delegate Payments implementation for ${ctx.deviceType} (${ctx.deviceCategory}). Includes API specifications, XML schemas, leg-wise changes, device capability tags, and error codes.

**Device Type Tag:** \`${ctx.deviceTag}\`
**Capability Flags:** \`${ctx.capabilityFlags}\`
**PSP(P)** = Primary User PSP | **PSP(S)** = Secondary User PSP (${ctx.deviceType} App PSP)

---

## Document History
| Version | Date | Description | Author |
|---------|------|-------------|--------|
| 1.0 | Jul 2025 | Initial API flows and tag specifications | NPCI Product Team |
| 1.1 | Aug 2025 | Added Device tags for IoT, purpose code H, Device capability table | NPCI Product Team |
| 1.2 | Aug 2025 | Updated Device tags, added Lite approach for Type D devices | NPCI Product Team |
| 1.3 | Aug 2025 | Added LinkType="IoTDID" in ReqDelegateAdd | NPCI Product Team |
| 1.4 | Aug 2025 | Removed LinkTypeMobile in ValAdd; New DeviceTypes; Attributes guideline | NPCI Product Team |
| 1.5 | Oct 2025 | Added note for ReqMandate Revoke initiated by Secondary PSP | NPCI Product Team |
| 1.6 | Nov 2025 | PSP status fetch for mandate; Revoke note updates | NPCI Product Team |
| 1.7 | ${today()} | ${canvas.featureName} — ${ctx.deviceType} specific documentation | NPCI Product Team |

---

## 1. Introduction
This document describes the changes in UPI for ${canvas.featureName}. All IoT devices are classified by Device Category (Type A–E) and assigned a DeviceType tag used in the \`<Device>\` element of API requests.

PSPs can call \`ReqListAccPvd\` API to get the list of banks/PSPs supporting delegate payments version 2.37.

---

## 2. Linking Flow — Full Delegation Approach

### Step-by-step Leg Sequence
1. PSP(S) → NPCI: **ValAdd** — Validate secondary device UPI address
2. PSP(P) → NPCI: **ReqMandate (CREATE)** — Create authorization with purpose H, monthly limit, validity
3. NPCI → PSP(S): **ReqAuthMandate** — Forward to Secondary PSP for device consent
4. PSP(S) → NPCI: **RespAuthMandate** — Secondary PSP confirms device acceptance
5. NPCI → Issuer Bank: **ReqMandate** — Register mandate at issuer bank with device details
6. Issuer Bank → NPCI: **RespMandate** — Mandate creation confirmed
7. NPCI → PSP(S): **ReqMandateConfirmation** — Final confirmation to secondary PSP
8. PSP(P)/PSP(S): **DelegateAdd** — Add/Remove secondary user to/from authorization

### 2.1 ReqValAdd — Validate Secondary Device

\`\`\`xml
<upi:ReqValAdd xmlns:upi="http://npci.org/upi/schema/">
  <Head ver="2.0" ts="" orgId="" msgId="" prodType="UPI"/>
  <Txn id="" note="" refId="" refUrl="" ts="" type="ValAdd"
       custRef="" purpose="BH"/>
  <Payer addr="" name="" seqNum="" type="PERSON" code="">
    <Device>
      <Tag name="MOBILE" value=""/>
      <Tag name="TYPE"   value="${ctx.deviceTag}"/>
      <Tag name="ID"     value="{OEM_DEVICE_HARDWARE_ID}"/>
      <Tag name="OS"     value="{DEVICE_OS_VERSION}"/>
      <Tag name="APP"    value="{IOT_APP_BUNDLE_ID}"/>
      <Tag name="CAPABILITY" value="${ctx.capabilityFlags};AUTH:${ctx.authMethod.split('/')[0].trim()}"/>
    </Device>
  </Payer>
  <Payee addr="" name="" seqNum="" type="PERSON" code=""/>
</upi:ReqValAdd>
\`\`\`

> **Note:** Payee mobile number must match the primary user's mobile number.
> **Note:** TYPE must use ${ctx.deviceTag} — MOB is NOT valid for IoT devices.

### 2.2 ReqMandate — Create Authorization (PSP-P → NPCI)

\`\`\`xml
<upi:ReqMandate xmlns:upi="http://npci.org/upi/schema/">
  <Head ver="2.0" ts="" orgId="" msgId=""/>
  <Txn id="" note="" custRef="" refId="" refUrl="" ts=""
       type="CREATE" initiationMode="" initiatedBy="PAYER"
       purpose="H" orgTxnId="">
    <Rules>
      <Rule name="EXPIREAFTER" value="1 minute to max 64800 minutes"/>
    </Rules>
  </Txn>
  <Mandate name="" txnId="" umn="" ts=""
           revokeable="Y" shareToPayee="Y" type="" blockFund="N">
    <Validity start="ddMMYYYY" end="ddMMYYYY"/>
    <Amount value="{MAX_MONTHLY_AMOUNT}" rule="MAX"/>
    <Recurrence pattern="ASPRESENTED">
      <Rule value="" type="BEFORE|ON|AFTER"/>
    </Recurrence>
  </Mandate>
  <Payer addr="{PRIMARY_UPI_ID}" name="" seqNum="" type="PERSON" code="">
    <Device>
      <Tag name="MOBILE" value=""/>
      <Tag name="TYPE"   value="MOB"/>
      <Tag name="ID"     value=""/>
    </Device>
    <Creds>
      <Cred type="PIN" subType="MPIN">
        <Data code="" ki="">base-64 encoded/encrypted UPI PIN</Data>
      </Cred>
    </Creds>
  </Payer>
  <Payees>
    <Payee addr="{SECONDARY_DEVICE_UPI_ID}" name=""
           seqNum="" type="PERSON" code=""/>
  </Payees>
</upi:ReqMandate>
\`\`\`

### 2.3 ReqDelegateAdd — Add Secondary User (with IoTDID LinkType)

\`\`\`xml
<upi:ReqDelegateAdd xmlns:upi="http://npci.org/upi/schema/">
  <Head ver="2.0" ts="" orgId="" msgId=""/>
  <Txn id="" note="" ts="" type="DelegateAdd" custRef="" refId="" refUrl=""/>
  <Mandate umn="{UMN_FROM_LINKING}" txnId="" seqNum=""/>
  <Payer addr="{PRIMARY_UPI_ID}" name="" seqNum="" type="PERSON" code="">
    <Info>
      <Identity id="" type="ACCOUNT" verifiedName=""/>
    </Info>
  </Payer>
  <Payee addr="{SECONDARY_DEVICE_UPI_ID}" name="" seqNum="" type="PERSON" code="">
    <Info>
      <Identity id="" type="ACCOUNT" verifiedName=""/>
      <LinkType value="IoTDID"/>
    </Info>
    <Device>
      <Tag name="TYPE"       value="${ctx.deviceTag}"/>
      <Tag name="ID"         value="{DEVICE_ID}"/>
      <Tag name="APP"        value="{APP_ID}"/>
      <Tag name="CAPABILITY" value="${ctx.capabilityFlags}"/>
    </Device>
  </Payee>
</upi:ReqDelegateAdd>
\`\`\`

> **Note:** \`LinkType="IoTDID"\` is mandatory for IoT device linking (added in v1.4).

---

## 3. Transaction Flow

### Leg-wise Sequence for Full Delegation Payment

\`\`\`
${ctx.deviceType} App (PSP-S)
  │
  ├─▶ ReqDelegateAuth (PSP-S → NPCI → PSP-P)
  │     ├ Device: TYPE=${ctx.deviceTag}, ID=..., APP=..., CAPABILITY=...
  │     └ Mandate: UMN, Txn amount, Payee UPI ID
  │
PSP-P validates: Device details + authorization limit
  │
  ├─▶ ReqPay (PSP-P → NPCI)
  │     ├ purpose="H"
  │     └ Mandate UMN included
  │
  ├─▶ ReqAuthDetails (NPCI → Payee PSP) — address resolution
  │
  ├─▶ ReqPay (NPCI → Remitter Bank — DEBIT)
  │     └ Mandate limit check + deduct
  │
  ├─▶ RespPay (Remitter Bank → NPCI — ARPC)
  │
  ├─▶ ReqPay (NPCI → Beneficiary Bank — CREDIT)
  │
  └─▶ Final RespPay (NPCI → PSP-P)
        └ Updated remaining mandate limit
\`\`\`

### 3.1 ReqDelegateAuth (PSP-S → NPCI → PSP-P)

\`\`\`xml
<upi:ReqDelegateAuth xmlns:upi="http://npci.org/upi/schema/">
  <Head ver="2.0" ts="" orgId="" msgId=""/>
  <Txn id="" note="" custRef="" refId="" refUrl=""
       ts="" type="Pay" purpose="H"/>
  <Mandate umn="{UMN}" txnId="" seqNum=""/>
  <Payer addr="{SECONDARY_DEVICE_UPI_ID}" name="" seqNum=""
         type="PERSON" code="">
    <Device>
      <Tag name="TYPE"       value="${ctx.deviceTag}"/>
      <Tag name="ID"         value="{DEVICE_HARDWARE_ID}"/>
      <Tag name="APP"        value="{IOT_APP_ID}"/>
      <Tag name="CAPABILITY" value="${ctx.capabilityFlags}"/>
    </Device>
    <Creds>
      <Cred type="PIN" subType="MPIN">
        <Data code="" ki="">base-64 encoded device authentication data</Data>
      </Cred>
    </Creds>
  </Payer>
  <Payees>
    <Payee addr="{MERCHANT_UPI_ID}" name="" seqNum=""
           type="ENTITY" code="">
      <Merchant>
        <Identifier mid="" tid=""
                    merchantType="SMALL|LARGE"
                    merchantGenre="OFFLINE|ONLINE"/>
      </Merchant>
    </Payee>
  </Payees>
</upi:ReqDelegateAuth>
\`\`\`

---

## 4. Device Capability Table

| Device Category | Device Type | Screen | NFC | Voice | Auth Method | DeviceType Tag |
|----------------|------------|--------|-----|-------|-------------|---------------|
| **${ctx.deviceCategory}** | **${ctx.deviceType}** | **${ctx.capabilityFlags.includes('SCREEN:Y') ? 'Yes' : 'No'}** | **${ctx.capabilityFlags.includes('NFC:Y') ? 'Yes' : 'No'}** | **${ctx.capabilityFlags.includes('VOICE:Y') ? 'Yes' : 'No'}** | **${ctx.authMethod}** | **${ctx.deviceTag}** |
| Type A | Smartwatch | Yes | Yes | Optional | Passcode/Biometric | WEARABLE |
| Type B | Smart Ring | No | Yes | No | NFC Tap | WEARABLE |
| Type C | Smart TV | Yes | No | No | On-screen Passcode | SMARTTV |
| Type D | Meta Glasses / AI Agent | No | No | Yes | Voiceprint + Passphrase | GLASSES / SOFTWARE |
| Type E | Car Dashboard | Yes | No | Yes | Passcode/Biometric | AUTOMOBILE |

---

## 5. New / Modified Tags for IoT

| Tag Name | Element | Valid Values | Description |
|----------|---------|-------------|-------------|
| \`TYPE\` | Device > Tag | MOB \| ${ctx.deviceTag} \| WEARABLE \| AUTOMOBILE \| SMARTTV \| GLASSES \| SOFTWARE \| APPLIANCE | Device type — use IoT-specific type for secondary devices; MOB only for primary smartphone |
| \`ID\` | Device > Tag | String (OEM Hardware ID) | Unique immutable hardware identifier; bound at device manufacture |
| \`APP\` | Device > Tag | String (App Bundle ID) | IoT Device App identifier; validated against NPCI app registry |
| \`CAPABILITY\` | Device > Tag | SCREEN:Y\|N;NFC:Y\|N;VOICE:Y\|N;AUTH:<method> | Device capability flags; must accurately reflect hardware |
| \`LinkType\` | ReqDelegateAdd | IoTDID | Mandatory for IoT device linking; distinguishes from mobile-based linking |
| \`purpose\` | Txn | H | Purpose code for IoT Delegate Payments; mandatory for ALL IoT transactions |
| \`umn\` | Mandate | String | Unique Mandate Number generated during linking; required in all payment requests |

> **All tags mandatory** for IoT transactions. Missing tags rejected by NPCI switch.
> Tag values must exactly match registration data at Secondary PSP — mismatch = error U37.

---

## 6. Error Codes

| Error Code | Description | Source | Resolution |
|-----------|-------------|--------|-----------|
| U30 | Linking Request Expired (30-min window elapsed) | NPCI / Secondary PSP | User must regenerate QR from ${ctx.deviceType} |
| U31 | Device Validation Failed — Mobile/Device Mismatch | Secondary PSP | Check device registration; re-register if needed |
| U32 | Monthly Cumulative Limit Breached | NPCI Switch | Limit resets on anniversary date; check remaining balance |
| U33 | Authorization Limit Exceeded per Transaction | Primary PSP | Reduce transaction amount or modify monthly limit |
| U34 | Cooling Period Active | Secondary PSP | Retry after 24 hours from device linking timestamp |
| U35 | Insufficient Balance in Primary Account | Remitter Bank | Top up primary account |
| U36 | Maximum Linking Limit Reached | NPCI / PSP | Delink an existing device before adding new one |
| U37 | Invalid Device Details — Mismatch at Transaction | Secondary PSP | Device re-registration required |
| U38 | Device UPI ID Already Exists | Secondary PSP | Device already linked; use existing UPI ID |

---

## 7. Attributes Tag Guideline

All IoT device attribute tags under \`<Device>\` must follow these guidelines:

1. **TYPE:** Must use approved DeviceType tag (\`${ctx.deviceTag}\` for ${ctx.deviceType}). \`MOB\` is NOT valid for secondary IoT devices.
2. **ID:** Must be OEM-provided hardware ID — immutable after device manufacture. Not user-changeable under any circumstance.
3. **APP:** Must be the bundle ID of the NPCI-certified IoT Device App — validated against NPCI's approved app registry at transaction time.
4. **CAPABILITY:** Must accurately reflect device hardware capabilities — false declarations are grounds for PSP regulatory action.
5. **All tags are mandatory** for IoT transactions — missing tags will result in NPCI switch rejection (no error code returned; transaction dropped).
6. Tags must exactly match the registration values stored at Secondary PSP — any mismatch results in transaction decline with error U37.
7. **LinkType="IoTDID"** must be present in ReqDelegateAdd for all IoT device linking requests.
`;
}

// ─── 7. Product Deck (Slide content as markdown) ─────────────────────────────

function genProductDeck(canvas: CanvasData, ctx: IoTContext): string {
  return `# Product Deck — ${canvas.featureName}
**NPCI | UPI Payments through IoT | ${today()}**

---

## Slide 1: Title
**UPI Payments through ${ctx.deviceType}**

*"${ctx.deviceType} reimagines payments — turning ${ctx.deviceType.toLowerCase()} into instant, secure, and contactless payment endpoints, unlocking new value in speed, accessibility, and convenience."*

---

## Slide 2: The Opportunity

**Why ${ctx.deviceType}?**
- Rapidly growing ${ctx.deviceType} adoption across India
- Users already use ${ctx.deviceType} for ${ctx.primaryUseCase.split(',')[0]} — payments should follow naturally
- UPI is India's most trusted payment rail — extend it to where users already are
- Device Category ${ctx.deviceCategory} — ${ctx.capabilityFlags} — optimized for ${ctx.authMethod}

**The Problem Today:**
Users must interrupt their ${ctx.deviceType} experience to pull out a smartphone, open UPI App, authenticate, and pay — breaking the device context and causing friction and abandonment.

---

## Slide 3: The Solution — UPI Circle on ${ctx.deviceType}

**One-time setup. Seamless recurring payments.**

1. Link ${ctx.deviceType} to your UPI account (once)
2. Set monthly spending limit (up to ₹15,000)
3. Pay directly from ${ctx.deviceType} using ${ctx.authMethod}
4. Primary account gets debited — full visibility & control via UPI App

**Key benefits:**
- No smartphone needed during payment
- Full control: modify limits, view history, delink instantly
- Works with all UPI member PSPs — fully interoperable

---

## Slide 4: Use Cases

| Use Case | Description | Auth |
|----------|-------------|------|
${ctx.primaryUseCase.split(',').map(uc => `| ${uc.trim()} | Initiated directly from ${ctx.deviceType} | ${ctx.authMethod} |`).join('\n')}
| Subscription Renewal | Auto-renew recurring services | Delegated mandate |
| Transit Payments | Quick contactless payments | ${ctx.authMethod} |
| Micro-transactions | Low-value daily spend | ${ctx.authMethod} |

---

## Slide 5: Linking Journey (${ctx.deviceType})

\`\`\`
Step 1: Open IoT App on ${ctx.deviceType} → Enter mobile number
Step 2: Complete OTP verification → UPI ID created
Step 3: ${ctx.deviceType} displays QR with UPI ID + device details
Step 4: Primary user scans QR from their UPI App
Step 5: Set monthly limit (max ₹15,000) + validity + enter UPI PIN
Step 6: Accept consent on ${ctx.deviceType} → Linked ✓
\`\`\`
*QR expires in 30 minutes. Cooling period of 24 hours applies.*

---

## Slide 6: Payment Journey (${ctx.deviceType})

\`\`\`
Step 1: User initiates ${ctx.primaryUseCase.split(',')[0]} on ${ctx.deviceType}
Step 2: Device checks available authorization limit
Step 3: User authenticates via ${ctx.authMethod}
Step 4: Payment request → Secondary PSP → NPCI → Primary PSP
Step 5: Primary PSP validates device + limit → ReqPay to Remitter Bank
Step 6: Debit confirmed → Credit to Beneficiary Bank
Step 7: Success notification on ${ctx.deviceType} + primary phone
\`\`\`

---

## Slide 7: Design Principles

1. **Interoperable** — Any PSP, any ${ctx.deviceType}, any bank
2. **Authentication** — Primary user authorizes with UPI PIN; device uses ${ctx.authMethod}
3. **Controls** — Primary user modifies/revokes at any time
4. **Device Security** — Device binding: ID + App + Mobile; tokens are device+session bound
5. **Visibility** — All transactions visible to primary user in real-time
6. **Device-Native** — ${ctx.authMethod} on ${ctx.deviceType} — no smartphone needed during payment

---

## Slide 8: Linking API Sequence

\`\`\`
PSP(S) ──ValAdd──────────────────────────▶ NPCI
PSP(P) ──ReqMandate (CREATE, purpose=H)──▶ NPCI ──▶ PSP(S) [ReqAuthMandate]
                                           NPCI ◀── PSP(S) [RespAuthMandate]
PSP(P) ◀── NPCI ◀── Issuer Bank [RespMandate]
NPCI ──ReqMandateConfirmation───────────▶ PSP(S)
PSP(P)/PSP(S) ──DelegateAdd (IoTDID)────▶ NPCI
\`\`\`

---

## Slide 9: Transaction API Sequence

\`\`\`
${ctx.deviceType} App
    │ ReqDelegateAuth (Device: TYPE=${ctx.deviceTag}, ID=..., CAPABILITY=...)
    ▼
PSP(S) ──▶ NPCI ──▶ PSP(P)  [validates: device + limit]
PSP(P) ──ReqPay (purpose=H, UMN)──▶ NPCI ──▶ Remitter Bank [DEBIT]
NPCI ──▶ Beneficiary Bank [CREDIT]
NPCI ──Final RespPay──▶ PSP(P) ──▶ PSP(S) ──▶ ${ctx.deviceType} App
\`\`\`

---

## Slide 10: Transaction Controls

| Control | Value |
|---------|-------|
| Maximum Monthly Limit | ₹15,000 |
| Cooling Period | 24 hours from linking |
| Auth Validity | As set by primary user (max 1 year) |
| Limit Reset | Same date monthly |
| International Transactions | ✗ Not permitted |
| Collect Requests on Device | ✗ Not permitted |
| Purpose Code | H (IoT Delegate) |
| DeviceType Tag | ${ctx.deviceTag} |

---

## Slide 11: Security & Risk Framework

| Risk | Mitigation |
|------|-----------|
| Device theft/loss | Instant delink via UPI App; auto-expiry on inactivity |
| Compromised pairing | 2FA via primary app; tokens are device+session bound |
| Voice spoofing (Type D) | Voiceprint + passphrase combination |
| Monthly limit gaming | Rolling 30-day window at NPCI switch |
| Abnormal transaction patterns | PSP-level fraud detection + alert |

---

## Slide 12: Go-to-Market

1. **Phase 1 (T+0 to T+90):** Pilot with 2-3 PSPs + ${ctx.deviceType} OEMs — validate device binding + limit controls
2. **Phase 2 (T+90 to T+180):** PSP SDK release + merchant enablement at ${ctx.primaryUseCase.split(',')[0]} touchpoints
3. **Phase 3 (T+180+):** Full ecosystem rollout — all UPI member PSPs + merchant categories

**Success Metrics:** Device linking rate >60% | Txn success rate >98% | Dispute rate <0.1% | User NPS >70
`;
}

// ─── Main Export ──────────────────────────────────────────────────────────────

export function generateIoTDocuments(canvas: CanvasData): Document[] {
  const ctx = detectIoTContext(canvas);
  const dateStr = today();

  return [
    {
      id: 'iot-canvas',
      title: 'Product Canvas',
      icon: '📋',
      approved: false,
      lastEdited: dateStr,
      content: genCanvas(canvas, ctx),
    },
    {
      id: 'circular',
      title: 'Operational Circular',
      icon: '📜',
      approved: false,
      lastEdited: dateStr,
      content: genCircular(canvas, ctx),
    },
    {
      id: 'iot-deck',
      title: 'Product Deck',
      icon: '🎯',
      approved: false,
      lastEdited: dateStr,
      content: genProductDeck(canvas, ctx),
    },
    {
      id: 'product-doc',
      title: 'Product Note',
      icon: '📝',
      approved: false,
      lastEdited: dateStr,
      content: genProductNote(canvas, ctx),
    },
    {
      id: 'video-script',
      title: 'Prototype Screens',
      icon: '📱',
      approved: false,
      lastEdited: dateStr,
      content: genPrototype(canvas, ctx),
    },
    {
      id: 'test-cases',
      title: 'Test Cases',
      icon: '✅',
      approved: false,
      lastEdited: dateStr,
      content: genTestCases(canvas, ctx),
    },
    {
      id: 'rbi-summary',
      title: 'TSD (Technical Spec)',
      icon: '⚙️',
      approved: false,
      lastEdited: dateStr,
      content: genTSD(canvas, ctx),
    },
  ];
}
