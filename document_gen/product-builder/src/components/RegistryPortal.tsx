import React, { useState } from 'react';
import { Shield, Key, Fingerprint, Activity, CheckCircle, Database, Network } from 'lucide-react';

export default function RegistryPortal({ onClose }: { onClose: () => void }) {
  const [did, setDid] = useState<string | null>(null);
  const [manifestHash, setManifestHash] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [orgName, setOrgName] = useState('SBI Bank Node');
  const [skills, setSkills] = useState('verify_signature, acknowledge_intent');
  const [allowlist, setAllowlist] = useState('npci_master, switch');

  const handleRegister = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8001/api/registry/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org: orgName,
          skills: skills.split(',').map(s => s.trim()),
          allowed_callers: allowlist.split(',').map(s => s.trim())
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setDid(data.bundle.did);
        setManifestHash(data.bundle.manifest_hash);
      }
    } catch (err) {
      console.error("Registry failed", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col px-10 py-10 animate-fadeIn bg-slate-950 text-white min-h-[90vh]">
      <div className="flex-shrink-0 flex items-center justify-between mb-8">
        <div className="flex items-center gap-6">
          <div className="w-16 h-16 rounded-[1.5rem] bg-indigo-900/50 flex items-center justify-center shadow-[0_0_30px_rgba(99,102,241,0.3)] border border-indigo-500/30">
            <Shield className="w-8 h-8 text-indigo-400" />
          </div>
          <div>
            <h2 className="text-4xl font-black text-white tracking-tighter leading-tight drop-shadow-md">
              Zero-Trust Registry
            </h2>
            <div className="flex items-center gap-2 mt-1 opacity-80">
               <span className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em] bg-indigo-900/40 px-2 py-1 rounded">NPCI Mesh Auth</span>
               <div className="w-1 h-1 rounded-full bg-slate-600" />
               <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">DID Minting Portal</span>
            </div>
          </div>
        </div>
        <button onClick={onClose}
          className="px-6 py-3 rounded-xl bg-slate-800 text-white text-xs font-bold uppercase tracking-widest hover:bg-slate-700 transition border border-slate-700">
          Close Registry
        </button>
      </div>

      <div className="max-w-4xl w-full mx-auto grid grid-cols-2 gap-8">
        {/* Left Form */}
        <div className="bg-slate-900/60 p-8 rounded-[2rem] border border-slate-800 shadow-xl backdrop-blur-xl flex flex-col gap-5 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
            <Database className="w-48 h-48" />
          </div>

          <h3 className="text-xl font-black uppercase italic tracking-wider text-slate-300 z-10 flex items-center gap-3">
             <Fingerprint className="text-indigo-500" /> Agent Onboarding Request
          </h3>
          
          <div className="z-10 mt-2">
            <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Organization</label>
            <input value={orgName} onChange={e=>setOrgName(e.target.value)} className="w-full bg-slate-950/50 border border-slate-700 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 text-indigo-200 font-mono transition-colors" />
          </div>

          <div className="z-10">
            <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Required Skills (Comma Sep)</label>
            <textarea value={skills} onChange={e=>setSkills(e.target.value)} rows={3} className="w-full bg-slate-950/50 border border-slate-700 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 text-indigo-200 font-mono transition-colors" />
          </div>

          <div className="z-10">
            <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Allowed Callers (Comma Sep)</label>
            <input value={allowlist} onChange={e=>setAllowlist(e.target.value)} className="w-full bg-slate-950/50 border border-slate-700 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 text-indigo-200 font-mono transition-colors" />
          </div>

          <button onClick={handleRegister} disabled={loading} className="z-10 mt-4 w-full bg-indigo-600 hover:bg-indigo-500 text-white font-black text-xs tracking-widest uppercase py-4 rounded-xl shadow-[0_0_20px_rgba(99,102,241,0.4)] transition-all flex items-center justify-center gap-2">
             {loading ? 'Minting Credential...' : <><Key className="w-4 h-4" /> Submit to Authority</>}
          </button>
        </div>

        {/* Right Status */}
        <div className="flex flex-col gap-6">
           {did ? (
              <div className="bg-emerald-900/20 border-2 border-emerald-500/30 p-8 rounded-[2rem] shadow-[0_0_40px_rgba(16,185,129,0.1)] relative overflow-hidden animate-slideIn flex flex-col h-full">
                 <div className="absolute top-0 right-0 p-8 opacity-10">
                   <Network className="w-32 h-32 text-emerald-500" />
                 </div>
                 <div className="flex items-center gap-4 mb-6 z-10">
                   <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center">
                     <CheckCircle className="w-6 h-6 text-emerald-400" />
                   </div>
                   <h3 className="text-xl font-black uppercase text-emerald-400 tracking-wider">Credential Minted</h3>
                 </div>

                 <div className="z-10 flex-1 flex flex-col gap-4">
                   <div className="bg-slate-950/50 p-4 rounded-xl border border-emerald-500/20">
                     <span className="text-[10px] text-emerald-500/70 font-black uppercase tracking-widest block mb-1">Agent DID</span>
                     <span className="font-mono text-sm text-emerald-100 break-all">{did}</span>
                   </div>
                   <div className="bg-slate-950/50 p-4 rounded-xl border border-emerald-500/20">
                     <span className="text-[10px] text-emerald-500/70 font-black uppercase tracking-widest block mb-1">Manifest Hash (SHA-256)</span>
                     <span className="font-mono text-xs text-emerald-100/70 break-all">{manifestHash}</span>
                   </div>
                 </div>

                 <p className="z-10 text-[10px] text-emerald-400/50 font-bold uppercase tracking-widest flex items-center gap-2 mt-4"><Activity className="w-3 h-3" /> Agent may now authenticate via Token Authority</p>
              </div>
           ) : (
              <div className="border border-slate-800 border-dashed rounded-[2rem] p-8 flex flex-col items-center justify-center h-full text-slate-500 bg-slate-900/20">
                 <Shield className="w-16 h-16 mb-4 opacity-50" />
                 <p className="text-xs font-black uppercase tracking-widest text-center">Awaiting Submission</p>
                 <p className="text-[10px] text-center mt-2 max-w-[200px] leading-relaxed">Submit the request to generate a cryptographic identity for this agent.</p>
              </div>
           )}
        </div>
      </div>
    </div>
  );
}
