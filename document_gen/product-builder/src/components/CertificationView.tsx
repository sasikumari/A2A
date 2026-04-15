import { useState, useEffect } from 'react';
import { 
  ShieldCheck, CheckCircle2, 
  ChevronRight, Info, Cpu, Lock, FileCheck 
} from 'lucide-react';

interface CertificationViewProps {
  featureName: string;
  onProceed: () => void;
}

interface PillarResult {
  status: 'PASSED' | 'FAILED' | 'PENDING';
  score: number;
  findings: string[];
  auditor_notes: string;
}

export default function CertificationView({ featureName, onProceed }: CertificationViewProps) {
  const [activePillar, setActivePillar] = useState<'TECHNICAL' | 'SECURITY' | 'COMPLIANCE'>('TECHNICAL');
  const [loading, setLoading] = useState(true);

  const pillars: Record<'TECHNICAL' | 'SECURITY' | 'COMPLIANCE', PillarResult> = {
    TECHNICAL: {
      status: 'PASSED',
      score: 98,
      findings: [
        "XSD Schema validation successful across all 6 nodes.",
        "Response time benchmarks met titanium standards (< 200ms).",
        "Callback URL SSL certificate verified (TLS 1.3)."
      ],
      auditor_notes: "System architecture aligns with NPCI distributed mesh standards. No schema regressions detected."
    },
    SECURITY: {
      status: 'PASSED',
      score: 100,
      findings: [
        "Message signing (RSA-2048) verified for all inter-agent traffic.",
        "Encryption of PII fields (Amount, VPA) confirmed at rest.",
        "No hardcoded credentials detected in agent skill execution logs."
      ],
      auditor_notes: "Cryptographic handshakes between NPCI Switch and Banks are robust. HSM simulated modules responding correctly."
    },
    COMPLIANCE: {
      status: 'PASSED',
      score: 95,
      findings: [
        "Adheres to RBI Digital Payment Security Controls (2024).",
        "Dispute (UDIR) automated resolution flow confirmed.",
        "Data localization check: All records stored in local 'storage/' nodes."
      ],
      auditor_notes: "Regulatory parameters for the use-case are fully met. UDIR integration is live."
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 2000);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-20 animate-pulse bg-white">
        <div className="w-24 h-24 bg-indigo-50 rounded-[2.5rem] flex items-center justify-center mb-8 border-2 border-indigo-100">
          <ShieldCheck className="w-12 h-12 text-indigo-500 animate-bounce" />
        </div>
        <h2 className="text-3xl font-black text-slate-900 tracking-tighter uppercase">Regulatory Audit in Progress</h2>
        <p className="mt-4 text-slate-400 font-bold uppercase tracking-widest text-xs">Performing 3-Pillar Formal Certification Audit</p>
      </div>
    );
  }

  const current = pillars[activePillar];

  return (
    <div className="h-full flex flex-col px-10 py-10 animate-fadeIn bg-white selection:bg-indigo-100">
      {/* Header */}
      <div className="flex-shrink-0 flex items-center justify-between mb-12">
        <div className="flex items-center gap-8">
          <div className="w-20 h-20 rounded-[2.2rem] bg-indigo-600 flex items-center justify-center shadow-2xl shadow-indigo-500/20 text-white border-4 border-white">
            <ShieldCheck className="w-10 h-10" />
          </div>
          <div>
            <h2 className="text-5xl font-black text-slate-900 tracking-tighter leading-none mb-3">
              NPCI <span className="text-indigo-600">3-Pillar</span> Certification
            </h2>
            <div className="flex items-center gap-3">
               <span className="text-[11px] font-black text-indigo-600 uppercase tracking-[0.2em] bg-indigo-50 px-4 py-2 rounded-full border border-indigo-100 shadow-sm">{featureName}</span>
               <div className="w-1.5 h-1.5 rounded-full bg-slate-200" />
               <span className="text-[11px] font-black text-slate-400 uppercase tracking-widest leading-none">Formal Regulatory Dashboard</span>
            </div>
          </div>
        </div>
        <button 
          onClick={onProceed}
          className="group flex items-center gap-6 px-12 py-6 rounded-[2.8rem] bg-slate-900 text-white font-black uppercase tracking-[0.3em] text-[12px] hover:bg-emerald-600 transition-all shadow-2xl active:scale-95"
        >
          APPROVE FOR MAINNET <ChevronRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform" />
        </button>
      </div>

      <div className="flex-1 flex gap-10 min-h-0">
        {/* Left: Pillar Selectors */}
        <div className="w-1/3 flex flex-col gap-4">
          {(['TECHNICAL', 'SECURITY', 'COMPLIANCE'] as const).map(p => {
            const Icon = p === 'TECHNICAL' ? Cpu : p === 'SECURITY' ? Lock : FileCheck;
            const isActive = activePillar === p;
            return (
              <button
                key={p}
                onClick={() => setActivePillar(p)}
                className={`flex items-center gap-6 p-8 rounded-[2.5rem] border-2 transition-all duration-300 text-left group ${
                  isActive 
                    ? 'bg-white border-indigo-600 shadow-2xl shadow-indigo-500/10 ring-4 ring-indigo-500/5 -translate-y-1' 
                    : 'bg-slate-50 border-transparent hover:bg-white hover:border-slate-200 hover:shadow-lg'
                }`}
              >
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-all ${isActive ? 'bg-indigo-600 text-white shadow-lg' : 'bg-white text-slate-400 border border-slate-100'}`}>
                  <Icon className="w-7 h-7" />
                </div>
                <div className="flex-1">
                   <div className={`text-[10px] font-black uppercase tracking-[0.3em] mb-1 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`}>Pillar {p === 'TECHNICAL' ? 'I' : p === 'SECURITY' ? 'II' : 'III'}</div>
                   <div className={`text-xl font-black tracking-tight ${isActive ? 'text-slate-900' : 'text-slate-600'}`}>{p}</div>
                </div>
                <div className="flex flex-col items-end gap-1">
                   <div className={`text-base font-black ${pillars[p].status === 'PASSED' ? 'text-emerald-500' : 'text-amber-500'}`}>{pillars[p].score}%</div>
                   {pillars[p].status === 'PASSED' && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
                </div>
              </button>
            );
          })}
        </div>

        {/* Right: Detailed Audit Results */}
        <div className="flex-1 bg-slate-50 rounded-[3rem] p-12 border-2 border-slate-100 overflow-y-auto custom-scrollbar flex flex-col gap-10 selection:bg-indigo-100/30">
          
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-5">
              <div className="w-16 h-16 rounded-[1.5rem] bg-white flex items-center justify-center text-indigo-600 border border-slate-100 shadow-xl">
                 {activePillar === 'TECHNICAL' ? <Cpu className="w-8 h-8" /> : activePillar === 'SECURITY' ? <Lock className="w-8 h-8" /> : <FileCheck className="w-8 h-8" />}
              </div>
              <div>
                <h3 className="text-3xl font-black text-slate-900 tracking-tighter mb-1">{activePillar} Audit Status</h3>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                  <span className="text-[10px] font-black text-emerald-600 uppercase tracking-widest">Formal Certification Passed</span>
                </div>
              </div>
            </div>
            <div className="bg-white px-6 py-3 rounded-2xl border border-slate-100 shadow-sm flex flex-col items-center">
               <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Audit Score</span>
               <span className="text-3xl font-black text-indigo-600 tracking-tighter">{current.score}<span className="text-slate-300 text-lg">/100</span></span>
            </div>
          </div>

          <div className="space-y-6">
            <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-3">
               <Info className="w-4 h-4" /> Pillar Findings
            </h4>
            <div className="grid grid-cols-1 gap-4">
              {current.findings.map((finding, idx) => (
                <div key={idx} className="flex items-center gap-6 p-6 bg-white border border-slate-100 rounded-[2rem] hover:border-indigo-200 transition-all group">
                   <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-500 shrink-0 group-hover:scale-110 transition-transform">
                      <CheckCircle2 className="w-5 h-5" />
                   </div>
                   <span className="text-[15px] font-bold text-slate-700 leading-snug">{finding}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-indigo-900 rounded-[2.5rem] p-10 text-white relative overflow-hidden group">
             <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
                <ShieldCheck className="w-24 h-24" />
             </div>
             <h4 className="text-[11px] font-black text-indigo-300 uppercase tracking-[0.3em] mb-4">Official Auditor Notes</h4>
             <p className="text-xl font-bold leading-relaxed tracking-tight italic opacity-90">
                "{current.auditor_notes}"
             </p>
             <div className="mt-8 pt-8 border-t border-white/10 flex items-center justify-between">
                <div className="flex items-center gap-4">
                   <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center font-black text-xs text-indigo-300">SC</div>
                   <div>
                      <div className="text-xs font-black uppercase tracking-widest">S Committee Audit Agent</div>
                      <div className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest mt-0.5">Titan Signature Verified</div>
                   </div>
                </div>
                <div className="text-indigo-500 font-mono text-[10px] font-black tracking-widest px-4 py-2 border border-indigo-500/30 rounded-lg">
                   CERT_SHA256: 8A7F...2B9C
                </div>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
