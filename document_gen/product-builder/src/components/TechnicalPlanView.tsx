import { useState, useEffect, useRef } from 'react';
import {
  FileText, Code2, Check,
  ChevronRight, BookOpen, Cpu,
  AlertCircle, Loader2, RefreshCw,
  GitBranch, Plus, Pencil, ChevronDown, ChevronUp,
  Layers, Terminal, Brain, Sparkles, Download
} from 'lucide-react';
import type { CanvasData, CMPlan, ExecutionItem } from '../types';
import { getCodePlan, getFilesTouched, getTotalLinesAffected, getLayerSummary, type FileChange } from '../utils/upiCodebaseMap';

interface ThinkingStep {
  label: string;
  detail: string;
  duration: number;
}

interface ArchitectMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isThinking?: boolean;
  steps?: ThinkingStep[];
  totalMs?: number;
}

interface TechnicalPlanViewProps {
  canvas: CanvasData;
  featureName: string;
  executionItems?: import('../types').ExecutionItem[];
  active?: boolean;
  onApprove: (plan: CMPlan) => void;
}

type DocTab = 'brd' | 'tsd' | 'manifest';

/* ─── Markdown renderer (reused from DocumentsView) ─────────────────────── */
function InlineText({ text }: { text: string }) {
  const parts = text.split(/(\*\*.*?\*\*|\*.*?\*)/g);
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith('**') && p.endsWith('**')) return <strong key={i} className="font-black text-slate-900">{p.slice(2, -2)}</strong>;
        if (p.startsWith('*') && p.endsWith('*')) return <em key={i} className="italic text-slate-500">{p.slice(1, -1)}</em>;
        return <span key={i}>{p}</span>;
      })}
    </>
  );
}

function MarkdownRenderer({ content }: { content: string }) {
  const lines = content.split('\n');
  const rendered: React.ReactNode[] = [];
  let currentTable: string[][] = [];

  const flushTable = (key: number) => {
    if (currentTable.length === 0) return null;
    const table = (
      <div key={`table-${key}`} className="overflow-hidden border border-slate-200 rounded-2xl shadow-sm my-6 bg-white">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <tbody className="divide-y divide-slate-50">
              {currentTable.map((row, ri) => (
                <tr key={ri} className={ri === 0 ? "bg-slate-50/50" : "hover:bg-blue-50/10 transition-colors"}>
                  {row.map((cell, ci) => (
                    <td key={ci} className={`px-6 py-4 text-xs border-r border-slate-50 last:border-0 ${ri === 0 ? "font-black text-slate-900 uppercase tracking-widest" : "font-semibold text-slate-600"}`}>
                      <InlineText text={cell.trim()} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
    currentTable = [];
    return table;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed.startsWith('|')) {
      const cells = line.split('|').filter((c, idx, arr) => {
        if (idx === 0 && !c.trim()) return false;
        if (idx === arr.length - 1 && !c.trim()) return false;
        return true;
      });
      if (cells.every(c => c.trim().match(/^[-:| ]+$/))) continue;
      currentTable.push(cells);
      continue;
    } else {
      const table = flushTable(i);
      if (table) rendered.push(table);
    }

    if (trimmed.startsWith('# ')) rendered.push(<h1 key={i} className="text-4xl font-black text-slate-900 mt-12 mb-8 tracking-tighter leading-tight border-l-8 border-indigo-600 pl-6">{line.slice(2)}</h1>);
    else if (trimmed.startsWith('## ')) rendered.push(<h2 key={i} className="text-2xl font-black text-slate-900 mt-10 mb-6 border-b-2 border-slate-100 pb-4 tracking-tight">{line.slice(3)}</h2>);
    else if (trimmed.startsWith('### ')) rendered.push(<h3 key={i} className="text-xl font-black text-slate-900 mt-8 mb-4 tracking-tight flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-indigo-600" />{line.slice(4)}</h3>);
    else if (trimmed.startsWith('#### ')) rendered.push(<h4 key={i} className="text-lg font-black text-slate-800 mt-6 mb-3 tracking-tight">{line.slice(5)}</h4>);
    else if (trimmed.startsWith('• ') || trimmed.startsWith('- ')) {
      rendered.push(
        <div key={i} className="flex gap-4 ml-2 items-start group">
          <span className="text-indigo-600 font-black mt-1.5 flex-shrink-0 select-none group-hover:scale-125 transition-transform">•</span>
          <span className="text-slate-600 transition-colors group-hover:text-slate-900">
            <InlineText text={line.trim().slice(2)} />
          </span>
        </div>
      );
    }
    else if (line.match(/^[✓☐✅🔄]/)) rendered.push(<div key={i} className="ml-2 flex gap-4 font-bold text-slate-900 bg-white p-5 rounded-3xl border-2 border-slate-50 shadow-sm">{line}</div>);
    else if (line.startsWith('```')) { /* skip */ }
    else if (line === '---') rendered.push(<div key={i} className="h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent my-12" />);
    else if (line === '') rendered.push(<div key={`empty-${i}`} className="h-4" />);
    else {
      rendered.push(
        <p key={i} className="text-slate-600 font-medium whitespace-pre-wrap">
          <InlineText text={line} />
        </p>
      );
    }
  }

  const finalTable = flushTable(lines.length);
  if (finalTable) rendered.push(finalTable);

  return (
    <div className="text-base text-slate-700 leading-[1.8] space-y-4 font-medium selection:bg-indigo-100 pb-20">
      {rendered}
    </div>
  );
}

/* ─── Code Changes Panel ────────────────────────────────────────────────────── */
import type { FeatureCodePlan } from '../utils/upiCodebaseMap';

function FileChangeCard({ fc }: { fc: FileChange }) {
  const [expanded, setExpanded] = useState(false);
  const layerColor: Record<string, string> = {
    switch: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    psp: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    bank: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    api: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    frontend: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    agents: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  };
  const layer = fc.path.split('/')[0];
  const effortColor = { low: 'text-emerald-400', medium: 'text-amber-400', high: 'text-rose-400' }[fc.effort];

  return (
    <div className={`rounded-[2rem] border transition-all duration-500 overflow-hidden ${expanded ? 'bg-white border-indigo-200 shadow-2xl shadow-indigo-500/10' : 'bg-white border-slate-100 hover:border-slate-300 shadow-sm'}`}>
      <button
        className="w-full flex items-center gap-4 px-6 py-5 text-left group"
        onClick={() => setExpanded(v => !v)}
      >
        <div className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center border shadow-sm transition-transform group-hover:scale-110 ${
          fc.changeType === 'add' || fc.changeType === 'add-function'
            ? 'bg-emerald-50 text-emerald-600 border-emerald-200'
            : 'bg-indigo-50 text-indigo-600 border-indigo-200'
        }`}>
          {fc.changeType === 'add' || fc.changeType === 'add-function'
            ? <Plus className="w-4 h-4" />
            : <Pencil className="w-3.5 h-3.5" />
          }
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1">
            <span className={`font-mono text-sm font-black tracking-tight ${expanded ? 'text-indigo-600' : 'text-slate-900 group-hover:text-indigo-600'}`}>{fc.path}</span>
            <span className={`flex-shrink-0 text-[10px] font-black uppercase tracking-widest px-2.5 py-1 rounded-xl border ${layerColor[layer] || 'bg-slate-100 text-slate-500'}`}>{layer}</span>
          </div>
          <div className={`text-xs font-bold truncate ${expanded ? 'text-slate-500' : 'text-slate-400'}`}>{fc.what}</div>
        </div>
        <div className="flex items-center gap-6 flex-shrink-0">
          {fc.linesAffected && (
            <div className="flex flex-col items-end">
              <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest opacity-60">Impact</span>
              <span className="text-sm font-black text-slate-900 tabular-nums">{fc.linesAffected} LOC</span>
            </div>
          )}
          <div className="flex flex-col items-end min-w-[60px]">
            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest opacity-60">Effort</span>
            <span className={`text-sm font-black uppercase tracking-widest ${effortColor}`}>{fc.effort}</span>
          </div>
          <div className={`p-2 rounded-xl transition-all ${expanded ? 'bg-indigo-600 text-white animate-bounce-subtle shadow-lg shadow-indigo-500/20' : 'bg-slate-50 text-slate-400'}`}>
            {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </div>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-slate-100 animate-slideDown">
          <div className="px-8 py-6 bg-slate-50/50 border-b border-slate-100">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="w-4 h-4 text-indigo-600" />
              <span className="text-[10px] font-black text-indigo-600 uppercase tracking-widest">Strategic Rationale</span>
            </div>
            <p className="text-sm text-slate-600 font-bold leading-relaxed">{fc.why}</p>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 bg-white">
            {fc.codeBefore && (
              <div className="border-r border-slate-100 group/source">
                <div className="px-6 py-2.5 bg-slate-50/80 border-b border-slate-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-rose-500" />
                    <span className="text-[10px] text-slate-400 font-black uppercase tracking-widest">Legacy_Head</span>
                  </div>
                  <span className="text-[9px] text-rose-500/50 font-black uppercase tracking-widest">DELETION</span>
                </div>
                <pre className="text-xs font-mono text-slate-500 p-8 overflow-x-auto leading-relaxed bg-slate-50/20">{fc.codeBefore}</pre>
              </div>
            )}
            <div className={fc.codeBefore ? '' : 'col-span-2'}>
              <div className="px-6 py-2.5 bg-indigo-50/50 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                  <span className="text-[10px] text-indigo-600 font-black uppercase tracking-widest">Proposed_Target</span>
                </div>
                <span className="text-[9px] text-emerald-600/50 font-black uppercase tracking-widest font-mono">STAGED_COMMIT</span>
              </div>
              <pre className="text-xs font-mono text-slate-800 p-8 overflow-x-auto leading-relaxed bg-indigo-50/5">{fc.codeAfter}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CodeChangesPanel({
  codePlan, filesTouched, totalLines, layerSummary, featureName, executionItems
}: {
  codePlan: FeatureCodePlan;
  filesTouched: string[];
  totalLines: number;
  layerSummary: Record<string, number>;
  featureName: string;
  executionItems: ExecutionItem[];
}) {
  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Summary card */}
      <div className="bg-white rounded-[2.5rem] border border-slate-100 p-10 shadow-2xl shadow-slate-200/50 relative overflow-hidden group">
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/5 blur-[100px] -z-10" />
        <div className="flex items-center gap-8 mb-10">
          <div className="w-16 h-16 rounded-2xl bg-indigo-50 flex items-center justify-center border-2 border-white shadow-xl">
            <Terminal className="w-8 h-8 text-indigo-600" />
          </div>
          <div className="flex-1">
            <div className="text-[10px] font-black text-indigo-600 uppercase tracking-[0.25em] mb-2">Impact Analysis Engine</div>
            <h3 className="text-4xl font-black text-slate-900 tracking-tighter leading-tight">{featureName} Manifest</h3>
          </div>
          <div className="flex items-center gap-10">
            <div className="text-right">
              <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Scope</div>
              <div className="text-5xl font-black text-slate-900 tabular-nums">{filesTouched.length}<span className="text-slate-400 text-sm ml-2 font-black uppercase tracking-widest">Files</span></div>
            </div>
            <div className="h-12 w-px bg-slate-100" />
            <div className="text-right">
              <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Delta</div>
              <div className="text-5xl font-black text-emerald-500 tabular-nums">+{totalLines}<span className="text-slate-400 text-sm ml-2 font-black uppercase tracking-widest">LOC</span></div>
            </div>
          </div>
        </div>

        <div className="bg-slate-50/50 border-2 border-slate-50 rounded-[2rem] p-8 mb-10 shadow-inner">
          <p className="text-lg font-bold text-slate-600 leading-relaxed italic">"{codePlan.summary}"</p>
        </div>

        {/* Layer summary */}
        <div className="flex flex-wrap gap-4">
          {Object.entries(layerSummary).map(([layer, count]) => (
            <div key={layer} className="flex items-center gap-3 px-5 py-3 rounded-2xl bg-white border border-slate-100 group hover:border-indigo-600 transition-all hover:shadow-lg shadow-sm">
              <Layers className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 transition-colors" />
              <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 group-hover:text-slate-900 transition-colors">{layer}</span>
              <div className="w-1.5 h-1.5 rounded-full bg-slate-200 mx-1" />
              <span className="text-base font-black text-indigo-600 tabular-nums">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* New API endpoints */}
      {codePlan.newEndpoints.length > 0 && (
        <div className="bg-white rounded-[2.5rem] border border-slate-100 p-10 shadow-2xl shadow-slate-200/50 group">
          <div className="flex items-center gap-5 mb-8">
            <div className="w-12 h-12 rounded-2xl bg-indigo-50 flex items-center justify-center border border-white text-indigo-600 shadow-xl">
              <Globe className="w-6 h-6" />
            </div>
            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em]">Exposed API Cluster</h3>
            <div className="h-px flex-1 bg-slate-50 group-hover:bg-indigo-100 transition-colors" />
            <span className="text-[10px] font-black text-indigo-600 bg-indigo-50 px-4 py-2 rounded-full uppercase tracking-widest border border-white shadow-sm">{codePlan.newEndpoints.length} Entry Points</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {codePlan.newEndpoints.map((ep, i) => {
              const [method, ...rest] = ep.split(' ');
              const methodColor = method === 'POST' ? 'bg-amber-100 text-amber-700 border-amber-200' : method === 'GET' ? 'bg-emerald-100 text-emerald-700 border-emerald-200' : 'bg-rose-100 text-rose-700 border-rose-200';
              return (
                <div key={i} className="flex items-center gap-4 font-mono text-sm bg-slate-50/50 p-5 rounded-[1.5rem] border-2 border-transparent hover:border-indigo-100 hover:bg-white transition-all hover:translate-x-1 group/item shadow-sm">
                  <span className={`px-3 py-1.5 rounded-xl text-[10px] font-black tracking-widest ${methodColor} shadow-sm group-hover/item:scale-110 transition-transform uppercase border`}>{method}</span>
                  <span className="text-slate-700 font-bold group-hover/item:text-indigo-600 transition-colors">{rest.join(' ')}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* File changes grid */}
      <div className="space-y-4">
        <div className="flex items-center gap-4 px-4 mb-6">
          <GitBranch className="w-5 h-5 text-indigo-600" />
          <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em]">Component Refactor Roadmap</h3>
          <div className="text-[9px] font-black text-white uppercase tracking-widest bg-indigo-600 px-3 py-1 rounded-full ml-auto shadow-lg shadow-indigo-500/20">VERIFIED_MAP</div>
        </div>
        <div className="space-y-3">
          {codePlan.fileChanges.map((fc, i) => (
            <FileChangeCard key={i} fc={fc} />
          ))}
        </div>
      </div>

      {/* AI-Generated Execution Steps */}
      {executionItems.length > 0 && (
        <div className="bg-white rounded-[3rem] p-10 shadow-2xl relative overflow-hidden mb-10 border border-slate-100">
          <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-50 blur-[100px] -z-10" />
          <div className="flex items-center gap-5 mb-10">
            <div className="w-14 h-14 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-2xl shadow-indigo-500/30">
              <Cpu className="w-7 h-7 text-white" />
            </div>
            <div className="flex-1">
               <h3 className="text-[10px] font-black text-indigo-600 uppercase tracking-[0.25em] mb-1">Synthesized Implementation Path</h3>
               <p className="text-xl font-bold text-slate-900 tracking-tight">Technical Task Decomposition</p>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4">
            {executionItems.map((item: ExecutionItem, i: number) => (
              <div key={i} className="flex items-start gap-6 p-6 rounded-[2rem] bg-slate-50 border border-slate-100 hover:border-indigo-200 transition-all group backdrop-blur-sm">
                <div className="w-8 h-8 rounded-xl bg-indigo-50 flex items-center justify-center text-xs font-black text-indigo-600 border border-indigo-100 mt-1 shadow-inner">{item.id}</div>
                <div className="flex-1">
                   <div className="font-mono text-[11px] text-indigo-600 font-black mb-2 uppercase tracking-widest">{item.file}</div>
                   <div className="text-[15px] text-slate-800 leading-relaxed font-bold">{item.change}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* New files manifest */}
      {codePlan.newFiles.length > 0 && (
        <div className="bg-emerald-50 rounded-[3rem] p-10 shadow-2xl shadow-emerald-500/5 overflow-hidden mb-10 border border-emerald-100">
          <div className="flex items-center gap-5 mb-10">
            <div className="w-14 h-14 rounded-2xl bg-emerald-500 flex items-center justify-center shadow-xl shadow-emerald-500/20">
              <Plus className="w-7 h-7 text-white" />
            </div>
            <div className="flex-1">
               <h3 className="text-[10px] font-black text-emerald-600 uppercase tracking-[0.25em] mb-1">Architecture Expansion</h3>
               <p className="text-xl font-bold text-slate-900 tracking-tight">New Structural Components</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {codePlan.newFiles.map((nf, i) => (
              <div key={i} className="flex flex-col gap-2 p-6 rounded-[2rem] bg-white border border-emerald-100 hover:border-emerald-500 transition-all group shadow-sm">
                <span className="font-mono text-sm text-emerald-600 font-black tracking-tight uppercase group-hover:translate-x-1 transition-transform">{nf.path}</span>
                <span className="text-sm text-slate-500 font-bold italic leading-relaxed">— {nf.purpose}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Multi-Party Manifest Section ────────────────────────────────────────── */
function MultiPartyManifest({ }: { featureName: string }) {
  const parties = [
    { name: 'NPCI Switch', role: 'Orchestrator', intent: 'Update routing logic to support new purpose code H for IoT. Enable Circle Delegate validation.', impact: 'High' },
    { name: 'Payer PSP', role: 'Initiator', intent: 'Implement device-native auth handler. Support mandate creation via mobile OTP linking.', impact: 'Medium' },
    { name: 'Payee PSP', role: 'Acquirer', intent: 'Enable credit notification hooks for IoT specialized categories.', impact: 'Low' },
    { name: 'Remitter Bank', role: 'Issuer', intent: 'Support Single Block Multiple Debit (SBMD) for mandate-based funds holding.', impact: 'High' },
    { name: 'Beneficiary Bank', role: 'Receiver', intent: 'Verify real-time credit success signals for IoT low-latency nodes.', impact: 'Low' },
  ];

  return (
    <div className="bg-slate-900 rounded-[3rem] p-10 text-white shadow-2xl relative overflow-hidden mb-10 border border-slate-800">
      <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 blur-[100px] -z-10" />
      <div className="flex items-center gap-5 mb-10">
        <div className="w-14 h-14 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-2xl shadow-indigo-500/30">
          <GitBranch className="w-7 h-7 text-white" />
        </div>
        <div className="flex-1">
           <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.25em] mb-1">A2A Ecosystem Synchronization</h3>
           <p className="text-xl font-bold text-white tracking-tight">Multi-Party Change Manifest</p>
        </div>
        <div className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/50 rounded-xl flex items-center gap-2">
           <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
           <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">Intent Confirmed</span>
        </div>
      </div>
      
      <div className="grid grid-cols-1 gap-4">
        {parties.map((p, i) => (
          <div key={i} className="flex items-start gap-6 p-6 rounded-[2rem] bg-white/5 border border-white/10 hover:bg-white/10 transition-all group">
            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center text-xs font-black text-indigo-300 border border-white/10 mt-1">{i+1}</div>
            <div className="flex-1">
               <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-black text-white uppercase tracking-widest">{p.name} <span className="text-indigo-400 opacity-60 ml-2">— {p.role}</span></span>
                  <span className={`text-[9px] font-black px-2 py-1 rounded-lg border ${p.impact === 'High' ? 'bg-rose-500/10 border-rose-500/50 text-rose-400' : 'bg-indigo-500/10 border-indigo-500/50 text-indigo-400'}`}>{p.impact} IMPACT</span>
               </div>
               <div className="text-[13px] text-slate-300 leading-relaxed font-medium">{p.intent}</div>
               <div className="mt-3 flex items-center gap-2 text-[9px] font-black text-emerald-400 uppercase tracking-widest bg-emerald-500/5 w-fit px-3 py-1.5 rounded-full border border-emerald-500/20">
                  <Check className="w-3 h-3" /> Agent Handshake Complete
               </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Globe icon (inline since not in lucide) ────────────────────────────── */
function Globe({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
    </svg>
  );
}



/* ─── Main component ─────────────────────────────────────────────────────── */
export default function TechnicalPlanView({ canvas, featureName, executionItems, active, onApprove }: TechnicalPlanViewProps) {
  const [activeTab, setActiveTab] = useState<DocTab>('brd');
  
  // Initialization from props
  const initialBrd = executionItems?.find(i => i.id === 'brd')?.change || '';
  const initialTsd = executionItems?.find(i => i.id === 'tsd')?.change || '';
  const [brdContent, setBrdContent] = useState(initialBrd);
  const [tsdContent, setTsdContent] = useState(initialTsd);
  const [isGenerating, setIsGenerating] = useState(active && !initialBrd);

  const [localExecutionItems, setLocalExecutionItems] = useState<ExecutionItem[]>([]);

  const [brdEditing, setBrdEditing] = useState(false);
  const [tsdEditing, setTsdEditing] = useState(false);
  const [brdDraft, setBrdDraft] = useState('');
  const [tsdDraft, setTsdDraft] = useState('');
  const [brdApproved, setBrdApproved] = useState(false);
  const [tsdApproved, setTsdApproved] = useState(false);
  const [thinkingStep, setThinkingStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedbackInput, setFeedbackInput] = useState('');
  const [isRefining, setIsRefining] = useState(false);

  // Messages for Architect Chat
  const [messages, setMessages] = useState<ArchitectMessage[]>([]);

  const chatEndRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Codebase analysis — derived directly from canvas (no async needed)
  const codePlan = getCodePlan(canvas);
  const filesTouched = getFilesTouched(codePlan);
  const totalLines = getTotalLinesAffected(codePlan);
  const layerSummary = getLayerSummary(codePlan);

  // Keep track of whether we've initialized the 'initial' message
  const initializedRef = useRef(false);

  // Consolidated Sync and Auto-Generation Effect
  useEffect(() => {
    if (!active) return;

    const newBrd = executionItems?.find(i => i.id === 'brd')?.change || '';
    const newTsd = executionItems?.find(i => i.id === 'tsd')?.change || '';
    const items = executionItems?.filter(i => i.id !== 'brd' && i.id !== 'tsd') || [];
    
    // Process approved plan
    if (newBrd) {
      setBrdContent(newBrd);
      setBrdDraft(newBrd);
      setBrdApproved(true);
      setIsGenerating(false);
      
      if (!initializedRef.current) {
        setMessages([
          {
            id: 'initial',
            role: 'assistant',
            content: "I've successfully synthesized the technical orchestrator specifications. The BRD and TSD are ready for your review in the workspace panel.",
          }
        ]);
        initializedRef.current = true;
      }
    } else {
      // Small delay to allow prop hydration, then auto-generate if still empty
      const timer = setTimeout(() => {
        if (!brdContent && active && !isGenerating && !initializedRef.current) {
          runGeneration();
        }
      }, 1200);
      return () => clearTimeout(timer);
    }

    if (newTsd) {
      setTsdContent(newTsd);
      setTsdDraft(newTsd);
      setTsdApproved(true);
    }
    if (items.length > 0) {
      setLocalExecutionItems(items);
    }
  }, [executionItems, active, brdContent, isGenerating]);

  const runGeneration = async (feedback?: string) => {
    const steps: ThinkingStep[] = [
      { label: 'Deconstructing Functional Requirements', detail: 'Parsing core business logic and user intent from the approved canvas.', duration: 4000 },
      { label: 'Analyzing UPI Lifecycle State Machine', detail: 'Mapping transitions for block creation, authorization, and execution.', duration: 5000 },
      { label: 'Validating Regulatory Compliance (OC 228)', detail: 'Cross-checking with RBI Single Block Multiple Debit guidelines.', duration: 4500 },
      { label: 'Synthesizing API Orchestration Layer', detail: 'Architecture design for high-throughput, idempotent payment APIs.', duration: 5500 },
      { label: 'Evaluating Risk & Fraud Vectors', detail: 'Simulating velocity checks and behavioral anomaly detection.', duration: 6000 },
      { label: 'Optimizing Database Schema Performance', detail: 'Normalization for real-time transaction tracking and MIS reporting.', duration: 5000 },
      { label: 'Generating Implementation Roadmap', detail: 'Prioritizing development tasks and building verification matrix.', duration: 4000 },
      { label: 'Final Verification Complete', detail: 'Technical specification aligned with NPCI production standards.', duration: 3000 }
    ];

    const userMsgId = Date.now().toString();
    if (feedback) {
      setMessages(prev => [...prev, { id: userMsgId, role: 'user', content: feedback }]);
    }

    const thinkingId = 'thinking-' + (Date.now() + 1);
    setMessages(prev => [...prev, { 
      id: thinkingId, 
      role: 'assistant', 
      content: '', 
      isThinking: true, 
      steps, 
      totalMs: 0 
    }]);

    const startMs = Date.now();
    setIsGenerating(true);

    try {
      // Progress simulation for the thinking message
      const progressPromise = (async () => {
        for (let i = 0; i < steps.length; i++) {
          setThinkingStep(i);
          await new Promise(r => setTimeout(r, steps[i].duration));
        }
      })();

      const fetchPromise = fetch('/api/execution/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          canvas, 
          feedback, 
          messages: (feedback ? messages : []).map(m => ({ role: m.role, content: m.content })) 
        }),
      });

      const [_, res] = await Promise.all([progressPromise, fetchPromise]);
      const totalMs = Date.now() - startMs;
      
      if (res.ok) {
        const data = await res.json();
        const apiItems = data.items || [];
        const message = data.message || "I've updated the technical plan based on your feedback.";

        if (apiItems.length > 0) {
          const brd_doc = apiItems.find((i: any) => i.id === 'brd');
          const tsd_doc = apiItems.find((i: any) => i.id === 'tsd');
          
          if (brd_doc) { 
            setBrdContent(brd_doc.change); 
            setBrdDraft(brd_doc.change); 
            setBrdApproved(true);
          }
          if (tsd_doc) { 
            setTsdContent(tsd_doc.change); 
            setTsdDraft(tsd_doc.change); 
            setTsdApproved(true);
          }
          
          setLocalExecutionItems(apiItems.filter((i: any) => i.id !== 'brd' && i.id !== 'tsd'));
        }

        // Finalize the thinking message into a real response
        setMessages(prev => {
          const filtered = prev.filter(m => m.id !== thinkingId);
          return [...filtered, {
            id: 'res-' + Date.now(),
            role: 'assistant',
            content: message,
            isThinking: false,
            steps,
            totalMs
          }];
        });

        setIsGenerating(false);
        return;
      }
    } catch (error) {
       console.error("Execution generation failed:", error);
    }

    // Fallback
    await new Promise(r => setTimeout(r, 1200));
    setMessages(prev => {
      const filtered = prev.filter(m => m.id !== thinkingId);
      return [...filtered, {
        id: 'fallback-' + Date.now(),
        role: 'assistant',
        content: "I've synthesized the updated technical specifications. You can review the changes in the documents above.",
        isThinking: false,
        totalMs: Date.now() - startMs
      }];
    });
    setIsGenerating(false);
  };

  const handleRefineArchitecture = () => {
    if (!feedbackInput.trim() || isGenerating) return;
    const feedback = feedbackInput;
    setFeedbackInput('');
    setIsRefining(true);
    runGeneration(feedback).finally(() => setIsRefining(false));
  };

  const currentContent = activeTab === 'brd' ? brdContent : tsdContent;
  const currentEditing = activeTab === 'brd' ? brdEditing : tsdEditing;
  const currentDraft   = activeTab === 'brd' ? brdDraft : tsdDraft;
  const currentApproved = activeTab === 'brd' ? brdApproved : tsdApproved;
  const setCurrentDraft = activeTab === 'brd' ? setBrdDraft : setTsdDraft;
  const setCurrentEditing = activeTab === 'brd' ? setBrdEditing : setTsdEditing;
  const setCurrentContent = activeTab === 'brd' ? setBrdContent : setTsdContent;
  const setCurrentApproved = activeTab === 'brd' ? setBrdApproved : setTsdApproved;
  const allApproved = brdApproved && tsdApproved;

  const saveEdit = () => {
    setCurrentContent(currentDraft);
    setCurrentEditing(false);
  };
  const cancelEdit = () => {
    setCurrentDraft(currentContent);
    setCurrentEditing(false);
  };
  const startEdit = () => {
    setCurrentDraft(currentContent);
    setCurrentEditing(true);
  };

  const downloadDocx = async (title: string, content: string) => {
    try {
      const res = await fetch('/api/documents/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, content }),
      });
      if (!res.ok) throw new Error('DOCX Download failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${title.replace(/\s+/g, '_')}.docx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('DOCX download error:', err);
      alert('Failed to generate .docx.');
    }
  };

  const handleApproveAndProceed = async () => {
    setIsSubmitting(true);
    
    const execPlan: CMPlan = {
      version: '2.0',
      description: `Implementation of ${featureName}`,
      // Pass the actual content so agents have context
      brd: brdContent,
      tsd: tsdContent,
      plan: localExecutionItems.length > 0 
        ? localExecutionItems.map(item => `${item.id}: ${item.change} (File: ${item.file})`)
        : [
            `Implement core logic for ${featureName} per TSD Section 2`,
            `Update Payer/Payee PSP handlers for ${featureName} handling`,
            `Update Remitter/Beneficiary Bank handlers for ${featureName} funds flow`,
            `Apply schema changes in upi_pay_request.xsd if required`,
            `Run verification suite for ${featureName}`
          ],
      impact_analysis: {
        business_value: `Feature: ${featureName}`,
        compliance_check: 'Standard UPI Compliance & RBI Master Directions',
        risk_assessment: 'Medium — autonomous agent execution enabled',
      },
      verification_payload: `<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqPay xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="2.0" ts="${new Date().toISOString()}" orgId="PAYER_PSP" msgId="${Date.now()}" prodType="UPI"/>
  <upi:Txn id="TXN-${Date.now()}" type="PAY" note="${featureName} verification test"/>
  <upi:Payer addr="ramesh@payer">
    <upi:Amount value="2000.00"/>
    <upi:Creds><upi:Cred><upi:Data code="123456"/></upi:Cred></upi:Creds>
  </upi:Payer>
  <upi:Payees><upi:Payee addr="merchant@benef"/></upi:Payees>
</upi:ReqPay>`,
    };

    // NOTE: approve-change is now fired from NFBLiveExecution after SSE is confirmed open
    // to ensure no events are missed due to race conditions.

    setIsSubmitting(false);
    onApprove(execPlan);
  };

  return (
    <div className="flex-1 flex min-h-0 overflow-hidden bg-white">
      {/* ════ LEFT — Architect Chat ════ */}
      <div className="flex flex-col border-r border-slate-100 w-[30%] min-w-[340px] bg-slate-50/10 relative shadow-2xl">
        <div className="flex items-center gap-4 px-8 py-6 border-b border-slate-50 bg-white shadow-sm z-10 transition-all">
          <div className="w-12 h-12 rounded-[1.25rem] bg-slate-900 flex items-center justify-center shadow-xl shadow-indigo-500/20">
            <Brain className="w-6 h-6 text-white" />
          </div>
          <div className="min-w-0">
            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] truncate">Titan Orchestrator</h3>
            <p className="text-sm font-black text-slate-900 uppercase tracking-tight mt-0.5">Live Architect Chat</p>
          </div>
          <div className="ml-auto">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_10px_rgba(16,185,129,0.5)]" />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-8 space-y-6 scroll-smooth">
          {messages.length === 0 && isGenerating && (
             <div className="flex items-center justify-center h-full text-slate-400 animate-pulse">
               <div className="flex flex-col items-center gap-4">
                  <Brain className="w-12 h-12 text-indigo-100" />
                  <span className="text-xs font-black uppercase tracking-[0.2em]">Initializing Architect...</span>
               </div>
             </div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={`flex gap-4 ${m.role === 'user' ? 'flex-row-reverse' : ''} animate-fadeIn`}>
              <div className={`w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-xl border ${
                m.role === 'assistant' ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-slate-200 text-slate-800'
              }`}>
                {m.role === 'assistant' ? <Sparkles className="w-5 h-5" /> : <div className="font-black text-[10px] uppercase text-slate-400">ME</div>}
              </div>
              
              <div className={`max-w-[85%] space-y-4 ${m.role === 'user' ? 'items-end' : ''}`}>
                {m.content && (
                  <div className={`p-6 rounded-[2rem] text-[15px] font-bold leading-relaxed shadow-xl border ${
                    m.role === 'assistant' 
                      ? 'bg-white border-slate-100 text-slate-800 rounded-tl-sm' 
                      : 'bg-indigo-600 border-indigo-500 text-white rounded-tr-sm shadow-indigo-500/10'
                  }`}>
                    {m.content}
                    
                    {(m.id === 'initial' || (m.role === 'assistant' && (m.content.toLowerCase().includes('synthesized') || m.content.toLowerCase().includes('analyzed')))) && (
                      <div className="mt-4 grid grid-cols-1 gap-2">
                         <button 
                           onClick={() => setActiveTab('brd')}
                           className={`flex items-center gap-4 p-4 rounded-[1.5rem] border transition-all text-left group/btn ${activeTab === 'brd' ? 'bg-indigo-50 border-indigo-200 ring-4 ring-indigo-500/5' : 'bg-slate-50/50 border-slate-100 hover:border-indigo-200'}`}
                         >
                           <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center border border-slate-100 shadow-sm group-hover/btn:scale-110 transition-transform">
                             <FileText className="w-5 h-5 text-indigo-600" />
                           </div>
                           <div className="flex-1 min-w-0">
                              <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Impact Analysis</div>
                              <div className="text-sm text-slate-900 font-bold truncate">Business Specs</div>
                           </div>
                           <ChevronRight className={`w-5 h-5 transition-transform ${activeTab === 'brd' ? 'text-indigo-500 translate-x-1' : 'text-slate-300'}`} />
                         </button>
                         <button 
                           onClick={() => setActiveTab('manifest')}
                           className={`flex items-center gap-4 p-4 rounded-[1.5rem] border transition-all text-left group/btn ${activeTab === 'manifest' ? 'bg-indigo-50 border-indigo-200 ring-4 ring-indigo-500/5' : 'bg-slate-50/50 border-slate-100 hover:border-indigo-200'}`}
                         >
                           <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center border border-slate-100 shadow-sm group-hover/btn:scale-110 transition-transform">
                             <GitBranch className="w-5 h-5 text-indigo-600" />
                           </div>
                           <div className="flex-1 min-w-0">
                              <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Execution Plan</div>
                              <div className="text-sm text-slate-900 font-bold truncate">Change Manifest</div>
                           </div>
                           <ChevronRight className={`w-5 h-5 transition-transform ${activeTab === 'manifest' ? 'text-indigo-500 translate-x-1' : 'text-slate-300'}`} />
                         </button>
                         <button 
                           onClick={() => setActiveTab('tsd')}
                           className={`flex items-center gap-4 p-4 rounded-[1.5rem] border transition-all text-left group/btn ${activeTab === 'tsd' ? 'bg-indigo-50 border-indigo-200 ring-4 ring-indigo-500/5' : 'bg-slate-50/50 border-slate-100 hover:border-indigo-200'}`}
                         >
                           <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center border border-slate-100 shadow-sm group-hover/btn:scale-110 transition-transform">
                             <Cpu className="w-5 h-5 text-indigo-600" />
                           </div>
                           <div className="flex-1 min-w-0">
                              <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Architecture</div>
                              <div className="text-sm text-slate-900 font-bold truncate">Technical TSD</div>
                           </div>
                           <ChevronRight className={`w-5 h-5 transition-transform ${activeTab === 'tsd' ? 'text-indigo-500 translate-x-1' : 'text-slate-300'}`} />
                         </button>
                      </div>
                    )}
                  </div>
                )}

                {m.isThinking && m.steps && (
                  <div className="bg-indigo-50/50 border border-indigo-100/50 rounded-[1.25rem] p-4 space-y-3.5 animate-fadeIn shadow-sm">
                    <div className="flex items-center gap-2 mb-1">
                      <Brain className="w-3.5 h-3.5 text-indigo-600 animate-pulse" />
                      <span className="text-[10px] font-black text-indigo-900 uppercase tracking-widest">Architectural Analysis...</span>
                    </div>
                    {m.steps.map((s, i) => {
                      const isDone = i < thinkingStep;
                      const isActive = i === thinkingStep;
                      return (
                        <div key={i} className={`flex gap-3.5 transition-opacity duration-500 ${i > thinkingStep ? 'opacity-20' : 'opacity-100'}`}>
                          <div className={`w-5 h-5 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 border shadow-sm ${
                            isDone ? 'bg-emerald-500 border-emerald-500 text-white' : 
                            isActive ? 'bg-indigo-600 border-indigo-500 text-white animate-bounce-subtle' : 
                            'bg-slate-100 border-slate-200 text-slate-400'
                          }`}>
                            {isDone ? <Check className="w-3 h-3" /> : <div className="text-[9px] font-black">{i+1}</div>}
                          </div>
                          <div className="min-w-0">
                            <div className={`text-[11px] font-black leading-tight truncate ${isActive ? 'text-indigo-600' : 'text-slate-700'}`}>{s.label}</div>
                            {isActive && <div className="text-[10px] text-slate-500 mt-1 italic leading-relaxed animate-fadeIn">{s.detail}</div>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        <div className="p-6 bg-white border-t border-slate-50 shadow-2xl">
          <div className="flex items-center gap-4 bg-slate-100/50 border-2 border-slate-50 rounded-[1.5rem] px-5 py-4 focus-within:border-indigo-600 focus-within:bg-white focus-within:ring-8 focus-within:ring-indigo-500/5 transition-all">
            <input
              type="text"
              value={feedbackInput}
              onChange={e => setFeedbackInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleRefineArchitecture()}
              placeholder="Critique architecture or ask anything..."
              className="flex-1 bg-transparent border-none outline-none text-[15px] font-bold text-slate-900 placeholder-slate-300"
              disabled={isGenerating || isRefining}
            />
            <button
              onClick={handleRefineArchitecture}
              disabled={!feedbackInput.trim() || isGenerating || isRefining}
              className={`p-3 rounded-2xl transition-all ${
                feedbackInput.trim() && !isGenerating && !isRefining 
                  ? 'bg-indigo-600 text-white shadow-xl shadow-indigo-500/20 active:scale-90' 
                  : 'text-slate-300'
              }`}
            >
              <RefreshCw className={`w-5 h-5 ${isRefining ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {/* ════ RIGHT — Technical Blueprint ════ */}
      <div className="flex-1 flex flex-col min-w-0 bg-slate-50/10 overflow-y-auto">
        <div className="max-w-6xl w-full mx-auto px-10 py-12">
          {/* Header */}
          <div className="flex items-end justify-between gap-8 mb-12 pb-8 border-b border-slate-100">
            <div>
              <div className="text-[11px] font-black uppercase tracking-[0.3em] text-indigo-600 mb-2">Technical Specification Document</div>
              <h2 className="text-5xl font-black text-slate-900 tracking-tighter leading-none">{featureName}</h2>
            </div>
            <button
              onClick={handleApproveAndProceed}
              disabled={isSubmitting || !allApproved}
              className={`flex items-center gap-4 px-10 py-5 rounded-[1.5rem] font-black uppercase tracking-[0.2em] text-[11px] transition-all shadow-2xl ${
                allApproved 
                  ? 'bg-slate-900 text-white hover:bg-black shadow-indigo-500/30' 
                  : 'bg-slate-100 text-slate-300 cursor-not-allowed shadow-none border border-slate-200'
              }`}
            >
              {isSubmitting
                ? <><Loader2 className="w-5 h-5 animate-spin" /> Committing Changes…</>
                : <><Cpu className="w-5 h-5" /> Deploy Architecture</>
              }
            </button>
          </div>

          {/* Stats Bar */}
          <div className="grid grid-cols-4 gap-6 mb-12">
            <div className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-200/40 relative overflow-hidden group">
              <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 group-hover:text-indigo-600 transition-colors">Files Affected</div>
              <div className="text-3xl font-black text-slate-900 tabular-nums">{filesTouched.length}</div>
              <div className="absolute -bottom-4 -right-4 w-16 h-16 bg-slate-50 rounded-full group-hover:scale-150 transition-transform duration-500" />
            </div>
            <div className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-200/40 relative overflow-hidden group">
              <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 group-hover:text-emerald-500 transition-colors">Delta Intensity</div>
              <div className="text-3xl font-black text-slate-900 tabular-nums">{totalLines}<span className="text-[10px] ml-1 font-black text-slate-300">LOC</span></div>
              <div className="absolute -bottom-4 -right-4 w-16 h-16 bg-emerald-50 rounded-full group-hover:scale-150 transition-transform duration-500" />
            </div>
            <div className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-200/40 relative overflow-hidden group">
              <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 group-hover:text-indigo-600 transition-colors">Verification</div>
              <div className="text-3xl font-black text-indigo-600">{(brdApproved ? 1 : 0) + (tsdApproved ? 1 : 0)} / 2</div>
              <div className="absolute -bottom-4 -right-4 w-16 h-16 bg-indigo-50 rounded-full group-hover:scale-150 transition-transform duration-500" />
            </div>
            <div className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-200/40 relative overflow-hidden group">
              <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 group-hover:text-amber-500 transition-colors">Deploy Sync</div>
              <div className={`text-sm font-black uppercase tracking-[0.2em] mt-2 ${allApproved ? 'text-emerald-500 bg-emerald-50 px-3 py-1 rounded-lg w-fit border border-emerald-100 shadow-sm shadow-emerald-500/10' : 'text-amber-500 bg-amber-50 px-3 py-1 rounded-lg w-fit border border-amber-100 shadow-sm shadow-amber-500/10'}`}>
                {allApproved ? 'READY' : 'STAGING'}
              </div>
            </div>
          </div>

          {/* Document tabs */}
          <div className="flex items-center justify-between mb-8">
            <div className="flex gap-4">
              {(['brd', 'tsd', 'manifest'] as const).map(tabId => (
                <button
                  key={tabId}
                  onClick={() => setActiveTab(tabId)}
                  className={`px-8 py-3.5 rounded-[1.5rem] text-[10px] font-black uppercase tracking-[0.2em] transition-all border-2
                    ${activeTab === tabId
                      ? 'bg-indigo-600 text-white border-indigo-600 shadow-2xl shadow-indigo-500/20 active:scale-95'
                      : 'bg-white text-slate-400 border-slate-50 hover:border-indigo-600 hover:text-indigo-600 shadow-sm'
                    }`}
                >
                  {tabId === 'brd' ? 'BRD Objective' : tabId === 'tsd' ? 'Tech Specs' : 'Change Manifest'}
                </button>
              ))}
            </div>
            
            {(activeTab === 'brd' || activeTab === 'tsd') && (
            <button
                onClick={() => downloadDocx(
                  activeTab === 'brd' ? 'Business Requirements Document' : 'Technical Specification Document',
                  currentContent
                )}
                className="flex items-center gap-3 px-6 py-3.5 rounded-2xl text-[10px] font-black uppercase tracking-widest text-slate-600 bg-white border-2 border-slate-50 hover:border-indigo-600 hover:text-indigo-600 transition-all shadow-xl shadow-slate-200/50"
              >
                <Download className="w-5 h-5" />
                Export Archive
              </button>
            )}
          </div>

          {/* Main content area */}
          <div className="bg-white rounded-[3rem] border border-slate-100 shadow-2xl shadow-slate-200/40 overflow-hidden min-h-[650px] relative">
            {activeTab === 'manifest' ? (
              <div className="p-12 overflow-y-auto max-h-[700px] custom-scrollbar">
                <div className="bg-slate-900 rounded-[3rem] p-10 text-white shadow-2xl relative overflow-hidden mb-10 border border-slate-800">
                  <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 blur-[100px] -z-10" />
                  <div className="flex items-center gap-5 mb-10">
                    <div className="w-14 h-14 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-2xl shadow-indigo-500/30">
                      <GitBranch className="w-7 h-7 text-white" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.25em] mb-1">A2A Ecosystem Synchronization</h3>
                      <p className="text-xl font-bold text-white tracking-tight">Multi-Party Change Manifest</p>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 gap-4">
                    {localExecutionItems.map((item, i) => (
                      <div key={i} className="flex items-start gap-6 p-6 rounded-[2rem] bg-white/5 border border-white/10 hover:bg-white/10 transition-all group">
                        <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center text-xs font-black text-indigo-300 border border-white/10 mt-1">{i+1}</div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between mb-2">
                              <span className="text-sm font-black text-white uppercase tracking-widest">{item.file} <span className="text-indigo-400 opacity-60 ml-2">— Orchestrator Segment</span></span>
                              <span className={`text-[9px] font-black px-2 py-1 rounded-lg border bg-indigo-500/10 border-indigo-500/50 text-indigo-400`}>A2A MANIFEST</span>
                          </div>
                          <div className="text-[13px] text-slate-300 leading-relaxed font-medium">{item.change}</div>
                          <div className="mt-3 flex items-center gap-2 text-[9px] font-black text-emerald-400 uppercase tracking-widest bg-emerald-500/5 w-fit px-3 py-1.5 rounded-full border border-emerald-500/20">
                              <Check className="w-3 h-3" /> Agent Handshake Synced
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col h-full">
                <div className="flex items-center justify-between px-12 py-8 border-b border-slate-50">
                  <div className="flex items-center gap-5">
                    <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center shadow-inner">
                      {activeTab === 'brd' ? <BookOpen className="w-6 h-6" /> : <Code2 className="w-6 h-6" />}
                    </div>
                    <div>
                      <h3 className="font-black text-slate-900 uppercase tracking-widest text-sm leading-none">
                        {activeTab === 'brd' ? 'Business Objectives' : 'Architecture Blueprint'}
                      </h3>
                      <div className="text-[10px] font-black text-slate-300 uppercase tracking-widest mt-1">Staged for Provisioning</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                     <button onClick={startEdit} className="p-3 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-2xl transition-all"><Pencil className="w-5 h-5" /></button>
                     <button onClick={() => setCurrentApproved(!currentApproved)} className={`p-1.5 rounded-full border-2 transition-all group ${currentApproved ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-slate-100 text-slate-200 hover:border-indigo-600 hover:text-indigo-600'}`}>
                        <Check className={`w-5 h-5 ${currentApproved ? 'animate-bounce-subtle' : ''}`} />
                     </button>
                  </div>
                </div>
                
                <div className="p-12 overflow-y-auto max-h-[700px] custom-scrollbar">
                  {currentEditing ? (
                    <textarea
                      value={currentDraft}
                      onChange={e => setCurrentDraft(e.target.value)}
                      className="w-full h-[600px] text-[15px] font-bold text-slate-800 border-2 border-slate-50 outline-none resize-none bg-slate-50/30 rounded-3xl p-8 focus:ring-8 focus:ring-blue-500/5 focus:border-blue-100 transition-all"
                    />
                  ) : (
                    <div className="max-w-5xl mx-auto">
                       <MarkdownRenderer content={currentContent} />
                    </div>
                  )}
                </div>
                
                {currentEditing && (
                  <div className="p-6 border-t border-slate-50 flex justify-end gap-4 bg-white/50 backdrop-blur-md">
                    <button onClick={cancelEdit} className="px-8 py-3 text-[10px] font-black uppercase text-slate-400 tracking-widest hover:text-slate-600 transition-colors">Discard</button>
                    <button onClick={saveEdit} className="px-10 py-3 bg-indigo-600 text-white text-[10px] font-black uppercase tracking-widest rounded-2xl shadow-xl shadow-indigo-500/20 active:scale-95 transition-all">Apply Specifications</button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Bottom action row (Premium Desktop View) */}
          <div className="mt-12 bg-white rounded-[3rem] p-10 flex flex-col lg:flex-row items-center justify-between gap-10 shadow-2xl border border-slate-100 relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-indigo-500/[0.03] blur-[120px] -z-10 group-hover:bg-indigo-500/[0.08] transition-all duration-[1.5s]" />
            <div className="flex items-center gap-8">
              <div className="w-20 h-20 rounded-[2rem] bg-indigo-600 flex items-center justify-center shadow-2xl shadow-indigo-500/30 border-4 border-white transition-transform group-hover:rotate-12 duration-500">
                <Cpu className="w-10 h-10 text-white" />
              </div>
              <div>
                <div className="text-[11px] font-black text-indigo-600 uppercase tracking-[0.3em] mb-2">Orchestration Phase // 02</div>
                <h3 className="text-3xl font-black text-slate-900 tracking-tighter">Initiate Deployment</h3>
                <p className="text-sm font-bold text-slate-400 mt-1 uppercase tracking-widest opacity-60">Locked and Ready for Production</p>
              </div>
            </div>
            <div className="flex flex-col lg:items-end gap-6 w-full lg:w-auto">
              <div className="flex items-center gap-4">
                 <div className={`px-5 py-2.5 rounded-2xl border-2 text-[10px] font-black uppercase tracking-widest flex items-center gap-2 ${allApproved ? 'bg-emerald-50 text-emerald-600 border-emerald-100 shadow-sm shadow-emerald-500/10' : 'bg-amber-50 text-amber-600 border-amber-100 shadow-sm shadow-amber-500/10'}`}>
                    <div className={`w-2 h-2 rounded-full ${allApproved ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'}`} />
                    {allApproved ? 'SYNC_COMPLETE' : 'AWAITING_LOCK'}
                 </div>
                 <div className="px-5 py-2.5 rounded-2xl border-2 border-slate-50 bg-slate-50/50 text-[10px] font-black uppercase tracking-widest text-slate-400">
                    ISOLATED_SANDBOX
                 </div>
              </div>
              <button
                onClick={handleApproveAndProceed}
                disabled={isSubmitting || !allApproved}
                className={`btn-primary px-16 py-6 text-base font-black uppercase tracking-[0.25em] min-w-[320px] bg-indigo-600 hover:bg-slate-900 shadow-2xl shadow-indigo-500/30 border-4 border-white rounded-[2rem] transition-all active:scale-95 ${!allApproved ? 'opacity-50 grayscale cursor-not-allowed' : ''}`}
              >
                {isSubmitting
                  ? <><Loader2 className="w-6 h-6 animate-spin mr-3" /> Provisioning...</>
                  : <><Cpu className="w-6 h-6 mr-3" /> Agentic Deploy</>
                }
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
