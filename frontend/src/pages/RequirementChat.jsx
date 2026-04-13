import { useState, useRef, useEffect } from 'react'
import { createSession, startRequirement, respondRequirement } from '../api/client'
import useSessionStore from '../store/sessionStore'
import ChatBubble from '../components/ChatBubble'

function TypingIndicator() {
  return (
    <div className="flex items-end gap-2.5 mb-4 animate-fade-in">
      <div className="w-8 h-8 rounded-full bg-accent-500
                      flex items-center justify-center text-white text-[10px] font-bold shrink-0">
        AI
      </div>
      <div className="bg-white dark:bg-navy-800 border border-slate-200 dark:border-navy-600
                      rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
        <div className="flex gap-1 items-center h-4">
          {[0, 150, 300].map((delay) => (
            <span key={delay} className="w-2 h-2 bg-brand-400 rounded-full animate-bounce"
                  style={{ animationDelay: `${delay}ms` }} />
          ))}
        </div>
      </div>
    </div>
  )
}

export default function RequirementChat() {
  const [input, setInput]         = useState('')
  // Optimistic user message shown instantly while API is in-flight
  const [pendingMsg, setPendingMsg] = useState('')
  const bottomRef = useRef(null)

  const {
    sessionId, setSessionId,
    requirementMessages, requirementStatus, questionsAsked, structuredOutput,
    setRequirementState,
    loading, setLoading, error, setError, clearError,
    setStep,
  } = useSessionStore()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [requirementMessages, pendingMsg, loading])

  const handleSend = async () => {
    const msg = input.trim()
    if (!msg || loading) return

    // ① Clear input & show user message immediately — before any async work
    setInput('')
    setPendingMsg(msg)
    clearError()
    setLoading(true)

    try {
      if (requirementStatus === 'idle') {
        // First ever message — create session if needed, then start requirement
        let sid = sessionId
        if (!sid) {
          const res = await createSession()
          sid = res.data.session_id
          setSessionId(sid)
        }
        const res = await startRequirement(sid, msg)
        setRequirementState(res.data)
      } else {
        // Follow-up answer to a clarifying question
        const res = await respondRequirement(sessionId, msg)
        setRequirementState(res.data)
      }
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      // ② Clear pending once server messages (which include the user turn) are set
      setPendingMsg('')
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const isComplete  = requirementStatus === 'complete'
  const isClarifying = requirementStatus === 'clarifying'
  // Chat is "active" as soon as user sends first message
  const hasServerMessages = requirementMessages.length > 0
  const showChat = hasServerMessages || !!pendingMsg

  return (
    <div className="flex flex-col flex-1 min-h-0 w-full">

      {/* ── Chat area ─────────────────────────────────────── */}
      <div className="flex-1 min-h-0 overflow-y-auto">

        {/* Empty / welcome state — disappears the moment user hits send */}
        {!showChat && (
          <div className="flex flex-col items-center justify-center h-full min-h-64 animate-fade-in">
            <div className="w-14 h-14 rounded-2xl bg-brand-600 flex items-center justify-center mb-5 shadow-sm text-white">
              <svg viewBox="0 0 24 24" className="w-8 h-8" fill="none" stroke="currentColor"
                   strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="2" x2="12" y2="5" />
                <circle cx="12" cy="1.5" r="1" fill="currentColor" stroke="none" />
                <rect x="4" y="5" width="16" height="12" rx="3" />
                <circle cx="9"  cy="11" r="1.5" fill="currentColor" stroke="none" />
                <circle cx="15" cy="11" r="1.5" fill="currentColor" stroke="none" />
                <path d="M9 14.5 Q12 16.5 15 14.5" strokeWidth={1.4} />
                <path d="M8 17 v2 M16 17 v2" /><path d="M6 19 h12" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-slate-800 dark:text-slate-100 mb-1">
              What would you like to build?
            </h2>
            <p className="text-sm text-slate-400 dark:text-slate-500">
              Describe a feature and I'll ask a few questions to shape it.
            </p>
          </div>
        )}

        {/* Messages from server + pending optimistic message */}
        {showChat && (
          <div className="space-y-1">
            {requirementMessages.map((msg, i) => (
              <ChatBubble key={i} role={msg.role} content={msg.content} />
            ))}
            {/* Show user's message immediately while API is processing */}
            {pendingMsg && (
              <ChatBubble role="user" content={pendingMsg} />
            )}
          </div>
        )}

        {/* AI typing indicator — shown while waiting for response */}
        {loading && <TypingIndicator />}

        <div ref={bottomRef} />
      </div>

      {/* ── Progress bar ──────────────────────────────────── */}
      {isClarifying && (
        <div className="flex items-center gap-3 py-2 shrink-0">
          <div className="flex-1 h-1 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-accent-500 rounded-full transition-all duration-500"
              style={{ width: `${(questionsAsked / 5) * 100}%` }}
            />
          </div>
          <span className="text-xs text-slate-400 shrink-0">{questionsAsked} / 5 questions</span>
        </div>
      )}
      {isComplete && !loading && (
        <div className="flex items-center gap-2 py-2 shrink-0">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
            Requirements complete
          </span>
        </div>
      )}

      {/* ── Error ─────────────────────────────────────────── */}
      {error && (
        <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl
                        bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800
                        text-sm text-red-600 dark:text-red-400 mb-2 shrink-0">
          <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
          {error}
        </div>
      )}

      {/* ── Input bar ─────────────────────────────────────── */}
      {!isComplete && (
        <div className="shrink-0 pt-2">
          <div className="flex gap-2 items-end
                          bg-white dark:bg-navy-800
                          border border-slate-200 dark:border-navy-600
                          rounded-2xl p-2 shadow-sm
                          focus-within:ring-2 focus-within:ring-brand-600/20
                          focus-within:border-brand-500 transition-all">
            <textarea
              className="flex-1 bg-transparent text-sm text-slate-900 dark:text-slate-100
                         placeholder-slate-400 dark:placeholder-slate-500
                         resize-none focus:outline-none px-2 py-1.5 min-h-[40px] max-h-32"
              rows={2}
              placeholder={
                requirementStatus === 'idle'
                  ? 'Describe the feature you want to build...'
                  : 'Type your answer...'
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="shrink-0 w-9 h-9 rounded-xl bg-brand-600 hover:bg-brand-700
                         disabled:opacity-40 disabled:cursor-not-allowed
                         flex items-center justify-center text-white transition-all active:scale-95"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
              </svg>
            </button>
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-600 text-center mt-1.5">
            <kbd className="font-mono bg-slate-100 dark:bg-navy-800 px-1 rounded text-[10px] text-slate-500">Enter</kbd> to send ·{' '}
            <kbd className="font-mono bg-slate-100 dark:bg-navy-800 px-1 rounded text-[10px] text-slate-500">Shift+Enter</kbd> for new line
          </p>
        </div>
      )}

      {/* ── Complete state ────────────────────────────────── */}
      {isComplete && (
        <div className="shrink-0 mt-4 space-y-3 animate-slide-up">
          {structuredOutput && (
            <details className="group card p-4 cursor-pointer">
              <summary className="flex items-center justify-between text-sm font-semibold
                                  text-slate-700 dark:text-slate-300 list-none">
                <span className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" />
                  </svg>
                  Structured Output
                </span>
                <svg className="w-4 h-4 text-slate-400 group-open:rotate-180 transition-transform"
                     fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                </svg>
              </summary>
              <pre className="mt-3 text-xs text-slate-600 dark:text-slate-400 overflow-x-auto
                              bg-slate-50 dark:bg-slate-800/50 p-3 rounded-lg">
                {JSON.stringify(structuredOutput, null, 2)}
              </pre>
            </details>
          )}
          <button
            onClick={() => setStep('research')}
            className="btn-primary w-full py-3 justify-center text-base"
          >
            Proceed to Deep Research
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
            </svg>
          </button>
        </div>
      )}
    </div>
  )
}
