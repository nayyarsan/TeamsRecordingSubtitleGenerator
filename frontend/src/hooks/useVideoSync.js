import { useState, useEffect, useCallback, useRef } from 'react'

export default function useVideoSync(videoRef, subtitles) {
  const [currentTime, setCurrentTime] = useState(0)
  const [activeIndex, setActiveIndex] = useState(-1)
  const rafRef = useRef(null)

  const update = useCallback(() => {
    if (!videoRef.current) return
    const t = videoRef.current.currentTime
    setCurrentTime(t)

    const idx = subtitles.findIndex((s) => s.start <= t && t < s.end)
    setActiveIndex(idx)

    rafRef.current = requestAnimationFrame(update)
  }, [videoRef, subtitles])

  useEffect(() => {
    rafRef.current = requestAnimationFrame(update)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [update])

  const seekTo = useCallback((time) => {
    if (videoRef.current) videoRef.current.currentTime = time
  }, [videoRef])

  return { currentTime, activeIndex, seekTo }
}
