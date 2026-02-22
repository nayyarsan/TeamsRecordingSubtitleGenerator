import { useEffect, useRef } from 'react'

const LEVEL_COLORS = {
  info: 'text-gray-300',
  success: 'text-green-400',
  warning: 'text-yellow-400',
  error: 'text-red-400',
}

export default function SystemLogs({ logs }) {
  const endRef = useRef()

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  return (
    <div className="bg-surface border border-border rounded-lg">
      <div className="px-4 py-2 border-b border-border">
        <h3 className="text-xs font-semibold text-gray-400 uppercase">System Logs</h3>
      </div>
      <div className="p-3 max-h-48 overflow-y-auto font-mono text-xs leading-relaxed">
        {(!logs || logs.length === 0) && (
          <span className="text-gray-600">Waiting for log output...</span>
        )}
        {logs?.map((log, i) => (
          <div key={i} className={LEVEL_COLORS[log.level] || LEVEL_COLORS.info}>
            [{log.step}] {log.message}
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  )
}
