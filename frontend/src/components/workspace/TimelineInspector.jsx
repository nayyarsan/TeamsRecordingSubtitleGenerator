import { useEffect, useRef } from 'react'
import useVideoSync from '../../hooks/useVideoSync'
import { formatTime } from '../../utils/formatters'

export default function TimelineInspector({ videoId, subtitles, videoRef, onRenamed }) {
  const { currentTime, activeIndex, seekTo } = useVideoSync(videoRef, subtitles)
  const activeRef = useRef(null)

  // Auto-scroll to keep active segment visible
  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [activeIndex])

  // Generate consistent color for speaker name
  const getSpeakerColor = (speaker) => {
    if (!speaker) return 'bg-gray-600'
    let hash = 0
    for (let i = 0; i < speaker.length; i++) {
      hash = speaker.charCodeAt(i) + ((hash << 5) - hash)
    }
    const colors = [
      'bg-blue-600',
      'bg-green-600',
      'bg-purple-600',
      'bg-pink-600',
      'bg-yellow-600',
      'bg-indigo-600',
      'bg-red-600',
      'bg-teal-600',
    ]
    return colors[Math.abs(hash) % colors.length]
  }

  if (!subtitles || subtitles.length === 0) {
    return (
      <div className="p-4 text-center text-gray-400 text-sm">
        No timeline data available
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-border">
        <div className="text-xs text-gray-400">
          {subtitles.length} segments • {formatTime(currentTime)}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {subtitles.map((segment, index) => {
          const isActive = index === activeIndex
          return (
            <div
              key={index}
              ref={isActive ? activeRef : null}
              onClick={() => seekTo(segment.start)}
              className={`p-3 border-b border-border cursor-pointer transition-colors ${
                isActive
                  ? 'bg-primary/10 border-l-2 border-l-primary'
                  : 'hover:bg-surface/50'
              }`}
            >
              {/* Timestamp */}
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono text-gray-500">
                  {formatTime(segment.start)}
                </span>
                {segment.speaker && (
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium text-white ${getSpeakerColor(
                      segment.speaker
                    )}`}
                  >
                    {segment.speaker}
                  </span>
                )}
              </div>

              {/* Text preview */}
              <div className={`text-sm ${isActive ? 'text-white' : 'text-gray-300'} line-clamp-2`}>
                {segment.text}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
