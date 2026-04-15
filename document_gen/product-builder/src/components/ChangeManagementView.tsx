import { useState, useEffect, useRef, useCallback } from 'react';
import {
  PenLine, Compass, Cpu, FlaskConical, Rocket,
  ChevronRight, Edit3, Check, X, RotateCcw, Play,
  Terminal, GitBranch, AlertCircle, CheckCircle, Clock,
  Zap, RefreshCw, ExternalLink, ChevronDown, ChevronUp,
  Code2, Loader2
} from 'lucide-react';
import type { CMStage, CMPlan, AgentCard, TestResult, FlowStep, DeployVersion } from '../types';

/* ─── Test XML Scenarios ─────────────────────────────────────────────────── */
const TEST_SCENARIOS: Record<string, string> = {
  basic: `<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqPay xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="1.0" ts="2026-03-23T10:00:00Z" orgId="PAYERPSP" msgId="REQPAY001" prodType="UPI"/>
  <upi:Txn id="TXN-001" type="PAY" note="Test basic payment"/>
  <upi:Payer addr="ramesh@payer">
    <upi:Amount value="100.00"/>
    <upi:Creds><upi:Cred><upi:Data code="1234"/></upi:Cred></upi:Creds>
  </upi:Payer>
  <upi:Payees><upi:Payee addr="merchant@benef"/></upi:Payees>
</upi:ReqPay>`,
  highvalue: `<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqPay xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="1.0" ts="2026-03-23T10:00:00Z" orgId="PAYERPSP" msgId="REQPAY002" prodType="UPI"/>
  <upi:Txn id="TXN-HV-001" type="PAY" note="High value payment"/>
  <upi:Payer addr="corporate@payer">
    <upi:Amount value="150000.00"/>
    <upi:Creds><upi:Cred><upi:Data code="9876"/></upi:Cred></upi:Creds>
  </upi:Payer>
  <upi:Payees><upi:Payee addr="vendor@benef"/></upi:Payees>
</upi:ReqPay>`,
  risk: `<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqPay xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="1.0" ts="2026-03-23T10:00:00Z" orgId="PAYERPSP" msgId="REQPAY003" prodType="UPI"/>
  <upi:Txn id="TXN-RISK-001" type="PAY" note="Risk score test"/>
  <upi:RiskScore value="72" model="v2"/>
  <upi:Payer addr="new_user@payer">
    <upi:Amount value="49999.00"/>
    <upi:Creds><upi:Cred><upi:Data code="5555"/></upi:Cred></upi:Creds>
  </upi:Payer>
  <upi:Payees><upi:Payee addr="risky@benef"/></upi:Payees>
</upi:ReqPay>`,
  custom: '',
};

/* ─── Sub-stage config ───────────────────────────────────────────────────── */
const CM_STAGES: { id: CMStage; label: string; icon: React.ReactNode; accentClass: string }[] = [
  { id: 'prompt',    label: 'Mission',  icon: <PenLine className="w-4 h-4" />,    accentClass: 'border-l-indigo-500'   },
  { id: 'plan',      label: 'Blueprint', icon: <Compass className="w-4 h-4" />,    accentClass: 'border-l-slate-400' },
  { id: 'execution', label: 'Orchestrate',icon: <Cpu className="w-4 h-4" />,       accentClass: 'border-l-indigo-600'   },
  { id: 'test',      label: 'Validate', icon: <FlaskConical className="w-4 h-4" />, accentClass: 'border-l-emerald-500' },
  { id: 'deploy',    label: 'Transmit',  icon: <Rocket className="w-4 h-4" />,     accentClass: 'border-l-indigo-900'   },
];

/* ─── Agent status card component ───────────────────────────────────────── */
function AgentStatusCard({ card }: { card: AgentCard }) {
  const config = {
    queued:      { bg: 'bg-slate-900',  border: 'border-slate-800',  dot: 'bg-slate-700',    text: 'text-slate-500',   icon: <Clock className="w-3.5 h-3.5" /> },
    running:     { bg: 'bg-indigo-950', border: 'border-indigo-700', dot: 'bg-indigo-400',  text: 'text-indigo-300', icon: <Loader2 className="w-3.5 h-3.5 animate-spin" /> },
    updating:    { bg: 'bg-slate-900',  border: 'border-indigo-900', dot: 'bg-indigo-500', text: 'text-indigo-400', icon: <RefreshCw className="w-3.5 h-3.5 animate-spin" /> },
    done:        { bg: 'bg-emerald-950',border: 'border-emerald-700', dot: 'bg-emerald-400', text: 'text-emerald-300', icon: <CheckCircle className="w-3.5 h-3.5" /> },
    ready:       { bg: 'bg-emerald-950',border: 'border-emerald-700', dot: 'bg-emerald-400', text: 'text-emerald-300', icon: <CheckCircle className="w-3.5 h-3.5" /> },
    completed:   { bg: 'bg-emerald-950',border: 'border-emerald-700', dot: 'bg-emerald-400', text: 'text-emerald-300', icon: <CheckCircle className="w-3.5 h-3.5" /> },
    action:      { bg: 'bg-indigo-950', border: 'border-indigo-700', dot: 'bg-indigo-400',  text: 'text-indigo-300', icon: <Zap className="w-3.5 h-3.5 animate-pulse" /> },
    action_ok:   { bg: 'bg-emerald-950',border: 'border-emerald-700', dot: 'bg-emerald-400', text: 'text-emerald-300', icon: <CheckCircle className="w-3.5 h-3.5" /> },
    action_fail: { bg: 'bg-rose-950',    border: 'border-rose-900',   dot: 'bg-rose-500',    text: 'text-rose-300',   icon: <AlertCircle className="w-3.5 h-3.5" /> },
    error:       { bg: 'bg-rose-950',    border: 'border-rose-900',   dot: 'bg-rose-500',    text: 'text-rose-300',   icon: <AlertCircle className="w-3.5 h-3.5" /> },
    skipped:     { bg: 'bg-slate-900',  border: 'border-slate-800',  dot: 'bg-slate-700',    text: 'text-slate-600',   icon: <ChevronRight className="w-3.5 h-3.5" /> },
  }[card.status] || { bg: 'bg-gray-800', border: 'border-gray-700', dot: 'bg-gray-500', text: 'text-gray-400', icon: <Clock className="w-3.5 h-3.5" /> };

  return (
    <div className={`${config.bg} border ${config.border} rounded-xl p-3`}>
      <div className="flex items-center gap-2 mb-1">
        <div className={`w-2 h-2 rounded-full ${config.dot} ${card.status === 'running' ? 'animate-pulse' : ''}`} />
        <span className="text-sm font-bold text-white">{card.name}</span>
        <span className={`ml-auto text-sm font-semibold ${config.text} flex items-center gap-1`}>
          {config.icon}
          {card.status.toUpperCase()}
        </span>
      </div>
      <p className="text-sm text-gray-400 leading-relaxed truncate">{card.msg}</p>
    </div>
  );
}

/* ─── Execution Terminal ─────────────────────────────────────────────────── */
function ExecTerminal({ logs, onClear }: { logs: string[]; onClear: () => void }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [logs]);

  return (
    <div className="bg-gray-950 rounded-xl border border-gray-800 flex flex-col flex-1 min-h-0">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 flex-shrink-0">
        <div className="flex items-center gap-2 text-sm font-bold text-gray-500 uppercase tracking-wider">
          <Terminal className="w-3.5 h-3.5" /> Live Logs
        </div>
        <button onClick={onClear} className="text-sm text-gray-600 hover:text-gray-400 px-2 py-0.5 rounded bg-gray-800 hover:bg-gray-700 transition-colors">
          Clear
        </button>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto p-4 font-mono text-sm space-y-0.5">
        {logs.length === 0
          ? <div className="text-gray-600 italic">Waiting for execution…</div>
          : logs.map((line, i) => (
            <div key={i} className={
              line.includes('[ERROR]') || line.includes('error') ? 'text-rose-400' :
              line.includes('[DONE]') || line.includes('✓') ? 'text-emerald-400' :
              line.includes('[SYSTEM]') ? 'text-indigo-400' :
              line.includes('[') ? 'text-slate-400' :
              'text-slate-500 font-medium'
            }>{line}</div>
          ))
        }
        <div ref={endRef} />
      </div>
    </div>
  );
}

/* ─── Main Component ─────────────────────────────────────────────────────── */
interface ChangeManagementViewProps {
  currentStage: CMStage;
  onStageChange: (s: CMStage) => void;
}

export default function ChangeManagementView({ currentStage, onStageChange }: ChangeManagementViewProps) {
  /* ── Prompt state ── */
  const [promptText, setPromptText] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  /* ── Plan state ── */
  const [plan, setPlan] = useState<CMPlan | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editedPlanText, setEditedPlanText] = useState('');
  const [planVersion, setPlanVersion] = useState('');
  const [planDesc, setPlanDesc] = useState('');
  const [planVerification, setPlanVerification] = useState('');
  const [versions, setVersions] = useState<DeployVersion[]>([]);

  /* ── Execution state ── */
  const [agentCards, setAgentCards] = useState<AgentCard[]>([]);
  const [execLogs, setExecLogs] = useState<string[]>([]);
  const [sysStatus, setSysStatus] = useState<AgentCard['status']>('queued');
  const [sysMsg, setSysMsg] = useState('Waiting for plan approval…');
  const sseRef = useRef<EventSource | null>(null);

  /* ── Test state ── */
  const [testXml, setTestXml] = useState(TEST_SCENARIOS.basic);
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [flowSteps, setFlowSteps] = useState<FlowStep[]>([]);
  const [activeFlowStep, setActiveFlowStep] = useState<FlowStep | null>(null);
  const [isRunningTest, setIsRunningTest] = useState(false);
  const [pmFeedback, setPmFeedback] = useState('');
  const [txnFinalStatus, setTxnFinalStatus] = useState('');
  const [liveLimitText, setLiveLimitText] = useState('—');
  const [showTestResults, setShowTestResults] = useState(true);

  /* ── Deploy state ── */
  const [selectedVersion, setSelectedVersion] = useState('');
  const [deployStatus, setDeployStatus] = useState('Select a version and click Deploy.');
  const [isDeploying, setIsDeploying] = useState(false);
  const [gitBranch, setGitBranch] = useState('');
  const [gitStatusText, setGitStatusText] = useState('Checking…');
  const [showHistory, setShowHistory] = useState(true);

  /* ── Load versions on mount & when deploy view shown ── */
  const loadVersions = useCallback(async () => {
    try {
      const data = await fetch('/deploy/versions').then(r => r.json());
      setVersions(data.versions || []);
    } catch { /* ignore */ }
  }, []);

  const refreshGit = useCallback(async () => {
    try {
      const d = await fetch('/git/info').then(r => r.json());
      if (!d.is_repo) { setGitStatusText(d.message || 'Not a Git repo'); setGitBranch(''); return; }
      setGitBranch('branch: ' + (d.branch || 'unknown'));
      setGitStatusText(d.dirty ? 'Uncommitted changes present.' : 'Working tree clean.');
    } catch { setGitStatusText('Unable to reach git endpoint.'); }
  }, []);

  const refreshLimits = useCallback(async () => {
    try {
      const d = await fetch('/limits').then(r => r.json());
      const p2p = d.P2P_LIMIT !== undefined ? (d.P2P_LIMIT / 100000).toFixed(1) + 'L' : '—';
      setLiveLimitText(`P2P: ₹${p2p}`);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    loadVersions();
    refreshGit();
    refreshLimits();
  }, []);

  useEffect(() => {
    if (currentStage === 'deploy') { loadVersions(); refreshGit(); }
    if (currentStage === 'test') { refreshLimits(); }
  }, [currentStage]);

  /* ── SSE connection (start when execution begins) ── */
  const startSSE = useCallback(() => {
    if (sseRef.current) { sseRef.current.close(); }
    const es = new EventSource('/stream');
    sseRef.current = es;

    es.addEventListener('agent_status', (e) => {
      try {
        const d = JSON.parse(e.data);
        setAgentCards(prev => {
          const exists = prev.find(c => c.name === d.name);
          const card: AgentCard = { name: d.name, status: d.status?.toLowerCase() as AgentCard['status'], msg: d.msg || '' };
          if (exists) return prev.map(c => c.name === d.name ? card : c);
          return [...prev, card];
        });
        setExecLogs(prev => [...prev, `[${d.name}] ${d.status}: ${d.msg || ''}`]);
        if (d.name === 'SYSTEM') {
          setSysStatus((d.status?.toLowerCase() === 'completed' ? 'done' : d.status?.toLowerCase()) as AgentCard['status']);
          setSysMsg(d.msg || '');
          if (d.status === 'COMPLETED' || d.status === 'ERROR') {
            refreshLimits(); loadVersions();
          }
        }
      } catch { /* ignore parse error */ }
    });

    es.addEventListener('spec_change', (e) => {
      try {
        const d = JSON.parse(e.data);
        setExecLogs(prev => [...prev, `[SYSTEM] Spec Change Broadcast: v${d.version}`]);
        if (d.verification_payload) setTestXml(d.verification_payload);
      } catch { /* ignore */ }
    });

    es.addEventListener('xml_log', (e) => {
      try {
        const d = JSON.parse(e.data);
        handleXmlLog(d);
      } catch { /* ignore */ }
    });

    es.onerror = () => {
      setExecLogs(prev => [...prev, '[SSE] Connection lost — retrying…']);
    };
  }, []);

  const handleXmlLog = (d: { source?: string; step?: string; content?: string; result?: string }) => {
    const step: FlowStep = {
      id: `step-${Date.now()}-${Math.random()}`,
      label: d.source || d.step || 'Step',
      xml: d.content || '',
    };
    setFlowSteps(prev => [...prev, step]);
    if (d.result) setTxnFinalStatus(d.result);
  };

  /* ── Prompt → Plan ── */
  const analyzePrompt = async () => {
    if (!promptText.trim()) { alert('Please enter a change prompt.'); return; }
    setIsAnalyzing(true);
    onStageChange('plan');
    setPlan(null);
    setPlanVersion('—');
    setPlanDesc('');
    setPlanVerification('');
    try {
      const res = await fetch('/agents/propose-change', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: promptText }),
      });
      const data: CMPlan = await res.json();
      setPlan(data);
      setPlanVersion(String(data.version || data.seq_version || '1.x'));
      setPlanDesc(data.description || '');
      setPlanVerification(data.verification_payload || '');
      if (data.verification_payload) setTestXml(data.verification_payload);
      const planText = Array.isArray(data.plan) ? data.plan.join('\n') : JSON.stringify(data, null, 2);
      setEditedPlanText(planText);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown error';
      setPlan({ description: 'Error: ' + msg });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const approvePlan = async () => {
    if (!plan) return;
    const approvedPlan = {
      ...plan,
      version: planVersion,
      description: planDesc,
      verification_payload: planVerification,
      plan: editedPlanText.split('\n').filter(l => l.trim()),
    };
    onStageChange('execution');
    setAgentCards([]);
    setExecLogs(['[SYSTEM] Execution started…']);
    setSysStatus('running');
    setSysMsg('Creating backup before applying changes…');
    startSSE();
    try {
      await fetch('/agents/approve-change', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(approvedPlan),
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'error';
      setExecLogs(prev => [...prev, '[ERROR] ' + msg]);
    }
  };

  /* ── Test transaction ── */
  const runTestTransaction = async () => {
    if (!testXml.trim()) { alert('Enter XML to test.'); return; }
    setIsRunningTest(true);
    setFlowSteps([]);
    setActiveFlowStep(null);
    setTxnFinalStatus('');
    startSSE();
    try {
      const res = await fetch('/push', {
        method: 'POST',
        headers: { 'Content-Type': 'application/xml' },
        body: testXml,
      });
      const data = await res.json();
      const status = (data.result || data.status || 'UNKNOWN').toUpperCase();
      setTxnFinalStatus(status);
      const result: TestResult = {
        id: `t${Date.now()}`,
        scenario: 'Manual',
        status: status === 'SUCCESS' || status === 'ACCEPTED' ? 'pass' : 'fail',
        detail: `${status} — RRN: ${data.rrn || data.RRN || '—'}`,
        timestamp: new Date().toLocaleTimeString(),
      };
      setTestResults(prev => [result, ...prev]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'error';
      const result: TestResult = { id: `t${Date.now()}`, scenario: 'Manual', status: 'fail', detail: 'Error: ' + msg, timestamp: new Date().toLocaleTimeString() };
      setTestResults(prev => [result, ...prev]);
    } finally {
      setIsRunningTest(false);
    }
  };

  const runTestSuite = async () => {
    const scenarios = [
      { name: 'Basic ₹100', xml: TEST_SCENARIOS.basic },
      { name: 'High Value ₹1.5L', xml: TEST_SCENARIOS.highvalue },
    ];
    for (const s of scenarios) {
      setIsRunningTest(true);
      try {
        const res = await fetch('/push', { method: 'POST', headers: { 'Content-Type': 'application/xml' }, body: s.xml });
        const data = await res.json();
        const status = (data.result || data.status || 'UNKNOWN').toUpperCase();
        setTestResults(prev => [{
          id: `t${Date.now()}`,
          scenario: s.name,
          status: status === 'SUCCESS' || status === 'ACCEPTED' ? 'pass' : 'fail',
          detail: `${status} — RRN: ${data.rrn || '—'}`,
          timestamp: new Date().toLocaleTimeString(),
        }, ...prev]);
      } catch { /* ignore */ }
      await new Promise(r => setTimeout(r, 400));
    }
    setIsRunningTest(false);
  };

  /* ── Deploy ── */
  const deployVersion = async () => {
    if (!selectedVersion) { setDeployStatus('Select a version first.'); return; }
    setIsDeploying(true);
    const lbl = versions.find(v => v.id === selectedVersion)?.description || selectedVersion;
    setDeployStatus(`⏳ Deploying ${lbl}…`);
    try {
      const data = await fetch('/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version: selectedVersion }),
      }).then(r => r.json());

      if (data.restarting) {
        setDeployStatus(`Deployed ${lbl}. Server restarting…`);
        let att = 0;
        const poll = setInterval(async () => {
          att++;
          try {
            const h = await fetch('/current-version');
            if (h.ok) {
              clearInterval(poll);
              setDeployStatus(`✅ ${lbl} is live!`);
              setIsDeploying(false);
              loadVersions();
            }
          } catch { /* still restarting */ }
          if (att > 30) { clearInterval(poll); setDeployStatus('Took too long — check backend.'); setIsDeploying(false); }
        }, 1000);
      } else {
        setDeployStatus(data.message || 'Deployed.');
        setIsDeploying(false);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'error';
      setDeployStatus('Deploy failed: ' + msg);
      setIsDeploying(false);
    }
  };

  const createGitCommit = async () => {
    setGitStatusText('Creating commit…');
    const msg = (plan && (plan.description || plan.version)) || 'UPI spec change via agents';
    try {
      const d = await fetch('/git/commit', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg }),
      }).then(r => r.json());
      if (d.error) throw new Error(d.error);
      setGitStatusText(`Commit: ${d.commit_hash || ''} ${d.commit_subject || ''}`.trim());
      refreshGit();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'error';
      setGitStatusText('Commit failed: ' + msg);
    }
  };

  const hotReload = async () => {
    try {
      const d = await fetch('/agents/reload', { method: 'POST' }).then(r => r.json());
      const p2p = d.P2P_LIMIT !== undefined ? (d.P2P_LIMIT / 100000).toFixed(1) + 'L' : '?';
      setDeployStatus(`✅ Hot-reloaded — P2P: ₹${p2p}`);
      refreshLimits();
    } catch { setDeployStatus('Hot reload failed.'); }
  };

  /* ── Stage navigation mini-bar ── */
  const StageBar = () => (
    <div className="flex items-center gap-1 mb-6 overflow-x-auto pb-1">
      {CM_STAGES.map((s, i) => {
        const stageOrder = CM_STAGES.map(x => x.id);
        const curIdx = stageOrder.indexOf(currentStage);
        const sIdx = stageOrder.indexOf(s.id);
        const isActive = s.id === currentStage;
        const isDone = sIdx < curIdx;
        return (
          <div key={s.id} className="flex items-center flex-shrink-0">
            <button
              onClick={() => onStageChange(s.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-semibold transition-all border
                ${isActive ? 'bg-indigo-700 text-white border-indigo-600 shadow-md' :
                  isDone ? 'text-emerald-600 border-emerald-200 bg-emerald-50 hover:bg-emerald-100' :
                  'text-gray-400 border-gray-200 hover:bg-gray-50 hover:text-gray-600'}`}
            >
              {isDone ? <CheckCircle className="w-3.5 h-3.5 text-emerald-500" /> : s.icon}
              <span className="hidden sm:inline">{s.label}</span>
            </button>
            {i < CM_STAGES.length - 1 && (
              <div className={`w-6 h-px mx-1 ${isDone ? 'bg-emerald-400' : 'bg-gray-200'}`} />
            )}
          </div>
        );
      })}
    </div>
  );

  /* ══════════════════════════════════════════════════════════════════════════
     STAGE: PROMPT
  ══════════════════════════════════════════════════════════════════════════ */
  if (currentStage === 'prompt') {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 animate-fadeIn">
        <StageBar />
        <div className="max-w-2xl mx-auto">
          <div className="text-center mb-10">
            <div className="inline-flex items-center gap-2 bg-indigo-50 text-indigo-700 border border-indigo-100 rounded-full px-4 py-2 text-sm font-black uppercase tracking-widest mb-6 shadow-sm">
              <Zap className="w-4 h-4" /> Cognitive Spec Orchestrator
            </div>
            <h2 className="text-[56px] font-black text-slate-900 mb-4 tracking-tighter leading-none">
              Modernize the <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-indigo-500 to-slate-900">Protocol.</span>
            </h2>
            <p className="text-slate-500 text-lg font-medium max-w-lg mx-auto leading-relaxed">Broadcast changes across the ecosystem using signed manifests and automated A2A syncing.</p>
          </div>

          <div className="bg-white rounded-[2rem] border border-slate-200 shadow-[0_20px_50px_rgba(0,0,0,0.05)] p-10 space-y-6">
            <div>
              <label className="block text-[11px] font-black text-slate-400 uppercase tracking-widest mb-3 ml-1">Change Mandate</label>
              <textarea
                value={promptText}
                onChange={e => setPromptText(e.target.value)}
                rows={5}
                className="w-full px-6 py-5 rounded-2xl border-2 border-slate-100 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-900 placeholder-slate-300 resize-none text-lg font-bold transition-all shadow-inner bg-slate-50/50"
                placeholder="e.g. Add a RiskScore tag to the ReqPay schema with values 0–100 and update all agents to validate it…"
              />
            </div>

            {/* Quick examples */}
            <div>
              <div className="text-sm font-medium text-gray-500 mb-2">Quick examples:</div>
              <div className="flex flex-wrap gap-2">
                {[
                  'Add RiskScore field to ReqPay XML schema',
                  'Increase P2P limit from ₹1L to ₹2L per RBI directive',
                  'Add UPI Circle delegated payment support to switch',
                ].map(ex => (
                  <button key={ex} onClick={() => setPromptText(ex)}
                    className="text-sm bg-gray-100 hover:bg-indigo-100 hover:text-indigo-700 text-gray-600 px-3 py-1.5 rounded-full transition-colors border border-transparent hover:border-indigo-200">
                    {ex}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={analyzePrompt}
              disabled={isAnalyzing || !promptText.trim()}
              className="w-full flex items-center justify-center gap-3 py-5 rounded-2xl bg-slate-900 text-white font-black text-xs uppercase tracking-widest hover:bg-black transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-xl shadow-slate-900/20 active:scale-[0.98]"
            >
              {isAnalyzing ? <><Loader2 className="w-4 h-4 animate-spin" /> Synthesizing…</> : <><Zap className="w-4 h-4 text-indigo-400" /> Mobilize Agents</>}
            </button>
          </div>

          {/* Info box */}
          <div className="mt-4 bg-blue-50 rounded-xl p-4 flex gap-3">
            <AlertCircle className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-700">
              The Reasoning Agent reads NPCI specs, RBI guidelines, and current schema to create a detailed, editable execution plan before any changes are applied.
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ══════════════════════════════════════════════════════════════════════════
     STAGE: PLAN
  ══════════════════════════════════════════════════════════════════════════ */
  if (currentStage === 'plan') {
    const planLines = editedPlanText.split('\n').filter(l => l.trim());
    const impactAnalysis = plan?.impact_analysis;

    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 animate-fadeIn">
        <StageBar />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Left: Plan info */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-white rounded-[2rem] border border-slate-200 p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-2xl bg-indigo-50 flex items-center justify-center">
                  <Compass className="w-6 h-6 text-indigo-600" />
                </div>
                <div>
                  <h3 className="font-black text-slate-900 tracking-tight">Cognitive Blueprint</h3>
                  {isAnalyzing && <p className="text-xs text-indigo-500 font-black animate-pulse uppercase tracking-widest mt-0.5">Synthesizing…</p>}
                  {!isAnalyzing && plan && <p className="text-xs text-slate-400 font-black uppercase tracking-widest mt-0.5">v{planVersion} · Verified</p>}
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5 ml-1">Protocol Version</label>
                  <input value={planVersion} onChange={e => setPlanVersion(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl border-2 border-slate-100 text-base font-black font-mono text-indigo-600 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500" />
                </div>
                <div>
                  <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5 ml-1">Description</label>
                  <input value={planDesc} onChange={e => setPlanDesc(e.target.value)} readOnly={!editMode}
                    className={`w-full px-4 py-3 rounded-xl border-2 text-base font-bold transition-all focus:outline-none ${editMode ? 'border-indigo-300 focus:ring-4 focus:ring-indigo-500/10' : 'border-slate-50 bg-slate-50 text-slate-600'}`} />
                </div>
              </div>
            </div>

            {/* Impact Analysis */}
            {impactAnalysis && (
              <div className="bg-white rounded-[2rem] border border-slate-200 p-6 shadow-sm">
                <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4 ml-1">Impact Analysis</h4>
                {Array.isArray(impactAnalysis) ? (
                  <ul className="space-y-2">
                    {impactAnalysis.map((item, i) => (
                      <li key={i} className="flex items-start gap-2 text-[13px] text-slate-700 font-medium">
                        <Code2 className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0 mt-0.5" /> {item}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="space-y-3">
                    {impactAnalysis.business_value && (
                      <div className="p-3.5 rounded-2xl bg-indigo-50/50 border border-indigo-100">
                        <div className="text-[10px] font-black text-indigo-700 uppercase tracking-widest mb-1">Business Value</div>
                        <div className="text-[13px] text-slate-800 font-bold">{impactAnalysis.business_value}</div>
                      </div>
                    )}
                    {impactAnalysis.compliance_check && (
                      <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200">
                        <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Compliance</div>
                        <div className="text-[13px] text-slate-800 font-bold">{impactAnalysis.compliance_check}</div>
                      </div>
                    )}
                    {impactAnalysis.risk_assessment && (
                      <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-100">
                        <div className="text-[10px] font-black text-rose-700 uppercase tracking-widest mb-1">Risk Assessment</div>
                        <div className="text-[13px] text-slate-800 font-bold">{impactAnalysis.risk_assessment}</div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Verification payload */}
            {planVerification && (
              <div className="bg-white rounded-[2rem] border border-slate-200 p-6 shadow-sm">
                <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 ml-1">Verification Manifest</h4>
                <textarea value={planVerification} onChange={e => setPlanVerification(e.target.value)} rows={4}
                  className="w-full text-xs font-mono bg-slate-900 text-indigo-400 p-4 rounded-xl border border-slate-800 focus:outline-none resize-none shadow-inner" />
              </div>
            )}
          </div>

          {/* Right: Plan steps */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-white rounded-[2rem] border border-slate-200 shadow-sm overflow-hidden">
              <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100 bg-slate-50/50">
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Orchestration Plan</span>
                <div className="flex items-center gap-2">
                  {editMode && (
                    <button onClick={() => { setPlan(p => ({ ...p, plan: editedPlanText.split('\n').filter(l => l.trim()) })); setEditMode(false); }}
                      className="flex items-center gap-1.5 text-xs bg-emerald-500 text-white px-4 py-2 rounded-xl font-black uppercase tracking-widest shadow-md hover:bg-emerald-600 transition-all active:scale-95">
                      <Check className="w-3 h-3" /> Commit
                    </button>
                  )}
                  <button onClick={() => setEditMode(v => !v)}
                    className={`flex items-center gap-1.5 text-xs px-4 py-2 rounded-xl font-black uppercase tracking-widest transition-all active:scale-95
                      ${editMode ? 'bg-rose-500 text-white hover:bg-rose-600 shadow-md' : 'bg-slate-200 text-slate-700 hover:bg-slate-300'}`}>
                    {editMode ? <><X className="w-3 h-3" /> ABORT</> : <><Edit3 className="w-3 h-3" /> MODIFY BLUEPRINT</>}
                  </button>
                </div>
              </div>
              <div className="p-6">
                {isAnalyzing ? (
                  <div className="flex flex-col items-center gap-4 py-12 justify-center">
                    <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                    <span className="text-sm text-slate-400 font-black uppercase tracking-widest animate-pulse">Calculating optimal path…</span>
                  </div>
                ) : editMode ? (
                  <textarea value={editedPlanText} onChange={e => setEditedPlanText(e.target.value)} rows={14}
                    className="w-full font-mono text-sm bg-slate-900 text-indigo-300 p-6 rounded-2xl border border-slate-800 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 resize-none shadow-inner" />
                ) : (
                  <ol className="space-y-3">
                    {planLines.map((line, i) => (
                      <li key={i} className="flex items-start gap-4 text-base group">
                        <span className="flex-shrink-0 w-8 h-8 rounded-xl bg-slate-100 border border-slate-200 text-slate-600 flex items-center justify-center text-xs font-black shadow-sm group-hover:bg-indigo-600 group-hover:text-white group-hover:border-indigo-600 transition-all">{i + 1}</span>
                        <span className="text-slate-800 font-bold pt-1.5 leading-snug">{line}</span>
                      </li>
                    ))}
                    {planLines.length === 0 && <li className="text-slate-400 text-base italic font-medium">No plan steps yet.</li>}
                  </ol>
                )}
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex gap-4 justify-end">
              <button onClick={() => { onStageChange('prompt'); }}
                className="flex items-center gap-2 px-6 py-3.5 rounded-2xl text-xs font-black uppercase tracking-widest text-slate-400 hover:text-slate-900/40 hover:bg-slate-100 transition-all active:scale-95">
                <RotateCcw className="w-4 h-4" /> ABORT MISSION
              </button>
              <button onClick={approvePlan} disabled={!plan || isAnalyzing}
                className="flex items-center gap-3 px-10 py-3.5 rounded-2xl text-xs font-black uppercase tracking-[0.2em] bg-slate-900 text-white hover:bg-black transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-xl shadow-slate-900/20 active:scale-95">
                <CheckCircle className="w-4 h-4 text-emerald-400" /> AUTHORIZE & SYNC
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ══════════════════════════════════════════════════════════════════════════
     STAGE: EXECUTION
  ══════════════════════════════════════════════════════════════════════════ */
  if (currentStage === 'execution') {
    const sysConfig = {
      queued:    { bg: 'bg-gray-100',    text: 'text-gray-600',   badge: 'bg-gray-200 text-gray-600'     },
      running:   { bg: 'bg-blue-50',     text: 'text-blue-700',   badge: 'bg-blue-100 text-blue-700'     },
      updating:  { bg: 'bg-indigo-50',   text: 'text-indigo-700', badge: 'bg-indigo-100 text-indigo-700' },
      action:    { bg: 'bg-blue-50',     text: 'text-blue-700',   badge: 'bg-blue-100 text-blue-700'     },
      done:      { bg: 'bg-emerald-50',  text: 'text-emerald-700',badge: 'bg-emerald-100 text-emerald-700' },
      ready:     { bg: 'bg-emerald-50',  text: 'text-emerald-700',badge: 'bg-emerald-100 text-emerald-700' },
      completed: { bg: 'bg-emerald-50',  text: 'text-emerald-700',badge: 'bg-emerald-100 text-emerald-700' },
      action_ok: { bg: 'bg-emerald-50',  text: 'text-emerald-700',badge: 'bg-emerald-100 text-emerald-700' },
      error:     { bg: 'bg-red-50',      text: 'text-red-700',    badge: 'bg-red-100 text-red-700'       },
      action_fail: { bg: 'bg-red-50',    text: 'text-red-700',    badge: 'bg-red-100 text-red-700'       },
      skipped:   { bg: 'bg-gray-50',     text: 'text-gray-500',   badge: 'bg-gray-200 text-gray-500'     },
    }[sysStatus] || { bg: 'bg-gray-100', text: 'text-gray-600', badge: 'bg-gray-200 text-gray-600' };

    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 animate-fadeIn">
        <StageBar />

        {/* System status block */}
        <div className={`${sysConfig.bg} rounded-[2rem] border-2 border-slate-100 p-6 mb-8 flex items-center justify-between gap-4 shadow-sm`}>
          <div className="flex items-center gap-4 min-w-0">
            {sysStatus === 'running' ? (
              <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center flex-shrink-0 shadow-inner">
                <Loader2 className="w-7 h-7 text-indigo-500 animate-spin" />
              </div>
            ) : sysStatus === 'done' ? (
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                <CheckCircle className="w-7 h-7 text-emerald-500" />
              </div>
            ) : (
              <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center flex-shrink-0">
                <Clock className="w-7 h-7 text-slate-400" />
              </div>
            )}
            <div className="min-w-0">
              <div className="flex items-center gap-3">
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Orchestrator Heartbeat</span>
                <span className={`text-[9px] font-black px-2.5 py-1 rounded-full uppercase tracking-widest shadow-sm ${sysConfig.badge}`}>{sysStatus.toUpperCase()}</span>
                {sysStatus === 'running' && <span className="flex items-center gap-1.5 text-[10px] text-emerald-600 font-black uppercase tracking-widest bg-emerald-50 px-2 py-1 rounded-full"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]" /> BROADCASTING</span>}
              </div>
              <p className="text-lg text-slate-900 mt-1.5 truncate font-black tracking-tight">{sysMsg}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Agent cards */}
          <div className="lg:col-span-1">
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-3">Agent Statuses</h3>
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {agentCards.length === 0 ? (
                <div className="bg-gray-50 rounded-xl border border-gray-200 p-6 text-center text-base text-gray-400">
                  Agents will appear as they start…
                </div>
              ) : agentCards.map(card => <AgentStatusCard key={card.name} card={card} />)}
            </div>
          </div>

          {/* Exec logs */}
          <div className="lg:col-span-2 flex flex-col" style={{ minHeight: 320 }}>
            <ExecTerminal logs={execLogs} onClear={() => setExecLogs([])} />
          </div>
        </div>

        <div className="mt-5 flex justify-end">
          <button onClick={() => onStageChange('test')}
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-700 to-indigo-700 text-white font-semibold text-base hover:opacity-90 transition-opacity shadow-lg shadow-indigo-500/20">
            Proceed to Verification <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  }

  /* ══════════════════════════════════════════════════════════════════════════
     STAGE: TEST & VERIFY
  ══════════════════════════════════════════════════════════════════════════ */
  if (currentStage === 'test') {
    const passCount = testResults.filter(r => r.status === 'pass').length;
    const failCount = testResults.filter(r => r.status === 'fail').length;

    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 animate-fadeIn">
        <StageBar />

        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-3xl font-bold text-gray-900">PM Testing & Verification</h2>
            <p className="text-base text-gray-500 mt-0.5">
              Live limit: <span className="font-mono font-medium text-indigo-700">{liveLimitText}</span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={runTestSuite} disabled={isRunningTest}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-700 text-white text-sm font-semibold hover:bg-indigo-800 transition-colors disabled:opacity-50">
              {isRunningTest ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />} Run Suite
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Left col: scenarios + xml */}
          <div className="space-y-4">
            <div className="bg-slate-900 rounded-2xl border border-gray-200 p-4">
              <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-3">Test Scenarios</h3>
              <div className="grid grid-cols-2 gap-1.5">
                {Object.entries({ basic: 'Basic', highvalue: 'High Value', risk: 'Risk Score', custom: 'Custom' }).map(([key, label]) => (
                  <button key={key} onClick={() => setTestXml(TEST_SCENARIOS[key] || '')}
                    className="text-left px-3 py-2 rounded-lg bg-gray-100 hover:bg-indigo-100 hover:text-indigo-700 text-sm text-gray-700 transition-colors font-medium">
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-[2rem] border border-slate-200 p-6 flex flex-col shadow-sm" style={{ minHeight: 200 }}>
              <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 ml-1">Simulation Payload</h3>
              <textarea value={testXml} onChange={e => setTestXml(e.target.value)} rows={8}
                className="flex-1 w-full font-mono text-xs text-indigo-400 bg-slate-900 border border-slate-800 p-5 rounded-2xl focus:outline-none resize-none shadow-inner" />
              <button onClick={runTestTransaction} disabled={isRunningTest}
                className="mt-4 flex items-center justify-center gap-3 py-4 rounded-xl bg-slate-900 text-white text-xs font-black uppercase tracking-widest hover:bg-black transition-all disabled:opacity-50 shadow-xl shadow-slate-900/20 active:scale-95">
                {isRunningTest ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />} Fire Simulation
              </button>
            </div>
          </div>

          {/* Center: flow timeline */}
          <div className="flex flex-col">
            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 ml-1">Live Transaction Flow</h3>
            <div className="bg-slate-950 rounded-[2rem] border border-slate-800 flex flex-col flex-1 shadow-2xl relative overflow-hidden" style={{ minHeight: 320 }}>
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-indigo-400 to-indigo-500 opacity-20" />
              {/* Flow steps bar */}
              <div className="border-b border-slate-800/50 px-4 py-3 flex items-center gap-2 overflow-x-auto bg-slate-900/30 backdrop-blur-sm">
                {flowSteps.length === 0
                  ? <span className="text-xs text-slate-500 font-black uppercase tracking-widest opacity-50">Waiting for pulse…</span>
                  : flowSteps.map(step => (
                    <button key={step.id} onClick={() => setActiveFlowStep(step)}
                      className={`flex-shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all
                        ${activeFlowStep?.id === step.id ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${activeFlowStep?.id === step.id ? 'bg-white' : 'bg-indigo-400'} opacity-60`} /> {step.label}
                    </button>
                  ))
                }
              </div>
              {/* XML viewer */}
              <div className="flex-1 p-6 overflow-auto scroll-smooth">
                {activeFlowStep
                  ? <pre className="font-mono text-xs text-indigo-300 whitespace-pre-wrap leading-relaxed animate-fadeIn">{activeFlowStep.xml}</pre>
                  : <div className="h-full flex items-center justify-center text-slate-600 font-black uppercase tracking-[0.2em] text-[10px] opacity-20">No active packet</div>
                }
              </div>
              {txnFinalStatus && (
                <div className="border-t border-slate-800/50 px-6 py-3 text-[10px] font-black uppercase tracking-widest bg-slate-900/50 backdrop-blur-sm">
                  <span className="text-slate-500">Node Ack Status:</span>
                  <span className={`ml-3 px-2 py-0.5 rounded-full ${txnFinalStatus.includes('SUCCESS') || txnFinalStatus.includes('ACCEPTED') ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                    {txnFinalStatus}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Right: results + feedback */}
          <div className="space-y-4">
            <div className="bg-slate-900 rounded-2xl border border-gray-200 p-4">
              <button onClick={() => setShowTestResults(v => !v)}
                className="w-full flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider">Test Results</h3>
                  {testResults.length > 0 && (
                    <p className="text-sm text-gray-400 mt-0.5">{passCount} pass · {failCount} fail</p>
                  )}
                </div>
                {showTestResults ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
              </button>
              {showTestResults && (
                <div className="mt-3 max-h-52 overflow-y-auto space-y-2">
                  {testResults.length === 0
                    ? <div className="text-sm text-gray-400 italic text-center py-4">No tests run yet</div>
                    : testResults.map(r => (
                      <div key={r.id} className={`flex items-start gap-2 p-2 rounded-lg text-sm ${r.status === 'pass' ? 'bg-emerald-50 border border-emerald-200' : 'bg-red-50 border border-red-200'}`}>
                        {r.status === 'pass' ? <CheckCircle className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" /> : <AlertCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0 mt-0.5" />}
                        <div className="min-w-0">
                          <div className="font-medium text-gray-800">{r.scenario}</div>
                          <div className="text-gray-500 truncate">{r.detail}</div>
                          <div className="text-gray-400">{r.timestamp}</div>
                        </div>
                      </div>
                    ))
                  }
                </div>
              )}
            </div>

            {/* PM Feedback */}
            <div className="bg-white rounded-[2rem] border border-slate-200 p-6 shadow-sm">
              <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 ml-1">Certification Notes</h3>
              <textarea value={pmFeedback} onChange={e => setPmFeedback(e.target.value)} rows={3}
                className="w-full text-base font-bold text-slate-800 border-2 border-slate-50 bg-slate-50 rounded-2xl p-4 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:bg-white focus:border-indigo-500 transition-all resize-none mb-4"
                placeholder="Certification context…" />
              <div className="flex gap-2">
                {[
                  { label: 'PASSED', color: 'bg-emerald-500 text-white shadow-emerald-500/20', icon: <Check className="w-3.5 h-3.5" /> },
                  { label: 'FAILED', color: 'bg-rose-500 text-white shadow-rose-500/20', icon: <X className="w-3.5 h-3.5" /> },
                  { label: 'REVISE', color: 'bg-slate-900 text-white shadow-slate-900/20', icon: <Edit3 className="w-3.5 h-3.5" /> },
                ].map(({ label, color, icon }) => (
                  <button key={label} className={`flex-1 ${color} text-[10px] font-black uppercase tracking-widest py-3 rounded-xl flex items-center justify-center gap-1.5 transition-all shadow-lg active:scale-95`}>
                    {icon} {label}
                  </button>
                ))}
              </div>
            </div>

            <button onClick={() => onStageChange('deploy')}
              className="w-full flex items-center justify-center gap-3 py-4.5 rounded-2xl bg-slate-900 text-white font-black text-xs uppercase tracking-widest hover:bg-black transition-all shadow-2xl shadow-slate-900/20 active:scale-95">
              <Rocket className="w-4 h-4 text-indigo-400" /> Transmit Code Changes
            </button>
          </div>
        </div>
      </div>
    );
  }

  /* ══════════════════════════════════════════════════════════════════════════
     STAGE: DEPLOY
  ══════════════════════════════════════════════════════════════════════════ */
  if (currentStage === 'deploy') {
    return (
      <div className="animate-slideUp">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-3xl font-black text-slate-900 tracking-tight">Protocol Transmit</h2>
            <p className="text-sm font-black text-slate-400 uppercase tracking-widest mt-1">Snapshot Management & Infrastructure Hot-Sync</p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={hotReload}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-white text-indigo-600 text-[10px] font-black uppercase tracking-widest hover:bg-slate-50 transition-all border-2 border-slate-100 shadow-sm active:scale-95">
              <RefreshCw className="w-3.5 h-3.5" /> Hot Sync
            </button>
            <a href="http://localhost:5000" target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-slate-900 text-white text-[10px] font-black uppercase tracking-widest hover:bg-black transition-all shadow-lg active:scale-95">
              <ExternalLink className="w-3.5 h-3.5" /> Launch Phase 1
            </a>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="bg-white rounded-[2rem] border border-slate-200 p-8 shadow-sm">
            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-6 flex items-center gap-2 ml-1">
              <Rocket className="w-4 h-4 text-rose-500" /> Restore Snapshot
            </h3>
            <select value={selectedVersion} onChange={e => setSelectedVersion(e.target.value)}
              className="w-full px-5 py-4 rounded-2xl border-2 border-slate-100 text-slate-900 font-bold focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 mb-4 bg-slate-50 transition-all">
              <option value="">Select version sequence…</option>
              {versions.map(v => <option key={v.id} value={v.id}>{v.seq_version || v.version || '?'}</option>)}
            </select>
            <button onClick={deployVersion} disabled={isDeploying || !selectedVersion}
              className="w-full flex items-center justify-center gap-3 py-4 rounded-2xl bg-indigo-600 text-white font-black text-xs uppercase tracking-widest hover:bg-indigo-700 transition-all disabled:opacity-50 shadow-xl shadow-indigo-600/20 active:scale-95">
              {isDeploying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Rocket className="w-4 h-4" />} Transmit Snapshot
            </button>
            <div className="mt-4 text-[11px] font-bold text-slate-500 bg-slate-50/50 rounded-xl border border-slate-100 px-4 py-3 min-h-[44px] flex items-center tracking-tight">{deployStatus}</div>
          </div>

          <div className="bg-white rounded-[2rem] border border-slate-200 p-8 shadow-sm">
            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-6 flex items-center gap-2 ml-1">
              <GitBranch className="w-4 h-4 text-emerald-500" /> Integrity Control
              {gitBranch && <span className="ml-auto font-mono text-indigo-500 text-[11px] font-black">{gitBranch}</span>}
            </h3>
            <div className="text-[11px] font-bold text-slate-500 bg-slate-50/50 rounded-xl border border-slate-100 px-4 py-3 mb-4 min-h-[44px] flex items-center tracking-tight">{gitStatusText}</div>
            <div className="flex gap-3">
              <button onClick={createGitCommit}
                className="flex-1 flex items-center justify-center gap-2 py-3.5 rounded-xl bg-slate-900 text-white text-[10px] font-black uppercase tracking-widest hover:bg-black transition-all shadow-lg active:scale-95">
                <GitBranch className="w-3.5 h-3.5 text-emerald-400" /> Sign & Commit
              </button>
              <button onClick={refreshGit}
                className="px-4 py-3.5 rounded-xl bg-slate-100 text-slate-600 hover:bg-slate-200 transition-all border border-slate-200 active:scale-95">
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-[2rem] border border-slate-200 shadow-sm overflow-hidden mb-6">
          <button onClick={() => setShowHistory(v => !v)}
            className="w-full flex items-center justify-between px-8 py-6 hover:bg-slate-50/50 transition-all">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600">
                <GitBranch className="w-5 h-5" />
              </div>
              <div className="text-left">
                <span className="block text-sm font-black text-slate-900 uppercase tracking-widest">Protocol Audit Trail</span>
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{versions.length} valid checkpoints</span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={(e) => { e.stopPropagation(); loadVersions(); }}
                className="text-[10px] font-black text-slate-500 hover:text-indigo-600 flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-white border border-transparent hover:border-slate-200 transition-all">
                <RefreshCw className="w-3 h-3" /> RELOAD
              </button>
              {showHistory ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
            </div>
          </button>
          {showHistory && (
            <div className="border-t border-slate-100">
              <div className="grid grid-cols-12 gap-4 px-8 py-3 bg-slate-50 border-b border-slate-100 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                <div className="col-span-1">SIG</div>
                <div className="col-span-5">Directive Description</div>
                <div className="col-span-3">Timestamp</div>
                <div className="col-span-2 text-center">Transmission</div>
                <div className="col-span-1 text-right">Act</div>
              </div>
              <div className="max-h-72 overflow-y-auto divide-y divide-slate-50">
                {versions.length === 0
                  ? <div className="text-xs text-slate-400 font-black uppercase tracking-widest text-center py-12 opacity-30">No checkpoints recorded</div>
                  : versions.map((v, i) => {
                    const isLatest = i === 0;
                    const seqVer = v.seq_version || v.version || '?';
                    const desc = (v.description || v.id).slice(0, 60);
                    const dateStr = v.timestamp
                      ? new Date(v.timestamp).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: '2-digit', hour: '2-digit', minute: '2-digit' })
                      : '—';
                    return (
                      <div key={v.id} className={`grid grid-cols-12 gap-4 items-center px-8 py-4 ${isLatest ? 'bg-indigo-50/30' : 'hover:bg-slate-50/50'} transition-all`}>
                        <div className="col-span-1">
                          <span className={`text-[11px] font-black font-mono ${isLatest ? 'text-indigo-600' : 'text-slate-400'}`}>v{seqVer}</span>
                          {isLatest && <div className="text-[9px] text-indigo-500 font-black uppercase tracking-tight mt-0.5">ACTIVE</div>}
                        </div>
                        <div className="col-span-5 text-sm font-bold text-slate-700 truncate" title={desc}>{desc}</div>
                        <div className="col-span-3 text-[11px] text-slate-400 font-black uppercase tracking-wider">{dateStr}</div>
                        <div className="col-span-2 text-center">
                          {isLatest
                            ? <span className="inline-block text-[9px] font-black px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-600 uppercase tracking-widest border border-emerald-100">Live Sync</span>
                            : <span className="inline-block text-[9px] font-black px-2.5 py-1 rounded-full bg-slate-100 text-slate-400 uppercase tracking-widest border border-slate-200">Archived</span>}
                        </div>
                        <div className="col-span-1 text-right">
                          <button onClick={() => setSelectedVersion(v.id)}
                            className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm transition-all ml-auto ${isLatest ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'bg-slate-100 text-slate-400 hover:bg-white hover:text-indigo-600 hover:border-slate-200 border border-transparent active:scale-95'}`}>
                            <Rocket className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    );
                  })
                }
              </div>
            </div>
          )}
        </div>

        <div className="mt-4 bg-indigo-50/50 border border-indigo-100 rounded-2xl p-6 flex gap-4">
          <AlertCircle className="w-5 h-5 text-indigo-500 flex-shrink-0 mt-0.5" />
          <span className="text-[11px] font-bold text-indigo-700 leading-relaxed uppercase tracking-widest">
            Protocol Notice: Snapshot restoration will synchronize all participating bank nodes. Hot-sync triggers immediate activation of logic manifestations. Use with high-integrity clearance.
          </span>
        </div>
      </div>
    );
  }

  return null;
}
