import { useEffect, useState } from 'react'
import { generateCanvas, regenerateSection, updateSectionManually } from '../api/client'
import useSessionStore from '../store/sessionStore'
import SectionEditor from '../components/SectionEditor'
import DownloadButtons from '../components/DownloadButtons'

function SkeletonSection() {
  return (
    <div className="card p-5 space-y-3 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="h-4 bg-slate-200 dark:bg-navy-700 rounded-lg w-1/4" />
        <div className="flex gap-2">
          <div className="h-7 w-14 bg-slate-200 dark:bg-navy-700 rounded-lg" />
          <div className="h-7 w-20 bg-slate-200 dark:bg-navy-700 rounded-lg" />
        </div>
      </div>
      <div className="h-3 bg-slate-100 dark:bg-navy-800 rounded w-full" />
      <div className="h-3 bg-slate-100 dark:bg-navy-800 rounded w-4/5" />
      <div className="h-3 bg-slate-100 dark:bg-navy-800 rounded w-3/4" />
    </div>
  )
}

export default function ProductCanvas() {
  const [autoStarted, setAutoStarted] = useState(false)

  const {
    sessionId,
    canvas, canvasStatus, canvasVersions,
    setCanvasState,
    loading, setLoading, error, setError, clearError,
  } = useSessionStore()

  useEffect(() => {
    if (!autoStarted && !canvas && sessionId) {
      setAutoStarted(true)
      handleGenerate()
    }
  }, [sessionId])

  const handleGenerate = async () => {
    clearError()
    setLoading(true)
    try {
      const res = await generateCanvas(sessionId)
      setCanvasState(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleRegenerate = async (sectionKey, instructions) => {
    clearError()
    setLoading(true)
    try {
      const res = await regenerateSection(sessionId, sectionKey, instructions || null)
      setCanvasState(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async (sectionKey, content) => {
    clearError()
    setLoading(true)
    try {
      const res = await updateSectionManually(sessionId, sectionKey, content)
      setCanvasState(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  const isReady = canvasStatus === 'ready'

  return (
    <div className="flex flex-col flex-1 min-h-0 w-full">
      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden pr-1 space-y-5">
      {/* ── Status Row ────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {canvasVersions.length > 0 && (
            <span className="status-badge bg-slate-100 dark:bg-navy-800 text-slate-500 dark:text-slate-400">
              Canvas v{canvas?.version}
            </span>
          )}
          {isReady && (
            <span className="status-badge bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Canvas Ready
            </span>
          )}
          {loading && canvas && (
            <span className="status-badge bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-400 animate-pulse">
              <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Updating...
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {isReady && sessionId && <DownloadButtons sessionId={sessionId} />}
          {canvas && (
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="btn-secondary gap-2"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
              Regenerate All
            </button>
          )}
        </div>
      </div>

      {/* ── Loading Skeleton ──────────────────────────────── */}
      {loading && !canvas && (
        <div className="space-y-3 animate-fade-in">
          <div className="card p-5 flex items-center gap-4 mb-2">
            <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center shrink-0">
              <svg className="w-5 h-5 text-indigo-600 dark:text-indigo-400 animate-pulse-slow" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">Generating Product Canvas...</p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                Synthesizing research into structured product sections. This may take a moment.
              </p>
            </div>
          </div>
          {[...Array(5)].map((_, i) => <SkeletonSection key={i} />)}
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

      {/* ── Canvas Sections ───────────────────────────────── */}
      {canvas?.sections && (
        <div className="space-y-3">
          {canvas.sections.map((section) => (
            <SectionEditor
              key={section.key}
              section={section}
              onRegenerate={handleRegenerate}
              onSave={handleSave}
              disabled={loading}
            />
          ))}
        </div>
      )}
      </div>

      {/* ── Bottom Navigation ─────────────────────────────── */}
      <div className="shrink-0 mt-4 pt-4 border-t border-slate-100 dark:border-navy-700 flex justify-between items-center">
        <button
          onClick={() => useSessionStore.getState().setStep('research')}
          className="btn-ghost"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
          </svg>
          Back to Research
        </button>

        {isReady && (
          <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
            <svg className="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
            Canvas complete — download above to export
          </div>
        )}
      </div>
    </div>
  )
}
