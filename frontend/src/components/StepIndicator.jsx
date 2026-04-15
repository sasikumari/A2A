const STEPS = [
  { key: 'requirement', label: 'Requirements', num: 1 },
  { key: 'research', label: 'Research', num: 2 },
  { key: 'canvas', label: 'Product Canvas', num: 3 },
  { key: 'documents', label: 'Document Suite', num: 4 },
]

export default function StepIndicator({ current }) {
  const currentIdx = STEPS.findIndex((s) => s.key === current)

  return (
    <div className="flex items-center gap-0 mb-8">
      {STEPS.map((step, i) => (
        <div key={step.key} className="flex items-center">
          <div className="flex flex-col items-center">
            <div
              className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all
                ${i < currentIdx
                  ? 'bg-green-500 border-green-500 text-white'
                  : i === currentIdx
                    ? 'bg-blue-600 border-blue-600 text-white'
                    : 'bg-white border-gray-300 text-gray-400'
                }`}
            >
              {i < currentIdx ? '✓' : step.num}
            </div>
            <span className={`text-xs mt-1 font-medium ${i === currentIdx ? 'text-blue-600' : 'text-gray-400'}`}>
              {step.label}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div className={`w-24 h-0.5 mx-1 mb-4 ${i < currentIdx ? 'bg-green-400' : 'bg-gray-200'}`} />
          )}
        </div>
      ))}
    </div>
  )
}
