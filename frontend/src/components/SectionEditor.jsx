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
    <div className="border border-gray-200 rounded-xl mb-4 overflow-hidden shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between bg-gray-50 px-4 py-3 border-b border-gray-200">
        <div>
          <h3 className="font-semibold text-gray-800 text-sm">{section.title}</h3>
          <span className="text-xs text-gray-400">v{section.version}</span>
        </div>
        <div className="flex gap-2">
          {!editing && (
            <button
              onClick={() => { setEditing(true); setDraft(section.content) }}
              disabled={disabled}
              className="text-xs px-3 py-1 rounded-lg bg-white border border-gray-300 text-gray-600 hover:bg-gray-100 disabled:opacity-40"
            >
              Edit
            </button>
          )}
          <button
            onClick={() => setShowRegenPanel(!showRegenPanel)}
            disabled={disabled}
            className="text-xs px-3 py-1 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 hover:bg-blue-100 disabled:opacity-40"
          >
            Regenerate
          </button>
        </div>
      </div>

      {/* Regenerate panel */}
      {showRegenPanel && (
        <div className="bg-blue-50 px-4 py-3 border-b border-blue-100 flex gap-2 items-center">
          <input
            className="flex-1 text-sm border border-blue-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
            placeholder="Optional: specific instructions for regeneration..."
            value={regenInstructions}
            onChange={(e) => setRegenInstructions(e.target.value)}
          />
          <button
            onClick={handleRegen}
            disabled={disabled}
            className="text-sm px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40"
          >
            Go
          </button>
          <button
            onClick={() => setShowRegenPanel(false)}
            className="text-sm px-3 py-2 rounded-lg text-gray-500 hover:text-gray-700"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Content */}
      <div className="px-4 py-4">
        {editing ? (
          <div>
            <textarea
              className="w-full h-64 text-sm font-mono border border-gray-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-400 resize-y"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
            <div className="flex gap-2 mt-2 justify-end">
              <button
                onClick={() => setEditing(false)}
                className="text-sm px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="text-sm px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700"
              >
                Save
              </button>
            </div>
          </div>
        ) : (
          <div className="prose prose-sm max-w-none text-gray-700">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {section.content || '_Not generated yet._'}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}
