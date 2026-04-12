import useSessionStore from './store/sessionStore'
import StepIndicator from './components/StepIndicator'
import RequirementChat from './pages/RequirementChat'
import ResearchReport from './pages/ResearchReport'
import ProductCanvas from './pages/ProductCanvas'

function App() {
  const currentStep = useSessionStore((s) => s.currentStep)

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Navbar */}
      <nav className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">AI</span>
          </div>
          <div>
            <h1 className="font-bold text-gray-900 text-base leading-tight">
              Change Orchestration Platform
            </h1>
            <p className="text-xs text-gray-400">AI-driven Product Canvas Generator</p>
          </div>
        </div>
      </nav>

      {/* Main */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        <StepIndicator current={currentStep} />

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 min-h-[600px] flex flex-col">
          {currentStep === 'requirement' && <RequirementChat />}
          {currentStep === 'research' && <ResearchReport />}
          {currentStep === 'canvas' && <ProductCanvas />}
        </div>
      </main>
    </div>
  )
}

export default App
