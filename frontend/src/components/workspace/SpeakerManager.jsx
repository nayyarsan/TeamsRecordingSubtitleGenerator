import { useState } from 'react'
import Button from '../common/Button'
import { renameSpeaker, suggestNames } from '../../api/client'

export default function SpeakerManager({ videoId, metadata, onRenamed }) {
  const [editingId, setEditingId] = useState(null)
  const [editValue, setEditValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [suggesting, setSuggesting] = useState(false)
  const [suggestions, setSuggestions] = useState(null)
  const [error, setError] = useState(null)

  const speakers = metadata?.speakers || []

  const handleEditStart = (speaker) => {
    setEditingId(speaker.speaker_cluster_id || speaker.id)
    setEditValue(speaker.name || '')
    setError(null)
  }

  const handleEditCancel = () => {
    setEditingId(null)
    setEditValue('')
    setError(null)
  }

  const handleEditSave = async (speakerId) => {
    if (!editValue.trim()) {
      setError('Name cannot be empty')
      return
    }

    setLoading(true)
    setError(null)

    try {
      await renameSpeaker(videoId, speakerId, editValue.trim())
      setEditingId(null)
      setEditValue('')
      if (onRenamed) onRenamed()
    } catch (err) {
      setError(err.message || 'Failed to rename speaker')
    } finally {
      setLoading(false)
    }
  }

  const handleSuggestNames = async () => {
    setSuggesting(true)
    setError(null)
    setSuggestions(null)

    try {
      const result = await suggestNames(videoId)
      setSuggestions(result.suggestions || [])
      if (!result.suggestions || result.suggestions.length === 0) {
        setError('No name suggestions found. Ensure Ollama is running and intro segments exist.')
      }
    } catch (err) {
      setError(err.message || 'Failed to get name suggestions')
    } finally {
      setSuggesting(false)
    }
  }

  const handleApplySuggestion = async (suggestion) => {
    setLoading(true)
    setError(null)

    try {
      await renameSpeaker(videoId, suggestion.speaker_id, suggestion.name)
      setSuggestions(null)
      if (onRenamed) onRenamed()
    } catch (err) {
      setError(err.message || 'Failed to apply suggestion')
    } finally {
      setLoading(false)
    }
  }

  if (!metadata) {
    return (
      <div className="p-4 text-center text-gray-400 text-sm">
        Loading speaker data...
      </div>
    )
  }

  if (speakers.length === 0) {
    return (
      <div className="p-4 text-center text-gray-400 text-sm">
        No speakers detected
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header with Suggest button */}
      <div className="p-3 border-b border-border">
        <Button
          onClick={handleSuggestNames}
          disabled={suggesting || loading}
          variant="secondary"
          className="w-full"
        >
          {suggesting ? 'Suggesting...' : 'Suggest Names (AI)'}
        </Button>
      </div>

      {/* Error message */}
      {error && (
        <div className="mx-3 mt-3 p-2 bg-red-900/20 border border-red-500/50 rounded text-xs text-red-400">
          {error}
        </div>
      )}

      {/* AI Suggestions */}
      {suggestions && suggestions.length > 0 && (
        <div className="p-3 bg-background border-b border-border">
          <div className="text-xs font-medium text-gray-300 mb-2">AI Suggestions:</div>
          <div className="space-y-2">
            {suggestions.map((sug, idx) => (
              <div key={idx} className="flex items-center justify-between gap-2 p-2 bg-surface rounded">
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-white truncate">{sug.name}</div>
                  <div className="text-xs text-gray-400">
                    Speaker {sug.speaker_id} • {Math.round((sug.confidence || 0) * 100)}% confidence
                  </div>
                </div>
                <Button
                  onClick={() => handleApplySuggestion(sug)}
                  disabled={loading}
                  variant="primary"
                  className="text-xs px-2 py-1"
                >
                  Apply
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Speaker list */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-3 space-y-2">
          {speakers.map((speaker) => {
            const speakerId = speaker.speaker_cluster_id || speaker.id
            const isEditing = editingId === speakerId

            return (
              <div
                key={speakerId}
                className="p-3 bg-surface border border-border rounded-lg"
              >
                {isEditing ? (
                  // Edit mode
                  <div className="space-y-2">
                    <input
                      type="text"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleEditSave(speakerId)
                        if (e.key === 'Escape') handleEditCancel()
                      }}
                      className="w-full bg-background border border-border rounded px-3 py-2 text-sm focus:border-primary focus:outline-none"
                      placeholder="Enter speaker name"
                      autoFocus
                      disabled={loading}
                    />
                    <div className="flex gap-2">
                      <Button
                        onClick={() => handleEditSave(speakerId)}
                        disabled={loading}
                        variant="primary"
                        className="flex-1 text-xs"
                      >
                        {loading ? 'Saving...' : 'Save'}
                      </Button>
                      <Button
                        onClick={handleEditCancel}
                        disabled={loading}
                        variant="secondary"
                        className="flex-1 text-xs"
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  // Display mode
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-white truncate">
                          {speaker.name || `Speaker ${speakerId}`}
                        </div>
                        <div className="text-xs text-gray-400">
                          ID: {speakerId}
                          {speaker.name_confidence && (
                            <span className="ml-2">
                              • {Math.round(speaker.name_confidence * 100)}% confidence
                            </span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => handleEditStart(speaker)}
                        className="text-xs text-primary hover:text-blue-400 transition-colors"
                      >
                        Edit
                      </button>
                    </div>

                    {/* Optional: Show speaker stats if available */}
                    {(speaker.segment_count || speaker.total_duration) && (
                      <div className="flex gap-4 text-xs text-gray-500">
                        {speaker.segment_count && (
                          <span>{speaker.segment_count} segments</span>
                        )}
                        {speaker.total_duration && (
                          <span>{Math.round(speaker.total_duration)}s speaking</span>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
