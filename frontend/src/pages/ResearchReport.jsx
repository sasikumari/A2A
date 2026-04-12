import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { generateResearch, submitResearchFeedback } from '../api/client'
import useSessionStore from '../store/sessionStore'

export default function ResearchReport() {
  const [feedback, setFeedback] = useState('')
  const [expandedSection, setExpandedSection] = useState(null)
  const [autoStarted, setAutoStarted] = useState(false)

  const {
    sessionId,
    researchReport, researchStatus, researchVersions,
    setResearchState,
    loading, setLoading, error, setError, clearError,
    setStep,
  } = useSessionStore()

  // Auto-trigger research on mount if not yet generated
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

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h2 className="text-lg font-bold text-gray-800">Deep Research Report</h2>
          <p className="text-sm text-gray-500">AI-generated analysis across all requirement sections.</p>
        </div>
        <div className="flex items-center gap-2">
          {researchVersions.length > 0 && (
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
              Version {researchReport?.version} of {researchVersions.length}
            </span>
          )}
          {researchStatus === 'ready' && (
            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">Ready</span>
          )}
          {(researchStatus === 'generating' || researchStatus === 'regenerating') && (
            <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded-full animate-pulse">
              {researchStatus === 'generating' ? 'Generating...' : 'Regenerating...'}
            </span>
          )}
        </div>
      </div>

      {/* Loading skeleton */}
      {loading && !researchReport && (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="animate-pulse bg-gray-100 rounded-xl h-20" />
          ))}
          <p className="text-sm text-center text-gray-400 mt-4">
            Researching across knowledge base and web... this may take a minute.
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-3 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg border border-red-200">
          {error}
        </div>
      )}

      {/* Executive Summary */}
      {researchReport?.summary && (
        <div className="mb-4 bg-blue-50 border border-blue-200 rounded-xl px-4 py-3">
          <p className="text-xs font-semibold text-blue-600 mb-1">Executive Summary</p>
          <p className="text-sm text-gray-700">{researchReport.summary}</p>
        </div>
      )}

      {/* Sections */}
      {researchReport?.sections && (
        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {researchReport.sections.map((section, i) => (
            <div key={i} className="border border-gray-200 rounded-xl overflow-hidden shadow-sm">
              <button
                className="w-full flex justify-between items-center px-4 py-3 bg-gray-50 hover:bg-gray-100 text-left"
                onClick={() => setExpandedSection(expandedSection === i ? null : i)}
              >
                <span className="font-semibold text-sm text-gray-800">{section.title}</span>
                <span className="text-gray-400 text-lg">{expandedSection === i ? '−' : '+'}</span>
              </button>
              {expandedSection === i && (
                <div className="px-4 py-4">
                  <div className="prose prose-sm max-w-none text-gray-700">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.content}</ReactMarkdown>
                  </div>
                  {section.sources?.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <p className="text-xs font-medium text-gray-400 mb-1">Sources</p>
                      <div className="flex flex-wrap gap-1">
                        {[...new Set(section.sources)].map((src, j) => (
                          <span key={j} className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
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

      {/* Feedback + actions */}
      {researchReport && (
        <div className="mt-4 space-y-3">
          <div className="flex gap-2">
            <textarea
              className="flex-1 border border-gray-300 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
              rows={2}
              placeholder="Provide feedback to refine the report (e.g. 'Add more detail on RBI compliance section')..."
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              disabled={loading}
            />
            <button
              onClick={handleFeedback}
              disabled={loading || !feedback.trim()}
              className="px-5 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-40"
            >
              {loading ? '...' : 'Refine'}
            </button>
          </div>
          <div className="flex justify-between">
            <button
              onClick={() => useSessionStore.getState().setStep('requirement')}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              ← Back
            </button>
            <button
              onClick={() => useSessionStore.getState().setStep('canvas')}
              disabled={researchStatus !== 'ready'}
              className="px-6 py-2.5 rounded-xl bg-green-600 text-white font-semibold text-sm hover:bg-green-700 disabled:opacity-40"
            >
              Generate Product Canvas →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
