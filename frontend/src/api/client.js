const ROOT = '/api'
export const casePath = id => `/cases/${encodeURIComponent(id)}`
export const contentUrl = (caseId, documentId, preview = false) => `${ROOT}${casePath(caseId)}/documents/${encodeURIComponent(documentId)}/content${preview ? '?preview=true' : ''}`
export const requestListUrl = caseId => `${ROOT}${casePath(caseId)}/request-list`

export async function request(path, options = {}) {
  const response = await fetch(`${ROOT}${path}`, options)
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    const detail = typeof data.detail === 'string' ? data.detail : `Request failed (${response.status}). Check the supplied fields and retry.`
    const error = new Error(detail)
    error.status = response.status
    throw error
  }
  return response.json()
}
export const post = (path, body) => request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const dashboard = id => request(`${casePath(id)}/dashboard`)

export async function upload(caseId, file, metadata) {
  const params = new URLSearchParams({ filename: file.name, metadata: JSON.stringify(metadata) })
  return request(`${casePath(caseId)}/documents?${params}`, { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: file })
}
export async function demoMetadata(file, presets) {
  const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer())
  const hash = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('')
  return presets.find(p => p.sha256 === hash)?.metadata
}
