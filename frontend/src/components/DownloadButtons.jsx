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
    <div className="flex gap-3">
      <button
        onClick={() => handleDownload('docx')}
        disabled={!!loading}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm hover:bg-indigo-700 disabled:opacity-50"
      >
        {loading === 'docx' ? 'Generating...' : 'Download DOCX'}
      </button>
      <button
        onClick={() => handleDownload('pdf')}
        disabled={!!loading}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 text-white text-sm hover:bg-red-700 disabled:opacity-50"
      >
        {loading === 'pdf' ? 'Generating...' : 'Download PDF'}
      </button>
    </div>
  )
}
