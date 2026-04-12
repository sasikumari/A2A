import { useEffect, useState } from 'react'
import { generateCanvas, regenerateSection, updateSectionManually } from '../api/client'
import useSessionStore from '../store/sessionStore'
import SectionEditor from '../components/SectionEditor'
import DownloadButtons from '../components/DownloadButtons'

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

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h2 className="text-lg font-bold text-gray-800">Product Canvas</h2>
          <p className="text-sm text-gray-500">
            Each section is independently editable and regeneratable.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {canvasVersions.length > 0 && (
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
              Canvas v{canvas?.version}
            </span>
          )}
          {canvasStatus === 'ready' && sessionId && (
            <DownloadButtons sessionId={sessionId} />
          )}
        </div>
      </div>

      {/* Loading skeleton */}
      {loading && !canvas && (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="animate-pulse bg-gray-100 rounded-xl h-24" />
          ))}
          <p className="text-sm text-center text-gray-400 mt-4">
            Generating Product Canvas from research... this may take a moment.
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-3 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg border border-red-200">
          {error}
        </div>
      )}

      {/* Sections */}
      {canvas?.sections && (
        <div className="flex-1 overflow-y-auto pr-1">
          {loading && (
            <div className="mb-3 text-sm text-blue-600 bg-blue-50 px-3 py-2 rounded-lg border border-blue-200 animate-pulse">
              Updating section...
            </div>
          )}
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

      {/* Bottom nav */}
      <div className="mt-4 flex justify-between items-center">
        <button
          onClick={() => useSessionStore.getState().setStep('research')}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          ← Back to Research
        </button>
        {canvas && (
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="text-sm px-4 py-2 rounded-xl border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
          >
            Regenerate All
          </button>
        )}
      </div>
    </div>
  )
}
