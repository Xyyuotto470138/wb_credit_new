import { useEffect, useState } from 'react'
import { casePath, post } from '../api/client'
import { wordingView } from './diff'
import { stage } from './status'

const STATUS = { waiting: ['Waiting for another section', 'grey'], ready: ['To update', 'amber'], proposed: ['Proposal ready', 'blue'], updated: ['Updated', 'green'], attention: ['Updated, wording to review', 'amber'] }
const when = iso => new Date(iso).toLocaleString('en-SG', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`

function Cells({ cells }) {
  return <table className="cells"><thead><tr><th>Row</th><th>Column</th><th>Before</th><th>After</th></tr></thead>
    <tbody>{cells.map((c, i) => <tr key={i} className={c.lost ? 'lost' : ''}>
      <td>{c.row}</td><td>{c.column || (c.change === 'row added' ? 'New row' : 'Row removed')}</td>
      <td>{c.before ? <del>{c.before}</del> : <span className="none">none</span>}</td>
      <td>{c.after ? <ins>{c.after}</ins> : <span className="none">none</span>}
        {c.computed && <span className="tag">calculated</span>}{c.lost && <span className="tag warn">no longer sourced</span>}</td></tr>)}</tbody></table>
}

function Wording({ change }) {
  const { before, after, type } = change
  if (type === 'narrative') {
    const was = (before.paragraphs || []).join('\n\n'), now = (after.paragraphs || []).join('\n\n')
    const { pieces, rewritten } = wordingView(was, now)
    if (rewritten) return <div className="tracked whole"><span className="lbl">Current wording</span><div className="was">{was}</div><span className="lbl">Proposed wording (largely rewritten)</span><div className="now">{now}</div></div>
    return <div className="tracked">{pieces.map((p, i) => p.type === 'same' ? <span key={i}>{p.text}</span> : p.type === 'del' ? <del key={i}>{p.text}</del> : <ins key={i}>{p.text}</ins>)}
      {!after.paragraphs?.length && <p className="warn-line">The proposal has no supported wording for this part. {after.note}</p>}</div>
  }
  if (type === 'choice') return <div className="tracked">{(after.answers || []).map((a, i) => {
    const was = before.answers?.[i]
    return <p key={i}>{a[0]}: {was && was[1] !== a[1] && <del>{was[1]}</del>} <ins>{a[1]}</ins>{a[2] && ` (${a[2]})`}</p>
  })}</div>
  return change.cells.length ? <Cells cells={change.cells} /> : <p className="warn-line">{after.note || 'The layout of this table changed.'}</p>
}

function Proposal({ entry, keep, setKeep, readOnly }) {
  const { proposal } = entry
  const figures = proposal.changes.filter(c => c.kind === 'figures'), wording = proposal.changes.filter(c => c.kind === 'wording')
  return <div className="proposal">
    <p className="by">Proposed for {proposal.proposed_by}, {when(proposal.created_at)}{proposal.cost_usd ? ` · model cost USD ${Number(proposal.cost_usd).toFixed(2)}` : ''}</p>
    {!proposal.changes.length && <p className="check yes">Nothing in this section changes on the current documents. Apply the proposal to bring the section onto them.</p>}
    {figures.length > 0 && <><h4>Figures: updated together when you apply</h4>
      {figures.map(c => <div key={c.key} className="part-change"><b>{c.title}</b> <span className="origin">{c.origin}</span>
        {c.cells.length ? <Cells cells={c.cells} /> : <p className="warn-line">{c.after.note || 'The layout of this table changed.'}</p>}</div>)}</>}
    {wording.length > 0 && <><h4>Wording: accept or keep each part</h4>
      {wording.map(c => {
        const kept = keep.includes(c.key)
        return <div key={c.key} className={`part-change${kept ? ' kept' : ''}`}><b>{c.title}</b> <span className="origin">{c.reasons.join(' ')}</span>
          {c.analyst_edit && <span className="tag warn">includes your edit</span>}
          <Wording change={c} />
          {!readOnly && <div className="choice">
            <label><input type="radio" name={`${proposal.id}-${c.key}`} checked={!kept} onChange={() => setKeep(keep.filter(k => k !== c.key))} /> Accept the proposed wording</label>
            <label><input type="radio" name={`${proposal.id}-${c.key}`} checked={kept} onChange={() => setKeep([...keep, c.key])} /> Keep the current wording</label></div>}
          {kept && c.cites_replaced && <p className="warn-line">The current wording cites a replaced document. If you keep it, this section cannot be confirmed until it is updated.</p>}
        </div>
      })}</>}
    {proposal.kept.length > 0 && <p className="quiet">{plural(proposal.kept.length, 'other wording part')} {proposal.kept.length === 1 ? 'is' : 'are'} not affected and stay{proposal.kept.length === 1 ? 's' : ''} as written.</p>}
  </div>
}

function SectionCard({ entry, view, caseId, actor, busy, run, reload, readOnly }) {
  const [keep, setKeep] = useState([])
  const [label, tone] = STATUS[entry.status]
  const token = { actor, role: 'CA', ...entry.token }
  const base = `${casePath(caseId)}/sections`
  const act = (text, operation) => run(text, async () => { await operation(); setKeep([]); await reload() })
  const propose = () => act(`Preparing a proposed update of section ${entry.section_id}`, () => post(`${base}/${entry.section_id}/update-proposal`, token))
  const apply = () => act(`Applying the update to section ${entry.section_id}`, () => post(`${base}/update-proposals/${entry.proposal.id}/apply`, { ...token, keep }))
  const dismiss = () => act('Dismissing the proposal', () => post(`${base}/update-proposals/${entry.proposal.id}/dismiss`, token))
  const applied = entry.applied
  return <div className={`card upd ${entry.status}`}>
    <div className="head"><h3><a href={`#/workbench/${entry.section_id}`}>{entry.section_id}. {entry.name}</a></h3><span className={`chip ${tone}`}>{label}</span></div>
    {entry.status !== 'updated' && entry.reasons.map(r => <p key={r} className="why">{r}</p>)}
    {entry.status === 'waiting' && <p className="why">Waits for section{entry.waiting_on.length > 1 ? 's' : ''} {entry.waiting_on.join(', ')}, which this section reads. Update {entry.waiting_on.length > 1 ? 'them' : 'it'} first.</p>}
    {applied && ['updated', 'attention'].includes(entry.status) && <p className="why">Updated by {applied.resolved_by}, {when(applied.resolved_at)}: {plural(applied.changes.filter(c => c.kind === 'figures').length, 'figure table')} updated,
      {' '}{plural(applied.decisions.accepted?.length || 0, 'wording part')} accepted, {applied.decisions.keep?.length || 0} kept. Any earlier confirmation of the section was reset.</p>}
    {entry.kept_on_replaced.length > 0 && <p className="warn-line">Kept wording still cites a replaced document: {entry.kept_on_replaced.join(', ')}. The section cannot be confirmed until this is updated.</p>}
    {entry.proposal && <Proposal entry={entry} keep={keep} setKeep={setKeep} readOnly={readOnly} />}
    {!readOnly && <div className="buttons">
      {entry.proposal && <><button className="btn primary" disabled={busy} onClick={apply}>Apply to section {entry.section_id}</button>
        <button className="btn" disabled={busy || !view.live} onClick={propose}>Propose again</button>
        <button className="btn" disabled={busy} onClick={dismiss}>Dismiss</button></>}
      {!entry.proposal && ['ready', 'attention'].includes(entry.status) && <button className="btn primary" disabled={busy || !view.live} onClick={propose}>{entry.status === 'attention' ? 'Propose again' : 'Propose update'}</button>}
    </div>}
  </div>
}

export default function UpdatesTab({ data, role, actor, busy, run, rail, updates, reload }) {
  const caseId = data.case.id
  const state = data.case.workflow_state
  const readOnly = role !== 'CA' || !['Draft', 'Returned to CA'].includes(state)
  useEffect(() => { reload() }, [caseId]) // eslint-disable-line react-hooks/exhaustive-deps
  const view = updates
  const open = view?.open || 0
  return <div className="shell no-panel">
    {rail}
    <main className="centre review updates">
      <div className="secbar"><span className={`chip ${open ? 'amber' : 'green'}`}>{open ? `${plural(open, 'section')} to update` : 'Nothing to update'}</span>
        <span className="meta">{data.case.borrower_name} · new information</span></div>
      {!view ? <p className="wb-loading">Loading…</p> : !view.available ? <div className="card"><p>Update proposals are available on papers drafted from the ES specification.</p></div> : <>
        <div className="card"><h3>New documents</h3>
          {!view.documents.length ? <p className="quiet">No document on this paper has replaced an earlier one. When a newer version of a document is added on the Files screen, it is listed here with the sections it affects.</p>
            : <table className="cells docs"><thead><tr><th>Document</th><th>Type</th><th>Dated</th><th>Replaces</th><th>Earlier version still cited in</th></tr></thead>
              <tbody>{view.documents.map(d => <tr key={d.id}><td>{d.filename}{d.synthetic && <span className="tag">synthetic</span>}</td><td>{d.type}</td><td>{d.period}</td>
                <td>{d.replaces.filename} ({d.replaces.period})</td>
                <td>{d.replaces.still_cited_in.length ? `Section${d.replaces.still_cited_in.length > 1 ? 's' : ''} ${d.replaces.still_cited_in.join(', ')}` : <span className="none">none</span>}</td></tr>)}</tbody></table>}
          <small>{view.note}</small>
        </div>
        {view.sections.length > 0 && !view.live && !readOnly && <p className="banner grey">A proposal calls the drafting model. Live model calls are off in this session, so new proposals cannot be prepared here.</p>}
        {readOnly && view.sections.length > 0 && <p className="banner grey">{role !== 'CA' ? 'Read only for reviewers.' : `Read only while the ES is ${stage(state)[0].toLowerCase()}.`}</p>}
        {view.sections.map(entry => <SectionCard key={`${entry.section_id}:${entry.proposal?.id || entry.status}`} entry={entry} view={view} caseId={caseId} actor={actor} busy={busy} run={run} reload={reload} readOnly={readOnly} />)}
      </>}
    </main>
  </div>
}
