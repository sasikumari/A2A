import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// Session
export const createSession = () => api.post('/session/create')

// Agent 1 — Requirement
export const startRequirement = (session_id, feature_request) =>
  api.post('/requirement/start', { session_id, feature_request })

export const respondRequirement = (session_id, answer) =>
  api.post('/requirement/respond', { session_id, answer })

export const getRequirementState = (session_id) =>
  api.get(`/requirement/${session_id}`)

// Agent 2 — Research
export const generateResearch = (session_id) =>
  api.post('/research/generate', { session_id })

export const submitResearchFeedback = (session_id, feedback, sections_to_regenerate = null) =>
  api.post('/research/feedback', { session_id, feedback, sections_to_regenerate })

export const getResearchState = (session_id) =>
  api.get(`/research/${session_id}`)

// Agent 3 — Canvas
export const generateCanvas = (session_id) =>
  api.post('/canvas/generate', { session_id })

export const regenerateSection = (session_id, section_key, instructions = null) =>
  api.post('/canvas/regenerate-section', { session_id, section_key, instructions })

export const updateSectionManually = (session_id, section_key, content) =>
  api.patch('/canvas/section', { session_id, section_key, content })

export const getCanvasState = (session_id) =>
  api.get(`/canvas/${session_id}`)

export const exportCanvas = (session_id, format = 'docx') =>
  api.get(`/canvas/${session_id}/export`, {
    params: { format },
    responseType: 'blob',
  })

// History
export const listHistory = () =>
  api.get('/history')

export const getHistoryDetail = (session_id) =>
  api.get(`/history/${session_id}`)

export const renameHistorySession = (session_id, title) =>
  api.patch(`/history/${session_id}/title`, { title })

export const deleteHistorySession = (session_id) =>
  api.delete(`/history/${session_id}`)
