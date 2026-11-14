// Counts describe saved work, never credit approval or submission readiness.
export function draftProgress(sections) {
  return {
    saved: sections.filter(s => s.current_draft_id).length,
    confirmed: sections.filter(s => s.readiness === 'CA confirmed').length,
    stale: sections.filter(s => s.readiness === 'Stale').length,
    na: sections.filter(s => s.readiness === 'Not applicable' && s.na_reason).length,
  }
}

export function trancheProgress(data) {
  return [1, 2, 3].map(number => {
    const presets = data.intake.presets.filter(p => p.tranche === number)
    const held = presets.filter(p => data.documents.some(d => d.content_hash === p.sha256 && d.current)).length
    return { number, held, total: presets.length }
  })
}

export function exportRevision(data) {
  return JSON.stringify([data.case.id, data.case.workflow_state, data.sections, data.documents, data.expected_documents])
}

export function mergeExportHistory(current, loaded) {
  return [...new Map([...loaded, ...current].map(item => [item.id, item])).values()]
    .sort((a, b) => a.created_at.localeCompare(b.created_at) || a.id.localeCompare(b.id))
}
