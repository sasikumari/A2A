"""
Prototype Agent: Generates UI blueprints and screen journeys for any UPI feature.
Uses archetype-based logic to create truly prompt-agnostic UX specifications,
moving away from device-specific hardcoding to generic 'Secondary Ecosystem' models.
"""
from .llm import chat, extract_json
from .figma_agent import figma_agent


# Deep UPI flow knowledge baked into the system prompt
SYSTEM = """You are a senior UPI product designer at NPCI with 12+ years experience designing high-stakes UPI applications.

You have deep knowledge of how real UPI apps work (PhonePe, Google Pay, Paytm, BHIM, CRED):

NPCI TITANIUM DESIGN STANDARDS:
- Every feature must be designed for full production-grade compliance (OC 228, RBI security mandates).
- Journeys must be comprehensive, covering Discovery, Configuration, Bio-Auth, NPCI Transaction Processing, and Post-Transaction Management.
- Data-First Representation: Use real merchant names, realistic INR amounts, and valid UPI reference (RRN) formats.
- Dual-Device / Cross-Channel: If a feature involves hardware (IoT), secondary users (Circle), or multi-bank coordination, the journey MUST reflect both sides.

UPI TECHNICAL FLOW (standard for all features):
1. USER OPENS PSP APP → Dashboard with balance details and feature-specific active status.
2. FEATURE DISCOVERY → High-fidelity onboarding or discovery banner within the app.
3. PAYEE SELECTION → VPA, QR, or Contact selection with risk indicators.
4. TRANSACTION CONFIG → Specific fields (Mandates, Reserves, Credit Lines, or Device Linking).
5. REVIEW & CONSENT → Mandatory review screen with explicit T&C and regulatory notes.
6. SOURCE SELECTION → Multi-account picker (CASA, RuPay Credit, UPI Lite).
7. BIOMETRIC AUTHENTICATION → NPCI Common Library style bio-auth screen.
8. PROCESSING STATE → Real-time animation of Payer PSP → NPCI Switch → Issuer Bank routing.
9. SUCCESS / FAILURE → Animated checkmark/cross with full RRN and shareable receipt.
10. MANAGEMENT HUB → Dashboard for active mandates/reserves/devices/loans.
11. LIFECYCLE ACTIONS → Detail view with history, Modify, Pause, and Revoke options.
12. GRIEVANCE (UDIR) → Integrated dispute resolution screen following T+1 SLA norms.

Return ONLY valid JSON. No markdown outside JSON.
"""


class PrototypeAgent:
    def generate(self, canvas: dict, feedback: str = None) -> dict:
        feature = canvas.get("featureName", "UPI Feature")
        feature_section = next(
            (s["content"] for s in canvas.get("sections", []) if s["id"] == 1), ""
        )
        need_section = next(
            (s["content"] for s in canvas.get("sections", []) if s["id"] == 2), ""
        )
        scalability_section = next(
            (s["content"] for s in canvas.get("sections", []) if s["id"] == 4), ""
        )

        # Detect feature archetype
        fl = feature.lower()
        is_reserve  = any(w in fl for w in ["reserve", "block", "sbmd"])
        is_autopay  = any(w in fl for w in ["autopay", "recurring", "mandate", "subscription"])
        is_delegated = any(w in fl for w in ["iot", "device", "machine", "sensor", "delegate", "circle", "secondary"])
        is_a2a      = any(w in fl for w in ["a2a", "account-to-account", "peer"])
        is_credit   = any(w in fl for w in ["credit", "loan", "bnpl", "buy now"])
        is_intl     = any(w in fl for w in ["international", "cross-border", "forex"])

        archetype = (
            "fund reservation — Single Block Multiple Debits (SBMD)" if is_reserve else
            "recurring mandate / autopay" if is_autopay else
            "delegated secondary ecosystem payment (Circle/IoT)" if is_delegated else
            "account-to-account transfer" if is_a2a else
            "credit line / BNPL linked UPI payment" if is_credit else
            "cross-border UPI remittance" if is_intl else
            "standard UPI P2M payment"
        )
        action_label = (
            "Reserve" if is_reserve else
            "Mandate" if is_autopay else
            "Auth Pay" if is_delegated else
            "Transfer" if is_a2a else
            "Credit Pay" if is_credit else
            "Payment"
        )
        item_label = (
            "Reserves" if is_reserve else
            "Mandates" if is_autopay else
            "Secondary" if is_delegated else
            "Transfers" if is_a2a else
            "Payments"
        )

        # Build screen blueprint based on archetype — determines which screens are needed
        screen_blueprint = self._get_screen_blueprint(feature, archetype, action_label, item_label)

        feedback_instr = f"\nUSER FEEDBACK ON PROTOTYPE: {feedback}\n" if feedback else ""

        prompt = f"""Design a complete UPI app prototype for: {feature}
Feature type: {archetype}

{feedback_instr}
Canvas context:
{feature_section[:500]}
User need: {need_section[:300]}
Target merchants/users: {scalability_section[:200]}

SCREEN BLUEPRINT — generate ALL these screens (you can add more if the feature needs them):
{screen_blueprint}

Return JSON with this structure. Include ALL screens from the blueprint above:
{{
  "status": "pending",
  "approved": false,
  "feedback": "",
  "userJourney": {{
    "persona": {{
      "name": "[Real Indian name, age, city, profession matching the feature's target user]",
      "context": "[Specific real-world context — what they're trying to do, what frustration they have today]"
    }},
    "upi_flow_overview": "[2-3 sentences: how does UPI technically process this? Name the path: Payer PSP → NPCI Switch → Issuer Bank → response flow]",
    "journey_steps": [
      // One step per screen — "step" is the screen number, "screen_id" matches the screen "id" below
      {{
        "step": 1,
        "phase": "[Phase name: Discovery/Select/Configure/Review/Authenticate/Processing/Confirm/Manage/Detail/Modify/Revoke/Dispute]",
        "screen_id": "[matches screen id]",
        "actor": "[User / System / User + Bank]",
        "action": "[What the user does on this screen — specific to {feature}]",
        "what_happens_technically": "[What NPCI/PSP/bank processes in the background]",
        "user_feeling": "[Emotion/thought at this point]",
        "pain_point_solved": "[What old UPI flow problem this screen solves]"
      }}
      // ... one entry per screen
    ]
  }},
  "screens": [
    {{
      "id": "[unique_snake_case_id]",
      "title": "[Screen title as shown in app header]",
      "journeyStep": [step number],
      "journeyPhase": "[Phase name matching journey_steps]",
      "description": "[1-2 sentences: what the user sees and does on this screen — SPECIFIC to {feature}]",
      "elements": [
        "[Specific UI element with real data — merchant names, amounts, dates, field labels]",
        "[Another element]"
        // 4-7 elements per screen
      ],
      "meta": {{
        "actionLabel": "{action_label}",
        "itemLabel": "{item_label}",
        "featureName": "{feature}",
        // Include sampleItems for home/manage screens, createLabel for create screens
        // Add any feature-specific meta fields needed for rendering
      }}
    }}
    // ... all screens
  ]
}}

CRITICAL:
- Replace EVERY placeholder with REAL specific values for {feature}
- Use real Indian merchant names (Zomato, Swiggy, Uber, Blinkit, DMRC, Netflix, LIC, etc.)
- Use realistic ₹ amounts, real dates, real bank names (SBI, HDFC, ICICI, Axis)
- Every screen description must be specific to {feature} — no generic "payment" text
- screens array must have ALL screens from the blueprint"""

        thinking, answer = chat(SYSTEM, prompt, temperature=0.3, max_tokens=10000)
        parsed = extract_json(answer)

        # Accept as long as we have at least 5 screens (flexible, not fixed at 6)
        if not parsed or not parsed.get("screens") or len(parsed.get("screens", [])) < 5:
            parsed = self._fallback(feature, action_label, item_label)

        # Ensure userJourney is always present
        if not parsed.get("userJourney"):
            parsed["userJourney"] = self._fallback_journey(feature, archetype, action_label, item_label)

        # Sync journey steps count to screens count if mismatched
        screens = parsed.get("screens", [])
        journey = parsed.get("userJourney", {})
        existing_steps = {s.get("screen_id") for s in journey.get("journey_steps", [])}
        for screen in screens:
            if screen.get("id") not in existing_steps:
                # Add missing journey step for this screen
                journey.setdefault("journey_steps", []).append({
                    "step": screen.get("journeyStep", len(journey["journey_steps"]) + 1),
                    "phase": screen.get("journeyPhase", "Flow"),
                    "screen_id": screen["id"],
                    "actor": "User",
                    "action": screen.get("description", screen.get("title", "")),
                    "what_happens_technically": "",
                    "user_feeling": "",
                    "pain_point_solved": "",
                })

        parsed["userJourney"] = journey
        parsed.setdefault("status", "pending")
        parsed.setdefault("approved", False)
        parsed.setdefault("feedback", "")
        
        # Phase 6: Figma Integration
        parsed["figma_url"] = figma_agent.generate_canvas_design(parsed)
        
        return parsed

    def _get_screen_blueprint(self, feature: str, archetype: str, action_label: str, item_label: str) -> str:
        """
        Returns the universal 11-16 screen journey blueprint for any UPI archetype.
        Ensures NPCI Titanium standards for depth and post-transaction management.
        """
        # Core discovery and entry screens (Common to all)
        core = [
            f"1. home — {feature} Dashboard: Balance tile, active {item_label} summary cards (Status: Active/Pending), quick {action_label} button, and recent transaction timeline.",
            f"2. discover — Onboarding & Discovery: Dynamic banner explaining {feature} benefits, 'How it Works' carousel, and 'Get Started' CTA.",
        ]

        # Feature-specific configuration screens
        if "reserve" in archetype or "block" in archetype or "sbmd" in archetype:
            feature_specific = [
                f"5. configure_reserve — Reserve configuration (validity period: 7/15/30/90 days, max debit cap per transaction, merchant category selection)",
                f"6. review — Full summary before auth (merchant, total block amount, validity, debit terms — user confirms all)",
                f"7. bank_select — Bank account / credit line selection (CASA vs RuPay Credit, available balance shown)",
                f"8. authenticate — Bank auth (biometric + UPI PIN, bank logo, masked account, NPCI security badge)",
                f"9. processing — NPCI routing animation (PSP → NPCI Switch → Issuer Bank, 2-3 second wait)",
                f"10. success — Reserve created confirmation (UPI Ref/RRN, block amount, valid until date, share receipt)",
                f"11. manage_reserves — My Reserves dashboard (Active/Expired tabs, reserve cards with usage bar, expiry countdown)",
                f"12. reserve_detail — Individual reserve detail (merchant, total/used/remaining, debit history, validity timeline)",
                f"13. modify_reserve — Modify reserve (increase/decrease amount or extend validity — with re-auth)",
                f"14. revoke — Revoke reserve confirmation dialog (amount to be released, merchant name, confirm/cancel)",
                f"15. dispute — Raise dispute via UDIR (wrong debit, merchant non-delivery, unauthorized, evidence upload)",
            ]
        elif "autopay" in archetype or "mandate" in archetype or "recurring" in archetype:
            feature_specific = [
                f"5. configure_mandate — Mandate setup (frequency: daily/weekly/monthly/yearly, start date, end date, max debit per cycle)",
                f"6. review — Full mandate summary (merchant, amount, frequency, total commitment, terms)",
                f"7. bank_select — Source account selection (bank + available balance)",
                f"8. authenticate — Bank auth (biometric + PIN for mandate creation)",
                f"9. processing — Mandate registration with NPCI",
                f"10. success — Mandate activated (UPI Mandate Ref, next debit date, amount, share)",
                f"11. manage_mandates — My Mandates dashboard (Active/Paused/Cancelled, next debit countdown)",
                f"12. mandate_detail — Individual mandate detail (debit history, upcoming schedule, pause/resume)",
                f"13. upcoming_debit — Pre-debit notification screen (24hr notice, confirm upcoming debit details)",
                f"14. pause_mandate — Pause mandate (duration: 1 week / 1 month / indefinite)",
                f"15. dispute — Dispute unauthorized or failed debit",
            ]
        elif "delegated" in archetype or "secondary" in archetype or "circle" in archetype:
            # Generic Hardware / Secondary User Delegation Blueprint
            feature_specific = [
                f"2. type_select — [PRIMARY] Select [Device/User] type to link (List of supported categories matching {feature})",
                f"3. secondary_prompt — [SECONDARY SCREEN] Secondary interface shows activation prompt: 'You have not activated {feature} yet. Register?' with PROCEED button",
                f"4. secondary_qr — [SECONDARY SCREEN] Secondary interface displays QR/Link code: 'Scan/Enter this code on your Primary app' with device/user ID",
                f"5. delegate_setup — [PRIMARY] Linking & Consent: Review secondary entity details, T&C acceptance, and limit preferences",
                f"6. set_limits — [PRIMARY] Set spending limits: Maximum transaction value, monthly cycle cap, and source account selection",
                f"7. primary_auth — [PRIMARY] UPI PIN entry: 6-digit PIN to authorize the delegation linked to {feature}",
                f"8. secondary_consent — [SECONDARY SCREEN] Secondary interface shows incoming request: 'Primary has requested delegation. Approve?' — DECLINE / APPROVE",
                f"9. link_success — [SECONDARY SCREEN] Registration Success: 'Congratulations! Your account is linked', shows assigned VPA, and 'Ready' status",
                f"10. transaction_trigger — [SECONDARY SCREEN] Initiate {feature}: Trigger payment/action from secondary interface (e.g. Map selection / NFC tap / Service start)",
                f"11. primary_notification — [PRIMARY] Real-time Alert: '[Secondary] is initiating {feature} payment'. ALLOW/DENY prompt for high-value transactions",
                f"12. transaction_success — [SECONDARY SCREEN] Payment Complete: Checkmark, Transaction ID, Amount, and confirmation on both interfaces",
                f"13. management_dashboard — [PRIMARY] My Linked Entities: List of all active secondary devices/users with status, limit remaining, and Add button",
                f"14. item_detail — [PRIMARY] Detailed View: Subscription/Device history, usage progress bar, and Modify/Suspend controls",
                f"15. suspend_access — [PRIMARY] Suspend Confirmation: Warning banner, reason selector, and CONFIRM SUSPEND to block immediate access",
                f"16. dispute — [PRIMARY] UDIR Dispute: Report unauthorized or incorrect secondary transactions via NPCI's resolution framework",
            ]
        elif "credit" in archetype or "bnpl" in archetype:
            feature_specific = [
                f"5. credit_select — Select credit instrument (RuPay Credit Card, bank credit line, BNPL — available limit shown)",
                f"6. emi_options — EMI/repayment options (3/6/9/12 months, interest rate, total payable)",
                f"7. review — Full credit payment summary (merchant, amount, EMI plan, interest, total cost)",
                f"8. authenticate — Auth with bank credit verification",
                f"9. processing — Credit authorization with bank",
                f"10. success — Credit payment done (UPI Ref, credit used, EMI schedule, repayment reminder)",
                f"11. credit_dashboard — Credit usage dashboard (limit used/available, active EMIs, next EMI due)",
                f"12. emi_detail — Individual EMI schedule (payment dates, amounts, outstanding)",
                f"13. repay — Manual early repayment flow",
                f"14. dispute — Dispute wrong credit charge",
            ]
        elif "international" in archetype or "cross-border" in archetype:
            feature_specific = [
                f"5. corridor_select — Select country/corridor (Singapore, UAE, UK, Bhutan, Nepal — live FX rate shown)",
                f"6. fx_preview — FX rate and fee preview (INR amount, recipient gets X in local currency, total charges)",
                f"7. beneficiary — Beneficiary details (name, bank/VPA, country, purpose code for FEMA)",
                f"8. review — Full remittance summary (sender, beneficiary, amount, FX rate, fee, estimated delivery)",
                f"9. authenticate — Bank auth + RBI purpose code confirmation",
                f"10. processing — Cross-border routing (Indian bank → SWIFT/PayNow corridor → foreign bank)",
                f"11. success — Remittance initiated (UPI Ref, beneficiary credited in 2-5 min, tracking ID)",
                f"12. track — Live remittance tracking (status: sent → routing → received)",
                f"13. history — International transfer history with FX rates used",
                f"14. dispute — Dispute failed or delayed remittance",
            ]
        else:
            feature_specific = [
                f"5. configure — Feature-specific configuration screen (unique parameters for {feature})",
                f"6. review — Full summary before auth (all details user entered, confirm button)",
                f"7. bank_select — Bank account selection (CASA, credit, UPI Lite options with balances)",
                f"8. authenticate — Bank auth (biometric + UPI PIN, bank name shown)",
                f"9. processing — NPCI processing animation (PSP → NPCI → Bank routing)",
                f"10. success — Confirmation (UPI Ref/RRN, feature-specific details, share receipt)",
                f"11. manage — My {item_label} dashboard (Active/Expired, status cards)",
                f"12. detail — Individual {action_label} detail view (full history, status timeline)",
                f"13. modify — Modify/edit screen (change relevant parameters)",
                f"14. dispute — UDIR dispute raising (dispute type, evidence, T+1 SLA)",
            ]

        all_screens = core + feature_specific
        return "\n".join(all_screens)

    def _fallback_journey(self, feature: str, archetype: str, action_label: str, item_label: str) -> dict:
        return {
            "persona": {"name": "Priya, 28, urban professional", "context": f"Uses UPI daily, wants to use {feature}"},
            "upi_flow_overview": f"{feature} flows through Payer PSP → NPCI Switch → Issuer Bank. Bank authorises the {action_label.lower()} and returns confirmation to PSP within 2-3 seconds.",
            "journey_steps": [
                {"step": 1, "phase": "Initiate", "screen_id": "home", "actor": "User", "action": f"Opens {feature} in UPI app", "what_happens_technically": "PSP loads active items from issuer", "user_feeling": "Wants to get started", "pain_point_solved": f"One place for all {item_label}"},
                {"step": 2, "phase": "Create", "screen_id": "create", "actor": "User", "action": f"Fills in {action_label} details", "what_happens_technically": "PSP validates merchant and amount", "user_feeling": "Simple and quick form", "pain_point_solved": "No repeated data entry"},
                {"step": 3, "phase": "Authenticate", "screen_id": "auth", "actor": "User + Bank", "action": "Biometric / UPI PIN auth", "what_happens_technically": "Payer PSP → NPCI → Issuer Bank auth", "user_feeling": "Secure and fast", "pain_point_solved": "One-time auth vs multiple"},
                {"step": 4, "phase": "Confirm", "screen_id": "confirm", "actor": "System", "action": f"{action_label} confirmed on screen", "what_happens_technically": "Bank sends success → NPCI → PSP → merchant", "user_feeling": "Reassured", "pain_point_solved": "Instant confirmation"},
                {"step": 5, "phase": "Manage", "screen_id": "manage", "actor": "User", "action": f"Views and manages {item_label}", "what_happens_technically": "PSP queries issuer for real-time status", "user_feeling": "In control", "pain_point_solved": "Transparent status"},
                {"step": 6, "phase": "Resolve", "screen_id": "dispute", "actor": "User + NPCI UDIR", "action": "Raises dispute if needed", "what_happens_technically": "UDIR routes dispute T+1", "user_feeling": "Confident in resolution", "pain_point_solved": "Structured grievance process"},
            ]
        }

    def _fallback(self, feature: str, action_label: str = "Payment", item_label: str = "Payments") -> dict:
        slug = feature.lower()
        is_reserve = "reserve" in slug or "block" in slug
        is_autopay = "autopay" in slug or "mandate" in slug
        is_iot     = "iot" in slug or "device" in slug
        sample_home = (
            [{"icon": "🍕", "label": "Zomato Food", "sub": "Expires 15 Apr", "val": "₹2,000"},
             {"icon": "🚗", "label": "Uber Rides", "sub": "Expires 30 Apr", "val": "₹3,000"}] if is_reserve else
            [{"icon": "🎬", "label": "Netflix", "sub": "Next: 1 Apr", "val": "₹649/mo"},
             {"icon": "💡", "label": "Electricity", "sub": "Next: 5 Apr", "val": "₹1,200/mo"}] if is_autopay else
             [{"icon": "⚡", "label": "Active Service #1", "sub": "Delegated access", "val": "₹450/unit"},
              {"icon": "🔒", "label": "Hardware Node #3", "sub": "Threshold: ₹100", "val": "₹100"}] if is_iot else
            [{"icon": "💳", "label": "Last Payment", "sub": "Merchant · 2d ago", "val": "₹1,200"},
             {"icon": "📅", "label": "Scheduled", "sub": "Tomorrow · Utility", "val": "₹500"}]
        )
        if is_iot:
            base_screens = [
                {"id": "home", "title": f"{feature} — My Linked Accounts", "journeyStep": 1, "journeyPhase": "Initiate",
                 "description": f"{feature} home showing active linking status, spending summary, and Link New button",
                 "elements": [f"Secondary #1 · ID: SEC-9876 · ● Active · ₹1,200 used", f"Secondary #2 · ID: SEC-1234 · ● Active · ₹340 used", f"Secondary #3 · ID: SEC-5521 · ○ Offline · ₹0 used", "Link New button", "Total this month: ₹1,540"],
                 "meta": {"actionLabel": action_label, "itemLabel": item_label, "createLabel": "Link New", "featureName": feature,
                          "sampleItems": [{"icon": "👤", "label": "Secondary #1", "sub": "SEC-9876 · Active", "val": "₹1,200"}, {"icon": "👤", "label": "Secondary #2", "sub": "SEC-1234 · Active", "val": "₹340"}]}},
                {"id": "type_select", "title": "Select Category", "journeyStep": 2, "journeyPhase": "Select",
                 "description": f"Grid of supported categories for {feature} — user selects what they want to link",
                 "elements": ["Category A", "Category B", "Category C", "Category D"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "secondary_prompt", "title": "Activation Required", "journeyStep": 3, "journeyPhase": "DevicePrompt",
                 "description": "Secondary interface shows activation prompt and PROCEED button",
                 "elements": ["UPI logo", f"Message: 'You have not activated {feature} yet. Do you want to register?'", "PROCEED button"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "secondary_qr", "title": "Scan to Link", "journeyStep": 4, "journeyPhase": "QRLink",
                 "description": "Secondary interface displays QR code for primary app scanning",
                 "elements": ["UPI logo", "Message: 'Scan this QR through your Primary UPI app'", "Registration QR code", "Entity ID: SEC-9876"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "delegate_setup", "title": "Adding Secondary", "journeyStep": 5, "journeyPhase": "Configure",
                 "description": "Primary app: user reviews entity to be added, sets consent and limit preference",
                 "elements": ["Header: 'Delegating Access'", "Name: SEC-9876", "Consent checkbox: 'I hereby accept Terms & Conditions'", "Toggle: 'Set payment limits?' — Yes / No", "Set limits button"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "set_limits", "title": "Set Limits", "journeyStep": 6, "journeyPhase": "Configure",
                 "description": "Primary app: set spending limits and source account",
                 "elements": ["Limit options: ₹1,000 / ₹5,000 / Custom", "Cycle: Monthly", "Source: Bank Account ••••1234", "Confirm button"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "auth", "title": "Enter UPI PIN", "journeyStep": 7, "journeyPhase": "Authenticate",
                 "description": "Primary app: UPI PIN entry to authorize delegation",
                 "elements": ["Label: 'Enter 6-digit UPI PIN'", "Bank: Savings Account ••••1234", "6 PIN dots", "Keypad"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "secondary_consent", "title": "Approve Request", "journeyStep": 8, "journeyPhase": "DeviceConsent",
                 "description": "Secondary interface shows consent request — user approves",
                 "elements": ["Header: 'Approve Request'", "Message: 'Request from primary for delegation'", "Body: 'Do you want to be added as secondary?'", "DECLINE button | APPROVE button"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "link_success", "title": "Linked Successfully", "journeyStep": 9, "journeyPhase": "Confirm",
                 "description": "Secondary interface shows success — ID, status, and Ready button",
                 "elements": ["UPI logo", "Green text: 'Congratulations!'", "'Your account has been linked'", "'Your ID is SEC-9876@psp'", "READY button"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "trigger", "title": "Initiate Action", "journeyStep": 10, "journeyPhase": "PaymentTrigger",
                 "description": "Secondary interface: user selects action and amount to pay/reserve",
                 "elements": ["Action Option 1", "Action Option 2", "Amount: ₹100 / ₹500 / ₹2,000", "PROCEED button"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "payment_notification", "title": "Authorization Alert", "journeyStep": 11, "journeyPhase": "Notification",
                 "description": "Primary app receives alert for secondary action — ALLOW or DENY",
                 "elements": ["Alert: 'SEC-9876@psp is initiating ₹2,000 action'", "DENY button | ALLOW button", "Countdown timer"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "success", "title": "Action Successful", "journeyStep": 12, "journeyPhase": "Confirm",
                 "description": "Secondary interface shows success with ID and details",
                 "elements": ["Green checkmark", "'Action Successful'", "Ref ID: 987654321", "Amount: ₹1,000"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "dashboard", "title": "Management Dashboard", "journeyStep": 13, "journeyPhase": "Manage",
                 "description": "Primary app: all linked entities with status and limits",
                 "elements": ["Active / Suspended tabs", "SEC-9876 · ● Active · Last used: Today", "SEC-1234 · ● Active · Last used: 2h ago", "Add New button"],
                 "meta": {"actionLabel": action_label, "itemLabel": item_label, "featureName": feature}},
                {"id": "item_detail", "title": "Entity Detail", "journeyStep": 14, "journeyPhase": "Detail",
                 "description": "Primary app: full detail — history, limits, and modify/suspend options",
                 "elements": ["ID: SEC-9876", "Limit used: ₹1,000 / ₹5,000", "History list", "Modify button | Suspend button"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "suspend", "title": "Suspend Access", "journeyStep": 15, "journeyPhase": "Manage",
                 "description": "Primary app: suspend access immediately",
                 "elements": ["Red warning: 'Access will be blocked'", "ID: SEC-9876", "CONFIRM button", "Cancel"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "dispute", "title": "Raise Dispute", "journeyStep": 16, "journeyPhase": "Resolve",
                 "description": "Report unauthorized secondary transactions",
                 "elements": ["Select ID: SEC-9876", "Select transaction", "Submit to UDIR"],
                 "meta": {"featureName": feature}},
            ]
        else:
            base_screens = [
                {"id": "home", "title": "Home", "journeyStep": 1, "journeyPhase": "Initiate",
                 "description": f"{feature} dashboard — active {item_label}, balance, quick actions",
                 "elements": ["Account balance", f"Active {item_label}: {sample_home[0]['label']}, {sample_home[1]['label']}", f"Quick {action_label} button", "Recent transactions"],
                 "meta": {"actionLabel": action_label, "itemLabel": item_label, "createLabel": f"Create {action_label}", "featureName": feature, "sampleItems": sample_home}},
                {"id": "select_merchant", "title": "Select Merchant", "journeyStep": 2, "journeyPhase": "Select",
                 "description": f"Search and select merchant or payee for {feature}",
                 "elements": ["Search bar (name, VPA, phone)", "Recent merchants with logos", "Scan QR code option", "Featured merchants for this feature"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "enter_details", "title": "Enter Details", "journeyStep": 3, "journeyPhase": "Configure",
                 "description": f"Amount and details entry for {feature}",
                 "elements": ["Amount (₹) with feature limits shown", "Note / purpose", "Source bank account", f"Feature-specific field for {feature}"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "review", "title": "Review", "journeyStep": 4, "journeyPhase": "Review",
                 "description": f"Full summary of {action_label.lower()} before authentication",
                 "elements": [f"Merchant: {sample_home[0]['label']}", f"Amount: {sample_home[0]['val']}", "Terms and conditions", "Edit button", "Confirm & Authenticate"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "authenticate", "title": "Authenticate", "journeyStep": 5, "journeyPhase": "Authenticate",
                 "description": f"Bank authentication for {feature} — biometric + UPI PIN",
                 "elements": [f"{action_label} summary with merchant and amount", "HDFC Bank · ••••4521", "Fingerprint / Face ID biometric", "UPI PIN fallback (6-digit)", "NPCI security badge"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "processing", "title": "Processing", "journeyStep": 6, "journeyPhase": "Processing",
                 "description": "NPCI routing animation while bank processes the request",
                 "elements": ["Animated NPCI routing diagram", "Payer PSP → NPCI Switch → Issuer Bank", "Progress indicator", "Please wait message"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "success", "title": f"{action_label} Confirmed", "journeyStep": 7, "journeyPhase": "Confirm",
                 "description": f"Success confirmation — bank has processed the {action_label.lower()}",
                 "elements": ["Animated green checkmark", f"UPI Reference: UPI{feature[:3].upper()}2025041500001", f"Feature detail (valid until / next debit / receipt)", "Share receipt", f"View My {item_label}"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "manage", "title": f"My {item_label}", "journeyStep": 8, "journeyPhase": "Manage",
                 "description": f"Management dashboard for all {item_label.lower()}",
                 "elements": ["Active / Expired / Cancelled tabs", f"{action_label} cards with status badge", "Usage bar (amount used vs total)", "Revoke / Pause / Modify actions", "Filter by date / merchant"],
                 "meta": {"actionLabel": action_label, "itemLabel": item_label, "featureName": feature,
                          "sampleItems": [{"icon": s["icon"], "label": s["label"], "sub": s["sub"], "val": s["val"], "used": "₹450", "pct": 22} for s in sample_home]}},
                {"id": "detail", "title": f"{action_label} Detail", "journeyStep": 9, "journeyPhase": "Detail",
                 "description": f"Detailed view of a single {action_label.lower()} — history, status, timeline",
                 "elements": ["Merchant and amount header", "Status timeline (Created → Active → Debits)", "Transaction history list", "Validity / schedule info", "Modify / Revoke buttons"],
                 "meta": {"actionLabel": action_label, "featureName": feature}},
                {"id": "dispute", "title": "Raise Dispute", "journeyStep": 10, "journeyPhase": "Resolve",
                 "description": f"UDIR dispute resolution for {feature}",
                 "elements": ["Select transaction to dispute", f"Dispute type: Unauthorized debit / Merchant non-delivery / Funds not released", "Evidence upload (screenshot/receipt)", "Submit via UDIR (T+1 SLA)", "Track resolution status"],
                 "meta": {"featureName": feature}},
            ]
        return {"status": "pending", "approved": False, "feedback": "", "screens": base_screens}
