import { useEffect, useRef, useState } from 'react'
import { casePath, post, request } from './api/client'
import { exportRevision, mergeExportHistory } from './dashboardModel'

export function ExportPreview({ preview }) {
  return <>
    <p className="notice"><strong>{preview.status}</strong> · {preview.layout_review}</p>
    <p>Template {preview.template.display_version} · {preview.template.id}</p>
    {!!preview.blockers.length && <div role="alert"><h3>Word export blocked</h3><ul>{preview.blockers.map(b => <li key={b}>{b}</li>)}</ul></div>}
    <div className="table-scroll"><table><thead><tr><th>Section</th><th>Saved version / state</th><th>Gaps</th></tr></thead><tbody>
      {Object.values(preview.sections).map(s => <tr key={s.section_id}><td>{s.section_id}</td><td>{s.draft ? s.draft.id : s.na_reason || 'No saved draft'}<small>{s.readiness} · {s.completeness}</small></td><td>{s.gaps.length ? <details><summary>{s.gaps.length} current gaps</summary><ul>{s.gaps.map((g, i) => <li key={i}>{g}</li>)}</ul></details> : 'No current input gaps'}
        {!!s.draft?.gaps.length && <details><summary>Saved draft gaps ({s.draft.gaps.length})</summary><ul>{s.draft.gaps.map((g, i) => <li key={i}>{g}</li>)}</ul></details>}</td></tr>)}
    </tbody></table></div>
    <details><summary>Template field and mapping gaps ({preview.mapping_gaps.length})</summary><ul>{preview.mapping_gaps.map((g, i) => <li key={i}>{g.anchor}: {g.reason}</li>)}</ul></details>
    <details><summary>Pinned request list</summary><pre>{preview.request_list}</pre></details>
    <p>{preview.public_source_policy}</p>
  </>
}

export default function DraftExport({ data, actor, busy, dirty, run }) {
  const [preview, setPreview] = useState(null)
  const [previewRevision, setPreviewRevision] = useState('')
  const [artifacts, setArtifacts] = useState([])
  const [error, setError] = useState('')
  const lock = useRef(false)
  const path = `${casePath(data.case.id)}/exports`
  const revision = exportRevision(data)
  const outdated = previewRevision !== revision
  const disabled = busy || dirty || !actor.trim() || data.case.workflow_state !== 'Draft'
  useEffect(() => {
    let active = true
    request(path).then(value => { if (active) setArtifacts(current => mergeExportHistory(current, value)) }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [path])
  const execute = (label, task) => {
    if (lock.current) return
    lock.current = true
    run(label, async () => {
      setError('')
      try { return await task() }
      catch (e) { setError(e.message); setPreviewRevision(''); throw e }
    }).finally(() => { lock.current = false })
  }
  return <section className="panel" id="draft-export">
    <h2>Draft template export</h2>
    <p>Preview the saved sections, template pin and gaps before creating a Word copy. The bundle includes the Word draft, source manifest and request list. It records no submission or approval.</p>
    {dirty && <p className="notice">Save or discard local section/chat input before preparing an export.</p>}
    {error && <p role="alert" className="error">{error}</p>}
    <div className="toolbar"><button disabled={disabled} onClick={() => execute('Preparing draft export preview', async () => {
      setPreview(await request(`${path}/preview`)); setPreviewRevision(revision)
      return 'Export preview prepared. Review all gaps before creating a draft bundle.'
    })}>Preview draft export</button>
      <button className="primary" disabled={disabled || !preview || outdated || !!preview.blockers.length} onClick={() => execute('Creating draft bundle', async () => {
        const artifact = await post(path, { actor, role: 'CA', expected_preview_token: preview.preview_token })
        setArtifacts(previous => mergeExportHistory(previous, [artifact])); setPreviewRevision('')
        return 'Draft bundle saved. Download it below; the case remains in Draft.'
      })}>Create draft bundle</button></div>
    {preview && <>{outdated && <p className="notice">Refresh the preview before creating another export. Saved versions or inputs may have changed.</p>}<ExportPreview preview={preview} /></>}
    <h3>Saved export history</h3>
    <p>Each download is an immutable snapshot from its recorded time. Later edits do not update an earlier bundle.</p>
    {!artifacts.length && <p>No saved exports yet.</p>}
    <ul>{[...artifacts].reverse().map(a => <li key={a.id}><p>DRAFT · {a.created_at} · Template {(a.template || a.manifest?.template)?.display_version}</p><small>Export {a.id} · ES snapshot {a.es_version_id}</small><div className="toolbar">
      <a className="button" href={`/api${path}/${encodeURIComponent(a.id)}/bundle.zip`}>Download draft bundle</a>
      <a href={`/api${path}/${encodeURIComponent(a.id)}/document.docx`}>Word draft</a>
      <a href={`/api${path}/${encodeURIComponent(a.id)}/manifest`}>Source / gap manifest</a>
      <a href={`/api${path}/${encodeURIComponent(a.id)}/request-list.txt`}>Pinned request list</a>
    </div></li>)}</ul>
  </section>
}
