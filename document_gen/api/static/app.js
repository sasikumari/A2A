function $(sel) { return document.querySelector(sel); }
function setOutput(id, data) {
  const el = $(id);
  if (!el) return;
  if (typeof data === 'string') el.textContent = data;
  else el.textContent = JSON.stringify(data, null, 2);
}

// Tabs
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    const panel = document.getElementById(btn.dataset.tab);
    if (panel) panel.classList.add('active');
  });
});

function buildReqPayXML({ payer, payee, amount, note, pin, purpose, type = 'PAY' }) {
  const ts = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  const esc = (s) => (s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
  const pinBlock = pin ? `<upi:Creds><upi:Cred><upi:Data code="${esc(pin)}"/></upi:Cred></upi:Creds>` : '';
  const purposeXML = purpose ? `<upi:purpose>${esc(purpose)}</upi:purpose><upi:purposeCode code="${esc(purpose)}" description="UPI Purpose ${esc(purpose)}"/>` : '';
  return `<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqPay xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="1.0" ts="${ts}" orgId="PAYERPSP" msgId="REQUI" prodType="UPI"/>
  <upi:Txn id="REQ-${Date.now()}" type="${esc(type)}" note="${esc(note || '')}"/>
  ${purposeXML}
  <upi:Payer addr="${esc(payer)}">
    <upi:Amount value="${Number(amount).toFixed(2)}"/>
    ${pinBlock}
  </upi:Payer>
  <upi:Payees>
    <upi:Payee addr="${esc(payee)}"/>
  </upi:Payees>
</upi:ReqPay>`;
}

function buildCollectXML({ payer, payee, amount, note, purpose }) {
  const esc = (s) => (s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
  const purposeXML = purpose ? `<PurposeCode>${esc(purpose)}</PurposeCode>` : '';
  return `<?xml version="1.0" encoding="UTF-8"?>
<CollectRequest>
  <PayeeVPA>${esc(payee)}</PayeeVPA>
  <PayerVPA>${esc(payer)}</PayerVPA>
  <Amount>${Number(amount).toFixed(2)}</Amount>
  <Note>${esc(note || '')}</Note>
  ${purposeXML}
</CollectRequest>`;
}

function buildValAddXML({ payer, payee }) {
  const ts = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  const esc = (s) => (s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
  return `<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqValAdd xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="1.0" ts="${ts}" orgId="PAYERPSP" msgId="VALUI" prodType="UPI"/>
  <upi:Txn id="VAL-${Date.now()}" type="ValAdd"/>
  <upi:Payer addr="${esc(payer)}"/>
  <upi:Payee addr="${esc(payee)}"/>
</upi:ReqValAdd>`;
}

// ---- ValAdd-first flow state for Pay tab ----
let lastValidatedPayee = '';
let lastValAddOk = false;

function parseRespValAdd(xmlText) {
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xmlText, 'application/xml');
    const resp = doc.getElementsByTagNameNS('http://npci.org/upi/schema/', 'Resp')[0] || doc.getElementsByTagName('Resp')[0];
    if (!resp) return { ok: false, message: 'Invalid RespValAdd' };
    const result = resp.getAttribute('result') || '';
    const ifsc = resp.getAttribute('IFSC') || '';
    const accType = resp.getAttribute('accType') || '';
    const maskName = resp.getAttribute('maskName') || '';
    return { ok: result === 'SUCCESS', ifsc, accType, maskName, message: result };
  } catch {
    return { ok: false, message: 'Parse error' };
  }
}

async function validatePayeeOnUI(payer, payee) {
  const infoRow = $('#payeeInfoRow');
  const infoEl = $('#payeeInfo');
  if (infoRow) infoRow.style.display = 'block';
  if (infoEl) infoEl.textContent = 'Validating payee address...';
  $('#payButton').disabled = true;
  lastValAddOk = false;
  lastValidatedPayee = '';
  try {
    const xml = buildValAddXML({ payer, payee });
    const respXML = await postXML('/validate-address', xml, true);
    const parsed = parseRespValAdd(respXML);
    if (parsed.ok) {
      lastValAddOk = true;
      lastValidatedPayee = payee;
      const parts = [];
      if (parsed.maskName) parts.push(`Name: ${parsed.maskName}`);
      if (parsed.ifsc) parts.push(`IFSC: ${parsed.ifsc}`);
      if (parsed.accType) parts.push(`Type: ${parsed.accType}`);
      infoEl.textContent = `Validated ✅ ${parts.join(' | ')}`;
      $('#payButton').disabled = false;
    } else {
      infoEl.textContent = `Validation failed ❌ (${parsed.message})`;
      $('#payButton').disabled = true;
    }
  } catch (err) {
    if (infoEl) infoEl.textContent = 'Validation error: ' + String(err);
    $('#payButton').disabled = true;
  }
}

function buildStatusXML(rrn) {
  return `<?xml version="1.0" encoding="UTF-8"?><StatusRequest><RRN>${rrn}</RRN></StatusRequest>`;
}

async function postXML(path, xml, expectXML = false) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/xml' },
    body: xml
  });
  const text = await res.text();
  if (!res.ok) throw new Error(text || `HTTP ${res.status}`);
  if (expectXML) return text;
  try { return JSON.parse(text); } catch { return text; }
}

// Pay flow via /reqpay (prompt for PIN after clicking Pay)
let pendingPayData = null;
const pinModal = document.getElementById('pinModal');
const pinInput = document.getElementById('pinInput');
const pinCancelBtn = document.getElementById('pinCancelBtn');
const pinConfirmBtn = document.getElementById('pinConfirmBtn');

function openPinModal() {
  if (!pinModal) return;
  pinModal.classList.add('show');
  pinModal.setAttribute('aria-hidden', 'false');
  if (pinInput) {
    pinInput.value = '';
    setTimeout(() => pinInput.focus(), 50);
  }
}
function closePinModal() {
  if (!pinModal) return;
  pinModal.classList.remove('show');
  pinModal.setAttribute('aria-hidden', 'true');
}

$('#payForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  // ensure payee validated first
  if (!lastValAddOk || lastValidatedPayee !== data.payee) {
    await validatePayeeOnUI(data.payer, data.payee);
    if (!lastValAddOk) {
      setOutput('#payOutput', 'Cannot proceed: payee validation failed.');
      return;
    }
  }
  pendingPayData = data;
  // Start flow animation immediately to show progression
  try { playFlowOnce(); } catch { }
  openPinModal();
});

if (pinCancelBtn) pinCancelBtn.addEventListener('click', () => {
  pendingPayData = null;
  closePinModal();
});

async function submitPayWithPin(pin) {
  if (!pendingPayData) return;
  const xml = buildReqPayXML({
    payer: pendingPayData.payer,
    payee: pendingPayData.payee,
    amount: pendingPayData.amount,
    note: pendingPayData.note,
    purpose: pendingPayData.purpose,
    pin,
    type: 'PAY'
  });
  setOutput('#payOutput', 'Submitting...\n' + xml);
  try {
    const ack = await postXML('/reqpay', xml, false);
    setOutput('#payOutput', `ACK:\n${JSON.stringify(ack, null, 2)}\n\nUse RRN above in Status tab.`);
    // Start polling status in Pay tab
    if (ack && ack.rrn) {
      startPayStatusPolling(ack.rrn);
    }
    // also trigger flow replay subtly after ACK to mirror backend legs
    triggerFlowAfterAck();
  } catch (err) {
    setOutput('#payOutput', 'Error:\n' + String(err));
  } finally {
    pendingPayData = null;
  }
}

if (pinConfirmBtn) pinConfirmBtn.addEventListener('click', async () => {
  const pin = (pinInput && pinInput.value) ? pinInput.value : '';
  if (!pin) {
    if (pinInput) pinInput.focus();
    return;
  }
  pinConfirmBtn.disabled = true;
  try {
    await submitPayWithPin(pin);
  } finally {
    pinConfirmBtn.disabled = false;
    closePinModal();
  }
});
if (pinInput) {
  pinInput.addEventListener('keydown', async (ev) => {
    if (ev.key === 'Enter') {
      ev.preventDefault();
      const pin = pinInput.value || '';
      if (!pin) return;
      pinConfirmBtn && (pinConfirmBtn.disabled = true);
      try {
        await submitPayWithPin(pin);
      } finally {
        pinConfirmBtn && (pinConfirmBtn.disabled = false);
        closePinModal();
      }
    }
    if (ev.key === 'Escape') {
      closePinModal();
    }
  });
}

// ---- Pay tab status polling ----
let payStatusTimer = null;
function setPayStatusUI(text, state, hint) {
  const row = document.getElementById('payStatusRow');
  const badge = document.getElementById('payStatusBadge');
  const hintEl = document.getElementById('payStatusHint');
  const icon = document.getElementById('payStatusIcon');
  const sub = document.getElementById('payStatusSub');
  const progress = document.getElementById('payStatusProgress');
  if (!row || !badge) return;
  row.style.display = 'flex';
  badge.textContent = text || '';
  badge.classList.remove('success', 'fail', 'pending');
  const up = String(state || '').toUpperCase();
  if (up === 'SUCCESS') badge.classList.add('success');
  else if (up === 'PENDING') badge.classList.add('pending');
  else badge.classList.add('fail');
  if (hintEl) hintEl.textContent = hint || '';
  if (icon) {
    icon.classList.remove('success', 'fail', 'pending');
    if (up === 'SUCCESS') { icon.classList.add('success'); icon.textContent = '✓'; }
    else if (up === 'PENDING') { icon.classList.add('pending'); icon.textContent = '⏳'; }
    else { icon.classList.add('fail'); icon.textContent = '✕'; }
  }
  if (sub) {
    if (up === 'SUCCESS') sub.textContent = 'Payment completed.';
    else if (up === 'PENDING') sub.textContent = 'Awaiting bank responses...';
    else sub.textContent = 'Payment failed. Please try again.';
  }
  if (progress) {
    progress.style.display = (up === 'PENDING') ? 'block' : 'none';
  }
}

async function pollStatusOnce(rrn) {
  const xml = buildStatusXML(rrn);
  const resp = await postXML('/status', xml, true);
  // naive parse: look for <Status>...</Status>
  let status = 'PENDING';
  try {
    const doc = new DOMParser().parseFromString(resp, 'application/xml');
    const s = doc.getElementsByTagName('Status')[0];
    if (s && s.textContent) status = s.textContent.trim();
  } catch { }
  return status;
}

function startPayStatusPolling(rrn) {
  if (payStatusTimer) clearInterval(payStatusTimer);
  setPayStatusUI('PENDING', 'PENDING', `RRN: ${rrn}`);
  // Poll every 1s until terminal
  payStatusTimer = setInterval(async () => {
    try {
      const status = await pollStatusOnce(rrn);
      if (status && status !== 'PENDING') {
        clearInterval(payStatusTimer);
        payStatusTimer = null;
        const ok = status.toUpperCase() === 'SUCCESS';
        setPayStatusUI(status.toUpperCase(), ok ? 'SUCCESS' : 'FAIL', `RRN: ${rrn}`);
      } else {
        setPayStatusUI('PENDING', 'PENDING', `RRN: ${rrn}`);
      }
    } catch (e) {
      // transient errors: keep pending
    }
  }, 1000);
}

// Collect flow (can also use /reqpay with type=COLLECT, but we call /collect to exercise both paths)
$('#collectForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  const xml = buildCollectXML({
    payer: data.payer,
    payee: data.payee,
    amount: data.amount,
    note: data.note,
    purpose: data.purpose
  });
  setOutput('#collectOutput', 'Submitting...\n' + xml);
  try {
    const ack = await postXML('/collect', xml, false);
    setOutput('#collectOutput', `ACK:\n${JSON.stringify(ack, null, 2)}\n\nUse RRN above in Status tab.`);
  } catch (err) {
    setOutput('#collectOutput', 'Error:\n' + String(err));
  }
});

// Validate address
$('#validateForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  const xml = buildValAddXML({ payer: data.payer, payee: data.payee });
  setOutput('#validateOutput', 'Submitting...\n' + xml);
  try {
    const respXML = await postXML('/validate-address', xml, true);
    setOutput('#validateOutput', respXML);
  } catch (err) {
    setOutput('#validateOutput', 'Error:\n' + String(err));
  }
});

// Status check
$('#statusForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  const xml = buildStatusXML(data.rrn);
  setOutput('#statusOutput', 'Submitting...\n' + xml);
  try {
    const respXML = await postXML('/status', xml, true);
    setOutput('#statusOutput', respXML);
  } catch (err) {
    setOutput('#statusOutput', 'Error:\n' + String(err));
  }
});



// Manual validation button and reset on input edit
const payeeInput = $('#payeeInput');
const validateBtn = $('#validatePayeeBtn');
if (validateBtn) {
  validateBtn.addEventListener('click', async () => {
    const payer = document.querySelector('#payForm [name="payer"]').value;
    const payee = document.querySelector('#payForm [name="payee"]').value;
    if (payer && payee) await validatePayeeOnUI(payer, payee);
  });
}
if (payeeInput) {
  payeeInput.addEventListener('input', () => {
    lastValAddOk = false;
    lastValidatedPayee = '';
    $('#payButton').disabled = true;
    const infoRow = $('#payeeInfoRow');
    const infoEl = $('#payeeInfo');
    if (infoRow) infoRow.style.display = 'block';
    if (infoEl) infoEl.textContent = 'Click "Validate Payee" to verify payee details.';
  });
}

// Transactions tab
async function fetchTransactions() {
  const res = await fetch('/transactions');
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

function renderTransactions(list) {
  const container = document.getElementById('txnsContainer');
  if (!container) return;
  container.innerHTML = '';
  const header = document.createElement('div');
  header.className = 'txn-row header';
  header.innerHTML = '<div>RRN</div><div>Payer → Payee</div><div>Amount</div><div>Status</div><div>Created</div>';
  container.appendChild(header);
  if (!list.length) {
    const empty = document.createElement('div');
    empty.className = 'hint';
    empty.textContent = 'No transactions yet.';
    container.appendChild(empty);
    return;
  }
  list.forEach(tx => {
    const row = document.createElement('div');
    row.className = 'txn-row';
    const statusOk = (tx.status || '').toUpperCase() === 'SUCCESS';
    const badgeClass = statusOk ? 'badge success' : 'badge fail';
    row.innerHTML = `
      <div>${tx.rrn || ''}</div>
      <div>${tx.payer_vpa || ''} → ${tx.payee_vpa || ''}</div>
      <div>₹${Number(tx.amount || 0).toFixed(2)}</div>
      <div><span class="${badgeClass}">${tx.status || ''}</span></div>
      <div>${tx.created_at || ''}</div>
    `;
    container.appendChild(row);
  });
}

const refreshBtn = document.getElementById('refreshTxnsBtn');
if (refreshBtn) {
  refreshBtn.addEventListener('click', async () => {
    try {
      const list = await fetchTransactions();
      renderTransactions(list);
    } catch (e) {
      const container = document.getElementById('txnsContainer');
      if (container) container.textContent = 'Failed to load transactions.';
    }
  });
}

// ---- Flow Diagram Animation ----
function setActive(id, on) {
  const el = document.getElementById(id);
  if (!el) return;
  if (on) el.classList.add('active'); else el.classList.remove('active');
}

function resetFlow() {
  ['node-payerpsp', 'node-switch', 'node-payeepSP', 'node-rembank', 'node-benebank',
    'edge-pay-req', 'edge-auth-req', 'edge-auth-resp', 'edge-debit', 'edge-debit-resp',
    'edge-credit', 'edge-credit-resp', 'edge-final-resp', 'edge-txnconf'].forEach(id => setActive(id, false));
}

async function playFlowOnce() {
  resetFlow();
  // PAY from Payer PSP -> Switch
  setActive('node-payerpsp', true);
  await new Promise(r => setTimeout(r, 400));
  setActive('edge-pay-req', true);
  await new Promise(r => setTimeout(r, 700));
  setActive('node-switch', true);

  // AuthDetails Switch <-> Payee PSP
  await new Promise(r => setTimeout(r, 400));
  setActive('edge-auth-req', true);
  await new Promise(r => setTimeout(r, 600));
  setActive('node-payeepSP', true);
  await new Promise(r => setTimeout(r, 400));
  setActive('edge-auth-resp', true);

  // Debit leg Switch -> Remitter Bank and back
  await new Promise(r => setTimeout(r, 500));
  setActive('edge-debit', true);
  await new Promise(r => setTimeout(r, 700));
  setActive('node-rembank', true);
  await new Promise(r => setTimeout(r, 500));
  setActive('edge-debit-resp', true);

  // Credit leg Switch -> Beneficiary Bank and back
  await new Promise(r => setTimeout(r, 500));
  setActive('edge-credit', true);
  await new Promise(r => setTimeout(r, 700));
  setActive('node-benebank', true);
  await new Promise(r => setTimeout(r, 500));
  setActive('edge-credit-resp', true);

  // Final RespPay to Payer PSP + TxnConfirmation to Payee PSP
  await new Promise(r => setTimeout(r, 500));
  setActive('edge-final-resp', true);
  await new Promise(r => setTimeout(r, 400));
  setActive('edge-txnconf', true);
}

// Auto-run the flow continuously
let flowLoopRunning = false;
async function startFlowAuto() {
  if (flowLoopRunning) return;
  flowLoopRunning = true;
  // tiny delay to allow initial paint
  await new Promise(r => setTimeout(r, 400));
  while (true) {
    try { await playFlowOnce(); } catch { }
    await new Promise(r => setTimeout(r, 800));
  }
}
startFlowAuto();

// Phase 1: Auto-validate default payee on load so Pay button is enabled
document.addEventListener('DOMContentLoaded', () => {
  const payeeInput = document.getElementById('payeeInput');
  const payerInput = document.querySelector('#payForm input[name="payer"]');
  if (payeeInput && payerInput) {
    const payee = (payeeInput.value || 'merchant@benef').trim();
    const payer = (payerInput.value || 'ramesh@payer').trim();
    if (payee) validatePayeeOnUI(payer, payee).catch(() => {});
  }
});

// No-op kept for compatibility; flow runs automatically
async function triggerFlowAfterAck() { }
