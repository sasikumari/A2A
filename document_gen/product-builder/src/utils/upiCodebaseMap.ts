/**
 * UPI Codebase Map
 *
 * This module encodes the structure of the upi_hackathon_titans codebase
 * so the product-builder can reason about which files need to change for
 * any new UPI feature, what each component does, and generate accurate
 * BRD/TSD and code-change plans grounded in the real codebase.
 */

// ─── Codebase File Registry ──────────────────────────────────────────────────

export interface CodeFile {
  path: string;
  role: string;
  layer: 'frontend' | 'api' | 'switch' | 'psp' | 'bank' | 'agents' | 'storage';
  keyClasses: string[];
  keyFunctions: string[];
  description: string;
}

export const UPI_CODEBASE: CodeFile[] = [
  // ── Switch Layer ──────────────────────────────────────────────────────────
  {
    path: 'switch/upi_switch.py',
    role: 'NPCI UPI Switch — transaction routing, limit enforcement, mandate management',
    layer: 'switch',
    keyClasses: ['UPISwitch', 'VPARegistry'],
    keyFunctions: ['handle_push', 'handle_collect', 'validate_limits', 'process_mandate'],
    description: 'Core transaction router. Enforces P2P_LIMIT (₹3L), validates VPAs via registry, routes ReqPay → banks. All new transaction types must be added here.',
  },
  {
    path: 'switch/ledger.py',
    role: 'Transaction ledger — stores all completed/failed transactions',
    layer: 'switch',
    keyClasses: ['Ledger', 'Transaction'],
    keyFunctions: ['record', 'get_by_rrn', 'balance_check'],
    description: 'In-memory ledger with SQLite persistence. New transaction categories (IoT delegate, A2A, etc.) need a new purpose code entry.',
  },
  {
    path: 'switch/notification_bus.py',
    role: 'Notification delivery — real-time alerts to payer/payee',
    layer: 'switch',
    keyClasses: ['NotificationBus'],
    keyFunctions: ['send', 'subscribe'],
    description: 'Pub/sub notification system. Push notifications for transaction events. Extend to support new notification types (mandate created, device linked, etc.).',
  },

  // ── PSP Layer ─────────────────────────────────────────────────────────────
  {
    path: 'psps/payer_psp.py',
    role: 'Payer PSP — initiates push transactions, validates credentials',
    layer: 'psp',
    keyClasses: ['PayerPSP'],
    keyFunctions: ['initiate_push_xml', 'send_push', 'validate_vpa'],
    description: 'Payer-side PSP. Creates UPI pay XML, validates UPI PIN, sends to switch. New features requiring PSP-side validation (biometric, device binding, mandate creation) go here.',
  },
  {
    path: 'psps/payee_psp.py',
    role: 'Payee PSP — resolves payee VPA, handles collect requests',
    layer: 'psp',
    keyClasses: ['PayeePSP'],
    keyFunctions: ['resolve_vpa', 'handle_collect'],
    description: 'Payee-side PSP. VPA address resolution and collect request processing. Payee validation, merchant category code (MCC) logic, and IoT secondary UPI ID management belong here.',
  },
  {
    path: 'psps/payer_psp_handler.py',
    role: 'Payer PSP API handler — XML parsing, request orchestration',
    layer: 'psp',
    keyClasses: [],
    keyFunctions: ['handle_reqpay', 'handle_mandate_create', 'handle_delegate_auth'],
    description: 'HTTP handler for Payer PSP. Parses incoming XML, calls PayerPSP methods. Add new API message type handlers here (ReqDelegateAuth, ReqMandate, ReqValAdd).',
  },
  {
    path: 'psps/payee_psp_handler.py',
    role: 'Payee PSP API handler — VPA resolution, collect processing',
    layer: 'psp',
    keyClasses: [],
    keyFunctions: ['handle_valadd', 'handle_collect'],
    description: 'HTTP handler for Payee PSP. Add new payee-side API message handlers here.',
  },

  // ── Bank Layer ────────────────────────────────────────────────────────────
  {
    path: 'banks/remitter_bank.py',
    role: 'Remitter (payer) bank — debit authorization, PIN verification, mandate creation',
    layer: 'bank',
    keyClasses: ['RemitterBank'],
    keyFunctions: ['debit', 'authorize', 'create_mandate', 'check_balance'],
    description: 'Payer\'s bank. Authorises debit with UPI PIN. For mandate-based/delegate payments, must validate mandate UMN and purpose code. IoT purpose code H handling goes here.',
  },
  {
    path: 'banks/beneficiary_bank.py',
    role: 'Beneficiary (payee) bank — credit processing',
    layer: 'bank',
    keyClasses: ['BeneficiaryBank'],
    keyFunctions: ['credit', 'verify_account'],
    description: 'Payee\'s bank. Credits the beneficiary. New features requiring payee-side validation (credit limits, merchant verification) go here.',
  },
  {
    path: 'banks/remitter_bank_handler.py',
    role: 'Remitter bank API handler',
    layer: 'bank',
    keyClasses: [],
    keyFunctions: ['handle_debit_request', 'handle_mandate'],
    description: 'HTTP handler for remitter bank. Add new bank-side API message handlers here.',
  },
  {
    path: 'banks/beneficiary_bank_handler.py',
    role: 'Beneficiary bank API handler',
    layer: 'bank',
    keyClasses: [],
    keyFunctions: ['handle_credit_request'],
    description: 'HTTP handler for beneficiary bank.',
  },

  // ── API Layer ─────────────────────────────────────────────────────────────
  {
    path: 'api/app.py',
    role: 'Flask API server — all HTTP endpoints, SSE streaming, deployment management',
    layer: 'api',
    keyClasses: [],
    keyFunctions: ['/push', '/collect', '/stream', '/deploy', '/workflow2/*', '/agents/*'],
    description: 'Main Flask app. New API endpoints for new features go here. Also registers all components (switch, PSPs, banks) at startup. Critical: SSE /stream endpoint drives live execution UI.',
  },

  // ── Frontend ──────────────────────────────────────────────────────────────
  {
    path: 'api/templates/new_ui.html',
    role: 'Main UPI app UI — transaction initiation, history, balance, navigation',
    layer: 'frontend',
    keyClasses: [],
    keyFunctions: ['sendPayment()', 'loadHistory()', 'showBalance()', 'openFeature()'],
    description: 'Main HTML frontend. New feature UI sections (IoT device management, mandate dashboard, biometric enrollment) are added here as new sections/modals.',
  },
  {
    path: 'api/static/app.js',
    role: 'Frontend JavaScript — UPI App logic, API calls, UI interactions',
    layer: 'frontend',
    keyClasses: [],
    keyFunctions: ['initApp()', 'handlePayment()', 'fetchTransactions()', 'setupSSE()'],
    description: 'All frontend JS. New features require new JS functions and event listeners here.',
  },
  {
    path: 'api/static/new_ui.css',
    role: 'Frontend styles — UPI App visual design',
    layer: 'frontend',
    keyClasses: [],
    keyFunctions: [],
    description: 'CSS for the UPI app frontend. Feature-specific UI components need new CSS classes here.',
  },

  // ── Agents Layer ──────────────────────────────────────────────────────────
  {
    path: 'agents/reasoning_agent.py',
    role: 'AI reasoning agent — LLM-based code change generation',
    layer: 'agents',
    keyClasses: ['ReasoningAgent'],
    keyFunctions: ['propose_change', 'generate_code_diff', 'analyze_impact'],
    description: 'Core AI agent that uses LLM to generate code changes. Receives feature spec, analyses codebase, produces targeted file edits.',
  },
  {
    path: 'agents/skill_planner.py',
    role: 'Skill planner — orchestrates multi-step code change sequences',
    layer: 'agents',
    keyClasses: ['SkillPlanner'],
    keyFunctions: ['plan', 'execute_step', 'rollback'],
    description: 'Plans and executes multi-file code changes in the correct dependency order.',
  },
  {
    path: 'agents/participant_agents.py',
    role: 'Participant agents — PSP, bank, switch specialised sub-agents',
    layer: 'agents',
    keyClasses: ['PSPAgent', 'BankAgent', 'SwitchAgent'],
    keyFunctions: ['modify_psp', 'modify_bank', 'modify_switch'],
    description: 'Specialised agents that understand each UPI participant\'s code and make targeted changes.',
  },
];

// ─── Feature → File Change Mapping ───────────────────────────────────────────

export interface FileChange {
  path: string;
  changeType: 'add' | 'modify' | 'add-function';
  what: string;
  why: string;
  codeBefore?: string;
  codeAfter: string;
  linesAffected?: number;
  effort: 'low' | 'medium' | 'high';
}

export interface FeatureCodePlan {
  featureType: string;
  summary: string;
  newEndpoints: string[];
  fileChanges: FileChange[];
  newFiles: { path: string; purpose: string }[];
  testFilePaths: string[];
  testCases: { name: string; description: string }[];
}

type FeatureType = 'iot' | 'biometric' | 'a2a' | 'credit' | 'mandate' | 'offline' | 'generic';

export function detectFeatureType(featureName: string, prompt: string): FeatureType {
  const t = (featureName + ' ' + prompt).toLowerCase();
  if (t.includes('iot') || t.includes('smartwatch') || t.includes('smart tv') || t.includes('car') || t.includes('wearable') || t.includes('television') || t.includes('glasses') || t.includes('ai agent') || t.includes('appliance')) return 'iot';
  if (t.includes('biometric') || t.includes('fingerprint') || t.includes('face') || t.includes('liveness')) return 'biometric';
  if (t.includes('a2a') || t.includes('account to account') || t.includes('account-to-account')) return 'a2a';
  if (t.includes('credit') || t.includes('credit line') || t.includes('post-pay') || t.includes('bnpl')) return 'credit';
  if (t.includes('mandate') || t.includes('recurring') || t.includes('block') || t.includes('sbmd') || t.includes('reserve')) return 'mandate';
  if (t.includes('offline') || t.includes('low connectivity') || t.includes('no internet')) return 'offline';
  return 'generic';
}

export function getCodePlan(canvas: { featureName: string; sections: { title: string; content: string }[] }): FeatureCodePlan {
  const prompt = canvas.sections.map(s => s.content).join(' ');
  const ft = detectFeatureType(canvas.featureName, prompt);
  return FEATURE_CODE_PLANS[ft](canvas.featureName);
}

// ─── IoT Feature Code Plan ────────────────────────────────────────────────────

function iotCodePlan(featureName: string): FeatureCodePlan {
  return {
    featureType: 'IoT / UPI Circle Delegate Payments',
    summary: `${featureName} requires adding delegate payment support across all UPI layers: device registration at the PSP level, mandate creation at the remitter bank, purpose code H routing at the switch, and a new IoT device management UI at the frontend.`,
    newEndpoints: [
      'POST /iot/register-device — register a secondary IoT device UPI ID',
      'POST /iot/delegate-auth — process ReqDelegateAuth from IoT device',
      'GET  /iot/devices/:mobile — list linked devices for a mobile number',
      'POST /iot/mandate/create — create authorization mandate (purpose code H)',
      'POST /iot/mandate/revoke — revoke device authorization',
    ],
    fileChanges: [
      {
        path: 'switch/upi_switch.py',
        changeType: 'add-function',
        what: 'Add handle_delegate_auth() and enforce_iot_monthly_limit()',
        why: 'IoT transactions use purpose code H and delegate auth flow — switch must route ReqDelegateAuth messages and enforce ₹15,000 monthly cumulative limit per secondary device',
        codeBefore: `# switch/upi_switch.py (current)
P2P_LIMIT = 300_000
MAX_TXN_AMOUNT = 3_00_000

class UPISwitch:
    def handle_push(self, xml_req: str):
        # existing P2P push logic
        ...`,
        codeAfter: `# switch/upi_switch.py (after change)
P2P_LIMIT = 300_000
MAX_TXN_AMOUNT = 3_00_000
IOT_MONTHLY_LIMIT = 15_000   # NEW: ₹15,000 monthly per IoT device
IOT_PURPOSE_CODE  = 'H'      # NEW: IoT Delegate Payments

class UPISwitch:
    def handle_push(self, xml_req: str):
        # existing P2P push logic
        ...

    # NEW: IoT Delegate Auth handler
    def handle_delegate_auth(self, xml_req: str):
        root = ET.fromstring(xml_req)
        umn   = root.findtext('.//Mandate[@umn]') or root.get('umn')
        dev   = {t.get('name'): t.get('value')
                 for t in root.findall('.//Device/Tag')}
        purpose = root.findtext('.//Txn[@purpose]') or root.find('Txn').get('purpose','')
        if purpose != IOT_PURPOSE_CODE:
            return self._error_resp('U39', 'Invalid purpose code for IoT')
        if not self._validate_device(dev):
            return self._error_resp('U37', 'Device details mismatch')
        spent = self.ledger.monthly_iot_spent(dev.get('ID',''), umn)
        amount = float(root.findtext('.//Amount') or 0)
        if spent + amount > IOT_MONTHLY_LIMIT:
            return self._error_resp('U32', 'Monthly IoT limit exceeded')
        if self._in_cooling_period(dev.get('ID',''), umn):
            return self._error_resp('U34', 'Cooling period active')
        return self.handle_push(xml_req)   # route as standard push

    def _validate_device(self, dev: dict) -> bool:
        required = {'TYPE', 'ID', 'APP', 'CAPABILITY'}
        return required.issubset(dev.keys()) and dev.get('TYPE') != 'MOB'

    def _in_cooling_period(self, device_id: str, umn: str) -> bool:
        link_ts = self.ledger.get_link_timestamp(device_id, umn)
        if not link_ts:
            return False
        return (time.time() - link_ts) < 86400   # 24 hours`,
        linesAffected: 42,
        effort: 'medium',
      },
      {
        path: 'psps/payer_psp.py',
        changeType: 'add-function',
        what: 'Add create_iot_mandate(), validate_device_details(), check_monthly_limit()',
        why: 'Payer PSP must create the authorization mandate when user links their IoT device from the primary UPI App, and validate device details on every transaction',
        codeBefore: `# psps/payer_psp.py (current)
class PayerPSP:
    def initiate_push_xml(self, payer_vpa, payee_vpa, amount, note, pin):
        ...
    def send_push(self, xml_req):
        return self.switch.handle_push(xml_req)`,
        codeAfter: `# psps/payer_psp.py (after change)
class PayerPSP:
    def initiate_push_xml(self, payer_vpa, payee_vpa, amount, note, pin):
        ...
    def send_push(self, xml_req):
        return self.switch.handle_push(xml_req)

    # NEW: IoT mandate creation
    def create_iot_mandate(self, primary_vpa: str, device_vpa: str,
                           device_id: str, app_id: str, mobile: str,
                           monthly_limit: float, validity_days: int, pin: str) -> dict:
        if monthly_limit > 15000:
            raise ValueError('Monthly limit cannot exceed ₹15,000')
        if not self.bank.auth_service.authorize(primary_vpa, pin):
            raise ValueError('Invalid UPI PIN')
        umn = f"UMN{uuid.uuid4().hex[:16].upper()}"
        mandate = {
            'umn': umn, 'primary_vpa': primary_vpa, 'device_vpa': device_vpa,
            'device_id': device_id, 'app_id': app_id, 'mobile': mobile,
            'monthly_limit': monthly_limit, 'validity_days': validity_days,
            'purpose': 'H', 'created_at': time.time(),
            'status': 'ACTIVE', 'monthly_spent': 0.0,
        }
        self.bank.register_iot_mandate(mandate)
        return mandate

    # NEW: Device transaction validation
    def validate_iot_transaction(self, device_vpa: str, device_id: str,
                                  app_id: str, amount: float) -> bool:
        mandate = self.bank.get_iot_mandate(device_vpa)
        if not mandate or mandate['status'] != 'ACTIVE':
            return False
        if mandate['device_id'] != device_id or mandate['app_id'] != app_id:
            return False   # U37
        return mandate['monthly_spent'] + amount <= mandate['monthly_limit']`,
        linesAffected: 38,
        effort: 'medium',
      },
      {
        path: 'banks/remitter_bank.py',
        changeType: 'add-function',
        what: 'Add register_iot_mandate(), get_iot_mandate(), process_iot_debit(), reset_monthly_limit()',
        why: 'Remitter bank stores IoT mandates, validates purpose code H debits, and resets monthly limits on anniversary date',
        codeBefore: `# banks/remitter_bank.py (current)
class RemitterBank:
    def debit(self, vpa, amount, rrn):
        ...
    def authorize(self, vpa, pin):
        ...`,
        codeAfter: `# banks/remitter_bank.py (after change)
class RemitterBank:
    def __init__(self, ...):
        ...
        self._iot_mandates: dict[str, dict] = {}  # NEW: device_vpa → mandate

    def debit(self, vpa, amount, rrn):
        ...
    def authorize(self, vpa, pin):
        ...

    # NEW: IoT mandate management
    def register_iot_mandate(self, mandate: dict):
        self._iot_mandates[mandate['device_vpa']] = mandate

    def get_iot_mandate(self, device_vpa: str) -> dict | None:
        return self._iot_mandates.get(device_vpa)

    def process_iot_debit(self, device_vpa: str, amount: float, rrn: str) -> bool:
        mandate = self._iot_mandates.get(device_vpa)
        if not mandate or mandate['status'] != 'ACTIVE':
            raise ValueError('IoT mandate not found or inactive')
        if mandate['monthly_spent'] + amount > mandate['monthly_limit']:
            raise ValueError('Monthly IoT limit exceeded')
        # Debit primary account holder (not device VPA)
        primary = mandate['primary_vpa']
        self.debit(primary, amount, rrn)
        mandate['monthly_spent'] += amount
        return True

    def reset_monthly_iot_limits(self):
        '''Called on anniversary date or 1st of month'''
        now = time.time()
        for m in self._iot_mandates.values():
            age = (now - m['created_at']) / (30 * 86400)
            if age >= int(age) and int(age) > 0:
                m['monthly_spent'] = 0.0`,
        linesAffected: 35,
        effort: 'medium',
      },
      {
        path: 'api/app.py',
        changeType: 'add',
        what: 'Add /iot/register-device, /iot/delegate-auth, /iot/devices, /iot/mandate/create, /iot/mandate/revoke endpoints',
        why: 'New HTTP API endpoints are needed for IoT device registration, mandate lifecycle, and delegate payment initiation',
        codeBefore: `# api/app.py (current)
@app.route("/push", methods=["POST"])
def push():
    ...

@app.route("/collect", methods=["POST"])
def collect():
    ...`,
        codeAfter: `# api/app.py (after — new endpoints added)
@app.route("/push", methods=["POST"])
def push():
    ...

@app.route("/collect", methods=["POST"])
def collect():
    ...

# ── NEW: IoT Device Registration ─────────────────────────────
@app.route("/iot/register-device", methods=["POST"])
def iot_register_device():
    d = request.json or {}
    mobile   = d.get("mobile", "").strip()
    device_id = d.get("device_id", "").strip()
    app_id   = d.get("app_id", "").strip()
    dev_type = d.get("device_type", "IOT_DEVICE")
    if not all([mobile, device_id, app_id]):
        return jsonify({"error": "mobile, device_id, app_id required"}), 400
    device_vpa = f"iot.{device_id[:8].lower()}@iotpsp"
    payee_psp.register_iot_device(mobile, device_id, app_id, dev_type, device_vpa)
    return jsonify({"device_vpa": device_vpa, "status": "registered"}), 200

# ── NEW: IoT Mandate Creation ─────────────────────────────────
@app.route("/iot/mandate/create", methods=["POST"])
def iot_mandate_create():
    d = request.json or {}
    try:
        mandate = payer_psp.create_iot_mandate(
            primary_vpa=d["primary_vpa"], device_vpa=d["device_vpa"],
            device_id=d["device_id"],    app_id=d["app_id"],
            mobile=d["mobile"],          monthly_limit=float(d.get("monthly_limit", 5000)),
            validity_days=int(d.get("validity_days", 180)), pin=d["pin"],
        )
        return jsonify({"umn": mandate["umn"], "status": "created"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

# ── NEW: IoT Delegate Auth (device-initiated payment) ─────────
@app.route("/iot/delegate-auth", methods=["POST"])
def iot_delegate_auth():
    xml_body = request.data.decode("utf-8")
    result = switch.handle_delegate_auth(xml_body)
    return jsonify(result), 200`,
        linesAffected: 55,
        effort: 'medium',
      },
      {
        path: 'api/templates/new_ui.html',
        changeType: 'add',
        what: 'Add IoT Device Management section: device list, link device flow, mandate dashboard',
        why: 'Users need to manage their linked IoT devices — view, modify limits, delink — directly from the UPI App frontend',
        codeAfter: `<!-- api/templates/new_ui.html — NEW section added -->
<!-- IoT Device Management Panel -->
<section id="iot-section" class="feature-section hidden">
  <div class="section-header">
    <h2>🔌 IoT Payments</h2>
    <p class="subtitle">Manage payments from your connected devices</p>
  </div>

  <!-- Linked Devices List -->
  <div id="iot-devices-list" class="devices-container">
    <div class="loading-state" id="iot-loading">Loading devices...</div>
  </div>

  <!-- Link New Device CTA -->
  <button class="primary-btn" onclick="openLinkDeviceModal()">
    + Link New Device
  </button>

  <!-- Link Device Modal -->
  <div id="link-device-modal" class="modal hidden">
    <div class="modal-content">
      <h3>Link IoT Device</h3>
      <input id="device-vpa" type="text" placeholder="Device UPI ID (scan QR from device)" />
      <input id="monthly-limit" type="number" placeholder="Monthly limit (max ₹15,000)" max="15000" />
      <select id="validity-period">
        <option value="90">3 Months</option>
        <option value="180" selected>6 Months</option>
        <option value="365">1 Year</option>
      </select>
      <input id="upi-pin" type="password" placeholder="Enter UPI PIN" maxlength="6" />
      <button class="primary-btn" onclick="linkDevice()">Authorize Device</button>
    </div>
  </div>
</section>`,
        linesAffected: 45,
        effort: 'low',
      },
      {
        path: 'api/static/app.js',
        changeType: 'add',
        what: 'Add loadIoTDevices(), linkDevice(), revokeDevice(), showIoTHistory() functions',
        why: 'Frontend JS needed for all IoT device management interactions in the new UI section',
        codeAfter: `// api/static/app.js — NEW IoT functions added

async function loadIoTDevices() {
  const mobile = getCurrentUserMobile();
  const resp = await fetch(\`/iot/devices/\${mobile}\`);
  const { devices = [] } = await resp.json();
  const container = document.getElementById('iot-devices-list');
  container.innerHTML = devices.length === 0
    ? '<p class="empty-state">No devices linked. Add one to get started.</p>'
    : devices.map(d => \`
      <div class="device-card \${d.status.toLowerCase()}">
        <div class="device-info">
          <span class="device-icon">📱</span>
          <div>
            <strong>\${d.device_type}</strong>
            <small>\${d.device_vpa}</small>
          </div>
        </div>
        <div class="device-limits">
          <span class="spent">₹\${d.monthly_spent} spent</span>
          <span class="limit">of ₹\${d.monthly_limit}</span>
          <div class="limit-bar">
            <div style="width:\${(d.monthly_spent/d.monthly_limit*100).toFixed(0)}%"></div>
          </div>
        </div>
        <button onclick="revokeDevice('\${d.umn}')" class="danger-btn">Delink</button>
      </div>\`).join('');
}

async function linkDevice() {
  const payload = {
    primary_vpa:   getCurrentUserVPA(),
    device_vpa:    document.getElementById('device-vpa').value.trim(),
    device_id:     extractDeviceId(document.getElementById('device-vpa').value),
    app_id:        'IOT_APP_V1',
    mobile:        getCurrentUserMobile(),
    monthly_limit: parseFloat(document.getElementById('monthly-limit').value) || 5000,
    validity_days: parseInt(document.getElementById('validity-period').value),
    pin:           document.getElementById('upi-pin').value,
  };
  const resp = await fetch('/iot/mandate/create', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const data = await resp.json();
  if (data.umn) {
    showToast('✅ Device linked! UMN: ' + data.umn);
    closeModal('link-device-modal');
    loadIoTDevices();
  } else {
    showToast('❌ ' + (data.error || 'Linking failed'), 'error');
  }
}`,
        linesAffected: 52,
        effort: 'medium',
      },
    ],
    newFiles: [
      { path: 'switch/iot_mandate_store.py', purpose: 'IoT mandate storage with monthly limit tracking and anniversary reset logic' },
      { path: 'api/schemas/iot_delegate_auth.xsd', purpose: 'XSD schema for ReqDelegateAuth XML message validation' },
    ],
    testFilePaths: [
      'test_iot_register.py',
      'test_iot_mandate_create.py',
      'test_iot_delegate_auth.py',
      'test_iot_cooling_period.py',
      'test_iot_monthly_limit.py',
    ],
    testCases: [
      { name: 'Device Registration', description: 'Verify secondary IoT device can be linked to primary VPA with monthly limit' },
      { name: 'Mandate Creation', description: 'Validate purpose code H mandate creation with UPI PIN authorization' },
      { name: 'Delegate Auth', description: 'Confirm IoT device can initiate payment using pre-authorized mandate' },
      { name: 'Cooling Period', description: 'Ensure 24-hour cooling period is enforced for new device links' },
      { name: 'Monthly Limit', description: 'Verify transaction declines once ₹15,000 monthly IoT limit is reached' },
    ],
  };
}

// ─── Biometric Feature Code Plan ─────────────────────────────────────────────

function biometricCodePlan(featureName: string): FeatureCodePlan {
  return {
    featureType: 'Biometric Authentication Enhancement',
    summary: `${featureName} requires replacing or augmenting PIN authentication in the remitter bank and payer PSP with biometric credential support. The switch and frontend also need updates to support biometric Cred type.`,
    newEndpoints: [
      'POST /biometric/enroll — enroll biometric credential for a VPA',
      'POST /biometric/verify — verify biometric during transaction',
    ],
    fileChanges: [
      {
        path: 'banks/remitter_bank.py',
        changeType: 'modify',
        what: 'Extend authorize() to accept biometric credential type alongside PIN',
        why: 'Current authorize() only supports PIN (MPIN subtype). Biometric requires FIDO/biometric token verification.',
        codeBefore: `def authorize(self, vpa: str, pin: str) -> bool:
    return self.auth_service.authorize(vpa, pin)`,
        codeAfter: `def authorize(self, vpa: str, credential: str,
              cred_type: str = 'PIN', liveness_score: float = 0.0) -> bool:
    if cred_type == 'BIOMETRIC':
        if liveness_score < 0.95:
            raise ValueError('Liveness score below threshold (0.95 required)')
        return self.auth_service.verify_biometric(vpa, credential)
    return self.auth_service.authorize(vpa, credential)`,
        linesAffected: 8,
        effort: 'medium',
      },
      {
        path: 'psps/payer_psp.py',
        changeType: 'modify',
        what: 'Add biometric cred support in initiate_push_xml()',
        why: 'ReqPay XML Cred element must support subType="BIOMETRIC" alongside existing MPIN',
        codeBefore: `def initiate_push_xml(self, payer_vpa, payee_vpa, amount, note, pin):
    if not self.bank.auth_service.authorize(payer_vpa, pin):
        raise ValueError("Invalid PIN")`,
        codeAfter: `def initiate_push_xml(self, payer_vpa, payee_vpa, amount, note,
                          credential: str, cred_type: str = 'PIN',
                          liveness_score: float = 0.0):
    if not self.bank.authorize(payer_vpa, credential, cred_type, liveness_score):
        raise ValueError(f"Authentication failed ({cred_type})")`,
        linesAffected: 6,
        effort: 'low',
      },
      {
        path: 'api/app.py',
        changeType: 'add',
        what: 'Add /biometric/enroll and /biometric/verify endpoints',
        why: 'New endpoints needed for biometric enrollment and verification flows',
        codeAfter: `@app.route("/biometric/enroll", methods=["POST"])
def biometric_enroll():
    d = request.json or {}
    vpa = d.get("vpa", "")
    template = d.get("biometric_template", "")
    if not vpa or not template:
        return jsonify({"error": "vpa and biometric_template required"}), 400
    remitter_bank.auth_service.enroll_biometric(vpa, template)
    return jsonify({"status": "enrolled", "vpa": vpa}), 200

@app.route("/biometric/verify", methods=["POST"])
def biometric_verify():
    d = request.json or {}
    score = remitter_bank.auth_service.verify_biometric(
        d.get("vpa"), d.get("template"), d.get("liveness_score", 0)
    )
    return jsonify({"verified": score >= 0.95, "score": score}), 200`,
        linesAffected: 18,
        effort: 'low',
      },
      {
        path: 'api/templates/new_ui.html',
        changeType: 'modify',
        what: 'Add biometric enrollment UI and replace PIN input with biometric option',
        why: 'Users need to enroll biometric and choose biometric vs PIN during payment',
        codeAfter: `<!-- Biometric option in payment flow -->
<div class="auth-choice">
  <button class="auth-tab active" data-type="PIN" onclick="switchAuth('PIN')">🔐 PIN</button>
  <button class="auth-tab" data-type="BIOMETRIC" onclick="switchAuth('BIOMETRIC')">👆 Biometric</button>
</div>
<div id="pin-auth" class="auth-section">
  <input type="password" id="upi-pin" placeholder="Enter UPI PIN" maxlength="6" />
</div>
<div id="biometric-auth" class="auth-section hidden">
  <div class="biometric-prompt">
    <div class="fingerprint-icon">👆</div>
    <p>Place your finger on the sensor</p>
    <button onclick="triggerBiometric()">Scan Fingerprint</button>
  </div>
</div>`,
        linesAffected: 20,
        effort: 'low',
      },
    ],
    newFiles: [
      { path: 'agents/skills/biometric_skill.py', purpose: 'Agent skill for biometric enrollment and verification flows' },
    ],
    testFilePaths: ['test_biometric_enroll.py', 'test_biometric_verify.py', 'test_biometric_liveness.py'],
    testCases: [
      { name: 'Credential Enrollment', description: 'Verify FIDO/Biometric template can be securely enrolled for a VPA' },
      { name: 'Biometric Auth', description: 'Validate transaction authorization using biometric token instead of PIN' },
      { name: 'Liveness Check', description: 'Ensure spoofing attempts are blocked by liveness score threshold (0.95)' },
    ],
  };
}

// ─── A2A Feature Code Plan ────────────────────────────────────────────────────

function a2aCodePlan(featureName: string): FeatureCodePlan {
  return {
    featureType: 'UPI A2A (Account-to-Account) Payments',
    summary: `${featureName} requires enhanced P2P routing with AI-assisted beneficiary validation, expanded transaction corridors, and real-time fraud scoring at the switch level.`,
    newEndpoints: [
      'POST /a2a/validate-corridor — validate A2A payment corridor',
      'POST /a2a/fraud-score — get AI fraud score before transaction',
      'GET  /a2a/corridors — list available A2A payment corridors',
    ],
    fileChanges: [
      {
        path: 'switch/upi_switch.py',
        changeType: 'modify',
        what: 'Add A2A corridor validation and fraud scoring in handle_push()',
        why: 'A2A Phase 2 introduces new corridors (cross-bank, NRE accounts) and AI fraud scoring pre-clearance',
        codeBefore: `def handle_push(self, xml_req: str):
    root = ET.fromstring(xml_req)
    # existing validation
    ...`,
        codeAfter: `def handle_push(self, xml_req: str):
    root = ET.fromstring(xml_req)
    payer = root.findtext('.//Payer[@addr]') or root.find('Payer').get('addr')
    payee = root.findtext('.//Payees/Payee[@addr]') or root.find('.//Payee').get('addr')
    amount = float(root.findtext('.//Amount') or 0)

    # NEW: A2A corridor validation
    corridor = self._detect_corridor(payer, payee)
    if not self._is_corridor_allowed(corridor):
        return self._error_resp('U40', f'Corridor {corridor} not enabled')

    # NEW: AI fraud scoring
    fraud_score = self.fraud_engine.score(payer, payee, amount, corridor)
    if fraud_score > 0.85:
        return self._error_resp('U41', 'Transaction flagged by AI fraud engine')

    # existing validation continues ...`,
        linesAffected: 16,
        effort: 'medium',
      },
      {
        path: 'api/app.py',
        changeType: 'add',
        what: 'Add A2A corridor management and fraud scoring endpoints',
        why: 'New A2A Phase 2 API surface',
        codeAfter: `@app.route("/a2a/validate-corridor", methods=["POST"])
def a2a_validate_corridor():
    d = request.json or {}
    corridor = switch._detect_corridor(d.get("payer_vpa"), d.get("payee_vpa"))
    allowed = switch._is_corridor_allowed(corridor)
    return jsonify({"corridor": corridor, "allowed": allowed}), 200

@app.route("/a2a/fraud-score", methods=["POST"])
def a2a_fraud_score():
    d = request.json or {}
    score = switch.fraud_engine.score(
        d.get("payer_vpa"), d.get("payee_vpa"),
        d.get("amount", 0), d.get("corridor", "P2P")
    )
    return jsonify({"fraud_score": score, "flagged": score > 0.85}), 200`,
        linesAffected: 16,
        effort: 'low',
      },
    ],
    newFiles: [
      { path: 'switch/fraud_engine.py', purpose: 'AI-based real-time fraud scoring engine for A2A transactions' },
      { path: 'switch/corridor_registry.py', purpose: 'A2A payment corridor registry with allowed corridor configuration' },
    ],
    testFilePaths: ['test_a2a_corridor.py', 'test_a2a_fraud_score.py', 'test_a2a_highvalue.py'],
    testCases: [
      { name: 'Corridor Validation', description: 'Verify cross-bank and NRE account corridors are correctly identified' },
      { name: 'Fraud Scoring', description: 'Validate pre-clearance fraud scoring for high-value A2A transfers' },
      { name: 'Velocity Checks', description: 'Ensure daily and per-transaction velocity limits are enforced per corridor' },
    ],
  };
}

// ─── Credit Line Feature Code Plan ────────────────────────────────────────────

function creditCodePlan(featureName: string): FeatureCodePlan {
  return {
    featureType: 'UPI Credit Line / BNPL Payments',
    summary: `${featureName} requires adding credit line account support across UPI: credit eligibility check at PSP level, credit disbursement at issuer bank, credit-specific routing at switch, and a credit dashboard UI at the frontend.`,
    newEndpoints: [
      'POST /credit/check-eligibility — check customer credit eligibility',
      'POST /credit/disburse — initiate credit line disbursement for payment',
      'GET  /credit/dashboard/:vpa — credit usage dashboard',
      'POST /credit/emi/convert — convert transaction to EMI',
    ],
    fileChanges: [
      {
        path: 'switch/upi_switch.py',
        changeType: 'add-function',
        what: 'Add handle_credit_pay() with credit limit validation and RCC account routing',
        why: 'Switch must route credit line transactions differently — validate credit limit at issuer, enforce per-txn and daily caps, apply credit-specific fraud scoring',
        codeAfter: `# switch/upi_switch.py (after change)
CREDIT_PURPOSE_CODE = 'CREDIT'
CREDIT_MAX_TXN = 200_000

class UPISwitch:
    def handle_credit_pay(self, xml_req: str):
        root = ET.fromstring(xml_req)
        payer = root.find('Payer').get('addr')
        amount = float(root.findtext('.//Amount') or 0)
        account_type = root.findtext('.//AccountType') or 'SAVINGS'
        if account_type not in ('CREDIT', 'RCC'):
            return self._error_resp('U80', 'Invalid account type for credit payment')
        if amount > CREDIT_MAX_TXN:
            return self._error_resp('U81', 'Credit transaction limit exceeded')
        credit_info = self._check_credit_limit(payer, amount)
        if not credit_info['eligible']:
            return self._error_resp('U82', 'Credit limit insufficient')
        return self.handle_push(xml_req)

    def _check_credit_limit(self, vpa: str, amount: float) -> dict:
        limit = self.ledger.get_credit_limit(vpa)
        used = self.ledger.get_credit_used(vpa)
        return {'eligible': (limit - used) >= amount, 'available': limit - used}`,
        linesAffected: 28,
        effort: 'medium',
      },
      {
        path: 'banks/remitter_bank.py',
        changeType: 'add-function',
        what: 'Add credit_disburse(), get_credit_limit(), convert_to_emi()',
        why: 'Remitter bank must support credit line accounts — real-time credit check, disbursement against credit line, and EMI conversion post-transaction',
        codeAfter: `# banks/remitter_bank.py (after change)
class RemitterBank:
    def __init__(self, ...):
        ...
        self._credit_lines: dict[str, dict] = {}

    def credit_disburse(self, vpa: str, amount: float, merchant_vpa: str, rrn: str) -> dict:
        cl = self._credit_lines.get(vpa)
        if not cl or cl['available'] < amount:
            raise ValueError('Credit limit insufficient')
        cl['available'] -= amount
        cl['used'] += amount
        self.debit(vpa, amount, rrn)
        return {'rrn': rrn, 'remaining_limit': cl['available'], 'emi_eligible': amount >= 3000}

    def convert_to_emi(self, vpa: str, rrn: str, tenure_months: int) -> dict:
        txn = self.ledger.get_by_rrn(rrn)
        emi_amount = txn['amount'] / tenure_months
        return {'emi_amount': round(emi_amount, 2), 'tenure': tenure_months, 'total_interest': round(txn['amount'] * 0.01 * tenure_months, 2)}`,
        linesAffected: 25,
        effort: 'medium',
      },
      {
        path: 'psps/payer_psp.py',
        changeType: 'add-function',
        what: 'Add check_credit_eligibility(), initiate_credit_payment()',
        why: 'Payer PSP must check credit eligibility before initiating payment from credit line account',
        codeAfter: `# psps/payer_psp.py (after change)
class PayerPSP:
    def check_credit_eligibility(self, vpa: str, amount: float) -> dict:
        return self.bank.get_credit_info(vpa, amount)

    def initiate_credit_payment(self, payer_vpa: str, payee_vpa: str,
                                 amount: float, pin: str, account_type: str = 'CREDIT') -> dict:
        if not self.bank.auth_service.authorize(payer_vpa, pin):
            raise ValueError('Invalid UPI PIN')
        xml = self._build_credit_xml(payer_vpa, payee_vpa, amount, account_type)
        return self.switch.handle_credit_pay(xml)`,
        linesAffected: 15,
        effort: 'low',
      },
      {
        path: 'api/app.py',
        changeType: 'add',
        what: 'Add /credit/check-eligibility, /credit/disburse, /credit/dashboard, /credit/emi/convert endpoints',
        why: 'New HTTP endpoints for credit line payment flow',
        codeAfter: `@app.route("/credit/check-eligibility", methods=["POST"])
def credit_check():
    d = request.json or {}
    result = payer_psp.check_credit_eligibility(d.get("vpa"), float(d.get("amount", 0)))
    return jsonify(result), 200

@app.route("/credit/disburse", methods=["POST"])
def credit_disburse():
    d = request.json or {}
    try:
        result = payer_psp.initiate_credit_payment(
            d["payer_vpa"], d["payee_vpa"], float(d["amount"]), d["pin"], "CREDIT"
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/credit/emi/convert", methods=["POST"])
def credit_emi_convert():
    d = request.json or {}
    result = remitter_bank.convert_to_emi(d["vpa"], d["rrn"], int(d.get("tenure", 3)))
    return jsonify(result), 200`,
        linesAffected: 28,
        effort: 'low',
      },
      {
        path: 'api/templates/new_ui.html',
        changeType: 'add',
        what: 'Add Credit Line dashboard with credit limit, EMI tracker, and payment flow',
        why: 'Users need to view credit limits, make payments from credit, and manage EMIs',
        codeAfter: `<section id="credit-section" class="feature-section hidden">
  <div class="section-header"><h2>💳 Credit Line Payments</h2></div>
  <div class="credit-overview">
    <div class="credit-limit-card">
      <div class="limit-circle"><span id="credit-available">₹38,000</span></div>
      <div class="credit-details">Total: ₹50,000 | Used: ₹12,000</div>
    </div>
  </div>
  <div class="emi-section"><h3>Active EMIs</h3><div id="emi-list"></div></div>
  <button onclick="openCreditPayModal()" class="primary-btn">Pay with Credit</button>
</section>`,
        linesAffected: 20,
        effort: 'low',
      },
    ],
    newFiles: [
      { path: 'switch/credit_limit_store.py', purpose: 'Credit limit storage, real-time available balance tracking, EMI schedule management' },
      { path: 'api/schemas/upi_credit_request.xsd', purpose: 'XSD schema for credit line payment XML with AccountType=CREDIT/RCC' },
    ],
    testFilePaths: [
      'test_credit_eligibility.py',
      'test_credit_payment.py',
      'test_credit_limit_enforcement.py',
      'test_credit_emi_conversion.py',
    ],
    testCases: [
      { name: 'Eligibility Check', description: 'Verify real-time credit limit check before payment initiation' },
      { name: 'Credit Disbursement', description: 'Validate successful debit from RCC/Credit account type' },
      { name: 'Limit Enforcement', description: 'Ensure transaction declines if total credit used exceeds sanctioned limit' },
      { name: 'EMI Conversion', description: 'Check post-transaction EMI conversion logic and interest calculation' },
    ],
  };
}

// ─── Mandate / Reserve Pay (SBMD) Code Plan ──────────────────────────────────

function mandateCodePlan(featureName: string): FeatureCodePlan {
  return {
    featureType: 'UPI Reserve Pay / Single Block Multiple Debits (SBMD)',
    summary: `${featureName} requires block-based payment support: block creation at switch, block accounting at remitter bank, partial debit trigger from merchant, and block management UI at frontend.`,
    newEndpoints: [
      'POST /reserve/create — create a fund block for a merchant',
      'POST /reserve/debit — merchant triggers partial debit against block',
      'POST /reserve/revoke — customer revokes active block',
      'GET  /reserve/blocks/:vpa — list all blocks for a customer',
    ],
    fileChanges: [
      {
        path: 'switch/upi_switch.py',
        changeType: 'add-function',
        what: 'Add handle_block_create(), handle_block_debit(), validate_block_limits()',
        why: 'Switch must manage block lifecycle — create, partial debit, revoke, expiry — with DSC validation and merchant eligibility checks',
        codeAfter: `# switch/upi_switch.py (after change)
BLOCK_MAX_AMOUNT = 200_000
BLOCK_MAX_DURATION_DAYS = 90

class UPISwitch:
    def handle_block_create(self, xml_req: str) -> dict:
        root = ET.fromstring(xml_req)
        amount = float(root.findtext('.//Block[@amount]') or root.find('.//Block').get('amount', '0'))
        merchant = root.findtext('.//Payee[@addr]') or root.find('.//Payee').get('addr', '')
        if amount > BLOCK_MAX_AMOUNT:
            return self._error_resp('U69', 'Block limit exceeded')
        if not self._is_merchant_eligible(merchant):
            return self._error_resp('U73', 'Merchant not authorized for blocks')
        risk_score = self.fraud_engine.score_block(root)
        if risk_score > 0.85:
            return self._error_resp('U16', 'Risk threshold exceeded')
        block_id = f"BLK{uuid.uuid4().hex[:12].upper()}"
        self.ledger.create_block(block_id, root)
        self._notify_customer('block_created', block_id, amount, merchant)
        return {'block_id': block_id, 'status': 'ACTIVE', 'amount': amount}

    def handle_block_debit(self, xml_req: str) -> dict:
        root = ET.fromstring(xml_req)
        block_ref = root.findtext('.//Txn[@blockRef]') or root.find('.//Txn').get('blockRef', '')
        amount = float(root.findtext('.//Amount') or 0)
        block = self.ledger.get_block(block_ref)
        if not block or block['status'] not in ('ACTIVE', 'PARTIALLY_DEBITED'):
            return self._error_resp('U72', 'Block not active')
        if amount > block['available_amount']:
            return self._error_resp('U69', 'Debit exceeds remaining block')
        self.ledger.debit_block(block_ref, amount)
        return self.handle_push(xml_req)`,
        linesAffected: 40,
        effort: 'high',
      },
      {
        path: 'banks/remitter_bank.py',
        changeType: 'add-function',
        what: 'Add create_block(), debit_block(), revoke_block(), get_blocks()',
        why: 'Remitter bank must reserve funds (block), process partial debits, handle revocations, and reconcile block amounts with available balance',
        codeAfter: `# banks/remitter_bank.py (after change)
class RemitterBank:
    def __init__(self, ...):
        ...
        self._blocks: dict[str, dict] = {}

    def create_block(self, block_id: str, payer_vpa: str, amount: float, merchant: str, validity_days: int):
        balance = self.get_balance(payer_vpa)
        if balance < amount:
            raise ValueError('Insufficient balance for block')
        self._blocks[block_id] = {
            'payer_vpa': payer_vpa, 'amount': amount, 'available': amount,
            'merchant': merchant, 'status': 'ACTIVE',
            'created_at': time.time(), 'valid_until': time.time() + validity_days * 86400,
        }
        self._reduce_available_balance(payer_vpa, amount)
        return block_id

    def debit_block(self, block_id: str, amount: float, rrn: str) -> dict:
        block = self._blocks.get(block_id)
        if not block:
            raise ValueError('Block not found')
        block['available'] -= amount
        if block['available'] <= 0:
            block['status'] = 'FULLY_DEBITED'
        else:
            block['status'] = 'PARTIALLY_DEBITED'
        return {'rrn': rrn, 'remaining': block['available']}

    def revoke_block(self, block_id: str) -> dict:
        block = self._blocks.get(block_id)
        if not block:
            raise ValueError('Block not found')
        restored = block['available']
        self._restore_available_balance(block['payer_vpa'], restored)
        block['status'] = 'REVOKED'
        return {'restored_amount': restored}`,
        linesAffected: 38,
        effort: 'high',
      },
      {
        path: 'api/app.py',
        changeType: 'add',
        what: 'Add /reserve/create, /reserve/debit, /reserve/revoke, /reserve/blocks endpoints',
        why: 'HTTP API endpoints for full block lifecycle management',
        codeAfter: `@app.route("/reserve/create", methods=["POST"])
def reserve_create():
    d = request.json or {}
    try:
        result = switch.handle_block_create(build_block_xml(d))
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/reserve/debit", methods=["POST"])
def reserve_debit():
    d = request.json or {}
    result = switch.handle_block_debit(build_debit_xml(d))
    return jsonify(result), 200

@app.route("/reserve/revoke", methods=["POST"])
def reserve_revoke():
    d = request.json or {}
    result = remitter_bank.revoke_block(d["block_id"])
    return jsonify(result), 200`,
        linesAffected: 25,
        effort: 'medium',
      },
      {
        path: 'api/templates/new_ui.html',
        changeType: 'add',
        what: 'Add Reserve Pay section: block creation form, active blocks list, block detail view',
        why: 'Users need to create fund blocks, view active reserves, and manage revocations',
        codeAfter: `<section id="reserve-section" class="feature-section hidden">
  <div class="section-header"><h2>🔒 Reserve Pay</h2></div>
  <div id="active-blocks" class="blocks-list"></div>
  <button onclick="openCreateBlockModal()" class="primary-btn">+ Create Reserve</button>
  <div id="create-block-modal" class="modal hidden">
    <input placeholder="Merchant VPA" id="block-merchant" />
    <input type="number" placeholder="Amount (₹)" id="block-amount" />
    <select id="block-validity"><option value="7">7 days</option><option value="15">15 days</option><option value="30">30 days</option></select>
    <input type="password" placeholder="UPI PIN" id="block-pin" maxlength="6" />
    <button onclick="createBlock()" class="primary-btn">Reserve Funds</button>
  </div>
</section>`,
        linesAffected: 22,
        effort: 'low',
      },
    ],
    newFiles: [
      { path: 'switch/block_registry.py', purpose: 'Block lifecycle management — creation, debit, revocation, expiry, and reconciliation' },
      { path: 'api/schemas/upi_block_request.xsd', purpose: 'XSD schema for ReqPay BLOCK_DEBIT and ReqDebit XML messages' },
    ],
    testFilePaths: [
      'test_block_create.py',
      'test_block_partial_debit.py',
      'test_block_revoke.py',
      'test_block_expiry.py',
      'test_block_limits.py',
    ],
    testCases: [
      { name: 'Block Creation', description: 'Verify fund reservation (SBMD) with explicit customer consent' },
      { name: 'Partial Debit', description: 'Validate merchant-triggered debit against active fund block' },
      { name: 'Block Revocation', description: 'Ensure customer can release blocked funds back to available balance' },
      { name: 'Expiry Management', description: 'Verify automatic block expiry after 90 days or per-mandate duration' },
    ],
  };
}

// ─── Offline Payments Code Plan ──────────────────────────────────────────────

function offlineCodePlan(featureName: string): FeatureCodePlan {
  return {
    featureType: 'UPI Offline / Low-Connectivity Payments',
    summary: `${featureName} requires pre-authorized token generation at the PSP, offline token storage on device, NFC-based offline payment processing, and delayed settlement reconciliation at the switch.`,
    newEndpoints: [
      'POST /offline/generate-token — generate pre-authorized payment token',
      'POST /offline/redeem — redeem offline token (when back online)',
      'GET  /offline/tokens/:vpa — list active offline tokens',
      'POST /offline/sync — sync offline transactions when connectivity restored',
    ],
    fileChanges: [
      {
        path: 'switch/upi_switch.py',
        changeType: 'add-function',
        what: 'Add handle_offline_redeem(), reconcile_offline_transactions()',
        why: 'Switch must handle delayed settlement of offline tokens — validate token authenticity, process redemption, and reconcile with bank ledger when device syncs',
        codeAfter: `# switch/upi_switch.py (after change)
OFFLINE_TOKEN_MAX = 500
OFFLINE_TOKEN_VALIDITY_HOURS = 48

class UPISwitch:
    def handle_offline_redeem(self, token_data: dict) -> dict:
        token_id = token_data.get('token_id')
        amount = token_data.get('amount', 0)
        if not self._validate_token_signature(token_data):
            return self._error_resp('U60', 'Invalid offline token signature')
        if self._is_token_expired(token_data):
            return self._error_resp('U61', 'Offline token expired')
        if self._is_token_already_redeemed(token_id):
            return self._error_resp('U62', 'Token already redeemed')
        self.ledger.record_offline_redemption(token_data)
        return self.handle_push(self._build_offline_pay_xml(token_data))

    def reconcile_offline_transactions(self, device_txns: list) -> dict:
        reconciled = 0
        for txn in device_txns:
            if not self._is_token_already_redeemed(txn['token_id']):
                self.handle_offline_redeem(txn)
                reconciled += 1
        return {'reconciled': reconciled, 'total': len(device_txns)}`,
        linesAffected: 30,
        effort: 'high',
      },
      {
        path: 'psps/payer_psp.py',
        changeType: 'add-function',
        what: 'Add generate_offline_token(), store_token_on_device()',
        why: 'Payer PSP pre-authorizes tokens while online that can be used offline — token signed with PSP key, amount capped at ₹500',
        codeAfter: `# psps/payer_psp.py (after change)
class PayerPSP:
    def generate_offline_token(self, vpa: str, amount: float, pin: str, validity_hours: int = 24) -> dict:
        if amount > 500:
            raise ValueError('Offline token max is ₹500')
        if not self.bank.auth_service.authorize(vpa, pin):
            raise ValueError('Invalid UPI PIN')
        self.bank.debit(vpa, amount, f"OFL{uuid.uuid4().hex[:10]}")
        token = {
            'token_id': f"TKN{uuid.uuid4().hex[:16].upper()}",
            'vpa': vpa, 'amount': amount,
            'created_at': time.time(),
            'valid_until': time.time() + validity_hours * 3600,
            'signature': self._sign_token(vpa, amount),
            'status': 'ACTIVE',
        }
        return token`,
        linesAffected: 20,
        effort: 'medium',
      },
      {
        path: 'api/app.py',
        changeType: 'add',
        what: 'Add /offline/generate-token, /offline/redeem, /offline/tokens, /offline/sync endpoints',
        why: 'HTTP API for offline token lifecycle',
        codeAfter: `@app.route("/offline/generate-token", methods=["POST"])
def offline_generate_token():
    d = request.json or {}
    try:
        token = payer_psp.generate_offline_token(
            d["vpa"], float(d.get("amount", 200)), d["pin"],
            int(d.get("validity_hours", 24))
        )
        return jsonify(token), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/offline/sync", methods=["POST"])
def offline_sync():
    txns = request.json.get("transactions", [])
    result = switch.reconcile_offline_transactions(txns)
    return jsonify(result), 200`,
        linesAffected: 20,
        effort: 'low',
      },
      {
        path: 'api/templates/new_ui.html',
        changeType: 'add',
        what: 'Add Offline Payments section: token generation, active tokens list, sync status',
        why: 'Users need to generate offline tokens while online and view/manage them',
        codeAfter: `<section id="offline-section" class="feature-section hidden">
  <div class="section-header"><h2>📴 Offline Payments</h2></div>
  <div class="offline-status"><span class="connectivity-indicator"></span> Online</div>
  <div id="active-tokens" class="tokens-list"></div>
  <button onclick="generateOfflineToken()" class="primary-btn">+ Generate Token</button>
  <div class="sync-section">
    <button onclick="syncOfflineTxns()" class="secondary-btn">Sync Offline Transactions</button>
    <span id="sync-status">All synced ✓</span>
  </div>
</section>`,
        linesAffected: 18,
        effort: 'low',
      },
    ],
    newFiles: [
      { path: 'switch/offline_token_store.py', purpose: 'Offline token storage, signature validation, and redemption tracking' },
      { path: 'api/schemas/upi_offline_token.xsd', purpose: 'Schema for offline payment token XML structure' },
    ],
    testFilePaths: [
      'test_offline_token_generate.py',
      'test_offline_token_redeem.py',
      'test_offline_token_expiry.py',
      'test_offline_sync.py',
      'test_offline_double_spend.py',
    ],
    testCases: [
      { name: 'Token Generation', description: 'Verify pre-authorized offline token generation (max ₹500)' },
      { name: 'Offline Redemption', description: 'Validate token signature and redemption at merchant NFC terminal' },
      { name: 'Sync & Reconcile', description: 'Ensure offline transactions are correctly settled when connectivity returns' },
      { name: 'Double Spend Guard', description: 'Verify token cannot be reused or spent beyond its pre-authorized value' },
    ],
  };
}

// ─── Generic Feature Code Plan ────────────────────────────────────────────────

function genericCodePlan(featureName: string): FeatureCodePlan {
  return {
    featureType: 'New UPI Feature',
    summary: `${featureName} requires changes across the UPI switch for transaction routing, PSP layers for request validation, remitter bank for debit authorization, and the frontend for user-facing flows.`,
    newEndpoints: [
      `POST /feature/initiate — initiate ${featureName} transaction`,
      `GET  /feature/status/:id — check transaction status`,
    ],
    fileChanges: [
      {
        path: 'switch/upi_switch.py',
        changeType: 'modify',
        what: `Add ${featureName} transaction type handling in handle_push()`,
        why: `Switch must recognize new transaction purpose code and apply feature-specific routing and limit logic`,
        codeAfter: `# New purpose code constant
FEATURE_PURPOSE_CODE = 'NEW_CODE'

class UPISwitch:
    def handle_push(self, xml_req: str):
        purpose = self._extract_purpose(xml_req)
        if purpose == FEATURE_PURPOSE_CODE:
            return self._handle_feature_transaction(xml_req)
        # existing flow continues
        ...

    def _handle_feature_transaction(self, xml_req: str):
        # Feature-specific validation and routing
        ...`,
        linesAffected: 20,
        effort: 'medium',
      },
      {
        path: 'psps/payer_psp.py',
        changeType: 'modify',
        what: `Add feature-specific request creation and validation`,
        why: `Payer PSP must support new request type for ${featureName}`,
        codeAfter: `def initiate_feature_request(self, payer_vpa, payee_vpa, amount, pin, feature_params):
    # Validate feature-specific parameters
    ...
    # Build feature XML request
    xml = self._build_feature_xml(payer_vpa, payee_vpa, amount, feature_params)
    return self.switch.handle_push(xml)`,
        linesAffected: 15,
        effort: 'low',
      },
      {
        path: 'banks/remitter_bank.py',
        changeType: 'add-function',
        what: `Add feature-specific debit authorization and validation`,
        why: `Remitter bank must support ${featureName}-specific validation before debit`,
        codeAfter: `def authorize_feature(self, vpa: str, pin: str, feature_params: dict) -> bool:
    if not self.auth_service.authorize(vpa, pin):
        return False
    # Feature-specific validation
    return self._validate_feature_constraints(vpa, feature_params)`,
        linesAffected: 10,
        effort: 'low',
      },
      {
        path: 'api/app.py',
        changeType: 'add',
        what: `Add /feature/initiate and /feature/status endpoints`,
        why: `New HTTP endpoints for ${featureName} flow`,
        codeAfter: `@app.route("/feature/initiate", methods=["POST"])
def feature_initiate():
    d = request.json or {}
    try:
        result = payer_psp.initiate_feature_request(
            d["payer_vpa"], d["payee_vpa"], d["amount"], d["pin"], d
        )
        return jsonify({"status": "success", "rrn": result.get("rrn")}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/feature/status/<txn_id>")
def feature_status(txn_id):
    txn = switch.ledger.get_by_id(txn_id)
    return jsonify(txn or {"error": "Not found"}), 200 if txn else 404`,
        linesAffected: 18,
        effort: 'low',
      },
      {
        path: 'api/templates/new_ui.html',
        changeType: 'add',
        what: `Add ${featureName} UI section with form, history, and management`,
        why: `Users need a dedicated UI flow for ${featureName}`,
        codeAfter: `<section id="feature-section" class="feature-section hidden">
  <h2>${featureName}</h2>
  <div class="feature-form">
    <input placeholder="Payee VPA" id="feat-payee" />
    <input type="number" placeholder="Amount" id="feat-amount" />
    <input type="password" placeholder="UPI PIN" id="feat-pin" maxlength="6" />
    <button onclick="initiateFeature()" class="primary-btn">Proceed</button>
  </div>
  <div id="feature-history" class="history-section"></div>
</section>`,
        linesAffected: 16,
        effort: 'low',
      },
    ],
    newFiles: [],
    testFilePaths: ['test_feature_happy_path.py', 'test_feature_negative.py', 'test_feature_limits.py'],
    testCases: [
      { name: 'Happy Path', description: 'Verify successful end-to-end execution of the new feature flow' },
      { name: 'Negative Testing', description: 'Validate error handling for invalid parameters and auth failures' },
      { name: 'Limit Validation', description: 'Ensure business rule limits are correctly enforced for the new feature' },
    ],
  };
}

// ─── Feature plan dispatcher ──────────────────────────────────────────────────

const FEATURE_CODE_PLANS: Record<FeatureType, (name: string) => FeatureCodePlan> = {
  iot: iotCodePlan,
  biometric: biometricCodePlan,
  a2a: a2aCodePlan,
  credit: creditCodePlan,
  mandate: mandateCodePlan,
  offline: offlineCodePlan,
  generic: genericCodePlan,
};

// ─── Summary helpers ──────────────────────────────────────────────────────────

export function getFilesTouched(plan: FeatureCodePlan): string[] {
  return [
    ...plan.fileChanges.map(fc => fc.path),
    ...plan.newFiles.map(nf => nf.path),
  ];
}

export function getTotalLinesAffected(plan: FeatureCodePlan): number {
  return plan.fileChanges.reduce((sum, fc) => sum + (fc.linesAffected || 0), 0);
}

export function getLayerSummary(plan: FeatureCodePlan): Record<string, number> {
  const byLayer: Record<string, number> = {};
  for (const fc of plan.fileChanges) {
    const file = UPI_CODEBASE.find(f => f.path === fc.path);
    const layer = file?.layer || 'unknown';
    byLayer[layer] = (byLayer[layer] || 0) + 1;
  }
  return byLayer;
}
