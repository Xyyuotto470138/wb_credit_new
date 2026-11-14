import { useState } from 'react'
import FileUpload from './components/FileUpload'
import { casePath, demoMetadata, post, upload } from './api/client'

export default function IntakePanel({ data, busy, run }) {
  const [folderId, setFolderId] = useState(data.intake.folders[0]?.id || '')
  const [type, setType] = useState('')
  const [entity, setEntity] = useState(data.case.borrower_name)
  const [period, setPeriod] = useState('')
  const [scope, setScope] = useState('default')
  const [synthetic, setSynthetic] = useState(false)
  const [useDemo, setUseDemo] = useState(true)
  const [results, setResults] = useState([])
  const folder = data.intake.folders.find(f => f.id === folderId)
  const filesSelected = files => run('Uploading documents', async () => {
    const next = []
    for (const file of files) {
      try {
        if (file.size > 25 * 1024 * 1024) throw new Error('File exceeds the 25 MB intake limit.')
        const preset = useDemo ? await demoMetadata(file, data.intake.presets) : null
        const metadata = preset || { ...(type ? { catalogue_id: Number(type) } : {}),
          ...(entity.trim() ? { entity: entity.trim() } : {}), ...(period.trim() ? { period: period.trim() } : {}), scope, synthetic }
        next.push({ ...await upload(data.case.id, file, metadata), classification: preset ? 'Matching demo manifest (verified content hash)' : 'Supplied hints and automatic classification' })
      } catch (error) { next.push({ filename: file.name, outcome: 'rejected', explanations: [error.message] }) }
      setResults([...next])
    }
    return `${next.length} file(s) processed. Review the intake results below.`
  })
  return <section className="panel" id="intake">
    <div className="panel-heading"><div><h2>Add documents</h2><p>New inputs refresh the expected list and section readiness.</p></div></div>
    <div className="intake-grid">
      <div>
        <FileUpload onFiles={filesSelected} busy={busy} />
        <details className="upload-options"><summary>Classification hints for uploads</summary>
          <p>Hints apply to each selected file. Use automatic type detection for mixed document batches.</p>
          <div className="form-grid">
            <label>Document type<select value={type} disabled={busy} onChange={e => setType(e.target.value)}><option value="">Automatic detection</option>{data.expected_documents.filter(e => e.catalogue_id).map(e => <option key={e.id} value={e.catalogue_id}>{e.name}</option>)}</select></label>
            <label>Entity<input value={entity} disabled={busy} onChange={e => setEntity(e.target.value)} /></label>
            <label>Period / effective date<input placeholder="YYYY-MM-DD, FY2025 or 2026-Q3" value={period} disabled={busy} onChange={e => setPeriod(e.target.value)} /></label>
            <label>Evidence scope<input value={scope} disabled={busy} onChange={e => setScope(e.target.value)} /></label>
          </div>
          <label className="check"><input type="checkbox" checked={synthetic} disabled={busy} onChange={e => setSynthetic(e.target.checked)} /> Synthetic demo data</label>
        </details>
        <label className="check"><input type="checkbox" checked={useDemo} disabled={busy} onChange={e => setUseDemo(e.target.checked)} /> Use demo manifest hints for exact matching files</label>
        <small>Only verified demo content receives the manifest’s type, entity, effective date and synthetic label.</small>
      </div>
      <div className="folder-intake">
        <h3>Scan a configured folder</h3><p>Scan each tranche when it arrives. Repeating a scan reports duplicates and keeps the existing versions.</p>
        <label>Folder<select value={folderId} onChange={e => setFolderId(e.target.value)} disabled={busy || !data.intake.folders.length}>
          {!data.intake.folders.length && <option value="">No folders configured</option>}
          {data.intake.folders.map(f => <option key={f.id} value={f.id}>{f.label}</option>)}
        </select></label>
        <button className="primary" disabled={busy || !folder} onClick={() => run('Scanning folder', async () => {
          const next = await post(`${casePath(data.case.id)}/documents/scan`, { folder_id: folder.id, metadata_by_path: folder.metadata_by_path || {} })
          setResults(next)
          return `${folder.label}: ${next.length} file(s) processed.`
        })}>Scan folder</button>
        <small>Configured demo folders use the supplied manifest classifications. No background scan runs.</small>
      </div>
    </div>
    {results.length > 0 && <details className="intake-results" open><summary>Latest intake results · {results.length} files</summary>
      <ul>{results.map((r, i) => <li key={i}><strong>{r.filename}</strong> — {r.outcome}
        {r.document && <> · revision {r.document.revision} · {r.document.conflict_status === 'pending' ? 'Manual review required' : 'Classified'}</>}
        <small>{r.classification}</small>{r.explanations.map((text, j) => <p key={j}>{text}</p>)}</li>)}</ul>
    </details>}
  </section>
}
