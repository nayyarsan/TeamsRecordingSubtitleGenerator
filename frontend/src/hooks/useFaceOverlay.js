import { useEffect, useRef, useCallback } from 'react'

export default function useFaceOverlay(canvasRef, videoRef, faceData) {
  const framesRef = useRef([])
  const resolutionRef = useRef([1920, 1080])

  useEffect(() => {
    if (!faceData) return
    framesRef.current = faceData.frames || []
    resolutionRef.current = faceData.video_resolution || [1920, 1080]
  }, [faceData])

  const findNearestFrame = useCallback((time) => {
    const frames = framesRef.current
    if (!frames.length) return null
    let best = frames[0]
    let bestDist = Math.abs(frames[0].timestamp - time)
    for (let i = 1; i < frames.length; i++) {
      const d = Math.abs(frames[i].timestamp - time)
      if (d < bestDist) { best = frames[i]; bestDist = d }
      if (frames[i].timestamp > time + 1) break
    }
    return bestDist < 1 ? best : null
  }, [])

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    const video = videoRef.current
    if (!canvas || !video) return

    const ctx = canvas.getContext('2d')
    const w = canvas.width
    const h = canvas.height
    ctx.clearRect(0, 0, w, h)

    const frame = findNearestFrame(video.currentTime)
    if (!frame || !frame.faces) return

    const [origW, origH] = resolutionRef.current
    const scaleX = w / (origW || 1)
    const scaleY = h / (origH || 1)

    for (const face of frame.faces) {
      if (!face.bbox || face.bbox.length < 4) continue
      const [x, y, bw, bh] = face.bbox
      const rx = x * scaleX
      const ry = y * scaleY
      const rw = bw * scaleX
      const rh = bh * scaleY

      const isLowConf = (face.confidence || 0) < 0.6
      ctx.strokeStyle = isLowConf ? '#EAB308' : '#2563EB'
      ctx.lineWidth = 2
      ctx.strokeRect(rx, ry, rw, rh)

      const label = face.speaker_label || face.face_id || ''
      if (label) {
        ctx.font = '12px sans-serif'
        const tm = ctx.measureText(label)
        ctx.fillStyle = isLowConf ? 'rgba(234,179,8,0.7)' : 'rgba(37,99,235,0.7)'
        ctx.fillRect(rx, ry - 18, tm.width + 8, 18)
        ctx.fillStyle = '#fff'
        ctx.fillText(label, rx + 4, ry - 5)
      }
    }
  }, [canvasRef, videoRef, findNearestFrame])

  useEffect(() => {
    let running = true
    function loop() {
      if (!running) return
      draw()
      requestAnimationFrame(loop)
    }
    loop()
    return () => { running = false }
  }, [draw])
}
