import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { casePath, post, request } from '../api/client'
import { changedClaims, sourcePageLabel, versionToken } from '../sectionModel'
import AssistantPanel from './AssistantPanel'
import Comments from './Comments'
import Roundtrip from './Roundtrip'
import Preview from './Preview'
import SectionView, { SectionBody } from './SectionView'
import { buildBlocks } from './sectionContent'
import { trackedChanges } from './diff'
import { SECTION_ICON, sectionStatus, stage } from './status'
import ReviewTab, { ReviewBar } from './Review'
import UpdatesTab from './Updates'

const SourcePanel = lazy(() => import('../SourcePanel'))
const TONE = { Confirmed: 'green', 'In progress': 'blue', 'Update required': 'amber', 'Pending inputs': 'grey', 'Not started': 'grey', 'Not applicable': 'grey' }
const uniqueGaps = (section, draft) => [...new Set([...(section.gaps || []), ...(draft?.gaps || [])])]
const currentDraft = history => history?.versions.find(d => d.id === history.section.current_draft_id)
const fetchSection = path => Promise.all([request(`${path}/history`), request(`${path}/chat`).catch(() => ({ messages: [], proposals: [] }))])
const fetchUpdates = caseId => request(`${casePath(caseId)}/sections/updates`).catch(() => null)
const fetchThreads = caseId => request(`${casePath(caseId)}/threads`).catch(() => [])
const fetchSense = caseId => request(`${casePath(caseId)}/sense-checks`).catch(() => [])
// The mock assistant takes wording and facts only. Figures must reach the ES through a source file, so the system computes them.
const propose = (path, body) => post(path, body).catch(error => {
  if (/Quantitative facts/.test(error.message)) throw new Error('The assistant cannot take figures or dates in a typed note in mock mode. Figures must come from a source file so that the system computes them. Rephrase the note without numbers, or add the file on the Inputs screen.')
  throw error
})
const when = iso => new Date(iso).toLocaleString('en-SG', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })

function Rail({ data, tab, review, role, updates }) {
  const pending = data.counts.documents.Missing || 0
  const reviewing = review && review.state !== 'Draft'
  return <nav className="rail" aria-label="ES sections">
    <a className="top" href="#/inputs">Files {pending > 0 && <span className="chip amber">{pending} pending</span>}</a>
    <a className={`top${tab === 'full' ? ' on' : ''}`} href="#/workbench/full">Full ES</a>
    <a className={`top${tab === 'review' ? ' on' : ''}`} href="#/workbench/review">Review {review && <span className={`chip ${stage(review.state)[1]}`}>{role === 'CA' || review.state !== 'Submitted to Credit Head' ? stage(review.state)[0] : `${review.summary.reviewed} of ${review.summary.to_review}`}</span>}</a>
    {updates?.sections.length > 0 && <a className={`top${tab === 'updates' ? ' on' : ''}`} href="#/workbench/updates">What changed {updates.open > 0 && <span className="chip amber">{updates.open} to update</span>}</a>}
    <div className="sections">{data.sections.map(section => {
      const status = sectionStatus(section), [kind, mark] = SECTION_ICON[status]
      const entry = reviewing && review.sections.find(s => s.section_id === section.section_id)
      // During review the mark shows the checker's read of the section; a returned section shows as returned.
      const flag = !entry ? null : review.state === 'Returned to CA' ? (entry.returned ? ['ret', '↩', 'Returned'] : null)
        : entry.mark_current ? (entry.mark.status === 'reviewed' ? ['rev', '✓', 'Reviewed'] : ['qry', '?', 'Query raised']) : null
      return <a key={section.section_id} href={`#/workbench/${section.section_id}`} className={String(section.section_id) === tab ? 'on' : ''} title={flag ? flag[2] : status}>
        <span className="num">{section.section_id}</span><span className="lbl">{section.name}</span>
        {flag ? <span className={`dot ${flag[0]}`} aria-label={flag[2]}>{flag[1]}</span> : <span className={`dot ${kind}`} aria-label={status}>{mark}</span>}</a>
    })}</div>
    <div className="legend">{Object.entries(SECTION_ICON).map(([status, [kind, mark]]) => <span key={status}><i className={`dot ${kind}`}>{mark}</i>{status}</span>)}</div>
  </nav>
}

function Sources({ draft, selected, caseId }) {
  const [openId, setOpenId] = useState(null)
  const { numbering, metadata } = useMemo(() => buildBlocks(draft), [draft])
  return <div className="sources">
    {!numbering.size && <p className="empty">This section has no cited sources yet.</p>}
    {[...numbering].map(([id, n]) => {
      const source = metadata.source_register?.[id]
      return <div key={id} className={`source${id === selected ? ' on' : ''}`}>
        <b><sup className="cite">{n}</sup> {source?.filename || 'Source unavailable'}</b>
        {source && <><small>{sourcePageLabel(source)} · {source.synthetic ? 'SYNTHETIC DEMO DATA' : source.origin === 'public' ? 'Public source' : source.origin}
          {source.url && <> · <a href={source.url} target="_blank" rel="noreferrer">original</a>, retrieved {String(source.retrieved_at).slice(0, 10)}</>}</small>
          {id === selected && source.excerpt && <pre>{source.excerpt.slice(0, 1200)}</pre>}
          {source.origin !== 'CA input' && <button className="btn small" onClick={() => setOpenId(id)}>Open the page</button>}</>}
      </div>
    })}
    {openId && <Suspense fallback={null}><SourcePanel key={openId} evidenceId={openId} caseId={caseId} close={() => setOpenId(null)} /></Suspense>}
  </div>
}

function Panel({ tab, setTab, close, children, sources }) {
  return <aside className="panel">
    <div className="tabs"><button className={tab === 'assistant' ? 'on' : ''} onClick={() => setTab('assistant')}>Credit Assistant</button>
      <button className={tab === 'sources' ? 'on' : ''} onClick={() => setTab('sources')}>Sources</button>
      <button className="close" aria-label="Close panel" onClick={close}>×</button></div>
    {tab === 'assistant' ? children : sources}
  </aside>
}

function SectionTab({ data, spec, sectionId, actor, role, review, reloadReview, updates, threads, reloadThreads, busy, run, assistantOpen, closeAssistant, openAssistant }) {
  const [history, setHistory] = useState(null)
  const [chat, setChat] = useState(null)
  const [editing, setEditing] = useState(false)
  const [edits, setEdits] = useState({})
  const [unsecured, setUnsecured] = useState(false)
  const [position, setPosition] = useState('')
  const [panelTab, setPanelTab] = useState('assistant')
  const [sourceId, setSourceId] = useState(null)
  const [showVersions, setShowVersions] = useState(false)
  const [checks, setChecks] = useState([])
  const caseId = data.case.id
  const path = `${casePath(caseId)}/sections/${sectionId}`
  const live = data.sections.find(s => s.section_id === sectionId)
  const load = useCallback(async () => {
    const [nextHistory, nextChat] = await fetchSection(path)
    setHistory(nextHistory); setChat(nextChat); setChecks(await fetchSense(caseId))
  }, [path, caseId])
  useEffect(() => {
    let active = true
    fetchSection(path).then(([nextHistory, nextChat]) => { if (active) { setHistory(nextHistory); setChat(nextChat) } }).catch(() => {})
    fetchSense(caseId).then(list => { if (active) setChecks(list) })
    return () => { active = false }
  }, [path, caseId, live.current_draft_id, live.editor_revision, live.input_fingerprint])

  const section = history?.section
  const draft = currentDraft(history)
  const status = sectionStatus(live)
  // Only the maker changes the ES, and only while it is with them: in drafting, or on the sections a reviewer returned.
  const entry = review?.sections.find(s => s.section_id === sectionId)
  const state = data.case.workflow_state
  const locked = role !== 'CA' || !(state === 'Draft' || (state === 'Returned to CA' && entry?.editable))
  const proposal = chat?.proposals.find(p => p.status === 'pending' && p.base_draft_id === draft?.id)
  // The saved text carries a full source-register line for each CA input; show it in plain words here.
  const changes = useMemo(() => proposal && draft ? trackedChanges(draft.text, proposal.proposed_text).map(pieces =>
    pieces.length === 1 && /^\[CA\d+\]/.test(pieces[0].text) ? [{ ...pieces[0], text: 'Cited as CA input, not independently verified.' }] : pieces) : [], [proposal, draft])
  const replacements = changedClaims(draft, edits)
  const act = (label, task) => run(label, async () => { await task(); setEditing(false); setEdits({}); await load() })
  const options = { confirm_unsecured: unsecured, ...(sectionId === 14 && position.trim() ? { ca_position: position } : {}) }
  const create = () => act('Drafting section', () => post(`${casePath(caseId)}/drafts/sections/${sectionId}`, { actor, role: 'CA', ...options }))
  const redraft = () => act('Updating section', () => post(`${path}/redraft`, { ...versionToken(section, actor), ...options }))
  const save = () => act('Saving your wording', () => post(`${path}/save`, { ...versionToken(section, actor), replacements }))
  const confirm = () => act('Confirming section', () => post(`${path}/confirm`, versionToken(section, actor)))
  const decide = action => act(action === 'accept' ? 'Accepting change' : 'Rejecting change',
    () => post(`${path}/chat/${encodeURIComponent(proposal.id)}/decision`, { actor, role: 'CA', action, accept_numeric_input: false }))
  const send = message => act('Preparing a suggested change',
    () => propose(`${path}/chat`, { ...versionToken(section, actor), message, mode: 'fact', synthetic: !!data.synthetic_demo }))
  const cite = id => { setSourceId(id); setPanelTab('sources') }
  const changeBlock = body => act('Saving your content', () => post(`${path}/blocks`, { ...versionToken(section, actor), ...body }))
  const canAdd = draft?.claim_spans[0]?.parts && !locked && !proposal && !editing
  // The model sense check reads the tables that code does not check. It suggests; it never changes or passes anything.
  const sense = checks.find(c => c.section_id === sectionId)
  const runSense = () => run('Reading the tables for a sense check', async () => { setChecks(await post(`${path}/sense-check`, { actor })) })
  const resolveSense = findingId => run('Recording that you looked at it', async () => {
    setChecks(await post(`${casePath(caseId)}/sense-checks/${encodeURIComponent(sense.id)}/resolve`, { actor, finding_id: findingId }))
  })
  // A facility described as unsecured needs the analyst's confirmation. Only ask where it can apply to this case.
  const unsecuredGap = !!draft?.gaps.some(gap => /described as unsecured/.test(gap))
  const askUnsecured = [7, 8].includes(sectionId) && (spec ? unsecuredGap || !data.case.property_or_asset_security : true)
  const unsecuredLabel = spec ? 'I confirm that the facility described as unsecured in the deal papers is correctly described.' : "I confirm the term sheet's description of the RCF as unsecured."
  const needsPosition = sectionId === 14 && !position.trim() && !data.case.ca_position
  const blockedReason = role !== 'CA' ? 'Read only for reviewers.' : locked ? (state === 'Returned to CA' ? 'This section was not returned, so it stays as submitted.' : `Read only while the ES is ${stage(state)[0].toLowerCase()}.`) : !draft ? 'Draft the section first.'
    : status === 'Update required' ? 'Update the section first.' : proposal ? 'Accept or reject the suggested change first.' : ''

  return <div className={`shell${assistantOpen ? '' : ' no-panel'}`}>
    <Rail data={data} tab={String(sectionId)} review={review} role={role} updates={updates} />
    <main className="centre">
      <div className="secbar">
        <span className={`chip ${TONE[status]}`}>{status}</span>
        {draft && <span className="meta">Version {history.versions.length} · {when(draft.created_at)} · <button className="link" onClick={() => setShowVersions(v => !v)}>History</button></span>}
        <span className="spacer" />
        {draft && !locked && (editing
          ? <><button className="btn" disabled={busy} onClick={() => { setEditing(false); setEdits({}) }}>Cancel</button>
            <button className="btn primary" disabled={busy || !Object.keys(replacements).length || Object.values(replacements).some(v => !v.trim())} onClick={save}>Save wording</button></>
          : <>{draft.claim_spans[0]?.parts && <button className="btn" disabled={busy} title="A model reads the tables that code does not check and suggests what to recheck" onClick={runSense}>Sense check</button>}
            <button className="btn" disabled={busy || !!proposal} onClick={() => setEditing(true)}>Edit text</button>
            {(status === 'Update required' || unsecuredGap && unsecured) && <button className="btn primary" disabled={busy || needsPosition} onClick={redraft}>Update section</button>}
            <button className="btn primary" disabled={busy || !!proposal || status !== 'In progress'} onClick={confirm}>{status === 'Confirmed' ? 'Confirmed' : 'Confirm section'}</button></>)}
      </div>
      <ReviewBar entry={entry} review={review} role={role} actor={actor} caseId={caseId} busy={busy} run={run} reload={reloadReview} />
      {status === 'Update required' && (updates?.sections.some(e => e.section_id === sectionId)
        ? <p className="banner amber">New information affects this section. <a href="#/workbench/updates">See what changed</a> to get a proposed update that shows each change before it is applied. Update section redrafts the whole section instead.</p>
        : <p className="banner amber">An input this section relies on has changed. Your saved wording is kept. Choose Update section to redraft it from the current inputs.</p>)}
      {sense && draft && (sense.current
        ? <p className={`banner ${sense.open ? 'amber' : 'grey'}`}>Sense check by the model on this version: {sense.tables_checked ? `${sense.findings.length} suggested check${sense.findings.length === 1 ? '' : 's'} across ${sense.tables_checked} table${sense.tables_checked === 1 ? '' : 's'}${sense.findings.length ? `, ${sense.open} still to look at` : ''}.` : 'this section has no tables outside the code checks.'} {sense.note}</p>
        : <p className="banner grey">The section changed after the last sense check. Run Sense check again to refresh the suggestions.</p>)}
      {showVersions && history && <div className="versions card"><b>Saved versions</b>
        {[...history.versions].reverse().map((v, i) => <details key={v.id}><summary>Version {history.versions.length - i} · {v.author} · {when(v.created_at)}{v.id === section.current_draft_id ? ' · current' : ''}</summary><div className="box old"><SectionBody draft={v} onCite={cite} /></div></details>)}
        <small>Every version is kept. Rolling back to an earlier version is not built yet.</small></div>}
      {!history ? <p className="wb-loading">Loading section…</p> : <SectionView section={live} draft={draft} gaps={draft?.claim_spans[0]?.parts ? draft.gaps : uniqueGaps(live, draft)} onCite={cite} editing={editing} edits={edits} setEdits={setEdits} blockOps={canAdd ? changeBlock : null} busy={busy}
        sense={sense?.current ? sense : null} onResolve={locked ? null : resolveSense}
        layout={spec?.sections.find(s => s.id === sectionId)} caseId={caseId}>
        {proposal && <div className="change" role="region" aria-label="Suggested change">
          <div className="bar">Suggested change from the Credit Assistant <span className="spacer" />
            <button className="btn small" disabled={busy} onClick={() => decide('reject')}>Reject</button>
            <button className="btn small primary" disabled={busy} onClick={() => decide('accept')}>Accept change</button></div>
          {changes.map((pieces, i) => <p key={i}>{pieces.map((piece, k) => piece.type === 'add' ? <ins key={k}>{piece.text}</ins> : piece.type === 'del' ? <del key={k}>{piece.text}</del> : <span key={k}>{piece.text}</span>)}</p>)}
          {!changes.length && <p>No wording differences.</p>}
        </div>}
        {!draft && live.applicable && !locked && <div className="start">
          {status === 'Pending inputs' && <p className="banner amber">This section is waiting for inputs. See the gaps below, or add files on the Inputs screen.</p>}
          {askUnsecured && <label className="check"><input type="checkbox" checked={unsecured} onChange={e => setUnsecured(e.target.checked)} />{unsecuredLabel}</label>}
          {sectionId === 14 && <label>Your position, in your own words. The draft words this position; it does not form one for you.
            <textarea rows={3} value={position} maxLength={10000} onChange={e => setPosition(e.target.value)} /></label>}
          <button className="btn primary" disabled={busy || live.completeness === 'none' && sectionId !== 14 || needsPosition} onClick={create}>Draft this section</button>
        </div>}
        {draft && unsecuredGap && !locked && <label className="check start"><input type="checkbox" checked={unsecured} onChange={e => setUnsecured(e.target.checked)} />{unsecuredLabel} Then choose Update section.</label>}
        {draft && sectionId === 14 && status === 'Update required' && !locked && <label className="start">Your position for the updated draft
          <textarea rows={3} value={position} placeholder={data.case.ca_position || ''} maxLength={10000} onChange={e => setPosition(e.target.value)} /></label>}
      </SectionView>}
      <Comments caseId={caseId} sectionId={sectionId} parts={spec?.sections.find(s => s.id === sectionId)?.parts} threads={threads}
        actor={actor} role={role} busy={busy} run={run} reload={reloadThreads} />
    </main>
    {!assistantOpen && <button className="reopen" onClick={openAssistant} aria-label="Open the Credit Assistant panel">Credit Assistant</button>}
    {assistantOpen && <Panel tab={panelTab} setTab={setPanelTab} close={closeAssistant}
      sources={draft ? <Sources draft={draft} selected={sourceId} caseId={caseId} /> : <p className="empty">No draft yet.</p>}>
      <AssistantPanel chat={chat} busy={busy} disabledReason={blockedReason} onSend={send}
        scope={<><b>Section {sectionId}, {live.name}.</b> I change only this section. I can read the others.</>} />
    </Panel>}
  </div>
}

function FullEs({ data, spec, actor, role, review, updates, reloadThreads, busy, run, assistantOpen, closeAssistant, openAssistant }) {
  const [histories, setHistories] = useState(null)
  const [artifact, setArtifact] = useState(null)
  const [target, setTarget] = useState('')
  const [panelTab, setPanelTab] = useState('assistant')
  const caseId = data.case.id
  const stamp = data.sections.map(s => `${s.current_draft_id}:${s.editor_revision}`).join()
  useEffect(() => {
    let active = true
    Promise.all(data.sections.map(s => request(`${casePath(caseId)}/sections/${s.section_id}/history`)))
      .then(list => { if (active) setHistories(list) }).catch(() => {})
    return () => { active = false }
    // Reload when any section's saved version changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId, stamp])
  const exportEs = () => run('Preparing the ES in the Word template', async () => {
    const path = `${casePath(caseId)}/exports`
    const preview = await request(`${path}/preview`)
    if (preview.blockers.length) throw new Error(`The ES cannot be exported yet. ${preview.blockers.join(' ')}`)
    setArtifact({ ...await post(path, { actor, role: 'CA', expected_preview_token: preview.preview_token }), path })
  })
  const send = message => run('Preparing a suggested change', async () => {
    const section = histories.find(h => String(h.section.section_id) === target).section
    await propose(`${casePath(caseId)}/sections/${target}/chat`, { ...versionToken(section, actor), message, mode: 'fact', synthetic: !!data.synthetic_demo })
    window.location.hash = `#/workbench/${target}`
  })
  const drafted = data.sections.filter(s => s.current_draft_id)
  return <div className={`shell${assistantOpen ? '' : ' no-panel'}`}>
    <Rail data={data} tab="full" review={review} role={role} updates={updates} />
    <main className="centre">
      <div className="secbar"><span className="meta">{drafted.length} of {data.sections.length} sections drafted · {data.sections.filter(s => sectionStatus(s) === 'Confirmed').length} confirmed</span><span className="spacer" />
        {artifact && <a className="btn" href={`/api${artifact.path}/${encodeURIComponent(artifact.id)}/document.docx`}>Download Word ES</a>}
        {drafted.length > 0 && <a className="btn" href="#/workbench/preview">Preview</a>}
        {role === 'CA' && data.case.workflow_state === 'Draft' && spec && drafted.length > 0 && <Roundtrip caseId={caseId} actor={actor} busy={busy} run={run} onDone={reloadThreads} />}
        <button className="btn primary" disabled={busy || !drafted.length || role !== 'CA' || data.case.workflow_state !== 'Draft'} onClick={exportEs}>Export ES to Word</button></div>
      {artifact && <p className="banner green">Draft ES created in the bank's Word template (template {(artifact.template || artifact.manifest?.template)?.display_version}). It is a draft for review, not a submission.</p>}
      {!histories ? <p className="wb-loading">Loading the ES…</p> : data.sections.map((section, i) => {
        const draft = currentDraft(histories[i]), status = sectionStatus(section)
        return <div key={section.section_id} className="full-section">
          <div className="secbar slim"><span className={`chip ${TONE[status]}`}>{status}</span><span className="spacer" /><a className="link" href={`#/workbench/${section.section_id}`}>Open section</a></div>
          <SectionView section={section} draft={draft} layout={spec?.sections.find(s => s.id === section.section_id)} caseId={caseId}
            gaps={draft ? (draft.claim_spans[0]?.parts ? draft.gaps : uniqueGaps(section, draft)) : section.gaps.slice(0, 3)} onCite={() => { window.location.hash = `#/workbench/${section.section_id}` }} />
        </div>
      })}
    </main>
    {!assistantOpen && <button className="reopen" onClick={openAssistant} aria-label="Open the Credit Assistant panel">Credit Assistant</button>}
    {assistantOpen && <Panel tab={panelTab} setTab={setPanelTab} close={closeAssistant} sources={<p className="empty">Open a section to see its sources.</p>}>
      <AssistantPanel chat={null} busy={busy || !histories} onSend={send} disabledReason={role !== 'CA' ? 'Read only for reviewers.' : data.case.workflow_state !== 'Draft' ? 'Open a returned section to change it.' : ''} sections={drafted.filter(s => sectionStatus(s) !== 'Update required')} target={target} setTarget={setTarget}
        scope={<><b>Whole ES.</b> Tell me which section a change is for. I will show the suggested change in that section for you to accept.</>} />
    </Panel>}
  </div>
}

export default function Workbench({ tab, ...props }) {
  const { data, role } = props
  const caseId = data.case.id
  const [review, setReview] = useState(null)
  const [checks, setChecks] = useState([])
  // Review threads: comments between the roles. They are loaded with the paper and after every comment.
  const [threads, setThreads] = useState([])
  const reloadThreads = async () => { setThreads(await fetchThreads(caseId)) }
  const reloadReview = async () => { setReview(await request(`${casePath(caseId)}/review`)) }
  // New information: documents that replaced earlier ones, and the sections they affect.
  const [updates, setUpdates] = useState(null)
  const reloadUpdates = async () => { setUpdates(await fetchUpdates(caseId)) }
  const documentStamp = `${data.documents.length}:${data.sections.map(s => `${s.current_draft_id}:${s.readiness}`).join()}`
  useEffect(() => {
    let active = true
    fetchUpdates(caseId).then(next => { if (active) setUpdates(next) })
    return () => { active = false }
  }, [caseId, documentStamp])
  // The review picture follows the paper's stage and every saved section version.
  const stamp = `${data.case.workflow_state}:${data.case.active_es_version_id}:${data.sections.map(s => s.current_draft_id).join()}`
  useEffect(() => {
    let active = true
    request(`${casePath(caseId)}/review`).then(next => { if (active) setReview(next) }).catch(() => {})
    fetchSense(caseId).then(list => { if (active) setChecks(list) })
    fetchThreads(caseId).then(list => { if (active) setThreads(list) })
    return () => { active = false }
  }, [caseId, stamp])
  const sectionId = Number(tab)
  const shared = { ...props, review, reloadReview, updates, threads, reloadThreads }
  if (tab === 'preview') return <Preview data={data} spec={props.spec} />
  if (tab === 'review') return <ReviewTab data={data} role={role} actor={props.actor} review={review} reload={reloadReview} busy={props.busy} run={props.run} checks={checks}
    rail={<Rail data={data} tab="review" review={review} role={role} updates={updates} />} />
  if (tab === 'updates') return <UpdatesTab data={data} role={role} actor={props.actor} busy={props.busy} run={props.run} updates={updates} reload={reloadUpdates}
    rail={<Rail data={data} tab="updates" review={review} role={role} updates={updates} />} />
  if (data.sections.some(s => s.section_id === sectionId)) return <SectionTab key={sectionId} sectionId={sectionId} {...shared} />
  return <FullEs {...shared} />
}
