import { useState } from 'react'
import FileUpload from '../components/FileUpload'
import { casePath, contentUrl, demoMetadata, post, requestListUrl, upload } from '../api/client'
import { canStart, DOC_STATUS, DOC_TONE, DRAFT_ORDER, sectionStatus, shortGap } from './status'

const OWNER = { RM: 'Ask the RM', client: 'Ask the client', 'internal team': 'Ask internal teams' }
const Chip = ({ tone, children }) => <span className={`chip ${tone}`}>{children}</span>

function Item({ item, data, children }) {
  const status = DOC_STATUS[item.status] || item.status
  const docs = item.document_ids.map(id => data.documents.find(d => d.id === id)).filter(Boolean)
  return <div className="item">
    <span className="name">{item.name}</span><Chip tone={DOC_TONE[status]}>{status}</Chip>
    <span className="meta">
      {docs.map(doc => <span key={doc.id}><a href={contentUrl(data.case.id, doc.id)} target="_blank" rel="noreferrer">{doc.original_filename}</a>
        {doc.origin === 'public' ? ` · public, retrieved ${doc.retrieved_at?.slice(0, 10)} · ${doc.confirmed_by ? 'reviewed' : 'review pending'}`
          : doc.entity === data.case.borrower_name ? ' · borrower matches' : ''}{' '}</span>)}
      {!docs.length && (item.status === 'Missing' ? `Needed for section${item.section_ids.length > 1 ? 's' : ''} ${item.section_ids.join(', ')}.` : item.details[0] || '')}
      {children}
    </span>
  </div>
}

export default function InputsScreen({ data, spec, actor, busy, run }) {
  const [folderId, setFolderId] = useState(data.intake.folders[0]?.id || '')
  const [results, setResults] = useState(null)
  const [unsecured, setUnsecured] = useState(false)
  const [progress, setProgress] = useState('')
  const caseId = data.case.id
  const borrower = data.case.borrower_name
  const folder = data.intake.folders.find(f => f.id === folderId)
  const applicable = data.expected_documents.filter(e => e.applicable)
  const held = applicable.filter(e => ['Provided', 'Found publicly'].includes(e.status))
  const received = held.filter(e => e.status === 'Provided')
  const found = held.filter(e => e.status === 'Found publicly')
  const required = applicable.filter(e => e.status !== 'Suggested')
  const missing = applicable.filter(e => e.status === 'Missing')
  const generate = applicable.filter(e => e.status === 'Can generate')
  const suggested = applicable.filter(e => e.status === 'Suggested')
  const notApplicable = data.expected_documents.filter(e => !e.applicable || e.status === 'Not applicable')
  const waived = applicable.filter(e => e.status === 'Dismissed')
  const flagged = data.documents.filter(d => d.current !== false && (d.conflict_status === 'pending' || (d.entity && d.entity !== borrower)))
  const unreviewed = data.documents.filter(d => d.origin === 'public' && d.current && !d.confirmed_by)
  const startable = DRAFT_ORDER.map(id => data.sections.find(s => s.section_id === id)).filter(s => s && canStart(s))
  const drafted = data.sections.filter(s => s.current_draft_id).length
  const spreadOffer = data.generation_offers.find(o => o.kind === 'spread')

  const record = list => setResults({ at: new Date(), list })
  const filesSelected = files => run('Reading files', async () => {
    const list = []
    for (const file of files) {
      try {
        if (file.size > 25 * 1024 * 1024) throw new Error('File is larger than the 25 MB limit.')
        const preset = await demoMetadata(file, data.intake.presets)
        list.push(await upload(caseId, file, preset || { entity: borrower, scope: 'default', synthetic: false }))
      } catch (error) { list.push({ filename: file.name, outcome: 'rejected', explanations: [error.message] }) }
    }
    record(list)
  })
  const scan = () => run('Scanning folder', async () => {
    record(await post(`${casePath(caseId)}/documents/scan`, { folder_id: folder.id, metadata_by_path: folder.metadata_by_path || {} }))
  })
  const search = () => run('Searching saved public sources', () => post(`${casePath(caseId)}/public-search`, { actor, role: 'CA' }))
  const confirmPublic = () => run('Recording your review of public files', async () => {
    for (const doc of unreviewed) await post(`${casePath(caseId)}/documents/${doc.id}/confirm`, { actor, role: 'CA' })
  })
  const spread = () => run('Generating the financial spread', async () => {
    const result = await post(`${casePath(caseId)}/demo/spread`, { actor, role: 'CA' })
    if (result.spread.validation_status !== 'valid') throw new Error(`The spread needs review: ${result.spread.issues.join('; ')}`)
  })
  const startDrafting = () => run('Drafting sections', async () => {
    const failed = []
    for (const [index, section] of startable.entries()) {
      setProgress(`Drafting section ${section.section_id}, ${index + 1} of ${startable.length}`)
      try { await post(`${casePath(caseId)}/drafts/sections/${section.section_id}`, { actor, role: 'CA', confirm_unsecured: unsecured }) }
      catch (error) { failed.push(`Section ${section.section_id}: ${error.message}`) }
    }
    setProgress('')
    if (failed.length) throw new Error(`Some sections could not be drafted. ${failed.join(' ')}`)
    window.location.hash = '#/workbench'
  }).finally(() => setProgress(''))

  const count = outcome => results.list.filter(r => r.outcome === outcome).length
  return <main className="inputs">
    <div className="step"><span className="n">1</span><h2>Add files</h2><span className="sub">Add them as they arrive. Nothing is lost when you add more later.</span></div>
    <div className={`upload${data.intake.folders.length ? '' : ' alone'}`}>
      <FileUpload onFiles={filesSelected} busy={busy} />
      {data.intake.folders.length > 0 && <div className="card scan"><b>Or scan a folder</b>
        <small>Reads every file in a prepared folder in one go, in place of uploading them one by one. In this demo the folders hold the sample deal papers that come with the project.</small>
        <div className="row"><select aria-label="Folder to scan" value={folderId} disabled={busy} onChange={e => setFolderId(e.target.value)}>
          {data.intake.folders.map(f => <option key={f.id} value={f.id}>{f.label}</option>)}</select>
          <button className="btn" disabled={busy || !folder} onClick={scan}>Scan folder</button></div>
      </div>}
    </div>
    {results && <div className="card result" role="status">
      <span>Last intake, {results.at.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}:</span>
      <span><b>{results.list.length}</b>files read</span>
      <span><b>{results.list.filter(r => r.document && r.document.entity === borrower && r.document.conflict_status !== 'pending').length}</b>matched to {borrower}</span>
      <span><b>{count('duplicate')}</b>duplicate{count('duplicate') === 1 ? '' : 's'} skipped</span>
      <span><b className={flagged.length ? 'bad' : ''}>{results.list.filter(r => r.outcome === 'rejected' || r.document?.conflict_status === 'pending').length}</b>flagged</span>
    </div>}
    {flagged.map(doc => <div className="flag" key={doc.id} role="alert">
      <div className="txt"><b>This file may not belong to this borrower.</b> <code>{doc.original_filename}</code> {doc.entity && doc.entity !== borrower
        ? <>names <b className="plain">{doc.entity}</b>. The target borrower is {borrower}.</> : 'needs your review.'} It is not used in any draft until it is reviewed.
        {(doc.intake.issues || []).map((issue, i) => <small key={i}>{issue}</small>)}</div>
      <a className="btn small" href={contentUrl(caseId, doc.id)} target="_blank" rel="noreferrer">View file</a>
    </div>)}

    <div className="step"><span className="n">2</span><h2>Checklist</h2><span className="sub">Every document for this paper and where it stands, and which sections can start.</span></div>
    <div className="grid">
      <section className="card col" aria-label="Documents">
        <h3>Documents <span className="count">{held.length} of {required.length} required received</span></h3>
        <div className="group">Required, still outstanding <span>{missing.length}</span></div>
        {!missing.length && <p className="empty">Nothing outstanding. Every required document is received, found publicly or can be generated.</p>}
        {missing.map(item => <Item key={item.id} item={item} data={data}>
          {OWNER[item.usual_owner] ? ` ${OWNER[item.usual_owner]}.` : ''}{item.search_outcome === 'not run' ? '' : ' Not found in public sources.'}</Item>)}
        <div className="group">Received <span>{received.length}</span></div>
        {!received.length && <p className="empty">Nothing yet. Add files above.</p>}
        {received.map(item => <Item key={item.id} item={item} data={data} />)}
        {generate.length > 0 && <><div className="group">Can be generated <span>{generate.length}</span></div>
          {generate.map(item => <Item key={item.id} item={item} data={data}>
            {spreadOffer?.expected_id === item.id && data.demo_spread_available
              ? <button className="btn small" disabled={busy} onClick={spread}>Generate now</button> : ' For you to confirm. Not available in this build yet.'}</Item>)}</>}
        {suggested.length > 0 && <><div className="group">Suggested, not required <span>{suggested.length}</span></div>
          {suggested.map(item => <Item key={item.id} item={item} data={data} />)}</>}
        {(notApplicable.length > 0 || waived.length > 0) && <><div className="group">Does not apply to this case <span>{notApplicable.length + waived.length}</span></div>
          {notApplicable.map(item => <div className="item" key={item.id}><span className="name light">{item.name}</span><Chip tone="grey">Not applicable</Chip>
            <span className="meta">{item.reason.replace(/^Case does not meet rule: /, 'Only needed for: ')}</span></div>)}
          {waived.map(item => <div className="item" key={item.id}><span className="name light">{item.name}</span><Chip tone="grey">Waived</Chip>
            <span className="meta">Waived by {item.confirmed_by}: {item.dismiss_reason}</span></div>)}</>}
        <div className="group">Public sources <span>
          {unreviewed.length > 0 && <button className="btn small" disabled={busy} onClick={confirmPublic}>Mark {unreviewed.length} public file{unreviewed.length === 1 ? '' : 's'} as reviewed</button>}
          {' '}<button className="btn small" disabled={busy} onClick={search}>Search public sources</button></span></div>
        {!found.length && <p className="empty">No required document has been filled from public sources yet.</p>}
        {found.map(item => <Item key={item.id} item={item} data={data} />)}
        <div className="foot"><span>{data.documents.length} file{data.documents.length === 1 ? '' : 's'} in total · <a href="#/classic">See all files and versions</a></span>
          <a className="btn small" href={requestListUrl(caseId)}>Export request list</a></div>
      </section>

      <section className="card col" aria-label="Sections that can start">
        <h3>Sections that can start <span className="count">{data.sections.filter(s => s.current_draft_id || canStart(s)).length} of {data.sections.length}</span></h3>
        {data.sections.map(section => {
          const status = sectionStatus(section)
          const [tone, label] = section.current_draft_id ? ['blue', status === 'Confirmed' ? 'Confirmed' : 'Drafted']
            : status === 'Not applicable' ? ['grey', 'Not applicable']
            : section.readiness === 'Can draft (full)' ? ['green', 'Ready']
            : section.readiness === 'Can draft (partial)' ? ['blue', 'Ready, with gaps'] : ['amber', 'Waiting']
          return <div className="sec" key={section.section_id}><span className="num">{section.section_id}</span><span>{section.name}</span><Chip tone={tone}>{label}</Chip>
            {!section.current_draft_id && section.gaps[0] && label !== 'Ready' && <span className="why">{label === 'Waiting' ? 'Needs: ' : 'Gap: '}{shortGap(section.gaps[0])}{section.gaps.length > 1 ? ` and ${section.gaps.length - 1} more` : ''}</span>}
            {section.na_reason && <span className="why">{section.na_reason}</span>}</div>
        })}
        <div className="go">
          {startable.some(s => [7, 8].includes(s.section_id)) && (!spec || !data.case.property_or_asset_security) && <label className="check"><input type="checkbox" checked={unsecured} disabled={busy} onChange={e => setUnsecured(e.target.checked)} />
            {spec ? 'I confirm that any facility described as unsecured in the deal papers is correctly described (used in sections 7 and 8).'
              : "I confirm the term sheet's description of the RCF as unsecured (used in sections 7 and 8)."}</label>}
          {startable.length > 0 ? <button className="btn primary" disabled={busy} onClick={startDrafting}>{progress || `Start drafting ${startable.length} section${startable.length === 1 ? '' : 's'}`}</button>
            : <a className={`btn primary${drafted ? '' : ' disabled'}`} href="#/workbench">Open ES workbench</a>}
          <p>Drafts are for your review. You confirm each section.</p>
        </div>
      </section>
    </div>
  </main>
}
