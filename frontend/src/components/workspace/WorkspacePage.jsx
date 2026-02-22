import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import VideoPlayer from './VideoPlayer'
import TimelineInspector from './TimelineInspector'
import SpeakerManager from './SpeakerManager'
import ExportModal from './ExportModal'
import { getMetadata, getSubtitles, getFaces } from '../../api/client'
import Button from '../common/Button'

export default function WorkspacePage() {
  const { videoId } = useParams()
  const navigate = useNavigate()
  const videoRef = useRef(null)

  const [metadata, setMetadata] = useState(null)
  const [subtitles, setSubtitles] = useState([])
  const [faceData, setFaceData] = useState(null)
  const [sidebarTab, setSidebarTab] = useState('timeline')
  const [showExport, setShowExport] = useState(false)
  const [showFaces, setShowFaces] = useState(true)

  useEffect(() => {
    if (!videoId) return
    getMetadata(videoId).then(setMetadata).catch(() => {})
    getSubtitles(videoId).then((d) => setSubtitles(d.subtitles || [])).catch(() => {})
    getFaces(videoId).then(setFaceData).catch(() => {})
  }, [videoId])

  function handleSpeakerRenamed() {
    getSubtitles(videoId).then((d) => setSubtitles(d.subtitles || [])).catch(() => {})
    getMetadata(videoId).then(setMetadata).catch(() => {})
  }

  return (
    <div className="flex flex-col h-full">
      {/* Top menu bar */}
      <div className="h-9 bg-surface border-b border-border flex items-center px-4 text-xs gap-4 shrink-0">
        <button onClick={() => navigate('/')} className="text-gray-400 hover:text-white">File</button>
        <button onClick={() => setShowExport(true)} className="text-gray-400 hover:text-white">Export</button>
        <button data-testid="face-toggle" onClick={() => setShowFaces((f) => !f)} className="text-gray-400 hover:text-white">
          {showFaces ? 'Hide Faces' : 'Show Faces'}
        </button>
        <div className="ml-auto text-gray-500">{videoId}</div>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Main video area */}
        <div className="flex-1 p-4 flex flex-col min-w-0">
          <VideoPlayer
            videoId={videoId}
            videoRef={videoRef}
            subtitles={subtitles}
            faceData={faceData}
            showFaces={showFaces}
          />
        </div>

        {/* Right sidebar */}
        <div className="w-80 bg-surface border-l border-border flex flex-col shrink-0">
          {/* Tab buttons */}
          <div className="flex border-b border-border">
            <button
              data-testid="tab-timeline"
              onClick={() => setSidebarTab('timeline')}
              className={`flex-1 py-2 text-xs font-medium ${sidebarTab === 'timeline' ? 'text-primary border-b-2 border-primary' : 'text-gray-400'}`}
            >
              Timeline
            </button>
            <button
              data-testid="tab-speakers"
              onClick={() => setSidebarTab('speakers')}
              className={`flex-1 py-2 text-xs font-medium ${sidebarTab === 'speakers' ? 'text-primary border-b-2 border-primary' : 'text-gray-400'}`}
            >
              Speakers
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            {sidebarTab === 'timeline' && (
              <TimelineInspector
                videoId={videoId}
                subtitles={subtitles}
                videoRef={videoRef}
                onRenamed={handleSpeakerRenamed}
              />
            )}
            {sidebarTab === 'speakers' && (
              <SpeakerManager
                videoId={videoId}
                metadata={metadata}
                onRenamed={handleSpeakerRenamed}
              />
            )}
          </div>
        </div>
      </div>

      <ExportModal open={showExport} onClose={() => setShowExport(false)} videoId={videoId} />
    </div>
  )
}
