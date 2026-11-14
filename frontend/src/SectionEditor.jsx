import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { casePath, post, request } from './api/client'
import { changedClaims, editableClaim, sameRevision, sourcePageLabel, versionToken } from './sectionModel'
import Badge from './components/Badge'
import SectionChat from './SectionChat'
import VersionHistory from './VersionHistory'
import { ModelOptions, ModelCompare } from './ModelControls'

const SourcePanel = lazy(() => import('./SourcePanel'))

export function SectionContent({ draft, edits, setEdits, disabled, showSource }) {
  const metadata = draft.claim_spans.find(c => c.kind === 'draft_metadata')
  return <>
    <p className="mode-label">{metadata?.label || 'Draft for CA review'}</p>
    {draft.claim_spans.filter(c => c.kind !== 'draft_metadata').map((claim, index) => <article className="claim" key={claim.id}>
      <h3>{index + 1}. {claim.kind === 'facility' ? `${claim.facility} · ${claim.field}` : claim.kind === 'computed' ? claim.value?.metric : claim.kind.replaceAll('_', ' ')}</h3>
      {editableClaim(claim) ? <label>CA wording · claim {index + 1}<textarea rows={4} maxLength={20000} readOnly={disabled}
        value={edits[claim.id] ?? claim.text} onChange={e => setEdits(previous => ({ ...previous, [claim.id]: e.target.value }))} /></label>
        : <><p className="claim-text">{claim.text}</p><small>Read-only supplied input or Python computation.</small></>}
      {claim.value && <p>{claim.value.synthetic && <strong>SYNTHETIC DEMO DATA · </strong>}{claim.value.proxy && <strong>PROXY · </strong>}{claim.value.value} {claim.value.unit} {claim.value.currency} · {claim.value.period} · {claim.value.scope}</p>}
      {claim.ca_edit && <p className="notice">CA-edited wording · {claim.ca_edit.actor} · {claim.ca_edit.recorded_at}. Source links retained for review; not independently verified.</p>}
      {claim.ca_position && <p>CA input · {claim.ca_position.actor} · {claim.ca_position.recorded_at}. Human position, not independently verified.</p>}
      {claim.ca_confirmation && <p>Supplied description confirmed by {claim.ca_confirmation.actor}.</p>}
      {claim.dependency_draft_id && <small>From section {claim.dependency_section_id} · draft {claim.dependency_draft_id}</small>}
      <ul className="claim-sources">{(claim.evidence_ids || []).map(id => {
        const source = metadata?.source_register?.[id]
        return <li key={id}>{source ? <>
          <button className="link" onClick={() => showSource(id)}>{source.filename} · {sourcePageLabel(source)}</button>
          <small>{source.synthetic ? 'SYNTHETIC DEMO DATA · ' : ''}{source.origin} · revision {source.revision}{source.origin === 'CA input' && ` · ${source.actor} · ${source.recorded_at} · not independently verified`}</small>
          {source.url && <small><a href={source.url} target="_blank" rel="noreferrer">Public source</a> · retrieved {source.retrieved_at} · {source.confirmed_by ? 'CA confirmed at drafting' : 'CA confirmation pending at drafting'}</small>}
        </> : <span className="notice">Source reference unavailable: {id}. Review required.</span>}</li>
      })}</ul>
    </article>)}
    <details><summary>Saved section text and provenance</summary><pre className="saved-section">{draft.text}</pre></details>
  </>
}

function EditorSession({ data, sectionId, actor, busy, run, onDirtyChange }) {
  const [history, setHistory] = useState(null)
  const [chatDirty, setChatDirty] = useState(false)
  const [edits, setEdits] = useState({})
  const [error, setError] = useState('')
  const [conflict, setConflict] = useState(false)
  const [loading, setLoading] = useState(true)
  const [sourceId, setSourceId] = useState(null)
  const [unsecured, setUnsecured] = useState(false)
  const [position, setPosition] = useState('')
  const [modelId, setModelId] = useState('')
  const models = data.model_registry?.models || []
  const modelUnavailable = !models.some(m => m.id === (modelId || data.case.default_model_id || 'mock-v1') && m.runnable)
  const actionLock = useRef(false)
  const path = `${casePath(data.case.id)}/sections/${sectionId}`
  const section = history?.section
  const live = data.sections.find(s => s.section_id === sectionId)
  const draft = history?.versions.find(d => d.id === section?.current_draft_id)
  const replacements = changedClaims(draft, edits)
  const dirty = Object.keys(replacements).length > 0
  const changed = !!section && !sameRevision(section, live)
  const locked = data.case.workflow_state !== 'Draft' || !section?.applicable
  const disabled = busy || loading || locked || conflict || changed || !actor.trim()
  const pending = dirty || !!position || unsecured || chatDirty
  useEffect(() => {
    onDirtyChange(pending)
    const warn = e => { e.preventDefault(); e.returnValue = '' }
    if (pending) window.addEventListener('beforeunload', warn)
    return () => { window.removeEventListener('beforeunload', warn); onDirtyChange(false) }
  }, [pending, onDirtyChange])
  useEffect(() => {
    let active = true
    request(`${path}/history`).then(value => { if (active) { setHistory(value); setLoading(false) } })
      .catch(e => { if (active) { setError(e.message); setLoading(false) } })
    return () => { active = false }
  }, [path])
  const reload = () => run('Reloading section', async () => {
    setLoading(true); setError('')
    try {
      const value = await request(`${path}/history`)
      setHistory(value); setEdits({}); setPosition(''); setUnsecured(false); setConflict(false)
    } catch (e) { setError(e.message); throw e }
    finally { setLoading(false) }
    return 'Section reloaded. Review current wording and inputs.'
  })
  const act = action => {
    if (actionLock.current) return
    actionLock.current = true
    run('Updating section', async () => {
      setError('')
      try {
        const options = { ...(modelId ? { model_id: modelId } : {}), confirm_unsecured: unsecured, ...(sectionId === 14 && position.trim() ? { ca_position: position } : {}) }
        if (action === 'create') await post(`${casePath(data.case.id)}/drafts/sections/${sectionId}`, { actor, role: 'CA', ...options })
        else await post(`${path}/${action}`, { ...versionToken(section, actor), ...(action === 'save' ? { replacements } : action === 'redraft' ? options : {}) })
        // If this refresh fails, do not retry the successful write with old tokens.
        setEdits({}); setPosition(''); setUnsecured(false); setConflict(true)
        const value = await request(`${path}/history`)
        setHistory(value); setConflict(false)
        return action === 'confirm' ? 'Section confirmed by CA. Named gaps remain open.' : 'New section version saved. Review wording, sources and named gaps.'
      } catch (e) {
        if (e.status === 409) setConflict(true)
        setError(e.message)
        throw e
      }
    }).finally(() => { actionLock.current = false })
  }
  return <>
    {error && <p role="alert" className="error">{error}</p>}
    {loading && <p role="status">Loading section…</p>}
    {(changed || conflict) && <p role="alert" className="notice">The section or its inputs changed, or the latest version needs reloading. Local wording is retained below. Copy it before discarding and reloading; review the current sources before applying it again.</p>}
    <div className="toolbar"><button disabled={busy || loading || chatDirty} onClick={reload}>{pending ? 'Discard local changes and reload' : 'Reload section'}</button>
      {section && <><Badge>{changed ? live.readiness : section.readiness}</Badge><span>Input completeness: {live.completeness}</span></>}
    </div>
    {locked && section && <p className="notice">{section.applicable ? `Read-only while case is ${data.case.workflow_state}.` : section.na_reason}</p>}
    {(section?.readiness === 'Stale' || live.readiness === 'Stale') && <p className="notice">Stale: keep the saved wording for review, or explicitly choose Redraft as new version below. Keeping or saving wording leaves this section Stale and cannot reconfirm it. Reload changed inputs first; earlier versions and confirmations remain in Saved version history.</p>}
    <aside className="section-gaps"><h3>Named gaps · current inputs and saved draft</h3>
      {[...new Set([...(live.gaps || []), ...(draft?.gaps || [])])].length ? <ul>{[...new Set([...(live.gaps || []), ...(draft?.gaps || [])])].map(g => <li key={g}>{g}</li>)}</ul> : <p>No named gaps recorded for this section.</p>}
      <small>CA confirmation records review of this section; it does not waive gaps or approve credit.</small>
    </aside>
    {draft && <>
      <p>Recorded model: {draft.model_version}</p>
      <p>Saved by {draft.author} · {draft.created_at}{dirty && <strong> · Unsaved wording changes</strong>}</p>
      <p>Only existing narrative wording is editable. Keep facts and numbers unchanged; use typed section chat below for new CA facts or numeric inputs.</p>
      <SectionContent draft={draft} edits={edits} setEdits={setEdits} disabled={disabled || !!position || unsecured || chatDirty} showSource={setSourceId} />
    </>}
    {!draft && !loading && <p>No saved draft for this section. Drafting uses the available evidence and retains named gaps.</p>}
    {[7, 8].includes(sectionId) && !locked && <label className="check"><input type="checkbox" checked={unsecured} disabled={disabled || dirty || chatDirty} onChange={e => setUnsecured(e.target.checked)} />I confirm the supplied term sheet’s unsecured description for the new draft.</label>}
    {sectionId === 14 && !locked && <label>CA-stated position for the new draft<textarea rows={3} value={position} disabled={disabled || dirty || chatDirty} onChange={e => setPosition(e.target.value)} maxLength={10000} /><small>The draft words this position; it does not form a recommendation. {data.case.ca_position && `Saved position: ${data.case.ca_position}`}</small></label>}
    {(position || unsecured) && draft && <p className="notice">New-draft options are set. Clear them to edit existing wording, or redraft to use these inputs.</p>}
    <label>Model for new draft<select value={modelId} disabled={disabled || dirty || chatDirty} onChange={e => setModelId(e.target.value)}>
      <option value="">Case default · {data.case.default_model_id || 'mock-v1'}</option><ModelOptions models={models} />
    </select></label><p>{modelUnavailable ? 'Estimate unavailable: choose an enabled offline mock.' : 'Estimated cost: US$0 for the selected offline mock.'} Live routes are disabled.</p>
    <div className="toolbar editor-actions">
      {draft ? <>
        <button className="primary" disabled={disabled || chatDirty || !dirty || Object.values(replacements).some(v => !v.trim())} onClick={() => act('save')}>Save wording as new version</button>
        <button disabled={disabled || modelUnavailable || chatDirty || dirty || (sectionId === 14 && !position.trim())} onClick={() => act('redraft')}>Redraft as new version</button>
        <button disabled={disabled || pending || section.readiness === 'Stale' || section.readiness === 'CA confirmed'} onClick={() => act('confirm')}>Confirm section reviewed</button>
        <a className="button" href={`/api${casePath(data.case.id)}/drafts/${encodeURIComponent(draft.id)}/preview.txt`}>Download saved section text</a>
      </> : <button className="primary" disabled={disabled || modelUnavailable || (sectionId !== 14 && section?.completeness === 'none') || (sectionId === 14 && !position.trim())} onClick={() => act('create')}>Create mock first draft</button>}
    </div>
    {draft && <p className="muted">Redrafting uses current evidence and accepted chat inputs. Earlier manual wording edits remain in history; they are not automatically carried into the new version. The text download contains the saved version.</p>}
    {!!history?.confirmations.length && <details><summary>Earlier confirmation records ({history.confirmations.length})</summary><ul>{history.confirmations.map(c => <li key={c.id}>{c.actor} · {c.created_at} · draft {c.draft_id}{!changed && live.readiness === 'CA confirmed' && section.readiness === 'CA confirmed' && c.draft_id === section.current_draft_id ? ' · current confirmed draft' : ' · historical confirmation'}</li>)}</ul></details>}
    {section && <ModelCompare key={`${section.current_draft_id}:${section.editor_revision}:${section.input_fingerprint}:${position}:${unsecured}`}
      caseId={data.case.id} section={section} actor={actor} models={models} run={run}
      disabled={disabled || dirty || chatDirty || (sectionId === 14 && !position.trim())}
      options={{ confirm_unsecured: unsecured, ...(sectionId === 14 && position.trim() ? { ca_position: position } : {}) }} />}
    {history && <VersionHistory history={history} live={live} caseId={data.case.id} showSource={setSourceId} />}
    {draft && section && <SectionChat caseId={data.case.id} section={section} draft={draft} actor={actor}
      disabled={disabled || dirty || !!position || unsecured || section.readiness === 'Stale'} run={run}
      onDirtyChange={setChatDirty} onChanged={async () => {
        setConflict(true)
        setHistory(await request(`${path}/history`))
        setConflict(false)
      }} />}
    {sourceId && <Suspense fallback={<p role="status">Loading source viewer…</p>}><SourcePanel key={sourceId} evidenceId={sourceId} caseId={data.case.id} close={() => setSourceId(null)} /></Suspense>}
  </>
}

export default function SectionEditor({ data, actor, busy, run, onDirtyChange, sectionId, onSelect }) {
  const [pending, setPending] = useState(false)
  useEffect(() => { onDirtyChange(pending); return () => onDirtyChange(false) }, [pending, onDirtyChange])
  return <section className="panel section-editor" id="section-editor">
    <h2 tabIndex={-1} id="section-editor-heading">Section editor</h2><p>Review the wording, supporting pages and named gaps before confirming.</p>
    <div className="toolbar"><label>ES section<select value={sectionId} disabled={busy || pending} onChange={e => onSelect(Number(e.target.value))}>
      {data.sections.map(s => <option key={s.section_id} value={s.section_id}>{s.section_id}. {s.name}</option>)}
    </select></label><button disabled={busy || pending || sectionId === data.sections[0].section_id} onClick={() => onSelect(data.sections[data.sections.findIndex(s => s.section_id === sectionId) - 1].section_id)}>Previous section</button><button disabled={busy || pending || sectionId === data.sections.at(-1).section_id} onClick={() => onSelect(data.sections[data.sections.findIndex(s => s.section_id === sectionId) + 1].section_id)}>Next section</button>{pending && <span>Save or discard local changes before changing sections or cases.</span>}</div>
    <EditorSession key={sectionId} data={data} sectionId={sectionId} actor={actor} busy={busy} run={run} onDirtyChange={setPending} />
  </section>
}
