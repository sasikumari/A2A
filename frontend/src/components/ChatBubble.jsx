export default function ChatBubble({ role, content }) {
  const isAgent = role === 'agent'
  return (
    <div className={`flex ${isAgent ? 'justify-start' : 'justify-end'} mb-3`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm
          ${isAgent
            ? 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm'
            : 'bg-blue-600 text-white rounded-tr-sm'
          }`}
      >
        {isAgent && (
          <div className="text-xs font-semibold text-blue-600 mb-1">AI Agent</div>
        )}
        <p className="whitespace-pre-wrap">{content}</p>
      </div>
    </div>
  )
}
