import { useEffect, useState } from 'react'
import { casePath, post, request } from '../api/client'
import { ROLES, stage } from './status'

const when = iso => new Date(iso).toLocaleString('en-SG', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
const ACTION = { submit: 'submitted the ES for review', return: 'returned the ES to the credit analyst', support: 'supported the ES', handoff: 'handed the ES to the Credit Approver',
  approve: 'approved', approve_with_conditions: 'approved with conditions', decline: 'declined', question: 'asked a question', answer_resubmit: 'answered and resubmitted' }
const ROLE_LABEL = { CA: 'Credit analyst', 'Credit Head': 'Credit Head', 'Credit Approver': 'Credit Approver' }
const command = (review, actor, role, action, extra = {}) => ({ actor, role, action, expected_state: review.state, expected_event_id: review.latest_event_id, expected_es_version_id: review.active_es_version_id, ...extra })

// The checker's control on one section: mark it reviewed, or raise a query for the maker. The maker sees the query here.
export function ReviewBar({ entry, review, role, actor, caseId, busy, run, reload }) {
  const [note, setNote] = useState('')
  const [asking, setAsking] = useState(false)
  if (!entry || !review) return null
  const mark = entry.mark
  const send = (status, text = '') => run(status === 'query' ? 'Recording your query' : 'Recording your review', async () => {
    await post(`${casePath(caseId)}/review/marks`, { actor, role, section_id: entry.section_id, status, note: text, expected_es_version_id: review.active_es_version_id })
    setAsking(false); setNote(''); await reload()
  })
  if (role === 'CA') {
    if (review.state !== 'Returned to CA') return null
    if (mark?.status === 'query') return <p className="banner amber review-note"><b>Query from {mark.reviewer} ({ROLE_LABEL[mark.role]}):</b> {mark.note}{entry.changed_since_submission && <span> You have changed this section since it was returned.</span>}</p>
    if (entry.returned) return <p className="banner amber review-note"><b>Returned for changes.</b> See the reviewer's comment on the Review page.</p>
    if (entry.editable) return <p className="banner grey review-note">Open for changes because it draws on a returned section. Confirm it again before you resubmit.</p>
    return <p className="banner grey review-note">Not returned. This section stays as submitted.</p>
  }
  if (review.state !== 'Submitted to Credit Head') return null
  if (!entry.submitted_draft_id) return null
  return <div className="review-bar">
    {entry.mark_current && mark.status === 'reviewed' && <span className="chip green">Reviewed by {mark.reviewer}</span>}
    {entry.mark_current && mark.status === 'query' && <span className="chip amber">Query raised</span>}
    {!entry.mark_current && <span className="chip grey">{entry.changed_since_mark ? 'Changed since your last review' : 'Not yet reviewed'}</span>}
    {mark?.status === 'query' && <span className="q">{entry.mark_current ? '' : 'Earlier query: '}{mark.note}</span>}
    <span className="spacer" />
    {!asking && <>
      {entry.mark_current && <button className="btn small" disabled={busy} onClick={() => send('cleared')}>Clear</button>}
      <button className="btn small" disabled={busy} onClick={() => setAsking(true)}>Query this section</button>
      <button className="btn small primary" disabled={busy || (entry.mark_current && mark.status === 'reviewed')} onClick={() => send('reviewed')}>Mark as reviewed</button></>}
    {asking && <div className="ask"><textarea aria-label="Query for the credit analyst" rows={2} maxLength={4000} autoFocus placeholder="What should the credit analyst change or explain?" value={note} onChange={e => setNote(e.target.value)} />
      <button className="btn small" disabled={busy} onClick={() => setAsking(false)}>Cancel</button>
      <button className="btn small primary" disabled={busy || !note.trim()} onClick={() => send('query', note.trim())}>Save query</button></div>}
  </div>
}

function Trail({ review }) {
  const sections = ids => ids.length ? ` Section${ids.length > 1 ? 's' : ''} ${ids.join(', ')}.` : ''
  return <div className="card trail"><h3>Review trail</h3>
    {!review.events.length && <p className="empty">Nothing yet. The trail starts when the credit analyst submits the ES.</p>}
    {review.events.map(event => <div key={event.id} className="event"><b>{event.actor}</b> ({ROLE_LABEL[event.role] || event.role}) {ACTION[event.action] || event.action}.{sections(event.returned_sections)}
      <small>{when(event.created_at)}</small>{event.payload?.comment && <p>{event.payload.comment}</p>}</div>)}
    <small>Every submission keeps the exact section versions that were reviewed.</small></div>
}

function Maker({ data, review, actor, busy, run, reload, checks }) {
  const [report, setReport] = useState(null)
  const [reasons, setReasons] = useState({})
  const [comment, setComment] = useState('')
  const caseId = data.case.id
  const working = ['Draft', 'Returned to CA'].includes(review.state)
  const stamp = data.sections.map(s => `${s.current_draft_id}:${s.readiness}`).join()
  useEffect(() => {
    let active = true
    if (working) request(`${casePath(caseId)}/submission-checks/preview`).then(next => { if (active) setReport(next) }).catch(() => {})
    return () => { active = false }
  }, [caseId, working, stamp, review.latest_event_id])
  if (!working) return <div className="card act"><h3>{stage(review.state)[0]}</h3><p>The ES is read only while it is with the reviewer. You will see it here if it is returned.</p></div>
  if (!report) return <div className="card act"><p className="wb-loading">Checking the ES…</p></div>
  const open = report.sections.filter(s => s.status !== 'passed')
  const gaps = report.mandatory_gaps
  const suggested = checks.filter(c => c.current).reduce((n, c) => n + c.open, 0)
  const reason = id => reasons[id] ?? review.gap_reasons?.[id] ?? ''
  const ready = !open.length && !report.blockers.length && gaps.every(g => reason(g.id).trim())
  const returned = review.state === 'Returned to CA' && review.events.at(-1)
  const submit = () => run('Submitting the ES for review', async () => {
    const fresh = await request(`${casePath(caseId)}/submission-checks/preview`)
    await post(`${casePath(caseId)}/workflow/transitions`, command(review, actor, 'CA', 'submit', { expected_preview_token: fresh.preview_token,
      mandatory_gap_reasons: Object.fromEntries(gaps.map(g => [g.id, reason(g.id).trim()])), ...(comment.trim() ? { comment: comment.trim() } : {}) }))
    setComment(''); await reload()
  })
  return <div className="card act"><h3>{returned ? 'Returned by the reviewer' : 'Submit for review'}</h3>
    {returned && <div className="banner amber"><b>{returned.actor} returned section{returned.returned_sections.length > 1 ? 's' : ''} {returned.returned_sections.join(', ')}.</b> {returned.payload?.comment}
      <div className="links">{review.sections.filter(s => s.editable).map(s => <a key={s.section_id} href={`#/workbench/${s.section_id}`}>{s.section_id}. {s.name}{s.returned ? '' : ' (depends on a returned section)'}</a>)}</div></div>}
    <p className="prev"><a className="btn small" href="#/workbench/preview">Preview the full ES</a> Read the whole paper as it stands before you submit.</p>
    <h4>Before you submit</h4>
    <div className={`check ${open.length ? 'no' : 'yes'}`}><b>{report.sections.length - open.length} of {report.sections.length} sections confirmed or not applicable.</b>
      {open.map(s => <a key={s.section_id} href={`#/workbench/${s.section_id}`}>{s.section_id}. {s.name}: {s.issues[0] || 'needs confirmation'}</a>)}</div>
    {gaps.map(gap => <div key={gap.id} className={`check ${reason(gap.id).trim() ? 'yes' : 'no'}`}><b>Required input not complete: {gap.name}.</b>
      <label>Reason for submitting without it<input value={reason(gap.id)} maxLength={500} onChange={e => setReasons({ ...reasons, [gap.id]: e.target.value })} placeholder="Recorded with the submission" /></label></div>)}
    {report.blockers.map(text => <div key={text} className="check no"><b>{text}</b></div>)}
    {suggested > 0 && <div className="check info"><b>{suggested} model suggestion{suggested === 1 ? '' : 's'} not yet looked at.</b> This does not stop the submission. The reviewer sees them as open items.</div>}
    <div className="check info"><b>Credit master system: {report.future_credit_master.label}.</b> Limits and outstanding amounts are not compared with a master system in this prototype.</div>
    <label className="reply">{returned ? 'Reply to the reviewer (optional)' : 'Note to the reviewer (optional)'}<textarea rows={2} maxLength={4000} value={comment} onChange={e => setComment(e.target.value)} /></label>
    <button className="btn primary" disabled={busy || !ready} onClick={submit}>{returned ? 'Resubmit to the Credit Head' : 'Submit to the Credit Head'}</button>
    <small>Submitting records the exact version of every section and locks the ES until the reviewer acts. It is a request for review, not a credit decision.</small>
  </div>
}

function Checker({ data, review, actor, busy, run, reload }) {
  const [comment, setComment] = useState('')
  const caseId = data.case.id
  const move = (label, action, extra) => run(label, async () => { await post(`${casePath(caseId)}/workflow/transitions`, command(review, actor, 'Credit Head', action, extra)); setComment(''); await reload() })
  if (review.state === 'Supported') return <div className="card act"><h3>Supported</h3><p>You have supported this ES. The next step is the Credit Approver, which this build does not show as a role.</p>
    <button className="btn" disabled={busy} onClick={() => move('Handing the ES to the Credit Approver', 'handoff')}>Hand off to the Credit Approver</button></div>
  if (review.state !== 'Submitted to Credit Head') return <div className="card act"><h3>Nothing waiting for you</h3>
    <p>This paper is {review.state === 'Draft' ? 'still being drafted by the credit analyst' : `at stage: ${stage(review.state)[0]}`}. You can read it; you cannot change it.</p></div>
  const list = review.sections.filter(s => s.applicable && s.submitted_draft_id)
  const queries = list.filter(s => s.mark_current && s.mark.status === 'query')
  const { reviewed, to_review: total } = review.summary
  return <div className="card act"><h3>Review the submitted ES</h3>
    <p><b>{reviewed} of {total} sections reviewed</b>{queries.length ? `, ${queries.length} with a query` : ''}. Open each section, read it against its sources, then mark it reviewed or raise a query.</p>
    <div className="marks">{list.map(s => <a key={s.section_id} href={`#/workbench/${s.section_id}`} className={s.mark_current ? s.mark.status : 'todo'}>
      <span className="n">{s.section_id}</span><span>{s.name}</span>
      <i>{s.mark_current ? (s.mark.status === 'reviewed' ? 'Reviewed' : `Query: ${s.mark.note}`) : s.changed_since_mark ? 'Changed since your last review' : 'To review'}</i></a>)}</div>
    <label className="reply">Comment to the credit analyst{queries.length ? ' (sent with the return)' : ''}<textarea rows={2} maxLength={4000} value={comment} onChange={e => setComment(e.target.value)} /></label>
    <div className="buttons">
      <button className="btn" disabled={busy || !queries.length || !comment.trim()} title={queries.length ? '' : 'Raise a query on a section first'}
        onClick={() => move('Returning the ES to the credit analyst', 'return', { section_ids: queries.map(s => s.section_id), comment: comment.trim() })}>Return {queries.length || ''} section{queries.length === 1 ? '' : 's'} to the analyst</button>
      <button className="btn primary" disabled={busy || reviewed < total || queries.length > 0} title={reviewed < total ? 'Mark every section as reviewed first' : ''}
        onClick={() => move('Recording your support', 'support', comment.trim() ? { comment: comment.trim() } : {})}>Support the ES</button>
    </div>
    <small>{review.note} Support passes the ES on for approval; the credit decision is made by the approving officers.</small>
  </div>
}

export default function ReviewTab({ data, role, actor, review, reload, busy, run, checks, rail }) {
  return <div className="shell no-panel">
    {rail}
    <main className="centre review">
      <div className="secbar"><span className={`chip ${review ? stage(review.state)[1] : 'grey'}`}>{review ? stage(review.state)[0] : 'Loading'}</span>
        <span className="meta">{data.case.borrower_name} · viewing as {ROLES[role].label}</span></div>
      {!review ? <p className="wb-loading">Loading the review…</p> : <>
        {role === 'CA' ? <Maker data={data} review={review} actor={actor} busy={busy} run={run} reload={reload} checks={checks} />
          : <Checker data={data} review={review} actor={actor} busy={busy} run={run} reload={reload} />}
        <Trail review={review} /></>}
    </main>
  </div>
}
