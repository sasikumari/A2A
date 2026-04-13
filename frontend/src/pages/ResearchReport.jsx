import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { generateResearch, submitResearchFeedback } from '../api/client'
import useSessionStore from '../store/sessionStore'

function SkeletonCard() {
  return (
    <div className="card p-4 space-y-3 animate-pulse">
      <div className="h-4 bg-slate-200 dark:bg-navy-700 rounded-lg w-1/3" />
      <div className="h-3 bg-slate-100 dark:bg-navy-800 rounded w-full" />
      <div className="h-3 bg-slate-100 dark:bg-navy-800 rounded w-5/6" />
    </div>
  )
}

export default function ResearchReport() {
  const [feedback, setFeedback] = useState('')
  const [expandedSection, setExpandedSection] = useState(null)
  const [autoStarted, setAutoStarted] = useState(false)

  const {
    sessionId,
    researchReport, researchStatus, researchVersions,
    setResearchState,
    loading, setLoading, error, setError, clearError,
  } = useSessionStore()

  useEffect(() => {
    if (!autoStarted && !researchReport && sessionId) {
      setAutoStarted(true)
      handleGenerate()
    }
  }, [sessionId])

  const handleGenerate = async () => {
    clearError()
    setLoading(true)
    try {
      const res = await generateResearch(sessionId)
      setResearchState(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleFeedback = async () => {
    if (!feedback.trim()) return
    clearError()
    setLoading(true)
    try {
      const res = await submitResearchFeedback(sessionId, feedback.trim())
      setResearchState(res.data)
      setFeedback('')
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  const isGenerating = loading && !researchReport
  const isReady = researchStatus === 'ready'

  return (
    <div className="flex flex-col flex-1 min-h-0 w-full">
      {/* Scrollable report body (summary + sections); footer stays pinned */}
      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden pr-1 space-y-5">
      {/* ── Status + Version Row ──────────────────────────── */}
      <div className="flex items-center gap-3">
        {researchVersions.length > 0 && (
          <span className="status-badge bg-slate-100 dark:bg-navy-800 text-slate-500 dark:text-slate-400">
            v{researchReport?.version} of {researchVersions.length}
          </span>
        )}
        {isReady && (
          <span className="status-badge bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            Report Ready
          </span>
        )}
        {(researchStatus === 'generating' || researchStatus === 'regenerating') && (
          <span className="status-badge bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 animate-pulse">
            <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            {researchStatus === 'generating' ? 'Generating...' : 'Regenerating...'}
          </span>
        )}
      </div>

      {/* ── Loading Skeleton ──────────────────────────────── */}
      {isGenerating && (
        <div className="space-y-3 animate-fade-in">
          <div className="card p-5 flex items-center gap-4 mb-4">
            <div className="w-10 h-10 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center shrink-0">
              <svg className="w-5 h-5 text-brand-600 dark:text-brand-400 animate-pulse-slow" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 1-6.23-.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21a48.25 48.25 0 0 1-8.135-.687c-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">Running deep research...</p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                Searching knowledge base, regulatory documents, and domain context. This may take a moment.
              </p>
            </div>
          </div>
          {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {/* ── Error ─────────────────────────────────────────── */}
      {error && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-50 dark:bg-red-900/20
                        border border-red-200 dark:border-red-800 text-sm text-red-600 dark:text-red-400">
          <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
          {error}
        </div>
      )}

      {/* ── Executive Summary ─────────────────────────────── */}
      {researchReport?.summary && (
        <div className="card p-5 border-l-4 border-l-brand-500">
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-4 h-4 text-brand-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
            </svg>
            <span className="text-xs font-bold text-brand-600 dark:text-brand-400 uppercase tracking-wider">Executive Summary</span>
          </div>
          <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{researchReport.summary}</p>
        </div>
      )}

      {/* ── Research Sections ─────────────────────────────── */}
      {researchReport?.sections && (
        <div className="space-y-2">
          {loading && researchReport && (
            <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-brand-50 dark:bg-brand-900/20
                            border border-brand-200 dark:border-brand-800 text-sm text-brand-700 dark:text-brand-400 animate-pulse">
              <svg className="w-4 h-4 animate-spin shrink-0" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Refining report...
            </div>
          )}

          {researchReport.sections.map((section, i) => (
            <div key={i} className="card overflow-hidden">
              <button
                className="w-full flex items-center justify-between px-5 py-4 text-left
                           hover:bg-slate-50 dark:hover:bg-navy-800/50 transition-colors"
                onClick={() => setExpandedSection(expandedSection === i ? null : i)}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold shrink-0
                    ${expandedSection === i
                      ? 'bg-brand-600 text-white'
                      : 'bg-slate-100 dark:bg-navy-800 text-slate-500 dark:text-slate-400'
                    }`}>
                    {i + 1}
                  </div>
                  <span className="font-semibold text-sm text-slate-800 dark:text-slate-200">{section.title}</span>
                </div>
                <svg
                  className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${expandedSection === i ? 'rotate-180' : ''}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                </svg>
              </button>

              {expandedSection === i && (
                <div className="px-5 pb-5 border-t border-slate-100 dark:border-navy-700 pt-4 animate-fade-in">
                  <div className="prose prose-sm max-w-none prose-dark text-slate-700 dark:text-slate-300
                                  prose-headings:text-slate-900 dark:prose-headings:text-slate-100
                                  prose-strong:text-slate-900 dark:prose-strong:text-slate-100
                                  prose-li:text-slate-700 dark:prose-li:text-slate-300
                                  prose-code:text-brand-600 dark:prose-code:text-brand-400">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.content}</ReactMarkdown>
                  </div>
                  {section.sources?.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-slate-100 dark:border-navy-700">
                      <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">
                        Sources
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {[...new Set(section.sources)].map((src, j) => (
                          <span key={j}
                            className="text-xs bg-slate-100 dark:bg-navy-800 text-slate-500 dark:text-slate-400
                                       px-2.5 py-1 rounded-full border border-slate-200 dark:border-navy-600">
                            {src}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      </div>

      {/* ── Feedback + Navigation ─────────────────────────── */}
      {researchReport && (
        <div className="shrink-0 mt-4 space-y-3 pt-4 border-t border-slate-100 dark:border-navy-700">
          <div className="flex gap-2 items-end bg-white dark:bg-navy-800
                          border border-slate-200 dark:border-navy-600
                          rounded-2xl p-2 shadow-sm focus-within:ring-2 focus-within:ring-brand-500/30
                          focus-within:border-brand-400 transition-all">
            <textarea
              className="flex-1 bg-transparent text-sm text-slate-900 dark:text-slate-100
                         placeholder-slate-400 dark:placeholder-slate-500
                         resize-none focus:outline-none px-2 py-1.5 min-h-[40px] max-h-28"
              rows={2}
              placeholder="Provide feedback to refine the report... (e.g. 'Add more detail on RBI compliance')"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              disabled={loading}
            />
            <button
              onClick={handleFeedback}
              disabled={loading || !feedback.trim()}
              className="shrink-0 w-10 h-10 rounded-xl bg-brand-600 hover:bg-brand-700
                         disabled:opacity-40 disabled:cursor-not-allowed
                         flex items-center justify-center text-white transition-all active:scale-95"
            >
              {loading ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
                </svg>
              )}
            </button>
          </div>

          <div className="flex justify-between items-center">
            <button
              onClick={() => useSessionStore.getState().setStep('requirement')}
              className="btn-ghost"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
              </svg>
              Back
            </button>
            <button
              onClick={() => useSessionStore.getState().setStep('canvas')}
              disabled={!isReady}
              className="btn-primary"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
              </svg>
              Generate Product Canvas
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
