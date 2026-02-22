import { useState, useEffect } from 'react'
import { startProcessing, getOllamaModels, getOllamaStatus } from '../../api/client'
import Button from '../common/Button'
import StatusBadge from '../common/StatusBadge'

export default function ConfigPanel({ videoId, onProcessingStarted }) {
  const [asrModel, setAsrModel] = useState('base')
  const [maxSpeakers, setMaxSpeakers] = useState(10)
  const [ollamaModel, setOllamaModel] = useState('')
  const [ollamaModels, setOllamaModels] = useState([])
  const [ollamaAvailable, setOllamaAvailable] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getOllamaStatus().then((s) => setOllamaAvailable(s.available)).catch(() => {})
    getOllamaModels().then((d) => {
      setOllamaModels(d.models || [])
      if (d.models?.length) setOllamaModel(d.models[0])
    }).catch(() => {})
  }, [])

  async function handleStart() {
    if (!videoId) return
    setLoading(true)
    try {
      await startProcessing({
        video_id: videoId,
        asr_model: asrModel,
        max_speakers: maxSpeakers,
        ollama_model: ollamaModel || undefined,
      })
      onProcessingStarted?.(videoId)
    } catch (e) {
      alert(`Failed to start: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-5">
      <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Pipeline Config</h2>

      <div>
        <label htmlFor="asr-model" className="block text-xs text-gray-400 mb-1">ASR Model</label>
        <select
          id="asr-model"
          value={asrModel}
          onChange={(e) => setAsrModel(e.target.value)}
          className="w-full bg-background border border-border rounded px-3 py-2 text-sm"
        >
          {['tiny', 'base', 'small', 'medium', 'large'].map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="max-speakers" className="block text-xs text-gray-400 mb-1">Max Speakers</label>
        <input
          id="max-speakers"
          type="number"
          min={1}
          max={30}
          value={maxSpeakers}
          onChange={(e) => setMaxSpeakers(parseInt(e.target.value) || 10)}
          className="w-full bg-background border border-border rounded px-3 py-2 text-sm"
        />
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-1">
          Ollama Model
          <StatusBadge status={ollamaAvailable ? 'active' : 'inactive'} label={ollamaAvailable ? 'connected' : 'unavailable'} />
        </label>
        <select
          value={ollamaModel}
          onChange={(e) => setOllamaModel(e.target.value)}
          disabled={!ollamaAvailable}
          className="w-full bg-background border border-border rounded px-3 py-2 text-sm disabled:opacity-50"
        >
          {ollamaModels.length === 0 && <option value="">No models</option>}
          {ollamaModels.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      <Button
        onClick={handleStart}
        disabled={!videoId || loading}
        className="w-full"
      >
        {loading ? 'Starting...' : 'Start Processing'}
      </Button>

      {!videoId && (
        <p className="text-xs text-gray-500 text-center">Upload a file first</p>
      )}
    </div>
  )
}
