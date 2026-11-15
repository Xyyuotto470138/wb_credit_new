import { useState } from 'react'
import { ROLES, stage } from './status'

const day = iso => new Date(iso).toLocaleString('en-SG', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`

// The facts asked for a new paper. They decide which documents and sections apply to it.
const FACTS = [['property_or_asset_security', 'Secured on property or other assets'], ['insured_security_or_assets', 'The security or assets are insured'],
  ['new_money', 'New money'], ['property_income_repayment', 'Repaid from property income'], ['covenants', 'Existing facilities with covenants'],
  ['financial_covenants', 'Existing facilities with financial covenants'], ['bureau_covered', 'Borrower or guarantor covered by a credit bureau'],
  ['has_information_memorandum', 'The deal has an information memorandum']]
const FACILITIES = [['term', 'Term loan'], ['revolving', 'Revolving credit'], ['acquisition', 'Acquisition financing']]

function NewPaper({ create, cancel, busy }) {
  const [facts, setFacts] = useState({ borrower_name: '', case_type: 'new', existing_client: false, borrower_type: 'reit', facility_types: [] })
  const set = (key, value) => setFacts(now => ({ ...now, [key]: value }))
  const renewal = facts.case_type === 'renewal'
  const submit = event => {
    event.preventDefault()
    create({ ...facts, borrower_name: facts.borrower_name.trim(), existing_client: renewal || facts.existing_client })
  }
  return <form className="card newpaper" onSubmit={submit} aria-label="New paper">
    <h2>New paper</h2>
    <p className="sub">These answers decide which documents the checklist asks for and which sections apply. The paper uses the FIG Executive Summary template.</p>
    <div className="fields">
      <label>Borrower name<input autoFocus required maxLength="200" value={facts.borrower_name} onChange={e => set('borrower_name', e.target.value)} /></label>
      <label>Paper type<select value={facts.case_type} onChange={e => set('case_type', e.target.value)}><option value="new">New</option><option value="renewal">Renewal</option></select></label>
      <label>Borrower type<select value={facts.borrower_type} onChange={e => set('borrower_type', e.target.value)}>
        <option value="reit">REIT</option><option value="fund">Fund</option><option value="bank">Bank</option><option value="other">Other</option></select></label>
    </div>
    <fieldset><legend>Facilities</legend>
      {FACILITIES.map(([key, label]) => <label className="tick" key={key}><input type="checkbox" checked={facts.facility_types.includes(key)}
        onChange={e => set('facility_types', e.target.checked ? [...facts.facility_types, key] : facts.facility_types.filter(f => f !== key))} />{label}</label>)}</fieldset>
    <fieldset><legend>About the case</legend>
      <label className="tick"><input type="checkbox" checked={renewal || facts.existing_client} disabled={renewal} onChange={e => set('existing_client', e.target.checked)} />
        Existing client{renewal ? ' (a renewal always is)' : ''}</label>
      {FACTS.map(([key, label]) => <label className="tick" key={key}><input type="checkbox" checked={!!facts[key]} onChange={e => set(key, e.target.checked)} />{label}</label>)}</fieldset>
    <div className="actions"><button className="btn primary" type="submit" disabled={busy || !facts.borrower_name.trim()}>Create paper</button>
      <button className="btn" type="button" disabled={busy} onClick={cancel}>Cancel</button></div>
  </form>
}

// Every paper the user works on, with where each stands. Opening one switches the whole workbench to it.
export default function PapersScreen({ papers, current, role, choose, create, busy }) {
  const maker = role === 'CA'
  // The maker opens on every paper; a reviewer opens on what is waiting for them.
  const [filter, setFilter] = useState(maker ? 'all' : 'mine')
  const [adding, setAdding] = useState(false)
  const me = ROLES[role].label
  const mine = papers.filter(p => p.waiting_for === me)
  const shown = filter === 'mine' ? mine : filter === 'others' ? papers.filter(p => p.waiting_for !== me) : papers
  return <main className="papers">
    <div className="head"><h1>Papers</h1>
      <div className="filters" role="tablist">
        {[['all', `All (${papers.length})`], ['mine', `${maker ? 'Waiting for me' : 'Waiting for my review'} (${mine.length})`], ['others', `With others (${papers.length - mine.length})`]].map(([key, label]) =>
          <button key={key} role="tab" aria-selected={filter === key} className={filter === key ? 'on' : ''} onClick={() => setFilter(key)}>{label}</button>)}
      </div>
      <span className="spacer" /><small>Viewing as {me}</small>
      {maker && create && !adding && <button className="btn primary" disabled={busy} onClick={() => setAdding(true)}>+ New paper</button>}</div>
    {adding && <NewPaper create={create} cancel={() => setAdding(false)} busy={busy} />}
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
      {!shown.length && <p className="empty">{filter !== 'mine' ? 'No papers in this view.' : maker ? 'No paper is waiting for you.' : 'No paper is waiting for your review. Papers appear here once a credit analyst submits them.'}</p>}
    </div>
    <p className="hint">Each paper keeps its own files, drafts, versions and review trail. Switching papers changes nothing in either.</p>
  </main>
}
