import { useState } from 'react'
import useSessionStore from '../store/sessionStore'

function RobotIcon({ className = 'w-7 h-7' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="2" x2="12" y2="5" />
      <circle cx="12" cy="1.5" r="1" fill="currentColor" stroke="none" />
      <rect x="4" y="5" width="16" height="12" rx="3" />
      <circle cx="9"  cy="11" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="15" cy="11" r="1.5" fill="currentColor" stroke="none" />
      <path d="M9 14.5 Q12 16.5 15 14.5" strokeWidth={1.4} />
      <path d="M8 17 v2 M16 17 v2" strokeWidth={1.6} />
      <path d="M6 19 h12" strokeWidth={1.6} />
    </svg>
  )
}

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPwd, setShowPwd]   = useState(false)
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  const login = useSessionStore((s) => s.login)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!username.trim() || !password.trim()) {
      setError('Please enter your username and password.')
      return
    }
    setLoading(true)
    await new Promise((r) => setTimeout(r, 600))
    setLoading(false)
    login({ email: `${username}@npci.org`, name: username })
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden
                    bg-slate-50 dark:bg-navy-950">

      {/* Subtle navy glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-64 pointer-events-none opacity-20 dark:opacity-30"
           style={{ background: 'radial-gradient(ellipse, #1B3F8F, transparent 70%)' }} />
      {/* Mustard accent dot top-right */}
      <div className="absolute top-16 right-24 w-3 h-3 rounded-full bg-accent-500 opacity-60" />
      <div className="absolute top-32 right-16 w-1.5 h-1.5 rounded-full bg-accent-400 opacity-40" />
      {/* dot grid */}
      <div className="absolute inset-0 opacity-[0.025] pointer-events-none dark:opacity-[0.04]"
           style={{
             backgroundImage: 'radial-gradient(circle at 1px 1px, #1B3F8F 1px, transparent 0)',
             backgroundSize: '28px 28px',
           }} />

      <div className="relative z-10 w-full max-w-[360px] mx-4">

        {/* Logo */}
        <div className="flex flex-col items-center mb-8 select-none">
          <div className="w-14 h-14 rounded-2xl bg-brand-600 flex items-center justify-center
                          shadow-lg shadow-brand-900/25 mb-4 text-white relative">
            <RobotIcon className="w-8 h-8" />
            {/* mustard accent dot on icon */}
            <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-accent-500
                             border-2 border-white dark:border-navy-950" />
          </div>
          <h1 className="text-[22px] font-bold text-slate-900 dark:text-white tracking-tight">
            NPCI AgentHub
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Sign in to your workspace</p>
        </div>

        {/* Form card */}
        <div className="bg-white dark:bg-navy-900
                        border border-slate-200 dark:border-navy-600
                        rounded-2xl p-6 shadow-lg shadow-slate-200/70 dark:shadow-none">
          <form onSubmit={handleSubmit} className="space-y-4">

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                Username
              </label>
              <input
                type="text"
                autoComplete="username"
                autoFocus
                className="w-full bg-slate-50 dark:bg-navy-800 border border-slate-200 dark:border-navy-600
                           rounded-xl px-4 py-2.5 text-sm text-slate-900 dark:text-slate-100
                           placeholder-slate-400 dark:placeholder-slate-500
                           focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500
                           transition-all"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPwd ? 'text' : 'password'}
                  autoComplete="current-password"
                  className="w-full bg-slate-50 dark:bg-navy-800 border border-slate-200 dark:border-navy-600
                             rounded-xl px-4 py-2.5 pr-10 text-sm text-slate-900 dark:text-slate-100
                             placeholder-slate-400 dark:placeholder-slate-500
                             focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500
                             transition-all"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button type="button" onClick={() => setShowPwd(!showPwd)}
                        className="absolute right-3 top-1/2 -translate-y-1/2
                                   text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
                  {showPwd ? (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-600 dark:text-red-400 flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
                </svg>
                {error}
              </p>
            )}

            <button type="submit" disabled={loading}
                    className="w-full py-2.5 mt-1 rounded-xl bg-brand-600 hover:bg-brand-700
                               text-white text-sm font-semibold transition-all active:scale-95
                               disabled:opacity-50 flex items-center justify-center gap-2
                               shadow-sm shadow-brand-900/20">
              {loading ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Signing in...
                </>
              ) : 'Sign In'}
            </button>
          </form>

          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200 dark:border-navy-700" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-white dark:bg-navy-900 px-3 text-xs text-slate-400">or</span>
            </div>
          </div>

          <button type="button"
                  className="w-full py-2.5 rounded-xl border border-slate-200 dark:border-navy-600
                             text-slate-600 dark:text-slate-300 text-sm font-medium
                             hover:bg-slate-50 dark:hover:bg-navy-800 transition-all
                             flex items-center justify-center gap-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5a17.92 17.92 0 0 1-8.716-2.247" />
            </svg>
            Continue with SSO
          </button>
        </div>

        <p className="text-center text-xs text-slate-400 dark:text-slate-600 mt-5">
          NPCI Internal Platform · Authorized Personnel Only
        </p>
      </div>
    </div>
  )
}
