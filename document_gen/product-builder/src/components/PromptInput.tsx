import { useState } from 'react';
import { Sparkles, ArrowRight, Lightbulb } from 'lucide-react';

interface PromptInputProps {
  onSubmit: (prompt: string, featureName: string) => void;
}

const EXAMPLE_PROMPTS = [
  {
    name: 'UPI IoT Payments',
    description: 'Enable UPI payments across all IoT devices — Car Dashboard, Smart TV, Smartwatch, Smart Glasses, Smart Ring, Smart Appliances, and AI Agents — using UPI Circle Delegate Payments (purpose code H). Covers device onboarding (mobile OTP → UPI ID → QR linking), mandate creation with ₹15,000 monthly limit, device-native authentication, full payment flow, device management, transaction history, and UDIR dispute resolution. Supports all device categories (Type A–E) with device-specific capability flags.',
    tag: 'IoT',
  },
  {
    name: 'UPI A2A Phase 2',
    description: 'Build Phase 2 of Account-to-Account UPI payments with AI-assisted orchestration, enhanced interoperability, and expanded merchant categories',
    tag: '',
  },
  {
    name: 'UPI Biometric Enhancement',
    description: 'Enhance biometric UPI payments with liveness detection, multi-modal biometrics (face + fingerprint), and offline capability for low-connectivity areas',
    tag: '',
  },
  {
    name: 'UPI Reserve Pay (SBMD)',
    description: 'Build Single Block Multiple Debits — customers block funds for merchants, merchant triggers multiple partial debits upon service delivery, auto-expiry, UDIR dispute integration',
    tag: '',
  },
  {
    name: 'UPI Credit Line Payments',
    description: 'Enable UPI payments from credit line accounts (BNPL) — credit eligibility check, real-time credit disbursal, EMI conversion, and credit limit management within UPI flow',
    tag: '',
  },
  {
    name: 'UPI Offline Payments',
    description: 'Enable UPI payments in low/no connectivity areas using pre-generated payment tokens, NFC-based offline transactions, and delayed settlement with fraud safeguards',
    tag: '',
  },
];

export default function PromptInput({ onSubmit }: PromptInputProps) {
  const [prompt, setPrompt] = useState('');
  const [featureName, setFeatureName] = useState('');
  const [focused, setFocused] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    onSubmit(prompt.trim(), featureName.trim());
  };

  const useExample = (example: (typeof EXAMPLE_PROMPTS)[0]) => {
    setFeatureName(example.name);
    setPrompt(example.description);
  };

  return (
    <div className="min-h-full flex flex-col items-center justify-start p-4 sm:p-12 animate-fadeIn relative bg-slate-50/30 overflow-y-auto custom-scrollbar pb-32">
      {/* Decorative background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-500/5 blur-[120px] rounded-full pointer-events-none -z-10" />

      <div className="w-full max-w-4xl relative z-10">
        {/* Hero */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2.5 bg-indigo-50 border border-indigo-100 text-indigo-600 rounded-2xl px-5 py-2.5 text-xs font-black uppercase tracking-widest mb-8 shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            AI-Powered Product Builder
          </div>
          <h1 className="text-5xl sm:text-6xl font-black text-slate-900 mb-6 leading-[1.1] tracking-tight">
            Build your next<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-slate-900 via-indigo-600 to-slate-900">UPI Orchestration</span>
          </h1>
          <p className="text-slate-500 text-lg max-w-2xl mx-auto font-medium leading-relaxed uppercase tracking-tight">
            From car dashboards to smart rings. Input your vision and our agents generate the NPCI compliance pack autonomously.
          </p>
        </div>

        {/* Input Form */}
        <div className="bg-white rounded-[2.5rem] p-8 sm:p-10 mb-12 relative shadow-2xl shadow-indigo-900/5 border border-slate-100 overflow-hidden group">
          <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-slate-900 via-indigo-600 to-slate-900 opacity-80" />

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 gap-6">
              <div>
                <label className="block text-xs font-black text-slate-400 uppercase tracking-widest mb-3 ml-1">Feature Name</label>
                <input
                  type="text"
                  value={featureName}
                  onChange={e => setFeatureName(e.target.value)}
                  placeholder="e.g., UPI IoT Payments for Connected Cars"
                  className="w-full px-6 py-4.5 rounded-2xl border border-slate-200 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 bg-slate-50 text-slate-900 font-bold placeholder-slate-400 transition-all text-lg shadow-inner"
                />
              </div>

              <div>
                <label className="block text-xs font-black text-slate-400 uppercase tracking-widest mb-3 ml-1">Requirements & Scope</label>
                <div className={`relative rounded-[2rem] border transition-all duration-300 ${focused ? 'border-indigo-500 ring-4 ring-indigo-500/10 shadow-lg' : 'border-slate-200 shadow-inner'} bg-slate-50`}>
                  <textarea
                    value={prompt}
                    onChange={e => setPrompt(e.target.value)}
                    onFocus={() => setFocused(true)}
                    onBlur={() => setFocused(false)}
                    placeholder="Describe the feature journey, target users, and specific compliance needs..."
                    rows={6}
                    className="w-full px-6 py-5 rounded-[2rem] bg-transparent resize-none focus:outline-none text-slate-700 font-bold placeholder-slate-400 leading-relaxed shadow-inner"
                  />
                  <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 bg-slate-100/50 rounded-b-[2rem]">
                    <span className="text-[10px] font-black text-slate-400 tracking-wider">CHAR_COUNT: {prompt.length}</span>
                    <div className="flex items-center gap-2 text-[10px] font-black text-indigo-600 uppercase tracking-widest">
                      <Sparkles className="w-3.5 h-3.5 animate-pulse" />
                      Deep Analysis Active
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={!prompt.trim()}
              className="w-full bg-slate-900 hover:bg-indigo-600 text-white font-black text-lg py-5 rounded-2xl shadow-xl shadow-indigo-900/20 flex items-center justify-center gap-3 transition-all active:scale-[0.98] disabled:opacity-30 disabled:cursor-not-allowed group uppercase tracking-[0.2em]"
            >
              <Sparkles className="w-5 h-5 group-hover:rotate-12 transition-transform" />
              Initialize AI Feature Build
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform" />
            </button>
          </form>
        </div>

        {/* Example prompts */}
        <div className="mb-12">
          <div className="flex items-center gap-4 mb-8">
            <div className="w-10 h-10 rounded-2xl bg-amber-50 flex items-center justify-center border border-amber-100 shadow-sm">
              <Lightbulb className="w-5 h-5 text-amber-500" />
            </div>
            <span className="text-xs font-black text-slate-400 uppercase tracking-widest">Try a Titans Benchmark:</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 pb-8">
            {EXAMPLE_PROMPTS.map((ex) => (
              <button
                key={ex.name}
                onClick={() => useExample(ex)}
                className={`text-left p-6 rounded-[2.5rem] border transition-all duration-300 group shadow-sm hover:shadow-xl hover:-translate-y-1 ${
                  ex.tag === 'IoT'
                    ? 'bg-indigo-50 border-indigo-100 hover:bg-indigo-100 hover:border-indigo-200'
                    : 'bg-white border-slate-100 hover:bg-slate-50 hover:border-indigo-200'
                }`}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className={`text-sm font-black tracking-tight uppercase ${ex.tag === 'IoT' ? 'text-indigo-700' : 'text-slate-900 group-hover:text-indigo-600'}`}>
                    {ex.name}
                  </div>
                  {ex.tag === 'IoT' && (
                    <span className="text-[9px] font-black px-2 py-0.5 rounded-full bg-indigo-600 text-white shadow-sm flex-shrink-0 uppercase tracking-tighter">
                      IoT
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-slate-500 font-bold leading-relaxed line-clamp-3 group-hover:text-slate-600 transition-colors uppercase tracking-tight">{ex.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* RBI Guidelines note */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div className="bg-white rounded-[2.5rem] p-7 flex gap-5 border border-slate-100 shadow-xl shadow-slate-200/50 overflow-hidden relative group transition-all hover:shadow-2xl">
            <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 blur-3xl -z-10" />
            <div className="text-3xl mt-1 grayscale group-hover:grayscale-0 transition-all duration-500">🏛️</div>
            <div>
              <div className="text-xs font-black text-slate-900 uppercase tracking-widest mb-2">Policy Governance</div>
              <div className="text-[11px] text-slate-500 font-bold leading-relaxed uppercase tracking-tight">
                Integrated RBI Notifications & 2024 compliance analysis for Digital Payment Security Controls.
              </div>
            </div>
          </div>
          <div className="bg-slate-900 rounded-[2.5rem] p-7 flex gap-5 shadow-xl shadow-indigo-500/20 group relative overflow-hidden transition-all hover:shadow-2xl hover:scale-[1.01] active:scale-100">
             <div className="absolute -bottom-4 -right-4 text-white/10 text-7xl group-hover:scale-125 transition-transform duration-700 font-black">🔌</div>
            <div className="text-3xl mt-1">⚡</div>
            <div>
              <div className="text-xs font-black text-white uppercase tracking-widest mb-2">Titan IoT Engine</div>
              <div className="text-[11px] text-zinc-400 font-bold leading-relaxed uppercase tracking-tight">
                Autonomous generation of all 7 NPCI-standard compliance documents for Type A–E IoT device payments.
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Global vignette fix for landing page benchmarks */}
      <div className="vignette-bottom" />
    </div>
  );
}