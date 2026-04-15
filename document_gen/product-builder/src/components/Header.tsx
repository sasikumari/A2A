import { Zap, Sparkles } from 'lucide-react';
import type { Stage } from '../types';

interface HeaderProps {
  stage: Stage;
  featureName: string;
  onOpenRegistry?: () => void;
}

const STAGE_LABELS: Record<Stage, string> = {
  input:           'Mission Brief',
  clarify:         'Clarification',
  canvas:          'Product Canvas',
  documents:       'Documents',
  'product-kit':   'Product Kit',
  brd:             'Formal BRD',
  'technical-plan': 'Orchestration',
  'a2a-sync':      'A2A Protocol',
  execution:       'Execution',
  verify:          'Validation',
  certification:   'Certification',
  deploy:          'Deployment',
};

export default function Header({ stage, featureName, onOpenRegistry }: HeaderProps) {
  const label = STAGE_LABELS[stage] ?? stage;

  return (
    <header style={{ background: '#0f172a', borderBottom: '1px solid #1e293b' }} className="sticky top-0 z-50 shadow-lg">

      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-20 gap-4">

          {/* Brand */}
          <div className="flex items-center gap-4 flex-shrink-0">
            <div className="flex items-center gap-3 bg-slate-800/60 rounded-2xl px-4 py-2 border border-slate-700/50 shadow-sm transition-all hover:bg-slate-700/80 hover:shadow-md group backdrop-blur-md">
              <div className="bg-indigo-500/10 p-1.5 rounded-xl transition-colors group-hover:bg-indigo-500/20">
                <Zap className="w-5 h-5 text-indigo-400" />
              </div>
              <div className="flex flex-col">
                <span className="font-black text-[10px] tracking-widest uppercase text-indigo-400 leading-none mb-0.5">NPCI</span>
                <span className="text-slate-300 text-[10px] font-black tracking-tight opacity-40 group-hover:opacity-80 transition-opacity">TITAN AGENTS</span>
              </div>
            </div>
            {featureName && stage !== 'input' && (
              <div className="hidden sm:flex items-center gap-3">
                <span className="text-slate-600 font-bold text-lg leading-none select-none">/</span>
                <span className="text-white font-bold text-sm tracking-tight truncate max-w-[280px]">{featureName}</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-4">
            {onOpenRegistry && (
              <button 
                onClick={onOpenRegistry}
                className="hidden md:flex items-center gap-2.5 bg-slate-800/60 border border-indigo-500/30 rounded-2xl px-4 py-2 hover:bg-slate-700/80 transition-colors"
                title="Open NPCI Token Authority Registry"
              >
                <span className="text-[10px] font-black text-indigo-400 uppercase tracking-widest">Token Authority</span>
              </button>
            )}

            {/* AI Status badge */}
            <div className="hidden md:flex items-center gap-2.5 bg-emerald-900/20 border border-emerald-500/30 rounded-2xl px-4 py-2 backdrop-blur-md">
              <div className="relative">
                <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                <span className="absolute inset-0 w-full h-full bg-emerald-400 blur-sm opacity-30 animate-pulse"></span>
              </div>
              <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">Autonomous Sync: OK</span>
            </div>

            {/* Stage badge */}
            <div className="flex items-center gap-3 bg-indigo-900/40 rounded-2xl px-5 py-2 shadow-lg shadow-indigo-500/20 border border-indigo-500/50 active:scale-[0.98] transition-all backdrop-blur-md">
              <span className="text-[10px] text-indigo-300 uppercase font-black tracking-widest hidden sm:inline opacity-80">Phase</span>
              <div className="w-px h-3 bg-slate-700 hidden sm:block"></div>
              <span className="text-sm font-black tracking-tight text-white">{label}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
