import { useState } from 'react'
import { casePath } from './api/client'

export default function VersionHistory({ history, live, caseId, showSource }) {
  const [selectedId, setSelectedId] = useState('')
  const draft = history.versions.find(d => d.id === selectedId) || history.versions.at(-1)
  if (!draft) return <p>No saved versions yet.</p>
  const current = draft.id === live.current_draft_id
  const metadata = draft.claim_spans.find(c => c.kind === 'draft_metadata')
  return <details className="version-history">
    <summary>Saved version history ({history.versions.length})</summary>
    <p>Read-only snapshots retain exact wording, sources and gaps. Selecting history does not change the working draft.</p>
    <label>Saved version<select value={draft.id} onChange={e => setSelectedId(e.target.value)}>
      {[...history.versions].reverse().map((d, index) => <option key={d.id} value={d.id}>Version {history.versions.length - index} · {d.author} · {d.created_at}{d.id === live.current_draft_id ? ' · current' : ' · historical'}</option>)}
    </select></label>
    <p>{current ? 'Current saved version' : 'Historical saved version'}{current && live.readiness === 'Stale' ? ' · Stale' : ''} · {draft.model_version}</p>
    <p>Draft {draft.id} · Parent {draft.parent_id || 'First version'} · Template {draft.template_version_id}</p>
    {history.confirmations.filter(c => c.draft_id === draft.id).map(c => <p key={c.id}>{current && live.readiness === 'CA confirmed' ? 'Current CA confirmation' : 'Historical confirmation'} · {c.actor} · {c.created_at}</p>)}
    <pre className="saved-section">{draft.text}</pre>
    {!!draft.gaps.length && <ul>{draft.gaps.map((g, i) => <li key={i}>{g}</li>)}</ul>}
    <details><summary>Saved source references</summary><ul>{Object.entries(metadata?.source_register || {}).map(([id, source]) => <li key={id}>
      <button className="link" onClick={() => showSource(id)}>{source.filename} · {source.origin === 'CA input' ? `CA input · ${source.actor}` : `page ${source.page}`}</button>
      <small>{source.synthetic && 'SYNTHETIC DEMO DATA · '}{source.origin}{source.url && ` · ${source.url} · retrieved ${source.retrieved_at}`}</small>
    </li>)}</ul></details>
    <a className="button" href={`/api${casePath(caseId)}/drafts/${encodeURIComponent(draft.id)}/preview.txt`}>Download this saved version</a>
  </details>
}
