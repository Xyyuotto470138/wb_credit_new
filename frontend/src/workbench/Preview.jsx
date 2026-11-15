import { useEffect, useState } from 'react'
import { casePath, request } from '../api/client'
import SectionView from './SectionView'
import { PAPER_TYPE, sectionStatus, stage } from './status'

// The whole ES on one clean page, read only: what the maker checks before exporting or submitting.
// It shows the sections exactly as they are saved now. Nothing can be changed here.
export default function Preview({ data, spec }) {
  const [histories, setHistories] = useState(null)
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
  const open = data.sections.filter(s => !['Confirmed', 'Not applicable'].includes(sectionStatus(s)))
  return <main className="preview">
    <div className="preview-bar">
      <a className="btn" href="#/workbench/full">← Back to the ES</a>
      <span className="meta">Preview · read only · {open.length ? `${open.length} section${open.length === 1 ? '' : 's'} not yet confirmed` : 'every section confirmed or not applicable'}</span>
      <span className="spacer" />
      <a className="btn" href="#/workbench/review">Go to submit</a>
      <button className="btn primary" onClick={() => window.print()}>Print or save as PDF</button>
    </div>
    <article className="paper">
      <header>
        <p className="mark">Draft for review · not a submission</p>
        <h1>Executive Summary</h1>
        <p className="who">{data.case.borrower_name} · {PAPER_TYPE[data.case.case_type]} · {spec?.team_label || data.case.team_id.split('_')[0].toUpperCase()} · {stage(data.case.workflow_state)[0]}</p>
        <p className="when">Previewed {new Date().toLocaleString('en-SG', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}{data.synthetic_demo ? ' · SYNTHETIC DEMO DATA' : ''}</p>
      </header>
      {!histories ? <p className="wb-loading">Loading the ES…</p> : data.sections.map((section, i) => {
        const draft = histories[i]?.versions.find(d => d.id === histories[i].section.current_draft_id)
        const status = sectionStatus(section)
        return <div key={section.section_id} className="preview-section">
          {!['Confirmed', 'Not applicable'].includes(status) && <p className="state">{status === 'In progress' ? 'Drafted, not yet confirmed' : status}</p>}
          <SectionView section={section} draft={draft} layout={spec?.sections.find(s => s.id === section.section_id)} caseId={caseId}
            gaps={draft ? (draft.claim_spans[0]?.parts ? draft.gaps : [...new Set([...(section.gaps || []), ...(draft.gaps || [])])]) : section.gaps.slice(0, 3)} onCite={() => {}} />
        </div>
      })}
    </article>
  </main>
}
