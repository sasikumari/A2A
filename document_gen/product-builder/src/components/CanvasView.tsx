import { useState } from 'react';
import {
  Edit3, Check, X, CheckCircle, Download,
  ThumbsUp, Shield, Zap, TrendingUp, Users,
  BarChart2, FlaskConical, Settings, Megaphone,
  DollarSign, AlertTriangle, ShieldCheck, Info,
  XCircle, RefreshCw, ArrowRight
} from 'lucide-react';
import type { CanvasData, CanvasSection, CanvasStatus } from '../types';

interface CanvasViewProps {
  canvas: CanvasData;
  onUpdate: (canvas: CanvasData) => void;
  onApprove: () => void;
}

async function downloadCanvasAsDocx(canvas: CanvasData) {
  try {
    const fullContent = canvas.sections
      .map(s => `## ${s.title}\n\n${s.content}`)
      .join('\n\n---\n\n');
      
    const res = await fetch('/api/documents/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        title: `Product Build Canvas - ${canvas.buildTitle}`, 
        content: fullContent 
      }),
    });
    if (!res.ok) throw new Error('Download failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Canvas_${canvas.buildTitle.replace(/\s+/g, '_')}.docx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error('Canvas download error:', err);
    alert('Failed to generate .docx for canvas.');
  }
}

/* ── Status ─────────────────────────────────── */
const STATUS: Record<CanvasStatus, { label: string; dot: string; bg: string; text: string; border: string; desc: string }> = {
  'on-track': { label: 'Syncing',    dot: 'bg-emerald-500', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-100', desc: 'Compliant with RBI'  },
  'open':     { label: 'Idle',       dot: 'bg-slate-400',   bg: 'bg-slate-50',     text: 'text-slate-500',   border: 'border-slate-200',   desc: 'Awaiting analysis' },
  'ongoing':  { label: 'Thinking',   dot: 'bg-indigo-500',  bg: 'bg-indigo-50',    text: 'text-indigo-700',  border: 'border-indigo-100',  desc: 'Agent in loop' },
  'approved': { label: 'Verified',   dot: 'bg-indigo-600',  bg: 'bg-indigo-600 shadow-[0_0_10px_rgba(79,70,229,0.4)]',   text: 'text-white',       border: 'border-indigo-600',  desc: 'Locked' },
};

/* ── Section metadata ───────────────────────── */
const META = [
  { id: 1,  icon: Zap,            color: 'text-indigo-600',  accent: 'bg-indigo-50', title: 'Feature',           subPrompts: ['Explain the feature for a layman', 'User journey & experience'] },
  { id: 2,  icon: TrendingUp,     color: 'text-slate-600', accent: 'bg-slate-50', title: 'Need',              subPrompts: ['Why should we do this?', 'Differentiation (incremental or exponential)', 'What if we don\'t build this?'] },
  { id: 3,  icon: Users,          color: 'text-violet-600', accent: 'bg-violet-50', title: 'Market View',       subPrompts: ['Ecosystem anticipated response', 'Ecosystem costs', 'Regulatory view'] },
  { id: 4,  icon: BarChart2,      color: 'text-indigo-600',  accent: 'bg-indigo-50', title: 'Scalability',       subPrompts: ['Market anchors (demand & supply)', 'Delta in user experience', 'Impact opportunity'] },
  { id: 5,  icon: FlaskConical,   color: 'text-cyan-600',  accent: 'bg-cyan-50', title: 'Validation',        subPrompts: ['Creating & operating MVP', 'Data insights generated', 'Impact on SGF / FRM'] },
  { id: 6,  icon: Settings,       color: 'text-emerald-600',accent: 'bg-emerald-50',title: 'Product Operating', subPrompts: ['3 Success KPIs', 'Grievance redressal (Trust)', 'Day 0 automation'] },
  { id: 7,  icon: Megaphone,      color: 'text-amber-600', accent: 'bg-amber-50',title: 'Product Comms',     subPrompts: ['Product demo & video', 'Explanation video by PM', 'FAQs + trained LLM', 'Circular + Product doc'] },
  { id: 8,  icon: DollarSign,     color: 'text-orange-600', accent: 'bg-orange-50',title: 'Pricing',           subPrompts: ['3-year pricing & revenue view', 'Market ability to pay', 'Market view to pay'] },
  { id: 9,  icon: AlertTriangle,  color: 'text-rose-600',   accent: 'bg-rose-50', title: 'Potential Risks',   subPrompts: ['Fraud & infosec risk', 'Legal & data privacy risk', '2nd order negative effects'] },
  { id: 10, icon: ShieldCheck,    color: 'text-pink-600',   accent: 'bg-pink-50', title: 'Compliance',        subPrompts: ['Guideline changes', 'Must-have compliances in NPCI circular'] },
];

/* ── Helpers ─────────────────────────────────── */
function StatusDot({ status }: { status: CanvasStatus }) {
  return <span className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS[status].dot}`} />;
}

function StatusBadge({ status }: { status: CanvasStatus }) {
  const s = STATUS[status];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border ${s.bg} ${s.text} ${s.border}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}

/* ── Canvas Content Renderer (clean document style) ─────────────────────── */

// Render inline bold (**text**) and keep everything else plain
function InlineText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((p, i) =>
        p.startsWith('**') && p.endsWith('**')
          ? <strong key={i} className="font-bold text-slate-900">{p.slice(2, -2)}</strong>
          : <span key={i} className="font-medium text-slate-600">{p}</span>
      )}
    </>
  );
}

type Block =
  | { kind: 'h1'; text: string }
  | { kind: 'h2'; text: string }
  | { kind: 'bullet'; text: string; depth: number }
  | { kind: 'numbered'; n: number; text: string }
  | { kind: 'kv'; key: string; value: string }
  | { kind: 'para'; text: string }
  | { kind: 'space' };

function parseContent(raw: string): Block[] {
  const lines = raw.split('\n');
  const blocks: Block[] = [];

  for (const line of lines) {
    const trimmed = line.trim();

    if (!trimmed) {
      if (blocks.length > 0 && blocks[blocks.length - 1].kind !== 'space')
        blocks.push({ kind: 'space' });
      continue;
    }

    // ALL-CAPS heading (e.g. "WHY SHOULD WE DO THIS?", "DIFFERENTIATION")
    if (/^[A-Z][A-Z\s\-–/&()?,!:]{4,}$/.test(trimmed) && trimmed.length < 80) {
      blocks.push({ kind: 'h1', text: trimmed });
      continue;
    }

    // Mixed-case heading ending with colon, short enough to be a label
    if (/^([\w\s]+):$/.test(trimmed) && trimmed.length < 55) {
      blocks.push({ kind: 'h2', text: trimmed.replace(/:$/, '') });
      continue;
    }

    // Bullet: starts with •, -, →, ✓, ✅, ☐
    const bulletMatch = trimmed.match(/^([•\-→✓✅☐])\s+(.+)/);
    if (bulletMatch) {
      const depth = /^\s{2,}/.test(line) ? 1 : 0;
      blocks.push({ kind: 'bullet', text: bulletMatch[2], depth });
      continue;
    }

    // Numbered list: "1. text" or "1) text"
    const numMatch = trimmed.match(/^(\d+)[.)]\s+(.+)/);
    if (numMatch) {
      blocks.push({ kind: 'numbered', n: parseInt(numMatch[1]), text: numMatch[2] });
      continue;
    }

    // Key: Value (colon in middle, short key)
    const kvMatch = trimmed.match(/^([^:]{2,35}):\s+(.+)/);
    if (kvMatch && !kvMatch[1].includes('.') && kvMatch[2].length > 2) {
      blocks.push({ kind: 'kv', key: kvMatch[1], value: kvMatch[2] });
      continue;
    }

    blocks.push({ kind: 'para', text: trimmed });
  }

  return blocks;
}

function CanvasContentRenderer({ content }: { content: string }) {
  const blocks = parseContent(content);
  const elements: React.ReactNode[] = [];

  for (let i = 0; i < blocks.length; i++) {
    const b = blocks[i];

    if (b.kind === 'space') {
      elements.push(<div key={i} className="h-4" />);
      continue;
    }

    if (b.kind === 'h1') {
      elements.push(
        <div key={i} className="mt-8 mb-4 pb-2 border-b-2 border-slate-100 first:mt-0">
          <span className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">{b.text}</span>
        </div>
      );
      continue;
    }

    if (b.kind === 'h2') {
      elements.push(
        <div key={i} className="mt-6 mb-2">
          <span className="text-sm font-black text-slate-800 uppercase tracking-tight">{b.text}</span>
        </div>
      );
      continue;
    }

    if (b.kind === 'bullet') {
      elements.push(
        <div key={i} className={`flex items-start gap-3 py-1 ${b.depth ? 'ml-6' : ''}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-2 flex-shrink-0 shadow-sm" />
          <span className="text-sm leading-relaxed overflow-wrap-anywhere break-words">
            <InlineText text={b.text} />
          </span>
        </div>
      );
      continue;
    }

    if (b.kind === 'numbered') {
      elements.push(
        <div key={i} className="flex items-start gap-3 py-1">
          <span className="text-xs font-black text-indigo-600 w-5 flex-shrink-0 mt-0.5 text-right font-mono">{b.n}.</span>
          <span className="text-sm leading-relaxed overflow-wrap-anywhere break-words">
            <InlineText text={b.text} />
          </span>
        </div>
      );
      continue;
    }

    if (b.kind === 'kv') {
      elements.push(
        <div key={i} className="flex items-start gap-3 py-2 border-b border-slate-50 last:border-0 hover:bg-slate-50/50 rounded-lg px-2 -mx-2 transition-colors">
          <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest min-w-[120px] flex-shrink-0 pt-1">{b.key}</span>
          <span className="text-sm leading-relaxed flex-1 overflow-wrap-anywhere break-words">
            <InlineText text={b.value} />
          </span>
        </div>
      );
      continue;
    }

    if (b.kind === 'para') {
      elements.push(
        <p key={i} className="text-sm leading-relaxed py-1 px-1 overflow-wrap-anywhere break-words">
          <InlineText text={b.text} />
        </p>
      );
      continue;
    }
  }

  return <div className="space-y-1">{elements}</div>;
}

/* ── Detail Panel ────────────────────────────── */
function DetailPanel({ section, meta, onUpdate, onClose }: {
  section: CanvasSection;
  meta: typeof META[0];
  onUpdate: (s: CanvasSection) => void;
  onClose: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(section.content);
  const eff: CanvasStatus = section.approved ? 'approved' : section.status;
  const Icon = meta.icon;

  const save = () => { onUpdate({ ...section, content: draft }); setEditing(false); };
  const cancel = () => { setDraft(section.content); setEditing(false); };
  const toggleApprove = () => onUpdate({
    ...section,
    approved: !section.approved,
    status: section.approved ? 'ongoing' : 'approved',
  });

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className={`flex items-center gap-5 px-8 py-6 border-b flex-shrink-0 backdrop-blur-md bg-white/90 border-slate-100`}>
        <div className={`w-12 h-12 rounded-[1.25rem] flex items-center justify-center flex-shrink-0 shadow-lg shadow-indigo-500/10 ${meta.accent} ${meta.color}`}>
          <Icon className="w-6 h-6" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-4 flex-wrap">
            <span className="text-[10px] text-slate-400 font-black uppercase tracking-widest mt-0.5">Module Build #{section.id}</span>
            <h3 className={`text-xl font-black tracking-tight text-slate-900`}>{meta.title}</h3>
            <StatusBadge status={eff} />
          </div>
        </div>
        <button onClick={onClose} className="w-10 h-10 flex items-center justify-center hover:bg-slate-50 rounded-2xl transition-all flex-shrink-0 text-slate-400 hover:text-slate-900 group">
          <XCircle className="w-6 h-6 group-hover:scale-110 transition-transform" />
        </button>
      </div>

      {/* Sub-prompt chips */}
      <div className="flex gap-2.5 px-8 py-4 bg-slate-50/50 border-b border-slate-100 overflow-x-auto flex-shrink-0 custom-scrollbar">
        {meta.subPrompts.map((sp, i) => (
          <span key={i} className="text-[10px] font-black bg-white text-slate-400 px-4 py-2 rounded-xl whitespace-nowrap flex-shrink-0 border border-slate-200 shadow-sm uppercase tracking-widest">
            {sp}
          </span>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-10 bg-white selection:bg-indigo-100 custom-scrollbar">
        {editing ? (
          <div className="max-w-4xl mx-auto h-full">
            <textarea
              value={draft}
              onChange={e => setDraft(e.target.value)}
              autoFocus
              className="w-full h-full min-h-[500px] text-[15px] font-bold text-slate-700 bg-slate-50 border-2 border-indigo-100 rounded-[2.5rem] p-10 resize-none focus:outline-none focus:ring-8 focus:ring-indigo-500/5 focus:border-indigo-500 leading-relaxed transition-all shadow-inner"
            />
          </div>
        ) : (
          <div className="max-w-4xl mx-auto">
            <CanvasContentRenderer content={section.content} />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 border-t border-slate-100 px-8 py-6 bg-slate-50/50 flex items-center justify-between gap-6">
        {editing ? (
          <>
            <button onClick={cancel} className="flex items-center gap-2 text-xs font-black text-slate-400 hover:text-slate-600 px-6 py-3 rounded-2xl uppercase tracking-widest transition-all">
              <X className="w-4 h-4" /> Discard
            </button>
            <button onClick={save} className="flex items-center gap-2 text-xs font-black bg-emerald-600 text-white hover:bg-emerald-700 px-8 py-4 rounded-2xl shadow-xl shadow-emerald-500/20 uppercase tracking-widest transition-all active:scale-95">
              <Check className="w-4 h-4" /> Save Analysis
            </button>
          </>
        ) : (
          <>
            <button onClick={() => setEditing(true)} className="flex items-center gap-3 text-xs font-black text-slate-400 hover:text-indigo-600 py-3 px-5 rounded-2xl hover:bg-white border border-transparent hover:border-slate-200 transition-all uppercase tracking-widest">
              <Edit3 className="w-4 h-4" /> Edit Module
            </button>
            <button
              onClick={toggleApprove}
              className={`flex items-center gap-3 text-sm font-black py-4 px-8 rounded-2xl transition-all shadow-xl active:scale-95 ${
                section.approved
                  ? 'bg-indigo-50 text-indigo-600 border border-indigo-200 hover:bg-indigo-100'
                  : 'bg-slate-900 text-white hover:bg-indigo-600 shadow-indigo-500/20'
              }`}
            >
              {section.approved ? <><CheckCircle className="w-5 h-5" /> Approved Module</> : <><ThumbsUp className="w-5 h-5" /> Approve Module</>}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

/* ── Main CanvasView ─────────────────────────── */
export default function CanvasView({ canvas, onUpdate, onApprove }: CanvasViewProps) {
  const [selectedId, setSelectedId] = useState<number | 'rbi' | null>(null);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState(canvas.buildTitle);

  const approved = canvas.sections.filter(s => s.approved).length;
  const total = canvas.sections.length;
  const pct = Math.round((approved / total) * 100);

  const selectedSection = selectedId !== 'rbi' ? (canvas.sections.find(s => s.id === selectedId) ?? null) : null;
  const selectedMeta = selectedId !== 'rbi' ? (META.find(m => m.id === selectedId) ?? null) : null;
  const showRBIDetail = selectedId === 'rbi';

  const updateSection = (updated: CanvasSection) =>
    onUpdate({ ...canvas, sections: canvas.sections.map(s => s.id === updated.id ? updated : s) });

  const saveTitle = () => { onUpdate({ ...canvas, buildTitle: titleDraft }); setEditingTitle(false); };

  return (
    <div className="flex h-full overflow-hidden bg-white">

      {/* ══════════════════════════════
          LEFT SIDEBAR — ~28-32% — Tiles list
      ══════════════════════════════ */}
      <div className="flex flex-col bg-slate-50 border-r border-slate-200 h-full flex-shrink-0 shadow-inner" style={{ width: selectedId ? '28%' : '32%' }}>

        {/* Canvas header */}
        <div className="bg-gradient-to-br from-white via-indigo-50/50 to-white px-8 py-10 flex-shrink-0 relative overflow-hidden border-b border-slate-100">
          <div className="absolute -top-12 -right-12 w-48 h-48 bg-indigo-500/5 blur-[80px] rounded-full" />
          <div className="text-indigo-600 text-[10px] font-black uppercase tracking-[0.2em] mb-4 flex items-center gap-2.5">
            <Zap className="w-4 h-4" /> AI CANVAS ENGINE
          </div>

          {editingTitle ? (
            <div className="flex items-center gap-3">
              <input
                value={titleDraft}
                onChange={e => setTitleDraft(e.target.value)}
                className="flex-1 text-sm font-bold bg-white border-2 border-indigo-100 rounded-xl px-4 py-2.5 text-slate-900 focus:outline-none focus:ring-4 focus:ring-indigo-500/5 focus:border-indigo-500 min-w-0 shadow-sm"
              />
              <button onClick={saveTitle} className="w-10 h-10 flex items-center justify-center bg-indigo-600 rounded-xl flex-shrink-0 shadow-lg shadow-indigo-500/20 active:scale-90 transition-transform"><Check className="w-5 h-5 text-white" /></button>
            </div>
          ) : (
            <h2
              onClick={() => setEditingTitle(true)}
              className="text-2xl font-black text-slate-900 cursor-pointer hover:text-indigo-600 transition-all flex items-center gap-3 group leading-[1.2] tracking-tight"
            >
              {canvas.buildTitle}
              <Edit3 className="w-4 h-4 opacity-0 group-hover:opacity-40 flex-shrink-0 transition-opacity" />
            </h2>
          )}

          {/* Progress */}
          <div className="mt-10">
            <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-[0.15em] mb-3">
              <span className="text-slate-400">{approved} of {total} Approved</span>
              <span className="text-indigo-600 font-black">{pct}% COMPLETE</span>
            </div>
            <div className="bg-slate-200/50 rounded-full h-3 overflow-hidden border border-slate-100 p-0.5 shadow-inner">
              <div 
                className="h-full bg-gradient-to-r from-slate-900 via-indigo-600 to-indigo-400 rounded-full transition-all duration-1000 shadow-[0_0_15px_rgba(99,102,241,0.3)] relative" 
                style={{ width: `${pct}%` }} 
              >
                <div className="absolute inset-0 bg-[linear-gradient(45deg,rgba(255,255,255,0.2)_25%,transparent_25%,transparent_50%,rgba(255,255,255,0.2)_50%,rgba(255,255,255,0.2)_75%,transparent_75%,transparent)] bg-[length:24px_24px] animate-shimmer opacity-30" />
              </div>
            </div>
          </div>
        </div>

        {/* Status legend (compact) */}
        <div className="px-6 py-4 bg-white/50 border-b border-slate-100 flex-shrink-0">
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            {(['on-track', 'open', 'ongoing', 'approved'] as CanvasStatus[]).map(s => (
              <div key={s} className="flex items-center gap-2">
                <StatusDot status={s} />
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{STATUS[s].label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Section list — 1 column */}
        <div className="flex-1 overflow-y-auto py-4 px-4 space-y-2 custom-scrollbar">
          {/* Canvas sections 1–10 */}
          {canvas.sections.map(section => {
            const meta = META.find(m => m.id === section.id)!;
            const eff: CanvasStatus = section.approved ? 'approved' : section.status;
            const Icon = meta.icon;
            const isSelected = selectedId === section.id;

            // Extract a 1-line preview
            const previewLine = section.content
              .split('\n')
              .map(l => l.trim())
              .find(l => l && !/^[A-Z][A-Z\s\-–/&()?,!:]{4,}$/.test(l) && !l.startsWith('#'))
              ?.replace(/^[•\-→✓✅☐\d.)\s]+/, '')
              ?.slice(0, 50) ?? '';

            return (
              <button
                key={section.id}
                onClick={() => setSelectedId(isSelected ? null : section.id)}
                className={`w-full flex items-start gap-4 px-5 py-4 text-left transition-all rounded-[1.5rem] group ${
                  isSelected
                    ? 'bg-white shadow-xl shadow-indigo-900/5 ring-1 ring-indigo-100'
                    : 'hover:bg-white/80 hover:shadow-lg hover:shadow-slate-200/50'
                }`}
              >
                <div className={`w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm transition-transform group-hover:scale-105 ${isSelected ? 'bg-indigo-600 text-white' : meta.accent + ' ' + meta.color}`}>
                  <Icon className="w-5 h-5 shadow-sm" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className={`text-sm font-black tracking-tight flex items-center justify-between gap-3 ${isSelected ? 'text-slate-900' : 'text-slate-700'}`}>
                    <span className="truncate">{section.id}. {meta.title}</span>
                    {section.approved && <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />}
                  </div>
                  {previewLine && (
                    <div className="text-[11px] text-slate-400 font-bold truncate mt-1 leading-relaxed uppercase tracking-tight opacity-70 group-hover:opacity-100 transition-opacity">{previewLine}</div>
                  )}
                  <div className="flex items-center gap-2.5 mt-2.5">
                    <StatusDot status={eff} />
                    <span className="text-[9px] font-black text-slate-400 uppercase tracking-[0.15em]">{STATUS[eff].label}</span>
                  </div>
                </div>
              </button>
            );
          })}

          {/* Divider */}
          <div className="mx-6 py-4">
             <div className="h-px bg-slate-200 w-full" />
          </div>

          {/* RBI Guidelines — inline item, distinct style */}
          <button
            onClick={() => setSelectedId(selectedId === 'rbi' ? null : 'rbi')}
            className={`w-full flex items-center gap-5 px-6 py-5 text-left transition-all rounded-[2rem] border-2 group ${
              showRBIDetail
                ? 'bg-indigo-50 border-indigo-100 shadow-inner'
                : 'bg-white border-slate-100 hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-900/5'
            }`}
          >
            <div className={`w-11 h-11 rounded-[1.25rem] flex items-center justify-center flex-shrink-0 shadow-md ${showRBIDetail ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' : 'bg-indigo-50 text-indigo-600'}`}>
              <Shield className="w-5 h-5" />
            </div>
            <div className="flex-1 min-w-0">
              <div className={`text-[13px] font-black tracking-[0.05em] uppercase ${showRBIDetail ? 'text-indigo-900' : 'text-slate-800'}`}>
                RBI COMPLIANCE GUARD
              </div>
              <div className={`text-[10px] font-black mt-1 uppercase tracking-widest ${showRBIDetail ? 'text-indigo-600/70' : 'text-slate-400'}`}>Policy Intelligence Active</div>
            </div>
            <ArrowRight className={`w-5 h-5 text-indigo-500 opacity-0 group-hover:opacity-100 transition-opacity translate-x-2 group-hover:translate-x-0`} />
          </button>
        </div>

        {/* Approve canvas */}
        <div className="border-t border-slate-200/60 p-6 flex-shrink-0 space-y-3 bg-white/50 backdrop-blur-sm">
          <button onClick={() => downloadCanvasAsDocx(canvas)} className="w-full flex items-center justify-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 hover:text-indigo-600 py-3 transition-all border-2 border-slate-100 rounded-2xl bg-white hover:border-indigo-100 hover:shadow-lg hover:shadow-indigo-900/5">
            <Download className="w-4 h-4" /> Export Canvas .docx
          </button>
          <button onClick={() => window.location.reload()} className="w-full flex items-center justify-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-slate-300 hover:text-slate-500 py-1 transition-colors">
            <RefreshCw className="w-3.5 h-3.5" /> Reset Environment
          </button>
          <button
            onClick={onApprove}
            className={`w-full flex items-center justify-center gap-3 text-xs font-black py-4.5 rounded-2xl transition-all text-white uppercase tracking-[0.2em] shadow-xl active:scale-[0.98] ${
              approved === total ? 'bg-emerald-600 shadow-emerald-500/20 hover:bg-emerald-700' : 'bg-slate-900 shadow-indigo-500/10 hover:bg-indigo-600'
            }`}
          >
            <ThumbsUp className="w-4 h-4" />
            {approved === total ? 'Finalize Build' : 'Lock Progress'}
          </button>
        </div>
      </div>

      {/* ══════════════════════════════
          RIGHT — ~72-75% — Detail view
      ══════════════════════════════ */}
      <div className="flex-1 overflow-hidden flex flex-col bg-slate-50/50">
        {selectedSection && selectedMeta ? (
          <DetailPanel
            section={selectedSection}
            meta={selectedMeta}
            onUpdate={updateSection}
            onClose={() => setSelectedId(null)}
          />
        ) : showRBIDetail ? (
          /* RBI Guidelines detail */
          <div className="flex flex-col h-full bg-white">
            <div className="flex items-center gap-5 px-8 py-6 border-b border-indigo-100 bg-indigo-50/50 flex-shrink-0">
              <div className="w-12 h-12 rounded-[1.25rem] bg-indigo-600 shadow-lg shadow-indigo-500/20 text-white flex items-center justify-center flex-shrink-0">
                <Shield className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <h3 className="font-black text-slate-900 tracking-tight uppercase">RBI Compliance Protocol</h3>
                <p className="text-[10px] font-black text-indigo-600 uppercase tracking-widest">3 Active Notifications Integrated</p>
              </div>
              <button onClick={() => setSelectedId(null)} className="w-10 h-10 flex items-center justify-center hover:bg-indigo-100 rounded-2xl transition-colors">
                <XCircle className="w-6 h-6 text-indigo-400" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-10 space-y-6 custom-scrollbar">
              {canvas.rbiGuidelines.split('\n\n').map((block, i) =>
                block.trim() ? (
                  <div key={i} className="bg-white border border-slate-100 rounded-[2rem] p-8 shadow-xl shadow-slate-200/50 group hover:border-blue-200 transition-all">
                    <pre className="text-sm text-slate-600 whitespace-pre-wrap font-bold leading-relaxed">{block.trim()}</pre>
                  </div>
                ) : null
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-12 gap-8">
            {/* Mini canvas graphic */}
            <div className="space-y-3 opacity-20 pointer-events-none select-none grayscale group-hover:grayscale-0 transition-all">
              <div className="flex gap-2.5">
                {[1,2,3,4].map(n => (
                  <div key={n} className="w-16 h-12 bg-blue-600 rounded-xl flex items-center justify-center text-xs font-black text-white">{n}</div>
                ))}
              </div>
              <div className="flex gap-2.5">
                {[5,6,7].map(n => (
                  <div key={n} className="w-20 h-12 bg-blue-600 rounded-xl flex items-center justify-center text-xs font-black text-white">{n}</div>
                ))}
              </div>
              <div className="flex gap-2.5">
                {[8,9,10].map(n => (
                  <div key={n} className="w-20 h-12 bg-blue-600 rounded-xl flex items-center justify-center text-xs font-black text-white">{n}</div>
                ))}
              </div>
            </div>
            <div className="max-w-xs">
              <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-2">Module Inspector</p>
              <p className="text-[10px] font-black text-slate-300 uppercase tracking-[0.15em] leading-relaxed">Select any analysis module from the left to drill down into NPCI policy mappings and UX flows.</p>
            </div>
            {/* Info legend */}
            <div className="mt-4 bg-white border border-slate-100 rounded-[2.5rem] p-8 text-left w-80 shadow-2xl shadow-slate-200/50">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-8 h-8 rounded-xl bg-indigo-50 flex items-center justify-center">
                  <Info className="w-4 h-4 text-indigo-500" />
                </div>
                <span className="text-[10px] font-black text-slate-900 uppercase tracking-widest">Intelligence Guide</span>
              </div>
              <div className="space-y-4">
                {(['on-track', 'open', 'ongoing', 'approved'] as CanvasStatus[]).map(s => (
                  <div key={s} className="flex items-center gap-4 group">
                    <StatusDot status={s} />
                    <div className="flex-1">
                      <div className="text-[10px] font-black text-slate-800 uppercase tracking-widest">{STATUS[s].label}</div>
                      <div className="text-[9px] font-black text-slate-400 uppercase tracking-widest opacity-60 group-hover:opacity-100 transition-opacity">{STATUS[s].desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
