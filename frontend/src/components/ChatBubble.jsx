export default function ChatBubble({ role, content }) {
  const isAgent = role === 'agent'

  return (
    <div className={`flex items-end gap-2.5 mb-4 animate-slide-up ${isAgent ? 'justify-start' : 'justify-end'}`}>
      {isAgent && (
        <div className="w-8 h-8 rounded-full bg-accent-500 flex items-center justify-center
                        text-white text-[10px] font-bold shrink-0 mb-0.5">
          AI
        </div>
      )}

      <div className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm
        ${isAgent
          ? 'bg-white dark:bg-navy-800 border border-slate-200 dark:border-navy-600 text-slate-800 dark:text-slate-200 rounded-bl-sm'
          : 'bg-brand-600 text-white rounded-br-sm'
        }`}
      >
        {isAgent && (
          <div className="text-[10px] font-bold text-accent-600 dark:text-accent-400 mb-1.5 uppercase tracking-wider">
            AI Agent
          </div>
        )}
        <p className="whitespace-pre-wrap">{content}</p>
      </div>

      {!isAgent && (
        <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-navy-700 flex items-center justify-center
                        text-slate-600 dark:text-slate-300 shrink-0 mb-0.5">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
          </svg>
        </div>
      )}
    </div>
  )
}
