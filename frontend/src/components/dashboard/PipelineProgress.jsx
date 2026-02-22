const STEPS = [
  { key: 'diarization', label: 'Audio Diarization', icon: '1' },
  { key: 'face_detection', label: 'Face Detection', icon: '2' },
  { key: 'fusion', label: 'Audio-Visual Fusion', icon: '3' },
  { key: 'complete', label: 'Complete', icon: '4' },
]

function getStepStatus(stepKey, currentStep, percent) {
  const stepOrder = ['diarization', 'transcription', 'face_detection', 'fusion', 'naming', 'output', 'complete']
  const currentIdx = stepOrder.indexOf(currentStep)
  const thisIdx = stepOrder.indexOf(stepKey)

  // Map pipeline steps to display steps
  const displayMap = { diarization: 0, transcription: 0, face_detection: 1, fusion: 2, naming: 2, output: 3, complete: 3 }
  const currentDisplay = displayMap[currentStep] ?? -1
  const thisDisplay = STEPS.findIndex((s) => s.key === stepKey)

  if (percent >= 100 || currentStep === 'complete') return 'done'
  if (thisDisplay < currentDisplay) return 'done'
  if (thisDisplay === currentDisplay) return 'active'
  return 'pending'
}

export default function PipelineProgress({ data }) {
  if (!data) return null
  const { step, percent, status } = data

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold">Processing Pipeline</h3>
        <span className="text-xs text-gray-400">{percent}%</span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden mb-4">
        <div
          className={`h-full rounded-full transition-all duration-500 ${status === 'error' ? 'bg-red-500' : 'bg-primary'}`}
          style={{ width: `${percent}%` }}
        />
      </div>

      {/* Steps */}
      <div className="flex justify-between">
        {STEPS.map((s) => {
          const st = getStepStatus(s.key, step, percent)
          return (
            <div key={s.key} className="flex flex-col items-center gap-1">
              <div className={`
                w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2
                ${st === 'done' ? 'bg-green-600 border-green-500 text-white' :
                  st === 'active' ? 'bg-primary border-blue-400 text-white animate-pulse' :
                  'bg-gray-800 border-border text-gray-500'}
              `}>
                {st === 'done' ? '\u2713' : s.icon}
              </div>
              <span className={`text-[10px] ${st === 'active' ? 'text-white' : 'text-gray-500'}`}>{s.label}</span>
            </div>
          )
        })}
      </div>

      {status === 'error' && data.error && (
        <p className="mt-3 text-xs text-red-400 bg-red-500/10 rounded p-2">{data.error}</p>
      )}
    </div>
  )
}
