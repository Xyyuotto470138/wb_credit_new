import { useRef, useState } from 'react'
import { casePath, post, request } from '../api/client'
import { trackedChanges } from './diff'

// Offline round trip: the analyst uploads an ES that was exported to Word and edited there. The comparison is shown
// change by change; only wording the analyst ticks is taken, and it is saved as a new version of its section.
export default function Roundtrip({ caseId, actor, busy, run, onDone }) {
  const input = useRef(null)
  const [result, setResult] = useState(null)
  const [take, setTake] = useState({})
  const [notes, setNotes] = useState({})
  const [done, setDone] = useState(null)
  const pick = event => {
    const file = event.target.files[0]
    event.target.value = ''
    if (!file) return
    setDone(null)
    run('Comparing the Word file with the ES', async () => {
      const found = await request(`${casePath(caseId)}/roundtrip/compare`, { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: file })
      setResult({ ...found, filename: file.name })
      setTake(Object.fromEntries(found.sections.flatMap(sec => sec.changes.filter(c => c.kind === 'wording').map(c => [c.claim_id, true]))))
      setNotes(Object.fromEntries(found.comments.map((c, i) => [i, c.section_id != null])))
    })
  }
  const wording = result ? result.sections.flatMap(sec => sec.changes.filter(c => c.kind === 'wording')) : []
  const chosen = wording.filter(c => take[c.claim_id]).length
  const chosenNotes = result ? result.comments.filter((c, i) => notes[i] && c.section_id != null) : []
  const apply = () => run('Saving the wording you chose', async () => {
    const sections = Object.fromEntries(result.sections.map(sec => [sec.section_id, {
      draft_id: sec.draft_id, replacements: Object.fromEntries(sec.changes.filter(c => c.kind === 'wording' && take[c.claim_id]).map(c => [c.claim_id, c.after])) }])
      .filter(([, value]) => Object.keys(value.replacements).length))
    const saved = await post(`${casePath(caseId)}/roundtrip/apply`, { actor, sections, comments: chosenNotes })
    setDone(saved); setResult(null)
    if (onDone) await onDone()
  })
  return <>
    <input ref={input} type="file" accept=".docx" hidden onChange={pick} />
    <button className="btn" disabled={busy} title="Upload an ES that was exported from here and edited in Word" onClick={() => input.current.click()}>Upload edited Word ES</button>
    {done && <p className="banner green roundtrip-note">Saved from the Word file: {done.saved_sections.length ? `new versions of section${done.saved_sections.length > 1 ? 's' : ''} ${done.saved_sections.join(', ')}` : 'no wording'}
      {done.threads_opened ? ` and ${done.threads_opened} comment${done.threads_opened > 1 ? 's' : ''} as review threads` : ''}. Changed sections need to be confirmed again.</p>}
    {result && <section className="card roundtrip" aria-label="Changes in the Word file">
      <h3>Changes in {result.filename} <button className="btn small" disabled={busy} onClick={() => setResult(null)}>Close</button></h3>
      <p className="sub">{result.note}</p>
      {result.stale_sections.length > 0 && <p className="banner amber">Section{result.stale_sections.length > 1 ? 's' : ''} {result.stale_sections.join(', ')} changed here after this file was exported, so {result.stale_sections.length > 1 ? 'they were' : 'it was'} not compared. Export again to edit {result.stale_sections.length > 1 ? 'them' : 'it'} in Word.</p>}
      {!result.sections.some(sec => sec.changes.length) && <p className="empty">No wording differences were found in the paragraphs that could be matched.</p>}
      {result.sections.filter(sec => sec.changes.length).map(sec => <div key={sec.section_id} className="rt-section">
        <h4>{sec.section_id}. {sec.name}</h4>
        {sec.changes.map(change => <label key={change.claim_id} className={`rt-change ${change.kind}`}>
          <input type="checkbox" checked={!!take[change.claim_id]} disabled={busy || change.kind !== 'wording'} onChange={e => setTake({ ...take, [change.claim_id]: e.target.checked })} />
          <span><b>{change.part}</b>
            {trackedChanges(change.before, change.after).map((pieces, k) => <span className="diff" key={k}>
              {pieces.map((piece, i) => piece.type === 'add' ? <ins key={i}>{piece.text}</ins> : piece.type === 'del' ? <del key={i}>{piece.text}</del> : <span key={i}>{piece.text}</span>)}</span>)}
            {change.reason && <small>{change.reason}</small>}</span>
        </label>)}
      </div>)}
      {result.comments.length > 0 && <div className="rt-section"><h4>Comments left in Word</h4>
        {result.comments.map((comment, i) => <label key={i} className={`rt-change${comment.section_id == null ? ' figures' : ''}`}>
          <input type="checkbox" checked={!!notes[i]} disabled={busy || comment.section_id == null} onChange={e => setNotes({ ...notes, [i]: e.target.checked })} />
          <span><b>{comment.author}{comment.section_id != null ? ` · section ${comment.section_id}` : ''}</b><span className="diff">{comment.text}</span>
            {comment.section_id == null && <small>The app could not tell which section this comment is on.</small>}</span></label>)}
      </div>}
      <div className="rt-actions"><button className="btn primary" disabled={busy || (!chosen && !chosenNotes.length)} onClick={apply}>
        Take {chosen} wording change{chosen === 1 ? '' : 's'}{chosenNotes.length ? ` and ${chosenNotes.length} comment${chosenNotes.length === 1 ? '' : 's'}` : ''}</button>
        <small>Each section you change gets a new version, marked as edited by you, and must be confirmed again.</small></div>
    </section>}
  </>
}
