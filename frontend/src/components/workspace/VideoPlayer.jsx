import { useRef, useCallback, useEffect, useState } from 'react'
import FaceOverlay from './FaceOverlay'
import SubtitleOverlay from './SubtitleOverlay'
import PlayerControls from './PlayerControls'
import useVideoSync from '../../hooks/useVideoSync'

export default function VideoPlayer({ videoId, videoRef, subtitles, faceData, showFaces }) {
  const containerRef = useRef(null)
  const canvasRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })
  const { currentTime, activeIndex, seekTo } = useVideoSync(videoRef, subtitles)

  const activeSub = activeIndex >= 0 ? subtitles[activeIndex] : null

  const updateDimensions = useCallback(() => {
    if (!videoRef.current) return
    const v = videoRef.current
    setDimensions({ width: v.clientWidth, height: v.clientHeight })
  }, [videoRef])

  useEffect(() => {
    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [updateDimensions])

  // Keyboard shortcuts
  useEffect(() => {
    function onKey(e) {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
      const v = videoRef.current
      if (!v) return
      if (e.code === 'Space') { e.preventDefault(); v.paused ? v.play() : v.pause() }
      if (e.code === 'ArrowLeft') { e.preventDefault(); v.currentTime = Math.max(0, v.currentTime - 5) }
      if (e.code === 'ArrowRight') { e.preventDefault(); v.currentTime += 5 }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [videoRef])

  return (
    <div className="flex flex-col h-full">
      <div ref={containerRef} className="relative bg-black rounded-lg overflow-hidden max-h-[calc(100vh-16rem)] flex items-center justify-center">
        <video
          ref={videoRef}
          src={videoId ? `/api/video/${videoId}/original` : undefined}
          className="max-w-full max-h-full object-contain"
          onLoadedMetadata={updateDimensions}
          onResize={updateDimensions}
        />

        {showFaces && (
          <FaceOverlay
            canvasRef={canvasRef}
            videoRef={videoRef}
            faceData={faceData}
            width={dimensions.width}
            height={dimensions.height}
          />
        )}

        <SubtitleOverlay subtitle={activeSub} />
      </div>

      <PlayerControls
        videoRef={videoRef}
        currentTime={currentTime}
        faceData={faceData}
      />
    </div>
  )
}
