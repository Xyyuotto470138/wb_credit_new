import { lazy, Suspense, useCallback, useState } from 'react'
import IntakePanel from './IntakePanel'
import SectionEditor from './SectionEditor'
import DraftExport from './DraftExport'
import { CaseModelPicker } from './ModelControls'
import { draftProgress, trancheProgress } from './dashboardModel'
import Badge from './components/Badge'
import StatusBanner from './components/StatusBanner'
import { casePath, post, requestListUrl } from './api/client'

const statuses = ['Provided', 'Found publicly', 'Can generate', 'Missing', 'Suggested', 'Not applicable', 'Dismissed']
const SourcePanel = lazy(() => import('./SourcePanel'))

function ExpectedRow({ item, busy, run, caseId, actor, showDocument, documents }) {
  const [reason, setReason] = useState('')
  const dismissed = item.status === 'Dismissed'
  const mutate = () => run(dismissed ? 'Restoring request' : 'Dismissing request', async () => {
    await post(`${casePath(caseId)}/expected-documents/${item.id}/${dismissed ? 'restore' : 'dismiss'}`, { actor, role: 'CA', reason })
    setReason('')
    return dismissed ? 'Request restored.' : 'Request dismissed. Any mandatory gap remains open.'
  })
  return <tr>
    <td><strong>{item.name}</strong><small>{item.mandatory ? 'Mandatory' : 'Optional'} · {item.usual_owner}</small>
      <details><summary>Why needed & actions</summary><p>{item.reason}</p><p>ES sections: {item.section_ids.join(', ')}</p>
        {item.alternative_group && <p>Alternative group: {item.alternative_group}. The configured minimum must be met.</p>}
        {item.dismiss_reason && <p>Dismissal reason: {item.dismiss_reason}</p>}
        {item.applicable && <><label>{dismissed ? 'Reason to restore' : 'Reason to dismiss'}<input value={reason} onChange={e => setReason(e.target.value)} disabled={busy} /></label>
          <button disabled={busy || !reason.trim() || !actor.trim()} onClick={mutate}>{dismissed ? 'Restore request' : 'Dismiss request'}</button>
          {item.mandatory && <small>Dismissal does not waive this mandatory gap.</small>}</>}
      </details>
    </td>
    <td><Badge>{item.status}</Badge><small>{!item.applicable ? 'Rule does not apply' : item.satisfied ? 'Input requirement met' : 'Evidence not yet complete'}</small></td>
    <td>{item.document_ids.length ? item.document_ids.map(id => {
      const doc = documents.find(d => d.id === id)
      return doc && <div key={id} className="source-link"><button className="link" onClick={() => showDocument(id)}>{doc.intake.title || doc.original_filename}</button>
        <small>{doc.synthetic ? 'Synthetic' : doc.origin === 'public' ? 'Public' : 'Supplied'} · {doc.period || 'Period needs review'}{doc.origin === 'public' ? ` · ${doc.confirmed_by ? 'CA confirmed' : 'CA confirmation pending'}` : ''}</small>
        {doc.origin === 'public' && <small>Retrieved {doc.retrieved_at?.slice(0, 10)}{doc.intake.cached && ' · Cached pack'}</small>}
      </div>
    }) : <span className="muted">No supporting document held</span>}
      {item.details.map((detail, i) => <small key={i}>{detail}</small>)}
    </td>
    <td><span>Search: {item.search_outcome}</span>{item.search_attempts.length > 0 && <details><summary>Search history</summary>
      {item.search_attempts.map((attempt, i) => <div key={i}><p>{attempt.attempted_at?.slice(0, 10)} · {attempt.provider} · {attempt.outcome}</p><p>{attempt.reason}</p>
        {(attempt.sources || []).map((source, j) => <p key={j}><a href={source.url} target="_blank" rel="noreferrer">Public source</a> · retrieved {source.retrieved_at?.slice(0, 10)}{source.cached && ' · Cached pack'}</p>)}
      </div>)}
    </details>}</td>
  </tr>
}

export default function CaseDashboard({ data, busy, run, actor, onDirtyChange }) {
  const [sectionId, setSectionId] = useState(1)
  const [dirty, setDirty] = useState(false)
  const trackDirty = useCallback(value => { setDirty(value); onDirtyChange?.(value) }, [onDirtyChange])
  const progress = draftProgress(data.sections)
  const [filter, setFilter] = useState('All')
  const [selectedId, setSelectedId] = useState(null)
  const selected = data.documents.find(d => d.id === selectedId)
  const confirm = doc => run('Confirming public evidence', async () => {
    await post(`${casePath(data.case.id)}/documents/${doc.id}/confirm`, { actor, role: 'CA' })
    return 'Public evidence confirmed. Partial public context still cannot replace full property or internal reports.'
  })
  const filtered = data.expected_documents.filter(e => filter === 'All' || e.status === filter)
  const count = status => data.counts.documents[status] || 0
  return <>
    <CaseModelPicker data={data} actor={actor} disabled={busy || dirty || data.case.workflow_state !== 'Draft'} run={run} />
    <StatusBanner workflowState={data.case.workflow_state} hasDraft={progress.saved > 0} />
    <section className="case-heading">
      <div><p className="eyebrow">{data.case.team_id.toUpperCase()} · {data.case.case_type} · {data.case.existing_client ? 'Existing client' : 'New to bank'}</p>
        <h1>{data.case.borrower_name}</h1><p>Draft preparation and evidence review</p></div>
      <div className="case-meta">{data.synthetic_demo && <><strong>SYNTHETIC DEMO DATA</strong><span>Fictional facility and internal records</span></>}<span>Public sources retain their own dates and provenance</span></div>
    </section>
    <div className="summary-grid" aria-label="Readiness overview">
      <div><span>Provided inputs</span><strong>{count('Provided')}</strong><small>Expected input categories</small></div>
      <div><span>Found publicly</span><strong>{count('Found publicly')}</strong><small>Confirmation / coverage shown below</small></div>
      <div><span>Missing inputs</span><strong>{count('Missing')}</strong><small>{data.counts.open_mandatory} mandatory requirements still open</small></div>
      <div><span>Draftable sections</span><strong>{data.counts.draftable}<small> / {data.sections.length}</small></strong><small>Full or partial input readiness</small></div>
    </div>
    <nav className="jump-links" aria-label="Dashboard sections"><a href="#sections">Draft progress</a><a href="#intake">Add documents</a><a href="#expected">Expected inputs</a><a href="#section-editor">Section editor</a><a href="#draft-export">Draft template export</a><a href="#requests">Requests by owner</a><a href="#documents">Document register</a></nav>
    <section className="panel" aria-label="Saved draft progress">
      <h2>Saved draft progress</h2>
      <div className="summary-grid"><div><span>Saved sections</span><strong>{progress.saved} / {data.sections.length}</strong></div><div><span>CA confirmed now</span><strong>{progress.confirmed}</strong></div><div><span>Stale · review required</span><strong>{progress.stale}</strong></div><div><span>N/A with reason</span><strong>{progress.na}</strong></div></div>
      <p>Saved sections may still have gaps. {data.counts.open_mandatory} mandatory input requirements remain open. Submission checks and reviewer workflow are not available in this prototype build.</p>
      {data.synthetic_demo && <><h3>Demo input progression</h3><div className="tranche-progress">{trancheProgress(data).map(t => <div key={t.number}><strong>Tranche {t.number}</strong><p>{t.held} / {t.total} exact demo files currently usable</p></div>)}</div><small>Tracks original pack hashes, not draft completeness. A revised source may supersede an original tranche file.</small></>}
      {!!progress.stale && <p className="notice">Stale sections retain saved wording. Open each affected section to review changes and choose when to redraft. Redraft prerequisites before dependent sections.{data.synthetic_demo && ' For the revised demo valuation: 8 → 9 → 11 → 14.'}</p>}
    </section>
    <IntakePanel data={data} busy={busy} run={run} />
    <section className="panel" id="expected">
      <div className="panel-heading"><div><h2>Expected inputs</h2><p>Missing means evidence is not yet held or complete. Public context may cover only part of a requirement.</p></div>
        <button className="primary" disabled={busy || !actor.trim()} onClick={() => run('Checking public sources', async () => {
          const result = await post(`${casePath(data.case.id)}/public-search`, { actor, role: 'CA' })
          return `Public search: ${result.search?.outcome || 'not run'}. ${result.search?.reason || ''}`
        })}>Check public sources</button>
      </div>
      <p className="mode-label">Search mode: <strong>{data.search_mode}</strong> · Saved evidence keeps its original retrieval date. No live search or model calls.</p>
      <div className="toolbar"><label>Input status<select value={filter} onChange={e => setFilter(e.target.value)}><option>All</option>{statuses.map(s => <option key={s}>{s}</option>)}</select></label><span>{filtered.length} of {data.expected_documents.length} input categories</span></div>
      <div className="table-scroll"><table className="expected-table"><thead><tr><th>Input / usual owner</th><th>Status / completeness</th><th>Supporting evidence</th><th>Public search</th></tr></thead><tbody>
        {filtered.map(item => <ExpectedRow key={item.id} item={item} busy={busy} run={run} caseId={data.case.id} actor={actor} documents={data.documents} showDocument={setSelectedId} />)}
        {!filtered.length && <tr><td colSpan="4">No inputs with this status.</td></tr>}
      </tbody></table></div>
      {data.generation_offers.length > 0 && <div className="generation-offers"><h3>Generation offers</h3><div className="offer-grid">
        {data.generation_offers.map(offer => <div key={offer.expected_id}><strong>{offer.kind === 'spread' ? 'Financial spread' : 'Industry code suggestion'}</strong><p>{offer.description}</p><small>{offer.source_confirmation_pending ? 'Public source confirmation pending. ' : ''}{offer.kind === 'spread' && data.demo_spread_available ? 'Generate explicitly, then review the validation result.' : offer.note}</small>{offer.kind === 'spread' && data.demo_spread_available ? <><p>Local saved ESR FY2025 transcription · mock only. Python validates the core Group rows for 2025 and 2024.</p><button disabled={busy || dirty || !actor.trim() || data.case.workflow_state !== 'Draft'} onClick={() => run('Generating saved mock spread', async () => {
          const result = await post(`${casePath(data.case.id)}/demo/spread`, { actor, role: 'CA' })
          if (result.spread.validation_status !== 'valid') throw new Error(`Spread needs review: ${result.spread.issues.join('; ')}`)
          return 'Validated mock core spread saved. Review source figures in section 10; other analytics and industry mapping gaps remain.'
        })}>Generate saved mock spread</button></> : <><small>{offer.kind !== 'spread' && 'Industry mapping remains an explicit review gap; no code is inferred or confirmed automatically.'}</small><button disabled>Generation not yet available</button></>}</div>)}
      </div></div>}
    </section>
    <section className="panel" id="sections"><div className="panel-heading"><div><h2>ES section readiness</h2><p>All {data.sections.length} sections remain visible. Open any section to edit, review sources, chat or inspect saved versions. Changes may make dependent sections Stale.</p></div></div>
      <div className="table-scroll"><table><thead><tr><th>Section</th><th>Readiness</th><th>Input completeness / remaining gaps</th></tr></thead><tbody>
        {data.sections.map(section => <tr key={section.section_id}><td><button className="link" disabled={busy || dirty} onClick={() => { setSectionId(section.section_id); document.getElementById('section-editor-heading')?.focus(); document.getElementById('section-editor')?.scrollIntoView() }}>{section.section_id}. {section.name}</button><small>{section.current_draft_id ? 'Saved version available' : 'No saved draft'}</small></td><td><Badge>{section.readiness}</Badge></td>
          <td><span>{section.completeness === 'full' ? 'Full' : section.completeness === 'partial' ? 'Partial' : section.readiness === 'Not applicable' ? 'Not applicable' : 'Not ready'}</span>
            {section.na_reason && <p>{section.na_reason}</p>}{section.gaps.length > 0 && <details><summary>{section.gaps.length} named gap{section.gaps.length !== 1 ? 's' : ''}</summary><ul>{section.gaps.map((gap, i) => <li key={i}>{gap}</li>)}</ul></details>}</td></tr>)}
      </tbody></table></div>
    </section>
    <SectionEditor data={data} actor={actor} busy={busy} run={run} onDirtyChange={trackDirty} sectionId={sectionId} onSelect={setSectionId} />
    <DraftExport data={data} actor={actor} busy={busy} dirty={dirty} run={run} />
    <section className="panel" id="requests"><div className="panel-heading"><div><h2>Requests by owner</h2><p>Send these requests through your usual channels. Export prepares a text file.</p></div><a className="button" href={requestListUrl(data.case.id)}>Export request list</a></div>
      <div className="request-grid">{Object.entries(data.gaps).map(([owner, items]) => <div key={owner}><h3>{owner === 'client' ? 'Client' : owner === 'internal team' ? 'Internal team' : owner} <span className="muted">({items.length})</span></h3>
        {!items.length && <p>No open requests.</p>}{items.map(item => <details key={item.id}><summary>{item.name}{item.mandatory ? ' · mandatory' : ''}</summary><p>{item.reason}</p><p>Sections {item.section_ids.join(', ')} · Search: {item.search_outcome}</p><p>{item.note}</p>{item.details.map((detail, i) => <p key={i}>{detail}</p>)}{item.dismiss_reason && <p>Dismissal: {item.dismiss_reason}</p>}</details>)}
      </div>)}</div>
    </section>
    <section className="panel" id="documents"><div className="panel-heading"><div><h2>Document register</h2><p>{data.documents.length} stored versions. Pending and historical evidence remains available for review.</p></div></div>
      <div className="table-scroll"><table><thead><tr><th>Document</th><th>Origin / period</th><th>Version / review</th><th>Source</th></tr></thead><tbody>
        {data.documents.map(doc => <tr key={doc.id}><td><button className="link" onClick={() => setSelectedId(doc.id)}>{doc.original_filename}</button><small>{doc.synthetic && 'SYNTHETIC DEMO DATA'}</small></td>
          <td>{doc.origin}<small>{doc.period || 'Period needs review'}</small></td><td>Revision {doc.revision} · {doc.conflict_status === 'pending' ? 'Manual review required' : doc.current ? 'Current usable version' : 'Historical / superseded'}
            {doc.supersedes_id && <small>Replaces version {data.documents.find(d => d.id === doc.supersedes_id)?.revision || doc.supersedes_id}</small>}
            {(doc.intake.issues || []).map((issue, i) => <small key={i}>{issue}</small>)}
            {doc.origin === 'public' && <small>{doc.confirmed_by ? `CA confirmed by ${doc.confirmed_by}` : 'CA confirmation pending'}</small>}
          </td><td>{doc.url ? <><a href={doc.url} target="_blank" rel="noreferrer">Public source</a><small>Retrieved {doc.retrieved_at?.slice(0, 10)}{doc.intake.cached && ' · Cached pack'}</small></> : 'Supplied case evidence'}</td></tr>)}
        {!data.documents.length && <tr><td colSpan="4">No documents provided yet. Add the first tranche above.</td></tr>}
      </tbody></table></div>
    </section>
    {selected && <Suspense fallback={<p role="status">Loading source viewer…</p>}><SourcePanel key={selected.id} doc={selected} caseId={data.case.id} close={() => setSelectedId(null)} confirm={confirm} busy={busy || !actor.trim()} /></Suspense>}
  </>
}
