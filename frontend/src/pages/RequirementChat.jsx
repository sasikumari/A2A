import { useState, useRef, useEffect } from 'react'
import { createSession, startRequirement, respondRequirement } from '../api/client'
import useSessionStore from '../store/sessionStore'
import ChatBubble from '../components/ChatBubble'

export default function RequirementChat() {
  const [input, setInput] = useState('')
  const [started, setStarted] = useState(false)
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
  }, [requirementMessages])

  const handleStart = async () => {
    if (!input.trim()) return
    clearError()
    setLoading(true)
    try {
      // Create session if needed
      let sid = sessionId
      if (!sid) {
        const res = await createSession()
        sid = res.data.session_id
        setSessionId(sid)
      }

      const res = await startRequirement(sid, input.trim())
      setRequirementState(res.data)
      setStarted(true)
      setInput('')
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAnswer = async () => {
    if (!input.trim() || requirementStatus === 'complete') return
    clearError()
    setLoading(true)
    try {
      const res = await respondRequirement(sessionId, input.trim())
      setRequirementState(res.data)
      setInput('')
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      started ? handleAnswer() : handleStart()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-lg font-bold text-gray-800">Requirement Gathering</h2>
        <p className="text-sm text-gray-500">
          Describe the feature you want to build. The agent will ask up to 5 clarifying questions.
        </p>
        {requirementStatus === 'clarifying' && (
          <span className="inline-block mt-1 text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">
            {questionsAsked}/5 questions asked
          </span>
        )}
        {requirementStatus === 'complete' && (
          <span className="inline-block mt-1 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
            Requirements complete
          </span>
        )}
      </div>

      {/* Chat window */}
      <div className="flex-1 overflow-y-auto bg-gray-50 rounded-xl p-4 border border-gray-200 min-h-[300px] max-h-[420px]">
        {requirementMessages.length === 0 && (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            Type your feature request below to begin...
          </div>
        )}
        {requirementMessages.map((msg, i) => (
          <ChatBubble key={i} role={msg.role} content={msg.content} />
        ))}
        {loading && (
          <div className="flex justify-start mb-3">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
              <div className="flex gap-1 items-center">
                <span className="text-xs text-blue-600 font-semibold mr-2">AI Agent</span>
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Error */}
      {error && (
        <div className="mt-2 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg border border-red-200">
          {error}
        </div>
      )}

      {/* Input */}
      {requirementStatus !== 'complete' && (
        <div className="mt-3 flex gap-2">
          <textarea
            className="flex-1 border border-gray-300 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
            rows={2}
            placeholder={started ? 'Type your answer...' : 'e.g. Add UPI embedded payments for merchant QR code flows'}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button
            onClick={started ? handleAnswer : handleStart}
            disabled={loading || !input.trim()}
            className="px-5 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-40"
          >
            {loading ? '...' : 'Send'}
          </button>
        </div>
      )}

      {/* Proceed button */}
      {requirementStatus === 'complete' && (
        <div className="mt-4 flex flex-col gap-2">
          {structuredOutput && (
            <details className="text-xs text-gray-500 bg-gray-50 rounded-lg p-3 border border-gray-200">
              <summary className="cursor-pointer font-medium text-gray-700">View structured output</summary>
              <pre className="mt-2 overflow-x-auto">{JSON.stringify(structuredOutput, null, 2)}</pre>
            </details>
          )}
          <button
            onClick={() => setStep('research')}
            className="mt-2 px-6 py-3 rounded-xl bg-green-600 text-white font-semibold hover:bg-green-700"
          >
            Proceed to Deep Research →
          </button>
        </div>
      )}
    </div>
  )
}
