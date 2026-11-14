import { useEffect, useRef, useState } from 'react'
import { casePath, post, request } from './api/client'
import { versionToken } from './sectionModel'

export function ProposalReview({ proposal, disabled, resolve, acceptNumeric, setAcceptNumeric }) {
  const numeric = proposal.payload?.request?.numeric
  return <article className="chat-proposal">
    <h4>Proposed revision · {proposal.status}</h4>
    <p>MOCK CHAT · {proposal.model_version} · base draft {proposal.base_draft_id}</p>
    {numeric && <>
      <p><strong>{numeric.synthetic && 'SYNTHETIC DEMO DATA · '}CA numeric input</strong> · {numeric.metric_id} · {numeric.period} · {numeric.scope}</p>
      <p>Basis: {numeric.basis}. Supplied values are CA assertions, not independently verified.</p>
      <ul>{Object.entries(numeric.operands).flatMap(([key, rows]) => rows.map((row, i) => <li key={`${key}-${i}`}>{key}: {row.value} {row.unit} {row.currency}</li>))}</ul>
      <ul>{proposal.payload.results.map(result => <li key={result.metric}>{result.name}: {result.display ?? 'N/A'} {result.unit}
        {result.gaps.map(gap => <p className="notice" key={gap}>{gap}</p>)}</li>)}</ul>
    </>}
    <details open><summary>Complete proposed text and sources</summary><pre className="saved-section">{proposal.proposed_text}</pre></details>
    {proposal.status === 'pending' && <>
      {numeric && <label className="check"><input type="checkbox" checked={acceptNumeric} disabled={disabled} onChange={e => setAcceptNumeric(e.target.checked)} />I accept these operands as sourced CA input and request Python recomputation. Invalid or incomplete results remain gaps.</label>}
      <div className="toolbar"><button disabled={disabled || (!!numeric && !acceptNumeric)} onClick={() => resolve('accept')}>Accept revision{numeric ? ' and recompute' : ''}</button>
        <button disabled={disabled} onClick={() => resolve('reject')}>Reject revision</button></div>
    </>}
    {proposal.resolved_by && <p>{proposal.status} by {proposal.resolved_by} · {proposal.resolved_at}</p>}
    {proposal.status === 'stale' && <p className="notice">The base section or inputs changed. Reload the section and request a fresh proposal.</p>}
  </article>
}

export default function SectionChat({ caseId, section, draft, actor, disabled, run, onChanged, onDirtyChange }) {
  const path = `${casePath(caseId)}/sections/${section.section_id}/chat`
  const [history, setHistory] = useState({ proposals: [], messages: [] })
  const [metrics, setMetrics] = useState([])
  const [message, setMessage] = useState('')
  const [mode, setMode] = useState('fact')
  const [claimId, setClaimId] = useState('')
  const [metricId, setMetricId] = useState('')
  const [period, setPeriod] = useState('')
  const [scope, setScope] = useState('')
  const [basis, setBasis] = useState('')
  const [values, setValues] = useState({})
  const [currency, setCurrency] = useState('SGD')
  const [synthetic, setSynthetic] = useState(true)
  const [accepted, setAccepted] = useState({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const lock = useRef(false)
  const metric = metrics.find(m => m.id === metricId)
  const dirty = !!(message || period || scope || basis || Object.keys(values).length)
  useEffect(() => { onDirtyChange(dirty); return () => onDirtyChange(false) }, [dirty, onDirtyChange])
  useEffect(() => {
    let active = true
    Promise.all([request(path), request(`${path}/metrics`)]).then(([saved, options]) => {
      if (active) { setHistory(saved); setMetrics(options); setLoading(false) }
    }).catch(e => { if (active) { setError(e.message); setLoading(false) } })
    return () => { active = false }
  }, [path, section.current_draft_id, section.editor_revision, section.input_fingerprint])
  const reset = () => { setMessage(''); setPeriod(''); setScope(''); setBasis(''); setValues({}) }
  const execute = (label, task) => {
    if (lock.current) return
    lock.current = true
    run(label, async () => {
      setError('')
      try { return await task() }
      catch (e) { setError(e.message); throw e }
    }).finally(() => { lock.current = false })
  }
  const propose = () => execute('Preparing chat proposal', async () => {
    const numeric = mode === 'numeric' ? { metric_id: metricId, period, scope, basis,
      synthetic, operands: Object.fromEntries(Object.entries(values).filter(([, value]) => value.trim()).map(([key, value]) => [key,
        [{ value, unit: metric.input_units[key], ...(metric.input_units[key].startsWith('currency') ? { currency } : {}) }]])) } : undefined
    await post(path, { ...versionToken(section, actor), message, mode, synthetic,
      ...(mode === 'emphasize' ? { claim_id: claimId } : {}), ...(numeric ? { numeric } : {}) })
    reset()
    setHistory(await request(path))
    return 'Proposal saved for CA review. The section text is unchanged until accepted.'
  })
  const resolve = (proposal, action) => execute('Recording chat decision', async () => {
    await post(`${path}/${encodeURIComponent(proposal.id)}/decision`, { actor, role: 'CA', action,
      accept_numeric_input: !!accepted[proposal.id] })
    setHistory(await request(path))
    await onChanged()
    return action === 'accept' ? 'Revision accepted as a new draft. Review the section before confirming.' : 'Proposal rejected; saved wording is unchanged.'
  })
  const blocked = disabled || loading
  return <section className="section-chat" aria-label="Typed section chat">
    <h3>Typed section chat</h3>
    <p>MOCK CHAT · Emphasize a sourced claim or add a verbatim CA assertion. Each proposal keeps citations and gaps for review. The offline model uses saved operations; free-form model rewriting requires a later approved live run.</p>
    {section.section_id === 12 && <p>CA notes do not supply or change the internal rating. Upload the current rating report.</p>}
    {section.section_id === 14 && <p>The human position remains unchanged. Use the CA-stated position and Redraft controls above to change it.</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {loading && <p role="status">Loading chat history…</p>}
    <label>Revision type<select value={mode} disabled={blocked} onChange={e => setMode(e.target.value)}>
      <option value="fact">Add CA fact or review note</option><option value="emphasize">Emphasize an existing sourced claim</option>
      {!!metrics.length && <option value="numeric">Supply numeric operands for Python</option>}
    </select></label>
    {mode === 'emphasize' && <label>Claim to emphasize<select value={claimId} disabled={blocked} onChange={e => setClaimId(e.target.value)}>
      <option value="">Select claim</option>{draft.claim_spans.slice(1).filter(c => c.kind !== 'ca_position').map((c, i) => <option key={c.id} value={c.id}>{i + 1}. {c.text.slice(0, 120)}</option>)}
    </select><small>Moves the exact cited claim earlier; all other claims remain.</small></label>}
    <label>{mode === 'fact' ? 'CA fact or note (no numeric changes)' : 'Request / review context'}<textarea rows={3} value={message} maxLength={10000} disabled={blocked} onChange={e => setMessage(e.target.value)} /></label>
    {mode === 'numeric' && <fieldset disabled={blocked}><legend>Explicit sourced operands</legend>
      <label>Metric<select value={metricId} onChange={e => { setMetricId(e.target.value); setValues({}); setBasis('') }}><option value="">Select metric</option>
        {metrics.filter(m => !['bucket_sum', 'weighted_average', 'sum'].includes(m.formula.op)).map(m => <option key={m.id} value={m.id}>{m.name}</option>)}</select></label>
      {metric && <><p>{metric.definition}</p><small>Enter base units shown below. Missing or incompatible operands produce named gaps.</small>
        <label>Period<input value={period} maxLength={80} onChange={e => setPeriod(e.target.value)} placeholder="2026-11-11" /></label>
        <label>Scope<input value={scope} maxLength={200} onChange={e => setScope(e.target.value)} placeholder="Group or named property" /></label>
        <label>Basis<input value={basis} maxLength={100} onChange={e => setBasis(e.target.value)} /></label>
        {metric.required_basis && <p>Required basis: {metric.required_basis}. Enter it only after reviewing the input definition.</p>}
        <label>Currency<input value={currency} maxLength={3} onChange={e => setCurrency(e.target.value.toUpperCase())} /></label>
        {[...new Set([...metric.formula.operands, ...(metric.reconcile_to ? [metric.reconcile_to] : [])])].map(key => <label key={key}>{key.replaceAll('_', ' ')} ({metric.input_units[key]})<input inputMode="decimal" value={values[key] || ''} onChange={e => setValues(old => ({ ...old, [key]: e.target.value }))} /></label>)}
        <label className="check"><input type="checkbox" checked={synthetic} onChange={e => setSynthetic(e.target.checked)} />SYNTHETIC DEMO DATA</label>
      </>}
    </fieldset>}
    {mode === 'fact' && <label className="check"><input type="checkbox" checked={synthetic} disabled={blocked} onChange={e => setSynthetic(e.target.checked)} />SYNTHETIC DEMO DATA</label>}
    <p><small>Numeric changes belong to section 10’s configured metrics. Exposure, conduct and projection tables require revised source files; chat cannot edit their cells.</small></p>
    <div className="toolbar"><button disabled={blocked || !message.trim() || (mode === 'emphasize' && !claimId) || (mode === 'numeric' && (!metric || !period.trim() || !scope.trim() || !basis.trim()))} onClick={propose}>Propose revision</button>
      <button disabled={!dirty} onClick={reset}>Discard typed input</button>
      <button disabled={disabled} onClick={() => execute('Reloading chat', async () => { setHistory(await request(path)); return 'Chat history reloaded.' })}>Reload chat history</button></div>
    {[...history.proposals].reverse().map(p => <div key={p.id}>
      <p className="chat-message">CA message · {history.messages.find(m => m.id === p.message_id)?.actor}: {history.messages.find(m => m.id === p.message_id)?.text}</p>
      <ProposalReview proposal={p} disabled={disabled || dirty} resolve={action => resolve(p, action)} acceptNumeric={!!accepted[p.id]} setAcceptNumeric={value => setAccepted(old => ({ ...old, [p.id]: value }))} />
    </div>)}
  </section>
}
