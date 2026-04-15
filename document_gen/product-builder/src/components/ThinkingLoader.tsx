import { useEffect, useRef, useState } from 'react';
import { Sparkles, Search, Shield, Brain, FileText, CheckCircle, ExternalLink, Zap } from 'lucide-react';

interface ThinkingLoaderProps {
  onComplete: () => void;
  featureName: string;
}

type MessageType = 'thinking' | 'tool' | 'result' | 'insight' | 'done';

interface ChatMessage {
  id: number;
  type: MessageType;
  text: string;
  subText?: string;
  icon?: React.ReactNode;
  delay: number;
  duration: number;
}

const buildMessages = (featureName: string): ChatMessage[] => [
  {
    id: 1, type: 'thinking', delay: 300, duration: 1200,
    icon: <Brain className="w-3.5 h-3.5" />,
    text: `Analyzing feature scope for "${featureName || 'your feature'}"...`,
    subText: 'Understanding requirements, target users, and integration points.',
  },
  {
    id: 2, type: 'tool', delay: 0, duration: 1600,
    icon: <Search className="w-3.5 h-3.5" />,
    text: 'Reading RBI Notification 12032',
    subText: 'Master Direction on Digital Payment Security Controls (Feb 2021)',
  },
  {
    id: 3, type: 'result', delay: 0, duration: 1200,
    icon: <Shield className="w-3.5 h-3.5" />,
    text: 'Found 6 key compliance requirements',
    subText: 'MFA mandatory · TLS 1.3+ · DSC validation · Audit trails (5yr) · Fraud monitoring · Incident reporting within 6hrs',
  },
  {
    id: 4, type: 'tool', delay: 0, duration: 1500,
    icon: <Search className="w-3.5 h-3.5" />,
    text: 'Reading RBI Notification 1888',
    subText: 'Payment Instruments & UPI Interoperability guidelines',
  },
  {
    id: 5, type: 'result', delay: 0, duration: 1100,
    icon: <Shield className="w-3.5 h-3.5" />,
    text: 'Found consumer protection framework',
    subText: 'Full KYC for high-value txns · T+1 grievance resolution · Limit framework per category · Ombudsman escalation',
  },
  {
    id: 6, type: 'tool', delay: 0, duration: 1400,
    icon: <Search className="w-3.5 h-3.5" />,
    text: 'Reading NPCI Operational Circular OC 228',
    subText: 'UPI Single Block Multiple Debits — Reserve Pay guidelines',
  },
  {
    id: 7, type: 'result', delay: 0, duration: 1000,
    icon: <Shield className="w-3.5 h-3.5" />,
    text: 'Reserve Pay compliance mapped',
    subText: 'Block duration limits · Customer notifications for all lifecycle events · Online-verified merchants only · Daily MIS to NPCI',
  },
  {
    id: 8, type: 'insight', delay: 0, duration: 1800,
    icon: <Brain className="w-3.5 h-3.5" />,
    text: 'Mapping ecosystem landscape...',
    subText: 'PSPs (PhonePe, GPay, Paytm) · Issuer banks (SBI, HDFC, ICICI) · Merchants (Zomato, Uber, Zepto) · RBI sandbox signals for AI payments',
  },
  {
    id: 9, type: 'insight', delay: 0, duration: 1600,
    icon: <Brain className="w-3.5 h-3.5" />,
    text: 'Key insight: Exponential differentiation opportunity',
    subText: 'Moves from single-event auth to AI-assisted payment orchestration. Addresses cart abandonment (18%) and checkout friction (avg 28s → target <10s).',
  },
  {
    id: 10, type: 'thinking', delay: 0, duration: 2200,
    icon: <FileText className="w-3.5 h-3.5" />,
    text: 'Drafting all 10 canvas sections...',
    subText: 'Feature · Need · Market View · Scalability · Validation · Product Operating · Comms · Pricing · Risks · Compliance',
  },
  {
    id: 11, type: 'done', delay: 0, duration: 800,
    icon: <CheckCircle className="w-3.5 h-3.5" />,
    text: 'Canvas ready! All sections generated with RBI compliance checks applied.',
    subText: '10 sections · 3 RBI notifications · Full ecosystem analysis',
  },
];

const TYPE_STYLES: Record<MessageType, { bg: string; border: string; iconBg: string; iconColor: string; label: string; labelColor: string }> = {
  thinking: {
    bg: 'bg-white', border: 'border-indigo-100',
    iconBg: 'bg-indigo-100', iconColor: 'text-indigo-600',
    label: 'Thinking', labelColor: 'text-indigo-600',
  },
  tool: {
    bg: 'bg-indigo-50/30', border: 'border-indigo-200',
    iconBg: 'bg-indigo-100', iconColor: 'text-indigo-600',
    label: 'Tool use', labelColor: 'text-indigo-600',
  },
  result: {
    bg: 'bg-emerald-50', border: 'border-emerald-200',
    iconBg: 'bg-emerald-100', iconColor: 'text-emerald-600',
    label: 'Result', labelColor: 'text-emerald-600',
  },
  insight: {
    bg: 'bg-amber-50', border: 'border-amber-200',
    iconBg: 'bg-amber-100', iconColor: 'text-amber-600',
    label: 'Insight', labelColor: 'text-amber-600',
  },
  done: {
    bg: 'bg-indigo-50', border: 'border-indigo-300',
    iconBg: 'bg-indigo-600', iconColor: 'text-white',
    label: 'Complete', labelColor: 'text-indigo-700',
  },
};

function TypingIndicator() {
  return (
    <div className="flex items-end gap-2 mb-3">
      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-600 to-indigo-600 flex items-center justify-center flex-shrink-0">
        <Sparkles className="w-3.5 h-3.5 text-white" />
      </div>
      <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
        <div className="flex gap-1 items-center h-4">
          <div className="thinking-dot" />
          <div className="thinking-dot" />
          <div className="thinking-dot" />
        </div>
      </div>
    </div>
  );
}

function ChatBubble({ msg, isNew }: { msg: ChatMessage; isNew: boolean }) {
  const style = TYPE_STYLES[msg.type];

  return (
    <div className={`flex items-end gap-2 mb-3 ${isNew ? 'animate-slideUp' : ''}`}>
      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-600 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-sm">
        <Sparkles className="w-3.5 h-3.5 text-white" />
      </div>

      <div className={`flex-1 max-w-xl border rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm ${style.bg} ${style.border}`}>
        <div className={`flex items-center gap-1.5 mb-1.5 text-xs font-semibold ${style.labelColor}`}>
          <span className={`w-4 h-4 rounded-full ${style.iconBg} ${style.iconColor} flex items-center justify-center`}>
            {msg.icon}
          </span>
          {style.label}
        </div>

        <p className="text-sm text-slate-900 font-medium leading-snug">{msg.text}</p>
        {msg.subText && (
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">{msg.subText}</p>
        )}

        {msg.type === 'tool' && (
          <div className="mt-2 flex items-center gap-1 text-xs text-indigo-500">
            <ExternalLink className="w-3 h-3" />
            <span>rbi.org.in → notifications</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ThinkingLoader({ onComplete, featureName }: ThinkingLoaderProps) {
  const messages = buildMessages(featureName);
  const [visibleCount, setVisibleCount] = useState(0);
  const [showTyping, setShowTyping] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let idx = 0;

    const showNext = () => {
      if (idx >= messages.length) {
        setShowTyping(false);
        setTimeout(onComplete, 600);
        return;
      }

      const msg = messages[idx];
      const startDelay = idx === 0 ? msg.delay : 0;

      setTimeout(() => {
        setShowTyping(true);
        setTimeout(() => {
          setShowTyping(false);
          setVisibleCount(idx + 1);
          idx++;
          setTimeout(showNext, 200);
        }, msg.duration);
      }, startDelay);
    };

    showNext();
  }, [onComplete]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [visibleCount, showTyping]);

  const progressPercent = Math.round((visibleCount / messages.length) * 100);

  return (
    <div className="min-h-[calc(100vh-130px)] flex items-center justify-center p-4 sm:p-6">
      <div className="w-full max-w-2xl flex flex-col" style={{ height: 'calc(100vh - 180px)', maxHeight: 680 }}>
        
        {/* Header */}
        <div className="flex items-center justify-between mb-6 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-[14px] bg-gradient-to-tr from-indigo-600 to-indigo-500 p-[2px] shadow-lg shadow-indigo-500/30">
              <div className="w-full h-full bg-indigo-600 rounded-[12px] flex items-center justify-center content-center relative overflow-hidden">
                <div className="absolute w-10 h-2 bg-white/20 rotate-45 -top-2 left-0" />
                <Zap className="w-4 h-4 text-white drop-shadow-md" />
              </div>
            </div>
            <div>
              <div className="text-sm font-black text-slate-900 uppercase tracking-tight">Cognitive Engine</div>
              <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none mt-1">NPCI A2A · Orchestrator</div>
            </div>
          </div>

          <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-widest transition-all ${
            visibleCount >= messages.length
              ? 'bg-emerald-50 text-emerald-600 border border-emerald-100'
              : 'bg-indigo-50 text-indigo-600 border border-indigo-100'
          }`}>
            {visibleCount >= messages.length ? (
              <><CheckCircle className="w-3.5 h-3.5" /> Done</>
            ) : (
              <>
                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                Working
              </>
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="mb-6 flex-shrink-0 px-2">
          <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">
            <span>Generating canvas for <span className="text-indigo-600">{featureName || 'your feature'}</span></span>
            <span>{progressPercent}%</span>
          </div>
          <div className="bg-slate-100 rounded-full h-2 shadow-inner p-0.5 border border-slate-50">
            <div
              className="bg-gradient-to-r from-indigo-600 via-indigo-500 to-indigo-400 h-full rounded-full transition-all duration-700 shadow-[0_0_10px_rgba(99,102,241,0.3)]"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Chat window */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto bg-white rounded-[2rem] border border-slate-100 p-8 space-y-0 shadow-2xl shadow-slate-200/50"
          style={{ scrollBehavior: 'smooth' }}
        >
          {/* Initial user prompt bubble (right side) */}
          <div className="flex justify-end mb-6">
            <div className="bg-indigo-600 text-white rounded-[1.5rem] rounded-tr-sm px-5 py-4 max-w-sm shadow-xl shadow-indigo-500/20">
              <p className="text-[10px] font-black uppercase tracking-widest opacity-60 mb-1.5">User Directive</p>
              <p className="text-sm font-bold leading-relaxed">{featureName || 'New UPI Feature Canvas'}</p>
              <p className="text-[10px] font-black uppercase tracking-widest opacity-40 mt-2">Policy Analysis Protocol Active</p>
            </div>
          </div>

          {/* Agent messages */}
          {messages.slice(0, visibleCount).map((msg, i) => (
            <ChatBubble key={msg.id} msg={msg} isNew={i === visibleCount - 1} />
          ))}

          {/* Typing indicator */}
          {showTyping && visibleCount < messages.length && <TypingIndicator />}
        </div>

        <div className="mt-5 text-center text-[10px] font-black text-slate-300 uppercase tracking-[0.2em] flex-shrink-0 animate-pulse">
          Canvas manifest will mount automatically · NPCI AI Orchestrator
        </div>
      </div>
    </div>
  );
}
