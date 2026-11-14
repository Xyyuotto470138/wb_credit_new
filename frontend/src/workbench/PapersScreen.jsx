import { useState } from 'react'
import { ROLES, stage } from './status'

const day = iso => new Date(iso).toLocaleString('en-SG', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`

// Every paper the user works on, with where each stands. Opening one switches the whole workbench to it.
export default function PapersScreen({ papers, current, role, choose }) {
  const [filter, setFilter] = useState('all')
  const me = ROLES[role].label
  const mine = papers.filter(p => p.waiting_for === me)
  const shown = filter === 'mine' ? mine : filter === 'others' ? papers.filter(p => p.waiting_for !== me) : papers
  return <main className="papers">
    <div className="head"><h1>Papers</h1>
      <div className="filters" role="tablist">
        {[['all', `All (${papers.length})`], ['mine', `Waiting for me (${mine.length})`], ['others', `With others (${papers.length - mine.length})`]].map(([key, label]) =>
          <button key={key} role="tab" aria-selected={filter === key} className={filter === key ? 'on' : ''} onClick={() => setFilter(key)}>{label}</button>)}
      </div>
      <span className="spacer" /><small>Viewing as {me}</small></div>
    <div className="card table">
      <div className="row th"><span>Borrower</span><span>Stage</span><span>Waiting for</span><span>Progress</span><span>Needs attention</span><span>Last activity</span><span /></div>
      {shown.map(paper => {
        const [label, tone] = stage(paper.workflow_state)
        const attention = [paper.returned_sections.length && [plural(paper.returned_sections.length, 'section') + ' open for changes', 'amber'], paper.update_required && [plural(paper.update_required, 'section') + ' to update', 'amber'],
          paper.inputs_outstanding && [plural(paper.inputs_outstanding, 'input') + ' outstanding', 'grey'], paper.suggested_checks && [plural(paper.suggested_checks, 'suggested check'), 'amber']].filter(Boolean)
        return <div key={paper.id} className={`row${paper.id === current ? ' current' : ''}`}>
          <span><b>{paper.borrower_name}</b><small>{paper.case_type === 'renewal' ? 'Renewal' : 'New'} · {paper.team_id.split('_')[0].toUpperCase()}{paper.synthetic_demo ? ' · SYNTHETIC DEMO DATA' : ''}</small></span>
          <span><i className={`chip ${tone}`}>{label}</i></span>
          <span className={paper.waiting_for === me ? 'me' : ''}>{paper.waiting_for ? (paper.waiting_for === me ? 'You' : paper.waiting_for) : 'Closed'}</span>
          <span><div className="bar"><i style={{ width: `${100 * paper.drafted / paper.sections}%` }} /><i className="ok" style={{ width: `${100 * paper.confirmed / paper.sections}%` }} /></div>
            <small>{paper.drafted} of {paper.sections} drafted · {paper.confirmed} confirmed</small></span>
          <span className="chips">{attention.length ? attention.map(([text, kind]) => <i key={text} className={`chip ${kind}`}>{text}</i>) : <small>Nothing outstanding</small>}</span>
          <span><small>{day(paper.last_activity)}{paper.last_event ? ` · ${paper.last_event.action} by ${paper.last_event.actor}` : ''}</small></span>
          <span><button className={`btn small${paper.id === current ? '' : ' primary'}`} onClick={() => choose(paper.id)}>{paper.id === current ? 'Current' : 'Open'}</button></span>
        </div>
      })}
      {!shown.length && <p className="empty">No papers in this view.</p>}
    </div>
    <p className="hint">Each paper keeps its own files, drafts, versions and review trail. Switching papers changes nothing in either.</p>
  </main>
}
