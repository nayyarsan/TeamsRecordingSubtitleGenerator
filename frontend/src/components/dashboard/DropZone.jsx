import { useState, useRef, useCallback } from 'react'
import { uploadFile } from '../../api/client'
import { formatBytes } from '../../utils/formatters'

const ACCEPTED = ['.mp4', '.mkv', '.avi', '.mov', '.mp3', '.wav']
const MAX_SIZE = 2 * 1024 * 1024 * 1024 // 2GB

export default function DropZone({ onUploadComplete }) {
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)
  const [fileName, setFileName] = useState(null)
  const inputRef = useRef()

  const validate = (file) => {
    const ext = '.' + file.name.split('.').pop().toLowerCase()
    if (!ACCEPTED.includes(ext)) return `Unsupported format: ${ext}`
    if (file.size > MAX_SIZE) return `File too large: ${formatBytes(file.size)} (max 2GB)`
    return null
  }

  const handleUpload = useCallback(async (file) => {
    const err = validate(file)
    if (err) { setError(err); return }
    setError(null)
    setFileName(file.name)
    setProgress(0)
    try {
      const result = await uploadFile(file, setProgress)
      setProgress(100)
      onUploadComplete?.(result)
    } catch (e) {
      setError(e.message)
      setProgress(null)
    }
  }, [onUploadComplete])

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleUpload(file)
  }, [handleUpload])

  return (
    <div
      data-testid="dropzone"
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      className={`
        border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
        ${dragging ? 'border-primary bg-primary/10' : 'border-border hover:border-gray-500'}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED.join(',')}
        className="hidden"
        onChange={(e) => { if (e.target.files[0]) handleUpload(e.target.files[0]) }}
      />

      <div className="text-3xl mb-2">&#128193;</div>
      <p className="text-sm text-gray-300">Drag & drop media files here</p>
      <p className="text-xs text-gray-500 mt-1">MP4, MKV, AVI, MP3 &middot; Max 2GB</p>

      {progress !== null && (
        <div className="mt-4 max-w-xs mx-auto">
          <div className="text-xs text-gray-400 mb-1">{fileName} &middot; {progress}%</div>
          <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {error && <p className="mt-3 text-xs text-red-400">{error}</p>}
    </div>
  )
}
