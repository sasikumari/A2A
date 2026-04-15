import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { generateCanvas, regenerateSection, updateSectionManually } from '../api/client'
import useSessionStore from '../store/sessionStore'
import DownloadButtons from '../components/DownloadButtons'

// ── Template grid layout (mirrors V1.2_Canvas_ProductBuild) ──────────────── //
const GRID = [
  ['feature'],                                           // row 1 — full width
  ['need', 'market_view', 'scalability'],                // row 2
  ['validation', 'product_operating', 'product_comms'], // row 3
  ['pricing', 'potential_risks', 'compliance'],          // row 4
]

const SECTION_META = {
  feature:          { number: 1, title: 'Feature',                           subtitle: 'Explain the feature for a layman' },
  need:             { number: 2, title: 'Need',                               subtitle: 'Why should we do this?' },
  market_view:      { number: 3, title: 'Market View' },
  scalability:      { number: 4, title: 'Scalability' },
  validation:       { number: 5, title: 'Validation' },
  product_operating:{ number: 6, title: 'Product Operating' },
  product_comms:    { number: 7, title: 'Product Comms',                      subtitle: 'external + internal' },
  pricing:          { number: 8, title: 'Pricing' },
  potential_risks:  { number: 9, title: 'Potential Risks' },
  compliance:       { number: 10, title: 'Compliance' },
}

// ── Edit modal ─────────────────────────────────────────────────────────────── //

function EditModal({ section, onClose, onSave, onRegenerate, disabled }) {
  const [tab, setTab]           = useState('edit')   // 'edit' | 'regen'
  const [content, setContent]   = useState(section.content)
  const [instructions, setInst] = useState('')
  const meta = SECTION_META[section.key] || {}

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
         onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="w-full max-w-2xl bg-white dark:bg-navy-900 rounded-2xl shadow-2xl
                      border border-slate-200 dark:border-navy-700 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 dark:border-navy-700 shrink-0">
          <div>
            <p className="text-xs font-bold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
              {meta.number}. {meta.title}
            </p>
            {meta.subtitle && <p className="text-xs text-slate-400 mt-0.5">{meta.subtitle}</p>}
          </div>
          <button onClick={onClose}
                  className="w-7 h-7 flex items-center justify-center rounded-lg text-slate-400
                             hover:bg-slate-100 dark:hover:bg-navy-800 transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-5 pt-3 shrink-0">
          {['edit', 'regen'].map(t => (
            <button key={t} onClick={() => setTab(t)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors
                      ${tab === t ? 'bg-brand-600 text-white' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-navy-800'}`}>
              {t === 'edit' ? 'Manual Edit' : 'AI Regenerate'}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 min-h-0 overflow-y-auto px-5 py-4">
          {tab === 'edit' ? (
            <textarea
              className="w-full h-72 text-sm text-slate-800 dark:text-slate-200 bg-slate-50 dark:bg-navy-800
                         border border-slate-200 dark:border-navy-600 rounded-xl p-3 resize-none
                         focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 font-mono"
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Optionally provide instructions to guide the AI regeneration:
              </p>
              <textarea
                className="w-full h-28 text-sm text-slate-800 dark:text-slate-200 bg-slate-50 dark:bg-navy-800
                           border border-slate-200 dark:border-navy-600 rounded-xl p-3 resize-none
                           focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400"
                placeholder="e.g. Focus more on RBI compliance aspects, add specific data points..."
                value={instructions}
                onChange={(e) => setInst(e.target.value)}
              />
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-navy-800 border border-slate-100 dark:border-navy-700">
                <p className="text-xs font-semibold text-slate-500 mb-2">Current content preview:</p>
                <div className="text-xs text-slate-600 dark:text-slate-400 line-clamp-4 leading-relaxed">
                  {section.content.slice(0, 300)}...
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-slate-100 dark:border-navy-700 shrink-0">
          <button onClick={onClose} className="btn-ghost text-sm py-1.5 px-3">Cancel</button>
          {tab === 'edit' ? (
            <button
              onClick={() => { onSave(section.key, content); onClose() }}
              disabled={disabled || content === section.content}
              className="btn-primary text-sm py-1.5 px-4"
            >
              Save Changes
            </button>
          ) : (
            <button
              onClick={() => { onRegenerate(section.key, instructions || null); onClose() }}
              disabled={disabled}
              className="btn-primary text-sm py-1.5 px-4"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
              Regenerate with AI
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Single canvas cell ─────────────────────────────────────────────────────── //

function CanvasCell({ section, onEdit, disabled }) {
  const meta = SECTION_META[section.key] || {}

  return (
    <div className="group relative flex flex-col bg-white dark:bg-navy-900
                    border-r border-b border-slate-200 dark:border-navy-700
                    last:border-r-0 min-h-0">
      {/* Cell header */}
      <div className="flex items-start justify-between px-3 pt-3 pb-1.5 shrink-0
                      border-b border-slate-100 dark:border-navy-700">
        <div>
          <span className="text-[11px] font-bold text-[#1B3F8F] dark:text-blue-300 leading-tight block">
            {meta.number}. {meta.title}
          </span>
          {meta.subtitle && (
            <span className="text-[10px] text-slate-400 dark:text-slate-500 italic">
              ({meta.subtitle})
            </span>
          )}
        </div>
        <button
          onClick={() => onEdit(section)}
          disabled={disabled}
          className="opacity-0 group-hover:opacity-100 transition-opacity
                     w-6 h-6 flex items-center justify-center rounded-md
                     text-slate-400 hover:bg-brand-50 dark:hover:bg-navy-700 hover:text-brand-600
                     disabled:opacity-0 shrink-0 ml-1"
          title="Edit section"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125" />
          </svg>
        </button>
      </div>

      {/* Cell content */}
      <div className="flex-1 overflow-y-auto px-3 py-2 text-[11px] leading-relaxed
                      text-slate-700 dark:text-slate-300 canvas-cell-content">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: () => null,
            h2: () => null,
            h3: ({ children }) => (
              <p className="font-bold text-[#1B3F8F] dark:text-blue-300 mt-2 mb-0.5 text-[11px]">{children}</p>
            ),
            strong: ({ children }) => (
              <strong className="font-semibold text-[#1B3F8F] dark:text-blue-300">{children}</strong>
            ),
            p: ({ children }) => <p className="mb-1">{children}</p>,
            ul: ({ children }) => <ul className="list-disc ml-3 mb-1 space-y-0.5">{children}</ul>,
            li: ({ children }) => <li className="text-[11px]">{children}</li>,
          }}
        >
          {section.content}
        </ReactMarkdown>
      </div>
    </div>
  )
}

// ── Skeleton ───────────────────────────────────────────────────────────────── //

function CanvasSkeleton() {
  return (
    <div className="flex-1 border border-slate-200 dark:border-navy-700 rounded-xl overflow-hidden animate-pulse">
      {/* Row 1 */}
      <div className="h-24 bg-slate-100 dark:bg-navy-800 border-b border-slate-200 dark:border-navy-700" />
      {/* Row 2 */}
      <div className="grid grid-cols-3 border-b border-slate-200 dark:border-navy-700">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-40 bg-slate-50 dark:bg-navy-900 border-r border-slate-200 dark:border-navy-700 last:border-r-0" />
        ))}
      </div>
      {/* Row 3 */}
      <div className="grid grid-cols-3 border-b border-slate-200 dark:border-navy-700">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-40 bg-slate-100 dark:bg-navy-800 border-r border-slate-200 dark:border-navy-700 last:border-r-0" />
        ))}
      </div>
      {/* Row 4 */}
      <div className="grid grid-cols-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-40 bg-slate-50 dark:bg-navy-900 border-r border-slate-200 dark:border-navy-700 last:border-r-0" />
        ))}
      </div>
    </div>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────── //

export default function ProductCanvas() {
  const [autoStarted, setAutoStarted] = useState(false)
  const [editingSection, setEditingSection] = useState(null)

  const {
    sessionId, structuredOutput,
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

  // Build section lookup from canvas data
  const sectionMap = {}
  canvas?.sections?.forEach(s => { sectionMap[s.key] = s })

  const featureTitle = structuredOutput?.feature_name
    || canvas?.sections?.find(s => s.key === 'feature')?.content?.split('\n')[0]?.replace(/^#+\s*/, '')
    || 'New Feature'

  return (
    <div className="flex flex-col flex-1 min-h-0 w-full">

      {/* ── Top bar ──────────────────────────────────────────── */}
      <div className="shrink-0 flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {canvasVersions.length > 0 && (
            <span className="status-badge bg-slate-100 dark:bg-navy-800 text-slate-500 dark:text-slate-400">
              v{canvas?.version}
            </span>
          )}
          {isReady && !loading && (
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
            <button onClick={handleGenerate} disabled={loading} className="btn-secondary gap-2 text-sm py-1.5">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
              Regenerate All
            </button>
          )}
        </div>
      </div>

      {/* ── Error ─────────────────────────────────────────────── */}
      {error && (
        <div className="shrink-0 flex items-center gap-2 px-4 py-3 mb-3 rounded-xl
                        bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800
                        text-sm text-red-600 dark:text-red-400">
          <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
          {error}
        </div>
      )}

      {/* ── Loading state ─────────────────────────────────────── */}
      {loading && !canvas && (
        <div className="shrink-0 flex items-center gap-4 card p-4 mb-3 animate-fade-in">
          <div className="w-9 h-9 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center shrink-0">
            <svg className="w-5 h-5 text-brand-600 dark:text-brand-400 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">Generating Product Canvas...</p>
            <p className="text-xs text-slate-400 mt-0.5">Filling all 10 sections of the NPCI Build Framework</p>
          </div>
        </div>
      )}

      {/* ── Canvas Grid (template layout) ─────────────────────── */}
      {canvas?.sections ? (
        <div className="flex-1 min-h-0 overflow-auto">
          {/* "Build framework for ___" header */}
          <div className="text-[11px] font-semibold text-[#1B3F8F] dark:text-blue-300 mb-2 px-1">
            Build framework for &nbsp;
            <span className="border-b border-[#1B3F8F] dark:border-blue-400 pb-px">
              {featureTitle}
            </span>
          </div>

          {/* Grid table */}
          <div className="border border-slate-200 dark:border-navy-700 rounded-xl overflow-hidden text-[11px]">
            {GRID.map((rowKeys, rowIdx) => (
              <div
                key={rowIdx}
                className={`grid border-b border-slate-200 dark:border-navy-700 last:border-b-0
                  ${rowKeys.length === 1 ? 'grid-cols-1' : 'grid-cols-3'}
                  ${rowIdx % 2 === 0 ? 'bg-white dark:bg-navy-900' : 'bg-slate-50/50 dark:bg-navy-950/30'}`}
                style={{ minHeight: rowIdx === 0 ? '80px' : '160px' }}
              >
                {rowKeys.map((key) => {
                  const section = sectionMap[key]
                  if (!section) return (
                    <div key={key} className="border-r border-slate-200 dark:border-navy-700 last:border-r-0 p-3 animate-pulse">
                      <div className="h-3 bg-slate-200 dark:bg-navy-700 rounded w-1/2 mb-2" />
                      <div className="h-2 bg-slate-100 dark:bg-navy-800 rounded w-full" />
                    </div>
                  )
                  return (
                    <CanvasCell
                      key={key}
                      section={section}
                      onEdit={setEditingSection}
                      disabled={loading}
                    />
                  )
                })}
              </div>
            ))}
          </div>

          <p className="text-[10px] text-slate-400 dark:text-slate-500 text-center mt-2">
            Hover over any cell to edit · Click "Edit" to modify manually or regenerate with AI
          </p>
        </div>
      ) : (
        !loading && <CanvasSkeleton />
      )}

      {/* ── Bottom nav ────────────────────────────────────────── */}
      <div className="shrink-0 mt-3 pt-3 border-t border-slate-100 dark:border-navy-700 flex justify-between items-center">
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
          <button
            onClick={() => useSessionStore.getState().setStep('documents')}
            className="btn-primary gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.429 9.75 2.25 12l4.179 2.25m0-4.5 5.571 3 5.571-3m-11.142 0L2.25 7.5 12 2.25l9.75 5.25-4.179 2.25m0 0L21.75 12l-4.179 2.25m0 0 4.179 2.25L12 21.75 2.25 16.5l4.179-2.25m11.142 0-5.571 3-5.571-3" />
            </svg>
            Generate Documents
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
            </svg>
          </button>
        )}
      </div>

      {/* ── Edit Modal ─────────────────────────────────────────── */}
      {editingSection && (
        <EditModal
          section={editingSection}
          onClose={() => setEditingSection(null)}
          onSave={handleSave}
          onRegenerate={handleRegenerate}
          disabled={loading}
        />
      )}
    </div>
  )
}
