// Arranges one saved draft for display. Values and wording are shown as saved; only number formatting is applied.
export function formatValue(value, unit = '') {
  const number = Number(value)
  if (value === null || value === undefined || value === '' || Number.isNaN(number)) return value ?? ''
  if (unit === 'currency_million') return `${number.toLocaleString('en-SG', { maximumFractionDigits: 2 })} m`
  if (unit.startsWith('currency')) return number.toLocaleString('en-SG', { maximumFractionDigits: 2 })
  const text = /\.\d{3,}$/.test(String(value)) ? number.toFixed(2) : String(value)
  if (unit === 'percent') return `${text}%`
  if (unit === 'times') return `${text}x`
  if (unit === 'percentage points') return `${text} pp`
  return unit && !['cents', 'sgd_per_unit', 'count'].includes(unit) ? `${text} ${unit.replaceAll('_', ' ')}` : text
}
export const columnLabel = key => key.replaceAll('_', ' ').replace(/\bpct\b/, '%').replace(/^./, c => c.toUpperCase())

export function buildBlocks(draft) {
  const numbering = new Map()
  const cite = ids => (ids || []).map(id => {
    if (!numbering.has(id)) numbering.set(id, numbering.size + 1)
    return { id, n: numbering.get(id) }
  })
  const blocks = []
  let facilities, financials, measures, heading
  for (const claim of draft.claim_spans.slice(1)) {
    const cites = cite(claim.evidence_ids)
    if (claim.kind === 'facility') {
      if (!facilities) blocks.push(facilities = { type: 'facilities', names: [], fields: [], cells: {} })
      if (!facilities.names.includes(claim.facility)) facilities.names.push(claim.facility)
      if (!facilities.fields.includes(claim.field)) facilities.fields.push(claim.field)
      ;(facilities.cells[`${claim.field}|${claim.facility}`] ||= []).push({ claim, cites })
    } else if (claim.financial_cell && claim.reviewed_value) {
      if (!financials) blocks.push(financials = { type: 'financials', periods: [], labels: [], cells: {} })
      const period = claim.financial_cell.interim ? 'Interim' : `FY${claim.reviewed_value.period}`
      if (!financials.periods.includes(period)) financials.periods.push(period)
      if (!financials.labels.includes(claim.financial_cell.label)) financials.labels.push(claim.financial_cell.label)
      financials.cells[`${claim.financial_cell.label}|${period}`] = { claim, cites }
    } else if (claim.kind === 'computed' && claim.value) {
      // Spread line items (one per statement row and year) are kept together, apart from the headline measures.
      const spread = /^\d{4}$/.test(claim.value.period || '')
      if (!measures) blocks.push(measures = { type: 'measures', rows: [], spread: [] })
      measures[spread ? 'spread' : 'rows'].push({ claim, cites, name: claim.text.split(':')[0].replaceAll('_', ' ').replace(/^cf /, 'Cash flow: ').replace(/^./, c => c.toUpperCase()) })
    } else {
      const title = claim.subpart || (claim.kind === 'risk_mitigant' ? 'Risks and mitigants' : claim.kind === 'ca_input' ? 'CA input' : '')
      if (title && title !== heading) blocks.push({ type: 'heading', text: heading = title })
      blocks.push({ type: 'para', claim, cites })
    }
  }
  if (financials) financials.periods.sort((a, b) => (a === 'Interim') - (b === 'Interim') || a.localeCompare(b))
  const metadata = draft.claim_spans[0] || {}
  // Specification-driven drafts also cite sources from table cells and answers.
  if (metadata.parts) Object.keys(metadata.source_register || {}).forEach(id => { if (!numbering.has(id)) numbering.set(id, numbering.size + 1) })
  return { blocks, numbering, metadata, tables: metadata.computed_tables || [] }
}
