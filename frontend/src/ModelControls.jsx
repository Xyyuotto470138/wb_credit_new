import { useRef, useState } from 'react'
import { casePath, post } from './api/client'

export function ModelOptions({ models }) {
  return models.map(model => <option key={model.id} value={model.id} disabled={!model.runnable}>
    {model.display_name}{model.bank_available ? ' · bank family available' : ''}{!model.runnable ? ' · disabled' : ''}
  </option>)
}

export function CaseModelPicker({ data, actor, disabled, run }) {
  const models = data.model_registry?.models || []
  const [choice, setChoice] = useState('')
  const current = data.case.default_model_id || 'mock-v1'
  return <section className="panel"><h2>Drafting model</h2>
    <p>Case default: {models.find(m => m.id === current)?.display_name || current}. Existing versions retain their recorded model.</p>
    <label>New case default<select value={choice || current} disabled={disabled} onChange={e => setChoice(e.target.value)}>
      <ModelOptions models={models} />
    </select></label>
    <p>Estimated cost per mock run: US$0. Live calls are disabled; enabling a registry entry does not authorize spend.</p>
    <button disabled={disabled || !actor.trim() || !choice || choice === current || !models.some(m => m.id === choice && m.runnable)} onClick={() => run('Saving case model', async () => {
      await post(`${casePath(data.case.id)}/model`, { actor, role: 'CA', model_id: choice, expected_model_id: current })
      setChoice('')
      return 'Case default saved. Existing draft versions are unchanged.'
    })}>Save case default</button>
    <details><summary>Configured model routes</summary><ul>{models.map(model => <li key={model.id}>
      <strong>{model.display_name}</strong> · {model.runnable ? 'offline mock available' : model.blocked_reason}
      {model.bank_available && ' · bank family available; exact deployment unconfirmed'}
      <small>{model.weights.replaceAll('_', ' ')} · {model.model_id || 'TODO: confirm model ID'} · {model.notes}</small>
    </li>)}</ul></details>
  </section>
}

export function ComparisonResults({ result }) {
  return <section className="comparison-results" aria-label="Model comparison results">
    <p className="notice">Preview only; working draft and confirmations are unchanged. These offline fixtures demonstrate the comparison workflow, not model quality.</p>
    <p>Same prompt and evidence verified. Python computed tables: {result.computed_tables_identical ? 'identical' : 'mismatch'} ({result.computed_table_count}{result.computed_table_count === 0 ? '; none in this section' : ''}).</p>
    <p>Python computed metrics: {result.computed_values_identical ? 'identical' : 'not checked'} ({result.computed_value_count ?? 0}).</p>
    <details><summary>Comparison input and table fingerprints</summary><p>Prompt: {result.prompt_hash}</p><p>Evidence: {result.evidence_hash}</p><p>Tables: {result.computed_tables_hash}</p></details>
    <div className="model-comparison">{result.results.map(item => <article key={item.model.id}>
      <h4>{item.model.display_name}</h4><p>Recorded model: {item.draft.model_version}</p>
      <dl><dt>Citation coverage</dt><dd>{item.metrics.citation_coverage.percent === null ? 'N/A — no displayed claims' : `${item.metrics.citation_coverage.percent}% (${item.metrics.citation_coverage.cited}/${item.metrics.citation_coverage.total})`}</dd>
        <dt>Unsupported claims rejected</dt><dd>{item.metrics.unsupported_claims_rejected}</dd>
        <dt>Malformed response</dt><dd>{item.metrics.malformed_response ? 'Yes — review gaps' : 'No'}</dd>
        <dt>Reviewed claims omitted</dt><dd>{item.metrics.omitted_claims}</dd>
        <dt>Latency</dt><dd>{item.metrics.latency_ms} ms · local response/validation</dd>
        <dt>Estimated cost</dt><dd>US${item.metrics.estimated_cost_usd} · offline fixture</dd>
      </dl><small>{item.metrics.citation_coverage.basis}</small>
      <details><summary>Gap markers ({item.metrics.gap_markers.length})</summary><ul>{item.metrics.gap_markers.map(g => <li key={g}>{g}</li>)}</ul></details>
      <pre className="saved-section">{item.draft.text}</pre>
    </article>)}</div>
    <p>To save a version, choose its model in the section picker and explicitly create or redraft after reviewing current inputs.</p>
  </section>
}

export function ModelCompare({ caseId, section, actor, options, models, disabled, run }) {
  const available = models.filter(m => m.runnable)
  const [left, setLeft] = useState(available[0]?.id || '')
  const [right, setRight] = useState(available[1]?.id || '')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const lock = useRef(false)
  const runnable = [left, right].every(id => models.some(m => m.id === id && m.runnable))
  const compare = () => {
    if (lock.current) return
    lock.current = true
    run('Comparing model drafts', async () => {
      setError(''); setResult(null)
      try {
        const value = await post(`${casePath(caseId)}/sections/${section.section_id}/compare`, {
          actor, role: 'CA', ...options, model_ids: [left, right], expected_draft_id: section.current_draft_id,
          expected_revision: section.editor_revision, expected_input_fingerprint: section.input_fingerprint,
        })
        setResult(value)
        return 'Comparison ready. No draft version was saved.'
      } catch (e) { setError(e.message); throw e }
    }).finally(() => { lock.current = false })
  }
  return <section className="model-compare"><h3>Compare two models</h3>
    <div className="toolbar"><label>Left model<select value={left} disabled={disabled} onChange={e => { setLeft(e.target.value); setResult(null) }}><ModelOptions models={models} /></select></label>
      <label>Right model<select value={right} disabled={disabled} onChange={e => { setRight(e.target.value); setResult(null) }}><ModelOptions models={models} /></select></label></div>
    <p>{runnable ? 'Estimated combined cost: US$0 (two offline mocks).' : 'Estimate unavailable: choose two enabled offline mocks.'} Both use the same current evidence and prompt. Computed tables come from Python.</p>
    <button disabled={disabled || !runnable || left === right} onClick={compare}>Compare section drafts</button>
    {left === right && left && <p>Choose two different models.</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {result && <ComparisonResults result={result} />}
  </section>
}
