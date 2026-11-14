// UI guards mirror B13; the API remains authoritative for validation and locks.
export function editableClaim(claim) {
  return typeof claim.text === 'string' && !claim.computed_value_id && !claim.computed_value_ids?.length &&
    !['draft_metadata', 'computed_summary', 'case_input', 'ca_position', 'ca_input'].includes(claim.kind) &&
    !claim.internal_rating && !claim.requires_unsecured_confirmation
}
export function versionToken(section, actor) {
  return { actor, role: 'CA', expected_draft_id: section.current_draft_id,
    expected_revision: section.editor_revision, expected_input_fingerprint: section.input_fingerprint }
}
export function sameRevision(a, b) {
  return !!a && !!b && a.current_draft_id === b.current_draft_id &&
    a.editor_revision === b.editor_revision && a.input_fingerprint === b.input_fingerprint
}
export function changedClaims(draft, edits) {
  return Object.fromEntries((draft?.claim_spans || []).filter(c => editableClaim(c) &&
    Object.hasOwn(edits, c.id) && edits[c.id] !== c.text).map(c => [c.id, edits[c.id]]))
}
export function sourcePageLabel(source) {
  if (source.origin === 'CA input') return `CA input · message ${source.message_id}`
  return `${source.locator?.format === 'pdf' ? 'PDF page' : 'Normalized page'} ${source.page}` +
    (source.printed_page ? ` · printed ${source.printed_page}` : '') +
    (source.region && source.region !== 'whole' ? ` · region ${source.region}` : '')
}
