import { useRef, useEffect } from 'react'
import useFaceOverlay from '../../hooks/useFaceOverlay'

export default function FaceOverlay({ canvasRef: externalRef, videoRef, faceData, width, height }) {
  const internalRef = useRef(null)
  const ref = externalRef || internalRef

  useEffect(() => {
    if (ref.current) {
      ref.current.width = width
      ref.current.height = height
    }
  }, [ref, width, height])

  useFaceOverlay(ref, videoRef, faceData)

  return (
    <canvas
      ref={ref}
      className="absolute top-0 left-0 pointer-events-none"
      style={{ width, height }}
    />
  )
}
