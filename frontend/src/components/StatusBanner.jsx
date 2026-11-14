// Adapted from Phase 1 StatusBanner: explicit current stage, future stages remain labelled.
export default function StatusBanner({ workflowState, hasDraft = false }) {
  const stage = workflowState !== 'Draft' ? 3 : hasDraft ? 2 : 1
  return <nav className="stage-strip" aria-label="Case stages">
    <span aria-current={stage === 1 ? 'step' : undefined}><b>1</b> Intake & readiness</span>
    <span aria-current={stage === 2 ? 'step' : undefined}><b>2</b> Prepare ES</span>
    <span aria-current={stage === 3 ? 'step' : undefined}><b>3</b> Review & decision <small>Workflow controls pending</small></span>
    <span className="workflow">ES status: <strong>{workflowState}</strong></span>
  </nav>
}
