import { useState } from 'react';
import { MessageSquare, Layout, CheckCircle, Sparkles } from 'lucide-react';
import ThinkingLoader from './ThinkingLoader';
import CanvasView from './CanvasView';
import type { CanvasData } from '../types';
import { generateCanvas } from '../utils/canvasGenerator';

interface ThinkingCanvasPageProps {
  prompt: string;
  featureName: string;
  onApprove: (canvas: CanvasData) => void;
}

type TabId = 'thinking' | 'canvas';

export default function ThinkingCanvasPage({ prompt, featureName, onApprove }: ThinkingCanvasPageProps) {
  const [activeTab, setActiveTab] = useState<TabId>('thinking');
  const [thinkingDone, setThinkingDone] = useState(false);
  const [canvas, setCanvas] = useState<CanvasData | null>(null);

  const handleThinkingComplete = () => {
    const generated = generateCanvas(prompt, featureName);
    setCanvas(generated);
    setThinkingDone(true);
    // Auto-switch to canvas tab
    setActiveTab('canvas');
  };

  const handleApprove = () => {
    if (canvas) onApprove(canvas);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      {/* ── Tab Bar ─────────────────────────────── */}
      <div className="bg-white border-b border-slate-200 flex-shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center gap-1 pt-2">
            {/* Deep Thinking Tab */}
            <button
              onClick={() => setActiveTab('thinking')}
              className={`relative flex items-center gap-2 px-5 py-3 text-sm font-semibold rounded-t-2xl border-b-2 transition-all duration-150 ${
                activeTab === 'thinking'
                  ? 'border-indigo-600 text-indigo-700 bg-indigo-50'
                  : 'border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-50'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              Deep Thinking Agent
              {!thinkingDone && (
                <span className="flex items-center gap-1 bg-indigo-100 text-indigo-600 text-xs px-1.5 py-0.5 rounded-full font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
                  Live
                </span>
              )}
              {thinkingDone && (
                <span className="bg-emerald-100 text-emerald-600 text-xs px-1.5 py-0.5 rounded-full font-medium flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" /> Done
                </span>
              )}
            </button>

            {/* Canvas Tab */}
            <button
              onClick={() => thinkingDone && setActiveTab('canvas')}
              disabled={!thinkingDone}
              className={`relative flex items-center gap-2 px-5 py-3 text-sm font-semibold rounded-t-2xl border-b-2 transition-all duration-150 ${
                activeTab === 'canvas' && thinkingDone
                  ? 'border-indigo-600 text-indigo-700 bg-indigo-50'
                  : thinkingDone
                  ? 'border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-50 cursor-pointer'
                  : 'border-transparent text-slate-300 cursor-not-allowed'
              }`}
            >
              <Layout className="w-4 h-4" />
              Product Canvas
              {!thinkingDone && (
                <span className="text-xs text-slate-400 font-normal tracking-tight uppercase tracking-widest">(generating...)</span>
              )}
              {thinkingDone && canvas && (
                <span className="bg-indigo-100 text-indigo-600 text-xs px-2 py-0.5 rounded-full font-black uppercase tracking-widest">
                  {canvas.sections.filter(s => s.approved).length}/{canvas.sections.length}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* ── Tab Content ─────────────────────────── */}
      <div className="flex-1 overflow-y-auto bg-slate-50">
        {activeTab === 'thinking' && (
          <ThinkingLoader
            featureName={featureName}
            onComplete={handleThinkingComplete}
          />
        )}

        {activeTab === 'canvas' && canvas && (
          <CanvasView
            canvas={canvas}
            onUpdate={setCanvas}
            onApprove={handleApprove}
          />
        )}

        {activeTab === 'canvas' && !canvas && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center p-12 bg-white rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-200/50">
              <Sparkles className="w-12 h-12 mx-auto mb-6 text-indigo-400 animate-pulse" />
              <p className="text-sm font-black text-slate-800 uppercase tracking-[0.2em]">Canvas Manifest In-Transit</p>
              <p className="text-[10px] font-black text-slate-400 mt-2 uppercase tracking-widest">Watch progress in the Deep Thinking Agent tab</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
