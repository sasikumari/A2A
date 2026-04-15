import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Send, Loader2, Sparkles, User,
  Brain, RefreshCw, ChevronRight, SkipForward
} from 'lucide-react';

interface ClarifyViewProps {
  prompt: string;
  onClarified: (finalContext: string) => void;
}

type MessageRole = 'user' | 'agent';

interface Message {
  id: string;
  role: MessageRole;
  text: string;
  isTyping?: boolean;
}

interface ClarifyResponse {
  message_to_pm?: string;
  clarification_questions?: string[];
  needs_clarification?: boolean;
  confident?: boolean;
}

// ── NPCI skill-based fallback questions — always ask these if LLM returns nothing
const NPCI_SKILL_QUESTIONS = [
  'What are the transaction limits (e.g. per-transaction cap, daily limit)? Any existing NPCI circular governing this?',
  'Who are the primary ecosystem participants — which banks, PSPs, or merchant categories must be onboarded first?',
  'What is the core user-facing problem this solves? How is this differentiated from existing UPI flows?',
  'Are there specific fraud, infosec, or consent guardrails that must be built in?',
  'What is your target launch timeline and the MVP scope for the initial pilot?',
];

const SCAN_TASKS = [
  'Scanning NPCI Circulars…',
  'Reviewing RBI Digital Payment Guidelines…',
  'Analyzing Ecosystem Participant Impact…',
  'Scoping Regulatory Compliance (OC-228)…',
  'Mapping 10-Section Canvas Requirements…',
  'Identifying Skill Coverage Gaps…',
];

function AgentThinkingBubble() {
  const [taskIdx, setTaskIdx] = useState(0);
  const [dots, setDots] = useState('');
  useEffect(() => {
    const t1 = setInterval(() => setDots(d => (d.length >= 3 ? '' : d + '.')), 400);
    const t2 = setInterval(() => setTaskIdx(i => (i + 1) % SCAN_TASKS.length), 1800);
    return () => { clearInterval(t1); clearInterval(t2); };
  }, []);
  return (
    <div className="flex flex-col gap-3 p-6 bg-slate-900 text-white rounded-[2.5rem] rounded-tl-lg shadow-2xl shadow-indigo-900/10 max-w-sm">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-white/10 rounded-2xl border border-white/10 flex items-center justify-center flex-shrink-0">
          <Brain className="w-5 h-5 text-indigo-400 animate-spin" />
        </div>
        <span className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-100">
          Titan Agent Analyzing{dots}
        </span>
      </div>
      <div className="flex items-center gap-3 pl-1">
        <RefreshCw className="w-3.5 h-3.5 text-indigo-400 animate-spin flex-shrink-0" />
        <span className="text-[10px] font-black text-indigo-300 uppercase tracking-widest transition-all duration-500">
          {SCAN_TASKS[taskIdx]}
        </span>
      </div>
      <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div className="h-full bg-indigo-500 shadow-[0_0_12px_rgba(99,102,241,0.6)] animate-loading-bar w-2/5" />
      </div>
    </div>
  );
}

function AssistantAvatar() {
  return (
    <div className="w-10 h-10 rounded-[1.25rem] bg-gradient-to-br from-slate-900 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-xl shadow-indigo-900/20 hover:scale-110 transition-transform">
      <Sparkles className="w-5 h-5 text-white" />
    </div>
  );
}

function UserAvatar() {
  return (
    <div className="w-10 h-10 rounded-[1.25rem] bg-slate-100 flex items-center justify-center flex-shrink-0 border border-slate-200 hover:scale-110 transition-transform">
      <User className="w-5 h-5 text-slate-400" />
    </div>
  );
}

function renderText(text: string) {
  return text.split('\n').map((line, i) => {
    if (!line) return <div key={i} className="h-2" />;
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    return (
      <span key={i} className="block leading-relaxed">
        {parts.map((p, j) =>
          p.startsWith('**')
            ? <strong key={j} className="font-black text-slate-900">{p.slice(2, -2)}</strong>
            : p
        )}
      </span>
    );
  });
}

export default function ClarifyView({ prompt, onClarified }: ClarifyViewProps) {
  /**
   * ClarifyView: Phase 1 Orchestrator
   * ---------------------------------
   * This component handles the multi-turn agentic conversation.
   * It interacts with the ReasoningAgent to:
   * 1.  Conduct a PM clarification loop.
   * 2.  Maintain local message history for contextual awareness.
   * 3.  Handle fallbacks for NPCI-specific domain knowledge.
   */
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  // Only allow proceed after user has answered at least once
  const [userTurns, setUserTurns] = useState(0);
  const [agentTurns, setAgentTurns] = useState(0);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const initFiredRef = useRef(false);

  const canProceed = userTurns >= 1;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addMsg = useCallback((role: MessageRole, text: string, isTyping = false) => {
    const id = `${role}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setMessages(prev => [...prev, { id, role, text, isTyping }]);
    return id;
  }, []);

  const removeMsg = useCallback((id: string) => {
    setMessages(prev => prev.filter(m => m.id !== id));
  }, []);

  /** Calls backend and returns an agent reply with guaranteed questions */
  const fetchAgentReply = useCallback(async (currentMessages: Message[]): Promise<string> => {
    const history = currentMessages
      .filter(m => !m.isTyping)
      .map(m => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.text }));

    try {
      const res = await fetch('/agents/clarify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, history }),
      });

      if (!res.ok) throw new Error('API error');
      const json: ClarifyResponse = await res.json();

      const msgText = json.message_to_pm || '';
      const qs = json.clarification_questions ?? [];

      // If LLM returned questions — great, use them
      if (qs.length > 0) {
        const qList = qs.slice(0, 3).map((q, i) => `${i + 1}. ${q}`).join('\n');
        return msgText
          ? `${msgText}\n\n${qList}`
          : `Here are a few things I need to clarify before building the canvas:\n\n${qList}`;
      }

      // If LLM returned confident immediately on first call (no user turn yet), 
      // override with domain-specific NPCI questions
      if (history.filter(h => h.role === 'user').length === 0) {
        const fallbackQs = NPCI_SKILL_QUESTIONS.slice(0, 3)
          .map((q, i) => `${i + 1}. ${q}`)
          .join('\n');
        const intro = msgText || "I've analyzed your request against the NPCI Product Canvas framework. To make the canvas truly precise, a few key details are needed:";
        return `${intro}\n\n${fallbackQs}`;
      }

      // User has already replied — just return the agent's ack
      return msgText || "Thanks for the clarification. I now have enough context to build a complete 10-section canvas. Ready when you are!";
    } catch {
      // Network / parse error — return skill-based fallback
      if (agentTurns === 0) {
        const fallbackQs = NPCI_SKILL_QUESTIONS.slice(0, 3)
          .map((q, i) => `${i + 1}. ${q}`)
          .join('\n');
        return `I've reviewed your brief. Let me ask a few NPCI-specific questions to ensure complete canvas coverage:\n\n${fallbackQs}`;
      }
      return "Thanks for the detail. You can now generate the canvas or add more context.";
    }
  }, [prompt, agentTurns]);

  // Initial load — always calls backend and forces questions on first turn
  useEffect(() => {
    if (initFiredRef.current) return;
    initFiredRef.current = true;

    const init = async () => {
      setLoading(true);
      const typingId = addMsg('agent', '', true);
      const reply = await fetchAgentReply([]);
      removeMsg(typingId);
      addMsg('agent', reply);
      setAgentTurns(1);
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 200);
    };
    init();
  }, [addMsg, removeMsg, fetchAgentReply]);

  // User sends a message → agent responds
  const handleSend = useCallback(async () => {
    const val = inputValue.trim();
    if (!val || loading) return;
    setInputValue('');

    // Add user message
    const userMsgId = addMsg('user', val);
    const newUserTurns = userTurns + 1;
    setUserTurns(newUserTurns);
    setLoading(true);

    // Snapshot messages including the new user message for history
    const snapshot: Message[] = [];
    setMessages(prev => {
      const updated = [...prev];
      snapshot.push(...updated.filter(m => !m.isTyping));
      return updated;
    });

    const typingId = addMsg('agent', '', true);

    // Small delay so typing indicator renders
    await new Promise(r => setTimeout(r, 300));

    const reply = await fetchAgentReply([
      ...snapshot.filter(m => m.id !== userMsgId),
      { id: userMsgId, role: 'user', text: val },
    ]);

    removeMsg(typingId);
    addMsg('agent', reply);
    setAgentTurns(t => t + 1);
    setLoading(false);
    setTimeout(() => inputRef.current?.focus(), 100);
  }, [inputValue, loading, userTurns, addMsg, removeMsg, fetchAgentReply]);

  const handleProceed = () => {
    const ctx = messages
      .filter(m => !m.isTyping)
      .map(m => `[${m.role.toUpperCase()}]: ${m.text}`)
      .join('\n\n');
    onClarified(`INITIAL PROMPT:\n${prompt}\n\nCLARIFICATION SESSION:\n${ctx}`);
  };

  const handleSkip = () => {
    onClarified(`INITIAL PROMPT:\n${prompt}`);
  };

  return (
    <div className="flex h-full bg-slate-50/50">
      <div className="flex flex-col w-full max-w-4xl mx-auto">

        {/* ── Messages ── */}
        <div className="flex-1 overflow-y-auto px-6 py-10 space-y-8 bg-transparent custom-scrollbar">

          {/* Initial user prompt bubble */}
          <div className="flex gap-4 flex-row-reverse">
            <UserAvatar />
            <div className="flex-1 flex flex-col items-end">
              <div className="bg-slate-900 text-white rounded-[2.5rem] rounded-tr-lg px-7 py-5 max-w-md shadow-2xl shadow-indigo-900/10 border border-white/5">
                <p className="text-sm font-black leading-relaxed whitespace-pre-wrap tracking-tight uppercase">
                  {prompt}
                </p>
              </div>
            </div>
          </div>

          {/* Dynamic messages */}
          {messages.map(msg => {
            const isUser = msg.role === 'user';
            return (
              <div key={msg.id} className={`flex gap-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
                {isUser ? <UserAvatar /> : <AssistantAvatar />}
                <div className={`flex-1 min-w-0 ${isUser ? 'flex flex-col items-end' : ''}`}>
                  {isUser ? (
                    <div className="bg-slate-900 text-white rounded-[2.5rem] rounded-tr-lg px-7 py-5 max-w-md shadow-2xl shadow-indigo-900/10 border border-white/5">
                      <p className="text-sm font-black leading-relaxed whitespace-pre-wrap tracking-tight uppercase">
                        {msg.text}
                      </p>
                    </div>
                  ) : (
                    <div className="max-w-2xl bg-white rounded-[2.5rem] rounded-tl-lg p-8 shadow-2xl shadow-slate-200/50 border border-slate-100">
                      {msg.isTyping
                        ? <AgentThinkingBubble />
                        : <div className="text-sm text-slate-800 leading-relaxed font-medium">{renderText(msg.text)}</div>
                      }
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Proceed card — only after user has replied at least once */}
          {canProceed && !loading && (
            <div className="flex gap-4 flex-row">
              <AssistantAvatar />
              <div className="flex-1 min-w-0">
                <div className="max-w-2xl bg-white rounded-[2.5rem] rounded-tl-lg p-7 shadow-2xl shadow-slate-200/50 border border-slate-100">
                  <p className="text-sm text-slate-700 font-bold mb-5 leading-relaxed">
                    I have enough context to build the canvas. You can proceed now, or continue refining.
                  </p>
                  <div className="flex items-center gap-4 flex-wrap">
                    <button
                      onClick={handleProceed}
                      className="flex items-center gap-3 px-7 py-3.5 bg-slate-900 hover:bg-black text-white font-black text-[11px] uppercase tracking-widest rounded-2xl shadow-xl shadow-slate-900/20 transition-all active:scale-95"
                    >
                      <Sparkles className="w-4 h-4" />
                      Generate Product Canvas
                      <ChevronRight className="w-4 h-4" />
                    </button>
                    <button
                      onClick={handleSkip}
                      className="flex items-center gap-2 px-5 py-3 text-[11px] font-black text-slate-400 hover:text-slate-700 uppercase tracking-widest transition-colors border border-slate-200 rounded-2xl hover:border-slate-300"
                    >
                      <SkipForward className="w-3.5 h-3.5" />
                      Skip refinement
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={endRef} />
        </div>

        {/* ── Input bar ── */}
        <div className="flex-shrink-0 px-6 py-8 border-t border-slate-200/60 bg-white/40 backdrop-blur-md">
          <div className={`flex items-end gap-3 bg-white border rounded-[2.5rem] px-6 py-5 shadow-2xl shadow-slate-200/50 transition-all duration-300 ${loading ? 'border-slate-100 opacity-60' : 'border-slate-200 focus-within:border-indigo-400 focus-within:ring-8 focus-within:ring-indigo-500/5'}`}>
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              disabled={loading}
              placeholder={loading ? 'Titan Agent is analyzing…' : 'Answer the question or add more context…'}
              className="flex-1 text-sm text-slate-800 font-bold placeholder-slate-400 focus:outline-none leading-relaxed bg-transparent"
            />
            <button
              onClick={handleSend}
              disabled={loading || !inputValue.trim()}
              className="w-12 h-12 rounded-2xl bg-slate-900 hover:bg-black disabled:bg-slate-100 disabled:cursor-not-allowed flex items-center justify-center shadow-xl shadow-slate-900/20 transition-all active:scale-95 group flex-shrink-0"
            >
              {loading
                ? <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />
                : <Send className="w-5 h-5 text-white group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              }
            </button>
          </div>
          <div className="text-center mt-3">
            <span className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">
              Press Enter to send · NPCI TITAN ENGINE ·&nbsp;
            </span>
            <button
              onClick={handleSkip}
              className="text-[10px] font-black text-indigo-500 hover:text-indigo-700 uppercase tracking-widest underline transition-colors"
            >
              Skip clarification →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
