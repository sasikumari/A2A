import { useState } from 'react';
import {
  Clock,
  ChevronRight, ArrowLeft,
  Fingerprint, Plus, List, AlertTriangle, Check,
  Wifi, MapPin, Tv, Car, Watch, Cpu, RefreshCw, Zap, Bell, CreditCard, Sparkles
} from 'lucide-react';
import type { PrototypeData, PrototypeScreen } from '../types';

interface PrototypeViewProps {
  prototype: PrototypeData;
  onUpdate: (updated: PrototypeData) => void;
  onApprove: () => void;
}

/* ─── Mobile Frame ─────────────────────────────────────────────────────────── */
function MobileFrame({ children, title, showBack = false, appName }: {
  children: React.ReactNode;
  title: string;
  showBack?: boolean;
  appName?: string;
}) {
  return (
    <div className="relative mx-auto drop-shadow-[0_35px_35px_rgba(0,0,0,0.25)]" style={{ width: 340, transform: 'scale(1.0)', transformOrigin: 'top center' }}>
      {/* Phone Body */}
      <div className="relative bg-[#0c0c0c] rounded-[55px] p-2.5 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.1),inset_0_0_4px_2px_rgba(255,255,255,0.2)]">
        {/* Hardware Buttons */}
        <div className="absolute top-32 -left-1 w-1 h-8 bg-zinc-800 rounded-l-md" />
        <div className="absolute top-48 -left-1 w-1 h-16 bg-zinc-800 rounded-l-md" />
        <div className="absolute top-64 -left-1 w-1 h-16 bg-zinc-800 rounded-l-md" />
        <div className="absolute top-40 -right-1 w-1 h-20 bg-zinc-800 rounded-r-md" />

        {/* Screen Area */}
        <div className="bg-[#f8f9fc] rounded-[45px] overflow-hidden relative shadow-inner" style={{ height: 700 }}>
          
          {/* Status Bar / Top Header */}
          <div className="absolute top-0 w-full z-50 bg-white/70 backdrop-blur-3xl pb-3 pt-5 px-6 border-b border-white/50 shadow-sm">
            {/* Dynamic Island */}
            <div className="absolute top-3 left-1/2 -translate-x-1/2 w-28 h-7 bg-black rounded-full flex items-center justify-between px-2 shadow-[inset_0_-2px_4px_rgba(255,255,255,0.1)]">
               <div className="w-2.5 h-2.5 bg-zinc-900 rounded-full flex items-center justify-center">
                 <div className="w-1.5 h-1.5 bg-[#0a0a0a] rounded-full opacity-50 shadow-[0_0_4px_blue]" />
               </div>
               <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
            </div>

            <div className="flex justify-between items-center px-1 mb-4 mt-1">
              <span className="text-slate-900 text-[11px] font-bold tracking-tight">9:41</span>
              <div className="flex gap-1.5 items-center">
                <Wifi className="w-3.5 h-3.5 text-slate-900" />
                <div className="flex gap-0.5">
                  {[1, 0.8, 0.6, 0.4].map((op, i) => (
                    <div key={i} className="w-0.5 bg-slate-900 rounded-full" style={{ height: 10 - i * 2, opacity: op }} />
                  ))}
                </div>
                <div className="w-6 h-3 border border-slate-400 bg-white rounded-sm flex items-center px-0.5 ml-1">
                  <div className="w-4 h-1.5 bg-slate-900 rounded-sm" />
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4 mt-2 mb-1">
              {showBack ? (
                <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center cursor-pointer hover:bg-slate-200 transition-colors">
                  <ArrowLeft className="w-4 h-4 text-slate-600" />
                </div>
              ) : (
                <div className="w-9 h-9 rounded-[14px] bg-gradient-to-tr from-indigo-600 to-blue-500 p-[2px] shadow-lg shadow-indigo-500/30">
                  <div className="w-full h-full bg-indigo-600 rounded-[12px] flex items-center justify-center content-center relative overflow-hidden">
                    <div className="absolute w-10 h-2 bg-white/20 rotate-45 -top-2 left-0" />
                    <Zap className="w-4 h-4 text-white drop-shadow-md" />
                  </div>
                </div>
              )}
              <h1 className="text-slate-900 text-base font-black tracking-tight flex-1 truncate">
                {showBack ? title : (appName || title)}
              </h1>
              {!showBack && (
                <div className="relative cursor-pointer group">
                  <div className="w-9 h-9 rounded-full bg-white shadow-sm border border-slate-100 flex items-center justify-center group-hover:shadow-md transition-all">
                    <Bell className="w-4 h-4 text-slate-600" />
                  </div>
                  <div className="absolute top-2 right-2.5 w-2 h-2 bg-rose-500 rounded-full border-2 border-white" />
                </div>
              )}
            </div>
          </div>

          <div className="overflow-y-auto bg-[#f8f9fc] custom-scrollbar pb-10" style={{ height: 700, paddingTop: 130 }}>
            {children}
          </div>

          {/* Home Indicator */}
          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-36 h-1.5 bg-zinc-300 rounded-full shadow-sm" />
        </div>
      </div>
    </div>
  );
}

/* ─── Utility to detect screen archetype from id/title ─────────────────────── */
type ScreenType =
  | 'home' | 'create' | 'auth' | 'confirm' | 'manage' | 'dispute' | 'generic'
  | 'home' | 'create' | 'auth' | 'confirm' | 'manage' | 'dispute' | 'generic'
  | 'sec_device_prompt' | 'sec_device_qr' | 'sec_device_consent' | 'sec_link_success'
  | 'sec_gps_pay' | 'sec_payment_notification' | 'sec_payment_success' | 'sec_device_type';

function detectType(screen: PrototypeScreen): ScreenType {
  const t = (screen.id + ' ' + screen.title + ' ' + (screen.journeyPhase || '')).toLowerCase();
  const iotView = (screen.meta?.iotView || '') as string;

  if (iotView === 'device_type' || t.includes('device_type_select')) return 'sec_device_type';
  if (iotView === 'device_prompt' || t.includes('sec_device_prompt') || t.includes('deviceprompt')) return 'sec_device_prompt';
  if (iotView === 'device_qr' || t.includes('sec_device_qr') || t.includes('qrlink')) return 'sec_device_qr';
  if (iotView === 'delegate_setup' || t.includes('delegate_setup')) return 'create';
  if (iotView === 'set_limits' || t.includes('set_limits')) return 'create';
  if (iotView === 'pin_auth' || t.includes('phone_pin_auth')) return 'auth';
  if (iotView === 'device_consent' || t.includes('sec_device_consent') || t.includes('deviceconsent')) return 'sec_device_consent';
  if (iotView === 'link_success' || t.includes('sec_link_success') || t.includes('linksuccess')) return 'sec_link_success';
  if (iotView === 'gps_pay' || t.includes('sec_payment_trigger') || t.includes('gps')) return 'sec_gps_pay';
  if (iotView === 'payment_notification' || t.includes('payment_notification')) return 'sec_payment_notification';
  if (iotView === 'payment_success' || t.includes('sec_payment_success')) return 'sec_payment_success';

  if (t.includes('home') || t.includes('dashboard') || t.includes('landing') || t.includes('discover')) return 'home';
  if (t.includes('create') || t.includes('setup') || t.includes('select') || t.includes('enter') || t.includes('configure') || t.includes('add_device') || t.includes('register') || t.includes('corridor') || t.includes('beneficiary') || t.includes('emi') || t.includes('credit_select')) return 'create';
  if (t.includes('auth') || t.includes('pin') || t.includes('biometric') || t.includes('finger') || t.includes('authenticate')) return 'auth';
  if (t.includes('confirm') || t.includes('success') || t.includes('done') || t.includes('created') || t.includes('activated') || t.includes('complete') || t.includes('processing') || t.includes('track')) return 'confirm';
  if (t.includes('manage') || t.includes('list') || t.includes('history') || t.includes('my ') || t.includes('detail') || t.includes('modify') || t.includes('pause') || t.includes('revoke') || t.includes('suspend') || t.includes('device_dashboard') || t.includes('credit_dashboard') || t.includes('review')) return 'manage';
  if (t.includes('dispute') || t.includes('report') || t.includes('complaint') || t.includes('issue') || t.includes('resolve')) return 'dispute';
  return 'generic';
}

/* ─── Secondary Device Frame ──────────────────── */
function SecondaryDeviceFrame({ deviceType, children }: { deviceType?: string; children: React.ReactNode }) {
  const isSmall = deviceType === 'watch' || deviceType === 'small';
  const isWide = deviceType === 'tv' || deviceType === 'wide';

  if (isSmall) return (
    <div className="relative mx-auto" style={{ width: 220 }}>
      <div className="bg-slate-200 rounded-[50px] p-2 shadow-2xl border-2 border-white" style={{ height: 240 }}>
        <div className="bg-white rounded-[42px] overflow-hidden h-full flex flex-col shadow-inner">
          <div className="bg-slate-50 flex items-center justify-between px-5 pt-4 pb-2 border-b border-slate-100">
            <span className="text-slate-900 text-[10px] font-black">10:28</span>
            <div className="flex gap-1">
              <Wifi className="w-2.5 h-2.5 text-slate-400" />
              <div className="w-5 h-2.5 border border-slate-300 rounded-[2px]"><div className="w-3 h-full bg-emerald-500 rounded-[1px]" /></div>
            </div>
          </div>
          <div className="flex-1 overflow-hidden">{children}</div>
        </div>
      </div>
    </div>
  );

  if (isWide) return (
    <div className="relative mx-auto" style={{ width: 340 }}>
      <div className="bg-slate-100 rounded-2xl p-2 shadow-2xl border border-white">
        <div className="bg-white rounded-xl overflow-hidden shadow-inner" style={{ height: 210 }}>
          <div className="bg-slate-50 flex items-center justify-between px-4 py-2 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-blue-600" />
              <span className="text-slate-900 text-[10px] font-black uppercase tracking-widest">Secondary Display</span>
            </div>
            <div className="flex gap-2">
               <Wifi className="w-3 h-3 text-slate-300" />
               <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            </div>
          </div>
          <div className="overflow-hidden h-full">{children}</div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="relative mx-auto" style={{ width: 310 }}>
      <div className="bg-slate-200 rounded-3xl p-2.5 shadow-2xl border border-white">
        <div className="bg-white rounded-2xl overflow-hidden shadow-inner" style={{ height: 180 }}>
          <div className="bg-slate-800 flex items-center justify-between px-4 py-2 border-b border-slate-700">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-400" />
              <span className="text-white text-[10px] font-black uppercase tracking-widest">Delegated Interface</span>
            </div>
            <div className="flex items-center gap-2">
              <Wifi className="w-3 h-3 text-blue-400/60" />
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
            </div>
          </div>
          <div className="overflow-hidden" style={{ height: 142 }}>{children}</div>
        </div>
      </div>
    </div>
  );
}

/* ─── Screen Components ──────────────────────────────────────── */
function HomeScreen({ screen }: { screen: PrototypeScreen }) {
  return (
    <div className="p-5 space-y-6">
      {/* Hyper-premium Home Card */}
      <div className="bg-gradient-to-br from-indigo-700 via-blue-600 to-indigo-900 rounded-[28px] p-7 text-white shadow-2xl shadow-indigo-500/30 relative overflow-hidden group hover:scale-[1.02] transition-transform duration-300">
        <div className="absolute -top-16 -right-16 w-48 h-48 bg-white/10 rounded-full blur-3xl group-hover:bg-white/20 transition-all duration-700" />
        <div className="absolute bottom-0 left-0 w-full h-1/2 bg-gradient-to-t from-black/20 to-transparent pointer-events-none" />
        
        <div className="flex justify-between items-center mb-6 relative z-10">
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-white/80">Available Limit</div>
          <div className="flex items-center gap-1.5 text-[9px] font-black uppercase tracking-wider bg-black/20 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10">
             <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Active
          </div>
        </div>
        
        <div className="text-[42px] font-black tracking-tighter leading-none relative z-10">₹24,850<span className="text-white/60 text-2xl">.25</span></div>
      </div>

      <div className="grid grid-cols-4 gap-3 px-1">
        {[{ icon: Plus, label: 'Add', color: 'from-blue-500 to-indigo-500 text-white' }, 
          { icon: CreditCard, label: 'Pay', color: 'bg-white text-indigo-600 border border-slate-100 shadow-sm' }, 
          { icon: List, label: 'History', color: 'bg-white text-slate-700 border border-slate-100 shadow-sm' }, 
          { icon: Bell, label: 'Alerts', color: 'bg-slate-100 text-slate-500' }].map(({ icon: Icon, label, color }) => (
          <div key={label} className={`flex flex-col items-center gap-2 group cursor-pointer transition-all duration-[400ms] hover:-translate-y-1`}>
            <div className={`w-14 h-14 rounded-[20px] flex items-center justify-center transition-all duration-300 transform group-hover:shadow-lg ${color.includes('from-') ? `bg-gradient-to-tr ${color} shadow-lg shadow-blue-500/30` : color}`}>
              <Icon className="w-6 h-6" />
            </div>
            <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 group-hover:text-indigo-600 transition-colors">{label}</span>
          </div>
        ))}
      </div>

      <div className="space-y-3 pt-2">
        <div className="flex justify-between items-center px-2 mb-3">
          <div className="text-xs font-black uppercase tracking-widest text-slate-800">Recent Activity</div>
          <div className="text-[10px] font-bold text-indigo-600 cursor-pointer hover:underline">See All</div>
        </div>
        
        {screen.elements.map((el, i) => (
          <div key={i} className={`flex items-center justify-between bg-white border border-slate-100 rounded-[20px] p-4 text-sm text-slate-800 shadow-[0_2px_8px_rgba(0,0,0,0.02)] hover:shadow-md hover:border-indigo-100 hover:-translate-y-0.5 transition-all cursor-pointer group`}>
            <div className="flex items-center gap-4">
               <div className="w-10 h-10 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-black group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                 {el.charAt(0).toUpperCase()}
               </div>
               <div className="flex flex-col">
                 <span className="font-bold text-[13px]">{el}</span>
                 <span className="text-[10px] text-slate-400 mt-0.5 font-medium">Just now</span>
               </div>
            </div>
            <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-indigo-500 group-hover:translate-x-1 transition-all" />
          </div>
        ))}
      </div>
    </div>
  );
}

function CreateScreen({ screen }: { screen: PrototypeScreen }) {
  return (
    <div className="p-6 space-y-6">
      <div className="text-center mb-6">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 mb-4 shadow-sm">
           <Zap className="w-6 h-6" />
        </div>
        <h3 className="text-2xl font-black text-slate-900 tracking-tight leading-none">{screen.title}</h3>
        <p className="text-[13px] text-slate-500 font-medium mt-3 leading-relaxed px-2">{screen.description}</p>
      </div>

      <div className="space-y-4">
        {screen.elements.map((el, i) => (
          <div key={i} className="space-y-1.5 transition-all">
            <label className="text-[10px] text-slate-500 uppercase font-black tracking-widest ml-1">{el}</label>
            <div className="bg-white border text-sm border-slate-200 rounded-[18px] p-4 text-slate-800 font-semibold focus-within:border-indigo-500 focus-within:ring-4 focus-within:ring-indigo-500/10 transition-all shadow-sm">
               <span className="opacity-30">Select or enter {el.toLowerCase().split(' ')[0]}...</span>
            </div>
          </div>
        ))}
      </div>

      <div className="pt-4">
        <button className="w-full bg-slate-900 text-white text-xs font-black py-4 rounded-[20px] shadow-lg shadow-slate-900/20 active:scale-95 hover:bg-black transition-all uppercase tracking-[0.2em] flex items-center justify-center gap-2">
          Proceed Securely <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

function AuthScreen({ screen: _screen }: { screen: PrototypeScreen }) {
  return (
    <div className="p-8 flex flex-col items-center justify-center h-full space-y-10">
      <div className="text-center">
        <div className="text-[10px] font-black uppercase text-indigo-600 tracking-[0.2em] mb-3">SECURE AUTHENTICATION</div>
        <div className="text-[44px] font-black text-slate-900 tracking-tighter leading-none">₹2,000.00</div>
        <div className="text-xs font-semibold text-slate-500 mt-3 bg-slate-100 inline-block px-3 py-1 rounded-full">General Stores Inc.</div>
      </div>

      <div className="relative group cursor-pointer my-10">
        <div className="absolute inset-0 bg-indigo-500 blur-2xl opacity-20 group-hover:opacity-40 group-hover:scale-110 transition-all duration-500" />
        <div className="w-28 h-28 rounded-full bg-white flex items-center justify-center border border-slate-100 shadow-[0_10px_40px_rgba(79,70,229,0.15)] relative z-10 transition-transform group-active:scale-90 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-50 to-white" />
            <Fingerprint className="w-12 h-12 text-indigo-600 relative z-20" />
            <div className="absolute inset-0 border-2 border-indigo-500 rounded-full animate-ping opacity-30" style={{ animationDuration: '2s' }} />
        </div>
      </div>

      <div className="text-center space-y-2">
        <p className="text-[13px] text-slate-900 font-black uppercase tracking-widest">Verify Identity</p>
        <p className="text-[11px] text-slate-400 font-bold uppercase tracking-tight leading-relaxed max-w-[200px] mx-auto">Use biometrics to securely authorize payment</p>
      </div>
    </div>
  );
}

function ConfirmScreen({ screen }: { screen: PrototypeScreen }) {
  return (
    <div className="p-6 flex flex-col items-center min-h-full space-y-8 bg-gradient-to-b from-emerald-50 to-[#f8f9fc] pt-12">
      <div className="relative">
         <div className="absolute inset-0 bg-emerald-400 blur-2xl opacity-30 animate-pulse" />
         <div className="w-24 h-24 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-full flex items-center justify-center shadow-2xl shadow-emerald-500/40 relative z-10 border-4 border-white animate-bounce-slow" style={{ animationDuration: '3s' }}>
           <Check className="w-12 h-12 text-white" strokeWidth={3} />
         </div>
      </div>

      <div className="text-center">
        <div className="text-[11px] font-black text-emerald-600 uppercase tracking-[0.2em] mb-2">PAYMENT SUCCESSFUL</div>
        <h3 className="text-5xl font-black text-slate-900 tracking-tighter">₹2,000</h3>
      </div>

      <div className="w-full bg-white rounded-[24px] p-6 space-y-5 border border-slate-100 shadow-[0_8px_30px_rgba(0,0,0,0.03)]">
        {screen.elements.map((el, i) => {
          const split = el.split(':');
          return (
            <div key={i} className="flex justify-between items-center border-b border-slate-100 pb-3 last:border-0 last:pb-0">
               <span className="text-[10px] text-slate-400 font-black uppercase tracking-widest">{split[0]}</span>
               <span className="text-[13px] text-slate-900 font-black text-right max-w-[150px] truncate">{split[1] || 'Verified'}</span>
            </div>
          );
        })}
      </div>

      <div className="w-full space-y-3 mt-auto">
        <button className="w-full bg-slate-900 text-white text-[11px] font-black py-4 rounded-2xl uppercase tracking-[0.2em] hover:bg-black hover:shadow-lg transition-all active:scale-95">
          View Receipt
        </button>
        <button className="w-full bg-white text-slate-900 text-[11px] font-black py-4 rounded-2xl border border-slate-200 uppercase tracking-[0.2em] hover:bg-slate-50 transition-all">
          Done
        </button>
      </div>
    </div>
  );
}

function ManageScreen({ screen }: { screen: PrototypeScreen }) {
  return (
    <div className="p-5 space-y-5">
       <div className="flex gap-2 p-1 bg-white rounded-2xl shadow-sm border border-slate-100 mx-1">
         {['Active', 'Flagged', 'All'].map((t, i) => (
           <div key={t} className={`flex-1 text-center text-[10px] font-black py-2.5 rounded-[12px] transition-all uppercase tracking-widest cursor-pointer ${i === 0 ? 'bg-indigo-600 text-white shadow-md' : 'bg-transparent text-slate-400 hover:bg-slate-50 hover:text-slate-600'}`}>{t}</div>
         ))}
       </div>

       <div className="space-y-3 px-1">
         {screen.elements.map((el, i) => (
           <div key={i} className={`bg-white border border-slate-100 rounded-[20px] p-5 shadow-[0_4px_15px_rgba(0,0,0,0.02)] hover:shadow-xl hover:border-indigo-100 hover:-translate-y-1 transition-all cursor-pointer group`}>
             <div className="text-[14px] font-black text-slate-900 tracking-tight leading-snug mb-4 group-hover:text-indigo-600 transition-colors">{el}</div>
             <div className="flex justify-between items-center bg-slate-50 p-3 rounded-xl">
               <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                  <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-widest">Active</span>
               </div>
               <span className="text-[10px] font-black text-indigo-600 uppercase tracking-widest flex items-center gap-1 group-hover:translate-x-1 transition-transform">Details <ChevronRight className="w-3 h-3"/></span>
             </div>
           </div>
         ))}
       </div>
    </div>
  );
}

function DisputeScreen({ screen }: { screen: PrototypeScreen }) {
  return (
    <div className="p-5 space-y-4">
      <div className="bg-rose-50 border border-rose-100/50 rounded-2xl p-4 flex gap-3">
        <AlertTriangle className="w-5 h-5 text-rose-500 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-rose-800 font-semibold leading-relaxed">Select a transaction to instantly raise a regulatory dispute via the UDIR framework.</p>
      </div>
      
      <div className="space-y-3 mt-4">
        {screen.elements.map((el, i) => (
          <div key={i} className="bg-white hover:bg-slate-50 border border-slate-100 rounded-[18px] px-4 py-4 text-sm text-slate-800 font-medium flex justify-between items-center cursor-pointer shadow-sm hover:shadow-md transition-all active:scale-95">
            <span className="truncate pr-4 leading-tight">{el}</span>
            <ChevronRight className="w-4 h-4 text-slate-300" />
          </div>
        ))}
      </div>
      
      <div className="pt-4">
        <button className="w-full bg-rose-600 text-white text-[11px] font-black py-4 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-rose-500/20 uppercase tracking-widest hover:bg-rose-700 transition-all active:scale-95">
          <RefreshCw className="w-4 h-4" /> Submit Dispute T+1
        </button>
      </div>
    </div>
  );
}

function GenericScreen({ screen }: { screen: PrototypeScreen }) {
  return (
    <div className="p-5 space-y-4">
      <div className="bg-indigo-50 rounded-3xl p-6 border border-indigo-100 text-center">
        <Sparkles className="w-8 h-8 text-indigo-400 mx-auto mb-3" />
        <div className="text-lg font-black text-indigo-900 tracking-tight leading-tight mb-2">{screen.title}</div>
        <div className="text-[13px] text-indigo-700/80 font-medium leading-relaxed">{screen.description}</div>
      </div>
      <div className="space-y-3">
        {screen.elements.map((el, i) => (
          <div key={i} className="bg-white rounded-2xl px-5 py-4 border border-slate-100 shadow-sm text-[13px] text-slate-700 font-semibold hover:shadow-md hover:border-indigo-200 transition-all">
            {el}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Secondary Ecosystem Screens ────────────────────────────────────────────── */
function SecondaryDevicePromptScreen({ screen }: { screen: PrototypeScreen }) {
  return <SecondaryDeviceFrame deviceType={screen.meta?.deviceType}><div className="h-full flex flex-col items-center justify-center p-4 bg-white text-center gap-3">
    <div className="text-blue-600 font-black uppercase tracking-widest">UPI Circle</div>
    <p className="text-sm text-slate-600 leading-snug">Access not authorized.<br/>Sync with Primary App.</p>
    <button className="bg-blue-600 text-white text-sm px-6 py-2 rounded-lg font-bold">AUTHORIZE</button>
  </div></SecondaryDeviceFrame>;
}

function SecondaryDeviceQrScreen({ screen }: { screen: PrototypeScreen }) {
   return <SecondaryDeviceFrame deviceType={screen.meta?.deviceType}><div className="h-full flex flex-col items-center justify-center p-2 bg-white gap-2">
     <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">Scan to Sync</p>
     <div className="w-16 h-16 border-2 border-slate-200 p-1 flex items-center justify-center rounded-lg">
       <div className="w-12 h-12 bg-slate-800 rounded-sm"></div>
     </div>
     <p className="text-[11px] font-mono font-bold text-slate-500">{screen.meta?.deviceVpa || 'sec.device@upi'}</p>
   </div></SecondaryDeviceFrame>;
}

function SecondaryDeviceConsentScreen({ screen }: { screen: PrototypeScreen }) {
  return <SecondaryDeviceFrame deviceType={screen.meta?.deviceType}><div className="h-full flex flex-col items-center justify-center p-3 bg-white gap-3">
    <div className="text-sm font-bold text-blue-600 border-b border-blue-50 pb-1 w-full text-center">DELEGATION CONSENT</div>
    <p className="text-xs text-slate-500 leading-tight">Primary User requests access.<br/>Review terms on phone.</p>
    <div className="flex gap-2 w-full">
      <button className="flex-1 bg-red-50 text-red-600 text-xs font-bold py-1.5 rounded-lg border border-red-200">DECLINE</button>
      <button className="flex-1 bg-emerald-600 text-white text-xs font-bold py-1.5 rounded-lg">CONFIRM</button>
    </div>
  </div></SecondaryDeviceFrame>;
}

function SecondaryLinkSuccessScreen({ screen }: { screen: PrototypeScreen }) {
  return <SecondaryDeviceFrame deviceType={screen.meta?.deviceType}><div className="h-full flex flex-col items-center justify-center p-3 bg-white gap-2">
    <div className="w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center"><Check className="text-emerald-600 w-6 h-6"/></div>
    <p className="text-sm font-black text-slate-900">SYNC COMPLETE</p>
    <button className="w-full bg-blue-600 text-white text-xs font-bold py-1.5 rounded-lg mt-1">CONTINUE</button>
  </div></SecondaryDeviceFrame>;
}

function SecondaryContextPayScreen({ screen }: { screen: PrototypeScreen }) {
  return <SecondaryDeviceFrame deviceType={screen.meta?.deviceType}><div className="h-full bg-slate-50 flex flex-col overflow-hidden">
    <div className="flex-1 flex items-center justify-center border-b border-slate-200 relative bg-slate-100">
      <MapPin className="text-blue-500 w-8 h-8"/>
      <div className="absolute top-2 left-2 bg-white px-2 py-0.5 rounded shadow text-[11px] font-black text-slate-800 uppercase">{screen.meta?.contextTag || 'STATION NEARBY'}</div>
    </div>
    <div className="p-3 gap-2 flex flex-col bg-white">
      <div className="flex justify-between items-center"><span className="text-xs font-bold text-slate-800 truncate pr-2">{screen.meta?.merchantName || 'MERCHANT'}</span><span className="text-sm font-black text-slate-900">₹{screen.meta?.amount || '---'}</span></div>
      <button className="w-full bg-blue-600 text-white text-xs font-bold py-2 rounded-lg">AUTHORIZE PAY</button>
    </div>
  </div></SecondaryDeviceFrame>;
}

function SecondaryPaymentNotificationScreen({ screen }: { screen: PrototypeScreen }) {
  return (
    <div className="p-3 h-full flex flex-col gap-3">
      <div className="bg-amber-50 border border-amber-200 p-3 rounded-2xl flex items-start gap-2">
        <Bell className="w-4 h-4 text-amber-600 mt-0.5"/>
        <p className="text-sm text-amber-900 font-medium">Delegated access request for <span className="font-bold">₹{screen.meta?.amount || '---'}</span> detected from secondary ecosystem.</p>
      </div>
      <div className="bg-white border border-slate-200 rounded-2xl p-4 flex-1 flex flex-col justify-center items-center text-center gap-2 shadow-sm">
        <Clock className="w-8 h-8 text-blue-500 animate-pulse"/>
        <p className="text-sm font-bold text-slate-500">Wait for Auth...</p>
      </div>
      <div className="flex gap-2">
         <button className="flex-1 bg-red-50 text-red-600 text-sm font-bold py-3 rounded-xl border border-red-200">DENY</button>
         <button className="flex-1 bg-emerald-600 text-white text-sm font-bold py-3 rounded-xl">APPROVE</button>
      </div>
    </div>
  );
}

function SecondaryPaymentSuccessScreen({ screen }: { screen: PrototypeScreen }) {
  return <SecondaryDeviceFrame deviceType={screen.meta?.deviceType}><div className="h-full flex flex-col items-center justify-center p-3 bg-white gap-2">
    <div className="w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center"><Check className="text-emerald-600 w-6 h-6"/></div>
    <p className="text-sm font-black text-emerald-700">PAID ₹{screen.meta?.amount || '---'}</p>
    <div className="text-[11px] font-bold text-slate-400 uppercase tracking-widest leading-none mt-1">Confirmed</div>
  </div></SecondaryDeviceFrame>;
}

function SecondaryDeviceTypeScreen({ screen }: { screen: PrototypeScreen }) {
  const items = (screen.meta?.deviceOptions || [{icon: Car, label: 'Vehicle'}, {icon: Watch, label: 'Accessory'}, {icon: Tv, label: 'Display'}, {icon: Cpu, label: 'Appliance'}]) as any[];
  return (
    <div className="p-3 grid grid-cols-2 gap-2 h-full">
      {items.map(({icon: Icon, label}) => (
        <div key={label} className="border border-slate-100 rounded-2xl p-4 flex flex-col items-center gap-2 bg-white shadow-sm hover:shadow-md transition-all">
          <Icon className="w-6 h-6 text-indigo-600"/>
          <span className="text-[11px] font-black uppercase tracking-widest text-slate-600">{label}</span>
        </div>
      ))}
    </div>
  );
}

/* ─── Dynamic Dispatcher ────────────────────────────────────── */
function DynamicScreen({ screen }: { screen: PrototypeScreen }) {
  const type = detectType(screen);
  switch (type) {
    case 'home': return <HomeScreen screen={screen} />;
    case 'create': return <CreateScreen screen={screen} />;
    case 'auth': return <AuthScreen screen={screen} />;
    case 'confirm': return <ConfirmScreen screen={screen} />;
    case 'manage': return <ManageScreen screen={screen} />;
    case 'dispute': return <DisputeScreen screen={screen} />;
    case 'sec_device_prompt': return <SecondaryDevicePromptScreen screen={screen} />;
    case 'sec_device_qr': return <SecondaryDeviceQrScreen screen={screen} />;
    case 'sec_device_consent': return <SecondaryDeviceConsentScreen screen={screen} />;
    case 'sec_link_success': return <SecondaryLinkSuccessScreen screen={screen} />;
    case 'sec_gps_pay': return <SecondaryContextPayScreen screen={screen} />;
    case 'sec_payment_notification': return <SecondaryPaymentNotificationScreen screen={screen} />;
    case 'sec_payment_success': return <SecondaryPaymentSuccessScreen screen={screen} />;
    case 'sec_device_type': return <SecondaryDeviceTypeScreen screen={screen} />;
    default: return <GenericScreen screen={screen} />;
  }
}

export function isSecondaryDeviceScreen(screen: PrototypeScreen): boolean {
  const type = detectType(screen);
  return ['sec_device_prompt', 'sec_device_qr', 'sec_device_consent', 'sec_link_success', 'sec_gps_pay', 'sec_payment_success', 'sec_device_type'].includes(type);
}

const PHASE_COLORS: Record<string, string> = {
  Initiate: 'bg-blue-50 text-blue-700 border-blue-100',
  Select: 'bg-slate-50 text-slate-700 border-slate-100',
  Create: 'bg-blue-50 text-blue-700 border-blue-100',
  Configure: 'bg-indigo-50 text-indigo-700 border-indigo-100',
  Authenticate: 'bg-amber-50 text-amber-700 border-amber-100',
  Confirm: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  Manage: 'bg-cyan-50 text-cyan-700 border-cyan-100',
  Detail: 'bg-cyan-50 text-cyan-700 border-cyan-100',
  Resolve: 'bg-rose-50 text-rose-700 border-rose-100',
};

/* ─── Main View ────────────────────────────────────────────── */
export default function PrototypeView({ prototype: proto, onUpdate, onApprove }: PrototypeViewProps) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [feedback, setFeedback] = useState(proto.feedback);

  const screens = proto.screens || [];
  const current = screens[activeIdx] ?? screens[0];
  const journey = proto.userJourney;

  const handleStepClick = (screenId: string) => {
    const idx = screens.findIndex(s => s.id === screenId);
    if (idx >= 0) setActiveIdx(idx);
  };

  return (
    <div className="w-full h-full flex gap-5 px-8 py-8 overflow-hidden animate-fadeIn bg-slate-100/50">
      {/* Col 1: Steps & Info */}
      <div className="flex-[1.2] flex flex-col gap-5 overflow-hidden max-w-[450px]">
        {/* Title Header */}
        <div className="bg-white rounded-[2rem] p-8 shadow-[0_15px_40px_rgba(0,0,0,0.06)] border border-slate-100 flex-shrink-0">
           <div className="flex items-start gap-5">
             <div className="w-16 h-16 rounded-[1.25rem] bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-3xl shadow-lg shadow-blue-500/30">📱</div>
             <div>
               <div className="flex items-center gap-2 mb-1.5">
                 <div className="text-[10px] font-black text-blue-600 uppercase tracking-[0.2em] bg-blue-50 px-2 py-0.5 rounded-full">{journey?.persona?.name} Flow</div>
                 <div className="text-[9px] font-black text-slate-400 uppercase tracking-widest border border-slate-200 px-2 py-0.5 rounded-full">Titan Native UI</div>
               </div>
               <h3 className="text-[26px] font-black text-slate-900 tracking-tight leading-none">{current?.title}</h3>
             </div>
           </div>
        </div>
        
        {/* Playbook List */}
        <div className="flex-1 bg-white rounded-[2rem] p-4 shadow-[0_15px_40px_rgba(0,0,0,0.06)] border border-slate-100 flex flex-col overflow-hidden">
           <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
              {journey?.journey_steps?.map((step, i) => {
                const isActive = step.screen_id === current?.id;
                return (
                  <button key={i} onClick={() => handleStepClick(step.screen_id)} className={`w-full text-left rounded-[20px] p-4 transition-all group border-2 ${isActive ? 'bg-indigo-50/50 border-indigo-100 shadow-sm' : 'bg-transparent border-transparent hover:bg-slate-50'}`}>
                    <div className="flex items-center gap-3 mb-2">
                      <span className={`w-8 h-8 rounded-full text-xs font-black flex items-center justify-center transition-all duration-300 shadow-sm ${isActive ? 'bg-indigo-600 text-white scale-110 shadow-indigo-500/30' : 'bg-white border border-slate-200 text-slate-400 group-hover:bg-slate-100'}`}>{step.step}</span>
                      <span className={`text-[9px] font-black px-3 py-1.5 rounded-full shadow-sm uppercase tracking-[0.15em] ${PHASE_COLORS[step.phase] || 'bg-slate-900 text-white'}`}>{step.phase}</span>
                    </div>
                    <p className={`text-[14px] font-bold leading-snug ml-11 transition-colors duration-300 ${isActive ? 'text-slate-900' : 'text-slate-500 group-hover:text-slate-700'}`}>{step.action}</p>
                  </button>
                );
              })}
           </div>
        </div>

        {/* Feedback Controller */}
        <div className="bg-white rounded-[2rem] p-6 shadow-[0_15px_40px_rgba(0,0,0,0.06)] border border-slate-100 flex-shrink-0 relative overflow-hidden">
          <div className="absolute -top-10 -right-10 w-32 h-32 bg-indigo-500/10 blur-3xl pointer-events-none rounded-full" />
          <div className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-3 ml-1">Iterate Design</div>
          <textarea
            value={feedback}
            onChange={e => setFeedback(e.target.value)}
            placeholder="Type your design feedback here to rebuild..."
            className="w-full text-[13px] font-bold border-2 border-slate-100 rounded-2xl p-4 mb-4 bg-slate-50/50 h-20 resize-none focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-200 transition-all placeholder:text-slate-300 relative z-10"
          />
          <div className="flex gap-3 relative z-10">
            <button onClick={() => onUpdate({ ...proto, feedback })} className="flex-1 py-4 rounded-xl bg-slate-100 text-[10px] font-black text-slate-500 uppercase tracking-widest hover:bg-slate-200 transition-all active:scale-95">Save Draft</button>
            <button onClick={onApprove} className="flex-[2] py-4 rounded-xl bg-slate-900 text-white text-[10px] font-black uppercase tracking-[0.15em] flex items-center justify-center gap-2 shadow-lg hover:bg-black transition-all active:scale-95">
               <Check className="w-4 h-4"/> Sync App Blueprint
            </button>
          </div>
        </div>
      </div>

      {/* Col 2: High Fidelity Simulator Preview */}
      <div className="flex-[2] bg-white rounded-[3rem] flex flex-col items-center justify-center p-8 border border-slate-100 shadow-[0_20px_60px_rgba(0,0,0,0.03)] relative overflow-hidden">
        {/* Ambient background glow behind the phone */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[80%] h-[80%] bg-[radial-gradient(circle_at_center,rgba(79,70,229,0.05)_0%,transparent_60%)] pointer-events-none" />
        
        <div className="flex-1 flex items-center justify-center w-full z-10">
           {isSecondaryDeviceScreen(current) ? (
             <DynamicScreen screen={current} />
           ) : (
             <MobileFrame title={current?.title || ''} showBack={activeIdx > 0}>
                <DynamicScreen screen={current}/>
             </MobileFrame>
           )}
        </div>
        
        {/* Navigation Paginator Bar */}
        <div className="flex items-center gap-8 mt-10 z-10 bg-white/80 backdrop-blur-lg px-8 py-4 rounded-full shadow-lg border border-slate-100/50">
           {activeIdx > 0 ? (
             <button onClick={() => setActiveIdx(activeIdx - 1)} className="text-[11px] font-black text-slate-400 hover:text-slate-900 transition-colors uppercase tracking-[0.2em]">← BACK</button>
           ) : <div className="w-[60px]" />}
           
           <div className="flex gap-2.5">
             {screens.map((_, i) => (
               <div key={i} className={`h-2 rounded-full transition-all duration-500 cursor-pointer ${i === activeIdx ? 'bg-indigo-600 w-8 shadow-sm shadow-indigo-500/50' : 'bg-slate-200 w-2 hover:bg-slate-300 hover:w-3'}`} onClick={() => setActiveIdx(i)}/>
             ))}
           </div>
           
           {activeIdx < screens.length - 1 ? (
             <button onClick={() => setActiveIdx(activeIdx + 1)} className="text-[11px] font-black text-indigo-600 hover:text-indigo-800 transition-colors uppercase tracking-[0.2em]">NEXT →</button>
           ) : <div className="w-[60px]" />}
        </div>
      </div>
    </div>
  );
}
