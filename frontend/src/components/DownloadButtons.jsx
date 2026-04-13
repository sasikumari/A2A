import { useState } from 'react'
import { exportCanvas } from '../api/client'

export default function DownloadButtons({ sessionId }) {
  const [loading, setLoading] = useState(null)

  const handleDownload = async (format) => {
    setLoading(format)
    try {
      const res = await exportCanvas(sessionId, format)
      const blob = new Blob([res.data], {
        type: format === 'docx'
          ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
          : 'application/pdf',
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `product_canvas.${format}`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      alert(`Export failed: ${e.message}`)
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="flex gap-2">
      <button
        onClick={() => handleDownload('docx')}
        disabled={!!loading}
        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold
                   bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800
                   text-indigo-700 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/40
                   disabled:opacity-50 transition-all active:scale-95"
      >
        {loading === 'docx' ? (
          <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m.75 12 3 3m0 0 3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
          </svg>
        )}
        {loading === 'docx' ? 'Exporting...' : 'DOCX'}
      </button>

      <button
        onClick={() => handleDownload('pdf')}
        disabled={!!loading}
        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold
                   bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800
                   text-red-700 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40
                   disabled:opacity-50 transition-all active:scale-95"
      >
        {loading === 'pdf' ? (
          <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m.75 12 3 3m0 0 3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
          </svg>
        )}
        {loading === 'pdf' ? 'Exporting...' : 'PDF'}
      </button>
    </div>
  )
}
