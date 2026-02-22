const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || err.error || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function uploadFile(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const form = new FormData()
    form.append('file', file)

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText))
      } else {
        reject(new Error(`Upload failed: ${xhr.status}`))
      }
    }
    xhr.onerror = () => reject(new Error('Upload failed'))
    xhr.open('POST', `${BASE}/upload`)
    xhr.send(form)
  })
}

export const startProcessing = (config) => request('/process', { method: 'POST', body: JSON.stringify(config) })

export const listVideos = () => request('/videos')

export const getMetadata = (id) => request(`/video/${id}/metadata`)

export const getSubtitles = (id) => request(`/video/${id}/subtitles`)

export const getFaces = (id) => request(`/video/${id}/faces`)

export const renameSpeaker = (videoId, speakerId, name) =>
  request(`/video/${videoId}/speakers/${speakerId}/rename`, { method: 'POST', body: JSON.stringify({ name }) })

export const suggestNames = (videoId) => request(`/video/${videoId}/suggest-names`, { method: 'POST' })

export const exportFile = async (videoId, format) => {
  const res = await fetch(`${BASE}/video/${videoId}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ format }),
  })
  if (!res.ok) throw new Error('Export failed')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${videoId}.${format === 'video' ? 'mp4' : format}`
  a.click()
  URL.revokeObjectURL(url)
}

export const getOllamaStatus = () => request('/ollama/status')

export const getOllamaModels = () => request('/ollama/models')

export const getSystemInfo = () => request('/system/info')
