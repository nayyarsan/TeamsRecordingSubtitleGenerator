import { useState, useEffect, useCallback } from 'react'
import { formatTime, formatDuration } from '../../utils/formatters'
import StatusBadge from '../common/StatusBadge'

export default function PlayerControls({ videoRef, currentTime, faceData }) {
  const [playing, setPlaying] = useState(false)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)

  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)
    const onMeta = () => setDuration(v.duration || 0)
    v.addEventListener('play', onPlay)
    v.addEventListener('pause', onPause)
    v.addEventListener('loadedmetadata', onMeta)
    return () => {
      v.removeEventListener('play', onPlay)
      v.removeEventListener('pause', onPause)
      v.removeEventListener('loadedmetadata', onMeta)
    }
  }, [videoRef])

  const togglePlay = useCallback(() => {
    const v = videoRef.current
    if (!v) return
    v.paused ? v.play() : v.pause()
  }, [videoRef])

  const seek = useCallback((e) => {
    const v = videoRef.current
    if (!v) return
    v.currentTime = parseFloat(e.target.value)
  }, [videoRef])

  const changeVolume = useCallback((e) => {
    const val = parseFloat(e.target.value)
    setVolume(val)
    if (videoRef.current) videoRef.current.volume = val
  }, [videoRef])

  // Count faces in current frame
  let faceCount = 0
  if (faceData?.frames) {
    const frame = faceData.frames.find(
      (f) => Math.abs(f.timestamp - currentTime) < 0.5
    )
    if (frame) faceCount = frame.faces?.length || 0
  }

  return (
    <div className="bg-surface border border-border rounded-lg mt-2 px-4 py-2 flex items-center gap-3">
      {/* Play/Pause */}
      <button onClick={togglePlay} className="text-white hover:text-primary text-lg w-8">
        {playing ? '\u23F8' : '\u25B6'}
      </button>

      {/* Time */}
      <span className="text-xs text-gray-400 w-24 shrink-0">
        {formatTime(currentTime)} / {formatDuration(duration)}
      </span>

      {/* Scrubber */}
      <input
        type="range"
        min={0}
        max={duration || 1}
        step={0.1}
        value={currentTime}
        onChange={seek}
        className="flex-1 h-1 accent-primary"
      />

      {/* Volume */}
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={volume}
        onChange={changeVolume}
        className="w-16 h-1 accent-primary"
      />

      {/* Face count */}
      {faceCount > 0 && (
        <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded">{faceCount} faces</span>
      )}

      <StatusBadge status="active" label="Recognition: active" />
    </div>
  )
}
