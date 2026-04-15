import { useState, useCallback, useRef, useEffect } from 'react';
import Header from './components/Header';
import StageProgress from './components/StageProgress';
import PromptInput from './components/PromptInput';
import ChatPage from './components/ChatPage';
import TechnicalPlanView from './components/TechnicalPlanView';
import CertificationView from './components/CertificationView';
import type {
  Stage, CanvasData, Document, FlowStep, CMPlan, AgentCard, ExecutionItem
} from './types';
import DocumentsChatPage from './components/DocumentsChatPage';
import ClarifyView from './components/ClarifyView';
import { getCodePlan } from './utils/upiCodebaseMap';
import RegistryPortal from './components/RegistryPortal';

/* 
   AppPhase: The central state of the Titan Orchestration Engine.
   It drives the rendering logic for all 11 stages of the UPI product lifecycle.
*/
type AppPhase =
  | 'input'               // Initial Mission Brief
  | 'clarify'             // PM Clarification Loop
  | 'thinking-canvas'     // Autonomous Canvas Generation
  | 'product-kit'         // GTM & FAQ Materials
  | 'brd'                 // Business Requirements Doc
  | 'technical-plan'      // TSD & Change Manifests
  | 'a2a-sync'            // Protocol Handshake Sync
  | 'nfb-execution'       // Live Cluster Code Injection
  | 'nfb-verify'          // Autonomous QA & Regression
  | 'nfb-certification'   // Regulatory Pass/Fail
  | 'nfb-deploy'          // Final Deployment
  | 'agent-registry';     // System Management Portal

/* ─── Shared API helpers (NFB product docs) ─────────────────────────────── */
/* ─── Shared API helpers (NFB product docs) ─────────────────────────────── */

async function apiApprovePhase(phase: string) {
  try {
    await fetch('/agents/approve-phase', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phase, decision: 'APPROVE' }),
    });
  } catch (e) {
    console.error(`Failed to approve phase ${phase}:`, e);
  }
}

/* ─── Phase → Stage mapping for progress bar ────────────────────────────── */
const PHASE_TO_STAGE: Record<AppPhase, Stage> = {
  'input': 'input',
  'clarify': 'clarify',
  'thinking-canvas': 'canvas',
  'product-kit': 'product-kit',
  'brd': 'brd',
  'technical-plan': 'technical-plan',
  'a2a-sync': 'a2a-sync',
  'nfb-execution': 'execution',
  'nfb-verify': 'verify',
  'nfb-certification': 'certification',
  'nfb-deploy': 'deploy',
  'agent-registry': 'input', // mock stage
};

/* ─── NFB Execution live component (inline, used only for NFB flow) ─────── */
import {
  Loader2, CheckCircle, Terminal,
  ChevronRight, Rocket as RocketIcon, RefreshCw,
  GitBranch,
  Cpu, Database, Globe, Zap as ZapIcon,
  ArrowRight, Server, Shield as ShieldIcon, Sparkles,
  FileCheck
} from 'lucide-react';

/* ─── A2A UPI Network Flow Visualizer ───────────────────────────────────── */
const A2A_NODES = [
  { id: 'customer', label: 'Customer App', icon: '📱', role: 'payer', row: 0, col: 0 },
  { id: 'payer_psp', label: 'Payer PSP', icon: '🏛️', role: 'psp', row: 0, col: 1 },
  { id: 'npci', label: 'NPCI Switch', icon: '⚡', role: 'switch', row: 0, col: 2 },
  { id: 'issuer', label: 'Issuer Bank', icon: '🏦', role: 'bank', row: 0, col: 3 },
  { id: 'benef', label: 'Benef. Bank', icon: '🏦', role: 'bank', row: 1, col: 3 },
  { id: 'payee_psp', label: 'Payee PSP', icon: '🏛️', role: 'psp', row: 1, col: 2 },
] as const;

const AGENT_TO_NODE: Record<string, string> = {
  PSP: 'payer_psp', PAYER: 'payer_psp', NPCI: 'npci', SWITCH: 'npci',
  ISSUER: 'issuer', BANK: 'issuer', DB: 'issuer', API: 'npci',
  GATEWAY: 'npci', PAYEE: 'payee_psp',
  BENEF: 'benef', BENEFICIARY: 'benef', CUSTOMER: 'customer',
};

function mapAgentToNode(agentName: string): string | null {
  const upper = agentName.toUpperCase();
  for (const [key, val] of Object.entries(AGENT_TO_NODE)) {
    if (upper.includes(key)) return val;
  }
  return null;
}

const AGENT_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  DB: Database, API: Globe, PSP: Server, NPCI: ZapIcon, ISSUER: ShieldIcon,
  BANK: ShieldIcon, GIT: GitBranch, TEST: CheckCircle, DEPLOY: RocketIcon,
};

function getAgentIcon(name?: string): React.ComponentType<{ className?: string }> {
  if (!name) return Cpu;
  const upper = name.toUpperCase();
  for (const [key, Icon] of Object.entries(AGENT_ICONS)) {
    if (upper.includes(key)) return Icon;
  }
  return Cpu;
}

function A2AFlowViz({ activeNodes }: { activeNodes: Set<string> }) {
  const nodeByPos = (row: number, col: number) =>
    A2A_NODES.find(n => n.row === row && n.col === col);

  const NodeBox = ({ label, icon, active }: { id: string; label: string; icon: string; active: boolean }) => (
    <div className={`flex flex-col items-center gap-1.5 transition-all duration-500 ${active ? 'scale-110' : 'scale-100'}`}>
      <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-4xl border transition-all duration-500 ${active
          ? 'bg-indigo-900/40 backdrop-blur-xl border-indigo-400 shadow-[0_0_20px_rgba(99,102,241,0.6)] agent-running'
          : 'bg-slate-800/40 backdrop-blur-xl border-slate-700 shadow-slate-900/50 opacity-60'
        }`}>
        {icon}
      </div>
      <div className={`text-center text-sm font-semibold leading-tight transition-colors ${active ? 'text-indigo-300 drop-shadow-[0_0_8px_rgba(99,102,241,0.8)]' : 'text-slate-500'}`}>
        {label}
      </div>
      {active && (
        <div className="flex gap-0.5">
          {[0, 1, 2].map(i => (
            <div key={i} className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
      )}
    </div>
  );

  const Arrow = ({ dir, active, delay = 0 }: { dir: 'right' | 'left' | 'down'; active: boolean; delay?: number }) => (
    <div className={`relative flex items-center justify-center flex-shrink-0 ${dir === 'down' ? 'flex-col w-10' : 'w-10 h-14'}`}>
      {dir === 'right' && (
        <>
          <div className="w-full h-0.5 bg-slate-200 relative overflow-hidden">
            {active && <div className="packet-right bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]" style={{ top: '-3px', animationDelay: `${delay}s` }} />}
          </div>
          <ArrowRight className="w-3 h-3 text-slate-300 absolute right-0" />
        </>
      )}
      {dir === 'left' && (
        <>
          <div className="w-full h-0.5 bg-slate-200 relative overflow-hidden">
            {active && <div className="packet-left bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]" style={{ top: '-3px', animationDelay: `${delay}s` }} />}
          </div>
          <ArrowRight className="w-3 h-3 text-slate-300 absolute left-0 rotate-180" />
        </>
      )}
      {dir === 'down' && (
        <>
          <div className="flex-1 w-0.5 bg-slate-200 relative overflow-hidden" style={{ minHeight: 40 }}>
            {active && <div className="packet-down bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" style={{ left: '-3px', animationDelay: `${delay}s` }} />}
          </div>
          <ArrowRight className="w-3 h-3 text-slate-300 rotate-90" />
        </>
      )}
    </div>
  );

  const isActive = (id: string) => activeNodes.has(id);
  const anyActive = activeNodes.size > 0;

  return (
    <div className="bg-slate-900/40 backdrop-blur-xl rounded-2xl border border-slate-700/50 p-5 shadow-2xl shadow-indigo-900/20">
      <div className="flex items-center gap-2 mb-4">
        <ZapIcon className="w-4 h-4 text-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.8)] rounded-full" />
        <span className="text-sm font-bold text-slate-300 uppercase tracking-wider drop-shadow-md">A2A UPI Network Flow</span>
        {anyActive && (
          <div className="ml-auto flex items-center gap-1.5 text-sm text-emerald-400 font-semibold">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse inline-block" /> LIVE
          </div>
        )}
      </div>

      {/* Row 0: Request path */}
      <div className="flex items-center justify-center gap-0 mb-2">
        {[0, 1, 2, 3].map(col => {
          const node = nodeByPos(0, col);
          if (!node) return null;
          return (
            <div key={node.id} className="flex items-center">
              <NodeBox id={node.id} label={node.label} icon={node.icon} active={isActive(node.id)} />
              {col < 3 && <Arrow dir="right" active={anyActive} delay={col * 0.4} />}
            </div>
          );
        })}
      </div>

      {/* Vertical connector from NPCI (col 2) down to Payee PSP (col 2) */}
      <div className="flex justify-center pl-[50%] pr-[25%] mb-1">
        <Arrow dir="down" active={anyActive} delay={1.2} />
      </div>

      {/* Row 1: Response path */}
      <div className="flex items-center justify-end gap-0">
        {[2, 3].map(col => {
          const node = nodeByPos(1, col);
          if (!node) return null;
          return (
            <div key={node.id} className="flex items-center">
              <NodeBox id={node.id} label={node.label} icon={node.icon} active={isActive(node.id)} />
              {col < 3 && <Arrow dir="right" active={anyActive} delay={1.6} />}
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-4 flex gap-4 justify-center">
        {[
          { color: 'bg-indigo-600', label: 'Request →' },
          { color: 'bg-indigo-400', label: '← Response' },
          { color: 'bg-emerald-500', label: 'Switch ↓' },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-slate-400">
            <div className={`w-2 h-2 rounded-full ${color}`} />{label}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Agent status card ────────────────────────────────────────────────── */
function AgentStatusCard({ card }: { card: AgentCard }) {
  const AgentIcon = getAgentIcon(card.name);
  const cfg: Record<string, { bg: string, border: string, txt: string, dot: string, badge: string, ring: string, glow: string }> = {
    queued: { 
      bg: 'bg-slate-800/30', border: 'border-slate-700', txt: 'text-slate-400', dot: 'bg-slate-500', 
      badge: 'bg-slate-800/80 text-slate-400', ring: '', glow: '' 
    },
    running: { 
      bg: 'bg-indigo-900/30 backdrop-blur-md', border: 'border-indigo-500/50', txt: 'text-indigo-400', dot: 'bg-indigo-500', 
      badge: 'bg-indigo-500/20 text-indigo-300', ring: 'ring-2 ring-indigo-500/20', glow: 'shadow-[0_0_15px_rgba(99,102,241,0.2)]'
    },
    updating: { 
      bg: 'bg-indigo-900/30 backdrop-blur-md', border: 'border-indigo-500/50', txt: 'text-indigo-400', dot: 'bg-indigo-500', 
      badge: 'bg-indigo-500/20 text-indigo-300', ring: 'ring-2 ring-indigo-500/20', glow: 'shadow-[0_0_15px_rgba(99,102,241,0.2)]'
    },
    done: { 
      bg: 'bg-emerald-900/20 backdrop-blur-md', border: 'border-emerald-500/30', txt: 'text-emerald-400', dot: 'bg-emerald-500', 
      badge: 'bg-emerald-500/20 text-emerald-400', ring: '', glow: 'shadow-[0_0_15px_rgba(16,185,129,0.1)]'
    },
    action: { 
      bg: 'bg-amber-900/30 backdrop-blur-md', border: 'border-amber-500/50', txt: 'text-amber-400', dot: 'bg-amber-500', 
      badge: 'bg-amber-500/20 text-amber-300', ring: 'ring-2 ring-amber-500/20', glow: 'shadow-[0_0_15px_rgba(245,158,11,0.2)]'
    },
    action_ok: { 
      bg: 'bg-emerald-900/20 backdrop-blur-md', border: 'border-emerald-500/30', txt: 'text-emerald-400', dot: 'bg-emerald-500', 
      badge: 'bg-emerald-500/20 text-emerald-400', ring: '', glow: '' 
    },
    action_fail: { 
      bg: 'bg-red-900/30 backdrop-blur-md', border: 'border-red-500/40', txt: 'text-red-400', dot: 'bg-red-500', 
      badge: 'bg-red-500/20 text-red-300', ring: 'ring-2 ring-red-500/20', glow: 'shadow-[0_0_15px_rgba(239,68,68,0.2)]'
    },
    ready: { 
      bg: 'bg-emerald-900/20 backdrop-blur-md', border: 'border-emerald-500/30', txt: 'text-emerald-400', dot: 'bg-emerald-500', 
      badge: 'bg-emerald-500/20 text-emerald-400', ring: '', glow: '' 
    },
    completed: { 
      bg: 'bg-emerald-900/20 backdrop-blur-md', border: 'border-emerald-500/30', txt: 'text-emerald-400', dot: 'bg-emerald-500', 
      badge: 'bg-emerald-500/20 text-emerald-400', ring: '', glow: '' 
    },
    error: { 
      bg: 'bg-red-900/30 backdrop-blur-md', border: 'border-red-500/40', txt: 'text-red-400', dot: 'bg-red-500', 
      badge: 'bg-red-500/20 text-red-300', ring: '', glow: '' 
    },
    skipped: { 
      bg: 'bg-slate-800/30', border: 'border-slate-700/50', txt: 'text-slate-500', dot: 'bg-slate-600', 
      badge: 'bg-slate-800/50 text-slate-500', ring: '', glow: '' 
    },
  };

  const safeStatus = card.status || 'queued';
  const currentCfg = cfg[safeStatus] || cfg.queued;
  const { bg, border, txt, dot, badge, ring, glow } = currentCfg;

  return (
    <div className={`${bg} ${border} ${ring} ${glow} rounded-2xl border-2 p-4 transition-all duration-500 group relative overflow-hidden`}>
      <div className="flex items-center gap-4 mb-3">
        <div className={`w-10 h-10 rounded-xl ${badge} flex items-center justify-center flex-shrink-0 shadow-sm group-hover:scale-110 transition-transform`}>
          <AgentIcon className={`w-5 h-5 ${txt}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-black text-slate-200 tracking-tight truncate">{card.name || 'ANONYMOUS AGENT'}</span>
            <div className={`ml-auto flex-shrink-0 flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-black tracking-widest ${badge}`}>
              <div className={`w-1.5 h-1.5 rounded-full ${dot} ${['running', 'action', 'updating'].includes(safeStatus) ? 'animate-pulse' : ''}`} />
              {safeStatus.replace('_', ' ').toUpperCase()}
            </div>
          </div>
        </div>
      </div>
      
      {card.msg && (
        <p className="text-xs font-bold text-slate-500 pl-14 leading-relaxed line-clamp-2 opacity-80 italic">{card.msg}</p>
      )}

      {(['running', 'updating', 'action'].includes(safeStatus)) && (
        <div className="mt-3 pl-14">
          <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-indigo-600 via-purple-500 to-indigo-400 rounded-full w-2/3 animate-shimmer shadow-[0_0_8px_rgba(99,102,241,0.4)]" />
          </div>
        </div>
      )}

      {(['done', 'completed', 'ready', 'action_ok'].includes(safeStatus)) && (
        <div className="mt-3 pl-14">
          <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full w-full shadow-[0_0_8px_rgba(16,185,129,0.3)]" />
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Shared inline execution view for NFB live agent execution ──────────── */
function NFBLiveExecution({
  featureName, onProceed, execPlan
}: {
  featureName: string;
  onProceed: () => void;
  execPlan?: import('./types').CMPlan | null;
}) {
  // Agent cards are built entirely from live SSE events — no hardcoding
  const [agentCards, setAgentCards] = useState<AgentCard[]>([]);
  const [logs, setLogs] = useState<string[]>(['[SYSTEM] Execution pipeline started…']);
  const [sysStatus, setSysStatus] = useState<AgentCard['status']>('running');
  const [activeA2ANodes, setActiveA2ANodes] = useState<Set<string>>(new Set(['npci']));
  const [doneFiles, setDoneFiles] = useState<Set<string>>(new Set());
  const sseRef = useRef<EventSource | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const planFiredRef = useRef(false);



  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  useEffect(() => {
    // A2A node animation — purely visual topology indicator
    const progression = [
      ['customer'], ['customer', 'payer_psp'], ['customer', 'payer_psp', 'npci'],
      ['payer_psp', 'npci', 'issuer'], ['npci', 'issuer', 'benef'],
      ['issuer', 'benef', 'payee_psp'], ['benef', 'payee_psp'],
      ['payee_psp'], [],
    ];
    let step = 0;
    const timer = setInterval(() => {
      if (step < progression.length) {
        setActiveA2ANodes(new Set(progression[step]));
        step++;
      } else {
        step = 0;
      }
    }, 1200);

    // SSE — connect first, then fire approve-change once connection is confirmed open
    if (sseRef.current) sseRef.current.close();
    const es = new EventSource('/stream');
    sseRef.current = es;

    es.onopen = () => {
      if (!planFiredRef.current && execPlan) {
        planFiredRef.current = true;
        setLogs(prev => [...prev, '[SYSTEM] SSE connected — submitting execution plan…']);
        fetch('/agents/approve-change', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(execPlan),
        }).catch(e => setLogs(prev => [...prev, `[ERROR] approve-change failed: ${e.message}`]));
      }
    };


    es.addEventListener('agent_status', (e) => {
      try {
        const d = JSON.parse(e.data);
        const statusLower = (d.status || '').toLowerCase();
        const card: AgentCard = { name: d.name, status: statusLower as AgentCard['status'], msg: d.msg || '' };

        // Update or insert agent card
        setAgentCards(prev => {
          const exists = prev.find(c => c.name === d.name);
          return exists ? prev.map(c => c.name === d.name ? card : c) : [...prev, card];
        });

        // Append to execution logs
        setLogs(prev => [...prev, `[${d.name}] ${d.status}: ${d.msg || ''}`]);

        // System status bar
        if (d.name === 'SYSTEM') {
          setSysStatus(statusLower === 'completed' ? 'done' : statusLower as AgentCard['status']);
          // Removed setSysMsg(d.msg || ''); as sysMsg is unused
        }

        // Light up corresponding A2A node
        const node = mapAgentToNode(d.name);
        if (node && (statusLower === 'running' || statusLower === 'updating')) {
          setActiveA2ANodes(prev => new Set([...prev, node]));
        }

        // Advance file-changes progress from agent messages
        if (d.name !== 'SYSTEM' && d.msg) {
          // Extract file paths from messages like "Files changed: foo.py, bar.py" or "Ready with v2.0. Files changed: ..."
          const filesMatch = d.msg.match(/Files? changed:\s*(.+)/i);
          if (filesMatch) {
            const files = filesMatch[1].split(',').map((f: string) => f.trim()).filter(Boolean);
            setDoneFiles(prev => {
              const next = new Set(prev);
              files.forEach((f: string) => next.add(f));
              return next;
            });
          }
          // Also match "Applied changes to <path>"
          const appliedMatch = d.msg.match(/Applied changes to (.+?)(?:\s|$)/i);
          if (appliedMatch) {
            setDoneFiles(prev => new Set([...prev, appliedMatch[1].trim()]));
          }
        }
      } catch { /**/ }
    });

    es.addEventListener('spec_change', (e) => {
      try { const d = JSON.parse(e.data); setLogs(prev => [...prev, `[SYSTEM] Spec change: v${d.version}`]); }
      catch { /**/ }
    });
    es.onerror = () => setLogs(prev => [...prev, '[SSE] Connection retrying…']);

    return () => { es.close(); clearInterval(timer); };
  }, []);

  const doneCount = agentCards.filter(c => ['done', 'ready', 'completed', 'action_ok'].includes(c.status)).length;
  const runningCount = agentCards.filter(c => ['running', 'updating', 'action'].includes(c.status)).length;
  // totalCount is fully dynamic — grows as agents register via SSE
  const totalCount = Math.max(agentCards.length, 1);
  const progress = Math.min(100, Math.round(((doneCount + runningCount * 0.5) / totalCount) * 100));

  return (
    <div className="h-full flex flex-col px-10 py-10 animate-fadeIn overflow-hidden bg-slate-950">
      {/* Top Row: Title & Global System Status */}
      <div className="flex-shrink-0 flex items-center justify-between mb-12">
        <div className="flex items-center gap-8">
          <div className="w-20 h-20 rounded-[2.2rem] bg-gradient-to-br from-indigo-600 to-indigo-700 flex items-center justify-center shadow-2xl shadow-indigo-500/30 text-white relative">
            <ZapIcon className="w-10 h-10 relative z-10" />
            <div className="absolute inset-0 bg-white/10 rounded-inherit opacity-0 hover:opacity-100 transition-opacity" />
          </div>
          <div>
            <h2 className="text-5xl font-black text-white tracking-tighter leading-none mb-3 drop-shadow-[0_0_15px_rgba(255,255,255,0.4)]">
              Agent Orchestration
            </h2>
            <div className="flex items-center gap-3">
               <span className="text-[11px] font-black text-indigo-600 uppercase tracking-[0.2em] leading-none bg-indigo-50 px-4 py-2 rounded-full border border-indigo-100 shadow-sm">{featureName}</span>
               <div className="w-1.5 h-1.5 rounded-full bg-slate-200" />
               <span className="text-[11px] font-black text-slate-400 uppercase tracking-[0.25em] leading-none">Titan Global Mesh v2.4</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className={`flex items-center gap-6 px-8 py-5 rounded-[2.5rem] border border-slate-700/50 transition-all duration-700 shadow-2xl ${
            sysStatus === 'done' ? 'bg-emerald-900/40 shadow-[0_0_30px_rgba(16,185,129,0.2)]' : 
            sysStatus === 'running' ? 'bg-indigo-900/40 shadow-[0_0_30px_rgba(99,102,241,0.2)]' :
            'bg-slate-800/40 shadow-none'
          } backdrop-blur-xl`}>
            <div className="relative">
              {sysStatus === 'running' || sysStatus === 'updating' ? (
                <div className="w-6 h-6 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              ) : (
                <div className="w-6 h-6 bg-emerald-500 rounded-full flex items-center justify-center shadow-lg shadow-emerald-500/30">
                  <CheckCircle className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
            <div className="pr-4 border-r border-slate-700/50">
              <div className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] mb-1">Pipeline State</div>
              <div className="text-base font-black text-slate-100 uppercase tracking-widest leading-none flex items-baseline gap-2">
                {sysStatus} <span className="text-xs text-indigo-400 font-black tracking-normal opacity-60">SYSTEM</span>
              </div>
            </div>
            <div className="pl-2 min-w-[80px]">
               <div className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] mb-1">Coverage</div>
               <div className="text-base font-black text-slate-100 tracking-tighter leading-none">{progress}%</div>
            </div>
          </div>
          <button onClick={onProceed}
            className="group flex items-center gap-6 px-12 py-6 rounded-[2.8rem] bg-slate-900 text-white font-black uppercase tracking-[0.3em] text-[12px] hover:bg-black transition-all shadow-2xl shadow-slate-900/40 active:scale-95 relative overflow-hidden">
            <span className="relative z-10">Check Verification</span>
            <ChevronRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform relative z-10" />
            <div className="absolute inset-0 bg-gradient-to-r from-indigo-600/0 via-indigo-600/20 to-indigo-600/0 -translate-x-[120%] group-hover:translate-x-[120%] transition-transform duration-1000" />
          </button>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0">
        {/* Left Column */}
        <div className="lg:col-span-7 flex flex-col gap-6 min-h-0">
          <div className="flex-shrink-0 bg-slate-900/40 rounded-[3.5rem] p-6 border-2 border-slate-800 flex items-center justify-center shadow-xl backdrop-blur-xl">
             <A2AFlowViz activeNodes={activeA2ANodes} />
          </div>

          <div className="flex-1 flex flex-col min-h-0 bg-[#020617] border border-slate-800 rounded-[3.5rem] shadow-2xl overflow-hidden relative group">
            <div className="flex items-center justify-between px-10 py-6 border-b border-white/5 bg-slate-900/50 backdrop-blur-md relative z-10 font-black italic">
              <div className="flex items-center gap-4 text-[13px] font-black text-indigo-400 uppercase tracking-[0.4em]">
                <div className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse shadow-[0_0_12px_rgba(99,102,241,0.8)]" />
                Titan Runtime Console
              </div>
              <button onClick={() => setLogs([])} className="text-[10px] font-black text-slate-500 hover:text-white uppercase tracking-[0.2em] transition-all bg-white/5 px-6 py-2.5 rounded-full border border-white/5 hover:bg-white/10">Flush</button>
            </div>
            
            <div className="flex-1 overflow-y-auto px-10 py-8 font-mono text-[13px] space-y-4 custom-scrollbar relative z-10">
              {logs.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center opacity-30 gap-4">
                   <Terminal className="w-10 h-10 text-slate-400" />
                   <p className="text-[11px] font-black uppercase tracking-[0.5em]">Awaiting pipeline…</p>
                </div>
              ) : (
                logs.map((line, i) => {
                  const ts = new Date().toLocaleTimeString('en', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
                  return (
                    <div key={i} className="flex gap-6 border-b border-white/[0.02] pb-3 last:border-0 hover:bg-white/[0.02] transition-colors">
                      <span className="text-white/20 flex-shrink-0 select-none font-black tracking-widest text-[10px] pt-0.5">{ts}</span>
                      <div className="flex flex-col gap-1 flex-1">
                         <span className={`leading-snug ${
                           line.includes('[ERROR]') || line.includes('ACTION_FAIL') ? 'text-red-400 font-bold' :
                           line.includes('[SYSTEM]') ? 'text-indigo-400 font-black' :
                           line.includes('ACTION_OK') || line.includes('DONE') || line.includes('COMPLETED') || line.includes('SUCCESS') ? 'text-emerald-400 font-bold' :
                           line.includes('ACTION') || line.includes('RUNNING') || line.includes('STARTED') || line.includes('UPDATING') ? 'text-amber-300 font-bold' :
                           line.includes('[') ? 'text-indigo-300' : 'text-slate-300'
                         }`}>{line}</span>
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={endRef} />
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="lg:col-span-5 flex flex-col gap-6 min-h-0">
          <div className="h-[220px] flex-shrink-0 flex flex-col min-h-0 bg-slate-900 rounded-[3.5rem] border-2 border-slate-800 shadow-xl overflow-hidden">
            <div className="px-8 py-6 border-b border-white/5 bg-emerald-500/10 flex items-center justify-between">
              <h3 className="text-[11px] font-black text-slate-300 uppercase tracking-[0.3em] flex items-center gap-3 italic">
                <GitBranch className="w-4 h-4 text-emerald-400" />
                Mesh Sync
              </h3>
              <div className="text-[10px] text-emerald-400 font-bold px-3 py-1 bg-emerald-500/20 rounded-full">{doneFiles.size} Files</div>
            </div>
            <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
              {doneFiles.size === 0 ? (
                <div className="h-full flex items-center justify-center opacity-40">
                   <p className="text-[10px] font-black text-slate-500 uppercase tracking-[0.4em]">Syncing…</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  {[...doneFiles].map(filePath => (
                    <div key={filePath} className="flex flex-col gap-1.5 px-4 py-3 rounded-2xl bg-slate-800 border-2 border-slate-700">
                      <div className="w-2 h-2 rounded-full bg-emerald-500" />
                      <div className="text-[10px] font-mono truncate text-slate-300">{filePath.split('/').pop()}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
          
          <div className="flex-1 flex flex-col min-h-0 bg-[#020617] rounded-[3.5rem] border-2 border-slate-800 shadow-xl overflow-hidden">
            <div className="px-8 py-6 border-b border-slate-800 bg-slate-900 sticky top-0 z-10 flex items-center justify-between">
              <div>
                <h3 className="text-[12px] font-black text-indigo-400 uppercase tracking-[0.4em] italic mb-1">Compute Pool</h3>
                <p className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Live Agents</p>
              </div>
              <span className="text-[9px] font-black text-indigo-400 bg-indigo-900/40 px-3 py-1.5 rounded-full border border-indigo-500/30 uppercase">{doneCount+runningCount}/{totalCount} ON</span>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-3 custom-scrollbar">
              {agentCards.map(card => (
                <div key={card.name} className="animate-slideIn">
                  <AgentStatusCard card={card} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}

/* ─── Inline Verify View (reuses CM test logic) ─────────────────────────── */
const TEST_SCENARIOS: Record<string, string> = {
  basic: `<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqPay xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="1.0" ts="${new Date().toISOString()}" orgId="PAYERPSP" msgId="VERIFY001" prodType="UPI"/>
  <upi:Txn id="TXN-VERIFY-001" type="PAY" note="Verification test"/>
  <upi:Payer addr="ramesh@payer">
    <upi:Amount value="100.00"/>
    <upi:Creds><upi:Cred><upi:Data code="1234"/></upi:Cred></upi:Creds>
  </upi:Payer>
  <upi:Payees><upi:Payee addr="merchant@benef"/></upi:Payees>
</upi:ReqPay>`,
  highvalue: `<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqPay xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="1.0" ts="${new Date().toISOString()}" orgId="PAYERPSP" msgId="VERIFY002" prodType="UPI"/>
  <upi:Txn id="TXN-HV-001" type="PAY" note="High value test"/>
  <upi:Payer addr="corporate@payer">
    <upi:Amount value="150000.00"/>
    <upi:Creds><upi:Cred><upi:Data code="9876"/></upi:Cred></upi:Creds>
  </upi:Payer>
  <upi:Payees><upi:Payee addr="vendor@benef"/></upi:Payees>
</upi:ReqPay>`,
};

interface TestResult { id: string; scenario: string; status: 'pass' | 'fail'; detail: string; ts: string; }

function NFBVerifyView({ onProceed, canvas }: { onProceed: () => void; canvas: import('./types').CanvasData | null }) {
  const [testXml, setTestXml] = useState(TEST_SCENARIOS.basic);
  const [results, setResults] = useState<TestResult[]>([]);
  const [flowSteps, setFlowSteps] = useState<FlowStep[]>([]);
  const [activeStep, setActiveStep] = useState<FlowStep | null>(null);
  const [running, setRunning] = useState(false);
  const [finalStatus, setFinalStatus] = useState('');
  const [testPrompt, setTestPrompt] = useState('');
  const [isGeneratingTest, setIsGeneratingTest] = useState(false);
  const sseRef = useRef<EventSource | null>(null);

  const startSSE = useCallback(() => {
    if (sseRef.current) sseRef.current.close();
    const es = new EventSource('/stream');
    sseRef.current = es;
    es.addEventListener('xml_log', e => {
      try {
        const d = JSON.parse(e.data);
        if (!d.content) return;
        const step: FlowStep = { id: `s${Date.now()}-${Math.random()}`, label: d.source || d.step || 'Step', xml: d.content };
        setFlowSteps(prev => {
          const next = [...prev, step];
          return next;
        });
        setActiveStep(prev => prev || step); // Auto-select first step
        if (d.result) setFinalStatus(d.result);
      } catch { /**/ }
    });
    return es;
  }, []);

  useEffect(() => {
    const es = startSSE();
    return () => {
      es.close();
    };
  }, [startSSE]);

  const runTest = async () => {
    if (!testXml.trim()) return;
    setRunning(true); setFlowSteps([]); setActiveStep(null); setFinalStatus('');
    try {
      const resp = await fetch('/push', { method: 'POST', headers: { 'Content-Type': 'application/xml' }, body: testXml });
      const d = await resp.json();
      const st = (d.result || d.status || 'UNKNOWN').toUpperCase();
      setFinalStatus(st);
      setResults(prev => [{
        id: `t${Date.now()}`, scenario: 'Manual',
        status: st === 'SUCCESS' || st === 'ACCEPTED' ? 'pass' : 'fail',
        detail: `${st} — RRN: ${d.rrn || '—'}`, ts: new Date().toLocaleTimeString(),
      }, ...prev]);
    } catch { /**/ }
    finally { setRunning(false); }
  };

  const handleGenerateTestCase = async () => {
    if (!testPrompt.trim()) return;
    setIsGeneratingTest(true);
    try {
      const res = await fetch('/api/verify/generate-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: testPrompt, canvas })
      });
      const data = await res.json();
      if (data.xml) {
        setTestXml(data.xml);
      } else {
        alert('AI failed to produce XML. Please try a different prompt.');
      }
    } catch (err) {
      console.error('Test generation error:', err);
      alert('Network error while generating test. Please check backend logs.');
    } finally {
      setIsGeneratingTest(false);
    }
  };

  const runSuite = async () => {
    setRunning(true);
    setFlowSteps([]); setActiveStep(null); setFinalStatus('');
    for (const [name, xml] of Object.entries(TEST_SCENARIOS)) {
      setTestXml(xml);
      try {
        const d = await fetch('/push', { method: 'POST', headers: { 'Content-Type': 'application/xml' }, body: xml }).then(r => r.json());
        const st = (d.result || d.status || 'UNKNOWN').toUpperCase();
        setResults(prev => [{ id: `t${Date.now()}`, scenario: name, status: st === 'SUCCESS' || st === 'ACCEPTED' ? 'pass' : 'fail', detail: `${st} — RRN: ${d.rrn || '—'}`, ts: new Date().toLocaleTimeString() }, ...prev]);
      } catch { /**/ }
      await new Promise(r => setTimeout(r, 400));
    }
    setRunning(false);
  };

  const codePlan = canvas ? getCodePlan(canvas) : null;
  const featureTestFiles = codePlan ? codePlan.testFilePaths : [];
  const featureTestCases = codePlan ? codePlan.testCases : [];

  const [tcStatuses, setTcStatuses] = useState<Record<string, 'pending' | 'pass' | 'fail' | 'running'>>({});
  const runFeatureTests = () => {
    featureTestFiles.forEach((f, i) => {
      setTimeout(() => {
        setTcStatuses(prev => ({ ...prev, [f]: 'running' }));
        setTimeout(() => {
          setTcStatuses(prev => ({ ...prev, [f]: Math.random() > 0.15 ? 'pass' : 'fail' }));
        }, 800 + Math.random() * 600);
      }, i * 400);
    });
  };

  const pass = results.filter(r => r.status === 'pass').length;
  const fail = results.filter(r => r.status === 'fail').length;

  return (
    <div className="h-full flex flex-col px-10 py-10 animate-fadeIn overflow-hidden bg-white">
      {/* Header */}
      <div className="flex-shrink-0 flex items-center justify-between mb-10">
        <div className="flex items-center gap-6">
          <div className="w-16 h-16 rounded-[1.5rem] bg-slate-900 flex items-center justify-center shadow-2xl shadow-indigo-500/20 text-white">
            <CheckCircle className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-4xl font-black text-slate-900 tracking-tighter leading-tight">
              Quality Assurance
            </h2>
            <div className="flex items-center gap-2 mt-1">
               <span className="text-[10px] font-black text-indigo-600 uppercase tracking-widest leading-none bg-indigo-50 px-2 py-1 rounded">{canvas ? canvas.featureName : ''}</span>
               <div className="w-1 h-1 rounded-full bg-slate-200" />
               <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">Automated Compliance Suites</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button onClick={runSuite} disabled={running}
            className="px-8 py-4 rounded-[1.5rem] bg-slate-100 text-slate-900 text-xs font-black uppercase tracking-widest hover:bg-slate-200 transition-all">
            Execute Full Suite
          </button>
          <button onClick={onProceed}
            className="flex items-center gap-4 px-10 py-5 rounded-[2rem] bg-slate-900 text-white font-black uppercase tracking-[0.2rem] text-[11px] hover:bg-black transition-all shadow-2xl shadow-indigo-500/20 active:scale-95">
            Ecosystem Certification <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-12 gap-8 min-h-0">
        <div className="col-span-4 flex flex-col gap-6 min-h-0">
          <div className="flex-1 bg-white rounded-[2.5rem] border-2 border-slate-50 p-6 shadow-2xl shadow-slate-200/50 flex flex-col min-h-0 overflow-hidden">
            <div className="flex items-center justify-between mb-6 bg-slate-50/50 p-4 rounded-2xl">
              <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em]">Feature Unit Tests</h3>
              <button onClick={runFeatureTests} className="text-[10px] font-black text-indigo-600 uppercase tracking-widest">Run Module</button>
            </div>
            <div className="flex-1 overflow-y-auto space-y-3 custom-scrollbar pr-2">
              {featureTestCases.map((tc, idx) => {
                const tf = featureTestFiles[idx] || '';
                const st = tcStatuses[tf];
                return (
                  <div key={idx} className={`p-5 rounded-[1.5rem] border-2 transition-all group ${st === 'pass' ? 'bg-emerald-50/30 border-emerald-100' : st === 'fail' ? 'bg-red-50/30 border-red-100' : 'bg-white border-slate-50 hover:border-blue-100'}`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-black text-sm text-slate-800 tracking-tight">{tc.name}</span>
                      <div className={`text-[9px] font-black uppercase tracking-widest px-2.5 py-1 rounded-full ${st === 'pass' ? 'bg-emerald-500 text-white' : st === 'fail' ? 'bg-red-500 text-white' : st === 'running' ? 'bg-indigo-600 text-white animate-pulse' : 'bg-slate-100 text-slate-400'}`}>
                        {st?.toUpperCase() || 'IDLE'}
                      </div>
                    </div>
                    <p className="text-[11px] text-slate-500 font-bold leading-relaxed mb-3">{tc.description}</p>
                    {tf && <div className="text-[10px] font-mono text-slate-400 bg-slate-100/50 px-2.5 py-1 rounded-lg border border-slate-100 inline-block font-bold">{tf.split('/').pop()}</div>}
                  </div>
                );
              })}
            </div>
          </div>
          <div className="flex-1 bg-white rounded-[2.5rem] border-2 border-slate-50 p-8 shadow-2xl shadow-slate-200/50 flex flex-col min-h-0">
            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em] mb-6">Manual Payload Forge</h3>
            <div className="flex gap-2 mb-4 scrollbar-hide overflow-x-auto">
               {Object.keys(TEST_SCENARIOS).map(k => (
                 <button key={k} onClick={() => setTestXml(TEST_SCENARIOS[k])} className="px-4 py-2 rounded-xl bg-slate-50 hover:bg-indigo-50 text-[10px] font-black uppercase tracking-widest transition-all border-2 border-transparent hover:border-indigo-100 whitespace-nowrap">{k}</button>
               ))}
            </div>
            <textarea value={testXml} onChange={e => setTestXml(e.target.value)}
              className="flex-1 w-full font-mono text-xs text-slate-800 bg-slate-50 border-2 border-slate-100 p-6 rounded-[1.5rem] focus:outline-none resize-none custom-scrollbar shadow-inner" />
            <button onClick={runTest} disabled={running} className="mt-6 w-full py-5 bg-slate-900 text-white text-[11px] font-black uppercase tracking-[0.3em] rounded-[1.5rem] shadow-2xl shadow-indigo-500/20 active:scale-[0.98] transition-all">Submit Transaction</button>
          </div>
        </div>

        <div className="col-span-5 flex flex-col min-h-0 bg-white border border-slate-100 rounded-[3rem] shadow-2xl shadow-slate-200/50 overflow-hidden relative group">
          <div className="px-10 py-8 border-b border-slate-50 flex items-center justify-between">
            <div className="flex items-center gap-3">
               <div className="w-1.5 h-6 bg-blue-600 rounded-full" />
               <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">Network Interceptor</h3>
            </div>
            {finalStatus && <span className={`text-[11px] font-black uppercase tracking-[0.2em] px-4 py-2 rounded-xl ${finalStatus.includes('SUCCESS') ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-red-50 text-red-600 border border-red-100'}`}>{finalStatus}</span>}
          </div>
          <div className="flex-shrink-0 flex gap-4 px-10 py-4 overflow-x-auto no-scrollbar bg-slate-50 border-b border-slate-100">
            {flowSteps.map(step => (
              <button key={step.id} onClick={() => setActiveStep(step)} className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${activeStep?.id === step.id ? 'bg-indigo-600 text-white shadow-xl shadow-indigo-500/20' : 'text-slate-400 hover:text-indigo-600'}`}>{step.label}</button>
            ))}
            {flowSteps.length === 0 && <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest italic flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-slate-300" /> Awaiting Network Activity…</span>}
          </div>
          <div className="flex-1 p-10 overflow-y-auto custom-scrollbar font-mono text-sm text-slate-800 whitespace-pre-wrap leading-relaxed shadow-inner">
            {activeStep ? activeStep.xml : (
              <div className="h-full flex flex-col items-center justify-center gap-6 opacity-40 grayscale group-hover:opacity-100 transition-all duration-1000">
                <Terminal className="w-20 h-20" />
                <div className="text-[10px] font-black uppercase tracking-[0.5em]">Titan Hub Interlock</div>
              </div>
            )}
          </div>
        </div>

        <div className="col-span-3 flex flex-col gap-6 min-h-0">
          <div className="flex-[2] bg-white rounded-[2.5rem] border-2 border-slate-50 p-8 shadow-2xl shadow-slate-200/50 flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-8 border-b border-slate-50 pb-6">
              <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em]">Audit Registry</h3>
              <div className="flex gap-2">
                <span className="text-[10px] font-black text-emerald-500 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100">{pass}P</span>
                <span className="text-[10px] font-black text-red-500 bg-red-50 px-2.5 py-1 rounded-full border border-red-100">{fail}F</span>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto space-y-3 custom-scrollbar">
              {results.map(r => (
                <div key={r.id} className={`p-5 rounded-2xl border-2 transition-all ${r.status === 'pass' ? 'bg-white border-emerald-100 hover:border-emerald-400' : 'bg-white border-red-100 hover:border-red-400'}`}>
                  <div className="font-black flex justify-between items-center mb-1">
                    <span className="text-xs text-slate-800 tracking-tight uppercase">{r.scenario}</span> 
                    <span className="text-[9px] text-slate-400 uppercase font-black">{r.ts}</span>
                  </div>
                  <div className="text-[10px] text-slate-500 font-bold tracking-tight opacity-70 group-hover:opacity-100 truncate">{r.detail}</div>
                </div>
              ))}
              {results.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-center py-10 opacity-20 filter grayscale">
                  <div className="w-12 h-12 rounded-full border-4 border-slate-200 border-t-slate-400 animate-spin mb-4" />
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Protocol Sync Pending…</p>
                </div>
              )}
            </div>
          </div>
          <div className="flex-1 bg-slate-900 rounded-[2.5rem] p-8 shadow-2xl shadow-indigo-500/20 flex flex-col min-h-0 group relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -translate-y-16 translate-x-16 blur-3xl group-hover:scale-150 transition-transform duration-1000" />
            <h3 className="text-[10px] font-black text-white/60 uppercase tracking-[0.25em] mb-6 flex items-center gap-3 relative z-10">
              <Sparkles className="w-4 h-4 text-white" />
              Agentic Test Synthesis
            </h3>
            <div className="flex flex-col gap-4 flex-1 relative z-10">
              <textarea 
                value={testPrompt} 
                onChange={e => setTestPrompt(e.target.value)} 
                className="flex-1 text-xs font-bold border-2 border-white/10 rounded-2xl p-5 bg-white/5 text-white placeholder-slate-500 resize-none focus:border-indigo-500 outline-none transition-all" 
                placeholder="Describe a custom NPCI test vector…" 
              />
              <button 
                onClick={handleGenerateTestCase}
                disabled={isGeneratingTest || !testPrompt.trim()}
                className="w-full py-4 bg-indigo-600 text-white text-[10px] font-black uppercase tracking-[0.3em] rounded-2xl shadow-lg hover:bg-indigo-700 transition-all disabled:opacity-50 flex items-center justify-center gap-3"
              >
                {isGeneratingTest ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Synthesizing...</>
                ) : (
                  <>Forge XML Vector</>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Inline Deploy View ─────────────────────────────────────────────────── */
interface DeployVersion { id: string; version?: string; seq_version?: number; description?: string; label?: string; timestamp?: string; }

function NFBDeployView({ plan, featureName }: { plan: CMPlan | null; featureName: string }) {
  const [versions, setVersions] = useState<DeployVersion[]>([]);
  const [selected, setSelected] = useState('');
  const [deployStatus, setDeployStatus] = useState('Standby');
  const [isDeploying, setIsDeploying] = useState(false);
  const [gitBranch, setGitBranch] = useState('...');
  const [gitStatus, setGitStatus] = useState('Checking...');

  const loadVersions = useCallback(async () => {
    try {
      const d = await fetch('/deploy/versions').then(r => r.json());
      setVersions(d.versions || []);
    } catch { /**/ }
  }, []);
  const refreshGit = useCallback(async () => {
    try {
      const d = await fetch('/git/info').then(r => r.json());
      if (d.is_repo) {
        setGitBranch(d.branch || 'main');
        setGitStatus(d.dirty ? 'Uncommitted changes' : 'Clean');
      }
    } catch { /**/ }
  }, []);

  useEffect(() => { loadVersions(); refreshGit(); }, []);

  const deploy = async () => {
    if (!selected) return;
    setIsDeploying(true); setDeployStatus('⏳ INITIALISING...');
    try {
      const resp = await fetch('/deploy', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ version: selected }) }).then(r => r.json());
      setDeployStatus(resp.restarting ? '✅ DEPLOYED' : (resp.message || 'SUCCESS'));
      if (resp.restarting) setTimeout(loadVersions, 3000);
    } finally { setIsDeploying(false); }
  };

  return (
    <div className="h-full flex flex-col px-10 py-10 animate-fadeIn overflow-hidden bg-white">
      {/* Header */}
      <div className="flex-shrink-0 flex items-center justify-between mb-10">
        <div className="flex items-center gap-6">
          <div className="w-16 h-16 rounded-[1.5rem] bg-indigo-600 flex items-center justify-center shadow-2xl shadow-indigo-500/20 text-white">
            <RocketIcon className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-4xl font-black text-slate-900 tracking-tighter leading-tight">
              Production Release
            </h2>
            <div className="flex items-center gap-2 mt-1">
               <span className="text-[10px] font-black text-indigo-600 uppercase tracking-widest leading-none bg-indigo-50 px-2 py-1 rounded">{featureName}</span>
               <div className="w-1 h-1 rounded-full bg-slate-200" />
               <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">Mainline Integration Node</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex flex-col items-end">
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-50 border border-slate-100 mb-1">
               <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
               <span className="text-[10px] font-black text-slate-600 uppercase tracking-widest font-mono">{gitBranch}</span>
            </div>
            <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest mr-1">{gitStatus}</span>
          </div>
          <button 
             onClick={() => window.location.href = '/'}
             className="px-10 py-5 rounded-[2rem] bg-slate-900 text-white font-black uppercase tracking-[0.2rem] text-[11px] hover:bg-black transition-all shadow-2xl shadow-indigo-500/20 active:scale-95">
             Complete Mission
          </button>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-12 gap-8 min-h-0">
        <div className="col-span-8 flex flex-col gap-8 min-h-0">
          <div className="bg-white rounded-[3rem] border-2 border-slate-50 p-10 shadow-2xl shadow-slate-200/50 flex flex-col min-h-0">
            <div className="flex items-center gap-4 mb-8">
               <div className="w-12 h-12 rounded-2xl bg-indigo-50 flex items-center justify-center text-indigo-600 shadow-lg shadow-indigo-500/5">
                 <RefreshCw className="w-6 h-6" />
               </div>
               <div>
                 <h3 className="text-xl font-black text-slate-900 tracking-tight">Deployment Strategy</h3>
                 <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Rolling Update via Blue/Green Agents</p>
               </div>
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-3 custom-scrollbar pr-2 mb-8">
              {versions.length === 0 ? (
                <div className="h-full flex items-center justify-center opacity-30 italic font-bold">No versions synthesised yet…</div>
              ) : versions.map(v => (
                <button
                  key={v.id}
                  onClick={() => setSelected(v.id)}
                  className={`w-full flex items-center gap-6 p-6 rounded-[2rem] border-2 transition-all ${
                    selected === v.id 
                      ? 'bg-slate-900 border-indigo-500/30 text-white shadow-2xl shadow-slate-900/30 -translate-y-1' 
                      : 'bg-white border-slate-50 text-slate-900 hover:border-indigo-100'
                  }`}
                >
                  <div className={`w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 transition-colors ${selected === v.id ? 'bg-white text-slate-900' : 'bg-slate-50 text-slate-400'}`}>
                    <GitBranch className="w-5 h-5 font-black" />
                  </div>
                  <div className="flex-1 text-left">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-black tracking-tight">{v.version || `v${v.seq_version}.0`}</span>
                      <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded ${selected === v.id ? 'bg-white/20' : 'bg-slate-100 text-slate-400'}`}>{v.id.substring(0,8)}</span>
                    </div>
                    <div className={`text-[11px] font-bold truncate opacity-70 group-hover:opacity-100 transition-opacity uppercase tracking-widest`}>{v.description || 'System patch synthesised by reasoning agent'}</div>
                  </div>
                  {selected === v.id && (
                    <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center animate-pulse">
                      <div className="w-2 h-2 rounded-full bg-white" />
                    </div>
                  )}
                </button>
              ))}
            </div>

            <div className="mt-auto grid grid-cols-2 gap-4">
               <button 
                  onClick={deploy} 
                  disabled={!selected || isDeploying}
                  className="flex items-center justify-center gap-3 py-6 bg-indigo-600 text-white rounded-[2rem] font-black uppercase tracking-[0.25em] text-[11px] hover:bg-slate-900 transition-all disabled:opacity-50 shadow-2xl shadow-indigo-500/20 active:scale-95"
               >
                 {isDeploying ? <Loader2 className="w-5 h-5 animate-spin" /> : <RocketIcon className="w-5 h-5" />}
                 Hot Sync Mainline
               </button>
               <div className={`flex items-center justify-center gap-4 px-8 py-6 rounded-[2rem] border-2 font-black uppercase tracking-[0.2em] text-[10px] ${deployStatus.includes('✅') || deployStatus.includes('SUCCESS') ? 'bg-emerald-50 border-emerald-100 text-emerald-600' : 'bg-slate-50 border-slate-100 text-slate-400'}`}>
                 <div className={`w-2 h-2 rounded-full ${deployStatus.includes('✅') ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]' : 'bg-slate-300'}`} />
                 {deployStatus}
               </div>
            </div>
          </div>
        </div>

        <div className="col-span-4 flex flex-col gap-8 min-h-0">
          <div className="bg-white rounded-[3rem] border-2 border-slate-50 p-10 shadow-2xl shadow-slate-200/50 flex-1 relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-40 h-40 bg-indigo-50/50 rounded-full translate-x-20 -translate-y-20 blur-3xl group-hover:scale-125 transition-transform duration-1000" />
            <div className="relative z-10">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-slate-100 flex items-center justify-center text-indigo-600 mb-6 shadow-sm">
                <ShieldIcon className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-black text-slate-900 tracking-tight mb-2">Integrity Shield</h3>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-8 leading-relaxed">Cross-referencing deployment v{plan?.version || '1.x'} against NPCI Master Directives and RBI Cryptographic Standards.</p>
              
              <div className="space-y-6">
                {[
                  { label: 'Schema Consistency', status: 'Verified' },
                  { label: 'Regulatory Guardrails', status: 'Locked' },
                  { label: 'Network Latency', status: 'Optimal' },
                  { label: 'Security Handshake', status: 'Trusted' },
                ].map(check => (
                  <div key={check.label} className="flex items-center justify-between border-b border-slate-50 pb-4">
                    <span className="text-[10px] font-black text-slate-700 uppercase tracking-widest">{check.label}</span>
                    <span className="text-[10px] font-black text-indigo-600 uppercase tracking-widest bg-indigo-50 px-2 py-1 rounded">{check.status}</span>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="mt-12 p-8 rounded-[2rem] bg-slate-900 text-white relative z-10 shadow-2xl shadow-indigo-500/30 group/banner overflow-hidden">
               <div className="absolute inset-0 bg-slate-900 translate-y-full group-hover/banner:translate-y-0 transition-transform duration-500" />
               <div className="relative z-10 text-center">
                 <div className="text-[10px] font-black uppercase tracking-[0.4em] mb-2 opacity-50 group-hover/banner:opacity-100 transition-opacity">Titan Orchestrator</div>
                 <div className="text-xl font-black tracking-tighter">MISSION COMPLETE</div>
               </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── A2A Phase View — Manifest first, then Execution ──────────────────── */
function A2APhaseView({
  plan,
  featureName,
  onConfirm,
}: {
  plan: CMPlan | null;
  featureName: string;
  onConfirm: () => void;
}) {
  const [dispatched, setDispatched] = useState(false);

  const planSteps: string[] = Array.isArray(plan?.plan) ? (plan!.plan as string[]) : [];

  const impactLines: string[] = (() => {
    const raw = plan?.impact_analysis;
    if (!raw) return [];
    if (Array.isArray(raw)) return raw.map((x: unknown) => typeof x === 'string' ? x : JSON.stringify(x));
    if (typeof raw === 'object') return Object.entries(raw as Record<string, string>).map(([k, v]) => `${k}: ${v}`);
    return [];
  })();

  const participants = A2A_NODES.map(n => n.label);

  if (!dispatched) {
    return (
      <div className="flex-1 flex flex-col overflow-y-auto bg-slate-900 text-white relative" style={{ maxHeight: '100%' }}>
        <div className="absolute inset-0 opacity-10 pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, #6366f1 1px, transparent 0)', backgroundSize: '40px 40px' }} />
        <div className="relative z-10 max-w-4xl mx-auto w-full p-10">
          {/* Header */}
          <div className="flex items-center gap-4 mb-8">
            <div className="w-16 h-16 rounded-[1.5rem] bg-indigo-500/20 border-2 border-indigo-500/40 flex items-center justify-center shadow-[0_0_30px_rgba(99,102,241,0.3)] flex-shrink-0">
              <FileCheck className="w-8 h-8 text-indigo-400" />
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-3xl font-black tracking-tighter uppercase italic">A2A Change Manifest</h2>
              <p className="text-indigo-400 text-xs font-black uppercase tracking-[0.2em] mt-1 truncate">{featureName} · Review before dispatch</p>
            </div>
            <div className="flex items-center gap-3 px-5 py-2.5 bg-amber-500/10 border border-amber-500/30 rounded-2xl flex-shrink-0">
              <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              <span className="text-amber-300 text-xs font-black uppercase tracking-widest">Pending Dispatch</span>
            </div>
          </div>

          {/* Manifest Card */}
          <div className="bg-slate-800/60 border border-slate-700 rounded-3xl p-8 mb-6 backdrop-blur-md">
            {/* Meta row */}
            <div className="grid grid-cols-3 gap-6 mb-8 pb-8 border-b border-slate-700">
              <div>
                <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Version</div>
                <div className="text-lg font-black text-white">{plan?.version || `v${plan?.seq_version ?? 1}.0`}</div>
              </div>
              <div>
                <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Feature</div>
                <div className="text-sm font-black text-indigo-300 truncate">{featureName}</div>
              </div>
              <div>
                <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Status</div>
                <div className="text-sm font-black text-amber-300">Awaiting Dispatch</div>
              </div>
            </div>

            {plan?.description && (
              <div className="mb-8">
                <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-3">Description</div>
                <p className="text-slate-300 text-sm font-bold leading-relaxed">{plan.description}</p>
              </div>
            )}

            {planSteps.length > 0 && (
              <div className="mb-8">
                <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4">Implementation Plan ({planSteps.length} steps)</div>
                <div className="space-y-2">
                  {planSteps.map((step, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-slate-900/50 border border-slate-700">
                      <div className="w-6 h-6 rounded-full bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <span className="text-[10px] font-black text-indigo-400">{i + 1}</span>
                      </div>
                      <span className="text-xs font-bold text-slate-300 leading-relaxed">{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {impactLines.length > 0 && (
              <div className="mb-8">
                <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4">Impact Analysis</div>
                <div className="space-y-2">
                  {impactLines.map((item, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-emerald-900/20 border border-emerald-500/20">
                      <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                      <span className="text-xs font-bold text-slate-300">{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {plan?.brd && (
              <div className="mb-8">
                <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-3">BRD Summary</div>
                <div className="bg-slate-900/60 border border-slate-700 rounded-2xl p-4 text-xs font-mono text-slate-400 leading-relaxed max-h-32 overflow-y-auto custom-scrollbar">
                  {plan.brd.slice(0, 600)}{plan.brd.length > 600 ? '…' : ''}
                </div>
              </div>
            )}

            {plan?.tsd && (
              <div>
                <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-3">TSD Summary</div>
                <div className="bg-slate-900/60 border border-slate-700 rounded-2xl p-4 text-xs font-mono text-slate-400 leading-relaxed max-h-32 overflow-y-auto custom-scrollbar">
                  {plan.tsd.slice(0, 600)}{plan.tsd.length > 600 ? '…' : ''}
                </div>
              </div>
            )}

            {!plan && (
              <div className="flex items-center justify-center py-12 opacity-50">
                <p className="text-sm font-black text-slate-500 uppercase tracking-widest">No manifest data — approve Technical Plan first</p>
              </div>
            )}
          </div>

          {/* Dispatch Button */}
          <button
            onClick={() => setDispatched(true)}
            className="w-full py-6 bg-indigo-600 hover:bg-indigo-500 text-white font-black uppercase tracking-[0.3em] text-[12px] rounded-2xl shadow-[0_10px_30px_rgba(99,102,241,0.4)] hover:shadow-[0_15px_40px_rgba(99,102,241,0.5)] transition-all active:scale-95 flex items-center justify-center gap-4"
          >
            <ZapIcon className="w-5 h-5" />
            Dispatch Manifest to All Agents
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    );
  }

  /* Step 2: Manifest dispatched — participants acknowledge, then start execution */
  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-slate-900 text-white p-16 text-center relative">
      <div className="absolute inset-0 opacity-20 pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, #6366f1 1px, transparent 0)', backgroundSize: '40px 40px' }} />
      <div className="max-w-xl relative z-10 w-full">
        <div className="w-24 h-24 rounded-[2.5rem] bg-emerald-500/10 flex items-center justify-center mx-auto mb-8 border-2 border-emerald-500/30 shadow-[0_0_50px_rgba(16,185,129,0.2)]">
          <CheckCircle className="w-12 h-12 text-emerald-400" />
        </div>
        <h2 className="text-4xl font-black mb-3 tracking-tighter uppercase italic">Manifest Dispatched</h2>
        <p className="text-slate-400 mb-8 font-bold text-[10px] uppercase tracking-[0.3em] leading-relaxed opacity-80">
          Change Manifest {plan?.version || `v${plan?.seq_version ?? 1}.0`} broadcast to all participant agents. Awaiting acknowledgments.
        </p>
        <div className="flex flex-col gap-2 mb-10 text-left">
          {participants.map((agent, i) => (
            <div
              key={agent}
              className="flex items-center gap-3 p-3 bg-slate-800/60 rounded-xl border border-slate-700 animate-slideIn"
              style={{ animationDelay: `${i * 0.12}s` }}
            >
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse flex-shrink-0" />
              <span className="text-xs font-black text-slate-300 uppercase tracking-widest flex-1">{agent}</span>
              <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">ACK ✓</span>
            </div>
          ))}
        </div>
        <button
          onClick={onConfirm}
          className="w-full py-6 bg-indigo-600 text-white font-black uppercase tracking-[0.4em] text-[11px] rounded-2xl shadow-[0_20px_50px_rgba(99,102,241,0.3)] hover:bg-white hover:text-slate-900 transition-all active:scale-95 border-2 border-transparent hover:border-indigo-400 flex items-center justify-center gap-3"
        >
          <RocketIcon className="w-5 h-5" />
          Start Live Execution
        </button>
      </div>
    </div>
  );
}

/* ─── Per-stage AI transition overlay ───────────────────────────────────── */
const STAGE_TRANSITION_STEPS: Record<string, { title: string; steps: string[] }> = {
  clarify: {
    title: 'Aligning Strategic Vision',
    steps: [
      'Analyzing PM prompt for intent and sentiment…',
      'Loading previous product context and RBI clauses…',
      'Cross-referencing ecosystem participant requirements…',
      'Drafting NPCI | CONFIDENTIAL Vision Proposal…',
      'Identifying potential strategic gaps and opportunities…',
      'Finalizing thought process and clarification points…',
    ],
  },
  'product-kit': {
    title: 'Generating Universal Product Kit',
    steps: [
      'Analysing approved canvas for document structure…',
      'Drafting High-Fidelity Product Note (API specs included)…',
      'Writing NPCI Operational Circular with compliance checklist…',
      'Compiling AI-generated FAQs for Payer/Payee PSPs…',
      'Creating 90-second product storyboard and deck slides…',
      'Summarising applicable RBI Master Directions (OC 228)…',
      'Generating 10 comprehensive XML test vectors…',
    ],
  },
  'technical-plan': {
    title: 'Architecting Technical Specification',
    steps: [
      'Parsing product kit and regulatory requirements…',
      'Mapping transaction flows to specific XML schemas…',
      'Defining state transitions and ledger update logic…',
      'Identifying cross-participant impact (Bank, PSP, Switch)…',
      'Drafting Change Manifest for Agent-to-Agent synchronization…',
      'Formulating NPCI Technical Specification Document (TSD)…',
      'Finalising implementation roadmap and gating criteria…',
    ],
  },
  'a2a-sync': {
    title: 'Agentic Synchronization Protocol',
    steps: [
      'NPCI Orchestrator broadcasting Change Manifest…',
      'Distributing TSD and Technical Intent to participants…',
      'Bank/PSP Agents analyzing local codebase impact…',
      'Synchronizing multi-party risk and audit modules…',
      'Awaiting technical acknowledgments from participant nodes…',
      'Verifying A2A technical alignment for the new feature…',
    ],
  },
};

function StageTransitionOverlay({ targetStage, featureName }: { targetStage: string; featureName: string }) {
  const config = STAGE_TRANSITION_STEPS[targetStage] || {
    title: 'AI is preparing the next stage…',
    steps: ['Analysing context…', 'Generating content…', 'Applying NPCI standards…'],
  };
  const [currentStep, setCurrentStep] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const tick = setInterval(() => setElapsed(s => s + 0.1), 100);
    const step = setInterval(() => setCurrentStep(s => Math.min(s + 1, config.steps.length - 1)), 800);
    return () => { clearInterval(tick); clearInterval(step); };
  }, [config.steps.length]);

  return (
    <div className="fixed inset-0 bg-slate-50/90 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200 rounded-3xl p-8 max-w-md w-full shadow-2xl animate-popIn">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-2xl bg-indigo-600 flex items-center justify-center flex-shrink-0">
            <ZapIcon className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div>
            <div className="text-slate-900 font-bold text-base">{config.title}</div>
            <div className="text-indigo-600 [text-shadow:_0_0_10px_rgba(99,102,241,0.2)] text-sm font-black uppercase tracking-widest">{featureName} · {elapsed.toFixed(1)}s</div>
          </div>
        </div>
        <div className="space-y-2">
          {config.steps.map((step, i) => {
            const done = i < currentStep;
            const active = i === currentStep;
            return (
              <div key={i} className={`flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-300 ${active ? 'bg-indigo-50 border border-indigo-100' : ''}`}>
                <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold transition-all shadow-sm ${done ? 'bg-emerald-500 text-white' : active ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-400'}`}>
                  {done ? '✓' : active ? <div className="w-2 h-2 rounded-full bg-white animate-pulse" /> : i + 1}
                </div>
                <span className={`text-xs font-bold transition-colors ${done ? 'text-emerald-600' : active ? 'text-slate-900' : 'text-slate-300'}`}>{step}</span>
              </div>
            );
          })}
        </div>
        <div className="mt-5 h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-indigo-600 to-indigo-400 rounded-full transition-all duration-700 shadow-[0_0_10px_rgba(99,102,241,0.4)]" style={{ width: `${Math.round((currentStep / (config.steps.length - 1)) * 100)}%` }} />
        </div>
        <div className="text-center text-[10px] font-black text-slate-400 mt-4 uppercase tracking-widest">
          Titan Orchestration Matrix · NPCI AI
        </div>
      </div>
    </div>
  );
}

/* ─── Root App Component ─────────────────────────────────────────────────── */
export default function App() {
  /**
   * TITAN ORCHESTRATOR CORE
   * -----------------------
   * The main state machine that manages the end-to-end SDLC.
   * It coordinates multiple specialized AI agent views and maintains the 
   * 'Source of Truth' for the current UPI feature development.
   */
  // DEV SHORTCUT: ?skip=docgen  — jumps straight to document generation
  const _skipParam = new URLSearchParams(window.location.search).get('skip');
  const _devCanvas: CanvasData | null = _skipParam === 'docgen' ? {
    featureName: 'UPI Credit Line',
    buildTitle: 'Credit Line on UPI — Pre-Sanctioned Credit for All',
    sections: [
      { title: 'Overview', content: 'Enable pre-sanctioned credit lines to be linked to a UPI VPA, allowing users to make purchases and P2P transfers from credit without a physical card.' },
      { title: 'User Journey', content: 'User onboards credit line from bank app → links to UPI VPA → makes payment from credit line at any UPI merchant.' },
      { title: 'Integration Points', content: 'Bank CBS via ISO-20022, NPCI UPI switch, PSP mobile SDK.' },
    ],
    rbiGuidelines: 'RBI circular DPSS.CO.PD No.3/02.12.004/2022-23 on credit lines on UPI.',
    ecosystemChallenges: 'Low credit penetration in Tier 2/3 cities; high MDR resistance from merchants.',
  } : null;

  const [phase, setPhase] = useState<AppPhase>(_skipParam === 'docgen' ? 'product-kit' : 'input');
  const [prompt, setPrompt] = useState(_skipParam === 'docgen' ? 'UPI Credit Line feature' : '');
  const [featureName, setFeatureName] = useState(_skipParam === 'docgen' ? 'UPI Credit Line' : '');
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [canvas, setCanvas] = useState<CanvasData | null>(_devCanvas);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [executionItems, setExecutionItems] = useState<ExecutionItem[]>([]);
  const [technicalPlan, setTechnicalPlan] = useState<CMPlan | null>(null);
  const [completedStages, setCompletedStages] = useState<Set<Stage>>(
    _skipParam === 'docgen' ? new Set(['clarify', 'canvas'] as Stage[]) : new Set()
  );
  const [transitionTarget, setTransitionTarget] = useState<string | null>(null);

  const currentStage: Stage = PHASE_TO_STAGE[phase];
  const markCompleted = (stage: Stage) => setCompletedStages(prev => new Set([...prev, stage]));

  const handlePromptSubmit = useCallback((p: string, name: string) => {
    setPrompt(p);
    setFeatureName(name || p.split(' ').slice(0, 4).join(' '));
    setPhase('clarify');
  }, []);

  const handleCanvasApprove = useCallback(async (approvedCanvas: CanvasData) => {
    if (completedStages.has('canvas')) return;
    setCanvas(approvedCanvas);
    markCompleted('canvas');

    // Add approval message to chat history
    setChatMessages(prev => {
      if (prev.some(m => m.id === 'u-appr-canv-final')) return prev;
      return [
        ...prev,
        { 
          id: 'u-appr-canv-final', 
          role: 'user', 
          blocks: [{ type: 'text', text: 'Product Canvas is approved. Proceeding to Product Kit.' }], 
          createdAt: Date.now() 
        }
      ];
    });

    setPhase('product-kit');
    
    // Clear backend audit gates
    apiApprovePhase('IDEATION');
    apiApprovePhase('CANVAS');
    apiApprovePhase('PROTOTYPE');
  }, [completedStages]);

  const handleDocumentsApprove = useCallback(async (approvedDocs: Document[], execItems: ExecutionItem[]) => {
    if (!canvas) return;
    setDocuments(approvedDocs);
    setExecutionItems(execItems);
    markCompleted('product-kit');
    setPhase('brd');
    apiApprovePhase('KIT');
  }, [canvas]);

  const handleBRDApprove = useCallback(() => {
    markCompleted('brd');
    setPhase('technical-plan');
    apiApprovePhase('BRD_FORMALIZATION');
  }, []);

  const handleTechnicalPlanApprove = useCallback((plan: CMPlan) => {
    markCompleted('technical-plan');
    setTechnicalPlan(plan);
    setPhase('a2a-sync');
    // TSD approval is sent to backend gate; approve-change fires later from NFBLiveExecution
    apiApprovePhase('TSD_SPEC');
  }, []);

  const handleA2ASyncComplete = useCallback(() => {
    markCompleted('a2a-sync');
    setPhase('nfb-execution');
    // MANIFEST_DISPATCH gate will be handled inside NFBLiveExecution after SSE opens
  }, []);

  const handleStageClick = (stage: Stage) => {
    // Always allow navigating to a completed stage (backward navigation)
    if (completedStages.has(stage as any)) {
      if (stage === 'canvas') setPhase('thinking-canvas');
      else if (stage === 'product-kit' && (completedStages.has('canvas') || documents.length > 0)) setPhase('product-kit');
      else if (stage === 'product-kit') setPhase('product-kit');
      else if (stage === 'brd') setPhase('brd');
      else if (stage === 'technical-plan') setPhase('technical-plan');
      else if (stage === 'a2a-sync') setPhase('a2a-sync');
      else if (stage === 'execution') setPhase('nfb-execution');
      else if (stage === 'verify') setPhase('nfb-verify');
      else if (stage === 'certification') setPhase('nfb-certification');
      else if (stage === 'deploy') setPhase('nfb-deploy');
      else if (stage === 'clarify') setPhase('clarify');
      return;
    }
    // Forward navigation — current stage or next unlocked
    if (stage === 'clarify') setPhase('clarify');
    else if (stage === 'canvas') setPhase('thinking-canvas');
    else if (stage === 'product-kit' && (completedStages.has('canvas') || documents.length > 0)) setPhase('product-kit');
    else if (stage === 'brd' && completedStages.has('product-kit')) setPhase('brd');
    else if (stage === 'technical-plan' && canvas) setPhase('technical-plan');
    else if (stage === 'a2a-sync' && technicalPlan) setPhase('a2a-sync');
    else if (stage === 'execution' && completedStages.has('a2a-sync')) setPhase('nfb-execution');
    else if (stage === 'verify' && completedStages.has('execution')) setPhase('nfb-verify');
    else if (stage === 'certification' && completedStages.has('verify')) setPhase('nfb-certification');
    else if (stage === 'deploy' && completedStages.has('certification')) setPhase('nfb-deploy');
  };

  /* ─── PHASE: INPUT ────────────────────────────────────────── */
  if (phase === ('input' as any)) {
    return (
      <div className="h-screen w-screen flex flex-col bg-slate-50 relative overflow-hidden">
        <Header stage="input" featureName="" onOpenRegistry={() => setPhase('agent-registry')} />
        <PromptInput onSubmit={handlePromptSubmit} />
        <div className="absolute -bottom-20 -left-20 w-96 h-96 bg-indigo-500/10 blur-[100px] rounded-full" />
        <div className="absolute -top-20 -right-20 w-96 h-96 bg-blue-500/5 blur-[100px] rounded-full" />
      </div>
    );
  }

  /* ─── PHASE: CLARIFY ────────────────────────────────────────── */
  if (phase === ('clarify' as any)) {
    return (
      <div className="h-screen w-screen flex flex-col bg-slate-50 overflow-hidden font-sans">
        <Header stage="clarify" featureName={featureName} onOpenRegistry={() => setPhase('agent-registry')} />
        <StageProgress currentStage={currentStage} onStageClick={handleStageClick} completedStages={completedStages} />
        <ClarifyView
          prompt={prompt}
          onClarified={(_context) => {
            markCompleted('clarify' as any);
            setPhase('thinking-canvas');
          }}
        />
      </div>
    );
  }


  /* ─── PHASE: THINKING / CANVAS ────────────────────────────── */
  return (
    <div className="h-screen overflow-hidden bg-slate-50 flex flex-col font-sans selection:bg-indigo-600/10 selection:text-indigo-600">
      <Header stage={currentStage} featureName={featureName} onOpenRegistry={() => setPhase('agent-registry')} />
      <StageProgress currentStage={currentStage} onStageClick={handleStageClick} completedStages={completedStages} />

      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {transitionTarget && <StageTransitionOverlay targetStage={transitionTarget} featureName={featureName} />}
        {phase === 'input' && <PromptInput onSubmit={handlePromptSubmit} />}
        {prompt && phase !== 'input' && (
          <div style={{ display: (phase === 'thinking-canvas' || phase === 'clarify') ? 'flex' : 'none' }} className="flex-1 flex flex-col overflow-hidden">
            <ChatPage 
              prompt={prompt} 
              featureName={featureName} 
              messages={chatMessages}
              setMessages={setChatMessages}
              onApprove={handleCanvasApprove} 
            />
          </div>
        )}
        <div style={{ display: 'none' }} className="flex-1 overflow-y-auto">
        </div>
        <div style={{ display: phase === 'product-kit' && canvas ? 'flex' : 'none' }} className="flex-1 flex flex-col overflow-hidden animate-fadeIn relative">
          {canvas && (
            <DocumentsChatPage 
              canvas={canvas} 
              featureName={featureName} 
              messages={chatMessages}
              setMessages={setChatMessages}
              active={phase === 'product-kit'}
              onApprove={(docs, items) => handleDocumentsApprove(docs, items)} 
            />
          )}
        </div>
        <div style={{ display: phase === 'brd' ? 'flex' : 'none' }} className="flex-1 flex flex-col overflow-hidden animate-fadeIn justify-center items-center bg-slate-50 p-20 text-center">
            <div className="max-w-xl bg-white p-12 rounded-[3.5rem] shadow-2xl shadow-indigo-500/10 border border-slate-100 relative overflow-hidden group">
              <div className="absolute top-0 inset-x-0 h-2 bg-gradient-to-r from-indigo-500 via-purple-500 to-rose-500" />
              <div className="w-24 h-24 rounded-[2rem] bg-indigo-50 flex items-center justify-center mx-auto mb-8 shadow-xl shadow-indigo-500/10 transition-all group-hover:scale-110 group-hover:rotate-3">
                <FileCheck className="w-11 h-11 text-indigo-600" />
              </div>
              <h2 className="text-4xl font-black text-slate-900 mb-4 tracking-tighter uppercase italic">BRD Signed Intent</h2>
              <p className="text-slate-500 mb-10 font-bold tracking-tight uppercase text-[10px] tracking-[0.3em] leading-relaxed opacity-60">The Product Kit has been verified. NPCI agents are formalizing the final signed Business Requirements Document (BRD) for multi-party nodal synchronization.</p>
              <button onClick={handleBRDApprove} className="w-full py-5 bg-slate-900 text-white font-black uppercase tracking-[0.4em] text-[11px] rounded-2xl shadow-2xl hover:bg-black transition-all active:scale-95 flex items-center justify-center gap-3 group/btn">
                Final Sign-off <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
              </button>
            </div>
        </div>
        <div style={{ display: phase === 'technical-plan' && canvas ? 'flex' : 'none' }} className="flex-1 flex flex-col overflow-hidden animate-fadeIn relative">
          {canvas && <TechnicalPlanView canvas={canvas} active={phase === 'technical-plan'} featureName={featureName} executionItems={executionItems} onApprove={handleTechnicalPlanApprove} />}
        </div>
        <div style={{ display: phase === 'a2a-sync' ? 'flex' : 'none' }} className="flex-1 flex flex-col overflow-hidden animate-fadeIn">
          <A2APhaseView
            plan={technicalPlan}
            featureName={featureName}
            onConfirm={handleA2ASyncComplete}
          />
        </div>
        <div style={{ display: phase === 'nfb-execution' ? 'block' : 'none' }} className="flex-1 overflow-hidden">
          {completedStages.has('a2a-sync') && <NFBLiveExecution featureName={featureName} execPlan={technicalPlan} onProceed={() => { markCompleted('execution'); setPhase('nfb-verify'); apiApprovePhase('ECOSYSTEM_TESTING'); }} />}
        </div>
        <div style={{ display: phase === 'nfb-verify' ? 'block' : 'none' }} className="flex-1 overflow-y-auto pt-2">
          {completedStages.has('execution') && <NFBVerifyView canvas={canvas} onProceed={() => { markCompleted('verify'); setPhase('nfb-certification'); }} />}
        </div>
        <div style={{ display: phase === 'nfb-certification' ? 'block' : 'none' }} className="flex-1 overflow-y-auto pt-2">
          {completedStages.has('verify') && <CertificationView featureName={featureName} onProceed={() => { markCompleted('certification'); setPhase('nfb-deploy'); apiApprovePhase('FINAL_DEPLOYMENT'); }} />}
        </div>
        <div style={{ display: phase === 'nfb-deploy' ? 'block' : 'none' }} className="flex-1 overflow-y-auto pt-2">
          {completedStages.has('certification') && <NFBDeployView plan={technicalPlan!} featureName={featureName} />}
        </div>
        <div style={{ display: phase === 'agent-registry' ? 'block' : 'none' }} className="flex-1 h-full overflow-hidden">
          <RegistryPortal onClose={() => setPhase('input')} />
        </div>
      </main>
    </div>
  );
}
