import { create } from 'zustand'

const useSessionStore = create((set, get) => ({
  // Session
  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),

  // Step tracking: 'requirement' | 'research' | 'canvas'
  currentStep: 'requirement',
  setStep: (step) => set({ currentStep: step }),

  // Agent 1
  requirementMessages: [],
  requirementStatus: 'idle',   // idle | clarifying | complete
  questionsAsked: 0,
  structuredOutput: null,
  setRequirementState: (data) => set({
    requirementMessages: data.messages || [],
    requirementStatus: data.status,
    questionsAsked: data.questions_asked,
    structuredOutput: data.structured_output,
  }),

  // Agent 2
  researchReport: null,
  researchStatus: 'idle',
  researchVersions: [],
  setResearchState: (data) => set({
    researchReport: data.current_report,
    researchStatus: data.status,
    researchVersions: data.versions || [],
  }),

  // Agent 3
  canvas: null,
  canvasStatus: 'idle',
  canvasVersions: [],
  setCanvasState: (data) => set({
    canvas: data.canvas,
    canvasStatus: data.status,
    canvasVersions: data.versions || [],
  }),

  // Loading states
  loading: false,
  setLoading: (v) => set({ loading: v }),

  error: null,
  setError: (e) => set({ error: e }),
  clearError: () => set({ error: null }),
}))

export default useSessionStore
