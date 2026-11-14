// Display vocabulary from project file section 2.14, mapped from the back end's saved states.
export const DOC_STATUS = {
  Provided: 'Received', 'Found publicly': 'Sourced publicly', 'Can generate': 'Can be generated', Missing: 'Outstanding',
  Suggested: 'Suggested', 'Not applicable': 'Not applicable', Dismissed: 'Waived',
}
export const DOC_TONE = {
  Received: 'green', 'Sourced publicly': 'blue', 'Can be generated': 'blue', Outstanding: 'amber',
  Suggested: 'grey', 'Not applicable': 'grey', Waived: 'grey',
}
export const SECTION_ICON = {
  Confirmed: ['ok', '✓'], 'In progress': ['prog', ''], 'Update required': ['upd', '!'],
  'Pending inputs': ['pend', '…'], 'Not started': ['none', ''], 'Not applicable': ['na', '–'],
}
export function sectionStatus(section) {
  if (!section.applicable || section.readiness === 'Not applicable') return 'Not applicable'
  if (section.readiness === 'CA confirmed') return 'Confirmed'
  if (section.readiness === 'Stale') return 'Update required'
  if (section.current_draft_id) return 'In progress'
  return section.readiness === 'Waiting for input' ? 'Pending inputs' : 'Not started'
}
export const canStart = section => section.applicable && !section.current_draft_id && section.readiness.startsWith('Can draft')
export function esStatus(data) {
  const state = stage(data.case.workflow_state)[0]
  const opened = new Date(data.case.first_upload_at || data.case.created_at)
  const days = Math.max(0, Math.floor((Date.now() - opened.getTime()) / 86400000))
  const pending = data.counts.documents.Missing || 0
  return { state, days, pending, text: `open ${days} day${days === 1 ? '' : 's'} · ${pending} input${pending === 1 ? '' : 's'} pending` }
}
// Sections in the order their inputs allow: 9 needs 7 and 10; 11 needs 3 to 10; 14 is last.
export const DRAFT_ORDER = [1, 2, 3, 4, 5, 6, 7, 8, 10, 9, 11, 12, 13, 14]
export const shortGap = gap => gap.split(':')[0].split(';')[0]

// Roles shown in this build, and how each workflow state reads on the screen.
export const ROLES = { CA: { label: 'Credit analyst', short: 'Maker', actor: 'demo-ca' }, 'Credit Head': { label: 'Credit Head', short: 'Checker', actor: 'demo-credit-head' } }
const STAGE = { Draft: ['Drafting', 'blue'], 'Submitted to Credit Head': ['Submitted for review', 'amber'], 'Returned to CA': ['Returned to analyst', 'amber'], Supported: ['Supported', 'green'],
  'With Credit Approver': ['With Credit Approver', 'blue'], 'Question to CA': ['Question to analyst', 'amber'], Approved: ['Approved', 'green'], 'Approved with conditions': ['Approved with conditions', 'green'], Declined: ['Declined', 'grey'] }
export const stage = state => STAGE[state] || [state, 'grey']
