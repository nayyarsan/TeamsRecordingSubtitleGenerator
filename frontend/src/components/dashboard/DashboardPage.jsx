import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import DropZone from './DropZone'
import ConfigPanel from './ConfigPanel'
import PipelineProgress from './PipelineProgress'
import SystemLogs from './SystemLogs'
import { listVideos } from '../../api/client'
import { formatDate } from '../../utils/formatters'
import useSSE from '../../hooks/useSSE'

export default function DashboardPage() {
  const navigate = useNavigate()
  const [videos, setVideos] = useState([])
  const [videoId, setVideoId] = useState(null)
  const [processing, setProcessing] = useState(false)
  const sse = useSSE()

  useEffect(() => { loadVideos() }, [])

  async function loadVideos() {
    try {
      const data = await listVideos()
      setVideos(data.videos || [])
    } catch { /* ignore */ }
  }

  function onUploadComplete(result) {
    setVideoId(result.video_id)
  }

  function onProcessingStarted(vid) {
    setProcessing(true)
    sse.connect(`/api/process/status/${vid}`)
  }

  useEffect(() => {
    if (sse.done && sse.data?.status === 'complete') {
      setProcessing(false)
      loadVideos()
    }
  }, [sse.done, sse.data])

  return (
    <div className="flex h-full">
      {/* Main area */}
      <div className="flex-1 overflow-y-auto p-6">
        <h1 className="text-2xl font-bold mb-1">MediaProcessor Dashboard</h1>
        <p className="text-sm text-gray-400 mb-6">Upload and process meeting recordings with speaker labeling</p>

        <DropZone onUploadComplete={onUploadComplete} />

        {processing && (
          <div className="mt-6 space-y-4">
            <PipelineProgress data={sse.data} />
            <SystemLogs logs={sse.logs} />
          </div>
        )}

        {/* Processed videos */}
        {videos.length > 0 && (
          <div className="mt-8">
            <h2 className="text-lg font-semibold mb-3">Processed Videos</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {videos.map((v) => (
                <button
                  key={v.id}
                  data-testid="video-card"
                  onClick={() => navigate(`/workspace/${v.id}`)}
                  className="bg-surface border border-border rounded-lg p-4 text-left hover:border-primary transition-colors"
                >
                  <div className="font-medium text-sm truncate">{v.name}</div>
                  <div className="text-xs text-gray-400 mt-1">{formatDate(v.timestamp)}</div>
                  <div className="text-xs text-gray-500 mt-1">{v.speaker_count || 0} speakers</div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Right sidebar: Config */}
      <div className="w-80 bg-surface border-l border-border p-4 overflow-y-auto">
        <ConfigPanel videoId={videoId} onProcessingStarted={onProcessingStarted} />
      </div>
    </div>
  )
}
