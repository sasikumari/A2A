import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function SectionEditor({ section, onRegenerate, onSave, disabled }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(section.content)
  const [regenInstructions, setRegenInstructions] = useState('')
  const [showRegenPanel, setShowRegenPanel] = useState(false)

  const handleSave = () => {
    onSave(section.key, draft)
    setEditing(false)
  }

  const handleRegen = () => {
    onRegenerate(section.key, regenInstructions)
    setShowRegenPanel(false)
    setRegenInstructions('')
  }

  return (
    <div className="card overflow-hidden">
      {/* ── Section Header ─────────────────────────────── */}
      <div className="flex items-center justify-between px-5 py-3.5
                      bg-slate-50 dark:bg-navy-800/50 border-b border-slate-200 dark:border-navy-600/50">
        <div className="flex items-center gap-2.5">
          <div className="w-1 h-5 rounded-full bg-brand-500" />
          <div>
            <h3 className="font-semibold text-slate-800 dark:text-slate-200 text-sm">{section.title}</h3>
            <span className="text-xs text-slate-400 dark:text-slate-500">Version {section.version}</span>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {!editing && (
            <button
              onClick={() => { setEditing(true); setDraft(section.content) }}
              disabled={disabled}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                         bg-white dark:bg-navy-800 border border-slate-200 dark:border-navy-600
                         text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-navy-700
                         disabled:opacity-40 transition-all"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125" />
              </svg>
              Edit
            </button>
          )}
          <button
            onClick={() => setShowRegenPanel(!showRegenPanel)}
            disabled={disabled}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                       disabled:opacity-40 transition-all
                       ${showRegenPanel
                         ? 'bg-brand-600 text-white border border-brand-600'
                         : 'bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800 text-brand-700 dark:text-brand-400 hover:bg-brand-100 dark:hover:bg-brand-900/40'
                       }`}
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
            Regenerate
          </button>
        </div>
      </div>

      {/* ── Regenerate Panel ───────────────────────────── */}
      {showRegenPanel && (
        <div className="px-5 py-3 border-b border-brand-100 dark:border-brand-900/50
                        bg-brand-50/50 dark:bg-brand-950/20 flex gap-2 items-center animate-fade-in">
          <div className="flex-1 flex items-center gap-2 bg-white dark:bg-navy-800
                          border border-brand-200 dark:border-brand-800 rounded-xl px-3 py-2">
            <svg className="w-4 h-4 text-brand-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
            <input
              className="flex-1 text-sm bg-transparent text-slate-800 dark:text-slate-200
                         placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none"
              placeholder="Optional instructions for regeneration..."
              value={regenInstructions}
              onChange={(e) => setRegenInstructions(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleRegen() }}
            />
          </div>
          <button
            onClick={handleRegen}
            disabled={disabled}
            className="btn-primary py-2 text-xs"
          >
            Run
          </button>
          <button
            onClick={() => setShowRegenPanel(false)}
            className="btn-ghost py-2 text-xs"
          >
            Cancel
          </button>
        </div>
      )}

      {/* ── Content ────────────────────────────────────── */}
      <div className="px-5 py-5">
        {editing ? (
          <div className="animate-fade-in">
            <textarea
              className="input-field h-64 font-mono text-xs resize-y"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
            <div className="flex gap-2 mt-3 justify-end">
              <button
                onClick={() => setEditing(false)}
                className="btn-secondary text-xs py-2"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="btn-primary text-xs py-2"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                </svg>
                Save Changes
              </button>
            </div>
          </div>
        ) : (
          <div className="prose prose-sm max-w-none
                          prose-headings:text-slate-900 dark:prose-headings:text-slate-100
                          prose-p:text-slate-700 dark:prose-p:text-slate-300
                          prose-strong:text-slate-900 dark:prose-strong:text-slate-100
                          prose-li:text-slate-700 dark:prose-li:text-slate-300
                          prose-code:text-brand-600 dark:prose-code:text-brand-400
                          prose-code:bg-brand-50 dark:prose-code:bg-brand-900/20
                          prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded
                          prose-blockquote:border-brand-400 prose-blockquote:text-slate-600 dark:prose-blockquote:text-slate-400">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {section.content || '_Content not generated yet._'}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}
