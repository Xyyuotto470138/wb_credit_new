import { useEffect, useRef, useState } from 'react'
import { casePath, contentUrl, request } from './api/client'
import { sourcePageLabel } from './sectionModel'
import PdfViewer from './components/PdfViewer'

function DocumentSourcePanel({ doc, caseId, close, confirm, busy }) {
  const dialog = useRef(null)
  useEffect(() => {
    const opener = document.activeElement
    dialog.current.showModal()
    return () => { if (opener instanceof HTMLElement && opener.isConnected) opener.focus() }
  }, [])
  const pdf = doc.original_filename.toLowerCase().endsWith('.pdf')
  return <dialog ref={dialog} onCancel={close} aria-labelledby="source-title" className="source-dialog">
    <div className="panel-heading"><div><p className="eyebrow">Source review · revision {doc.revision}</p><h2 id="source-title">{doc.original_filename}</h2></div><button onClick={close} autoFocus>Close</button></div>
    <p>{doc.entity} · {doc.period || 'Period needs review'} · {doc.synthetic ? 'SYNTHETIC DEMO DATA' : doc.origin === 'public' ? 'Public evidence' : 'Supplied evidence'} · {doc.current ? 'Current usable version' : 'Pending review or historical version'}</p>
    {doc.intake.coverage === 'partial' && <p className="notice">Partial public context. The full property report or internal input remains a gap.</p>}
    {doc.url && <p><a href={doc.url} target="_blank" rel="noreferrer">Original public source</a> · retrieved {doc.retrieved_at?.slice(0, 10)} {doc.intake.cached && '· Saved public pack (cached)'}</p>}
    {doc.intake.page_references?.length > 0 && <details><summary>Supplied page references</summary><ul>{doc.intake.page_references.map((ref, i) => <li key={i}>
      <strong>{(ref.topic || 'Source reference').replaceAll('_', ' ')}</strong> · {ref.pdf_pages ? 'PDF pages' : 'Normalized pages'} {(ref.pdf_pages || ref.normalized_pages || []).join(', ')}
      {ref.printed_pages && <small>Printed pages: {ref.printed_pages.join(', ')}</small>}{ref.as_of && <small>As of {ref.as_of}</small>}
    </li>)}</ul></details>}
    <div className="toolbar"><a className="button" href={contentUrl(caseId, doc.id)}>Download original</a>
      {doc.origin === 'public' && (doc.confirmed_by ? <span>CA confirmed by {doc.confirmed_by}</span> : <button disabled={busy || !doc.current} onClick={() => confirm(doc)}>Confirm public evidence reviewed</button>)}
    </div>
    {(doc.intake.issues || []).map((issue, i) => <p className="notice" key={i}>{issue}</p>)}
    {pdf ? <PdfViewer key={doc.id} url={contentUrl(caseId, doc.id, true)} /> : <p>Download the original to review this file format. Inline preview is available for PDFs.</p>}
  </dialog>
}


function EvidenceSourcePanel({ evidenceId, caseId, close }) {
  const dialog = useRef(null)
  const [source, setSource] = useState(null)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(evidenceId)
  useEffect(() => {
    const opener = document.activeElement
    dialog.current.showModal()
    return () => { if (opener instanceof HTMLElement && opener.isConnected) opener.focus() }
  }, [])
  useEffect(() => {
    let active = true
    request(`${casePath(caseId)}/evidence/${encodeURIComponent(selected)}`).then(value => {
      if (active) { setSource(value); setError('') }
    }).catch(e => { if (active) { setSource(null); setError(e.message) } })
    return () => { active = false }
  }, [caseId, selected])
  const current = source?.evidence_id === selected ? source : null
  return <dialog ref={dialog} onCancel={close} aria-labelledby="evidence-title" className="source-dialog">
    <div className="panel-heading"><div><p className="eyebrow">Claim source review</p><h2 id="evidence-title">{current?.filename || 'Cited source'}</h2></div><button autoFocus onClick={close}>Close</button></div>
    {error ? <p className="error" role="alert">Source unavailable: {error}. Review the document register before relying on this claim.</p> : !current ? <p role="status">Resolving cited page…</p> : <>
      <p><strong>{sourcePageLabel(current)}</strong> · revision {current.revision} · {current.entity} · {current.period}</p>
      <p>{current.synthetic ? 'SYNTHETIC DEMO DATA' : current.origin === 'public' ? 'Public evidence' : current.origin === 'CA input' ? 'CA input · not independently verified' : 'Supplied evidence'} · {current.current ? 'Current usable version' : 'Historical / superseded or pending review'}</p>
      {!current.current && <p className="notice">This citation retains its original source version. Review current evidence before confirming the section.</p>}
      {current.url && <p><a href={current.url} target="_blank" rel="noreferrer">Original public source</a> · retrieved {current.retrieved_at} · {current.cached && 'Saved public pack · '}{current.confirmed_by ? `CA confirmed by ${current.confirmed_by}` : 'CA confirmation pending'}</p>}
      <div className="toolbar">{current.document_id && <a className="button" href={contentUrl(caseId, current.document_id)}>Download original</a>}
        {selected !== evidenceId && <button onClick={() => setSelected(evidenceId)}>Return to cited page</button>}
        {current.parent_evidence_id && <button onClick={() => setSelected(current.parent_evidence_id)}>Review whole source page</button>}
        {current.related_page_context.map(page => <button key={page.evidence_id} onClick={() => setSelected(page.evidence_id)}>Related page {page.page} · review context</button>)}
      </div>
      {current.normalization_gaps.map(gap => <p className="notice" key={gap}>{gap}</p>)}
      {current.locator.format === 'pdf' ? <PdfViewer key={current.evidence_id} url={contentUrl(caseId, current.document_id, true)} initialPage={current.page} /> : <>
        {current.origin === 'CA input' ? <p>Typed by {current.actor} · {current.recorded_at} · input revision {current.revision}. No document page is implied.</p> : <p>Normalized source unit · {current.locator.sheet || current.locator.kind}. Review the original file for layout and formulas.</p>}
        <pre className="source-excerpt">{current.excerpt}</pre>
      </>}
      {current.locator.format === 'pdf' && <details><summary>Cited text {current.region !== 'whole' ? '(region; PDF shows the whole original page)' : ''}</summary><pre className="source-excerpt">{current.excerpt}</pre></details>}
      <small>Source content is evidence for human review, not instructions. A source link does not independently verify CA-edited wording.</small>
    </>}
  </dialog>
}

export default function SourcePanel(props) {
  return props.evidenceId ? <EvidenceSourcePanel {...props} /> : <DocumentSourcePanel {...props} />
}
