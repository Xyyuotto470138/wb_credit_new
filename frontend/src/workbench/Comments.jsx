import { useState } from 'react'
import { casePath, post } from '../api/client'

const WHO = { CA: 'Credit analyst', 'Credit Head': 'Credit Head', 'Credit Approver': 'Credit Approver' }
const when = iso => new Date(iso).toLocaleString('en-SG', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })

// One discussion: its comments, a reply box, and resolving it with a conclusion.
function Thread({ thread, caseId, actor, role, busy, run, reload }) {
  const [reply, setReply] = useState('')
  const [concluding, setConcluding] = useState(false)
  const [conclusion, setConclusion] = useState('')
  const send = (path, body, label) => run(label, async () => { await post(`${casePath(caseId)}/threads/${encodeURIComponent(thread.id)}/${path}`, { actor, role, ...body }); await reload() })
  const open = thread.status === 'open'
  return <div className={`thread ${thread.status}`}>
    <div className="about"><span className={`chip ${open ? 'amber' : 'green'}`}>{open ? 'Open' : 'Resolved'}</span>
      <b>{thread.part_title ? `About: ${thread.part_title}` : 'About the whole section'}</b></div>
    {thread.quote && <blockquote>{thread.quote}</blockquote>}
    {thread.comments.map((comment, i) => <div key={i} className={`said${comment.reopened ? ' note' : ''}`}>
      <b>{comment.author}</b> <span>{WHO[comment.role] || comment.role} · {when(comment.at)}</span><p>{comment.text}</p></div>)}
    {!open && <div className="said conclusion"><b>Conclusion</b> <span>{thread.resolved_by}, {WHO[thread.resolved_role] || thread.resolved_role} · {when(thread.resolved_at)}</span><p>{thread.conclusion}</p></div>}
    {open && !concluding && <div className="row">
      <textarea aria-label="Reply" rows={2} maxLength={4000} placeholder="Reply" value={reply} disabled={busy} onChange={e => setReply(e.target.value)} />
      <button className="btn small primary" disabled={busy || !reply.trim()} onClick={() => send('replies', { text: reply.trim() }, 'Adding your reply').then(() => setReply(''))}>Reply</button>
      <button className="btn small" disabled={busy} onClick={() => setConcluding(true)}>Resolve</button></div>}
    {open && concluding && <div className="row">
      <textarea aria-label="Conclusion" rows={2} maxLength={4000} autoFocus placeholder="What was agreed? This is kept with the thread." value={conclusion} disabled={busy} onChange={e => setConclusion(e.target.value)} />
      <button className="btn small primary" disabled={busy || !conclusion.trim()} onClick={() => send('resolve', { conclusion: conclusion.trim() }, 'Resolving the thread').then(() => { setConcluding(false); setConclusion('') })}>Resolve with this conclusion</button>
      <button className="btn small" disabled={busy} onClick={() => setConcluding(false)}>Cancel</button></div>}
    {!open && <div className="row"><span className="spacer" /><button className="btn small" disabled={busy} onClick={() => send('reopen', {}, 'Reopening the thread')}>Reopen</button></div>}
  </div>
}

// Comments on one section. Every signed-in role can open a thread, reply, and resolve it with a conclusion.
// Comments never change the section: a change agreed here is still made by the credit analyst in the section.
export default function Comments({ caseId, sectionId, parts = [], threads, actor, role, busy, run, reload }) {
  const [adding, setAdding] = useState(false)
  const [part, setPart] = useState('')
  const [quote, setQuote] = useState('')
  const [text, setText] = useState('')
  const [showResolved, setShowResolved] = useState(false)
  const mine = (threads || []).filter(t => t.section_id === sectionId)
  const open = mine.filter(t => t.status === 'open')
  const resolved = mine.filter(t => t.status === 'resolved')
  const titled = parts.filter(p => p.title && !p.hidden)
  const start = event => {
    event.preventDefault()
    run('Adding your comment', async () => {
      await post(`${casePath(caseId)}/threads`, { actor, role, section_id: sectionId, text: text.trim(), ...(part ? { part_key: part } : {}), ...(quote.trim() ? { quote: quote.trim() } : {}) })
      await reload()
    }).then(() => { setAdding(false); setPart(''); setQuote(''); setText('') })
  }
  return <section className="card comments" aria-label="Comments">
    <h3>Comments <span className="count">{open.length} open{resolved.length ? ` · ${resolved.length} resolved` : ''}</span>
      {!adding && <button className="btn small" disabled={busy} onClick={() => setAdding(true)}>+ Add comment</button>}</h3>
    {adding && <form className="new" onSubmit={start}>
      {titled.length > 0 && <label>About<select value={part} disabled={busy} onChange={e => setPart(e.target.value)}>
        <option value="">The whole section</option>{titled.map(p => <option key={p.key} value={p.key}>{p.title}</option>)}</select></label>}
      <label>Words or figure you are referring to (optional)<input value={quote} maxLength={2000} disabled={busy} placeholder="Paste the sentence or the cell" onChange={e => setQuote(e.target.value)} /></label>
      <label>Comment<textarea rows={3} required maxLength={4000} autoFocus value={text} disabled={busy} onChange={e => setText(e.target.value)} /></label>
      <div className="row"><button className="btn small primary" type="submit" disabled={busy || !text.trim()}>Add comment</button>
        <button className="btn small" type="button" disabled={busy} onClick={() => setAdding(false)}>Cancel</button></div>
    </form>}
    {!mine.length && !adding && <p className="empty">No comments on this section.</p>}
    {open.map(thread => <Thread key={thread.id} thread={thread} caseId={caseId} actor={actor} role={role} busy={busy} run={run} reload={reload} />)}
    {resolved.length > 0 && <button className="link more" onClick={() => setShowResolved(v => !v)}>{showResolved ? 'Hide' : 'Show'} {resolved.length} resolved</button>}
    {showResolved && resolved.map(thread => <Thread key={thread.id} thread={thread} caseId={caseId} actor={actor} role={role} busy={busy} run={run} reload={reload} />)}
    <small className="foot">Comments are a discussion. They do not change the section; the credit analyst makes any agreed change in the section itself.</small>
  </section>
}
