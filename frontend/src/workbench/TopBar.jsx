import logo from '../../../templates/UOB_logo.png'
import { ROLES, esStatus, sectionStatus } from './status'

export default function TopBar({ data, spec, view, assistantOpen, toggleAssistant, papers = [], choose, role, changeRole }) {
  const status = data && esStatus(data)
  const confirmed = data ? data.sections.filter(s => ['Confirmed', 'Not applicable'].includes(sectionStatus(s))).length : 0
  return <header className="topbar">
    <img className="logo" src={logo} alt="UOB" />
    <span className="product">WB Credit</span>
    <a className={`nav${view === 'papers' ? ' on' : ''}`} href="#/papers">Papers{papers.length > 1 ? ` (${papers.length})` : ''}</a>
    {data && view !== 'papers' && (papers.length > 1
      ? <label className="pick"><select aria-label="Switch paper" value={data.case.id} onChange={e => choose(e.target.value)}>
        {papers.map(p => <option key={p.id} value={p.id}>{p.borrower_name} · {p.case_type === 'renewal' ? 'Renewal' : 'New'}</option>)}</select></label>
      : <span className="case">{data.case.borrower_name} · {data.case.case_type === 'renewal' ? 'Renewal' : 'New'} · {spec?.team_label || data.case.team_id.toUpperCase()}</span>)}
    {status && view !== 'papers' && <span className="status"><b><span className="wide">ES STATUS: </span>{status.state.toUpperCase()}</b><span className="wide"> · open {status.days} day{status.days === 1 ? '' : 's'}</span> · {status.pending} input{status.pending === 1 ? '' : 's'} pending</span>}
    <span className="spacer" />
    {role && !changeRole && <span className="role">{ROLES[role].label} ({ROLES[role].short.toLowerCase()})</span>}
    {role && changeRole && <label className="role"><span className="wide">Viewing as </span><select aria-label="Role" value={role} onChange={e => changeRole(e.target.value)}>
      {Object.entries(ROLES).map(([key, r]) => <option key={key} value={key}>{r.label} ({r.short.toLowerCase()})</option>)}</select></label>}
    {view === 'papers' ? data && <a className="btn primary" href="#/workbench/full">Back to {data.case.borrower_name}</a> : view === 'inputs' ? <a className="btn primary" href="#/workbench">Open ES workbench →</a> : <>
      <a className="btn" href="#/inputs">← Inputs</a>
      <a className="btn" href="#/workbench/review">{role !== 'CA' ? 'Review' : data?.case.workflow_state === 'Draft' ? `Submit · ${confirmed} of ${data.sections.length} confirmed` : data?.case.workflow_state === 'Returned to CA' ? 'Resubmit' : 'Review status'}</a>
      <button className="toggle" aria-pressed={assistantOpen} onClick={toggleAssistant}>Credit Assistant <i className={assistantOpen ? 'on' : ''} /></button>
    </>}
  </header>
}
