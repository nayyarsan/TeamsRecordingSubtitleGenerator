import { useState } from 'react'
import Modal from '../common/Modal'
import Button from '../common/Button'
import { exportFile } from '../../api/client'

const EXPORT_FORMATS = [
  {
    id: 'srt',
    name: 'SRT Subtitles',
    description: 'Standard subtitle format with speaker labels. Compatible with all video players.',
    extension: '.srt',
    icon: '📝',
  },
  {
    id: 'json',
    name: 'JSON Metadata',
    description: 'Complete structured data including segments, speakers, timestamps, and confidence scores.',
    extension: '.json',
    icon: '📊',
  },
  {
    id: 'video',
    name: 'Annotated Video',
    description: 'Video with face bounding boxes and subtitles baked in. H.264 codec for compatibility.',
    extension: '.mp4',
    icon: '🎬',
  },
]

export default function ExportModal({ open, onClose, videoId }) {
  const [selectedFormat, setSelectedFormat] = useState('srt')
  const [exporting, setExporting] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState(null)

  const handleExport = async () => {
    if (!selectedFormat) return

    setExporting(true)
    setError(null)
    setSuccess(false)

    try {
      await exportFile(videoId, selectedFormat)
      setSuccess(true)
      // Close modal after short delay to show success message
      setTimeout(() => {
        setSuccess(false)
        onClose()
      }, 1500)
    } catch (err) {
      setError(err.message || 'Export failed')
    } finally {
      setExporting(false)
    }
  }

  const handleClose = () => {
    if (!exporting) {
      setSelectedFormat('srt')
      setSuccess(false)
      setError(null)
      onClose()
    }
  }

  return (
    <Modal open={open} onClose={handleClose} title="Export" testId="export-modal">
      <div className="space-y-4">
        {/* Format selection */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-300">Select Format:</label>
          <div className="space-y-2">
            {EXPORT_FORMATS.map((format) => (
              <button
                key={format.id}
                onClick={() => setSelectedFormat(format.id)}
                disabled={exporting}
                className={`w-full text-left p-3 rounded-lg border transition-colors ${
                  selectedFormat === format.id
                    ? 'border-primary bg-primary/10'
                    : 'border-border bg-surface hover:border-gray-500'
                } ${exporting ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-2xl">{format.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-white">
                        {format.name}
                      </span>
                      <span className="text-xs text-gray-500 font-mono">
                        {format.extension}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      {format.description}
                    </p>
                  </div>
                  {selectedFormat === format.id && (
                    <div className="flex-shrink-0 w-4 h-4 rounded-full bg-primary flex items-center justify-center">
                      <svg
                        className="w-3 h-3 text-white"
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Success message */}
        {success && (
          <div className="p-3 bg-green-900/20 border border-green-500/50 rounded text-sm text-green-400 flex items-center gap-2">
            <svg
              className="w-5 h-5 flex-shrink-0"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path d="M5 13l4 4L19 7" />
            </svg>
            <span>Export successful! File downloaded.</span>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="p-3 bg-red-900/20 border border-red-500/50 rounded text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-2 pt-2">
          <Button
            onClick={handleExport}
            disabled={exporting || !selectedFormat}
            variant="primary"
            className="flex-1"
          >
            {exporting ? 'Exporting...' : 'Export'}
          </Button>
          <Button
            onClick={handleClose}
            disabled={exporting}
            variant="secondary"
            className="flex-1"
          >
            Cancel
          </Button>
        </div>

        {/* Help text */}
        {selectedFormat === 'video' && (
          <p className="text-xs text-gray-500">
            Note: Annotated video export may take several minutes depending on video length.
          </p>
        )}
      </div>
    </Modal>
  )
}
