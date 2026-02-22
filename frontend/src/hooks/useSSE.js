import { useEffect, useRef, useState, useCallback } from 'react'

export default function useSSE(url) {
  const [data, setData] = useState(null)
  const [logs, setLogs] = useState([])
  const [connected, setConnected] = useState(false)
  const [done, setDone] = useState(false)
  const esRef = useRef(null)

  const connect = useCallback((activeUrl) => {
    if (esRef.current) esRef.current.close()
    setDone(false)
    setLogs([])

    const es = new EventSource(activeUrl || url)
    esRef.current = es

    es.addEventListener('progress', (e) => {
      const parsed = JSON.parse(e.data)
      setData(parsed)
      if (parsed.logs && parsed.logs.length > 0) {
        setLogs((prev) => [...prev, ...parsed.logs])
      }
      if (parsed.status === 'complete' || parsed.status === 'error') {
        setDone(true)
        es.close()
      }
    })

    es.onopen = () => setConnected(true)
    es.onerror = () => {
      setConnected(false)
      es.close()
    }
  }, [url])

  useEffect(() => {
    return () => { if (esRef.current) esRef.current.close() }
  }, [])

  return { data, logs, connected, done, connect }
}
